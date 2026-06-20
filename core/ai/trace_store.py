"""AI 对话 trace 本地落盘与读取（调试工作台 · 方案 A）。

目标：把每一轮真实对话的"完整输入 + 原始输出 + 用量/延迟"结构化落盘，
取代"人肉导出 md"的调试方式；供 replay 重放对比与 curator 转 eval 用例复用。

设计约束（对齐项目铁律）：
  - 不含 Qt 依赖，可在任意线程安全调用（纯文件 IO）；
  - 全程经 mask_sensitive 二次脱敏，不落原始日志 / 串口数据 / API Key / 序列号；
  - 隐私开关 trace_enabled=False 时彻底不采集、不写盘（record 直接 return）；
  - 禁 print，统一 log_config；异常 exc_info=True，禁裸 except。

落盘位置：get_user_data_dir("ai", "traces")/<YYYY-MM-DD>.jsonl，每行一轮 trace。
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from core.ai.config import AISettings
from core.ai.prompt_manager import mask_sensitive
from ui.resource_path import get_user_data_dir
from log_config import get_logger

logger = get_logger(__name__)

_TRACES_SUBDIR = "traces"
_MAX_RAW_OUTPUT_CHARS = 20000


def _traces_dir() -> str:
    return get_user_data_dir("ai", _TRACES_SUBDIR)


def _today_path() -> str:
    day = time.strftime("%Y-%m-%d", time.localtime())
    return os.path.join(_traces_dir(), f"{day}.jsonl")


def _hash_text(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:12]


def _mask_messages(messages: list[dict]) -> list[dict]:
    """对喂给模型的 messages 逐条脱敏；保留 role/角色结构，只清洗字符串内容。"""
    masked: list[dict] = []
    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        item: dict[str, Any] = {}
        for key, val in msg.items():
            if isinstance(val, str):
                item[key] = mask_sensitive(val)
            else:
                item[key] = val
        masked.append(item)
    return masked


@dataclass
class TraceRecord:
    """单轮对话的完整结构化快照（已脱敏）。"""

    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    ts: float = field(default_factory=time.time)
    page_key: str = ""
    mode: str = ""
    model: str = ""
    temperature: float = 0.0
    max_tokens: int = 0
    system_prompt_hash: str = ""
    messages_in: list[dict] = field(default_factory=list)
    raw_output: str = ""
    reasoning: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    usage: dict | None = None
    latency_ms: int = 0
    rating: str | None = None
    error: str | None = None

    def to_record(self) -> dict:
        return asdict(self)


def build_trace(
    *,
    page_key: str | None,
    mode: str,
    model: str,
    temperature: float,
    max_tokens: int,
    messages_in: list[dict],
    raw_output: str = "",
    reasoning: str = "",
    tool_calls: list[dict] | None = None,
    usage: dict | None = None,
    latency_ms: int = 0,
    error: str | None = None,
) -> TraceRecord:
    """组装一条 TraceRecord（含脱敏与正文截断），不落盘。"""
    masked_messages = _mask_messages(messages_in)
    system_text = ""
    for msg in masked_messages:
        if msg.get("role") == "system":
            system_text += str(msg.get("content") or "")
    raw = mask_sensitive(raw_output or "")
    if len(raw) > _MAX_RAW_OUTPUT_CHARS:
        raw = raw[:_MAX_RAW_OUTPUT_CHARS] + "…(truncated)"
    return TraceRecord(
        page_key=page_key or "",
        mode=str(mode or ""),
        model=str(model or ""),
        temperature=float(temperature),
        max_tokens=int(max_tokens),
        system_prompt_hash=_hash_text(system_text),
        messages_in=masked_messages,
        raw_output=raw,
        reasoning=mask_sensitive(reasoning or ""),
        tool_calls=list(tool_calls or []),
        usage=usage,
        latency_ms=int(latency_ms),
        error=error,
    )


def record(trace: TraceRecord, settings: AISettings) -> str | None:
    """落盘一条 trace（隐私开关关闭时静默）；返回 trace_id 供 UI 回填 rating。"""
    if not getattr(settings, "trace_enabled", False):
        return None
    try:
        path = _today_path()
        line = json.dumps(trace.to_record(), ensure_ascii=False)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return trace.trace_id
    except Exception:  # noqa: BLE001 - 采集失败绝不影响主流程
        logger.error("写入对话 trace 失败", exc_info=True)
        return None


def list_trace_files() -> list[str]:
    """返回 traces 目录下所有 jsonl 文件的绝对路径（按文件名排序）。"""
    directory = _traces_dir()
    if not os.path.isdir(directory):
        return []
    files = [
        os.path.join(directory, name)
        for name in sorted(os.listdir(directory))
        if name.endswith(".jsonl")
    ]
    return files


def load_traces(path: str) -> list[dict]:
    """读取单个 trace jsonl 文件；损坏行跳过。"""
    records: list[dict] = []
    if not os.path.isfile(path):
        logger.warning("trace 文件不存在: %s", path)
        return records
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        logger.error("读取 trace 文件失败: %s", path, exc_info=True)
    return records


def find_trace(trace_id: str) -> dict | None:
    """在所有 trace 文件中按 trace_id 查找一条（最近文件优先）。"""
    if not trace_id:
        return None
    for path in reversed(list_trace_files()):
        for rec in load_traces(path):
            if rec.get("trace_id") == trace_id:
                return rec
    return None


def set_rating(trace_id: str, rating: str) -> bool:
    """回填某条 trace 的 rating（👍/👎），就地重写所在文件。"""
    if not trace_id:
        return False
    for path in reversed(list_trace_files()):
        records = load_traces(path)
        changed = False
        for rec in records:
            if rec.get("trace_id") == trace_id:
                rec["rating"] = rating
                changed = True
                break
        if changed:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    for rec in records:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                return True
            except OSError:
                logger.error("回写 trace rating 失败: %s", path, exc_info=True)
                return False
    return False

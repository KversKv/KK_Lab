"""AI 对话 trace 重放 / 双模型并排对比（调试工作台 · 方案 A）。

读历史 trace（trace_store 落盘的 messages_in），用指定模型重跑，
命令行并排打印「原始输出 vs 重放输出」与 token/延迟，取代"换窗口手动重问"。

典型用法：
  # 列出最近 trace（trace_id / page / model / 评分 / 首问摘要）
  python -m core.ai.replay --list

  # 用当前配置默认模型重放某条 trace，并与原始输出并排对比
  python -m core.ai.replay --trace <trace_id>

  # 双模型并排对比（GLM vs Deepseek）
  python -m core.ai.replay --trace <trace_id> --models glm-5.1-fp8,deepseekv4flash

  # 重放整文件里所有差评（rating=down）的 trace
  python -m core.ai.replay --file <path.jsonl> --only-down

约束：纯命令行调试工具，不含 Qt 依赖；调模型复用 NewAPIClient；禁 print 之外的副作用。
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from core.ai.config import AISettings
from core.ai.newapi_client import AIClientError, ChatResult, NewAPIClient
from core.ai.trace_store import find_trace, list_trace_files, load_traces
from log_config import get_logger

logger = get_logger(__name__)

_SEP = "=" * 78
_SUBSEP = "-" * 78


@dataclass
class ReplayOutput:
    model: str
    content: str = ""
    latency_ms: int = 0
    total_tokens: int = 0
    tool_called: bool = False
    error: str = ""


def _first_user_text(trace: dict) -> str:
    for msg in reversed(trace.get("messages_in") or []):
        if msg.get("role") == "user":
            return str(msg.get("content") or "")
    return ""


def _short(text: str, width: int = 60) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text[:width] + ("…" if len(text) > width else "")


def list_recent(limit: int = 30, *, only_down: bool = False) -> None:
    """打印最近 trace 概览，供挑选 trace_id。"""
    rows: list[dict] = []
    for path in reversed(list_trace_files()):
        for rec in load_traces(path):
            if only_down and rec.get("rating") != "down":
                continue
            rows.append(rec)
            if len(rows) >= limit:
                break
        if len(rows) >= limit:
            break
    if not rows:
        print("（无 trace 记录；确认 trace_enabled=True 且已发生过对话）")
        return
    print(f"{'trace_id':<14} {'rating':<6} {'page':<16} {'model':<16} 首问")
    print(_SUBSEP)
    for rec in rows:
        print(
            f"{str(rec.get('trace_id',''))[:12]:<14} "
            f"{str(rec.get('rating') or '-'):<6} "
            f"{str(rec.get('page_key') or '-')[:15]:<16} "
            f"{str(rec.get('model') or '-')[:15]:<16} "
            f"{_short(_first_user_text(rec))}"
        )


def _replay_one(messages: list[dict], model: str, settings: AISettings) -> ReplayOutput:
    """用指定模型重跑一组 messages（不带 tools，纯文本重放）。"""
    if not settings.is_configured():
        return ReplayOutput(model=model, error="AI 未配置（缺 base_url / API Key）")
    client = NewAPIClient(
        base_url=settings.effective_base_url,
        api_key=settings.effective_api_key,
        timeout_seconds=settings.timeout_seconds,
    )
    try:
        result: ChatResult = client.chat(
            model=model,
            messages=messages,
            temperature=0.1,
            max_tokens=2048,
        )
    except AIClientError as exc:
        return ReplayOutput(model=model, error=str(exc))
    usage = result.usage or {}
    return ReplayOutput(
        model=model,
        content=result.content,
        latency_ms=result.elapsed_ms,
        total_tokens=int(usage.get("total_tokens") or 0),
        tool_called=bool(result.tool_calls),
    )


def replay_trace(trace: dict, models: list[str], settings: AISettings) -> None:
    """重放单条 trace：先打印原始输出，再逐模型重放并排对比。"""
    messages = trace.get("messages_in") or []
    print(_SEP)
    print(f"trace_id: {trace.get('trace_id')}  page: {trace.get('page_key') or '-'}  "
          f"rating: {trace.get('rating') or '-'}")
    print(f"首问: {_short(_first_user_text(trace), 200)}")
    print(_SUBSEP)
    orig_usage = trace.get("usage") or {}
    print(f"[原始 · {trace.get('model') or '-'}] "
          f"latency={trace.get('latency_ms', 0)}ms "
          f"tokens={orig_usage.get('total_tokens', '-')}")
    print((trace.get("raw_output") or "（原始输出为空）").strip())

    for model in models:
        print(_SUBSEP)
        out = _replay_one(list(messages), model, settings)
        if out.error:
            print(f"[重放 · {model}] 失败: {out.error}")
            continue
        print(f"[重放 · {model}] latency={out.latency_ms}ms "
              f"tokens={out.total_tokens} tool_called={out.tool_called}")
        print((out.content or "（重放输出为空）").strip())
    print(_SEP)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI trace 重放 / 双模型对比")
    parser.add_argument("--list", action="store_true", help="列出最近 trace 概览")
    parser.add_argument("--trace", default=None, help="按 trace_id 重放某条")
    parser.add_argument("--file", default=None, help="重放整个 trace jsonl 文件")
    parser.add_argument(
        "--models",
        default=None,
        help="重放模型清单（逗号分隔）；缺省用配置默认模型",
    )
    parser.add_argument(
        "--only-down", action="store_true", help="仅处理 rating=down（差评）的 trace"
    )
    parser.add_argument("--limit", type=int, default=30, help="--list / --file 上限")
    args = parser.parse_args(argv)

    settings = AISettings.load()
    models = (
        [m.strip() for m in args.models.split(",") if m.strip()]
        if args.models
        else [settings.effective_model]
    )

    if args.list:
        list_recent(args.limit, only_down=args.only_down)
        return 0

    if args.trace:
        trace = find_trace(args.trace)
        if not trace:
            print(f"未找到 trace_id={args.trace}")
            return 1
        replay_trace(trace, models, settings)
        return 0

    if args.file:
        traces = load_traces(args.file)
        if args.only_down:
            traces = [t for t in traces if t.get("rating") == "down"]
        traces = traces[: args.limit]
        if not traces:
            print("该文件无可重放 trace（或全部被 --only-down 过滤）")
            return 1
        for trace in traces:
            replay_trace(trace, models, settings)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""客户端遥测（AI_Assistant_MD §3 / Phase 5b 客户端侧）。

只做客户端侧：脱敏采集 → 本地 jsonl 缓冲 → 后台 QThread 批量 POST 上报；
服务器侧（POST /v1/telemetry 落库）不在本仓库范围。

隐私第一：
  - telemetry_enabled=False 时彻底不采集、不写盘、不上报（record 直接 return）；
  - 全程经 mask_sensitive 二次脱敏，不上报原始日志/串口数据/API Key/序列号；
  - endpoint 为空时只本地缓冲、不联网（供本机自查或后续补上报）。
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from core.ai.config import AISettings
from core.ai.prompt_manager import mask_sensitive
from ui.resource_path import get_user_data_dir
from log_config import get_logger

logger = get_logger(__name__)

_TELEMETRY_SUBDIR = "telemetry"
_BUFFER_FILENAME = "buffer.jsonl"
_MAX_BUFFER_LINES = 2000


def _telemetry_dir() -> str:
    return get_user_data_dir("ai", _TELEMETRY_SUBDIR)


def _buffer_path() -> str:
    return os.path.join(_telemetry_dir(), _BUFFER_FILENAME)


def ensure_client_id(settings: AISettings) -> str:
    """取/生成匿名机器标识；首启生成 UUID 并持久化到配置。"""
    cid = (settings.telemetry_client_id or "").strip()
    if cid:
        return cid
    cid = uuid.uuid4().hex
    settings.telemetry_client_id = cid
    try:
        settings.save()
    except Exception:  # noqa: BLE001 - 落盘失败不影响采集
        logger.error("保存 telemetry_client_id 失败", exc_info=True)
    return cid


@dataclass
class TelemetryEvent:
    """单条遥测事件；字段已是脱敏后的最小集（§3.2）。"""

    event_type: str
    page_key: str = ""
    payload: dict = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def to_record(self, client_id: str) -> dict:
        return {
            "event_type": self.event_type,
            "page_key": self.page_key or "",
            "payload": _mask_payload(self.payload),
            "ts": self.ts,
            "client_id": client_id,
        }


def _mask_payload(payload: dict) -> dict:
    """对 payload 内字符串值做二次脱敏。"""
    masked: dict = {}
    for key, val in (payload or {}).items():
        if isinstance(val, str):
            masked[key] = mask_sensitive(val)
        else:
            masked[key] = val
    return masked


def record(event: TelemetryEvent, settings: AISettings) -> None:
    """采集一条事件：脱敏后追加写本地 jsonl 缓冲（隐私开关关闭时静默）。"""
    if not settings.telemetry_enabled:
        return
    try:
        client_id = ensure_client_id(settings)
        line = json.dumps(event.to_record(client_id), ensure_ascii=False)
        path = _buffer_path()
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        _rotate_if_needed(path)
    except Exception:  # noqa: BLE001 - 采集失败绝不影响主流程
        logger.error("写入遥测缓冲失败", exc_info=True)


def _rotate_if_needed(path: str) -> None:
    """缓冲超过上限时只保留最新 _MAX_BUFFER_LINES 行，防无限增长。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return
    if len(lines) <= _MAX_BUFFER_LINES:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines[-_MAX_BUFFER_LINES:])
    except OSError:
        logger.error("滚动遥测缓冲失败", exc_info=True)


def _read_buffer() -> list[dict]:
    path = _buffer_path()
    if not os.path.isfile(path):
        return []
    records: list[dict] = []
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
        logger.error("读取遥测缓冲失败", exc_info=True)
    return records


def _rewrite_buffer(records: list[dict]) -> None:
    path = _buffer_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        logger.error("回写遥测缓冲失败", exc_info=True)


class _UploadWorker(QObject):
    """单次上报 worker：把缓冲里的一批 POST 出去，成功则从缓冲移除。"""

    done = Signal(int)
    failed = Signal(str)

    def __init__(self, endpoint: str, batch_size: int, timeout_s: float):
        super().__init__()
        self._endpoint = endpoint
        self._batch_size = max(1, int(batch_size))
        self._timeout_s = timeout_s

    def run(self) -> None:
        records = _read_buffer()
        if not records:
            self.done.emit(0)
            return
        batch = records[: self._batch_size]
        try:
            import httpx

            with httpx.Client(trust_env=False, timeout=self._timeout_s) as client:
                resp = client.post(self._endpoint, json={"events": batch})
                resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001 - 上报失败保留缓冲下次重试
            logger.warning("遥测上报失败，保留缓冲下次重试：%s", exc)
            self.failed.emit(str(exc))
            return
        _rewrite_buffer(records[len(batch):])
        self.done.emit(len(batch))


class TelemetryUploader(QObject):
    """后台批量上报器：按 flush_interval 定时把缓冲分批 POST。

    线程模型：QTimer 触发 → 起短命 QThread 跑一次 _UploadWorker → 清理。
    endpoint 为空或隐私开关关闭时不做任何网络动作。
    """

    def __init__(self, settings: AISettings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._thread: QThread | None = None
        self._worker: _UploadWorker | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.flush)

    def start(self) -> None:
        """启动定时上报（隐私开关关闭则不启动）。"""
        if not self._settings.telemetry_enabled:
            return
        interval_ms = max(10, int(self._settings.telemetry_flush_interval_s)) * 1000
        self._timer.start(interval_ms)
        logger.info("遥测上报器已启动，间隔 %ds", self._settings.telemetry_flush_interval_s)

    def stop(self) -> None:
        self._timer.stop()

    def flush(self) -> None:
        """触发一次批量上报（已有任务在跑/未配置 endpoint 则跳过）。"""
        if not self._settings.telemetry_enabled:
            return
        endpoint = self._settings.effective_telemetry_endpoint
        if not endpoint:
            return
        if self._thread is not None:
            return
        self._thread = QThread()
        self._worker = _UploadWorker(
            endpoint,
            self._settings.telemetry_batch_size,
            float(self._settings.timeout_seconds),
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.done.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup)
        self._thread.start()

    def _on_done(self, count: int) -> None:
        if count:
            logger.info("遥测上报成功 %d 条", count)

    def _on_failed(self, message: str) -> None:
        logger.debug("遥测上报本次失败：%s", message)

    def _cleanup(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None

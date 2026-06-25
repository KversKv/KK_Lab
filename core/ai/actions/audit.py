"""AuditLog：把所有动作执行（含拒绝/取消）写入 user_data/ai/audit.log（AIAssist_Architecture.md §10）。

每条审计是一行 JSON（JSONL），含时间戳 / 动作名 / 参数 / 风险等级 / 结果状态 /
消息。参数与结果经轻量脱敏（避免落盘明文 Key / 长串）。

落盘路径：get_user_data_dir("ai")/audit.log（开发态 user_data/ai/，打包后 %APPDATA%/KK_Lab/ai/）。
本模块纯逻辑，禁 import Qt。
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from typing import Any

from ui.resource_path import get_user_data_dir
from log_config import get_logger

logger = get_logger(__name__)

_AUDIT_FILENAME = "audit.log"

STATUS_EXECUTED = "executed"
STATUS_DENIED = "denied"
STATUS_CANCELLED = "cancelled"
STATUS_FAILED = "failed"

_MAX_VALUE_LEN = 500


def _audit_path() -> str:
    return os.path.join(get_user_data_dir("ai"), _AUDIT_FILENAME)


def _truncate(value: Any) -> Any:
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = str(value)
    if len(text) > _MAX_VALUE_LEN:
        return text[:_MAX_VALUE_LEN] + "...(truncated)"
    return value


class AuditLog:
    """线程安全的审计日志写入器（追加 JSONL）。"""

    def __init__(self, path: str | None = None) -> None:
        self._path = path or _audit_path()
        self._lock = threading.Lock()

    @property
    def path(self) -> str:
        return self._path

    def record(
        self,
        *,
        action: str,
        status: str,
        risk_level: str = "",
        arguments: dict[str, Any] | None = None,
        message: str = "",
    ) -> None:
        entry = {
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "status": status,
            "risk_level": risk_level,
            "arguments": _truncate(arguments or {}),
            "message": (message or "")[:_MAX_VALUE_LEN],
        }
        line = json.dumps(entry, ensure_ascii=False)
        try:
            with self._lock:
                os.makedirs(os.path.dirname(self._path), exist_ok=True)
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
        except OSError:
            logger.error("写入审计日志失败: %s", self._path, exc_info=True)


_audit_log: AuditLog | None = None
_init_lock = threading.Lock()


def get_audit_log() -> AuditLog:
    """进程级单例审计日志。"""
    global _audit_log
    with _init_lock:
        if _audit_log is None:
            _audit_log = AuditLog()
        return _audit_log

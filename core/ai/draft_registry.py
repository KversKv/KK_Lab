"""AI 草案注册表（AI_AssistFunction.md §5.6 P5）。

`AIService.generate_draft` 产出的草案（ConfigDraft / ScriptDraft）经 `draft_ready`
信号回灌 UI 预览的同时，由本注册表登记一个稳定 draft_id，供 AI 通过
`apply_test_config_draft(draft_id)` 动作在「预览确认」后落地。

约束：
  - 草案绝不自动应用，仅登记句柄；落地须经 ActionDispatcher 确认闭环；
  - payload 保留原始结构化对象（ConfigDraft / ScriptDraft dataclass 实例），
    由 apply 回调各自解释；
  - 本模块纯逻辑，禁 import Qt。
"""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Optional

from log_config import get_logger

logger = get_logger(__name__)

_MAX_DRAFTS = 50


class DraftRegistry:
    """草案句柄登记表（线程安全）。

    register(parsed) -> draft_id：把 ParsedResponse 登记为一个可引用句柄；
    get(draft_id) -> dict | None：取回草案原始信息（kind/payload/title/notes/created_at）；
    list() -> list[dict]：列出当前可用草案句柄摘要（供模型选择）。
    """

    def __init__(self, *, max_drafts: int = _MAX_DRAFTS) -> None:
        self._drafts: dict[str, dict[str, Any]] = {}
        self._counter = 0
        self._max_drafts = max_drafts
        self._lock = threading.Lock()

    def register(self, parsed: Any) -> Optional[str]:
        """登记一个草案，返回 draft_id；parsed 无有效 payload 时返回 None。"""
        if parsed is None:
            return None
        ok = getattr(parsed, "ok", False)
        payload = getattr(parsed, "payload", None)
        if not ok or payload is None:
            return None
        kind = getattr(parsed, "kind", "") or ""
        title = getattr(payload, "title", "") or ""
        notes = getattr(payload, "notes", "") or ""
        with self._lock:
            self._counter += 1
            draft_id = f"draft_{self._counter:03d}"
            self._drafts[draft_id] = {
                "draft_id": draft_id,
                "kind": kind,
                "payload": payload,
                "title": title,
                "notes": notes,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
            self._evict_if_needed()
        logger.debug("登记草案 %s（kind=%s, title=%s）", draft_id, kind, title)
        return draft_id

    def get(self, draft_id: str) -> Optional[dict[str, Any]]:
        if not draft_id:
            return None
        with self._lock:
            entry = self._drafts.get(draft_id)
            return dict(entry) if entry else None

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "draft_id": d["draft_id"],
                    "kind": d["kind"],
                    "title": d["title"],
                    "created_at": d["created_at"],
                }
                for d in self._drafts.values()
            ]

    def clear(self) -> None:
        with self._lock:
            self._drafts.clear()
            self._counter = 0

    def _evict_if_needed(self) -> None:
        """超过上限时按 FIFO 淘汰最旧草案，避免内存无限增长。"""
        while len(self._drafts) > self._max_drafts:
            oldest = next(iter(self._drafts))
            self._drafts.pop(oldest, None)

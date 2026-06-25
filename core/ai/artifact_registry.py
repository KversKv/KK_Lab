"""AI 产物注册表（AIAssist_ActionCatalog.md §5.7 P6）。

P6 数据导出与产物通道的统一句柄登记表：save_scope_screenshot /
export_datalog_csv / export_waveform_csv 等导出动作落盘后，把产物路径与元信息
登记为一个稳定 artifact_id，供 AI 通过 get_artifact_list 动作回看本次会话产出的
所有文件（截图 / CSV 等）。

约束：
  - 仅登记句柄与元信息（路径/字节数/通道/时间窗），不持有文件内容；
  - 二进制产物只回灌「路径 + 元信息」，不塞进对话上下文（防撑爆 token）；
  - 本模块纯逻辑，禁 import Qt。
"""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Optional

from log_config import get_logger

logger = get_logger(__name__)

_MAX_ARTIFACTS = 200


class ArtifactRegistry:
    """产物句柄登记表（线程安全）。

    register(kind, path, ...) -> artifact_id：登记一个落盘产物，返回可引用句柄；
    list() -> list[dict]：列出当前已登记产物（供 get_artifact_list 回灌模型）；
    get(artifact_id) -> dict | None：取回单个产物元信息。
    """

    def __init__(self, *, max_artifacts: int = _MAX_ARTIFACTS) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self._counter = 0
        self._max_artifacts = max_artifacts
        self._lock = threading.Lock()

    def register(
        self,
        kind: str,
        path: str,
        *,
        session_id: str = "",
        label: str = "",
        bytes: int = 0,
        meta: dict | None = None,
    ) -> Optional[str]:
        """登记一个产物，返回 artifact_id；kind/path 为空时返回 None。"""
        if not kind or not path:
            return None
        with self._lock:
            self._counter += 1
            artifact_id = f"artifact_{self._counter:03d}"
            self._items[artifact_id] = {
                "artifact_id": artifact_id,
                "kind": kind,
                "path": path,
                "session_id": session_id,
                "label": label,
                "bytes": int(bytes),
                "meta": dict(meta or {}),
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
            self._evict_if_needed()
        logger.debug(
            "登记产物 %s（kind=%s, path=%s, bytes=%d）",
            artifact_id, kind, path, bytes,
        )
        return artifact_id

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._items.values()]

    def get(self, artifact_id: str) -> Optional[dict[str, Any]]:
        if not artifact_id:
            return None
        with self._lock:
            item = self._items.get(artifact_id)
            return dict(item) if item else None

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._counter = 0

    def _evict_if_needed(self) -> None:
        """超过上限时按 FIFO 淘汰最旧产物，避免内存无限增长。"""
        while len(self._items) > self._max_artifacts:
            oldest = next(iter(self._items))
            self._items.pop(oldest, None)

"""AI 面板 UI 状态持久化：user_data/ai/ui_state.json。

仅保存 UI 偏好（是否打开、宽度），与 config.json（功能配置）分离。
宽度范围钳制 300~600，默认 360。
"""
from __future__ import annotations

import json
import os

from ui.resource_path import get_user_data_dir
from log_config import get_logger

logger = get_logger(__name__)

_FILENAME = "ui_state.json"
_MIN_WIDTH = 300
_MAX_WIDTH = 600
_DEFAULT_WIDTH = 360


def _state_path() -> str:
    return os.path.join(get_user_data_dir("ai"), _FILENAME)


def clamp_width(width: int) -> int:
    try:
        value = int(width)
    except (TypeError, ValueError):
        return _DEFAULT_WIDTH
    return max(_MIN_WIDTH, min(_MAX_WIDTH, value))


def load_panel_state() -> tuple[bool, int]:
    """返回 (panel_open, panel_width)。读取失败回退默认。"""
    path = _state_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            return bool(data.get("panel_open", False)), clamp_width(
                data.get("panel_width", _DEFAULT_WIDTH)
            )
        except (OSError, json.JSONDecodeError):
            logger.error("读取 AI 面板状态失败: %s", path, exc_info=True)
    return False, _DEFAULT_WIDTH


def save_panel_state(panel_open: bool, panel_width: int) -> None:
    path = _state_path()
    payload = {"panel_open": bool(panel_open), "panel_width": clamp_width(panel_width)}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except OSError:
        logger.error("写入 AI 面板状态失败: %s", path, exc_info=True)

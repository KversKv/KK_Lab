# -*- coding: utf-8 -*-
"""文件对话框目录 / 偏好记忆（叶子模块，纯 stdlib + log_config / resource_path）。

按操作类型（Export / Import / Save 等）记忆上一次使用的目录与少量偏好值
（如导出格式），落盘到用户 JSON 同目录的 file_dialog_dirs.json，重启软件后
仍生效；记忆的目录已不存在时回退调用方传入的默认位置。导入方向与
serial_style 同层（叶子），mixins / serial_log_panel / dialogs /
independent_window 均可直接 import。
"""

import json
import os
import sys

from log_config import get_logger
from resource_path import get_resource_base

logger = get_logger(__name__)

# 与 PersistenceMixin._SC_APP_NAMESPACE / _sc_user_config_dir 的目录规则保持一致
_NAMESPACE = "SerialCom"
_FILENAME = "file_dialog_dirs.json"

_dirs: dict = {}
_loaded = False


def _storage_path() -> str:
    if getattr(sys, "frozen", False):
        base = os.environ.get("APPDATA") or os.path.join(
            os.path.expanduser("~"), "AppData", "Roaming"
        )
        root = os.path.join(base, _NAMESPACE)
    else:
        root = os.path.join(get_resource_base(), "user_data", _NAMESPACE)
    try:
        os.makedirs(root, exist_ok=True)
    except OSError:
        pass
    return os.path.join(root, _FILENAME)


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        with open(_storage_path(), "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return
    if isinstance(raw, dict):
        _dirs.update(
            {str(k): str(v) for k, v in raw.items() if isinstance(v, str) and v}
        )


def last_dir(key: str, default: str = "") -> str:
    """返回 key 上一次使用的目录；目录已不存在（或无记忆）时回退 default。"""
    _ensure_loaded()
    d = _dirs.get(key, "")
    if d and os.path.isdir(d):
        return d
    return default


def initial_save_path(key: str, default_name: str) -> str:
    """Save 类对话框初始路径：记忆目录 + 默认文件名；无有效记忆时仅用默认文件名。"""
    d = last_dir(key)
    return os.path.join(d, default_name) if d else default_name


def _persist() -> None:
    try:
        with open(_storage_path(), "w", encoding="utf-8") as f:
            json.dump(_dirs, f, ensure_ascii=False, indent=2)
    except OSError:
        logger.warning("Failed to persist file dialog dirs", exc_info=True)


def remember_dir(key: str, directory: str) -> None:
    """记忆目录并立即落盘（尽力而为，失败不影响对话框流程）。"""
    if not key or not directory:
        return
    _ensure_loaded()
    directory = os.path.abspath(directory)
    if _dirs.get(key) == directory:
        return
    _dirs[key] = directory
    _persist()


def remember_path(key: str, path: str) -> None:
    """记忆所选文件所在目录。"""
    if path:
        remember_dir(key, os.path.dirname(os.path.abspath(path)))


def last_value(key: str, default: str = "") -> str:
    """返回 key 上一次记忆的普通偏好值（不做目录校验）；无记忆时回退 default。"""
    _ensure_loaded()
    return _dirs.get(key) or default


def remember_value(key: str, value: str) -> None:
    """记忆普通偏好值（如导出格式）并立即落盘。"""
    if not key or not value:
        return
    _ensure_loaded()
    if _dirs.get(key) == value:
        return
    _dirs[key] = value
    _persist()

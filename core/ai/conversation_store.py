"""会话历史持久化：user_data/ai/history/<session_key>.json（按页面/任务隔离）。

仅保存对话正文（role=user/assistant 的 content），用于多轮上下文恢复；
不保存 system 段、tool 调用、推理过程等。条数上限作为安全兜底，实际裁剪交给 token 预算。
与 config.json（功能配置）/ ui_state.json（UI 偏好）分离。

向后兼容：旧版单文件 user_data/ai/history.json 首次访问时迁移到 history/_default.json。
"""
from __future__ import annotations

import json
import os
import re

from ui.resource_path import get_user_data_dir
from log_config import get_logger

logger = get_logger(__name__)

_LEGACY_FILENAME = "history.json"
_HISTORY_SUBDIR = "history"
_DEFAULT_SESSION = "_default"
_MAX_MESSAGES = 40

_SAFE_KEY = re.compile(r"[^A-Za-z0-9_\-]")


def _sanitize_session_key(session_key: str | None) -> str:
    key = (session_key or "").strip() or _DEFAULT_SESSION
    return _SAFE_KEY.sub("_", key)


def _history_dir() -> str:
    return get_user_data_dir("ai", _HISTORY_SUBDIR)


def _legacy_path() -> str:
    return os.path.join(get_user_data_dir("ai"), _LEGACY_FILENAME)


def _session_path(session_key: str) -> str:
    return os.path.join(_history_dir(), f"{_sanitize_session_key(session_key)}.json")


def _migrate_legacy_if_needed() -> None:
    """旧单文件 history.json 存在且未迁移时，挪到 history/_default.json。"""
    legacy = _legacy_path()
    if not os.path.isfile(legacy):
        return
    default_path = _session_path(_DEFAULT_SESSION)
    if os.path.isfile(default_path):
        return
    try:
        with open(legacy, "r", encoding="utf-8") as f:
            data = f.read()
        with open(default_path, "w", encoding="utf-8") as f:
            f.write(data)
        os.remove(legacy)
        logger.info("已迁移旧会话历史 %s -> %s", legacy, default_path)
    except OSError:
        logger.error("迁移旧会话历史失败: %s", legacy, exc_info=True)


def _clean_messages(messages) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for item in messages or []:
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content:
            result.append({"role": role, "content": content})
    return result


def load_history(session_key: str = _DEFAULT_SESSION) -> list[dict[str, str]]:
    """读取指定会话的对话历史；失败回退空列表。"""
    _migrate_legacy_if_needed()
    path = _session_path(session_key)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        return _clean_messages(data.get("messages", []))[-_MAX_MESSAGES:]
    except (OSError, json.JSONDecodeError):
        logger.error("读取 AI 会话历史失败: %s", path, exc_info=True)
        return []


def save_history(
    messages: list[dict[str, str]], session_key: str = _DEFAULT_SESSION
) -> None:
    """把指定会话历史写回（仅 user/assistant 正文，超限截断旧消息）。"""
    path = _session_path(session_key)
    payload = {"messages": _clean_messages(messages)[-_MAX_MESSAGES:]}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except OSError:
        logger.error("写入 AI 会话历史失败: %s", path, exc_info=True)


def clear_history(session_key: str = _DEFAULT_SESSION) -> None:
    """清空指定会话的历史文件。"""
    path = _session_path(session_key)
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            logger.error("删除 AI 会话历史失败: %s", path, exc_info=True)


def list_sessions() -> list[str]:
    """列出已存在的会话键（按文件名去后缀）。"""
    _migrate_legacy_if_needed()
    directory = _history_dir()
    if not os.path.isdir(directory):
        return []
    sessions: list[str] = []
    try:
        for name in sorted(os.listdir(directory)):
            if name.lower().endswith(".json"):
                sessions.append(name[:-5])
    except OSError:
        logger.error("列出 AI 会话失败: %s", directory, exc_info=True)
    return sessions


def new_session(page_key: str | None) -> str:
    """为页面派生一个任务级会话键（带时间戳后缀，避免覆盖既有会话）。"""
    import time

    base = _sanitize_session_key(page_key)
    return f"{base}-{int(time.time())}"

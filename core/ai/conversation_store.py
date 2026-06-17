"""会话历史持久化：user_data/ai/history.json。

仅保存对话正文（role=user/assistant 的 content），用于多轮上下文恢复；
不保存 system 段、tool 调用、推理过程等。条数上限保护，超出截断旧消息。
与 config.json（功能配置）/ ui_state.json（UI 偏好）分离。
"""
from __future__ import annotations

import json
import os

from ui.resource_path import get_user_data_dir
from log_config import get_logger

logger = get_logger(__name__)

_FILENAME = "history.json"
_MAX_MESSAGES = 40


def _history_path() -> str:
    return os.path.join(get_user_data_dir("ai"), _FILENAME)


def load_history() -> list[dict[str, str]]:
    """读取持久化的对话历史；失败回退空列表。"""
    path = _history_path()
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        messages = data.get("messages", [])
        result: list[dict[str, str]] = []
        for item in messages:
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content:
                result.append({"role": role, "content": content})
        return result[-_MAX_MESSAGES:]
    except (OSError, json.JSONDecodeError):
        logger.error("读取 AI 会话历史失败: %s", path, exc_info=True)
        return []


def save_history(messages: list[dict[str, str]]) -> None:
    """把对话历史写回 history.json（仅 user/assistant 正文，超限截断旧消息）。"""
    path = _history_path()
    clean: list[dict[str, str]] = []
    for item in messages or []:
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content:
            clean.append({"role": role, "content": content})
    payload = {"messages": clean[-_MAX_MESSAGES:]}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except OSError:
        logger.error("写入 AI 会话历史失败: %s", path, exc_info=True)


def clear_history() -> None:
    """清空持久化的会话历史文件。"""
    path = _history_path()
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            logger.error("删除 AI 会话历史失败: %s", path, exc_info=True)

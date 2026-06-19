"""纠偏片段库（AI_Assistant_MD §2.5 / Phase 4）。

把散落的硬编码纠偏文案（如原 _FORCE_TOOL_NUDGE）系统化为可分发的片段库：
  - 随包只读：resources/ai/nudges.json；
  - 每条 {id, when, text}，按触发条件 when 命中后注入对应 text；
  - 新增坑只需加一条 json，无需改代码。

触发条件 when 约定（最小集）：
  - "no_tool_call_but_claims_done"：agent 未调用工具却声称已执行时触发；
  - "page=<page_key>"：当前页面键等于指定值时触发（常驻提示）。
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

from ui.resource_path import get_resource_base, get_user_data_dir
from log_config import get_logger

logger = get_logger(__name__)

_NUDGES_REL = ("resources", "ai", "nudges.json")
_LOCAL_NUDGES_NAME = "nudges.local.json"

_WHEN_FORCE_TOOL = "no_tool_call_but_claims_done"
_WHEN_PAGE_PREFIX = "page="


def _nudges_path() -> str:
    return os.path.join(get_resource_base(), *_NUDGES_REL)


def local_nudges_path() -> str:
    """本机沉淀的片段库覆盖文件（可写，frozen 下也生效）。"""
    return os.path.join(get_user_data_dir("ai"), _LOCAL_NUDGES_NAME)


def _parse_nudges(data: dict) -> list[dict[str, str]]:
    items = data.get("nudges") or []
    result: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        nid = str(item.get("id") or "").strip()
        when = str(item.get("when") or "").strip()
        text = str(item.get("text") or "").strip()
        if nid and when and text:
            entry = {"id": nid, "when": when, "text": text}
            src = item.get("_src")
            if isinstance(src, str) and src:
                entry["_src"] = src
            result.append(entry)
    return result


def _read_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except (OSError, json.JSONDecodeError):
        logger.error("读取纠偏片段库失败: %s", path, exc_info=True)
        return {}


@lru_cache(maxsize=1)
def _load_nudges() -> tuple[dict[str, str], ...]:
    """读取随包 + 本机沉淀片段库（缓存）；本机条目按 id 覆盖随包同 id。"""
    merged: dict[str, dict[str, str]] = {}
    for item in _parse_nudges(_read_json(_nudges_path())):
        merged[item["id"]] = item
    for item in _parse_nudges(_read_json(local_nudges_path())):
        merged[item["id"]] = item
    return tuple(merged.values())


def reload_nudges() -> None:
    """清缓存，用于本机沉淀新片段后立即生效（Phase 5a）。"""
    _load_nudges.cache_clear()


def get_nudge(nudge_id: str) -> str:
    """按 id 取片段文本；不存在回退空串。"""
    for item in _load_nudges():
        if item["id"] == nudge_id:
            return item["text"]
    return ""


def force_tool_nudge() -> str:
    """取 force_tool 片段（替代原硬编码 _FORCE_TOOL_NUDGE）。"""
    for item in _load_nudges():
        if item["when"] == _WHEN_FORCE_TOOL:
            return item["text"]
    return ""


def page_nudges(page_key: str | None) -> list[dict[str, str]]:
    """取当前页面命中的常驻纠偏片段（when=page=<page_key>）。"""
    if not page_key:
        return []
    target = f"{_WHEN_PAGE_PREFIX}{page_key}"
    return [item for item in _load_nudges() if item["when"] == target]

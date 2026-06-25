"""KK Lab AI 记忆受控动作 handlers（AIAssist_KKLabAIMemoryArchivePlan.md Phase 2）。

动作：
  - archive_kk_lab_memory : medium，把草稿写入当前页面记忆文件（默认本机私有层）；
  - list_kk_lab_memory    : low，列出当前页面 + _shared 已有条目索引；
  - search_kk_lab_memory  : low，在当前页面 + _shared 中搜索关键字。

写入路径白名单：只能写 docs/kk_lab_ai_memory/<page_key>/ 或
user_data/ai/kk_lab_ai_memory/<page_key>/；page_key 必须在白名单内。
项目级 docs 写入需 UI 二次确认（由 dispatcher 确认回调保证）。

本模块禁 import Qt。
"""
from __future__ import annotations

from typing import Any

from core.ai.actions.handlers.deps import ActionDeps
from core.ai.actions.registry import CATEGORY_QUERY, ActionSpec
from core.ai import kk_lab_memory
from log_config import get_logger

logger = get_logger(__name__)

_ARCHIVE_SCHEMA = {
    "type": "object",
    "properties": {
        "draft_kind": {
            "type": "string",
            "enum": list(kk_lab_memory.DRAFT_KINDS),
            "description": "草稿类型：kk_memory/kk_lesson/kk_test_item/kk_test_case/kk_quick_action。",
        },
        "title": {"type": "string", "description": "条目标题。"},
        "fields": {
            "type": "object",
            "description": "条目字段键值对，键为字段名（页面/类型/现象/处理办法 等），值为字符串。",
        },
        "target": {
            "type": "string",
            "enum": [kk_lab_memory.TARGET_LOCAL, kk_lab_memory.TARGET_PROJECT],
            "description": "写入目标：local 本机私有层（默认）；project 项目级 docs（需确认）。",
        },
    },
    "required": ["draft_kind", "title", "fields"],
}

_LIST_SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {
            "type": "string",
            "enum": list(kk_lab_memory.KINDS),
            "description": "只列指定类型；不传则列全部 5 类。",
        },
    },
}

_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "keyword": {"type": "string", "description": "搜索关键字（不区分大小写）。"},
        "kind": {
            "type": "string",
            "enum": list(kk_lab_memory.KINDS),
            "description": "只搜指定类型；不传则搜全部 5 类。",
        },
    },
    "required": ["keyword"],
}

SPECS: list[ActionSpec] = [
    ActionSpec(
        name="archive_kk_lab_memory",
        description=(
            "把当前对话或选中文本归档为 KK Lab AI 记忆条目，写入当前页面对应文件。"
            "默认写本机私有层（local）；写项目级 docs 需用户确认。"
            "page_key 自动取当前页面。"
        ),
        parameters_schema=_ARCHIVE_SCHEMA,
        risk_level="medium",
        require_confirmation=True,
        category=CATEGORY_QUERY,
    ),
    ActionSpec(
        name="list_kk_lab_memory",
        description="列出当前页面 + _shared 已有的 KK Lab AI 记忆条目索引。",
        parameters_schema=_LIST_SCHEMA,
        risk_level="low",
        category=CATEGORY_QUERY,
    ),
    ActionSpec(
        name="search_kk_lab_memory",
        description="在当前页面 + _shared 的 KK Lab AI 记忆中搜索关键字。",
        parameters_schema=_SEARCH_SCHEMA,
        risk_level="low",
        category=CATEGORY_QUERY,
    ),
]


def _resolve_page_key(deps: ActionDeps) -> str:
    if deps.page_key_getter is not None:
        try:
            return deps.page_key_getter() or ""
        except Exception:  # noqa: BLE001
            logger.error("page_key_getter 调用异常", exc_info=True)
    return ""


def _fields_to_list(fields: dict[str, Any]) -> list[tuple[str, str]]:
    """把 dict 字段转为 [(label, value)] 列表，保持插入顺序。"""
    result: list[tuple[str, str]] = []
    for key, value in (fields or {}).items():
        result.append((str(key), str(value)))
    return result


def build_handlers(deps: ActionDeps) -> dict[str, Any]:
    def archive_kk_lab_memory(args: dict) -> dict:
        page_key = _resolve_page_key(deps)
        if not kk_lab_memory.is_valid_page_key(page_key):
            return {
                "ok": False,
                "_message": f"当前页面键 '{page_key}' 不在白名单，无法归档。",
            }
        draft_kind = str(args.get("draft_kind") or "").strip()
        if draft_kind not in kk_lab_memory.DRAFT_KINDS:
            return {"ok": False, "_message": f"非法 draft_kind：{draft_kind}"}
        title = str(args.get("title") or "").strip()
        if not title:
            return {"ok": False, "_message": "title 不能为空。"}
        fields = args.get("fields") or {}
        if not isinstance(fields, dict):
            return {"ok": False, "_message": "fields 必须是对象。"}
        target = str(args.get("target") or kk_lab_memory.TARGET_LOCAL).strip()
        if target not in (kk_lab_memory.TARGET_LOCAL, kk_lab_memory.TARGET_PROJECT):
            target = kk_lab_memory.TARGET_LOCAL

        file_kind = kk_lab_memory.draft_kind_to_file_kind(draft_kind)
        entry_id = kk_lab_memory.make_id(file_kind)
        field_list = _fields_to_list(fields)
        if not any(label == "页面" for label, _ in field_list):
            field_list.insert(0, ("页面", page_key))
        entry_text = kk_lab_memory.render_entry(file_kind, entry_id, title, field_list)

        existing = kk_lab_memory.read_entries(page_key, file_kind)
        dup = kk_lab_memory.find_duplicate(existing, title)
        if dup is not None:
            logger.info(
                "归档命中重复条目 %s（标题相似），将覆盖", dup.entry_id
            )
            entry_text = kk_lab_memory.render_entry(
                file_kind, dup.entry_id, title, field_list
            )

        ok, message = kk_lab_memory.append_entry(
            page_key, file_kind, entry_text, target=target
        )
        if not ok:
            return {"ok": False, "_message": f"写入失败：{message}"}
        target_label = "项目级 docs" if target == kk_lab_memory.TARGET_PROJECT else "本机私有层"
        return {
            "ok": True,
            "entry_id": entry_id,
            "file_kind": file_kind,
            "page_key": page_key,
            "target": target,
            "_message": (
                f"已归档到{target_label}：{page_key}/{kk_lab_memory._FILE_NAME[file_kind]} "
                f"（{entry_id} {title}）"
            ),
        }

    def list_kk_lab_memory(args: dict) -> dict:
        page_key = _resolve_page_key(deps)
        if not kk_lab_memory.is_valid_page_key(page_key):
            return {
                "ok": False,
                "_message": f"当前页面键 '{page_key}' 不在白名单。",
                "entries": [],
            }
        kind = args.get("kind")
        if kind and kind not in kk_lab_memory.KINDS:
            return {"ok": False, "_message": f"非法 kind：{kind}"}
        entries = kk_lab_memory.list_entries(page_key, kind)
        return {
            "ok": True,
            "page_key": page_key,
            "count": len(entries),
            "entries": entries,
            "_message": f"当前页面 + _shared 共 {len(entries)} 条记忆条目。",
        }

    def search_kk_lab_memory(args: dict) -> dict:
        page_key = _resolve_page_key(deps)
        if not kk_lab_memory.is_valid_page_key(page_key):
            return {
                "ok": False,
                "_message": f"当前页面键 '{page_key}' 不在白名单。",
                "results": [],
            }
        keyword = str(args.get("keyword") or "").strip()
        if not keyword:
            return {"ok": False, "_message": "keyword 不能为空。"}
        kind = args.get("kind")
        kinds: tuple[str, ...] = (kind,) if kind and kind in kk_lab_memory.KINDS else kk_lab_memory.KINDS
        results = kk_lab_memory.search_entries(page_key, keyword, kinds=kinds)
        return {
            "ok": True,
            "page_key": page_key,
            "keyword": keyword,
            "count": len(results),
            "results": results,
            "_message": f"搜索到 {len(results)} 条匹配条目。",
        }

    return {
        "archive_kk_lab_memory": archive_kk_lab_memory,
        "list_kk_lab_memory": list_kk_lab_memory,
        "search_kk_lab_memory": search_kk_lab_memory,
    }

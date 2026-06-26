"""KK Lab AI 记忆体系：路径映射、白名单、读写、去重、摘要、草稿生成。

实现 AIAssist_KKLabAIMemoryArchivePlan.md Phase 2：
  - 页面键白名单与路径映射（项目级 docs/kk_lab_ai_memory/ + 本机私有层）；
  - 5 类文件（memory/lessons/test_items/test_cases/quick_actions）的读写与条目解析；
  - 写入前 mask_sensitive 脱敏 + 按 entry_id 去重覆盖；
  - 摘要读取（当前页面 memory.md + lessons.md + _shared/cross_page_lessons.md），
    按 token 预算裁剪，供 PromptManager 注入；
  - 快捷指令加载（quick_actions.md + quick_actions.local.md，status=active）；
  - KKLabMemoryCurator：把一轮对话整理为 5 类草稿（AI 优先，失败降级规则）。

红线：禁 print；禁裸 except；写入路径白名单；项目级写入需 UI 二次确认（由调用方保证）。
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field

from core.ai import context_budget
from core.ai.config import AISettings
from core.ai.newapi_client import AIClientError, NewAPIClient
from core.ai.prompt_manager import mask_sensitive
from ui.resource_path import get_resource_base, get_user_data_dir
from log_config import get_logger

logger = get_logger(__name__)

# ---- 文件类型常量 ----------------------------------------------------------

KIND_MEMORY = "memory"
KIND_LESSONS = "lessons"
KIND_TEST_ITEMS = "test_items"
KIND_TEST_CASES = "test_cases"
KIND_QUICK_ACTIONS = "quick_actions"

KINDS: tuple[str, ...] = (
    KIND_MEMORY,
    KIND_LESSONS,
    KIND_TEST_ITEMS,
    KIND_TEST_CASES,
    KIND_QUICK_ACTIONS,
)

_ID_PREFIX: dict[str, str] = {
    KIND_MEMORY: "M",
    KIND_LESSONS: "L",
    KIND_TEST_ITEMS: "T",
    KIND_TEST_CASES: "TC",
    KIND_QUICK_ACTIONS: "QA",
}

_FILE_NAME: dict[str, str] = {
    KIND_MEMORY: "memory.md",
    KIND_LESSONS: "lessons.md",
    KIND_TEST_ITEMS: "test_items.md",
    KIND_TEST_CASES: "test_cases.md",
    KIND_QUICK_ACTIONS: "quick_actions.md",
}

# 页面键白名单（来源：conventions.md §2，唯一来源 MainWindow._get_current_help_key）
_PAGE_KEYS: frozenset[str] = frozenset({
    "power_analyser",
    "datalog",
    "oscilloscope",
    "thermal_chamber",
    "kk_serials",
    "collection",
    "orchestrator",
    "vmin_hunter",
    "consumption_test",
    "pmu_dcdc_efficiency",
    "pmu_output_voltage",
    "pmu_is_gain",
    "pmu_oscp",
    "pmu_gpadc",
    "pmu_clk",
    "charger_config_traverse",
    "charger_status_register",
    "charger_iterm",
    "charger_regulation_voltage",
})

# 伞目录键（来源：conventions.md §2.1）。非页面键，不来自 _get_current_help_key，
# 用于承载跨页面的同一业务簇总记忆（如 PMU 整套常规测试），目录名小写 + 下划线，
# 可含一级 / 分隔。读写路径映射、白名单校验与页面键一致。
_UMBRELLA_KEYS: frozenset[str] = frozenset({
    "automation/pmu_test",
    "automation/charger_test",
    "instrument/power_analyser",
})

# 合法目录键 = 页面键 + 伞目录键。
PAGE_KEYS: frozenset[str] = _PAGE_KEYS | _UMBRELLA_KEYS

# 页面键 → 记忆目录相对路径映射（仅用于物理归类，不影响 page_key 本身）。
# page_key 对外保持不变（仍是 UI 动作命名空间 / AI 裁剪 / profiles 的键），
# 仅记忆目录在磁盘上按导航栏 4 大组（INSTRUMENTS / AUTOMATION / TOOLS /
# ORCHESTRATION）归入对应一级父目录下，使结构与左侧导航一一对应。
# 未登记的 page_key 默认目录名 == page_key。
_DIR_OVERRIDE: dict[str, str] = {
    # INSTRUMENTS 组
    "power_analyser": "instrument/power_analyser/power_analyser",
    "datalog": "instrument/power_analyser/datalog",
    "oscilloscope": "instrument/oscilloscope",
    "thermal_chamber": "instrument/thermal_chamber",
    # AUTOMATION 组 —— PMU 测试簇
    "pmu_dcdc_efficiency": "automation/pmu_test/pmu_dcdc_efficiency",
    "pmu_output_voltage": "automation/pmu_test/pmu_output_voltage",
    "pmu_is_gain": "automation/pmu_test/pmu_is_gain",
    "pmu_oscp": "automation/pmu_test/pmu_oscp",
    "pmu_gpadc": "automation/pmu_test/pmu_gpadc",
    "pmu_clk": "automation/pmu_test/pmu_clk",
    # AUTOMATION 组 —— Charger 测试簇
    "charger_config_traverse": "automation/charger_test/charger_config_traverse",
    "charger_status_register": "automation/charger_test/charger_status_register",
    "charger_iterm": "automation/charger_test/charger_iterm",
    "charger_regulation_voltage": "automation/charger_test/charger_regulation_voltage",
    # AUTOMATION 组 —— 其余自动化页面
    "consumption_test": "automation/consumption_test",
    "vmin_hunter": "automation/vmin_hunter",
    # TOOLS 组
    "kk_serials": "tools/kk_serials",
    "collection": "tools/collection",
    # ORCHESTRATION 组
    "orchestrator": "orchestration/orchestrator",
}


def _dir_rel(page_key: str) -> str:
    """page_key 对应的记忆目录相对路径（相对各 base）。"""
    return _DIR_OVERRIDE.get(page_key, page_key)

_PROJECT_DIR_NAME = "kk_lab_ai_memory"
_LOCAL_SUBDIR = ("ai", "kk_lab_ai_memory")
_SHARED_DIR = "_shared"
_CROSS_PAGE_LESSONS_FILE = "cross_page_lessons.md"
_PENDING_FILE = "pending.md"

TARGET_LOCAL = "local"
TARGET_PROJECT = "project"


# ---- 路径映射 --------------------------------------------------------------


def project_base() -> str:
    """项目级 docs/kk_lab_ai_memory/ 根目录。"""
    return os.path.join(get_resource_base(), "docs", _PROJECT_DIR_NAME)


def local_base() -> str:
    """本机私有 user_data/ai/kk_lab_ai_memory/ 根目录（自动创建）。"""
    return get_user_data_dir(*_LOCAL_SUBDIR)


def is_valid_page_key(page_key: str | None) -> bool:
    """page_key 是否在白名单内。"""
    return bool(page_key) and page_key in PAGE_KEYS


def project_dir(page_key: str) -> str | None:
    """项目级页面目录路径；非法 page_key 返回 None。"""
    if not is_valid_page_key(page_key):
        return None
    return os.path.join(project_base(), _dir_rel(page_key))


def local_dir(page_key: str) -> str | None:
    """本机私有页面目录路径；非法 page_key 返回 None。"""
    if not is_valid_page_key(page_key):
        return None
    return os.path.join(local_base(), _dir_rel(page_key))


def project_file(page_key: str, kind: str) -> str | None:
    """项目级文件路径，如 docs/kk_lab_ai_memory/kk_serials/lessons.md。"""
    directory = project_dir(page_key)
    if directory is None or kind not in _FILE_NAME:
        return None
    return os.path.join(directory, _FILE_NAME[kind])


def local_file(page_key: str, kind: str) -> str | None:
    """本机私有文件路径，如 user_data/ai/kk_lab_ai_memory/kk_serials/lessons.local.md。"""
    directory = local_dir(page_key)
    if directory is None or kind not in _FILE_NAME:
        return None
    name = _FILE_NAME[kind]
    if name.endswith(".md"):
        name = name[:-3] + ".local.md"
    return os.path.join(directory, name)


def shared_file(name: str) -> str:
    """_shared 目录下文件路径（项目级）。"""
    return os.path.join(project_base(), _SHARED_DIR, name)


def cross_page_lessons_path() -> str:
    return shared_file(_CROSS_PAGE_LESSONS_FILE)


def pending_path() -> str:
    """未知页面兜底写入路径（_shared/pending.md）。"""
    return shared_file(_PENDING_FILE)


# ---- 条目解析 --------------------------------------------------------------


@dataclass
class MemoryEntry:
    """一条 markdown 条目（## ID - title 起头）。"""

    entry_id: str
    title: str
    body: str = ""
    raw: str = ""
    source_file: str = ""

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "title": self.title,
            "body": self.body,
            "source_file": self.source_file,
        }


_ENTRY_HEADER_RE = re.compile(r"^##\s+([A-Z]+-\d{8}-\d{3,6})\s*-\s*(.*)$")


def parse_entries(text: str, source_file: str = "") -> list[MemoryEntry]:
    """解析 markdown 文本中的条目（## ID - title 起头）。

    非条目段落（如文件头部的标题、说明、模板注释）被忽略。
    """
    if not text:
        return []
    lines = text.splitlines()
    entries: list[MemoryEntry] = []
    current: MemoryEntry | None = None
    body_buf: list[str] = []

    def _flush() -> None:
        nonlocal current, body_buf
        if current is not None:
            current.body = "\n".join(body_buf).strip()
            current.raw = f"## {current.entry_id} - {current.title}\n" + "\n".join(body_buf)
            entries.append(current)
            current = None
            body_buf = []

    for line in lines:
        match = _ENTRY_HEADER_RE.match(line.strip())
        if match:
            _flush()
            current = MemoryEntry(
                entry_id=match.group(1).strip(),
                title=match.group(2).strip(),
                source_file=source_file,
            )
        elif current is not None:
            body_buf.append(line)
    _flush()
    return entries


def _read_text(path: str) -> str:
    if not path or not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        logger.error("读取 KK Lab 记忆文件失败: %s", path, exc_info=True)
        return ""


def read_file_text(page_key: str | None, kind: str, *, include_local: bool = True) -> str:
    """读取页面文件文本（项目级 + 本机级追加，以 \n\n 分隔）。"""
    parts: list[str] = []
    proj = project_file(page_key or "", kind) if page_key else None
    if proj:
        text = _read_text(proj)
        if text:
            parts.append(text)
    if include_local:
        loc = local_file(page_key or "", kind) if page_key else None
        if loc:
            text = _read_text(loc)
            if text:
                parts.append(text)
    return "\n\n".join(parts)


def read_entries(
    page_key: str | None, kind: str, *, include_local: bool = True
) -> list[MemoryEntry]:
    """读取并解析条目列表（项目级 + 本机级）。"""
    entries: list[MemoryEntry] = []
    proj = project_file(page_key or "", kind) if page_key else None
    if proj:
        entries.extend(parse_entries(_read_text(proj), proj))
    if include_local:
        loc = local_file(page_key or "", kind) if page_key else None
        if loc:
            entries.extend(parse_entries(_read_text(loc), loc))
    return entries


def read_shared_lessons() -> list[MemoryEntry]:
    """读取 _shared/cross_page_lessons.md 条目。"""
    path = cross_page_lessons_path()
    return parse_entries(_read_text(path), path)


# ---- ID 生成与渲染 ---------------------------------------------------------


def make_id(kind: str) -> str:
    """生成条目 ID：前缀-YYYYMMDD-HHMMSS。"""
    prefix = _ID_PREFIX.get(kind, "X")
    return f"{prefix}-{time.strftime('%Y%m%d-%H%M%S')}"


def render_entry(kind: str, entry_id: str, title: str, fields: list[tuple[str, str]]) -> str:
    """按模板渲染一条 markdown 条目。

    fields 为 [(label, value)] 列表，value 可多行；label 为空表示延续上一项。
    """
    lines = [f"## {entry_id} - {title}", ""]
    for label, value in fields:
        value = (value or "").strip()
        if not value:
            continue
        if "\n" in value:
            sub_lines = value.splitlines()
            lines.append(f"- {label}:")
            for sub in sub_lines:
                lines.append(f"  - {sub.strip()}")
        else:
            lines.append(f"- {label}: {value}")
    return "\n".join(lines)


# ---- 写入 ------------------------------------------------------------------


def _ensure_dir(path: str) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return True
    except OSError:
        logger.error("创建目录失败: %s", path, exc_info=True)
        return False


def _read_file_lines(path: str) -> list[str]:
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.readlines()
    except OSError:
        logger.error("读取文件失败: %s", path, exc_info=True)
        return []


def _write_file(path: str, text: str) -> bool:
    if not _ensure_dir(path):
        return False
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return True
    except OSError:
        logger.error("写入 KK Lab 记忆文件失败: %s", path, exc_info=True)
        return False


def append_entry(
    page_key: str | None,
    kind: str,
    entry_text: str,
    *,
    target: str = TARGET_LOCAL,
) -> tuple[bool, str]:
    """追加条目到目标文件（local 或 project）。

    写入前对 entry_text 执行 mask_sensitive 脱敏。
    去重：若同 entry_id 已存在则原地覆盖（按 ## ID 行匹配），否则追加到文件末尾。
    返回 (ok, message)。
    """
    if target == TARGET_PROJECT:
        path = project_file(page_key or "", kind)
    else:
        path = local_file(page_key or "", kind)
    if path is None:
        return False, f"非法 page_key 或 kind：page={page_key}, kind={kind}"

    entry_text = mask_sensitive(entry_text).strip()
    if not entry_text:
        return False, "条目内容为空"

    header_match = _ENTRY_HEADER_RE.match(entry_text.splitlines()[0] if entry_text else "")
    entry_id = header_match.group(1) if header_match else ""

    existing = _read_text(path)
    if existing and entry_id:
        entries = parse_entries(existing, path)
        for idx, ent in enumerate(entries):
            if ent.entry_id == entry_id:
                lines = existing.splitlines(keepends=True)
                start_line = _find_entry_line_index(lines, entry_id)
                end_line = _find_entry_end_index(lines, start_line, entry_id)
                new_block = entry_text + "\n\n"
                rebuilt = "".join(lines[:start_line]) + new_block + "".join(lines[end_line:])
                ok = _write_file(path, rebuilt)
                return ok, "已覆盖同 ID 条目" if ok else "写入失败"

    suffix = existing
    if suffix and not suffix.endswith("\n"):
        suffix += "\n"
    if suffix and not suffix.endswith("\n\n"):
        suffix += "\n"
    suffix += entry_text + "\n"
    ok = _write_file(path, suffix)
    return ok, "追加成功" if ok else "写入失败"


def _find_entry_line_index(lines: list[str], entry_id: str) -> int:
    target = f"## {entry_id}"
    for i, line in enumerate(lines):
        if line.startswith(target):
            return i
    return 0


def _find_entry_end_index(lines: list[str], start: int, entry_id: str) -> int:
    """返回条目结束后的下一行索引（到下一个 ## 或文件末尾）。"""
    for i in range(start + 1, len(lines)):
        if _ENTRY_HEADER_RE.match(lines[i].strip()):
            return i
    return len(lines)


def find_duplicate(
    entries: list[MemoryEntry], title: str, *, similarity_threshold: float = 0.85
) -> MemoryEntry | None:
    """查找高相似度重复条目（标题完全相同或相似度超阈值）。"""
    if not title:
        return None
    target = title.strip().lower()
    for ent in entries:
        ent_title = ent.title.strip().lower()
        if ent_title == target:
            return ent
        if _similarity(ent_title, target) >= similarity_threshold:
            return ent
    return None


def _similarity(a: str, b: str) -> float:
    """简单相似度：基于字符集 Jaccard 系数（避免引入额外依赖）。"""
    if not a or not b:
        return 0.0
    sa = set(a)
    sb = set(b)
    inter = sa & sb
    union = sa | sb
    return len(inter) / len(union) if union else 0.0


# ---- 摘要读取（供 PromptManager 注入） ------------------------------------


def read_summary(page_key: str | None, *, max_tokens: int = 1500) -> str:
    """读取当前页面 memory.md + lessons.md + _shared/cross_page_lessons.md 摘要。

    按 token 预算裁剪（保头尾、中段省略）。用于 PromptManager 注入 system 段。
    """
    if not page_key:
        return ""
    parts: list[str] = []

    memory_entries = read_entries(page_key, KIND_MEMORY)
    if memory_entries:
        parts.append(_entries_to_summary("页面长期记忆", memory_entries))

    lesson_entries = read_entries(page_key, KIND_LESSONS)
    shared_lessons = read_shared_lessons()
    if lesson_entries or shared_lessons:
        all_lessons = lesson_entries + shared_lessons
        parts.append(_entries_to_summary("经验与排障", all_lessons))

    if not parts:
        return ""

    raw = "\n\n".join(parts)
    return context_budget.clip_context_block(raw, max_tokens)


def _entries_to_summary(label: str, entries: list[MemoryEntry]) -> str:
    """把条目列表渲染为摘要文本（ID + 标题 + body 前 3 行）。"""
    lines = [f"[KK Lab AI 记忆·{label}]"]
    for ent in entries[-12:]:
        lines.append(f"- {ent.entry_id} {ent.title}")
        body_lines = [ln for ln in ent.body.splitlines() if ln.strip()][:3]
        for bl in body_lines:
            lines.append(f"    {bl.strip()}")
    return "\n".join(lines)


# ---- 快捷指令加载 ----------------------------------------------------------


def read_quick_action_templates(page_key: str | None) -> list[str]:
    """读取页面 quick_actions.md + quick_actions.local.md 中 status=active 的模板。

    返回模板文案列表（去重保序）。失败或无文件返回空列表。
    """
    if not page_key:
        return []
    entries = read_entries(page_key, KIND_QUICK_ACTIONS)
    templates: list[str] = []
    seen: set[str] = set()
    for ent in entries:
        status = _extract_field(ent.body, "状态")
        if status and status.strip().lower() not in ("active", ""):
            continue
        template = _extract_field(ent.body, "模板")
        if not template:
            continue
        template = template.strip()
        if template and template not in seen:
            seen.add(template)
            templates.append(template)
    return templates


_FIELD_RE = re.compile(r"^-\s*(.+?)\s*[:：]\s*(.*)$")


def _extract_field(body: str, field_name: str) -> str:
    """从条目 body 中提取单行字段值（- 字段名: 值）。"""
    if not body:
        return ""
    for line in body.splitlines():
        match = _FIELD_RE.match(line.strip())
        if match and match.group(1).strip() == field_name:
            return match.group(2).strip()
    return ""


_CONTINUATION_RE = re.compile(r"^\s+[-\d]")


def _extract_multiline_field(body: str, field_name: str) -> str:
    """提取字段值，包含后续缩进续行（- 子项 / 1. 编号 / 纯缩进文本）。"""
    if not body:
        return ""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        match = _FIELD_RE.match(line.strip())
        if not match or match.group(1).strip() != field_name:
            continue
        value = match.group(2).strip()
        buf: list[str] = []
        if value:
            buf.append(value)
        for j in range(i + 1, len(lines)):
            nxt = lines[j]
            if not nxt.strip():
                continue
            is_top_field = bool(_FIELD_RE.match(nxt)) and not nxt[:1].isspace()
            if is_top_field:
                break
            if _CONTINUATION_RE.match(nxt):
                buf.append(nxt.strip())
            elif value and not buf:
                break
            else:
                break
        return "\n".join(buf)
    return ""


# ---- 搜索与列表 ------------------------------------------------------------


def search_entries(
    page_key: str | None,
    keyword: str,
    *,
    kinds: tuple[str, ...] = KINDS,
    include_shared: bool = True,
) -> list[dict]:
    """在当前页面 + _shared 中搜索关键字，返回命中条目摘要列表。"""
    keyword = (keyword or "").strip().lower()
    if not keyword:
        return []
    results: list[dict] = []
    for kind in kinds:
        for ent in read_entries(page_key, kind):
            if _entry_matches(ent, keyword):
                results.append(_entry_to_search_result(ent, kind, page_key or ""))
    if include_shared:
        for ent in read_shared_lessons():
            if _entry_matches(ent, keyword):
                results.append(_entry_to_search_result(ent, KIND_LESSONS, "_shared"))
    return results


def _entry_matches(ent: MemoryEntry, keyword: str) -> bool:
    hay = (ent.title + "\n" + ent.body).lower()
    return keyword in hay


def _entry_to_search_result(ent: MemoryEntry, kind: str, page_key: str) -> dict:
    return {
        "entry_id": ent.entry_id,
        "title": ent.title,
        "kind": kind,
        "page": page_key,
        "source_file": ent.source_file,
        "snippet": (ent.body or "").splitlines()[0] if ent.body else "",
    }


def list_entries(
    page_key: str | None, kind: str | None = None, *, include_shared: bool = True
) -> list[dict]:
    """列出当前页面 + _shared 的条目索引。"""
    kinds: tuple[str, ...] = (kind,) if kind else KINDS
    results: list[dict] = []
    for k in kinds:
        for ent in read_entries(page_key, k):
            results.append(_entry_to_search_result(ent, k, page_key or ""))
    if include_shared and (kind is None or kind == KIND_LESSONS):
        for ent in read_shared_lessons():
            results.append(_entry_to_search_result(ent, KIND_LESSONS, "_shared"))
    return results


# ---- 草稿生成器 ------------------------------------------------------------


KIND_DRAFT_MEMORY = "kk_memory"
KIND_DRAFT_LESSON = "kk_lesson"
KIND_DRAFT_TEST_ITEM = "kk_test_item"
KIND_DRAFT_TEST_CASE = "kk_test_case"
KIND_DRAFT_QUICK_ACTION = "kk_quick_action"

DRAFT_KINDS: tuple[str, ...] = (
    KIND_DRAFT_MEMORY,
    KIND_DRAFT_LESSON,
    KIND_DRAFT_TEST_ITEM,
    KIND_DRAFT_TEST_CASE,
    KIND_DRAFT_QUICK_ACTION,
)

_DRAFT_TO_FILE_KIND: dict[str, str] = {
    KIND_DRAFT_MEMORY: KIND_MEMORY,
    KIND_DRAFT_LESSON: KIND_LESSONS,
    KIND_DRAFT_TEST_ITEM: KIND_TEST_ITEMS,
    KIND_DRAFT_TEST_CASE: KIND_TEST_CASES,
    KIND_DRAFT_QUICK_ACTION: KIND_QUICK_ACTIONS,
}

_DRAFT_KIND_LABELS: dict[str, str] = {
    KIND_DRAFT_MEMORY: "页面长期记忆",
    KIND_DRAFT_LESSON: "经验与排障",
    KIND_DRAFT_TEST_ITEM: "常用测试项",
    KIND_DRAFT_TEST_CASE: "测试用例",
    KIND_DRAFT_QUICK_ACTION: "快捷指令",
}


def draft_kind_to_file_kind(draft_kind: str) -> str:
    return _DRAFT_TO_FILE_KIND.get(draft_kind, KIND_LESSONS)


def draft_kind_label(draft_kind: str) -> str:
    return _DRAFT_KIND_LABELS.get(draft_kind, draft_kind)


_AI_INSTRUCTIONS: dict[str, str] = {
    KIND_DRAFT_MEMORY: (
        "你是 KK_Lab 页面记忆整理助手。基于给定的一轮对话，提炼一条页面长期记忆草稿，"
        "记录页面稳定约定、参数含义或常见上下文。"
        "只输出 JSON：{\"title\": \"简体中文标题\", \"summary\": \"一句话说明这条记忆解决什么问题\","
        "\"content\": \"内容要点，分号分隔\", \"conditions\": \"适用条件\", \"stability\": \"stable 或 tentative\"}。"
    ),
    KIND_DRAFT_LESSON: (
        "你是 KK_Lab 经验沉淀助手。基于给定的一轮对话，提炼一条踩坑/排障/参数经验条目。"
        "只输出 JSON：{\"title\": \"问题或经验标题\", \"phenomenon\": \"现象\", \"cause\": \"原因\","
        "\"solution\": \"处理办法\", \"verification\": \"验证方式\", \"risk\": \"low 或 medium 或 high\","
        "\"lesson_type\": \"坑点 或 排障 或 参数经验 或 UI 操作 或 仪器行为\"}。"
    ),
    KIND_DRAFT_TEST_ITEM: (
        "你是 KK_Lab 测试项整理助手。基于给定的一轮对话，提炼一条常用测试项。"
        "只输出 JSON：{\"title\": \"测试项名称\", \"goal\": \"验证什么\", \"preconditions\": \"前置条件\","
        "\"params\": \"参数\", \"steps\": \"步骤\", \"expected\": \"期望结果\", \"scope\": \"适用范围\"}。"
    ),
    KIND_DRAFT_TEST_CASE: (
        "你是 KK_Lab 测试用例整理助手。基于给定的一轮对话，提炼一条结构化测试用例。"
        "只输出 JSON：{\"title\": \"用例名称\", \"case_type\": \"smoke 或 regression 或 manual 或 instrument_required\","
        "\"input\": \"输入\", \"steps\": \"执行步骤\", \"expected\": \"期望行为\", \"pass_criteria\": \"通过标准\","
        "\"fail_debug\": \"失败排查\", \"automation\": \"none 或 partial 或 full\"}。"
    ),
    KIND_DRAFT_QUICK_ACTION: (
        "你是 KK_Lab 快捷指令整理助手。把用户刚发的有效指令整理成可复用模板，"
        "数值参数替换成 {占位符}（如通道用 {ch}、电压用 {v}）。"
        "只输出 JSON：{\"title\": \"分组名称\", \"template\": \"简体中文模板\","
        "\"placeholders\": \"占位符说明，如 ch:通道号; v:电压值V\", \"condition\": \"适用条件\","
        "\"expectation\": \"执行预期\", \"status\": \"active 或 draft\"}。"
    ),
}


_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])(-?\d+(?:\.\d+)?)")


def _now_src(via: str) -> str:
    return f"{via} @ {time.strftime('%Y-%m-%d %H:%M:%S')}"


def _extract_json(text: str) -> dict | None:
    """从模型输出里抽第一个 JSON 对象（容忍 ```json 包裹与前后赘述）。"""
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None


class KKLabMemoryCurator:
    """KK Lab AI 记忆草稿生成器（AI 优先，失败/关闭降级规则）。

    与 core/ai/curator.py 的 Curator 平行，专司 5 类 KK Lab 记忆条目。
    """

    def __init__(self, settings: AISettings):
        self._settings = settings

    def make_draft(self, turn: dict, draft_kind: str) -> dict:
        """生成草稿（AI 优先，失败/关闭降级规则）；结果已脱敏，供 UI 弹框微调。

        返回 dict 含：
          - entry_id: 已生成的 ID
          - file_kind: 目标文件类型（memory/lessons/...）
          - title: 条目标题
          - fields: [(label, value)] 列表，按模板顺序
          - target: 默认 'local'
          - _src: 来源标记
        """
        draft = None
        if self._settings.curator_ai_assist_enabled:
            draft = self._draft_via_ai(turn, draft_kind)
        if not draft:
            draft = self._draft_via_rule(turn, draft_kind)
            draft.setdefault("_src", _now_src("rule"))
        else:
            draft.setdefault("_src", _now_src("ai"))
        return self._finalize_draft(draft, turn, draft_kind)

    def _draft_via_ai(self, turn: dict, draft_kind: str) -> dict | None:
        """调 deepseekv4flash 汇总润色成结构化草稿；任何失败返回 None 降级。"""
        if not self._settings.is_configured():
            return None
        instruction = _AI_INSTRUCTIONS.get(draft_kind)
        if not instruction:
            return None
        user_text = turn.get("user", "")
        assistant_text = turn.get("assistant", "")
        page_key = turn.get("page_key", "")
        content = (
            f"页面键: {page_key}\n\n用户:\n{user_text}\n\n助手:\n{assistant_text}\n\n"
            "请只输出 JSON，不要额外说明。"
        )
        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": content},
        ]
        try:
            client = NewAPIClient(
                base_url=self._settings.effective_base_url,
                api_key=self._settings.effective_api_key,
                timeout_seconds=self._settings.timeout_seconds,
            )
            result = client.chat(
                model=self._settings.curator_draft_model,
                messages=messages,
                temperature=0.2,
                max_tokens=512,
            )
        except AIClientError as exc:
            logger.info("KK Lab 记忆草稿 AI 润色失败，降级规则兜底: %s", exc)
            return None
        except Exception:  # noqa: BLE001 - 兜底降级
            logger.info("KK Lab 记忆草稿 AI 润色异常，降级规则兜底", exc_info=True)
            return None
        parsed = _extract_json(result.content)
        if not isinstance(parsed, dict):
            logger.info("KK Lab 记忆草稿 AI 返回无法解析为 JSON，降级规则兜底")
            return None
        return parsed

    def _draft_via_rule(self, turn: dict, draft_kind: str) -> dict:
        """规则/模板兜底草稿，永不依赖网络。"""
        user_text = (turn.get("user") or "").strip()
        assistant_text = (turn.get("assistant") or "").strip()
        page_key = (turn.get("page_key") or "").strip()
        if draft_kind == KIND_DRAFT_MEMORY:
            return {
                "title": user_text[:40] or "页面记忆",
                "summary": "由对话沉淀",
                "content": assistant_text or user_text,
                "conditions": f"页面 {page_key}" if page_key else "",
                "stability": "tentative",
            }
        if draft_kind == KIND_DRAFT_LESSON:
            return {
                "title": user_text[:40] or "经验条目",
                "phenomenon": user_text,
                "cause": "",
                "solution": assistant_text,
                "verification": "",
                "risk": "low",
                "lesson_type": "排障",
            }
        if draft_kind == KIND_DRAFT_TEST_ITEM:
            return {
                "title": user_text[:40] or "测试项",
                "goal": user_text,
                "preconditions": "",
                "params": "",
                "steps": assistant_text,
                "expected": "",
                "scope": f"页面 {page_key}" if page_key else "",
            }
        if draft_kind == KIND_DRAFT_TEST_CASE:
            return {
                "title": user_text[:40] or "测试用例",
                "case_type": "manual",
                "input": user_text,
                "steps": assistant_text,
                "expected": "",
                "pass_criteria": "",
                "fail_debug": "",
                "automation": "none",
            }
        if draft_kind == KIND_DRAFT_QUICK_ACTION:
            template = _NUMBER_RE.sub("{v}", user_text)
            return {
                "title": "快捷指令",
                "template": template or user_text,
                "placeholders": "",
                "condition": f"页面 {page_key}" if page_key else "",
                "expectation": "",
                "status": "draft",
            }
        return {}

    def _mask_draft(self, draft: dict) -> dict:
        masked: dict = {}
        for key, val in draft.items():
            if isinstance(val, str):
                masked[key] = mask_sensitive(val)
            else:
                masked[key] = val
        return masked

    def _finalize_draft(self, draft: dict, turn: dict, draft_kind: str) -> dict:
        """补全 entry_id / file_kind / fields / target，并脱敏。"""
        draft = self._mask_draft(draft)
        file_kind = draft_kind_to_file_kind(draft_kind)
        entry_id = make_id(file_kind)
        page_key = (turn.get("page_key") or "").strip()
        title = str(draft.get("title") or "未命名条目").strip()
        fields = _draft_to_fields(draft, draft_kind, page_key)
        return {
            "entry_id": entry_id,
            "file_kind": file_kind,
            "draft_kind": draft_kind,
            "title": title,
            "fields": fields,
            "target": TARGET_LOCAL,
            "page_key": page_key,
            "_src": draft.get("_src", _now_src("rule")),
            "_raw": draft,
        }


def _draft_to_fields(
    draft: dict, draft_kind: str, page_key: str
) -> list[tuple[str, str]]:
    """把草稿 dict 转为 [(label, value)] 列表，按 conventions.md 模板顺序。"""
    if draft_kind == KIND_DRAFT_MEMORY:
        return [
            ("页面", page_key),
            ("来源", "ai_assistant"),
            ("稳定性", str(draft.get("stability") or "tentative").strip()),
            ("摘要", str(draft.get("summary") or "").strip()),
            ("内容", str(draft.get("content") or "").strip()),
            ("适用条件", str(draft.get("conditions") or "").strip()),
        ]
    if draft_kind == KIND_DRAFT_LESSON:
        return [
            ("页面", page_key),
            ("类型", str(draft.get("lesson_type") or "排障").strip()),
            ("现象", str(draft.get("phenomenon") or "").strip()),
            ("原因", str(draft.get("cause") or "").strip()),
            ("处理办法", str(draft.get("solution") or "").strip()),
            ("验证方式", str(draft.get("verification") or "").strip()),
            ("风险等级", str(draft.get("risk") or "low").strip()),
        ]
    if draft_kind == KIND_DRAFT_TEST_ITEM:
        return [
            ("页面", page_key),
            ("目标", str(draft.get("goal") or "").strip()),
            ("前置条件", str(draft.get("preconditions") or "").strip()),
            ("参数", str(draft.get("params") or "").strip()),
            ("步骤", str(draft.get("steps") or "").strip()),
            ("期望结果", str(draft.get("expected") or "").strip()),
            ("数据记录", ""),
            ("适用范围", str(draft.get("scope") or "").strip()),
        ]
    if draft_kind == KIND_DRAFT_TEST_CASE:
        return [
            ("页面", page_key),
            ("用例类型", str(draft.get("case_type") or "manual").strip()),
            ("输入", str(draft.get("input") or "").strip()),
            ("执行步骤", str(draft.get("steps") or "").strip()),
            ("期望行为", str(draft.get("expected") or "").strip()),
            ("通过标准", str(draft.get("pass_criteria") or "").strip()),
            ("失败排查", str(draft.get("fail_debug") or "").strip()),
            ("可自动化程度", str(draft.get("automation") or "none").strip()),
        ]
    if draft_kind == KIND_DRAFT_QUICK_ACTION:
        return [
            ("页面", page_key),
            ("来源", "ai_assistant"),
            ("状态", str(draft.get("status") or "draft").strip()),
            ("模板", str(draft.get("template") or "").strip()),
            ("占位符", str(draft.get("placeholders") or "").strip()),
            ("适用条件", str(draft.get("condition") or "").strip()),
            ("执行预期", str(draft.get("expectation") or "").strip()),
        ]
    return []


def render_draft_entry(draft: dict) -> str:
    """把 finalize 后的草稿渲染为 markdown 条目文本。"""
    return render_entry(
        draft.get("file_kind", KIND_LESSONS),
        draft.get("entry_id", ""),
        draft.get("title", ""),
        draft.get("fields", []),
    )


# ---- Phase 3：条目索引化 --------------------------------------------------


_TAG_FIELDS: dict[str, tuple[str, ...]] = {
    KIND_MEMORY: ("稳定性", "来源"),
    KIND_LESSONS: ("类型", "风险等级"),
    KIND_TEST_ITEMS: (),
    KIND_TEST_CASES: ("用例类型", "可自动化程度"),
    KIND_QUICK_ACTIONS: ("状态", "来源"),
}


def extract_tags(entry: MemoryEntry, kind: str) -> list[str]:
    """从条目 body 中抽取分类标签字段（类型/状态/风险等级等）。"""
    fields = _TAG_FIELDS.get(kind, ())
    tags: list[str] = []
    for name in fields:
        value = _extract_field(entry.body, name)
        if value:
            tags.append(f"{name}:{value}")
    return tags


def build_index(
    page_key: str | None = None,
    kind: str | None = None,
    *,
    include_shared: bool = False,
) -> list[dict]:
    """构建条目索引：entry_id / title / page / kind / tags / target / source_file。

    page_key 为 None 时遍历全部白名单页面；kind 为 None 时遍历全部 5 类。
    include_shared=True 时额外纳入 _shared/cross_page_lessons.md。
    """
    pages: list[str] = (
        [page_key] if page_key and is_valid_page_key(page_key) else list(PAGE_KEYS)
    )
    kinds: tuple[str, ...] = (kind,) if kind and kind in KINDS else KINDS
    index: list[dict] = []
    for pk in pages:
        for k in kinds:
            for ent in read_entries(pk, k):
                index.append(
                    _entry_to_index(ent, k, pk, _detect_target(ent.source_file))
                )
    if include_shared and (kind is None or kind == KIND_LESSONS):
        for ent in read_shared_lessons():
            index.append(_entry_to_index(ent, KIND_LESSONS, "_shared", "project"))
    return index


def _entry_to_index(
    ent: MemoryEntry, kind: str, page_key: str, target: str
) -> dict:
    return {
        "entry_id": ent.entry_id,
        "title": ent.title,
        "page": page_key,
        "kind": kind,
        "tags": extract_tags(ent, kind),
        "target": target,
        "source_file": ent.source_file,
    }


def _detect_target(source_file: str) -> str:
    """根据 source_file 路径推断来源层（local/project）。"""
    if not source_file:
        return TARGET_LOCAL
    if ".local.md" in os.path.basename(source_file):
        return TARGET_LOCAL
    return TARGET_PROJECT


# ---- Phase 3：测试项 → 快捷指令草稿 ---------------------------------------


_NUMBERED_STEP_RE = re.compile(r"^\s*\d+\.\s*(.*)$")


def test_item_to_quick_action_draft(entry: MemoryEntry, page_key: str) -> dict:
    """把一条 test_items 条目转为 quick_action 草稿（供 KKLabMemoryDialog 微调）。

    步骤首行作为模板雏形，数值替换成 {v} 占位符；参数字段映射为占位符说明。
    """
    goal = _extract_field(entry.body, "目标")
    steps = _extract_multiline_field(entry.body, "步骤")
    params = _extract_multiline_field(entry.body, "参数")
    expected = _extract_multiline_field(entry.body, "期望结果")

    template = _first_step_as_template(steps) or goal or entry.title
    placeholders = _params_to_placeholders(params)

    file_kind = KIND_QUICK_ACTIONS
    entry_id = make_id(file_kind)
    fields = _draft_to_fields(
        {
            "title": f"{entry.title}（快捷指令）",
            "template": template,
            "placeholders": placeholders,
            "condition": f"页面 {page_key}" if page_key else "",
            "expectation": expected or goal,
            "status": "draft",
        },
        KIND_DRAFT_QUICK_ACTION,
        page_key,
    )
    return {
        "entry_id": entry_id,
        "file_kind": file_kind,
        "draft_kind": KIND_DRAFT_QUICK_ACTION,
        "title": f"{entry.title}（快捷指令）",
        "fields": fields,
        "target": TARGET_LOCAL,
        "page_key": page_key,
        "_src": _now_src("test_item_conversion"),
        "_raw": {"source_entry_id": entry.entry_id},
    }


def _first_step_as_template(steps_text: str) -> str:
    """取步骤首行，数值替换为 {v}，作为快捷指令模板雏形。"""
    if not steps_text:
        return ""
    for line in steps_text.splitlines():
        match = _NUMBERED_STEP_RE.match(line)
        if match:
            return _NUMBER_RE.sub("{v}", match.group(1).strip())
    return _NUMBER_RE.sub("{v}", steps_text.splitlines()[0].strip())


def _params_to_placeholders(params_text: str) -> str:
    """把"参数"字段（chip: ...; voltage: ...）转成占位符说明。"""
    if not params_text:
        return ""
    parts: list[str] = []
    for line in params_text.splitlines():
        line = line.strip().lstrip("-").strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key:
            parts.append(f"{key}: {value}" if value else key)
    return "; ".join(parts)


# ---- Phase 3：测试用例 → eval 草稿 ----------------------------------------


_AUTOMATION_FULL = "full"
_AUTOMATION_PARTIAL = "partial"


def test_case_to_eval_draft(entry: MemoryEntry, page_key: str) -> dict | None:
    """把一条 test_cases 条目转为 eval case JSON 草稿。

    仅当"可自动化程度"为 full 或 partial 时导出；返回 None 表示不适用。
    """
    automation = _extract_field(entry.body, "可自动化程度").strip().lower()
    if automation not in (_AUTOMATION_FULL, _AUTOMATION_PARTIAL):
        return None

    case_input = _extract_multiline_field(entry.body, "输入")
    expected = _extract_multiline_field(entry.body, "期望行为")
    pass_criteria = _extract_multiline_field(entry.body, "通过标准")
    case_type = _extract_field(entry.body, "用例类型")

    case_id = _sanitize_eval_id(entry.entry_id, page_key)
    expect: dict = {}
    if case_type == "instrument_required":
        expect["expect_tool"] = True
    elif case_type == "manual":
        expect["expect_tool"] = False
    any_kw = _split_keywords(expected)
    if any_kw:
        expect["any_keywords"] = any_kw
    all_kw = _split_keywords(pass_criteria)
    if all_kw:
        expect["all_keywords"] = all_kw

    return {
        "id": case_id,
        "desc": f"{entry.title}（来源：{entry.entry_id}，自动化={automation}）",
        "page_key": page_key,
        "user": _strip_list_marker(case_input) or entry.title,
        "history": [],
        "expect": expect,
        "_source_entry_id": entry.entry_id,
        "_automation": automation,
    }


def _sanitize_eval_id(entry_id: str, page_key: str) -> str:
    """把 TC-YYYYMMDD-HHMMSS 转为 eval case 文件名友好的 id。"""
    raw = f"{page_key}_{entry_id}".lower()
    return re.sub(r"[^a-z0-9_]+", "_", raw).strip("_")


_LIST_MARKER_RE = re.compile(r"^\s*(?:-\s+|\d+\.\s+)")


def _strip_list_marker(text: str) -> str:
    """去掉 markdown 列表标记（- / 1.），保留正文。"""
    if not text:
        return ""
    lines = []
    for line in text.splitlines():
        lines.append(_LIST_MARKER_RE.sub("", line).strip())
    return "\n".join(lines).strip()


def _split_keywords(text: str) -> list[str]:
    """把多行/分号分隔的文本拆为关键字列表，去掉列表标记。"""
    if not text:
        return []
    parts: list[str] = []
    for chunk in re.split(r"[\n;；]", text):
        kw = _LIST_MARKER_RE.sub("", chunk).strip()
        if kw:
            parts.append(kw)
    return parts


def eval_cases_dir() -> str:
    """tests/ai_eval/cases 目录绝对路径。"""
    return os.path.join(get_resource_base(), "tests", "ai_eval", "cases")


def write_eval_draft(draft: dict) -> tuple[bool, str]:
    """把 eval 草稿写入 tests/ai_eval/cases/<id>.json。返回 (ok, path_or_message)。"""
    if not draft or not draft.get("id"):
        return False, "eval 草稿缺少 id"
    case_id = str(draft["id"])
    directory = eval_cases_dir()
    if not _ensure_dir(os.path.join(directory, case_id + ".json")):
        return False, "创建 eval 用例目录失败"
    path = os.path.join(directory, f"{case_id}.json")
    payload = {k: v for k, v in draft.items() if not k.startswith("_")}
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        return True, path
    except OSError:
        logger.error("写入 eval 草稿失败: %s", path, exc_info=True)
        return False, "写入 eval 草稿失败"


# ---- Phase 3：删除与提升 --------------------------------------------------


def delete_entry(
    page_key: str | None, kind: str, entry_id: str, *, target: str = TARGET_LOCAL
) -> tuple[bool, str]:
    """从指定文件删除一条 entry_id 条目。返回 (ok, message)。"""
    if target == TARGET_PROJECT:
        path = project_file(page_key or "", kind)
    else:
        path = local_file(page_key or "", kind)
    if path is None:
        return False, "非法 page_key 或 kind"
    existing = _read_text(path)
    if not existing:
        return False, "文件不存在或为空"
    lines = existing.splitlines(keepends=True)
    start = _find_entry_line_index(lines, entry_id)
    if start >= len(lines) or not lines[start].startswith(f"## {entry_id}"):
        return False, f"未找到条目 {entry_id}"
    end = _find_entry_end_index(lines, start, entry_id)
    rebuilt = "".join(lines[:start]) + "".join(lines[end:])
    ok = _write_file(path, rebuilt)
    return ok, "已删除" if ok else "写入失败"


def promote_local_to_project(
    page_key: str | None, kind: str, entry_id: str
) -> tuple[bool, str]:
    """把本机私有层条目提升到项目级 docs（删除本机 + 追加项目）。"""
    loc_path = local_file(page_key or "", kind)
    if loc_path is None:
        return False, "非法 page_key 或 kind"
    existing = _read_text(loc_path)
    if not existing:
        return False, "本机文件不存在或为空"
    entries = parse_entries(existing, loc_path)
    target_entry: MemoryEntry | None = None
    for ent in entries:
        if ent.entry_id == entry_id:
            target_entry = ent
            break
    if target_entry is None:
        return False, f"本机层未找到条目 {entry_id}"

    ok_append, msg_append = append_entry(
        page_key, kind, target_entry.raw.strip(), target=TARGET_PROJECT
    )
    if not ok_append:
        return False, f"写入项目级失败：{msg_append}"
    ok_del, msg_del = delete_entry(page_key, kind, entry_id, target=TARGET_LOCAL)
    if not ok_del:
        logger.warning(
            "提升后本机删除失败 entry_id=%s： %s", entry_id, msg_del
        )
    return True, f"已提升到项目级 docs（{entry_id}）"

"""本机经验沉淀器（AI_Assistant_MD §2.7 / Phase 5a）。

把"刚才这轮交互"一键固化为可复用资产，无需手改 json/md：
  - as_nudge        → 纠偏片段（user_data/ai/nudges.local.json）
  - as_quick_action → 快捷指令模板（user_data/ai/quick_actions.local.json）
  - as_project_rule → 项目规则追加（user_data/ai/project_rules.local.md）
  - as_eval_case    → eval 回归用例（tests/ai_eval/cases/*.json）

草稿生成默认走 AI 汇总润色（deepseekv4flash），失败/关闭则降级规则兜底；
写入前一律 mask_sensitive 脱敏 + 去重 + 记 _src 来源时间戳，便于回滚与统计。

红线：草稿生成失败只记 INFO 并降级，不抛断流程；禁裸 except；禁 print。
"""
from __future__ import annotations

import json
import os
import re
import time
import zipfile

from core.ai.config import AISettings
from core.ai.newapi_client import AIClientError, NewAPIClient
from core.ai.nudges import local_nudges_path, reload_nudges
from core.ai.prompt_manager import mask_sensitive
from ui.resource_path import get_user_data_dir
from log_config import get_logger

logger = get_logger(__name__)

KIND_NUDGE = "nudge"
KIND_QUICK_ACTION = "quick_action"
KIND_PROJECT_RULE = "project_rule"
KIND_EVAL_CASE = "eval_case"

_QUICK_ACTIONS_LOCAL = "quick_actions.local.json"
_PROJECT_RULES_LOCAL = "project_rules.local.md"
_USER_PROMPT_NAME = "user_prompt.md"

_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])(-?\d+(?:\.\d+)?)")


def _now_src(via: str) -> str:
    return f"{via} @ {time.strftime('%Y-%m-%d %H:%M:%S')}"


def _quick_actions_local_path() -> str:
    return os.path.join(get_user_data_dir("ai"), _QUICK_ACTIONS_LOCAL)


def _project_rules_local_path() -> str:
    return os.path.join(get_user_data_dir("ai"), _PROJECT_RULES_LOCAL)


def _eval_cases_dir() -> str:
    from core.ai.eval_runner import cases_dir

    directory = cases_dir()
    os.makedirs(directory, exist_ok=True)
    return directory


def _read_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except (OSError, json.JSONDecodeError):
        logger.error("读取本机经验文件失败: %s", path, exc_info=True)
        return {}


def _write_json(path: str, data: dict) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        logger.error("写入本机经验文件失败: %s", path, exc_info=True)
        return False


class Curator:
    """本机沉淀器：草稿生成（AI 优先）+ 写入去重 + 列出/删除/导出/重置。"""

    def __init__(self, settings: AISettings):
        self._settings = settings

    # ---- 草稿生成 -----------------------------------------------------

    def make_draft(self, turn: dict, kind: str) -> dict:
        """生成草稿（AI 优先，失败/关闭降级规则）；结果已脱敏，供 UI 弹框微调。"""
        draft = None
        if self._settings.curator_ai_assist_enabled:
            draft = self._draft_via_ai(turn, kind)
        if not draft:
            draft = self._draft_via_rule(turn, kind)
            draft.setdefault("_src", _now_src("rule"))
        else:
            draft.setdefault("_src", _now_src("ai"))
        return self._mask_draft(draft)

    def _draft_via_ai(self, turn: dict, kind: str) -> dict | None:
        """调 deepseekv4flash 汇总润色成结构化草稿；任何失败返回 None 降级。"""
        if not self._settings.is_configured():
            return None
        instruction = _AI_INSTRUCTIONS.get(kind)
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
            logger.info("草稿 AI 润色失败，降级规则兜底: %s", exc)
            return None
        except Exception:  # noqa: BLE001 - 兜底降级
            logger.info("草稿 AI 润色异常，降级规则兜底", exc_info=True)
            return None
        parsed = _extract_json(result.content)
        if not isinstance(parsed, dict):
            logger.info("草稿 AI 返回无法解析为 JSON，降级规则兜底")
            return None
        return parsed

    def _draft_via_rule(self, turn: dict, kind: str) -> dict:
        """规则/模板兜底草稿，永不依赖网络。"""
        user_text = (turn.get("user") or "").strip()
        assistant_text = (turn.get("assistant") or "").strip()
        page_key = (turn.get("page_key") or "").strip()
        if kind == KIND_NUDGE:
            return {
                "id": f"local_{int(time.time())}",
                "when": f"page={page_key}" if page_key else "no_tool_call_but_claims_done",
                "text": assistant_text or user_text,
            }
        if kind == KIND_QUICK_ACTION:
            template = _NUMBER_RE.sub("{v}", user_text)
            return {"page_key": page_key, "template": template or user_text}
        if kind == KIND_PROJECT_RULE:
            return {"text": user_text or assistant_text}
        if kind == KIND_EVAL_CASE:
            return {
                "id": f"local_{int(time.time())}",
                "desc": "本机沉淀用例",
                "page_key": page_key,
                "user": user_text,
                "history": [],
                "expect": {"any_keywords": []},
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

    # ---- 写入 ---------------------------------------------------------

    def as_nudge(self, draft: dict) -> bool:
        """把草稿写入本机片段库（按 id 去重覆盖）。"""
        nid = str(draft.get("id") or "").strip()
        when = str(draft.get("when") or "").strip()
        text = mask_sensitive(str(draft.get("text") or "").strip())
        if not (nid and when and text):
            logger.warning("nudge 草稿字段不全，放弃写入")
            return False
        path = local_nudges_path()
        data = _read_json(path)
        items = [x for x in (data.get("nudges") or []) if isinstance(x, dict)]
        items = [x for x in items if str(x.get("id")) != nid]
        items.append(
            {"id": nid, "when": when, "text": text, "_src": draft.get("_src", _now_src("rule"))}
        )
        data["nudges"] = items
        ok = _write_json(path, data)
        if ok:
            reload_nudges()
        return ok

    def as_quick_action(self, draft: dict) -> bool:
        """把模板写入本机快捷指令库（按 page_key 分组去重）。"""
        page_key = str(draft.get("page_key") or "_default").strip() or "_default"
        template = mask_sensitive(str(draft.get("template") or "").strip())
        if not template:
            logger.warning("quick_action 草稿无模板，放弃写入")
            return False
        path = _quick_actions_local_path()
        data = _read_json(path)
        groups = data.get("quick_actions") or {}
        if not isinstance(groups, dict):
            groups = {}
        bucket = [str(x) for x in (groups.get(page_key) or []) if str(x).strip()]
        if template not in bucket:
            bucket.append(template)
        groups[page_key] = bucket
        data["quick_actions"] = groups
        return _write_json(path, data)

    def as_project_rule(self, draft: dict) -> bool:
        """把一条规则追加到本机项目规则文件（带分隔标记，便于回滚）。"""
        text = mask_sensitive(str(draft.get("text") or "").strip())
        if not text:
            logger.warning("project_rule 草稿为空，放弃写入")
            return False
        path = _project_rules_local_path()
        marker = f"\n<!-- {draft.get('_src', _now_src('rule'))} -->\n- {text}\n"
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(marker)
            return True
        except OSError:
            logger.error("追加项目规则失败: %s", path, exc_info=True)
            return False

    def as_eval_case(self, draft: dict) -> bool:
        """把草稿写入 tests/ai_eval/cases/<id>.json。"""
        case_id = str(draft.get("id") or f"local_{int(time.time())}").strip()
        case_id = re.sub(r"[^A-Za-z0-9_\-]", "_", case_id)
        payload = {
            "id": case_id,
            "desc": mask_sensitive(str(draft.get("desc") or "")),
            "page_key": draft.get("page_key") or "",
            "user": mask_sensitive(str(draft.get("user") or "")),
            "history": draft.get("history") or [],
            "expect": draft.get("expect") or {},
        }
        path = os.path.join(_eval_cases_dir(), f"{case_id}.json")
        return _write_json(path, payload)

    # ---- 列出 / 删除（UI 本机经验面板） --------------------------------

    def list_local(self) -> dict:
        """汇总本机沉淀资产，供设置页面板展示。"""
        nudges = [
            x for x in (_read_json(local_nudges_path()).get("nudges") or [])
            if isinstance(x, dict)
        ]
        qa_groups = _read_json(_quick_actions_local_path()).get("quick_actions") or {}
        eval_cases = []
        directory = _eval_cases_dir()
        for name in sorted(os.listdir(directory)):
            if name.endswith(".json"):
                eval_cases.append(name[:-5])
        return {
            "nudges": nudges,
            "quick_actions": qa_groups if isinstance(qa_groups, dict) else {},
            "eval_cases": eval_cases,
        }

    def delete_nudge(self, nudge_id: str) -> bool:
        path = local_nudges_path()
        data = _read_json(path)
        items = [
            x for x in (data.get("nudges") or [])
            if isinstance(x, dict) and str(x.get("id")) != nudge_id
        ]
        data["nudges"] = items
        ok = _write_json(path, data)
        if ok:
            reload_nudges()
        return ok

    def delete_eval_case(self, case_id: str) -> bool:
        case_id = re.sub(r"[^A-Za-z0-9_\-]", "_", case_id)
        path = os.path.join(_eval_cases_dir(), f"{case_id}.json")
        if not os.path.isfile(path):
            return False
        try:
            os.remove(path)
            return True
        except OSError:
            logger.error("删除 eval 用例失败: %s", path, exc_info=True)
            return False

    # ---- 导出 / 重置（§2.7.3） ----------------------------------------

    def export_pack(self, target_zip: str) -> bool:
        """把本机经验（user_prompt + 本地 nudges/quick_actions/规则 + eval 草稿）打 zip。"""
        ai_dir = get_user_data_dir("ai")
        members: list[tuple[str, str]] = []
        for fname in (
            _USER_PROMPT_NAME,
            os.path.basename(local_nudges_path()),
            _QUICK_ACTIONS_LOCAL,
            _PROJECT_RULES_LOCAL,
        ):
            full = os.path.join(ai_dir, fname)
            if os.path.isfile(full):
                members.append((full, f"ai/{fname}"))
        cases_directory = _eval_cases_dir()
        for name in os.listdir(cases_directory):
            if name.endswith(".json") and name.startswith("local_"):
                members.append(
                    (os.path.join(cases_directory, name), f"ai_eval/cases/{name}")
                )
        try:
            with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for full, arc in members:
                    zf.write(full, arc)
            logger.info("已导出经验包: %s（%d 项）", target_zip, len(members))
            return True
        except OSError:
            logger.error("导出经验包失败: %s", target_zip, exc_info=True)
            return False

    def reset_local(self) -> bool:
        """清空用户层与本地沉淀（破坏性，UI 须二次确认）；仅保留随包项目层。"""
        ai_dir = get_user_data_dir("ai")
        ok = True
        for fname in (
            _USER_PROMPT_NAME,
            os.path.basename(local_nudges_path()),
            _QUICK_ACTIONS_LOCAL,
            _PROJECT_RULES_LOCAL,
        ):
            full = os.path.join(ai_dir, fname)
            if os.path.isfile(full):
                try:
                    os.remove(full)
                except OSError:
                    logger.error("重置删除失败: %s", full, exc_info=True)
                    ok = False
        cases_directory = _eval_cases_dir()
        for name in os.listdir(cases_directory):
            if name.endswith(".json") and name.startswith("local_"):
                try:
                    os.remove(os.path.join(cases_directory, name))
                except OSError:
                    logger.error("重置删除用例失败: %s", name, exc_info=True)
                    ok = False
        reload_nudges()
        return ok


_AI_INSTRUCTIONS = {
    KIND_NUDGE: (
        "你是 AI 行为约束整理助手。基于给定的一轮对话（用户纠正了 AI 的错误行为），"
        "提炼成一条简洁的 AI 行为约束片段，用于以后注入提示词纠偏。"
        "只输出 JSON：{\"id\": \"英文短标识\", \"when\": \"触发条件(no_tool_call_but_claims_done 或 page=页面键)\", "
        "\"text\": \"简体中文约束正文，祈使句，≤120字\"}。"
    ),
    KIND_QUICK_ACTION: (
        "你是快捷指令模板整理助手。把用户刚发的有效指令整理成可复用模板，"
        "并把其中的数值参数替换成 {占位符}（如通道用 {ch}、电压用 {v}）。"
        "只输出 JSON：{\"page_key\": \"页面键\", \"template\": \"简体中文模板\"}。"
    ),
    KIND_PROJECT_RULE: (
        "你是项目规则提炼助手。把这轮交互体现的项目约定提炼成一条简洁规则。"
        "只输出 JSON：{\"text\": \"简体中文规则，祈使句，≤80字\"}。"
    ),
    KIND_EVAL_CASE: (
        "你是回归用例整理助手。从这轮交互提炼一条 输入→期望行为 用例。"
        "只输出 JSON：{\"id\": \"英文短标识\", \"desc\": \"说明\", \"page_key\": \"页面键\", "
        "\"user\": \"用户输入\", \"expect\": {\"any_keywords\": [], \"forbid_keywords\": [], \"expect_tool\": false}}。"
    ),
}


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

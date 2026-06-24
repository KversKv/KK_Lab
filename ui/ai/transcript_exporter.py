"""AI 会话调试导出：把面板内扁平流水格式化为 Markdown。

从 ``ai_assist_panel`` 抽出的纯逻辑（无 Qt 控件依赖），沿用
``chat_view`` / ``config_preview`` / ``script_preview`` 的拆分风格，
便于单测与后续复用。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import TYPE_CHECKING

from log_config import get_logger

if TYPE_CHECKING:
    from core.ai.ai_service import AIService

logger = get_logger(__name__)


def build_export_markdown(
    service: "AIService",
    transcript: list[dict],
    session_started_at: datetime,
    model_selection,
) -> str:
    """组装完整的会话调试导出 Markdown。

    参数：
        service: ``AIService``，提供 ``current_page_key`` / ``settings`` /
            ``persisted_history``。
        transcript: 面板内扁平流水（``panel._transcript``）。
        session_started_at: 本轮会话开始时间。
        model_selection: 手动选择模型的标识（``model_combo.currentData()``）。
    """
    from core.ai.profiles import get_global_system_prompt, get_profile

    page_key = service.current_page_key()
    profile = get_profile(page_key)
    settings = service.settings
    lines: list[str] = []

    lines.append("# KK_Lab AI 会话调试导出")
    lines.append("")
    lines.append(
        f"- 导出时间：{datetime.now().isoformat(timespec='seconds')}"
    )
    lines.append(
        f"- 会话开始：{session_started_at.isoformat(timespec='seconds')}"
    )
    lines.append(f"- 当前页面 (page_key)：`{page_key or '_default'}`")
    lines.append(
        f"- 模型：`{getattr(settings, 'default_model', '')}` "
        f"（model_mode=`{getattr(settings, 'model_mode', '')}`，"
        f"stream=`{getattr(settings, 'stream', '')}`）"
    )
    lines.append(f"- 手动选择模型：`{model_selection or '自动'}`")
    lines.append("")

    lines.append("## 系统提示（System Prompt）")
    lines.append("")
    lines.append("### 全局")
    lines.append("")
    lines.append("```text")
    lines.append(get_global_system_prompt())
    lines.append("```")
    lines.append("")
    lines.append("### 页面 Profile")
    lines.append("")
    lines.append("```text")
    lines.append(str(profile.get("system_prompt", "")))
    lines.append("```")
    lines.append("")

    lines.append("## 会话流水（按轮次分组的完整顺序流程）")
    lines.append("")
    lines.append(
        "> 每一轮从用户提问开始，依序记录：注入上下文（喂给模型的数据）→ "
        "请求执行指令 → 指令执行结果 → 确认卡片 → AI 回复 → 用量。"
    )
    lines.append("")
    if not transcript:
        lines.append("_（本轮会话暂无流水记录）_")
        lines.append("")
    else:
        lines.extend(_format_rounds(transcript))

    lines.append("## 持久化历史（service.persisted_history）")
    lines.append("")
    history = service.persisted_history()
    if not history:
        lines.append("_（无）_")
    else:
        for item in history:
            role = item.get("role", "")
            lines.append(f"- **{role}**：{item.get('content', '')}")
    lines.append("")

    lines.append("## 动作审计日志（audit.log）")
    lines.append("")
    lines.append(_read_audit_tail())
    lines.append("")

    return "\n".join(lines)


def _format_rounds(transcript: list[dict]) -> list[str]:
    """把扁平流水按「轮次」分组并加步骤编号，让单轮调用顺序一目了然。

    每遇到一个 user / analysis 条目即开启新一轮；轮内每个条目依序编号
    （step 1、step 2 …），AI 回复 / 用量等都归入当轮，从而能看清一次
    提问到最终回答之间，数据注入、工具调用、确认、回复的完整顺序。
    """
    out: list[str] = []
    round_no = 0
    step_no = 0
    opened = False

    def _close_round() -> None:
        if opened:
            out.append("---")
            out.append("")

    for entry in transcript:
        kind = entry.get("kind", "")
        if kind in ("user", "analysis") or not opened:
            _close_round()
            round_no += 1
            step_no = 0
            opened = True
            ts = entry.get("ts", "")
            out.append(f"## 🔁 第 {round_no} 轮  `{ts}`")
            out.append("")
        step_no += 1
        out.extend(_format_entry(entry, step=step_no))
    _close_round()
    return out


def _format_entry(entry: dict, step: int | None = None) -> list[str]:
    ts = entry.get("ts", "")
    kind = entry.get("kind", "")
    out: list[str] = []
    if kind == "user":
        out.append(f"### 🧑 用户  `{ts}`")
        out.append("")
        out.append(str(entry.get("text", "")))
    elif kind == "assistant":
        out.append(f"### 🤖 AI 回复  `{ts}`")
        out.append("")
        out.append(str(entry.get("text", "")))
    elif kind == "analysis":
        out.append(f"### 📊 日志分析  `{ts}`")
        out.append("")
        out.append(str(entry.get("text", "")))
    elif kind == "error":
        out.append(f"### ⚠ 错误  `{ts}`")
        out.append("")
        out.append(str(entry.get("text", "")))
    elif kind == "action_requested":
        out.append(f"### ⚙ 请求执行指令  `{ts}`")
        out.append("")
        out.append(f"- 动作：`{entry.get('name', '')}`")
        out.append("- 参数：")
        out.append("")
        out.append("```json")
        out.append(
            json.dumps(
                entry.get("arguments", {}), ensure_ascii=False, indent=2, default=str
            )
        )
        out.append("```")
    elif kind == "action_result":
        out.append(f"### ✅ 指令执行结果  `{ts}`")
        out.append("")
        out.append(f"- 动作：`{entry.get('name', '')}`")
        out.append(f"- 状态：`{entry.get('status', '')}`")
        out.append(f"- 风险等级：`{entry.get('risk_level', '')}`")
        out.append(f"- 白名单自动执行：`{entry.get('auto_approved', False)}`")
        out.append(f"- 消息：{entry.get('message', '')}")
        out.append("- 结果：")
        out.append("")
        out.append("```json")
        out.append(
            json.dumps(
                entry.get("result", {}), ensure_ascii=False, indent=2, default=str
            )
        )
        out.append("```")
    elif kind == "confirm_prompt":
        out.append(f"### ❓ 弹出确认卡片  `{ts}`")
        out.append("")
        out.append(f"- 动作：`{entry.get('name', '')}`")
        out.append(f"- 风险等级：`{entry.get('risk_level', '')}`")
        out.append(f"- 原因：{entry.get('reason', '')}")
        out.append("- 参数：")
        out.append("")
        out.append("```json")
        out.append(
            json.dumps(
                entry.get("arguments", {}), ensure_ascii=False, indent=2, default=str
            )
        )
        out.append("```")
    elif kind == "confirm_decision":
        out.append(f"### 🖱 确认决定  `{ts}`")
        out.append("")
        out.append(f"- 动作：`{entry.get('name', '')}`")
        out.append(f"- 确认：`{entry.get('confirmed', False)}`")
        out.append(f"- 记住本会话：`{entry.get('remember_session', False)}`")
        out.append(f"- 加入白名单：`{entry.get('remember_resident', False)}`")
        out.append(f"- 卡片状态：{entry.get('status_text', '')}")
    elif kind == "context":
        out.append(f"### 📎 注入上下文（喂给模型的数据）  `{ts}`")
        out.append("")
        scope = str(entry.get("scope", "") or "")
        if scope:
            out.append(f"- 范围：{scope}")
        blocks = entry.get("blocks", []) or []
        out.append(f"- 数据块数量：{len(blocks)}")
        for block in blocks:
            out.append("")
            out.append(f"**{block.get('source', '上下文')}：**")
            out.append("")
            out.append("```text")
            out.append(str(block.get("text", "")))
            out.append("```")
    elif kind == "usage":
        out.append(f"### 📈 用量  `{ts}`")
        out.append("")
        out.append(
            f"- 本次：↑{entry.get('turn_prompt', 0)} ↓{entry.get('turn_completion', 0)} "
            f"tokens @ {entry.get('output_tps', 0)} tok/s"
        )
        out.append(
            f"- 会话累计：↑{entry.get('session_prompt', 0)} "
            f"↓{entry.get('session_completion', 0)} tokens "
            f"（{entry.get('requests', 0)} 次请求）"
        )
    else:
        out.append(f"### {kind}  `{ts}`")
        out.append("")
        out.append(
            "```json\n"
            + json.dumps(entry, ensure_ascii=False, indent=2, default=str)
            + "\n```"
        )
    out.append("")
    if step is not None and out and out[0].startswith("### "):
        out[0] = "#### " + f"步骤 {step} · " + out[0][len("### "):]
    return out


def _read_audit_tail(max_lines: int = 50) -> str:
    try:
        from core.ai.actions.audit import get_audit_log

        path = get_audit_log().path
        if not os.path.isfile(path):
            return "_（无审计日志文件）_"
        with open(path, "r", encoding="utf-8") as f:
            tail = f.readlines()[-max_lines:]
        if not tail:
            return "_（审计日志为空）_"
        return "```jsonl\n" + "".join(tail).rstrip("\n") + "\n```"
    except Exception:
        logger.error("读取审计日志失败", exc_info=True)
        return "_（读取审计日志失败，请查看应用日志）_"

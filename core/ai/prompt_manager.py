"""PromptManager：拼装发送给模型的 messages。

组成（system 段）：
  全局 system prompt + 当前 Profile system_prompt + 各 ContextProvider 上下文。
可选附加最近运行日志（由调用方按需传入，已脱敏）。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from core.ai import context_budget
from core.ai.nudges import page_nudges
from core.ai.profiles import (
    get_global_system_prompt,
    get_profile,
    get_project_prompt,
    get_user_prompt,
)
from core.ai.providers.base import ContextProvider
from ui.resource_path import get_user_data_dir

_LOCAL_PROJECT_RULES_NAME = "project_rules.local.md"


def _get_local_project_rules() -> str:
    """读取本机沉淀的项目规则（user_data/ai/project_rules.local.md）。"""
    path = os.path.join(get_user_data_dir("ai"), _LOCAL_PROJECT_RULES_NAME)
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


@dataclass
class BudgetConfig:
    """token 预算配置快照（按当前模型解析后的窗口）。"""

    window: int = 131072
    reserve_output: int = 4096
    soft_budget_ratio: float = 0.5
    max_context_block_tokens: int = 8192
    waveform_block_tokens: int = 8192

_MASK_PATTERNS = [
    (re.compile(r"(?i)\b(sk-[A-Za-z0-9_\-]{8,})\b"), "[REDACTED_KEY]"),
    (re.compile(r"(?i)(api[_\-]?key\s*[=:]\s*)\S+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(authorization\s*:\s*bearer\s+)\S+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(password\s*[=:]\s*)\S+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(token\s*[=:]\s*)\S+"), r"\1[REDACTED]"),
]


def mask_sensitive(text: str) -> str:
    if not text:
        return text
    masked = text
    for pattern, repl in _MASK_PATTERNS:
        masked = pattern.sub(repl, masked)
    return masked


def _fmt(value: float) -> str:
    try:
        return f"{float(value):.6g}"
    except (TypeError, ValueError):
        return str(value)


def format_waveform_digest(digest, *, include_downsampled: bool = True) -> str:
    """把 WaveformDigest 文本化为可喂模型的 prompt 片段（F1.6）。

    第 1 层统计摘要永远输出；第 2 层降采样形状点按 include_downsampled 决定是否附带。
    """
    if digest is None or not getattr(digest, "stats", None):
        return "[波形数据] 当前无可分析的波形。"

    lines = ["[波形数据摘要]"]
    window = getattr(digest, "window", None)
    if window:
        if window.get("full"):
            lines.append("分析范围：全程")
        else:
            lines.append(
                f"分析范围：{_fmt(window.get('x0'))}~{_fmt(window.get('x1'))} s（屏幕可见区）"
            )
    note = getattr(digest, "note", "")
    if note:
        lines.append(note)

    for stat in digest.stats:
        unit = f" {stat.unit}" if stat.unit else ""
        lines.append(
            f"- 通道 {stat.label}（{stat.point_count} 点，采样周期 "
            f"{_fmt(stat.sample_period_s)} s）："
            f"min={_fmt(stat.minimum)}{unit}，max={_fmt(stat.maximum)}{unit}，"
            f"avg={_fmt(stat.average)}{unit}，pp={_fmt(stat.peak_to_peak)}{unit}，"
            f"std={_fmt(stat.std)}{unit}"
        )
        spike_events = getattr(stat, "spike_events", None)
        if spike_events:
            over_total = spike_events[0].get("over_threshold_total", "")
            event_count = len(spike_events)
            shown = ", ".join(
                f"事件{idx}[{_fmt(e.get('start'))}~{_fmt(e.get('end'))}]s "
                f"峰值={_fmt(e.get('peak_value'))}{unit}({e.get('type', '')})"
                for idx, e in enumerate(spike_events, 1)
            )
            lines.append(
                f"  · 尖峰事件（按时间聚簇计 {event_count} 处；"
                f"超阈采样点共 {over_total} 个，非独立脉冲数）：{shown}"
            )
        elif stat.anomalies:
            shown = ", ".join(
                f"t={_fmt(a.get('t'))}s→{_fmt(a.get('value'))}{unit}({a.get('type', '')})"
                for a in stat.anomalies[:10]
            )
            lines.append(f"  · 异常点（{len(stat.anomalies)}）：{shown}")
        if stat.steady_segments:
            shown = ", ".join(
                f"[{_fmt(s.get('start'))}~{_fmt(s.get('end'))}]s avg={_fmt(s.get('avg'))}{unit}"
                for s in stat.steady_segments[:5]
            )
            lines.append(f"  · 稳态段：{shown}")
        segments = getattr(stat, "segments", None)
        if segments:
            shown = ", ".join(
                f"段{idx}[{_fmt(s.get('start'))}~{_fmt(s.get('end'))}]s "
                f"{s.get('label', '')} mean={_fmt(s.get('mean'))}{unit} "
                f"peak={_fmt(s.get('peak'))}{unit} 宽={_fmt(s.get('width_ms'))}ms "
                f"电荷={_fmt(s.get('charge_uAh'))}uAh"
                for idx, s in enumerate(segments[:15], 1)
            )
            lines.append(
                f"  · 事件感知段落（STA-LTA+MAD 定位，共 {len(segments)} 段）：{shown}"
            )
        density_map = getattr(stat, "density_map", None)
        if density_map:
            high = [d for d in density_map if d.get("density") == "full"]
            base = next(
                (d for d in density_map if d.get("kind") == "minmax_baseline"),
                None,
            )
            base_txt = (
                f"基线 min-max 每桶约 {base.get('bucket_points')} 点稀疏；"
                if base
                else ""
            )
            lines.append(
                f"  · 采样密度（非均匀）：{base_txt}事件高密度区 {len(high)} 处"
            )

    if include_downsampled and getattr(digest, "downsampled", None):
        lines.append("[降采样形状点（LTTB，仅供观察趋势，非原始精度）]")
        for label, series in digest.downsampled.items():
            times = series.get("time", [])
            values = series.get("values", [])
            pairs = ", ".join(
                f"({_fmt(t)},{_fmt(v)})" for t, v in zip(times, values)
            )
            lines.append(f"- {label}: {pairs}")

    marker = getattr(digest, "marker_segment", None)
    if marker and marker.get("per_channel"):
        lines.append(
            f"[Marker A→B 区间] A={_fmt(marker.get('a'))}s, B={_fmt(marker.get('b'))}s, "
            f"时长={_fmt(marker.get('duration_s'))}s"
        )
        for ch in marker.get("per_channel", []):
            unit = f" {ch.get('unit')}" if ch.get("unit") else ""
            lines.append(
                f"- 通道 {ch.get('label')}（{ch.get('point_count')} 点）："
                f"avg={_fmt(ch.get('average'))}{unit}，min={_fmt(ch.get('minimum'))}{unit}，"
                f"max={_fmt(ch.get('maximum'))}{unit}，pp={_fmt(ch.get('peak_to_peak'))}{unit}"
            )

    return "\n".join(lines)


class PromptManager:
    def __init__(self, enable_log_masking: bool = True):
        self._providers: list[ContextProvider] = []
        self._enable_masking = enable_log_masking

    def add_provider(self, provider: ContextProvider) -> None:
        self._providers.append(provider)

    def _build_system_text(
        self, page_key: str | None, budget: BudgetConfig | None = None
    ) -> str:
        parts = [get_global_system_prompt().strip()]

        project_prompt = get_project_prompt()
        if project_prompt:
            parts.append(project_prompt)

        local_rules = _get_local_project_rules()
        if local_rules:
            parts.append(local_rules)

        profile = get_profile(page_key)
        profile_prompt = (profile.get("system_prompt") or "").strip()
        if profile_prompt:
            parts.append(profile_prompt)

        for nudge in page_nudges(page_key):
            text = nudge.get("text", "").strip()
            if text:
                parts.append(text)

        user_prompt = get_user_prompt()
        if user_prompt:
            parts.append(user_prompt)

        block_cap = budget.max_context_block_tokens if budget else 0
        for provider in self._providers:
            try:
                ctx = provider.build_context(page_key)
            except Exception:
                ctx = ""
            if ctx:
                ctx = ctx.strip()
                if block_cap > 0:
                    ctx = context_budget.clip_context_block(ctx, block_cap)
                parts.append(ctx)
        return "\n\n".join(p for p in parts if p)

    def build_messages(
        self,
        page_key: str | None,
        history: list[dict[str, str]],
        user_text: str,
        log_context: str = "",
        extra_context: str = "",
        budget: BudgetConfig | None = None,
        summary: str = "",
        waveform_context: str = "",
    ) -> list[dict[str, str]]:
        """组装 OpenAI 兼容 messages。

        history: 既有对话（不含本轮 user_text），形如 [{"role","content"}, ...]。
        log_context: 可选最近日志文本，作为附加 system 提示注入。
        extra_context: 可选附加上下文，作为附加 system 提示注入。
        budget: 可选 token 预算配置；提供时按当前模型窗口裁剪历史，止住上下文膨胀。
        summary: 可选前情提要（Phase 6），作为 [前情提要] system 段注入会话头。
        waveform_context: 可选波形摘要（F1），紧邻本轮 user 消息注入并附时效声明，
            确保新的 Marker / 可见范围数据优先于历史中的旧波形结论。
        """
        system_text = self._build_system_text(page_key, budget)
        block_cap = budget.max_context_block_tokens if budget else 0
        wave_cap = budget.waveform_block_tokens if budget else 0
        if summary:
            summ = mask_sensitive(summary) if self._enable_masking else summary
            system_text += "\n\n[前情提要]\n" + summ
        if log_context:
            ctx = mask_sensitive(log_context) if self._enable_masking else log_context
            if block_cap > 0:
                ctx = context_budget.clip_context_block(ctx, block_cap)
            system_text += "\n\n[最近运行日志，供参考]\n" + ctx
        if extra_context:
            ctx = mask_sensitive(extra_context) if self._enable_masking else extra_context
            if block_cap > 0:
                ctx = context_budget.clip_context_block(ctx, block_cap)
            system_text += "\n\n" + ctx

        messages: list[dict[str, str]] = [{"role": "system", "content": system_text}]
        for item in history:
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        text = mask_sensitive(user_text) if self._enable_masking else user_text
        if waveform_context:
            wave = (
                mask_sensitive(waveform_context)
                if self._enable_masking
                else waveform_context
            )
            if wave_cap > 0:
                wave = context_budget.clip_context_block(wave, wave_cap)
            text = (
                "【本轮波形数据（最新，以此为准）】\n"
                "以下为当前 Marker / 屏幕可见范围对应的波形数据；"
                "若与此前对话中的波形数值或结论冲突，一律以本段为准，忽略历史中的旧波形数据。\n"
                f"{wave}\n\n"
                "【我的问题】\n"
                f"{text}"
            )
        messages.append({"role": "user", "content": text})

        if budget is not None:
            messages = context_budget.fit_messages(
                messages,
                window=budget.window,
                reserve_output=budget.reserve_output,
                soft_budget_ratio=budget.soft_budget_ratio,
            )
        return messages

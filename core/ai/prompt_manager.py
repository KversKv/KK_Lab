"""PromptManager：拼装发送给模型的 messages。

组成（system 段）：
  全局 system prompt + 当前 Profile system_prompt + 各 ContextProvider 上下文。
可选附加最近运行日志（由调用方按需传入，已脱敏）。
"""
from __future__ import annotations

import re

from core.ai.profiles import get_global_system_prompt, get_profile
from core.ai.providers.base import ContextProvider

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
        if stat.anomalies:
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

    if include_downsampled and getattr(digest, "downsampled", None):
        lines.append("[降采样形状点（LTTB，仅供观察趋势，非原始精度）]")
        for label, series in digest.downsampled.items():
            times = series.get("time", [])
            values = series.get("values", [])
            pairs = ", ".join(
                f"({_fmt(t)},{_fmt(v)})" for t, v in zip(times, values)
            )
            lines.append(f"- {label}: {pairs}")

    return "\n".join(lines)


class PromptManager:
    def __init__(self, enable_log_masking: bool = True):
        self._providers: list[ContextProvider] = []
        self._enable_masking = enable_log_masking

    def add_provider(self, provider: ContextProvider) -> None:
        self._providers.append(provider)

    def _build_system_text(self, page_key: str | None) -> str:
        parts = [get_global_system_prompt().strip()]
        profile = get_profile(page_key)
        profile_prompt = (profile.get("system_prompt") or "").strip()
        if profile_prompt:
            parts.append(profile_prompt)
        for provider in self._providers:
            try:
                ctx = provider.build_context(page_key)
            except Exception:
                ctx = ""
            if ctx:
                parts.append(ctx.strip())
        return "\n\n".join(p for p in parts if p)

    def build_messages(
        self,
        page_key: str | None,
        history: list[dict[str, str]],
        user_text: str,
        log_context: str = "",
        extra_context: str = "",
    ) -> list[dict[str, str]]:
        """组装 OpenAI 兼容 messages。

        history: 既有对话（不含本轮 user_text），形如 [{"role","content"}, ...]。
        log_context: 可选最近日志文本，作为附加 system 提示注入。
        extra_context: 可选附加上下文（如波形摘要 F1），作为附加 system 提示注入。
        """
        system_text = self._build_system_text(page_key)
        if log_context:
            ctx = mask_sensitive(log_context) if self._enable_masking else log_context
            system_text += "\n\n[最近运行日志，供参考]\n" + ctx
        if extra_context:
            ctx = mask_sensitive(extra_context) if self._enable_masking else extra_context
            system_text += "\n\n" + ctx

        messages: list[dict[str, str]] = [{"role": "system", "content": system_text}]
        for item in history:
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        text = mask_sensitive(user_text) if self._enable_masking else user_text
        messages.append({"role": "user", "content": text})
        return messages

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
    ) -> list[dict[str, str]]:
        """组装 OpenAI 兼容 messages。

        history: 既有对话（不含本轮 user_text），形如 [{"role","content"}, ...]。
        log_context: 可选最近日志文本，作为附加 system 提示注入。
        """
        system_text = self._build_system_text(page_key)
        if log_context:
            ctx = mask_sensitive(log_context) if self._enable_masking else log_context
            system_text += "\n\n[最近运行日志，供参考]\n" + ctx

        messages: list[dict[str, str]] = [{"role": "system", "content": system_text}]
        for item in history:
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        text = mask_sensitive(user_text) if self._enable_masking else user_text
        messages.append({"role": "user", "content": text})
        return messages

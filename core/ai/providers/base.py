"""Context Provider 协议：向 PromptManager 提供拼装 prompt 所需的上下文片段。"""
from __future__ import annotations

from abc import ABC, abstractmethod


class ContextProvider(ABC):
    """上下文提供者基类。

    实现者按需返回一段纯文本上下文（已做必要脱敏），由 PromptManager 拼到
    system / 附加消息中。返回空串表示当前无可提供上下文。
    """

    @abstractmethod
    def name(self) -> str:
        """provider 标识（用于日志与去重）。"""

    @abstractmethod
    def build_context(self, page_key: str | None) -> str:
        """根据当前页面键构建上下文文本（可为空串）。"""

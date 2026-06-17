"""AI 上下文 Provider 包（只读消费现有系统状态）。"""
from __future__ import annotations

from core.ai.providers.base import ContextProvider
from core.ai.providers.log_provider import LogContextProvider
from core.ai.providers.page_provider import PageContextProvider
from core.ai.providers.sequence_provider import SequenceContextProvider
from core.ai.providers.serial_provider import SerialContextProvider
from core.ai.providers.waveform_provider import (
    build_digest,
    lttb_downsample,
    slice_window,
)

__all__ = [
    "ContextProvider",
    "LogContextProvider",
    "PageContextProvider",
    "SequenceContextProvider",
    "SerialContextProvider",
    "build_digest",
    "lttb_downsample",
    "slice_window",
]

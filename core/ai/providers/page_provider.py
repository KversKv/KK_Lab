"""PageContextProvider：把"当前在哪个页面"翻译成简短上下文文本。

仅依赖一个轻量回调 page_key_getter（由 UI 层注入，读 MainWindow.current_instrument_ui
及导航子键），本类不直接 import ui，保持 core 不反向依赖 ui。
"""
from __future__ import annotations

from typing import Callable

from core.ai.providers.base import ContextProvider
from core.ai.profiles import get_profile

_PAGE_LABELS: dict[str, str] = {
    "power_analyser": "N6705C 电源分析仪",
    "datalog": "N6705C Datalog 数据记录",
    "oscilloscope": "示波器",
    "thermal_chamber": "VT6002 温箱",
    "pmu_test": "PMU 测试",
    "charger_test": "充电测试",
    "consumption_test": "功耗测试",
    "custom_test": "Custom Test 自定义测试",
    "vmin_hunter": "VminHunter",
    "kk_serials": "KK 串口工具",
    "collection": "Collection 集合页",
}


class PageContextProvider(ContextProvider):
    def __init__(self, page_key_getter: Callable[[], str | None]):
        self._getter = page_key_getter

    def name(self) -> str:
        return "page"

    def build_context(self, page_key: str | None) -> str:
        key = page_key if page_key is not None else self._getter()
        if not key:
            return ""
        label = _PAGE_LABELS.get(key, key)
        profile = get_profile(key)
        return f"当前页面：{label}（profile={profile.get('label', key)}）。"

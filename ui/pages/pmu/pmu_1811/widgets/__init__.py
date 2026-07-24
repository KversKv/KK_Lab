# -*- coding: utf-8 -*-
"""1811 PMU UI 层: 可复用控件集合。

包含:
- ToggleSwitch   : iOS 风格拨动开关
- ModuleCard     : 模块卡片 (LED + 名称 + 电压步进 + 齿轮)
- SwitchWidget   : SW 物理开关模型 (左右端点 + 动态连杆, 单击切换闭合/开路)
- DiagramCanvas  : 拓扑画布 (VSYS / 子母线 / 树状分支连线)
- PropertyPanel  : 属性面板 (使能/模式/电压/I2C/连接信息; SW 专属 Switch Controls)
- ContextMenu    : 右键菜单 (使能切换 + 模式选择)
"""

from ui.pages.pmu.pmu_1811.widgets.toggle_switch import ToggleSwitch
from ui.pages.pmu.pmu_1811.widgets.module_card import ModuleCard
from ui.pages.pmu.pmu_1811.widgets.switch_widget import SwitchWidget
from ui.pages.pmu.pmu_1811.widgets.diagram_canvas import DiagramCanvas
from ui.pages.pmu.pmu_1811.widgets.property_panel import PropertyPanel
from ui.pages.pmu.pmu_1811.widgets.context_menu import ContextMenu

__all__ = [
    "ToggleSwitch",
    "ModuleCard",
    "SwitchWidget",
    "DiagramCanvas",
    "PropertyPanel",
    "ContextMenu",
]

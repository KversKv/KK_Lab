# -*- coding: utf-8 -*-
"""KK'1811 PMU 配置工具包。

分层结构 (按 UI层 / 算法层 / 驱动中间层 分离):
- constants : 配色 / 字体 / 画布几何常量
- models    : 算法层 - PmuModule / LayoutRow / 拓扑布局 / 默认模块工厂
- workers   : 驱动中间层 - I2C 异步 Worker (QThread)
- widgets   : UI 层 - 可复用控件 (ToggleSwitch / ModuleCard / DiagramCanvas / PropertyPanel / ContextMenu)
- page      : UI 层 - 主页面 Pmu1811UI
"""

from ui.pages.pmu.pmu_1811.page import Pmu1811UI

__all__ = ["Pmu1811UI"]

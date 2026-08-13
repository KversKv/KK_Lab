"""CommandBar — Module Test 顶部命令条（ModuleTestUI 顶层，固定 48px）。

构成：
- ``Segmented``：LDO/DCDC 模块切换（对外发 ``moduleChanged(str)``）；
- 配置区：当前子页配置名 + 打开/保存/另存为（代理到当前子页）；
- ``StatusPill`` 组：N6705C / 示波器 / 温箱 连接态镜像 + 「连接设置」
  （滚动定位到左栏连接卡片）。

为什么这样拆：连接状态原本散落在两处文本标签，统一镜像到 CommandBar
后，切模块只需 ``bind_subpage`` 重绑信号，子页实现零感知。
"""
from __future__ import annotations

import os

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from ui.resource_path import get_resource_base
from ui.theme import current_theme
from ui.utils.icon_utils import tinted_svg_icon
from ui.widgets.segmented import Segmented
from ui.widgets.status_pill import StatusPill

_ICONS_DIR = os.path.join(get_resource_base(), "resources", "icons")


class CommandBar(QFrame):
    """顶部命令条。"""

    moduleChanged = Signal(str)          # "ldo" / "dcdc"
    openConfigRequested = Signal()
    saveConfigRequested = Signal()
    saveAsConfigRequested = Signal()
    connectionSettingsRequested = Signal()

    def __init__(self, items=(("ldo", "LDO"), ("dcdc", "DCDC")),
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("CommandBar")
        self.setFixedHeight(48)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(10)

        self.segmented = Segmented(items)
        self.segmented.currentChanged.connect(self._on_segment_changed)
        # 顶部不再显示 LDO/DCDC 切换（模块切换由左侧边栏导航驱动），
        # 保留 Segmented 实例以维持 current_module()/set_current_module() 契约。
        self.segmented.hide()
        lay.addWidget(self.segmented)

        # 页标题（纯展示；Segmented 隐藏后承担顶栏标识）
        self._title_label = QLabel("Module Test")
        self._title_label.setObjectName("commandBarTitle")
        lay.addWidget(self._title_label)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setObjectName("commandBarSep")
        sep1.hide()
        lay.addWidget(sep1)

        lay.addWidget(self._make_caption("配置:"))
        self.config_name_label = QLabel("（未加载）")
        self.config_name_label.setObjectName("configNameChip")
        self.config_name_label.setToolTip("当前生效的完整配置（设置 + 测试项）")
        lay.addWidget(self.config_name_label)

        self.open_btn = self._make_btn("打开", "按芯片分类浏览并加载已保存的配置（Ctrl+O）",
                                       self.openConfigRequested,
                                       icon="folder-open.svg")
        self.save_btn = self._make_btn("保存", "保存当前完整配置；已加载的配置直接覆盖（Ctrl+S）",
                                       self.saveConfigRequested,
                                       icon="save.svg")
        self.save_as_btn = self._make_btn("另存为", "基于当前设置生成新的配置文件",
                                          self.saveAsConfigRequested,
                                          icon="save-as.svg")
        lay.addWidget(self.open_btn)
        lay.addWidget(self.save_btn)
        lay.addWidget(self.save_as_btn)

        lay.addStretch()

        self.pill_n6705c = StatusPill("N6705C", "idle")
        self.pill_scope = StatusPill("示波器", "idle")
        self.pill_chamber = StatusPill("温箱", "idle")
        for pill in (self.pill_n6705c, self.pill_scope, self.pill_chamber):
            lay.addWidget(pill)

        self.conn_btn = self._make_btn("连接设置", "滚动到仪器连接区",
                                       self.connectionSettingsRequested,
                                       icon="settings.svg")
        lay.addWidget(self.conn_btn)

        self._subpage = None

    # ------------------------------------------------------------------ 构造
    @staticmethod
    def _make_caption(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("role", "caption")
        return lbl

    @staticmethod
    def _make_btn(text: str, tooltip: str, signal,
                  icon: str = "") -> QPushButton:
        btn = QPushButton(text)
        btn.setProperty("variant", "ghost")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip(tooltip)
        if icon:
            # 16px 线性图标，染色跟随次文本色（token 化）
            btn.setIcon(tinted_svg_icon(
                os.path.join(_ICONS_DIR, icon),
                current_theme().text_secondary, 16))
            btn.setIconSize(QSize(16, 16))
        btn.clicked.connect(signal.emit)
        return btn

    # ------------------------------------------------------------------ 模块切换
    def _on_segment_changed(self, key: str) -> None:
        self.moduleChanged.emit(key)

    def current_module(self) -> str:
        return self.segmented.current_key()

    def set_current_module(self, key: str, *, emit: bool = True) -> None:
        self.segmented.set_current_key(key, emit=emit)

    # ------------------------------------------------------------------ 子页绑定
    def bind_subpage(self, subpage) -> None:
        """绑定当前子页：连接状态镜像 + 配置名同步。"""
        if self._subpage is not None:
            try:
                self._subpage.connectionStateChanged.disconnect(self._refresh_pills)
            except (AttributeError, RuntimeError):
                pass
        self._subpage = subpage
        subpage.connectionStateChanged.connect(self._refresh_pills)
        self._refresh_pills()
        self.set_config_name(subpage.config_display_name())

    def _refresh_pills(self) -> None:
        sub = self._subpage
        if sub is None:
            return
        # N6705C
        n_ok = bool(getattr(sub, "is_connected", False))
        self.pill_n6705c.set_state("connected" if n_ok else "idle")
        n_addr = getattr(sub, "visa_resource_combo", None)
        self.pill_n6705c.set_tooltip(
            f"N6705C 直流电源分析仪\n{self._combo_text(n_addr) if n_ok else '未连接'}")
        # 示波器
        s_ok = bool(getattr(sub, "scope_connected", False))
        self.pill_scope.set_state("connected" if s_ok else "idle")
        s_addr = getattr(sub, "scope_resource_combo", None)
        self.pill_scope.set_tooltip(
            f"示波器\n{self._combo_text(s_addr) if s_ok else '未连接'}")
        # 温箱（本页测试流程暂未接入，仅展示）
        chamber = getattr(sub, "_chamber_ui", None)
        c_ok = bool(getattr(chamber, "is_connected", False)) if chamber else False
        self.pill_chamber.set_state("connected" if c_ok else "idle")
        self.pill_chamber.set_tooltip("温箱（Module Test 暂未接入测试流程）")

    @staticmethod
    def _combo_text(combo) -> str:
        try:
            return combo.currentText()
        except AttributeError:
            return ""

    # ------------------------------------------------------------------ 配置名
    def set_config_name(self, name: str) -> None:
        self.config_name_label.setText(name or "（未加载）")

    # ------------------------------------------------------------------ 运行态
    def set_running(self, running: bool) -> None:
        """运行中禁用模块切换与配置按钮（由子页 RunState 驱动）。"""
        self.segmented.setEnabled(not running)
        for btn in (self.open_btn, self.save_btn, self.save_as_btn,
                    self.conn_btn):
            btn.setEnabled(not running)

    def emit_open_later(self) -> None:
        """延迟发打开配置请求（供 Banner 动作复用）。"""
        QTimer.singleShot(0, self.openConfigRequested.emit)

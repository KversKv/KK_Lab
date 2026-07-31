"""preview_gallery — 组件库视觉走查页（设计评审 / 回归对比用）。

一个页面展示 P1 全部组件的各状态（idle/hover/focus/disabled/error/running），
支持暗/浅主题即时切换（``set_theme`` + 重挂 QSS + 全树 ``refresh_style``）。

运行：``python ui/dev/preview_gallery.py``
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from ui.theme import Theme, apply_qss, refresh_style, set_theme
from ui.models.result_model import LOG_KEY, STATUS_KEY
from ui.widgets.banner import InfoBanner
from ui.widgets.card import Card
from ui.widgets.empty_state import EmptyState
from ui.widgets.form import FormGrid
from ui.widgets.groups_editor import GroupColumn, GroupsTableEditor
from ui.widgets.log_panel import LogPanel
from ui.widgets.result_table import ResultTable
from ui.widgets.run_control_bar import RunControlBar, RunState
from ui.widgets.segmented import Segmented
from ui.widgets.status_pill import StatusPill
from ui.widgets.toast import Toast


def _section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setProperty("role", "caption")
    return lbl


class Gallery(QWidget):
    """组件走查窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("KK_Lab 组件库 Preview Gallery")
        self._dark = True

        root = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("主题:"))
        theme_btn = QPushButton("切换到 Light")
        theme_btn.setProperty("variant", "ghost")
        theme_btn.clicked.connect(lambda: self._toggle_theme(theme_btn))
        bar.addWidget(theme_btn)
        bar.addStretch()
        root.addLayout(bar)

        self._tabs = QTabWidget()
        root.addWidget(self._tabs, 1)
        self._build_tabs()
        self._apply_theme()

    # ------------------------------------------------------------------ 主题
    def _toggle_theme(self, btn: QPushButton) -> None:
        self._dark = not self._dark
        btn.setText("切换到 Light" if self._dark else "切换到 Dark")
        self._apply_theme()

    def _apply_theme(self) -> None:
        set_theme(Theme.dark() if self._dark else Theme.light())
        apply_qss(self, "controls")
        apply_qss(self, "table")
        for w in self.findChildren(QWidget):
            refresh_style(w)

    # ------------------------------------------------------------------ 页签
    def _build_tabs(self) -> None:
        self._tabs.addTab(self._tab_states(), "状态组件")
        self._tabs.addTab(self._tab_inputs(), "表单与容器")
        self._tabs.addTab(self._tab_run(), "运行控制")
        self._tabs.addTab(self._tab_data(), "数据组件")

    def _scroll(self, inner: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(inner)
        area.setFrameShape(QFrame.NoFrame)
        return area

    def _tab_states(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        lay.addWidget(_section("StatusPill — idle / connecting / connected / error / warning"))
        for st in ("idle", "connecting", "connected", "error", "warning"):
            lay.addWidget(StatusPill(f"N6705C · {st}", st,
                                     tooltip="TCPIP0::K-N6705C::hislip0\n型号 N6705C"))
        disabled_pill = StatusPill("禁用态", "connected")
        disabled_pill.setEnabled(False)
        lay.addWidget(disabled_pill)

        lay.addWidget(_section("Segmented"))
        lay.addWidget(Segmented([("ldo", "LDO"), ("dcdc", "DCDC")]))

        lay.addWidget(_section("InfoBanner — info / warning / error / success"))
        lay.addWidget(InfoBanner("尚未加载配置。", severity="info",
                                 actions=[("a", "选择配置"), ("b", "使用默认")]))
        lay.addWidget(InfoBanner("示波器未连接。", severity="warning"))
        lay.addWidget(InfoBanner("必填字段缺失：芯片名称。", severity="error"))
        lay.addWidget(InfoBanner("配置已保存。", severity="success"))

        lay.addWidget(_section("EmptyState"))
        lay.addWidget(EmptyState(title="暂无测试结果",
                                 hint="执行测试后结果显示在这里。",
                                 action=("开始测试", lambda: None)))

        lay.addWidget(_section("Toast（点击弹出，右下角 3s 消失）"))
        row = QHBoxLayout()
        for sev in ("info", "success", "warning", "error"):
            b = QPushButton(sev)
            b.clicked.connect(lambda _c=False, s=sev:
                              Toast.popup(self, f"{s} 提示示例", severity=s))
            row.addWidget(b)
        row.addStretch()
        lay.addLayout(row)
        lay.addStretch()
        return self._scroll(w)

    def _tab_inputs(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        lay.addWidget(_section("Card — 可折叠（动画 + QSettings 记忆）"))
        act = QPushButton("打开")
        act.setProperty("variant", "ghost")
        card = Card("DUT 配置", actions=[act], collapsible=True,
                    settings_key="gallery/dut")
        grid = FormGrid(columns=2)
        grid.add_row("芯片名称", QLineEdit("BES1307"), required=True)
        err_edit = QLineEdit("0xZZ")
        err_row = grid.add_row("Device 地址", err_edit, helper="如 0x62", required=True)
        grid.add_row("Vout 标称", QSpinBox(), unit="mV")
        combo = QComboBox()
        combo.addItems(["CH 1", "CH 2", "CH 3", "CH 4"])
        grid.add_row("Vin 通道", combo)
        err_row.set_error("地址格式无效，应为 0x 开头的十六进制")
        card.content_layout.addWidget(grid)
        lay.addWidget(card)

        lay.addWidget(_section("FormGrid — 行内校验（红边 + helper 红字）"))
        disabled_edit = QLineEdit("禁用输入")
        disabled_edit.setEnabled(False)
        grid2 = FormGrid(columns=2)
        grid2.add_row("禁用字段", disabled_edit)
        focus_edit = QLineEdit("点击我查看 focus 边框")
        grid2.add_row("焦点演示", focus_edit)
        lay.addWidget(grid2)
        lay.addStretch()
        return self._scroll(w)

    def _tab_run(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(_section("RunControlBar — 各 RunState（点击下方按钮切换）"))
        bar = RunControlBar()
        bar.set_total_text("3/15")
        bar.set_current_item("当前: Load Transient")
        bar.set_timing(59, 130)
        bar.set_counts(8, 1, 0)
        bar.set_progress(42)
        lay.addWidget(bar)
        row = QHBoxLayout()
        for st in RunState:
            b = QPushButton(st.name)
            b.clicked.connect(lambda _c=False, s=st: bar.set_state(s))
            row.addWidget(b)
        row.addStretch()
        lay.addLayout(row)
        lay.addStretch()
        return self._scroll(w)

    def _tab_data(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        lay.addWidget(_section("ResultTable — 动态列 / 排序 / 双击定位 / 导出"))
        table = ResultTable()
        table.set_columns([(STATUS_KEY, "判定"), ("item", "测试项"),
                           ("vout_mv", "Vout (mV)"), ("vpp_mv", "Vpp (mV)")])
        table.set_rows([
            {STATUS_KEY: "PASS", "item": "Line Regulation", "vout_mv": 1801.2, "vpp_mv": 3.1, LOG_KEY: "ldo_line_reg"},
            {STATUS_KEY: "FAIL", "item": "Load Transient", "vout_mv": 1750.0, "vpp_mv": 45.2, LOG_KEY: "ldo_load_transient"},
            {STATUS_KEY: "N/A", "item": "Quiescent", "vout_mv": 1800.0, "vpp_mv": 0, LOG_KEY: "ldo_quiescent"},
        ])
        lay.addWidget(table, 1)

        lay.addWidget(_section("GroupsTableEditor — 校验 / 拖拽排序 / TSV 粘贴"))
        cols = [
            GroupColumn("i0_ma", "I0", "mA", 0.0, 500.0, 1, 10.0),
            GroupColumn("i1_ma", "I1", "mA", 0.0, 500.0, 1, 100.0),
            GroupColumn("freq_hz", "频率", "Hz", 0.1, 10000.0, 1, 100.0),
        ]
        editor = GroupsTableEditor(cols, prefill=[
            {"i0_ma": 5, "i1_ma": 50, "freq_hz": 10},
            {"i0_ma": 10, "i1_ma": 100, "freq_hz": 100},
        ])
        lay.addWidget(editor, 1)

        lay.addWidget(_section("LogPanel — 批量 flush / 右键菜单 / 行数上限"))
        panel = LogPanel()
        panel.append_log("[INFO] Gallery 启动")
        panel.append_log("[WARN] 示例警告")
        panel.append_log("[ERROR] 示例错误")
        lay.addWidget(panel, 1)
        return w


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gallery = Gallery()
    gallery.resize(960, 720)
    gallery.show()
    sys.exit(app.exec())

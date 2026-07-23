# -*- coding: utf-8 -*-
"""1811 PMU 配置工具主页面 (UI 层入口)。

图形化配置 1811 PMIC：通过 USB 转 I2C（设备地址 0x17，10 位寄存器地址，16 位数据）
控制各 LDO / BUCK 的使能、模式与输出电压。

已接入真实 I2C 读写: 连接后 UI 操作经 QThread 异步下发到硬件。
"""

import os
import sys

if not getattr(sys, "frozen", False):
    _PROJECT_ROOT = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from PySide6.QtCore import Qt, QPoint, QThread, QTimer
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QScrollArea,
)

from log_config import get_logger

from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from ui.pages.pmu.pmu_1811.constants import (
    COL_CANVAS_BG, COL_PANEL_BG, COL_CARD_BG, COL_BORDER, COL_BORDER_HOVER, COL_EMERALD,
    COL_EMERALD_SOFT, COL_TEXT, COL_TEXT_MUTED, FONT_MONO,
)
from ui.pages.pmu.pmu_1811.models import _default_modules, get_pair_partner
from ui.pages.pmu.pmu_1811.widgets import DiagramCanvas, PropertyPanel, ContextMenu

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 主页面
# ---------------------------------------------------------------------------
class Pmu1811UI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pmu1811Page")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            f"QWidget#pmu1811Page {{ background:{COL_CANVAS_BG}; }}"
            f"QLabel {{ background:transparent; border:none; color:{COL_TEXT}; }}"
            f"QScrollBar:vertical {{ background:{COL_CANVAS_BG}; width:10px; margin:0; }}"
            f"QScrollBar::handle:vertical {{ background:{COL_BORDER};"
            f" min-height:30px; border-radius:4px; }}"
            f"QScrollBar::handle:vertical:hover {{ background:{COL_BORDER_HOVER}; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}"
            f"QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:transparent; }}"
            f"QScrollBar:horizontal {{ background:{COL_CANVAS_BG}; height:10px; margin:0; }}"
            f"QScrollBar::handle:horizontal {{ background:{COL_BORDER};"
            f" min-width:30px; border-radius:4px; }}"
            f"QScrollBar::handle:horizontal:hover {{ background:{COL_BORDER_HOVER}; }}"
            f"QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width:0; }}"
            f"QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background:transparent; }}"
            f"QDoubleSpinBox, QSpinBox {{ background:{COL_CARD_BG};"
            f" border:1px solid {COL_BORDER_HOVER}; border-radius:6px;"
            f" padding:4px 8px; color:{COL_TEXT};"
            f" selection-background-color:{COL_EMERALD}; selection-color:#06281d; }}"
            f"QDoubleSpinBox:focus, QSpinBox:focus {{ border:1px solid {COL_EMERALD}; }}"
            f"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,"
            f" QSpinBox::up-button, QSpinBox::down-button {{ width:0; height:0; border:none; }}"
            f"QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow,"
            f" QSpinBox::up-arrow, QSpinBox::down-arrow {{ width:0; height:0; }}"
        )

        self._modules = _default_modules()
        self._selected_id: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_chip_config())

        body_container = QWidget(self)
        body = QHBoxLayout(body_container)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.canvas = DiagramCanvas(self._modules, self)
        self.scroll = QScrollArea(self)
        self.scroll.setWidget(self.canvas)
        self.scroll.setWidgetResizable(False)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setStyleSheet(
            f"QScrollArea {{ background:{COL_CANVAS_BG}; border:none; }}"
            f"QScrollArea > QWidget > QWidget {{ background:{COL_CANVAS_BG}; }}"
        )
        body.addWidget(self.scroll, 1)

        self.panel = PropertyPanel(self)
        self.panel.setVisible(False)
        body.addWidget(self.panel)

        self.splitter, self.execution_logs = ExecutionLogsFrame.wrap_with(
            body_container, title="1811 PMU Logs", show_progress=False,
            stretch=(5, 1),
        )
        root.addWidget(self.splitter, 1)

        self.menu = ContextMenu(self)

        # I2C 连接状态与 Worker 线程
        self._i2c_connected = False
        self._dll_path = None       # None → 使用默认 DLL
        self._speed_mode = None     # None → 默认 100K
        self._worker_thread = None
        self._worker = None

        # 信号连接
        self.canvas.module_selected.connect(self._on_select)
        self.canvas.module_right_clicked.connect(self._on_context)
        self.canvas.voltage_stepped.connect(self._on_card_voltage)
        self.panel.enable_changed.connect(self._on_panel_enable)
        self.panel.mode_changed.connect(self._on_panel_mode)
        self.panel.voltage_changed.connect(self._on_panel_voltage)
        self.panel.voltage_dsleep_changed.connect(self._on_panel_voltage_dsleep)
        self.panel.voltage_rc_changed.connect(self._on_panel_voltage_rc)
        self.menu.enable_toggled.connect(self._on_menu_enable)
        self.menu.mode_changed.connect(self._on_menu_mode)

        # 首次显示后自动触发一次状态同步 (读取 DUT 实际使能/电压)
        self._first_shown = False

    def showEvent(self, event):
        super().showEvent(event)
        if not self._first_shown:
            self._first_shown = True
            # 延迟到事件循环下一轮, 确保 UI 完全布局后再发起 I2C 读取
            QTimer.singleShot(0, self._on_check)

    # ---- 头部 ----
    def _build_header(self) -> QFrame:
        header = QFrame(self)
        header.setFixedHeight(56)
        header.setStyleSheet(
            f"QFrame {{ background:{COL_PANEL_BG}; border-bottom:1px solid {COL_BORDER}; }}"
        )
        h = QHBoxLayout(header)
        h.setContentsMargins(20, 0, 20, 0)
        h.setSpacing(12)

        icon_lbl = QLabel("▣", header)
        icon_lbl.setStyleSheet(f"color:{COL_EMERALD}; font-size:18px;")
        title = QLabel("KK'1811 PMU Configuration Tool", header)
        title.setStyleSheet(f"color:{COL_TEXT}; font-size:15px; font-weight:700;")
        h.addWidget(icon_lbl)
        h.addWidget(title)
        h.addStretch(1)

        info = QLabel("DUT: 1811  |  I2C: 0x17", header)
        info.setStyleSheet(f"color:{COL_TEXT_MUTED}; font-family:{FONT_MONO}; font-size:12px;")
        h.addWidget(info)

        self.check_btn = QPushButton("Check", header)
        self.check_btn.setObjectName("checkBtn")
        self.check_btn.setCursor(Qt.PointingHandCursor)
        self.check_btn.setStyleSheet(
            f"QPushButton#checkBtn {{ background:{COL_EMERALD_SOFT}; color:{COL_EMERALD};"
            f" border:1px solid {COL_EMERALD}; border-radius:6px;"
            f" padding:6px 16px; font-weight:700; font-size:12px; }}"
            f"QPushButton#checkBtn:hover {{ background:{COL_EMERALD}; color:#06281d; }}"
        )
        self.check_btn.clicked.connect(self._on_check)
        h.addWidget(self.check_btn)
        return header

    def _build_chip_config(self) -> QFrame:
        """顶部 Chip Config 操作区: Auto / Force Normal / Force RC / Force Sleep。

        功能留空, 后续实现; 当前点击仅记录一条 WARN 日志。
        """
        frame = QFrame(self)
        frame.setStyleSheet(
            f"QFrame {{ background:{COL_PANEL_BG}; border-bottom:1px solid {COL_BORDER}; }}"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(20, 8, 20, 8)
        lay.setSpacing(8)

        title = QLabel("Chip Config", frame)
        title.setStyleSheet(
            f"color:{COL_TEXT_MUTED}; font-size:11px; font-weight:700;"
            f" letter-spacing:0.5px;"
        )
        lay.addWidget(title)
        lay.addSpacing(8)

        for name in ("Auto", "Force Normal", "Force RC", "Force Sleep"):
            btn = QPushButton(name, frame)
            btn.setObjectName("chipCfgBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setStyleSheet(
                f"QPushButton#chipCfgBtn {{ background:{COL_CARD_BG}; color:{COL_TEXT_MUTED};"
                f" border:1px solid {COL_BORDER}; border-radius:6px;"
                f" padding:5px 12px; font-size:11px; }}"
                f"QPushButton#chipCfgBtn:hover {{ border:1px solid {COL_BORDER_HOVER};"
                f" color:{COL_TEXT}; }}"
            )
            btn.clicked.connect(lambda _=False, n=name: self._on_chip_config(n))
            lay.addWidget(btn)
        lay.addStretch(1)
        return frame

    def _on_chip_config(self, name: str):
        """Chip Config 按钮占位: 功能后续实现。"""
        logger.debug("1811 PMU: Chip Config '%s' (未实现)", name)
        self._log("WARN", f"Chip Config '{name}' 暂未实现")

    def _log(self, level: str, message: str):
        """追加一条 LOG 到执行日志面板 (level 用于上色, 如 STEP/INFO/WARN/ERROR/PASS)。"""
        self.execution_logs.append_log(f"[{level}] {message}")

    def _on_check(self):
        """Check 按钮: 校验 Chip ID → 读取全部 LDO + BUCK 状态 → PMU 初始化。"""
        if self._worker_thread is not None:
            logger.warning("1811 PMU: 上一次操作尚未完成")
            self._log("WARN", "上一次操作尚未完成, 请稍候")
            return
        self._log("STEP", "开始 Check: 校验 Chip ID → 读取状态 → PMU 初始化 (I2C 0x17)...")
        self.check_btn.setEnabled(False)
        self.check_btn.setText("Reading...")
        from ui.pages.pmu.pmu_1811.workers import LdoReadAllWorker
        self._worker = LdoReadAllWorker(
            dll_path=self._dll_path, speed_mode=self._speed_mode)
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)
        self._worker.finished.connect(self._on_read_all_done)
        self._worker.error.connect(self._on_i2c_error)
        self._worker.log.connect(self.execution_logs.append_log)
        self._worker_thread.started.connect(self._worker.run)
        self._worker_thread.start()

    def _on_read_all_done(self, states: dict):
        """读取全部 LDO + BUCK 完成, 刷新 UI。

        ``states`` 的值可能是 ``LdoState`` (含 lp_dr/res_sel_dr) 或 ``BuckState``,
        两者都有 ``enabled`` / ``mode`` / ``voltage*`` 字段。
        """
        self._cleanup_worker()
        self._i2c_connected = True
        for ldo_id, st in states.items():
            mod = self._modules.get(ldo_id)
            if mod is None:
                continue
            mod.enabled = st.enabled
            mod.mode = st.mode if st.mode in ("Normal", "LP") else "Normal"
            if st.voltage is not None:
                mod.voltage = st.voltage
            if getattr(st, "voltage_dsleep", None) is not None:
                mod.voltage_dsleep = st.voltage_dsleep
            if getattr(st, "voltage_rc", None) is not None:
                mod.voltage_rc = st.voltage_rc
            self.canvas.refresh_card(ldo_id)
        if self._selected_id and self._selected_id in self._modules:
            self.panel.load(self._modules[self._selected_id])
        logger.info("1811 PMU: Check 完成, %d 个模块", len(states))
        on_cnt = sum(1 for s in states.values() if s.enabled)
        self._log("PASS", f"Check 完成: 读取 {len(states)} 个模块 ({on_cnt} 个已开启), PMU 初始化完成")

    def _on_i2c_error(self, msg: str):
        """I2C 操作出错。"""
        self._cleanup_worker()
        self._i2c_connected = False
        logger.error("1811 PMU I2C 错误: %s", msg)
        self._log("ERROR", f"I2C 错误: {msg}")

    def _cleanup_worker(self):
        """清理 Worker 线程。"""
        if self._worker_thread is not None:
            self._worker_thread.quit()
            self._worker_thread.wait()
            self._worker_thread = None
            self._worker = None
        self.check_btn.setEnabled(True)
        self.check_btn.setText("Check")

    # ---- 异步写入 ----
    def _start_write(self, ldo_id: str, action: str, value):
        """启动异步写入 (若已连接)。"""
        if not self._modules[ldo_id].controllable:
            return
        if not self._i2c_connected:
            logger.debug("1811 PMU: 未连接, 仅本地更新 %s", ldo_id)
            return
        if self._worker_thread is not None:
            logger.warning("1811 PMU:忙碌, 丢弃 %s/%s", ldo_id, action)
            self._log("WARN", f"忙碌, 丢弃写入 {ldo_id}/{action}")
            return
        self._log("STEP", f"写入 {ldo_id} {action}={value}")
        from ui.pages.pmu.pmu_1811.workers import LdoWriteWorker
        self._worker = LdoWriteWorker(
            ldo_id, action, value,
            dll_path=self._dll_path, speed_mode=self._speed_mode,
        )
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)
        self._worker.finished.connect(self._on_write_done)
        self._worker.error.connect(self._on_i2c_error)
        self._worker.log.connect(self.execution_logs.append_log)
        self._worker_thread.started.connect(self._worker.run)
        self._worker_thread.start()

    def _on_write_done(self, ldo_id: str):
        """单次写入完成。"""
        self._cleanup_worker()
        self._log("PASS", f"{ldo_id} 写入完成")

    # ---- 并联对偶使能互锁 ----
    def _start_enable_write(self, mod_id: str, enabled: bool):
        """使能写入入口: 处理 BUCK↔LDO 并联对偶的互斥使能。

        开启某模块时, 若存在对偶伙伴, 则在同一 I2C 会话内先开自己再关对偶;
        关闭某模块时不影响对偶 (用户可自由关闭)。
        """
        partner = get_pair_partner(mod_id)
        if enabled and partner:
            self._start_pair_write(mod_id, partner)
        else:
            self._start_write(mod_id, "enable", enabled)

    def _start_pair_write(self, primary_id: str, partner_id: str):
        """启动对偶互锁写入 (开主模块 + 关对偶), 一次 I2C 会话完成。"""
        if not self._i2c_connected:
            logger.debug("1811 PMU: 未连接, 仅本地更新 %s (含对偶 %s)",
                         primary_id, partner_id)
            self._apply_local_disable(partner_id)
            return
        if self._worker_thread is not None:
            logger.warning("1811 PMU: 忙碌, 丢弃 %s/enable (对偶 %s)",
                           primary_id, partner_id)
            self._log("WARN", f"忙碌, 丢弃写入 {primary_id}/enable")
            return
        self._log("STEP", f"开启 {primary_id} 并关闭对偶 {partner_id} (互锁)")
        from ui.pages.pmu.pmu_1811.workers import PairWriteWorker
        self._worker = PairWriteWorker(
            primary_id, partner_id, True,
            dll_path=self._dll_path, speed_mode=self._speed_mode,
        )
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)
        self._worker.finished.connect(self._on_pair_write_done)
        self._worker.error.connect(self._on_i2c_error)
        self._worker.log.connect(self.execution_logs.append_log)
        self._worker_thread.started.connect(self._worker.run)
        self._worker_thread.start()

    def _on_pair_write_done(self, primary_id: str, partner_id: str):
        """对偶互锁写入完成: 同步本地状态 (关闭对偶) 并刷新 UI。"""
        self._cleanup_worker()
        self._apply_local_disable(partner_id)
        self._log("PASS", f"{primary_id} 开启完成, 对偶 {partner_id} 已关闭 (互锁)")

    def _apply_local_disable(self, mod_id: str):
        """本地关闭某模块 (对偶互锁的副效果), 并刷新卡片与属性面板。"""
        mod = self._modules.get(mod_id)
        if mod is None:
            return
        mod.enabled = False
        self.canvas.refresh_card(mod_id)
        if mod_id == self._selected_id:
            self.panel.load(mod)

    # ---- 选择 ----
    def _on_select(self, mod_id: str):
        if not mod_id:
            self._selected_id = None
            self.canvas.clear_selection()
            self.panel.setVisible(False)
            return
        self._selected_id = mod_id
        self.canvas.set_selected(mod_id)
        self.panel.load(self._modules[mod_id])
        self.panel.setVisible(True)

    def _on_context(self, mod_id: str, pos: QPoint):
        self.menu.popup(self._modules[mod_id], pos)

    # ---- 状态联动 ----
    def _on_card_voltage(self, mod_id: str, v: float):
        # 卡片 +/- 按钮调整电压: 同步刷新属性面板并写入 DUT
        if mod_id == self._selected_id:
            self.panel.load(self._modules[mod_id])
        self._start_write(mod_id, "voltage", v)

    def _on_panel_enable(self, mod_id: str, enabled: bool):
        self.canvas.refresh_card(mod_id)
        if mod_id == self._selected_id:
            self.panel._refresh_i2c()
        self._start_enable_write(mod_id, enabled)

    def _on_panel_mode(self, mod_id: str, mode: str):
        self.canvas.refresh_card(mod_id)
        self._start_write(mod_id, "mode", mode)

    def _on_panel_voltage(self, mod_id: str, v: float):
        self.canvas.refresh_card(mod_id)
        self._start_write(mod_id, "voltage", v)

    def _on_panel_voltage_dsleep(self, mod_id: str, v: float):
        # dsleep / rc 电压不影响卡片显示 (卡片只显示 normal), 仅写入 DUT
        self._start_write(mod_id, "voltage_dsleep", v)

    def _on_panel_voltage_rc(self, mod_id: str, v: float):
        self._start_write(mod_id, "voltage_rc", v)

    def _on_menu_enable(self, mod_id: str):
        mod = self._modules[mod_id]
        mod.enabled = not mod.enabled
        self.canvas.refresh_card(mod_id)
        if mod_id == self._selected_id:
            self.panel.load(mod)
        self._start_enable_write(mod_id, mod.enabled)

    def _on_menu_mode(self, mod_id: str, mode: str):
        mod = self._modules[mod_id]
        mod.mode = mode
        self.canvas.refresh_card(mod_id)
        if mod_id == self._selected_id:
            self.panel.load(mod)
        self._start_write(mod_id, "mode", mode)


if __name__ == "__main__":
    """独立预览 1811 PMU 配置工具界面。"""
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = Pmu1811UI()
    window.setWindowTitle("KK'1811 PMU Configuration Tool")
    window.resize(1080, 720)
    window.show()
    sys.exit(app.exec())

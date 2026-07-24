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

from PySide6.QtCore import Qt, QPoint, QPointF, QSize, QRectF, QThread, QTimer
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QScrollArea,
)

from log_config import get_logger

from ui.resource_path import get_resource_base
from ui.utils.icon_utils import svg_pixmap

from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from ui.pages.pmu.pmu_1811.constants import (
    COL_CANVAS_BG, COL_PANEL_BG, COL_CARD_BG, COL_BORDER, COL_BORDER_HOVER, COL_EMERALD,
    COL_EMERALD_SOFT, COL_TEXT, COL_TEXT_MUTED, FONT_MONO,
)
from ui.pages.pmu.pmu_1811.models import _default_modules, get_pair_partner
from ui.pages.pmu.pmu_1811.widgets import DiagramCanvas, PropertyPanel, ContextMenu

logger = get_logger(__name__)

_PMU_ICON_SVG = os.path.join(
    get_resource_base(), "resources", "pages", "pmu_1811_SVGs", "pmu_1811.svg"
)


# ---------------------------------------------------------------------------
# Check 失败时的画布禁用遮罩
# ---------------------------------------------------------------------------
class _BlockedOverlay(QWidget):
    """半透明遮罩: 盖住画布+属性面板, 拦截全部交互, 中央提示未连接。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.ForbiddenCursor)
        self.setStyleSheet(
            "QWidget { background: rgba(3, 7, 18, 190); border:none; }"
            "QLabel { background:transparent; border:none; }"
        )
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(6)
        title = QLabel("DUT 未连接", self)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color:{COL_TEXT}; font-size:15px; font-weight:700;")
        hint = QLabel("画布已禁用, 请点击右上角 Check 重新连接", self)
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(f"color:{COL_TEXT_MUTED}; font-size:12px;")
        lay.addWidget(title)
        lay.addWidget(hint)

    def mousePressEvent(self, event):
        # 吞掉点击, 不穿透到画布
        event.accept()


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
        self._body_container = body_container
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
        self.canvas.enable_toggled.connect(self._on_card_enable)
        self.panel.enable_changed.connect(self._on_panel_enable)
        self.panel.mode_changed.connect(self._on_panel_mode)
        self.panel.voltage_changed.connect(self._on_panel_voltage)
        self.panel.voltage_dsleep_changed.connect(self._on_panel_voltage_dsleep)
        self.panel.voltage_rc_changed.connect(self._on_panel_voltage_rc)
        self.menu.enable_toggled.connect(self._on_menu_enable)
        self.menu.mode_changed.connect(self._on_menu_mode)

        # 首次显示后自动触发一次状态同步 (读取 DUT 实际使能/电压)
        self._first_shown = False

        # Check 失败时的"禁止使用"遮罩 (覆盖画布+属性面板, 阻止交互)
        self._blocked_overlay = None

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
            # 按模块允许的模式校验: BUCK 支持 Normal/LP/ULP, LDO 支持 Normal/LP
            mod.mode = st.mode if st.mode in mod.modes else "Normal"
            if st.voltage is not None:
                mod.voltage = st.voltage
            if getattr(st, "voltage_dsleep", None) is not None:
                mod.voltage_dsleep = st.voltage_dsleep
            if getattr(st, "voltage_rc", None) is not None:
                mod.voltage_rc = st.voltage_rc
            self.canvas.refresh_card(ldo_id)
        # SW 状态可能被上方主动写入改变, 兜底刷新全部 SW 卡片 (未读到的按本地默认)
        for mod_id, mod in self._modules.items():
            if mod.type == "SW":
                self.canvas.refresh_card(mod_id)
        if self._selected_id and self._selected_id in self._modules:
            self.panel.load(self._modules[self._selected_id])
        logger.info("1811 PMU: Check 完成, %d 个模块", len(states))
        on_cnt = sum(1 for s in states.values() if s.enabled)
        self._log("PASS", f"Check 完成: 读取 {len(states)} 个模块 ({on_cnt} 个已开启), PMU 初始化完成")
        self._set_body_blocked(False)

    def _on_i2c_error(self, msg: str):
        """I2C 操作出错 (含 Check 失败): 锁定画布, 禁止使用。"""
        self._cleanup_worker()
        self._i2c_connected = False
        logger.error("1811 PMU I2C 错误: %s", msg)
        self._log("ERROR", f"I2C 错误: {msg}")
        self._set_body_blocked(True)

    # ---- 画布禁用遮罩 (Check 失败后禁止使用) ----
    def _set_body_blocked(self, blocked: bool):
        """切换画布+属性面板的禁用遮罩。

        blocked=True: 半透明遮罩盖住画布与属性面板并拦截交互 (提示未连接);
        blocked=False: 移除遮罩恢复可操作。
        """
        if blocked:
            if self._blocked_overlay is None:
                self._blocked_overlay = _BlockedOverlay(self._body_container)
            self._blocked_overlay.setGeometry(self._body_container.rect())
            self._blocked_overlay.show()
            self._blocked_overlay.raise_()
        elif self._blocked_overlay is not None:
            self._blocked_overlay.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._blocked_overlay is not None and self._blocked_overlay.isVisible():
            self._blocked_overlay.setGeometry(self._body_container.rect())

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

    def _on_card_enable(self, mod_id: str):
        """SW 卡片内开关拨动: 同步属性面板并写入 DUT (闭合/开路)。"""
        mod = self._modules[mod_id]
        if mod_id == self._selected_id:
            self.panel.load(mod)
        self._start_enable_write(mod_id, mod.enabled)

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


# ---------------------------------------------------------------------------
# 独立预览: 无边框壳 + 自绘标题栏 (参考 main 窗口, 替代系统标题栏以适配主题)
# ---------------------------------------------------------------------------
def _caption_icon(kind: str, color: str, size: int = 12) -> QIcon:
    """绘制窗口控制图标 (细线条 1px 描边, 颜色随 1811 主题)。"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidthF(1.0)
    pen.setCosmetic(True)
    painter.setPen(pen)

    pad = 1.5
    x0, y0 = pad, pad
    x1, y1 = size - pad, size - pad
    cy = size / 2.0
    if kind == "min":
        painter.drawLine(QPointF(x0, cy), QPointF(x1, cy))
    elif kind == "max":
        painter.drawRect(QRectF(x0, y0, x1 - x0, y1 - y0))
    elif kind == "restore":
        off = 3.0
        painter.drawRect(QRectF(x0, y0 + off, (x1 - x0) - off, (y1 - y0) - off))
        painter.drawLine(QPointF(x0 + off, y0), QPointF(x1, y0))
        painter.drawLine(QPointF(x1, y0), QPointF(x1, y1 - off))
    elif kind == "close":
        painter.drawLine(QPointF(x0, y0), QPointF(x1, y1))
        painter.drawLine(QPointF(x1, y0), QPointF(x0, y1))
    painter.end()
    return QIcon(pixmap)


class _PreviewTitleBar(QWidget):
    """独立预览壳的自绘标题栏 (1811 主题色: 图标 + 标题 + min/max/close)。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("previewTitleBar")
        # 纯 QWidget 默认不绘制 QSS 背景, 必须置此属性 (否则露 Fusion 白底)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(32)
        self.setStyleSheet(
            f"QWidget#previewTitleBar {{ background:{COL_PANEL_BG};"
            f" border-bottom:1px solid {COL_BORDER}; }}"
            f"QWidget#previewTitleBar QLabel {{ background:transparent; border:none; }}"
            f"QPushButton#pvCtrlBtn, QPushButton#pvCloseBtn {{"
            f" min-width:40px; max-width:40px; min-height:32px; max-height:32px;"
            f" padding:0; border:none; border-radius:0; background:transparent; }}"
            f"QPushButton#pvCtrlBtn:hover {{ background:{COL_CARD_BG}; }}"
            f"QPushButton#pvCloseBtn:hover {{ background:#e81123; }}"
        )
        self._maximized = False
        self._normal_geom = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 0, 0)
        lay.setSpacing(8)

        icon = QLabel(self)
        icon.setFixedSize(16, 16)
        icon.setPixmap(svg_pixmap(_PMU_ICON_SVG, 16))
        lay.addWidget(icon, 0, Qt.AlignVCenter)

        title = QLabel("KK'1811 PMU Configuration Tool", self)
        title.setStyleSheet(f"color:{COL_TEXT}; font-size:12px; font-weight:600;")
        lay.addWidget(title, 0, Qt.AlignVCenter)
        lay.addStretch(1)

        self._add_btn(lay, "pvCtrlBtn", "min", "最小化", self._on_min)
        self._max_btn = self._add_btn(lay, "pvCtrlBtn", "max", "最大化", self._on_toggle_max)
        self._add_btn(lay, "pvCloseBtn", "close", "关闭", self._on_close)

    def _add_btn(self, lay, obj_name, kind, tooltip, slot):
        btn = QPushButton(self)
        btn.setObjectName(obj_name)
        btn.setIcon(_caption_icon(kind, COL_TEXT_MUTED))
        btn.setIconSize(QSize(12, 12))
        btn.setToolTip(tooltip)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.clicked.connect(slot)
        lay.addWidget(btn, 0, Qt.AlignVCenter)
        return btn

    def _on_min(self):
        self.window().showMinimized()

    def _on_close(self):
        self.window().close()

    def _on_toggle_max(self):
        # frameless 窗口直接 showMaximized 会盖住任务栏, 改为在屏幕可用区几何间切换
        w = self.window()
        if self._maximized:
            if self._normal_geom is not None:
                w.setGeometry(self._normal_geom)
            self._maximized = False
        else:
            self._normal_geom = w.geometry()
            w.setGeometry(w.screen().availableGeometry())
            self._maximized = True
        self._max_btn.setIcon(
            _caption_icon("restore" if self._maximized else "max", COL_TEXT_MUTED))
        self._max_btn.setToolTip("还原" if self._maximized else "最大化")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self._maximized:
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemMove()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_toggle_max()
        super().mouseDoubleClickEvent(event)


# 边缘缩放手柄宽度 (px)
_RESIZE_MARGIN = 6


def _resize_edges(widget, pos, margin=_RESIZE_MARGIN):
    """按窗口内坐标命中缩放边缘, 返回 Qt.Edge 组合 (空 flag 表示不在边缘)。"""
    edges = Qt.Edge(0)
    if pos.x() <= margin:
        edges |= Qt.LeftEdge
    if pos.x() >= widget.width() - margin:
        edges |= Qt.RightEdge
    if pos.y() <= margin:
        edges |= Qt.TopEdge
    if pos.y() >= widget.height() - margin:
        edges |= Qt.BottomEdge
    return edges


def _apply_dwm_round_corners(window):
    """Windows 11 下给窗口启用 DWM 原生微弱圆角 (与主窗口一致); 不支持则忽略。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        # 33 = DWMWA_WINDOW_CORNER_PREFERENCE, 2 = DWMWCP_ROUND
        pref = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            int(window.winId()), 33, ctypes.byref(pref), ctypes.sizeof(pref))
    except Exception:  # noqa: BLE001 - 老系统无 DWM 圆角, 忽略
        logger.debug("DWM 圆角设置失败 (系统不支持, 忽略)", exc_info=True)


if __name__ == "__main__":
    """独立预览 1811 PMU 配置工具界面 (无边框 + 自绘标题栏)。"""
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication

    # 缩放边缘 → 光标形状 (未命中为 None → 还原箭头)
    _EDGE_CURSORS = {
        Qt.LeftEdge: Qt.SizeHorCursor,
        Qt.RightEdge: Qt.SizeHorCursor,
        Qt.TopEdge: Qt.SizeVerCursor,
        Qt.BottomEdge: Qt.SizeVerCursor,
        Qt.LeftEdge | Qt.TopEdge: Qt.SizeFDiagCursor,
        Qt.RightEdge | Qt.BottomEdge: Qt.SizeFDiagCursor,
        Qt.LeftEdge | Qt.BottomEdge: Qt.SizeBDiagCursor,
        Qt.RightEdge | Qt.TopEdge: Qt.SizeBDiagCursor,
    }

    def _shell_event_filter(obj, event):
        """frameless 壳的边缘缩放 (装在 QApplication 上, 覆盖子控件边缘)。

        鼠标在窗口边缘时实际落在子控件上, shell 自身收不到事件, 故过滤
        QApplication; 用 mapTo 换算到壳坐标判定边缘, 移动改光标 / 左键启动缩放。
        """
        # 过滤非本窗口或非 QWidget 对象 (QApplication 会收到 QWindow/QStyle 等)
        if not isinstance(obj, QWidget) or not (obj is shell or shell.isAncestorOf(obj)):
            return False
        et = event.type()
        if et == QEvent.MouseMove:
            pos = obj.mapTo(shell, event.position().toPoint())
            cursor = _EDGE_CURSORS.get(_resize_edges(shell, pos))
            # 光标直接设在悬停控件上 (override 光标会被各控件自身光标覆盖)
            obj.setCursor(cursor if cursor is not None else Qt.ArrowCursor)
        elif et == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            pos = obj.mapTo(shell, event.position().toPoint())
            edges = _resize_edges(shell, pos)
            handle = shell.windowHandle()
            if edges and handle is not None:
                handle.startSystemResize(edges)
                return True
        return False

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    shell = QWidget()
    shell.setObjectName("pmu1811PreviewShell")
    shell.setWindowTitle("KK'1811 PMU Configuration Tool")
    shell.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
    # frameless 无系统边框: 事件过滤器装到 QApplication 才能收到子控件上的边缘事件
    shell.setMouseTracking(True)
    app.installEventFilter(shell)
    # 壳本身也按暗色主题绘制, 避免重绘/留白处露默认白底
    shell.setAttribute(Qt.WA_StyledBackground, True)
    shell.setStyleSheet(
        f"QWidget#pmu1811PreviewShell {{ background:{COL_CANVAS_BG}; }}")
    shell_root = QVBoxLayout(shell)
    shell_root.setContentsMargins(0, 0, 0, 0)
    shell_root.setSpacing(0)
    shell_root.addWidget(_PreviewTitleBar(shell))
    shell_root.addWidget(Pmu1811UI(shell), 1)
    shell.resize(1080, 720)
    shell.show()
    shell.eventFilter = _shell_event_filter
    _apply_dwm_round_corners(shell)
    sys.exit(app.exec())

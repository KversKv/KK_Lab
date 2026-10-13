#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BES GPIO Workbench — DUT GPIO 控制页（暗色精密仪器工作台）。

布局：Top Bar（品牌 + DUT 副标题 / 5 大视图 Tab / i2c.bes_chip_check() 主按钮）
→ DUT 状态与 Bank 面板（Profile / Bank / 地址速览 / 遥测统计）
→ 批处理与掩码注入工具条（全组操作 / 32bit 掩码）
→ 中央主工作视口（Pin Matrix / Register Map / I2C Sniffer /
  JSON Config / Confirm Note 五大视图）。

硬件语义（严格 SET/CLR，杜绝读-改-写竞态）：
OUTPUT=Base+0x04 / INPUT=Base+0x10 / HIGH=Base+0x00 / LOW=Base+0x0C / 读=Base+0x50。
PU/PD/drv 为普通 RW 寄存器，必须 OP_BITS 位域写（DLL RMW）。

铁律：真实硬件读写一律走 core/gpio/ Worker（QThread），页面无阻塞 I2C。
方向寄存器无回读，模式状态仅会话内记忆。
"""

import sys
import os
import json
from datetime import datetime

if not getattr(sys, "frozen", False):
    _PROJECT_ROOT = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QSizePolicy, QStackedWidget,
    QPlainTextEdit, QTextEdit, QLineEdit, QButtonGroup, QFileDialog,
    QApplication, QMenu,
)
from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtGui import QIcon, QTransform

from log_config import get_logger
from ui.resource_path import get_resource_base, get_user_data_dir
from ui.utils.icon_utils import tinted_svg_icon, tinted_svg_pixmap
from ui.widgets.dark_combobox import DarkComboBox
from ui.widgets.wheel_line_edit import HexWheelLineEdit
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from core.gpio.gpio_config import (
    load_gpio_config, list_gpio_config_chips, mode_label,
    MODE_OUT_HIGH, MODE_OUT_LOW, MODE_IN_FLOAT,
    MODE_IN_PULL_UP, MODE_IN_PULL_DOWN,
    OP_WRITE, OP_BITS,
    OFFSET_OUT_SET, OFFSET_DIR_SET, OFFSET_OUT_CLR, OFFSET_DIR_CLR,
    OFFSET_IN_READ, PINS_PER_GROUP, GROUPS_PER_BANK, GPIOS_PER_BANK,
)
from core.gpio.gpio_workers import (
    GpioChipCheckWorker, GpioReadBanksWorker, GpioApplyWorker,
)

logger = get_logger(__name__)

_ICONS_DIR = os.path.join(get_resource_base(), "resources", "icons")
_MONO = "Consolas, 'Courier New', monospace"

# ---------------------------------------------------------------- 调色板（60-30-10）
# 60% 基底 #020617/#0B0F19；30% 面板 #0F172A + 1px #1E293B；
# 10% 遥测荧光：青 #06B6D4/#22D3EE、翠 #10B981、琥珀 #F59E0B、靛 #6366F1、灰 #475569。

_GPIO_PAGE_QSS = """
QWidget#gpioPage {
    background-color: #020617;
    color: #E2E8F0;
}
QWidget#gpioViewPage {
    background-color: #020617;
}
QLabel {
    background-color: transparent;
    color: #E2E8F0;
    border: none;
}
QLabel#gpioTitle {
    font-size: 16px;
    font-weight: 700;
    color: #F1F5F9;
}
QLabel#gpioSub {
    font-family: """ + _MONO + """;
    font-size: 11px;
    color: #64748B;
}
QLabel#gpioStatus { color: #94A3B8; font-size: 11px; }
QLabel#gpioStatus[ok="1"] { color: #10B981; }
QLabel#gpioStatus[err="1"] { color: #EF4444; }
QLabel#gpioDim {
    color: #64748B;
    font-size: 11px;
}
QLabel#gpioMono {
    font-family: """ + _MONO + """;
    font-size: 11px;
    color: #94A3B8;
}
QLabel#gpioAddr {
    font-family: """ + _MONO + """;
    font-size: 11px;
    color: #22D3EE;
}
QLabel#gpioBankInfo { color: #64748B; font-size: 10px; }
QLabel#gpioPanelKey {
    color: #64748B;
    font-size: 11px;
}
QLabel#gpioSection {
    color: #94A3B8;
    font-size: 11px;
    font-weight: 600;
}

/* ---- Top bar tabs（盒模型一致，§25） ---- */
QPushButton#gpioTab {
    background-color: transparent;
    color: #94A3B8;
    border: 1px solid transparent;
    border-bottom: 2px solid transparent;
    border-radius: 0px;
    padding: 5px 10px 3px 10px;
    font-size: 12px;
}
QPushButton#gpioTab:hover { color: #E2E8F0; }
QPushButton#gpioTab:checked {
    color: #22D3EE;
    border: 1px solid transparent;
    border-bottom: 2px solid #06B6D4;
    padding: 5px 10px 3px 10px;
}
QPushButton#gpioTab:disabled { color: #334155; }

/* ---- 主操作按钮 chip_check ---- */
QPushButton#gpioPrimary {
    background-color: #164E63;
    color: #A5F3FC;
    border: 1px solid #06B6D4;
    border-radius: 4px;
    padding: 0px 14px;
    font-family: """ + _MONO + """;
    font-size: 12px;
    font-weight: 600;
    min-height: 26px;
    max-height: 26px;
}
QPushButton#gpioPrimary:hover { background-color: #155E75; }
QPushButton#gpioPrimary:disabled {
    background-color: #0B0F19; color: #475569; border-color: #1E293B;
}

/* ---- Pin Matrix 底部 READ 主按钮 ---- */
QPushButton#gpioReadBtn {
    background-color: #0E7490;
    color: #ECFEFF;
    border: 1px solid #22D3EE;
    border-radius: 4px;
    padding: 0px 14px;
    font-family: """ + _MONO + """;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 4px;
    min-height: 30px;
    max-height: 30px;
}
QPushButton#gpioReadBtn:hover { background-color: #0891B2; }
QPushButton#gpioReadBtn:pressed { background-color: #164E63; }
QPushButton#gpioReadBtn:disabled {
    background-color: #0B0F19; color: #334155; border-color: #1E293B;
}

/* ---- 面板容器 ---- */
QFrame#gpioPanel {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 6px;
}
QFrame#gpioSep {
    background-color: #1E293B;
    min-width: 1px; max-width: 1px;
}
QFrame#gpioHSep {
    background-color: #1E293B;
    min-height: 1px; max-height: 1px;
}

/* ---- 通用小按钮 ---- */
QPushButton#gpioBtn {
    background-color: #111D33;
    color: #CBD5E1;
    border: 1px solid #1E293B;
    border-radius: 4px;
    padding: 0px 10px;
    font-size: 11px;
    min-height: 22px;
    max-height: 22px;
}
QPushButton#gpioBtn:hover { border-color: #155E75; color: #E2E8F0; }
QPushButton#gpioBtn:disabled { background-color: #0B0F19; color: #475569; }
QPushButton#gpioBtn[on="1"] {
    background-color: #164E63; color: #22D3EE; border-color: #06B6D4;
}

/* ---- Bank 切换按钮（宽度受限，仅显示序号；粗体等宽数字方块） ---- */
QPushButton#gpioBankBtn {
    background-color: #111D33;
    color: #64748B;
    border: 1px solid #1E293B;
    border-radius: 4px;
    padding: 0px;
    font-family: """ + _MONO + """;
    font-size: 12px;
    font-weight: bold;
    min-width: 24px;
    max-width: 24px;
    min-height: 22px;
    max-height: 22px;
}
QPushButton#gpioBankBtn:hover { border-color: #155E75; color: #E2E8F0; }
QPushButton#gpioBankBtn:checked {
    background-color: #164E63; color: #22D3EE; border-color: #06B6D4;
}
QPushButton#gpioBankBtn:disabled { background-color: #0B0F19; color: #475569; }

QPushButton#gpioBatch {
    background-color: #111D33;
    color: #CBD5E1;
    border: 1px solid #1E293B;
    border-radius: 4px;
    padding: 0px 8px;
    font-family: """ + _MONO + """;
    font-size: 10px;
    min-height: 22px;
    max-height: 22px;
}
QPushButton#gpioBatch:hover { border-color: #155E75; color: #E2E8F0; }
QPushButton#gpioBatch:disabled { background-color: #0B0F19; color: #475569; }

/* ---- 输入框 ---- */
QLineEdit#gpioHexEdit, QLineEdit#gpioSearch, QLineEdit#gpioAliasEdit {
    background-color: #020617;
    color: #22D3EE;
    border: 1px solid #1E293B;
    border-radius: 4px;
    padding: 2px 8px;
    font-family: """ + _MONO + """;
    font-size: 12px;
    min-height: 20px;
    selection-background-color: #164E63;
}
QLineEdit#gpioSearch { color: #E2E8F0; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }
QLineEdit#gpioHexEdit:focus, QLineEdit#gpioSearch:focus, QLineEdit#gpioAliasEdit:focus {
    border-color: #06B6D4;
}
QLineEdit#gpioHexEdit:disabled { color: #475569; }

/* ---- 统计遥测 ---- */
QLabel#gpioStatKey { color: #475569; font-size: 10px; }
QLabel#gpioStatVal {
    font-family: """ + _MONO + """;
    font-size: 13px;
    font-weight: 700;
    color: #E2E8F0;
}
QLabel#gpioStatVal[k="out"]  { color: #22D3EE; }
QLabel#gpioStatVal[k="in"]   { color: #10B981; }
QLabel#gpioStatVal[k="high"] { color: #22D3EE; }
QLabel#gpioStatVal[k="low"]  { color: #64748B; }
QLabel#gpioStatVal[k="pu"]   { color: #F59E0B; }
QLabel#gpioStatVal[k="pd"]   { color: #6366F1; }

/* ---- Pin Matrix 单行卡片（斑马纹，行距 0） ---- */
QFrame#pinCard {
    background-color: #0F172A;
    border: 1px solid transparent;
    border-radius: 0px;
    min-height: 24px;
}
QFrame#pinCard[alt="1"] { background-color: #141D30; }
QFrame#pinCard:hover { border-color: #334155; }
QFrame#pinCard[sel="1"] { border: 1px solid #06B6D4; }
QFrame#pinCard[lvl="h"] { border: 1px solid #155E75; }
QFrame#pinCard[lvl="h"][sel="1"] { border: 1px solid #22D3EE; }
QFrame#matrixDivider {
    background-color: #1E293B;
    border: none;
    min-width: 1px;
    max-width: 1px;
}
QLabel#pinBit {
    font-family: """ + _MONO + """;
    font-size: 10px;
    color: #475569;
}
QLabel#pinName {
    font-family: """ + _MONO + """;
    font-size: 11px;
    font-weight: 700;
    color: #E2E8F0;
}
QLabel#pinAlias {
    font-size: 9px;
    color: #64748B;
}
QFrame#pinLed {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 5px;
    min-width: 10px; max-width: 10px;
    min-height: 10px; max-height: 10px;
}
QFrame#pinCard[lvl="h"] QFrame#pinLed {
    background-color: #22D3EE;
    border: 1px solid #22D3EE;
}
QPushButton#pinMini {
    background-color: transparent;
    color: #94A3B8;
    border: 1px solid #1E293B;
    border-radius: 3px;
    padding: 0px 2px;
    font-family: """ + _MONO + """;
    font-size: 9px;
    min-height: 15px;
    max-height: 15px;
}
QPushButton#pinMini:hover { border-color: #334155; color: #E2E8F0; }
QPushButton#pinMini:disabled { color: #334155; }
QPushButton#pinMini[cur="out"] { color: #22D3EE; border-color: #155E75; }
QPushButton#pinMini[cur="in"]  { color: #10B981; border-color: #064E3B; }
QPushButton#pinMini[cur="h"]   { color: #22D3EE; border-color: #155E75; }
QPushButton#pinMini[cur="l"]   { color: #64748B; }
QPushButton#pinMini[cur="pu"]  { color: #F59E0B; border-color: #78350F; }
QPushButton#pinMini[cur="pd"]  { color: #818CF8; border-color: #312E81; }

/* ---- 右键菜单（暗色） ---- */
QMenu {
    background-color: #0F172A;
    color: #CBD5E1;
    border: 1px solid #1E293B;
    padding: 4px;
}
QMenu::item {
    padding: 5px 24px 5px 16px;
    border-radius: 3px;
}
QMenu::item:selected { background-color: #164E63; color: #22D3EE; }
QMenu::item:disabled { color: #475569; }

/* ---- Export Manager（Matrix 右侧导出管理器） ---- */
QScrollArea#exportList { min-height: 132px; max-height: 132px; }
QFrame#exportRow {
    background-color: #111D33;
    border: 1px solid #1E293B;
    border-radius: 4px;
    min-height: 26px;
    max-height: 26px;
}
QLabel#exportMode { color: #64748B; font-size: 10px; }
QPushButton#exportDel {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    min-width: 20px; max-width: 20px;
    min-height: 20px; max-height: 20px;
}
QPushButton#exportDel:hover { background-color: #7F1D1D; border-color: #EF4444; }

/* ---- Inspector ---- */
QFrame#gpioInspector {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 6px;
}
QLabel#gpioPinName {
    font-family: """ + _MONO + """;
    font-size: 18px;
    font-weight: 700;
    color: #22D3EE;
}
QLabel#gpioPinInfo {
    font-family: """ + _MONO + """;
    font-size: 10px;
    color: #64748B;
}
QLabel#gpioBigState {
    font-family: """ + _MONO + """;
    font-size: 15px;
    font-weight: 700;
    color: #475569;
}
QLabel#gpioBigState[lvl="h"] { color: #22D3EE; }
QLabel#gpioBigState[lvl="l"] { color: #64748B; }
QPushButton#gpioAction {
    background-color: #111D33;
    color: #CBD5E1;
    border: 1px solid #1E293B;
    border-radius: 4px;
    padding: 0px 8px;
    font-size: 11px;
    min-height: 24px;
    max-height: 24px;
}
QPushButton#gpioAction:hover { border-color: #155E75; }
QPushButton#gpioAction:disabled { background-color: #0B0F19; color: #475569; }
QPushButton#gpioAction[cur="1"] {
    background-color: #164E63; color: #22D3EE; border-color: #06B6D4;
}
QPushButton#gpioAction[cur="pu"] {
    background-color: #451A03; color: #F59E0B; border-color: #B45309;
}
QPushButton#gpioAction[cur="pd"] {
    background-color: #1E1B4B; color: #818CF8; border-color: #4F46E5;
}

/* ---- 表格 / 寄存器位行内按钮 ---- */
QPushButton#gpioCellBtn {
    background-color: #111D33;
    color: #CBD5E1;
    border: 1px solid #1E293B;
    border-radius: 3px;
    padding: 0px 4px;
    font-family: """ + _MONO + """;
    font-size: 10px;
    min-height: 18px;
    max-height: 18px;
}
QPushButton#gpioCellBtn:hover { border-color: #155E75; }
QPushButton#gpioCellBtn:disabled { background-color: #0B0F19; color: #475569; }
QPushButton#gpioCellBtn[kind="out"] { color: #22D3EE; border-color: #155E75; }
QPushButton#gpioCellBtn[kind="in"]  { color: #10B981; border-color: #064E3B; }
QPushButton#gpioCellBtn[kind="h"]   { color: #22D3EE; border-color: #155E75; }
QPushButton#gpioCellBtn[kind="l"]   { color: #64748B; }

/* ---- Register Map ---- */
QFrame#regCard {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 6px;
}
QLabel#regCardName { font-size: 11px; font-weight: 700; color: #E2E8F0; }
QLabel#regCardAddr {
    font-family: """ + _MONO + """;
    font-size: 11px;
    color: #22D3EE;
}
QLabel#regCardVal {
    font-family: """ + _MONO + """;
    font-size: 12px;
    font-weight: 700;
    color: #F59E0B;
}
QLabel#regCardHint { font-size: 9px; color: #475569; }
QPushButton#regBit {
    background-color: #0B0F19;
    color: #475569;
    border: 1px solid #1E293B;
    border-radius: 2px;
    padding: 0px;
    font-family: """ + _MONO + """;
    font-size: 9px;
    min-width: 20px; max-width: 20px;
    min-height: 18px; max-height: 18px;
}
QPushButton#regBit:hover { border-color: #334155; }
QPushButton#regBit[on="1"] {
    background-color: #164E63; color: #22D3EE; border-color: #06B6D4;
}
QPushButton#regBit[rd="1"][on="1"] {
    background-color: #064E3B; color: #34D399; border-color: #10B981;
}
QPushButton#regBit:disabled { color: #1E293B; }

/* ---- I2C Sniffer ---- */
QTextEdit#gpioSniff {
    background-color: #020617;
    color: #CBD5E1;
    border: 1px solid #1E293B;
    border-radius: 4px;
    font-family: """ + _MONO + """;
    font-size: 11px;
    padding: 4px;
}
QPushButton#gpioChip {
    background-color: transparent;
    color: #64748B;
    border: 1px solid #1E293B;
    border-radius: 4px;
    padding: 0px 8px;
    font-family: """ + _MONO + """;
    font-size: 10px;
    min-height: 18px;
    max-height: 18px;
}
QPushButton#gpioChip:checked {
    background-color: #164E63; color: #22D3EE; border-color: #06B6D4;
}

/* ---- JSON / Code 编辑器 ---- */
QPlainTextEdit#gpioMonoEdit {
    background-color: #020617;
    color: #CBD5E1;
    border: 1px solid #1E293B;
    border-radius: 4px;
    font-family: """ + _MONO + """;
    font-size: 11px;
    padding: 4px;
    selection-background-color: #164E63;
}
QLabel#gpioJsonErr { color: #EF4444; font-size: 11px; }

/* ---- Confirm Note ---- */
QFrame#noteCard {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 6px;
}
QLabel#noteTitle { font-size: 12px; font-weight: 700; color: #E2E8F0; }
QLabel#noteBody { color: #94A3B8; font-size: 11px; }
QLabel#noteStatus {
    font-family: """ + _MONO + """;
    font-size: 10px;
    font-weight: 700;
    color: #F59E0B;
}
QLabel#noteStatus[ok="1"] { color: #10B981; }

/* ---- 滚动条（页内暗色） ---- */
QScrollArea#gpioScroll { background-color: #020617; border: none; }
QScrollBar:vertical {
    background: transparent; width: 8px; margin: 2px;
}
QScrollBar::handle:vertical {
    background: #1E293B; border-radius: 4px; min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #334155; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QScrollBar:horizontal {
    background: transparent; height: 8px; margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #1E293B; border-radius: 4px; min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #334155; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
"""

_SPEED_OPTIONS = None  # [(I2CSpeedMode, label), ...] 懒加载


def _speed_options():
    global _SPEED_OPTIONS
    if _SPEED_OPTIONS is None:
        from lib.i2c.Bes_I2CIO_Interface import I2CSpeedMode
        _SPEED_OPTIONS = [
            (I2CSpeedMode.SPEED_20K, "20 kHz"),
            (I2CSpeedMode.SPEED_100K, "100 kHz"),
            (I2CSpeedMode.SPEED_400K, "400 kHz"),
            (I2CSpeedMode.SPEED_750K, "750 kHz"),
        ]
    return _SPEED_OPTIONS


def _icon(name, color, size=14):
    return tinted_svg_icon(os.path.join(_ICONS_DIR, name), color, size)


def _fmt32(value):
    return "0x{0:08X}".format(value & 0xFFFFFFFF)


def _popcount(value):
    return bin(value & 0xFFFFFFFF).count("1")


def _repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _parse_hex(text):
    """解析 16 进制输入（容忍 0x 前缀/空格）；非法返回 None。"""
    text = (text or "").strip()
    if not text:
        return None
    try:
        return int(text, 16) & 0xFFFFFFFF
    except ValueError:
        return None


def _write_bits_line(op, addr, value, hi, lo):
    """寄存器动作 -> WRITE_BITS 脚本行；set/clear 单 bit 整写转位域写。"""
    if hi < 0:
        if value and (value & (value - 1)) == 0:
            bit = value.bit_length() - 1
            hi, lo, value = bit, bit, 1
        else:
            hi, lo = 31, 0
    return "WRITE_BITS 0x{0:08X} {1} {2} 0x{3:X}".format(addr, hi, lo, value)


class _PinCard(QFrame):
    """Pin Matrix 单行引脚条：BIT + 名称 + 别名 + OUT/IN、电平、PU/PD + LED。"""

    def __init__(self, group, pin, on_select, on_dir, on_level, on_pull,
                 on_menu, parent=None):
        super().__init__(parent)
        self.group = group
        self.pin = pin
        self._on_select = on_select
        self._on_menu = on_menu
        self.setObjectName("pinCard")
        self.setProperty("sel", "0")
        self.setProperty("lvl", "x")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 1, 6, 1)
        lay.setSpacing(6)

        self.bit_label = QLabel("BIT--")
        self.bit_label.setObjectName("pinBit")
        self.bit_label.setFixedWidth(38)
        lay.addWidget(self.bit_label)

        self.name_label = QLabel("GPIO--")
        self.name_label.setObjectName("pinName")
        self.name_label.setFixedWidth(48)
        lay.addWidget(self.name_label)

        self.alias_label = QLabel("")
        self.alias_label.setObjectName("pinAlias")
        lay.addWidget(self.alias_label, 1)

        self.dir_btn = QPushButton("IN")
        self.dir_btn.setObjectName("pinMini")
        self.dir_btn.setFixedWidth(36)
        self.dir_btn.setToolTip("方向切换 (Dir Set +0x04 / Dir Clr +0x10)")
        self.dir_btn.clicked.connect(lambda: on_dir(self.group, self.pin))
        lay.addWidget(self.dir_btn)

        self.level_btn = QPushButton("-")
        self.level_btn.setObjectName("pinMini")
        self.level_btn.setFixedWidth(28)
        self.level_btn.setToolTip(
            "输出: 电平翻转 (Out Set +0x00 / Out Clr +0x0C)；"
            "输入: 点击回读 0x50")
        self.level_btn.clicked.connect(lambda: on_level(self.group, self.pin))
        lay.addWidget(self.level_btn)

        self.pull_btn = QPushButton("Z")
        self.pull_btn.setObjectName("pinMini")
        self.pull_btn.setFixedWidth(32)
        self.pull_btn.setToolTip("上下拉轮转 Hi-Z -> PU -> PD")
        self.pull_btn.clicked.connect(lambda: on_pull(self.group, self.pin))
        lay.addWidget(self.pull_btn)

        self.led = QFrame()
        self.led.setObjectName("pinLed")
        lay.addWidget(self.led)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_select(self.group, self.pin)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        self._on_menu(self.group, self.pin, event.globalPos())


class GpioControlUI(QWidget):
    """BES GPIO Workbench：Detect DUT -> Bank 管理 -> 5 大视图 GPIO 操控。"""

    VIEW_TITLES = [
        ("Pin Matrix", "Pin Matrix Grid（引脚矩阵网格）"),
        ("Register Map", "Register Map（底层寄存器视图）"),
        ("I2C Sniffer", "I2C Bus Sniffer（总线事务嗅探器）"),
        ("JSON Config", "DUT JSON Config（芯片配置文件管理器）"),
        ("Confirm Note", "DUT Confirmation Note（硬件确认清单）"),
    ]

    MASK_TARGETS = [
        ("VAL_SET (+0x00)", OFFSET_OUT_SET),
        ("DIR_SET (+0x04)", OFFSET_DIR_SET),
        ("VAL_CLR (+0x0C)", OFFSET_OUT_CLR),
        ("DIR_CLR (+0x10)", OFFSET_DIR_CLR),
    ]

    # Pin Matrix 右键 Export Config 可导出配置（标签, mode）
    EXPORT_MODES = [
        ("输出高", MODE_OUT_HIGH),
        ("输出低", MODE_OUT_LOW),
        ("输入上拉", MODE_IN_PULL_UP),
        ("输入下拉", MODE_IN_PULL_DOWN),
    ]
    _EXPORT_MODE_LABELS = {mode: label for label, mode in EXPORT_MODES}

    POLL_INTERVALS = [(200, "200 ms"), (500, "500 ms"),
                      (1000, "1000 ms"), (2000, "2000 ms")]

    SNIFF_KINDS = ["WRITE32", "READ32", "CHIP_CHECK", "ERROR"]

    _SNIFF_COLORS = {
        "WRITE32": "#22D3EE",
        "READ32": "#10B981",
        "CHIP_CHECK": "#A78BFA",
        "ERROR": "#EF4444",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("gpioPage")
        self._cfg = None            # GpioChipConfig
        self._chip_info = None
        self._dev_addr = None
        self._cur_bank = 0
        self._selected = None       # (group, pin)
        self._pin_cards = {}        # (group, pin) -> _PinCard（当前 bank）
        self._pin_meta = {}         # (group, pin) -> {"alias": str}
        self._dir_shadow = {}       # bank_idx -> 32bit（会话影子，dir 无回读）
        self._out_shadow = {}       # bank_idx -> 32bit
        self._reg_shadow = {}       # addr -> 32bit（PU/PD/drv/任意写影子）
        self._in_value = {}         # bank_idx -> 32bit|None（0x50 最近读值）
        self._reg_cards = []        # [(kind, addr|None, card_widgets)]
        self._sniff_entries = []    # [(kind, raw, html)]
        self._sniff_kind = None     # None = All
        self._sniff_paused = False
        self._json_path = None
        self._thread = None
        self._worker = None
        self._worker_done_cb = None
        self._spin_angle = 0
        self._export_items = []     # [(group, pin, mode)] 导出管理器条目
        self._build_ui()

    # ================================================================ UI 构建

    def _build_ui(self):
        self.setStyleSheet(_GPIO_PAGE_QSS)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        content = QWidget()
        content.setObjectName("gpioContent")
        clay = QVBoxLayout(content)
        clay.setContentsMargins(0, 0, 0, 0)
        clay.setSpacing(6)

        clay.addLayout(self._build_top_bar())
        clay.addWidget(self._build_dut_panel())
        clay.addWidget(self._build_batch_toolbar())

        self._stack = QStackedWidget()
        clay.addWidget(self._stack, 1)
        self._build_views()

        self._splitter, self.execution_logs = ExecutionLogsFrame.wrap_with(
            content, title="Activity Logs", show_progress=False,
            stretch=(5, 1))
        root.addWidget(self._splitter, 1)

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._on_poll_tick)

        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(100)
        self._spin_timer.timeout.connect(self._on_spin_tick)

        # 延迟读定时器：页内子对象（页面销毁自动失效），重复延迟合并为最后一次
        self._deferred_read_fn = None
        self._deferred_timer = QTimer(self)
        self._deferred_timer.setSingleShot(True)
        self._deferred_timer.timeout.connect(self._on_deferred_read)

        self.append_log("[INFO] BES GPIO Workbench 已初始化，"
                        "请点击 i2c.bes_chip_check() 连接 DUT")
        self._refresh_all_views()

    def _build_top_bar(self):
        row = QHBoxLayout()
        row.setSpacing(6)

        chip_icon = QLabel()
        pm = tinted_svg_pixmap(os.path.join(_ICONS_DIR, "cpu.svg"), "#22D3EE", 18)
        if not pm.isNull():
            chip_icon.setPixmap(pm)
        row.addWidget(chip_icon)

        title = QLabel("BES GPIO Workbench")
        title.setObjectName("gpioTitle")
        self.dut_sub = QLabel("DUT: --")
        self.dut_sub.setObjectName("gpioSub")
        head = QVBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(0)
        head.addWidget(title)
        head.addWidget(self.dut_sub)
        row.addLayout(head)
        row.addSpacing(8)

        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        self._tab_buttons = []
        for idx, (short, full) in enumerate(self.VIEW_TITLES):
            btn = QPushButton(short)
            btn.setObjectName("gpioTab")
            btn.setCheckable(True)
            btn.setToolTip(full)
            # 垂直撑满顶栏（高度 = 标题 + DUT 副标题两行），勿在 QSS 钉死
            btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
            self._tab_group.addButton(btn, idx)
            row.addWidget(btn)
            self._tab_buttons.append(btn)
        self._tab_group.idClicked.connect(self._on_tab_changed)
        self._tab_buttons[0].setChecked(True)

        row.addStretch(1)

        row.addWidget(QLabel("Speed"))
        self.speed_combo = DarkComboBox()
        for mode, label in _speed_options():
            self.speed_combo.addItem(label, mode)
        self.speed_combo.setCurrentIndex(1)  # 100 kHz
        self.speed_combo.setToolTip("USB-I2C 桥接速率")
        row.addWidget(self.speed_combo)

        self.detect_btn = QPushButton("i2c.bes_chip_check()")
        self.detect_btn.setObjectName("gpioPrimary")
        self.detect_btn.setIcon(_icon("refresh-cw.svg", "#22D3EE", 13))
        self.detect_btn.clicked.connect(self._on_detect_clicked)
        row.addWidget(self.detect_btn)
        return row

    def _build_dut_panel(self):
        panel = QFrame()
        panel.setObjectName("gpioPanel")
        lay = QHBoxLayout(panel)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(8)

        dut_key = QLabel("DUT")
        dut_key.setObjectName("gpioPanelKey")
        lay.addWidget(dut_key)
        self.profile_combo = DarkComboBox()
        self.profile_combo.setToolTip("DUT Profile（chips/gpio_configs/*.json 预设）")
        for name in list_gpio_config_chips():
            self.profile_combo.addItem(name.upper(), name)
        lay.addWidget(self.profile_combo)
        self.load_btn = QPushButton("Load")
        self.load_btn.setObjectName("gpioBtn")
        self.load_btn.setToolTip("加载选中的 DUT Profile（需先 i2c.bes_chip_check()）")
        self.load_btn.clicked.connect(self._on_load_profile_clicked)
        lay.addWidget(self.load_btn)

        lay.addWidget(self._make_vsep())

        bank_key = QLabel("Bank")
        bank_key.setObjectName("gpioPanelKey")
        lay.addWidget(bank_key)
        self._bank_group = QButtonGroup(self)
        self._bank_group.setExclusive(True)
        self._bank_buttons = []
        self._bank_box = QHBoxLayout()
        self._bank_box.setContentsMargins(0, 0, 0, 0)
        self._bank_box.setSpacing(4)
        lay.addLayout(self._bank_box)
        self._bank_group.idClicked.connect(self._on_bank_changed)

        lay.addWidget(self._make_vsep())

        addr_box = QVBoxLayout()
        addr_box.setContentsMargins(0, 0, 0, 0)
        addr_box.setSpacing(0)
        self.addr_label = QLabel("Base --")
        self.addr_label.setObjectName("gpioAddr")
        addr_box.addWidget(self.addr_label)
        self.bank_label = QLabel("Bank --")
        self.bank_label.setObjectName("gpioBankInfo")
        addr_box.addWidget(self.bank_label)
        lay.addLayout(addr_box)

        lay.addWidget(self._make_vsep())

        self._stat_vals = {}
        for key, label in (("out", "OUT"), ("in", "IN"), ("high", "HIGH"),
                           ("low", "LOW"), ("pu", "PU"), ("pd", "PD")):
            box = QVBoxLayout()
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(0)
            k = QLabel(label)
            k.setObjectName("gpioStatKey")
            k.setAlignment(Qt.AlignCenter)
            v = QLabel("-")
            v.setObjectName("gpioStatVal")
            v.setProperty("k", key)
            v.setAlignment(Qt.AlignCenter)
            box.addWidget(k)
            box.addWidget(v)
            lay.addLayout(box)
            self._stat_vals[key] = v

        lay.addStretch(1)

        self.status_label = QLabel("未检测")
        self.status_label.setObjectName("gpioStatus")
        lay.addWidget(self.status_label)
        return panel

    def _build_batch_toolbar(self):
        bar = QFrame()
        bar.setObjectName("gpioPanel")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 5, 10, 5)
        lay.setSpacing(6)

        batch_defs = [
            ("All OUT HIGH", self._on_batch_out_high,
             "当前 Bank 32 引脚全部输出高电平 (DIR_SET+VAL_SET = 0xFFFFFFFF)"),
            ("All OUT LOW", self._on_batch_out_low,
             "当前 Bank 32 引脚全部输出低电平 (DIR_SET+VAL_CLR = 0xFFFFFFFF)"),
            ("All IN Hi-Z", self._on_batch_in_hiz,
             "当前 Bank 32 引脚全部高阻输入 (DIR_CLR = 0xFFFFFFFF，PU/PD 全关)"),
            ("All PU", lambda: self._on_batch_pull(True),
             "当前 Bank 32 引脚全部上拉 (OP_BITS 位域写)"),
            ("All PD", lambda: self._on_batch_pull(False),
             "当前 Bank 32 引脚全部下拉 (OP_BITS 位域写)"),
            ("Invert OUT", self._on_batch_invert,
             "当前 Bank 所有输出引脚高低电平反转"),
        ]
        self._batch_buttons = []
        for text, slot, tip in batch_defs:
            btn = QPushButton(text)
            btn.setObjectName("gpioBatch")
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            lay.addWidget(btn)
            self._batch_buttons.append(btn)

        lay.addWidget(self._make_vsep())

        mask_key = QLabel("Mask")
        mask_key.setObjectName("gpioPanelKey")
        lay.addWidget(mask_key)
        self.mask_edit = HexWheelLineEdit()
        self.mask_edit.setObjectName("gpioHexEdit")
        self.mask_edit.setPlaceholderText("0x000000FF")
        self.mask_edit.setFixedWidth(110)
        self.mask_edit.setToolTip("32-Bit 十六进制掩码（滚轮调值）")
        lay.addWidget(self.mask_edit)
        self.mask_target = DarkComboBox()
        for label, off in self.MASK_TARGETS:
            self.mask_target.addItem(label, off)
        lay.addWidget(self.mask_target)
        self.mask_btn = QPushButton("Write Mask")
        self.mask_btn.setObjectName("gpioBtn")
        self.mask_btn.setToolTip("将掩码写入选中的 SET/CLR 寄存器")
        self.mask_btn.clicked.connect(self._on_mask_write_clicked)
        lay.addWidget(self.mask_btn)

        lay.addStretch(1)
        return bar

    def _make_vsep(self):
        sep = QFrame()
        sep.setObjectName("gpioSep")
        return sep

    # ------------------------------------------------------------ 5 大视图

    def _build_views(self):
        self._stack.addWidget(self._build_matrix_view())   # 0
        self._stack.addWidget(self._build_regmap_view())   # 1
        self._stack.addWidget(self._build_sniffer_view())  # 2
        self._stack.addWidget(self._build_json_view())     # 3
        self._stack.addWidget(self._build_notes_view())    # 4

    # 视图 1：Pin Matrix Grid + Inspector
    def _build_matrix_view(self):
        page = QWidget()
        page.setObjectName("gpioViewPage")
        lay = QHBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self._matrix_scroll = QScrollArea()
        self._matrix_scroll.setObjectName("gpioScroll")
        self._matrix_scroll.setWidgetResizable(True)
        self._matrix_scroll.setFrameShape(QFrame.NoFrame)
        self._matrix_container = QWidget()
        self._matrix_container.setObjectName("gpioViewPage")
        cols = QHBoxLayout(self._matrix_container)
        cols.setContentsMargins(0, 0, 0, 0)
        cols.setSpacing(6)
        self._matrix_col_l = QVBoxLayout()
        self._matrix_col_l.setContentsMargins(0, 0, 0, 0)
        self._matrix_col_l.setSpacing(0)
        self._matrix_col_r = QVBoxLayout()
        self._matrix_col_r.setContentsMargins(0, 0, 0, 0)
        self._matrix_col_r.setSpacing(0)
        divider = QFrame()
        divider.setObjectName("matrixDivider")
        cols.addLayout(self._matrix_col_l, 1)
        cols.addWidget(divider)
        cols.addLayout(self._matrix_col_r, 1)
        self._matrix_placeholder = QLabel(
            "请先 i2c.bes_chip_check() 或加载 DUT Profile")
        self._matrix_placeholder.setObjectName("gpioStatus")
        self._matrix_placeholder.setAlignment(Qt.AlignCenter)
        self._matrix_col_l.addWidget(self._matrix_placeholder)
        self._matrix_scroll.setWidget(self._matrix_container)
        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(6)
        left.addWidget(self._matrix_scroll, 1)
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(6)
        self.read_btn = QPushButton("READ")
        self.read_btn.setObjectName("gpioReadBtn")
        self.read_btn.setToolTip("立即读取当前 Bank 输入状态寄存器 Base + 0x50")
        self.read_btn.clicked.connect(self._on_read_bank_clicked)
        bottom.addWidget(self.read_btn, 1)
        poll_key = QLabel("Poll 0x50")
        poll_key.setObjectName("gpioPanelKey")
        bottom.addWidget(poll_key)
        self.poll_combo = DarkComboBox()
        for ms, label in self.POLL_INTERVALS:
            self.poll_combo.addItem(label, ms)
        self.poll_combo.setCurrentIndex(1)  # 500 ms
        self.poll_combo.currentIndexChanged.connect(self._on_poll_interval_changed)
        bottom.addWidget(self.poll_combo)
        self.poll_btn = QPushButton("Start Poll")
        self.poll_btn.setObjectName("gpioBtn")
        self.poll_btn.setProperty("on", "0")
        self.poll_btn.setToolTip("定时轮询当前 Bank 输入状态寄存器 Base + 0x50")
        self.poll_btn.clicked.connect(self._on_poll_toggled)
        bottom.addWidget(self.poll_btn)
        left.addLayout(bottom)
        lay.addLayout(left, 1)

        lay.addWidget(self._build_inspector())
        self._export_panel = self._build_export_manager()
        self._export_panel.hide()   # 至少一个导出条目时才显示
        lay.addWidget(self._export_panel)
        return page

    def _build_inspector(self):
        panel = QFrame()
        panel.setObjectName("gpioInspector")
        panel.setFixedWidth(300)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        head = QHBoxLayout()
        head.setSpacing(6)
        self.insp_name = QLabel("GPIO--")
        self.insp_name.setObjectName("gpioPinName")
        head.addWidget(self.insp_name)
        head.addStretch(1)
        lay.addLayout(head)

        alias_row = QHBoxLayout()
        alias_row.setSpacing(6)
        alias_key = QLabel("Alias")
        alias_key.setObjectName("gpioPanelKey")
        alias_row.addWidget(alias_key)
        self.alias_edit = QLineEdit()
        self.alias_edit.setObjectName("gpioAliasEdit")
        self.alias_edit.setPlaceholderText("信号别名，如 LED_PWR / I2C_SDA")
        self.alias_edit.editingFinished.connect(self._on_alias_edited)
        alias_row.addWidget(self.alias_edit, 1)
        lay.addLayout(alias_row)

        self.insp_info = QLabel("-")
        self.insp_info.setObjectName("gpioPinInfo")
        lay.addWidget(self.insp_info)

        lay.addWidget(self._make_hsep())

        dir_key = QLabel("方向（OUTPUT=写 1 至 Base+0x04 / INPUT=Base+0x10）")
        dir_key.setObjectName("gpioSection")
        lay.addWidget(dir_key)
        dir_row = QHBoxLayout()
        dir_row.setSpacing(6)
        self.insp_dir_out = QPushButton("OUTPUT  +0x04")
        self.insp_dir_out.setObjectName("gpioAction")
        self.insp_dir_out.clicked.connect(lambda: self._on_insp_dir(True))
        dir_row.addWidget(self.insp_dir_out)
        self.insp_dir_in = QPushButton("INPUT  +0x10")
        self.insp_dir_in.setObjectName("gpioAction")
        self.insp_dir_in.clicked.connect(lambda: self._on_insp_dir(False))
        dir_row.addWidget(self.insp_dir_in)
        lay.addLayout(dir_row)

        lvl_key = QLabel("输出电平（HIGH=写 1 至 Base+0x00 / LOW=Base+0x0C）")
        lvl_key.setObjectName("gpioSection")
        lay.addWidget(lvl_key)
        lvl_row = QHBoxLayout()
        lvl_row.setSpacing(6)
        self.insp_lvl_h = QPushButton("HIGH  +0x00")
        self.insp_lvl_h.setObjectName("gpioAction")
        self.insp_lvl_h.clicked.connect(lambda: self._on_insp_level(True))
        lvl_row.addWidget(self.insp_lvl_h)
        self.insp_lvl_l = QPushButton("LOW  +0x0C")
        self.insp_lvl_l.setObjectName("gpioAction")
        self.insp_lvl_l.clicked.connect(lambda: self._on_insp_level(False))
        lvl_row.addWidget(self.insp_lvl_l)
        lay.addLayout(lvl_row)

        self.insp_pull_key = QLabel("上下拉三态（PU/PD 为 RW 寄存器位域写）")
        self.insp_pull_key.setObjectName("gpioSection")
        lay.addWidget(self.insp_pull_key)
        pull_row = QHBoxLayout()
        pull_row.setSpacing(6)
        self.insp_pull_hiz = QPushButton("High-Z")
        self.insp_pull_hiz.setObjectName("gpioAction")
        self.insp_pull_hiz.clicked.connect(lambda: self._on_insp_pull(0))
        pull_row.addWidget(self.insp_pull_hiz)
        self.insp_pull_pu = QPushButton("Pull-Up")
        self.insp_pull_pu.setObjectName("gpioAction")
        self.insp_pull_pu.clicked.connect(lambda: self._on_insp_pull(1))
        pull_row.addWidget(self.insp_pull_pu)
        self.insp_pull_pd = QPushButton("Pull-Down")
        self.insp_pull_pd.setObjectName("gpioAction")
        self.insp_pull_pd.clicked.connect(lambda: self._on_insp_pull(2))
        pull_row.addWidget(self.insp_pull_pd)
        lay.addLayout(pull_row)

        self.insp_drv_key = QLabel("驱动强度（drv_sel 位域：增减档调整）")
        self.insp_drv_key.setObjectName("gpioSection")
        lay.addWidget(self.insp_drv_key)
        drv_row = QHBoxLayout()
        drv_row.setSpacing(6)
        self.insp_drv_dec = QPushButton("- 减档")
        self.insp_drv_dec.setObjectName("gpioAction")
        self.insp_drv_dec.clicked.connect(lambda: self._on_drv_step(-1))
        drv_row.addWidget(self.insp_drv_dec)
        self.insp_drv_val = QLabel("Lv --")
        self.insp_drv_val.setObjectName("gpioMono")
        self.insp_drv_val.setAlignment(Qt.AlignCenter)
        drv_row.addWidget(self.insp_drv_val, 1)
        self.insp_drv_inc = QPushButton("+ 增档")
        self.insp_drv_inc.setObjectName("gpioAction")
        self.insp_drv_inc.clicked.connect(lambda: self._on_drv_step(1))
        drv_row.addWidget(self.insp_drv_inc)
        lay.addLayout(drv_row)

        lay.addWidget(self._make_hsep())

        read_row = QHBoxLayout()
        read_row.setSpacing(6)
        self.insp_big_state = QLabel("LOGIC --")
        self.insp_big_state.setObjectName("gpioBigState")
        read_row.addWidget(self.insp_big_state, 1)
        self.insp_read_btn = QPushButton("Read 0x50")
        self.insp_read_btn.setObjectName("gpioBtn")
        self.insp_read_btn.clicked.connect(self._on_read_bank_clicked)
        read_row.addWidget(self.insp_read_btn)
        lay.addLayout(read_row)

        self.insp_mask = QLabel("Mask --")
        self.insp_mask.setObjectName("gpioPinInfo")
        lay.addWidget(self.insp_mask)

        lay.addStretch(1)
        return panel

    # Pin Matrix 右侧：Export Manager（右键 Export Config 收集，合并导出）
    def _build_export_manager(self):
        panel = QFrame()
        panel.setObjectName("gpioPanel")
        panel.setFixedWidth(340)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(8, 6, 8, 8)
        lay.setSpacing(4)

        head = QHBoxLayout()
        head.setSpacing(6)
        title = QLabel("Export Manager")
        title.setObjectName("gpioSection")
        head.addWidget(title)
        self._export_count = QLabel("(0)")
        self._export_count.setObjectName("gpioDim")
        head.addWidget(self._export_count)
        head.addStretch(1)
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("gpioBtn")
        clear_btn.setIcon(_icon("trash.svg", "#94A3B8", 12))
        clear_btn.setToolTip("清空导出列表")
        clear_btn.clicked.connect(self._clear_export_items)
        head.addWidget(clear_btn)
        lay.addLayout(head)

        hint = QLabel("右键 Pin Matrix 引脚 -> Export Config 添加")
        hint.setObjectName("gpioDim")
        lay.addWidget(hint)

        self._export_list_area = QScrollArea()
        self._export_list_area.setObjectName("exportList")
        self._export_list_area.setWidgetResizable(True)
        self._export_list_area.setFrameShape(QFrame.NoFrame)
        self._export_list_host = QWidget()
        self._export_list_host.setObjectName("gpioViewPage")
        self._export_list_lay = QVBoxLayout(self._export_list_host)
        self._export_list_lay.setContentsMargins(0, 0, 0, 0)
        self._export_list_lay.setSpacing(3)
        self._export_list_lay.addStretch(1)
        self._export_list_area.setWidget(self._export_list_host)
        lay.addWidget(self._export_list_area)

        preview_key = QLabel("合并脚本预览（WRITE_BITS）")
        preview_key.setObjectName("gpioSection")
        lay.addWidget(preview_key)
        self._export_preview = QPlainTextEdit()
        self._export_preview.setObjectName("gpioMonoEdit")
        self._export_preview.setReadOnly(True)
        lay.addWidget(self._export_preview, 1)

        export_btn = QPushButton("Export")
        export_btn.setObjectName("gpioPrimary")
        export_btn.setIcon(_icon("copy.svg", "#E2E8F0", 12))
        export_btn.setToolTip("把全部 GPIO 配置合并为 WRITE_BITS 脚本并复制到剪贴板")
        export_btn.clicked.connect(self._on_export_copy)
        lay.addWidget(export_btn)
        return panel

    def _make_hsep(self):
        sep = QFrame()
        sep.setObjectName("gpioHSep")
        sep.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return sep

    # 视图 2：Register Map
    def _build_regmap_view(self):
        page = QWidget()
        page.setObjectName("gpioViewPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        bar = QFrame()
        bar.setObjectName("gpioPanel")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(10, 5, 10, 5)
        bl.setSpacing(6)
        raw_key = QLabel("Raw Access")
        raw_key.setObjectName("gpioPanelKey")
        bl.addWidget(raw_key)
        self.raw_addr = HexWheelLineEdit()
        self.raw_addr.setObjectName("gpioHexEdit")
        self.raw_addr.setPlaceholderText("ADDR 0x40081000")
        self.raw_addr.setFixedWidth(150)
        bl.addWidget(self.raw_addr)
        self.raw_data = HexWheelLineEdit()
        self.raw_data.setObjectName("gpioHexEdit")
        self.raw_data.setPlaceholderText("DATA 0x00000001")
        self.raw_data.setFixedWidth(140)
        bl.addWidget(self.raw_data)
        self.raw_write_btn = QPushButton("Write32")
        self.raw_write_btn.setObjectName("gpioBtn")
        self.raw_write_btn.clicked.connect(self._on_raw_write)
        bl.addWidget(self.raw_write_btn)
        self.raw_read_btn = QPushButton("Read32")
        self.raw_read_btn.setObjectName("gpioBtn")
        self.raw_read_btn.clicked.connect(self._on_raw_read)
        bl.addWidget(self.raw_read_btn)
        self.raw_result = QLabel("--")
        self.raw_result.setObjectName("gpioAddr")
        bl.addWidget(self.raw_result)
        bl.addStretch(1)
        self.reg_refresh_btn = QPushButton("Refresh Readable")
        self.reg_refresh_btn.setObjectName("gpioBtn")
        self.reg_refresh_btn.setToolTip("回读 VAL_IN / PU / PD / DRV 等可读寄存器")
        self.reg_refresh_btn.clicked.connect(self._on_refresh_readable)
        bl.addWidget(self.reg_refresh_btn)
        lay.addWidget(bar)

        self._regmap_scroll = QScrollArea()
        self._regmap_scroll.setObjectName("gpioScroll")
        self._regmap_scroll.setWidgetResizable(True)
        self._regmap_scroll.setFrameShape(QFrame.NoFrame)
        self._regmap_container = QWidget()
        self._regmap_container.setObjectName("gpioViewPage")
        self._regmap_grid = QGridLayout(self._regmap_container)
        self._regmap_grid.setContentsMargins(2, 2, 2, 2)
        self._regmap_grid.setSpacing(6)
        self._regmap_placeholder = QLabel("加载 DUT 配置后展示寄存器映射")
        self._regmap_placeholder.setObjectName("gpioStatus")
        self._regmap_placeholder.setAlignment(Qt.AlignCenter)
        self._regmap_grid.addWidget(self._regmap_placeholder, 0, 0)
        self._regmap_scroll.setWidget(self._regmap_container)
        lay.addWidget(self._regmap_scroll, 1)
        return page

    # 视图 3：I2C Bus Sniffer
    def _build_sniffer_view(self):
        page = QWidget()
        page.setObjectName("gpioViewPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        bar = QHBoxLayout()
        bar.setSpacing(4)
        self._sniff_chip_group = QButtonGroup(self)
        self._sniff_chip_group.setExclusive(True)
        all_btn = QPushButton("All")
        all_btn.setObjectName("gpioChip")
        all_btn.setCheckable(True)
        all_btn.setChecked(True)
        self._sniff_chip_group.addButton(all_btn, -1)
        bar.addWidget(all_btn)
        for i, kind in enumerate(self.SNIFF_KINDS):
            btn = QPushButton(kind)
            btn.setObjectName("gpioChip")
            btn.setCheckable(True)
            self._sniff_chip_group.addButton(btn, i)
            bar.addWidget(btn)
        self._sniff_chip_group.idClicked.connect(self._on_sniff_kind_changed)

        bar.addSpacing(6)
        self.sniff_search = QLineEdit()
        self.sniff_search.setObjectName("gpioSearch")
        self.sniff_search.setPlaceholderText("搜索地址 / 语义关键字")
        self.sniff_search.textChanged.connect(self._render_sniffer)
        bar.addWidget(self.sniff_search, 1)

        self.sniff_pause_btn = QPushButton("Pause")
        self.sniff_pause_btn.setObjectName("gpioBtn")
        self.sniff_pause_btn.setCheckable(True)
        self.sniff_pause_btn.setToolTip("暂停 / 恢复自动滚屏刷新")
        self.sniff_pause_btn.toggled.connect(self._on_sniff_pause)
        bar.addWidget(self.sniff_pause_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("gpioBtn")
        clear_btn.setIcon(_icon("trash.svg", "#94A3B8", 12))
        clear_btn.clicked.connect(self._on_sniff_clear)
        bar.addWidget(clear_btn)

        export_btn = QPushButton("Export .log")
        export_btn.setObjectName("gpioBtn")
        export_btn.setIcon(_icon("download.svg", "#94A3B8", 12))
        export_btn.clicked.connect(self._on_sniff_export)
        bar.addWidget(export_btn)
        lay.addLayout(bar)

        self.sniff_view = QTextEdit()
        self.sniff_view.setObjectName("gpioSniff")
        self.sniff_view.setReadOnly(True)
        lay.addWidget(self.sniff_view, 1)
        return page

    # 视图 4：DUT JSON Config
    def _build_json_view(self):
        page = QWidget()
        page.setObjectName("gpioViewPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.json_file_label = QLabel("chips/gpio_configs/--.json")
        self.json_file_label.setObjectName("gpioMono")
        bar.addWidget(self.json_file_label)
        bar.addStretch(1)
        for text, slot, tip in (
            ("Import JSON", self._on_json_import, "从本地磁盘载入芯片 JSON 文件"),
            ("Export JSON", self._on_json_export, "将编辑器内容导出为 JSON 文件"),
            ("Reload", self._on_json_reload, "放弃修改，重新从磁盘读取当前配置"),
            ("Apply Config", self._on_json_apply, "校验并写回 chips/gpio_configs/，立即生效"),
        ):
            btn = QPushButton(text)
            btn.setObjectName("gpioBtn")
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            bar.addWidget(btn)
        lay.addLayout(bar)

        self.json_err_label = QLabel("")
        self.json_err_label.setObjectName("gpioJsonErr")
        lay.addWidget(self.json_err_label)

        self.json_edit = QPlainTextEdit()
        self.json_edit.setObjectName("gpioMonoEdit")
        self.json_edit.setPlaceholderText(
            "DUT JSON 配置：gpio_banks 基地址 / drv_sel / pull_up_bases / pull_down_bases ...")
        lay.addWidget(self.json_edit, 1)
        return page

    # 视图 5：DUT Confirmation Note
    def _build_notes_view(self):
        page = QScrollArea()
        page.setObjectName("gpioScroll")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        container.setObjectName("gpioViewPage")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(6)

        self._note_status_labels = []
        self._note_bodies = []
        for i, title in enumerate((
            "1. PU / PD 上下拉寄存器地址",
            "2. 驱动强度档位与阻抗（drv_sel）",
            "3. I2C 7-bit 设备地址与位宽",
            "4. 通信桥接方式",
            "5. Pin function sel（复用为 GPIO）",
        )):
            card = QFrame()
            card.setObjectName("noteCard")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12, 8, 12, 8)
            cl.setSpacing(4)
            head = QHBoxLayout()
            t = QLabel(title)
            t.setObjectName("noteTitle")
            head.addWidget(t)
            head.addStretch(1)
            st = QLabel("--")
            st.setObjectName("noteStatus")
            head.addWidget(st)
            cl.addLayout(head)
            body = QLabel("-")
            body.setObjectName("noteBody")
            body.setWordWrap(True)
            cl.addWidget(body)
            lay.addWidget(card)
            self._note_status_labels.append(st)
            self._note_bodies.append(body)
        lay.addStretch(1)
        page.setWidget(container)
        return page

    # ================================================================ 状态访问

    def _ready(self):
        return self._cfg is not None and self._dev_addr is not None

    def _meta(self, group, pin):
        return self._pin_meta.setdefault((group, pin), {"alias": ""})

    def _alias(self, group, pin):
        return self._pin_meta.get((group, pin), {}).get("alias") or ""

    def _dir_bit(self, bank_idx, bit):
        return (self._dir_shadow.get(bank_idx, 0) >> bit) & 1

    def _out_bit(self, bank_idx, bit):
        return (self._out_shadow.get(bank_idx, 0) >> bit) & 1

    def _pull_state(self, group, bit):
        """0=Hi-Z 1=PU 2=PD（由 PU/PD 影子寄存器推导）。"""
        if self._cfg is None:
            return 0
        bank_idx = self._cfg.bank_index(group)
        pu_addr = self._cfg.pull_up_addr(group)
        pd_addr = self._cfg.pull_down_addr(group)
        pu = (self._reg_shadow.get(pu_addr, 0) >> bit) & 1 if pu_addr is not None else 0
        pd = (self._reg_shadow.get(pd_addr, 0) >> bit) & 1 if pd_addr is not None else 0
        if pu and not pd:
            return 1
        if pd and not pu:
            return 2
        return 0

    def _drv_field_value(self, group, pin):
        field_ = self._cfg.drv_field(group, pin) if self._cfg else None
        if field_ is None:
            return None
        addr, high, low = field_
        mask = (1 << (high - low + 1)) - 1
        return (self._reg_shadow.get(addr, 0) >> low) & mask

    def _drv_ohm_text(self, level):
        """该档位输出阻抗取整文本（"1463/1472 Ω"），无表返回 ""。"""
        hh, ll = self._cfg.drv_ohm(level)
        if hh is None or ll is None:
            return ""
        return "{0}/{1} Ω".format(round(hh), round(ll))

    def _drv_level_text(self, val):
        if val is None:
            return "Lv --"
        ohm = self._drv_ohm_text(val)
        return "Lv{0} · {1}".format(val, ohm) if ohm else "Lv{0}".format(val)

    def _func_sel_pin_actions(self, group, pin):
        """单脚控制前置：func sel 未选 GPIO 功能时生成配置动作（否则空）。"""
        field_ = self._cfg.func_sel_field(group, pin) if self._cfg else None
        if field_ is None:
            return []
        addr, high, low = field_
        mask = (1 << (high - low + 1)) - 1
        cur = (self._reg_shadow.get(addr, 0) >> low) & mask
        if cur == self._cfg.func_sel_gpio_value:
            return []
        return [(OP_BITS, addr, self._cfg.func_sel_gpio_value, high, low)]

    def _func_sel_mask_actions(self, bank_idx, bank_mask):
        """bank 位掩码涉及脚的 func sel 配置动作，按 group 合并整寄存器写
        （未涉及字段取影子值保持；影子已为 GPIO 功能时跳过该 group）。"""
        if self._cfg is None or not self._cfg.func_sel_supported:
            return []
        actions = []
        bits = self._cfg.func_sel_bits_per_gpio
        fmask = (1 << bits) - 1
        want = self._cfg.func_sel_gpio_value & fmask
        g0 = bank_idx * GROUPS_PER_BANK
        for g in range(g0, g0 + GROUPS_PER_BANK):
            field_ = self._cfg.func_sel_field(g, 0)
            if field_ is None:
                continue
            pins = (bank_mask >> ((g - g0) * PINS_PER_GROUP)) & 0xFF
            if not pins:
                continue
            addr = field_[0]
            cur = self._reg_shadow.get(addr, 0)
            new = cur
            for p in range(PINS_PER_GROUP):
                if (pins >> p) & 1:
                    new = (new & ~(fmask << (p * bits))) | (want << (p * bits))
            if new != cur:
                actions.append((OP_BITS, addr, new, 31, 0))
        return actions

    def _in_bit(self, bank_idx, bit):
        val = self._in_value.get(bank_idx)
        if val is None:
            return None
        return (val >> bit) & 1

    def _pin_mode(self, group, pin):
        """由影子寄存器推导工作模式（用于 label / Inspector）。"""
        bank_idx = self._cfg.bank_index(group)
        bit = self._cfg.bit_in_bank(group, pin)
        if self._dir_bit(bank_idx, bit):
            return MODE_OUT_HIGH if self._out_bit(bank_idx, bit) else MODE_OUT_LOW
        pull = self._pull_state(group, bit)
        if pull == 1:
            return MODE_IN_PULL_UP
        if pull == 2:
            return MODE_IN_PULL_DOWN
        return MODE_IN_FLOAT

    def _reset_session_state(self):
        self._selected = None
        self._pin_meta = {}
        self._dir_shadow = {i: 0 for i in range(len(self._cfg.banks))}
        self._out_shadow = {i: 0 for i in range(len(self._cfg.banks))}
        self._reg_shadow = {}
        self._in_value = {i: None for i in range(len(self._cfg.banks))}
        self._export_items = self._load_export_items()
        self._refresh_export_manager()

    # ================================================================ 刷新

    def _refresh_all_views(self):
        self._rebuild_bank_buttons()
        self._rebuild_matrix()
        self._rebuild_regmap()
        self._refresh_addr_bar()
        self._refresh_stats()
        self._refresh_inspector()
        self._refresh_notes()
        self._refresh_export_manager()
        self._update_op_enabled()

    def _refresh_after_hw(self):
        """硬件状态变化后的轻量刷新（不重建控件）。"""
        for group, pin in list(self._pin_cards.keys()):
            self._refresh_pin_card(group, pin)
        self._refresh_reg_cards()
        self._refresh_stats()
        self._refresh_inspector()

    def _rebuild_bank_buttons(self):
        for btn in self._bank_buttons:
            self._bank_group.removeButton(btn)
            btn.deleteLater()
        self._bank_buttons = []
        while self._bank_box.count():
            item = self._bank_box.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        count = len(self._cfg.banks) if self._cfg else 0
        if count == 0:
            lbl = QLabel("--")
            lbl.setObjectName("gpioDim")
            self._bank_box.addWidget(lbl)
            return
        if self._cur_bank >= count:
            self._cur_bank = 0
        for i in range(count):
            bank = self._cfg.banks[i]
            g0 = i * GROUPS_PER_BANK
            g1 = g0 + GROUPS_PER_BANK - 1
            btn = QPushButton(str(i))
            btn.setObjectName("gpioBankBtn")
            btn.setCheckable(True)
            btn.setToolTip("Bank {0} · {1} · GPIO_Group{2}~{3} · base {4}".format(
                i, bank.name, g0, g1, _fmt32(bank.base)))
            self._bank_group.addButton(btn, i)
            self._bank_box.addWidget(btn)
            self._bank_buttons.append(btn)
        self._bank_buttons[self._cur_bank].setChecked(True)

    def _rebuild_matrix(self):
        for col in (self._matrix_col_l, self._matrix_col_r):
            while col.count():
                item = col.takeAt(0)
                if item.widget() is not None:
                    item.widget().deleteLater()
        self._pin_cards = {}
        if self._cfg is None:
            ph = QLabel("请先 i2c.bes_chip_check() 或加载 DUT Profile")
            ph.setObjectName("gpioStatus")
            ph.setAlignment(Qt.AlignCenter)
            self._matrix_col_l.addWidget(ph)
            self._matrix_col_l.addStretch(1)
            self._matrix_col_r.addStretch(1)
            return
        base_group = self._cur_bank * GROUPS_PER_BANK
        for bit in range(GPIOS_PER_BANK - 1, -1, -1):
            group = base_group + bit // PINS_PER_GROUP
            pin = bit % PINS_PER_GROUP
            card = _PinCard(
                group, pin,
                on_select=self._on_pin_clicked,
                on_dir=self._on_card_dir,
                on_level=self._on_card_level,
                on_pull=self._on_card_pull,
                on_menu=self._on_pin_context_menu)
            # 两列排布：左列 BIT31~16 自上往下，右列 BIT15~0 自上往下
            # 行距 0，相邻行以 alt 斑马纹背景区分
            if bit >= 16:
                row, col = 31 - bit, self._matrix_col_l
            else:
                row, col = 15 - bit, self._matrix_col_r
            card.setProperty("alt", str(row % 2))
            col.addWidget(card)
            self._pin_cards[(group, pin)] = card
            self._refresh_pin_card(group, pin)

    def _refresh_pin_card(self, group, pin):
        card = self._pin_cards.get((group, pin))
        if card is None or self._cfg is None:
            return
        bank_idx = self._cfg.bank_index(group)
        bit = self._cfg.bit_in_bank(group, pin)
        linear = self._cfg.linear_index(group, pin)
        alias = self._alias(group, pin)
        card.name_label.setText(self._cfg.gpio_name(group, pin))
        card.bit_label.setText("BIT{0:02d}".format(bit))
        card.alias_label.setText(alias)
        card.setToolTip("{0} · {1} BIT{2:02d} · 全局 #{3}".format(
            self._cfg.gpio_name(group, pin), self._cfg.banks[bank_idx].name,
            bit, linear))

        is_out = bool(self._dir_bit(bank_idx, bit))
        card.dir_btn.setText("OUT" if is_out else "IN")
        card.dir_btn.setProperty("cur", "out" if is_out else "in")
        _repolish(card.dir_btn)

        if is_out:
            lvl = self._out_bit(bank_idx, bit)
            card.level_btn.setText("H" if lvl else "L")
            card.level_btn.setProperty("cur", "h" if lvl else "l")
        else:
            in_lvl = self._in_bit(bank_idx, bit)
            if in_lvl is not None:
                card.level_btn.setText(str(in_lvl))
                card.level_btn.setProperty("cur", "h" if in_lvl else "l")
            else:
                card.level_btn.setText("-")
                card.level_btn.setProperty("cur", "")
        _repolish(card.level_btn)

        pull_ok = self._cfg.pull_supported(group)
        pull = self._pull_state(group, bit)
        card.pull_btn.setText({0: "Z", 1: "PU", 2: "PD"}[pull])
        card.pull_btn.setProperty("cur", {0: "", 1: "pu", 2: "pd"}[pull])
        card.pull_btn.setEnabled(pull_ok)
        card.pull_btn.setToolTip(
            "上下拉轮转 Hi-Z -> PU -> PD" if pull_ok
            else "该 Bank 上下拉地址未在 JSON 配置 (pull_up/pull_down_bases)")
        _repolish(card.pull_btn)

        if is_out:
            lvl_prop = "h" if self._out_bit(bank_idx, bit) else "l"
        else:
            in_lvl = self._in_bit(bank_idx, bit)
            lvl_prop = {0: "l", 1: "h"}.get(in_lvl, "x")
        if card.property("lvl") != lvl_prop:
            card.setProperty("lvl", lvl_prop)
            _repolish(card)
        card.setProperty("sel", "1" if self._selected == (group, pin) else "0")
        _repolish(card)

    def _rebuild_regmap(self):
        while self._regmap_grid.count():
            item = self._regmap_grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._reg_cards = []
        if self._cfg is None:
            ph = QLabel("加载 DUT 配置后展示寄存器映射")
            ph.setObjectName("gpioStatus")
            ph.setAlignment(Qt.AlignCenter)
            self._regmap_grid.addWidget(ph, 0, 0)
            return
        bank = self._cfg.banks[self._cur_bank]
        specs = [
            ("val_set", bank.base + OFFSET_OUT_SET, "VAL_SET",
             "输出置位：写 1 -> 对应位输出 HIGH", False),
            ("dir_set", bank.base + OFFSET_DIR_SET, "DIR_SET",
             "方向置位：写 1 -> 对应位设为 OUTPUT", False),
            ("val_clr", bank.base + OFFSET_OUT_CLR, "VAL_CLR",
             "输出清零：写 1 -> 对应位输出 LOW", False),
            ("dir_clr", bank.base + OFFSET_DIR_CLR, "DIR_CLR",
             "方向清零：写 1 -> 对应位设为 INPUT", False),
            ("val_in", bank.base + OFFSET_IN_READ, "VAL_IN",
             "输入电平读取（点击卡片刷新）", True),
        ]
        if self._cfg.drv_supported:
            for addr, first in self._cfg.drv_registers(self._cur_bank):
                specs.append(("drv", addr,
                              "DRV_GPIO{0}0".format(first // PINS_PER_GROUP),
                              "驱动强度 {0}bit/脚（点击位翻转档位）".format(
                                  self._cfg.drv_bits_per_gpio), True))
        if self._cfg.func_sel_supported:
            g0 = self._cur_bank * GROUPS_PER_BANK
            for g in range(g0, g0 + GROUPS_PER_BANK):
                field_ = self._cfg.func_sel_field(g, 0)
                if field_ is None:
                    continue
                specs.append(("fsel", field_[0], "FSEL_GPIO{0}0".format(g),
                              "功能复用选择：0x{0:X}=GPIO（控制前自动写）".format(
                                  self._cfg.func_sel_gpio_value), True))
        pu_addr = self._cfg.pull_up_bases[self._cur_bank] \
            if self._cur_bank < len(self._cfg.pull_up_bases) else None
        pd_addr = self._cfg.pull_down_bases[self._cur_bank] \
            if self._cur_bank < len(self._cfg.pull_down_bases) else None
        specs.append(("pu", pu_addr, "PU_REG", "上拉使能（1bit/脚，OP_BITS 位域写）", True))
        specs.append(("pd", pd_addr, "PD_REG", "下拉使能（1bit/脚，OP_BITS 位域写）", True))

        for i, (kind, addr, name, hint, readable) in enumerate(specs):
            card = self._make_reg_card(kind, addr, name, hint, readable)
            self._regmap_grid.addWidget(card["frame"], i // 2, i % 2)
            self._reg_cards.append(card)
        self._refresh_reg_cards()

    def _make_reg_card(self, kind, addr, name, hint, readable):
        frame = QFrame()
        frame.setObjectName("regCard")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(10, 6, 10, 8)
        lay.setSpacing(4)

        head = QHBoxLayout()
        head.setSpacing(6)
        n = QLabel(name)
        n.setObjectName("regCardName")
        head.addWidget(n)
        a = QLabel(_fmt32(addr) if addr is not None else "TBD")
        a.setObjectName("regCardAddr")
        head.addWidget(a)
        head.addStretch(1)
        v = QLabel("--")
        v.setObjectName("regCardVal")
        head.addWidget(v)
        if readable and addr is not None:
            r = QPushButton("R")
            r.setObjectName("gpioCellBtn")
            r.setToolTip("回读该寄存器")
            r.clicked.connect(lambda _=False, k=kind, ad=addr: self._on_reg_read(k, ad))
            head.addWidget(r)
        lay.addLayout(head)

        h = QLabel(hint if addr is not None else "地址待确认（JSON 未配置），写入已禁用")
        h.setObjectName("regCardHint")
        lay.addWidget(h)

        bit_row = QHBoxLayout()
        bit_row.setContentsMargins(0, 0, 0, 0)
        bit_row.setSpacing(2)
        bit_row.addStretch(1)
        bits = []
        for bit in range(31, -1, -1):
            b = QPushButton("0")
            b.setObjectName("regBit")
            b.setProperty("on", "0")
            b.setToolTip("Bit {0}".format(bit))
            if readable:
                b.setProperty("rd", "1")
            if addr is None:
                b.setEnabled(False)
            else:
                b.clicked.connect(
                    lambda _=False, k=kind, ad=addr, bi=bit: self._on_reg_bit(k, ad, bi))
            bit_row.addWidget(b)
            bits.append((bit, b))
        bit_row.addStretch(1)
        lay.addLayout(bit_row)
        return {"frame": frame, "kind": kind, "addr": addr, "val": v, "bits": bits}

    def _reg_card_value(self, kind, addr):
        if addr is None or self._cfg is None:
            return None
        bank = self._cfg.banks[self._cur_bank]
        if kind in ("val_set", "val_clr"):
            return self._out_shadow.get(self._cur_bank, 0)
        if kind in ("dir_set", "dir_clr"):
            return self._dir_shadow.get(self._cur_bank, 0)
        if kind == "val_in":
            return self._in_value.get(self._cur_bank)
        return self._reg_shadow.get(addr, 0)

    def _refresh_reg_cards(self):
        for card in self._reg_cards:
            value = self._reg_card_value(card["kind"], card["addr"])
            card["val"].setText("--" if value is None else _fmt32(value))
            shown = value or 0
            for bit, btn in card["bits"]:
                on = (shown >> bit) & 1
                if btn.text() != str(on):
                    btn.setText(str(on))
                if btn.property("on") != str(on):
                    btn.setProperty("on", str(on))
                    _repolish(btn)

    def _refresh_addr_bar(self):
        if self._cfg is None:
            self.addr_label.setText("Base --")
            self.bank_label.setText("Bank --")
            self.dut_sub.setText("DUT: --")
            return
        bank = self._cfg.banks[self._cur_bank]
        g0 = self._cur_bank * GROUPS_PER_BANK
        self.addr_label.setText("Base {0}".format(_fmt32(bank.base)))
        self.bank_label.setText("Bank{0} (GPIO_Group{1}~{2})".format(
            self._cur_bank, g0, g0 + GROUPS_PER_BANK - 1))
        mode = ("dev 0x{0:02X}".format(self._dev_addr)
                if self._dev_addr is not None else "--")
        self.dut_sub.setText("DUT: {0} · {1}".format(
            self._cfg.chip.upper(), mode))

    def _refresh_stats(self):
        vals = {k: "-" for k in self._stat_vals}
        if self._cfg is not None:
            b = self._cur_bank
            dir_v = self._dir_shadow.get(b, 0)
            out_n = _popcount(dir_v)
            vals["out"] = str(out_n)
            vals["in"] = str(GPIOS_PER_BANK - out_n)
            in_v = self._in_value.get(b)
            if in_v is not None:
                high_n = _popcount(in_v)
                vals["high"] = str(high_n)
                vals["low"] = str(GPIOS_PER_BANK - high_n)
            pu_addr = self._cfg.pull_up_bases[b] \
                if b < len(self._cfg.pull_up_bases) else None
            pd_addr = self._cfg.pull_down_bases[b] \
                if b < len(self._cfg.pull_down_bases) else None
            if pu_addr is not None:
                vals["pu"] = str(_popcount(self._reg_shadow.get(pu_addr, 0)))
            if pd_addr is not None:
                vals["pd"] = str(_popcount(self._reg_shadow.get(pd_addr, 0)))
        for k, v in self._stat_vals.items():
            v.setText(vals[k])

    def _refresh_inspector(self):
        sel = self._selected
        has = sel is not None and self._cfg is not None
        ready = self._ready()
        if not has:
            self.insp_name.setText("GPIO--")
            self.insp_info.setText("未选择引脚")
            self.insp_mask.setText("Mask --")
            self.alias_edit.setText("")
            self.insp_big_state.setText("LOGIC --")
            self.insp_big_state.setProperty("lvl", "")
            _repolish(self.insp_big_state)
        else:
            group, pin = sel
            bank_idx = self._cfg.bank_index(group)
            bit = self._cfg.bit_in_bank(group, pin)
            linear = self._cfg.linear_index(group, pin)
            is_out = bool(self._dir_bit(bank_idx, bit))
            self.insp_name.setText(self._cfg.gpio_name(group, pin))
            self.insp_info.setText("{0} BIT{1:02d} · Group{2} Pin{3} · 全局 #{4} · {5}".format(
                self._cfg.banks[bank_idx].name, bit,
                group, pin, linear, mode_label(self._pin_mode(group, pin))))
            if self.alias_edit.text() != self._alias(group, pin) \
                    and not self.alias_edit.hasFocus():
                self.alias_edit.setText(self._alias(group, pin))

            self.insp_dir_out.setProperty("cur", "1" if is_out else "0")
            self.insp_dir_in.setProperty("cur", "0" if is_out else "1")
            _repolish(self.insp_dir_out)
            _repolish(self.insp_dir_in)
            lvl = self._out_bit(bank_idx, bit)
            self.insp_lvl_h.setProperty("cur", "1" if (is_out and lvl) else "0")
            self.insp_lvl_l.setProperty("cur", "1" if (is_out and not lvl) else "0")
            _repolish(self.insp_lvl_h)
            _repolish(self.insp_lvl_l)

            pull = self._pull_state(group, bit)
            self.insp_pull_hiz.setProperty("cur", "1" if pull == 0 else "0")
            self.insp_pull_pu.setProperty("cur", "pu" if pull == 1 else "0")
            self.insp_pull_pd.setProperty("cur", "pd" if pull == 2 else "0")
            for b in (self.insp_pull_hiz, self.insp_pull_pu, self.insp_pull_pd):
                _repolish(b)
            if self._cfg.pull_up_ohm is not None \
                    and self._cfg.pull_down_ohm is not None:
                self.insp_pull_key.setText(
                    "上下拉三态（PU≈{0} Ω / PD≈{1} Ω）".format(
                        round(self._cfg.pull_up_ohm),
                        round(self._cfg.pull_down_ohm)))
            else:
                self.insp_pull_key.setText("上下拉三态（PU/PD 为 RW 寄存器位域写）")

            field_ = self._cfg.drv_field(group, pin)
            if field_ is not None:
                val = self._drv_field_value(group, pin)
                self.insp_drv_val.setText(self._drv_level_text(val))
                self.insp_drv_key.setText(
                    "驱动强度（{0} 位域 [{1}:{2}]，0~{3} 档阻抗取整）".format(
                        _fmt32(field_[0]), field_[1], field_[2],
                        self._cfg.drv_max_level))
            else:
                self.insp_drv_val.setText("Lv --")
                self.insp_drv_key.setText(
                    "驱动强度（{0}）".format(
                        "该引脚无 drv_sel 寄存器" if self._cfg.drv_supported
                        else "该芯片 JSON 未配置 drv_sel"))

            in_lvl = self._in_bit(bank_idx, bit)
            if in_lvl is None:
                self.insp_big_state.setText("LOGIC --")
                self.insp_big_state.setProperty("lvl", "")
            else:
                self.insp_big_state.setText(
                    "LOGIC {0} ({1})".format("HIGH" if in_lvl else "LOW", in_lvl))
                self.insp_big_state.setProperty("lvl", "h" if in_lvl else "l")
            _repolish(self.insp_big_state)

            drv_txt = ""
            if field_ is not None:
                drv_txt = " · drv {0} [{1}:{2}]".format(
                    _fmt32(field_[0]), field_[1], field_[2])
            self.insp_mask.setText(
                "Mask {0} · bank bit {1}{2}".format(_fmt32(1 << bit), bit, drv_txt))

        pull_ok = has and self._cfg.pull_supported(sel[0])
        drv_ok = has and self._cfg.drv_field(sel[0], sel[1]) is not None
        drv_val = self._drv_field_value(sel[0], sel[1]) if drv_ok else None
        for b in (self.insp_dir_out, self.insp_dir_in,
                  self.insp_lvl_h, self.insp_lvl_l, self.insp_read_btn):
            b.setEnabled(has and ready)
        for b in (self.insp_pull_hiz, self.insp_pull_pu, self.insp_pull_pd):
            b.setEnabled(has and ready and pull_ok)
        self.insp_drv_dec.setEnabled(
            ready and drv_val is not None and drv_val > 0)
        self.insp_drv_inc.setEnabled(
            ready and drv_val is not None and drv_val < self._cfg.drv_max_level)
        self.insp_drv_val.setEnabled(drv_ok)
        self.alias_edit.setEnabled(has)

    def _update_op_enabled(self):
        ready = self._ready()
        busy = self._busy()
        for btn in self._batch_buttons:
            btn.setEnabled(ready and not busy)
        self.mask_btn.setEnabled(ready and not busy)
        self.read_btn.setEnabled(ready and not busy)
        self.raw_write_btn.setEnabled(ready and not busy)
        self.raw_read_btn.setEnabled(ready and not busy)
        self.reg_refresh_btn.setEnabled(ready and not busy)
        self.poll_btn.setEnabled(ready)
        self.detect_btn.setEnabled(not busy)
        self.load_btn.setEnabled(not busy)

    # ================================================================ Sniffer

    def _sniff(self, kind, addr, data, semantic):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        parts = ["{0} [{1}]".format(ts, kind)]
        if addr is not None:
            parts.append("ADDR: {0}".format(_fmt32(addr)))
        if data is not None:
            parts.append("DATA: {0}".format(_fmt32(data)))
        parts.append(semantic)
        raw = "  ".join(parts)

        color = self._SNIFF_COLORS.get(kind, "#94A3B8")
        esc = semantic.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html = (
            '<span style="color:#475569">{0}</span> '
            '<span style="color:{1};font-weight:600">[{2}]</span> '.format(ts, color, kind))
        if addr is not None:
            html += '<span style="color:#22D3EE">ADDR: {0}</span> '.format(_fmt32(addr))
        if data is not None:
            html += '<span style="color:#F59E0B">DATA: {0}</span> '.format(_fmt32(data))
        html += '<span style="color:#94A3B8">{0}</span>'.format(esc)
        self._sniff_entries.append((kind, raw, html))
        if not self._sniff_paused and self._sniff_match(kind, raw):
            self.sniff_view.append(html)
            self._sniff_scroll_bottom()

    def _sniff_match(self, kind, raw):
        if self._sniff_kind and kind != self._sniff_kind:
            return False
        text = self.sniff_search.text().strip().lower()
        if text and text not in raw.lower():
            return False
        return True

    def _sniff_scroll_bottom(self):
        sb = self.sniff_view.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _render_sniffer(self):
        self.sniff_view.clear()
        for kind, raw, html in self._sniff_entries:
            if self._sniff_match(kind, raw):
                self.sniff_view.append(html)
        self._sniff_scroll_bottom()

    def _on_sniff_kind_changed(self, idx):
        self._sniff_kind = None if idx < 0 else self.SNIFF_KINDS[idx]
        self._render_sniffer()

    def _on_sniff_pause(self, paused):
        self._sniff_paused = paused
        self.sniff_pause_btn.setText("Resume" if paused else "Pause")
        if not paused:
            self._render_sniffer()

    def _on_sniff_clear(self):
        self._sniff_entries = []
        self.sniff_view.clear()

    def _on_sniff_export(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 I2C 嗅探日志",
            "gpio_i2c_sniffer_{0}.log".format(ts),
            "Log Files (*.log);;Text Files (*.txt);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("BES GPIO Workbench - I2C Bus Sniffer Log\n")
                f.write("Chip: {0}  Mode: USB-I2C Bridge\n".format(
                    self._cfg.chip if self._cfg else "--"))
                for _kind, raw, _html in self._sniff_entries:
                    f.write(raw + "\n")
            self.append_log("[EXPORT] 嗅探日志已导出: {0}".format(path))
        except OSError as e:
            logger.error("sniffer export failed: %s", e, exc_info=True)
            self.append_log("[ERROR] 嗅探日志导出失败: {0}".format(e))

    def _mask_pins(self, mask):
        bits = [i for i in range(32) if (mask >> i) & 1]
        if not bits:
            return "no pin (mask: {0})".format(_fmt32(mask))
        if len(bits) > 8:
            head = "{0} pins".format(len(bits))
        else:
            head = " ".join("BIT{0:02d}".format(i) for i in bits)
        return "{0} (mask: {1})".format(head, _fmt32(mask))

    def _describe_write(self, op, addr, value, hi, lo):
        cfg = self._cfg
        if cfg is not None:
            for bank in cfg.banks:
                off = addr - bank.base
                if off == OFFSET_OUT_SET:
                    return "Output control (set): Write 1 to be HIGH -> {0}".format(
                        self._mask_pins(value))
                if off == OFFSET_OUT_CLR:
                    return "Output control (clr): Write 1 to be LOW -> {0}".format(
                        self._mask_pins(value))
                if off == OFFSET_DIR_SET:
                    return "Dir control (set): Write 1 to be OUTPUT -> {0}".format(
                        self._mask_pins(value))
                if off == OFFSET_DIR_CLR:
                    return "Dir control (clr): Write 1 to be INPUT -> {0}".format(
                        self._mask_pins(value))
            for b_idx in range(len(cfg.banks)):
                pu = cfg.pull_up_bases[b_idx] if b_idx < len(cfg.pull_up_bases) else None
                pd = cfg.pull_down_bases[b_idx] if b_idx < len(cfg.pull_down_bases) else None
                if pu is not None and addr == pu:
                    return "Pull-up enable (RMW [{0}:{1}] = {2}) -> {3}".format(
                        hi, lo, value, self._mask_pins(
                            ((value & ((1 << (hi - lo + 1)) - 1)) << lo)))
                if pd is not None and addr == pd:
                    return "Pull-down enable (RMW [{0}:{1}] = {2}) -> {3}".format(
                        hi, lo, value, self._mask_pins(
                            ((value & ((1 << (hi - lo + 1)) - 1)) << lo)))
            g = cfg.func_sel_reg_group(addr)
            if g is not None:
                if lo == 0 and hi == 31:
                    return "Func sel: [31:0] = {0} -> Group{1} 全 8 脚".format(
                        _fmt32(value), g)
                pin = lo // cfg.func_sel_bits_per_gpio
                if pin < PINS_PER_GROUP:
                    tag = (" (GPIO function)"
                           if value == cfg.func_sel_gpio_value else "")
                    return "Func sel: [{0}:{1}] = 0x{2:X}{3} -> {4}".format(
                        hi, lo, value, tag, cfg.gpio_name(g, pin))
            if cfg.drv_supported:
                owner = cfg.drv_field_owner(addr, lo)
                if owner is not None:
                    g, p = owner
                    ohm = self._drv_ohm_text(value)
                    return "Drv strength: [{0}:{1}] = Lv{2}{3} -> {4}".format(
                        hi, lo, value,
                        " ({0})".format(ohm) if ohm else "",
                        cfg.gpio_name(g, p))
        if op == OP_BITS:
            return "Raw bits write [{0}:{1}] = 0x{2:X}".format(hi, lo, value)
        return "Raw register write"

    def _describe_read(self, addr, value):
        cfg = self._cfg
        if cfg is not None:
            for bank in cfg.banks:
                if addr == bank.base + OFFSET_IN_READ:
                    return "Input status read ({0} VAL_IN +0x50)".format(bank.name)
            for b_idx in range(len(cfg.banks)):
                pu = cfg.pull_up_bases[b_idx] if b_idx < len(cfg.pull_up_bases) else None
                pd = cfg.pull_down_bases[b_idx] if b_idx < len(cfg.pull_down_bases) else None
                if pu is not None and addr == pu:
                    return "Pull-up enable read (Bank{0})".format(b_idx)
                if pd is not None and addr == pd:
                    return "Pull-down enable read (Bank{0})".format(b_idx)
            g = cfg.func_sel_reg_group(addr)
            if g is not None:
                return "Func sel read (Group{0})".format(g)
            if cfg.drv_supported \
                    and any(a == addr for a, _ in cfg.drv_registers()):
                return "Drv strength read"
        return "Raw register read"

    # ================================================================ 执行管道

    def _busy(self):
        return self._thread is not None and self._thread.isRunning()

    def _run_worker(self, worker, on_done, on_error):
        """装配并启动单次 Worker 线程（QObject + moveToThread）。

        线程不挂父对象：本页为内嵌子页面，销毁时不走 closeEvent；
        worker 到页面的信号均为绑定方法连接（页面销毁自动断开），
        线程自身由 finished -> deleteLater 自清理，杜绝"运行中的
        QThread 随页面析构"导致的进程崩溃（access violation）。
        """
        if self._busy():
            return False
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        if hasattr(worker, "progress"):
            worker.progress.connect(self.append_log)
        self._worker_done_cb = on_done
        worker.finished.connect(self._on_worker_done)
        worker.error.connect(on_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_thread_cleanup)
        self._worker = worker
        self._thread = thread
        self._set_top_busy(True)
        thread.start()
        return True

    def _on_worker_done(self, *args):
        """worker.finished 统一分发（绑定方法连接，页面销毁自动断开）。"""
        cb, self._worker_done_cb = self._worker_done_cb, None
        if cb is not None:
            cb(*args)

    def _on_thread_cleanup(self):
        # 旧线程 finished 晚到时勿清新线程引用（sender 校验）
        sender = self.sender()
        if sender is not None and self._thread is not None \
                and sender is not self._thread:
            return
        self._thread = None
        self._worker = None
        self._set_top_busy(False)

    def _defer_read(self, fn, delay_ms=80):
        """延迟执行读操作（§26）；定时器为页内子对象，页面销毁自动失效。"""
        self._deferred_read_fn = fn
        self._deferred_timer.start(delay_ms)

    def _on_deferred_read(self):
        fn, self._deferred_read_fn = self._deferred_read_fn, None
        if fn is not None:
            fn()

    def _set_top_busy(self, busy):
        self._update_op_enabled()

    def _on_op_error(self, msg):
        self.append_log("[ERROR] {0}".format(msg))
        self._sniff("ERROR", None, None, "操作失败: {0}".format(msg))
        self._set_status("操作失败: {0}".format(msg), err=True)
        self._stop_spin()

    def _apply_to_shadow(self, actions):
        for op, addr, value, hi, lo in actions:
            if op == OP_BITS:
                cur = self._reg_shadow.get(addr, 0)
                mask = ((1 << (hi - lo + 1)) - 1) << lo
                self._reg_shadow[addr] = (cur & ~mask) | ((value << lo) & mask)
                continue
            matched = False
            if self._cfg is not None:
                for b_idx, bank in enumerate(self._cfg.banks):
                    off = addr - bank.base
                    if off == OFFSET_OUT_SET:
                        self._out_shadow[b_idx] = \
                            self._out_shadow.get(b_idx, 0) | value
                        matched = True
                        break
                    if off == OFFSET_OUT_CLR:
                        self._out_shadow[b_idx] = \
                            self._out_shadow.get(b_idx, 0) & ~value & 0xFFFFFFFF
                        matched = True
                        break
                    if off == OFFSET_DIR_SET:
                        self._dir_shadow[b_idx] = \
                            self._dir_shadow.get(b_idx, 0) | value
                        matched = True
                        break
                    if off == OFFSET_DIR_CLR:
                        self._dir_shadow[b_idx] = \
                            self._dir_shadow.get(b_idx, 0) & ~value & 0xFFFFFFFF
                        matched = True
                        break
            if not matched:
                self._reg_shadow[addr] = value & 0xFFFFFFFF

    def _apply_actions(self, actions, label="", on_done=None):
        """统一下发管道：嗅探 -> 影子更新 -> 硬件 Worker。"""
        if not actions:
            return False
        if not self._ready():
            self.append_log("[WARN] 未连接 DUT，请先 i2c.bes_chip_check()")
            return False
        if self._busy():
            self.append_log("[WARN] 上一操作仍在执行，请稍候 ({0})".format(label))
            return False
        for op, addr, value, hi, lo in actions:
            self._sniff("WRITE32", addr, value,
                        self._describe_write(op, addr, value, hi, lo))
        if label:
            self.append_log("[I2C] {0}".format(label))
        self._apply_to_shadow(actions)
        worker = GpioApplyWorker(
            None, self.speed_combo.currentData(), self._dev_addr,
            actions, label=label)
        return self._run_worker(
            worker,
            lambda: self._on_hw_applied(on_done),
            self._on_op_error)

    def _on_hw_applied(self, on_done=None):
        self._refresh_after_hw()
        if on_done is not None:
            on_done()

    def _read_registers(self, pairs, on_done=None):
        """pairs: [(key, addr)]；硬件走 Worker 异步读取。"""
        if not pairs:
            return False
        if not self._ready():
            self.append_log("[WARN] 未连接 DUT，无法读取")
            return False
        if self._busy():
            return False
        worker = GpioReadBanksWorker(
            None, self.speed_combo.currentData(), self._dev_addr, pairs)
        return self._run_worker(
            worker,
            lambda values: self._on_read_done(pairs, values, on_done),
            self._on_op_error)

    def _on_read_done(self, pairs, values, on_done=None):
        for key, addr in pairs:
            value = values.get(key)
            if value is None:
                continue
            desc = self._describe_read(addr, value)
            self._sniff("READ32", addr, value, desc)
            self.append_log("[I2C] READ {0} = {1}  {2}".format(
                _fmt32(addr), _fmt32(value), desc))
            matched = False
            if self._cfg is not None:
                for b_idx, bank in enumerate(self._cfg.banks):
                    if addr == bank.base + OFFSET_IN_READ:
                        self._in_value[b_idx] = value
                        matched = True
                        break
            if not matched:
                self._reg_shadow[addr] = value & 0xFFFFFFFF
        self._refresh_after_hw()
        if on_done is not None:
            on_done(values)

    # ================================================================ 事件：顶部

    def _on_tab_changed(self, idx):
        self._stack.setCurrentIndex(idx)

    def _on_spin_tick(self):
        self._spin_angle = (self._spin_angle + 90) % 360
        pm = tinted_svg_pixmap(os.path.join(_ICONS_DIR, "refresh-cw.svg"),
                               "#22D3EE", 13)
        if not pm.isNull():
            self.detect_btn.setIcon(
                QIcon(pm.transformed(QTransform().rotate(self._spin_angle))))

    def _start_spin(self):
        self._spin_angle = 0
        self._spin_timer.start()

    def _stop_spin(self):
        self._spin_timer.stop()
        self.detect_btn.setIcon(_icon("refresh-cw.svg", "#22D3EE", 13))

    def _on_detect_clicked(self):
        if self._busy():
            return
        self._sniff("CHIP_CHECK", None, None,
                    "i2c.bes_chip_check() -> dev 0x11 reg 0x40080000 (32bit)")
        self._set_status("检测中...")
        self._start_spin()
        self.append_log("[I2C] BES 芯片检测中...")
        worker = GpioChipCheckWorker(None, self.speed_combo.currentData())
        self._run_worker(worker, self._on_detect_done, self._on_op_error)

    def _on_detect_done(self, chip_info):
        self._stop_spin()
        self._chip_info = chip_info
        chip_name = chip_info.get("chip_name")
        main_die = chip_info.get("main_die")
        if chip_info.get("warning"):
            self.append_log("[WARN] {0}".format(chip_info["warning"]))
        if not main_die or not chip_info.get("main_die_i2c_addr"):
            self._cfg = None
            self._dev_addr = None
            self._set_status("Main-die 无法读取，请确认芯片已开机并处于非休眠状态",
                             err=True)
            self.append_log("[ERROR] Main-die 检测失败")
            self._sniff("ERROR", None, None, "Main-die 检测失败")
            self._refresh_all_views()
            return
        addr = chip_info["main_die_i2c_addr"]
        self._dev_addr = int(addr, 0) if isinstance(addr, str) else int(addr)
        self.append_log("[I2C] 检测结果: {0} {1} · dev=0x{2:02X}".format(
            main_die, chip_info.get("main_die_version") or "", self._dev_addr))
        self._sniff("CHIP_CHECK", None, None,
                    "识别结果: {0} {1} · main_die dev=0x{2:02X}".format(
                        main_die, chip_info.get("main_die_version") or "",
                        self._dev_addr))

        self._cfg = load_gpio_config(chip_name)
        if self._cfg is None:
            self._set_status(
                "{0} · 无 GPIO 配置 chips/gpio_configs/{1}.json".format(
                    main_die, chip_name), err=True)
            self.append_log(
                "[WARN] 未找到芯片 {0} 的 GPIO 配置，请添加 "
                "chips/gpio_configs/{0}.json".format(chip_name))
            self._refresh_all_views()
            return

        idx = self.profile_combo.findData(chip_name)
        if idx >= 0:
            self.profile_combo.blockSignals(True)
            self.profile_combo.setCurrentIndex(idx)
            self.profile_combo.blockSignals(False)

        self._reset_session_state()
        self._set_status("{0} {1} · dev 0x{2:02X} · {3} banks".format(
            main_die, chip_info.get("main_die_version") or "",
            self._dev_addr, len(self._cfg.banks)), ok=True)
        self.append_log("[I2C] GPIO 配置已加载: {0}（{1} banks / {2} GPIO）".format(
            self._cfg.chip, len(self._cfg.banks),
            len(self._cfg.banks) * GPIOS_PER_BANK))
        self._load_json_editor()
        self._refresh_all_views()
        # 检测完成后自动全量回读一轮输入电平（§26：延迟 ≥50ms 再起新线程）
        self._defer_read(self._start_read_all_banks)

    def _on_load_profile_clicked(self):
        if self._busy():
            return
        name = self.profile_combo.currentData()
        if not name:
            self._set_status("无可用 DUT Profile", err=True)
            return
        if self._dev_addr is None:
            self.append_log("[WARN] 请先 i2c.bes_chip_check() 再加载 Profile")
            self._set_status("请先 Detect DUT", err=True)
            return
        cfg = load_gpio_config(name)
        if cfg is None:
            self._set_status("Profile 加载失败: {0}".format(name), err=True)
            return
        self._cfg = cfg
        self._reset_session_state()
        self._sniff("CHIP_CHECK", None, None,
                    "DUT Profile 手动加载: {0}".format(name))
        self._set_status("Profile: {0} · {1} banks".format(name, len(cfg.banks)),
                         ok=True)
        self.append_log("[I2C] DUT Profile 已加载: {0}".format(name))
        self._load_json_editor()
        self._refresh_all_views()
        self._start_read_all_banks()

    def _on_bank_changed(self, idx):
        if idx == self._cur_bank or self._cfg is None:
            return
        self._cur_bank = idx
        self._selected = None
        self._rebuild_matrix()
        self._rebuild_regmap()
        self._refresh_addr_bar()
        self._refresh_stats()
        self._refresh_inspector()

    # ================================================================ 事件：批处理

    def _batch_apply(self, actions, label):
        if not self._ready():
            self.append_log("[WARN] 未连接 DUT，请先 Detect 或加载 Profile")
            return
        self._apply_actions(actions, label=label,
                            on_done=lambda: self._queue_bank_read(self._cur_bank))

    def _queue_bank_read(self, bank_idx):
        # §26：worker finished 槽链里再起读线程须延迟 ≥50ms
        self._defer_read(lambda: self._start_read_bank(bank_idx))

    def _on_batch_out_high(self):
        if self._cfg is None:
            return
        bank = self._cfg.banks[self._cur_bank]
        self._batch_apply(
            self._func_sel_mask_actions(self._cur_bank, 0xFFFFFFFF) + [
                (OP_WRITE, bank.base + OFFSET_DIR_SET, 0xFFFFFFFF, -1, -1),
                (OP_WRITE, bank.base + OFFSET_OUT_SET, 0xFFFFFFFF, -1, -1),
            ], "All OUT HIGH -> Bank{0}".format(self._cur_bank))

    def _on_batch_out_low(self):
        if self._cfg is None:
            return
        bank = self._cfg.banks[self._cur_bank]
        self._batch_apply(
            self._func_sel_mask_actions(self._cur_bank, 0xFFFFFFFF) + [
                (OP_WRITE, bank.base + OFFSET_DIR_SET, 0xFFFFFFFF, -1, -1),
                (OP_WRITE, bank.base + OFFSET_OUT_CLR, 0xFFFFFFFF, -1, -1),
            ], "All OUT LOW -> Bank{0}".format(self._cur_bank))

    def _on_batch_in_hiz(self):
        if self._cfg is None:
            return
        bank = self._cfg.banks[self._cur_bank]
        actions = self._func_sel_mask_actions(self._cur_bank, 0xFFFFFFFF)
        actions.append((OP_WRITE, bank.base + OFFSET_DIR_CLR, 0xFFFFFFFF, -1, -1))
        for addr in (self._cfg.pull_up_bases[self._cur_bank]
                     if self._cur_bank < len(self._cfg.pull_up_bases) else None,
                     self._cfg.pull_down_bases[self._cur_bank]
                     if self._cur_bank < len(self._cfg.pull_down_bases) else None):
            if addr is not None:
                actions.append((OP_BITS, addr, 0, 31, 0))
        self._batch_apply(actions, "All IN Hi-Z -> Bank{0}".format(self._cur_bank))

    def _on_batch_pull(self, up):
        if self._cfg is None:
            return
        b = self._cur_bank
        pu = self._cfg.pull_up_bases[b] if b < len(self._cfg.pull_up_bases) else None
        pd = self._cfg.pull_down_bases[b] if b < len(self._cfg.pull_down_bases) else None
        if pu is None or pd is None:
            self.append_log("[WARN] Bank{0} 上下拉地址未在 JSON 配置".format(b))
            return
        actions = self._func_sel_mask_actions(b, 0xFFFFFFFF)
        actions += [
            (OP_BITS, pd if up else pu, 0, 31, 0),
            (OP_BITS, pu if up else pd, 0xFFFFFFFF, 31, 0),
        ]
        self._batch_apply(
            actions, "All {0} -> Bank{1}".format("PU" if up else "PD", b))

    def _on_batch_invert(self):
        if self._cfg is None:
            return
        bank = self._cfg.banks[self._cur_bank]
        b = self._cur_bank
        dir_v = self._dir_shadow.get(b, 0)
        out_v = self._out_shadow.get(b, 0)
        set_mask = (~out_v) & dir_v & 0xFFFFFFFF
        clr_mask = out_v & dir_v
        actions = self._func_sel_mask_actions(b, dir_v)
        if set_mask:
            actions.append((OP_WRITE, bank.base + OFFSET_OUT_SET, set_mask, -1, -1))
        if clr_mask:
            actions.append((OP_WRITE, bank.base + OFFSET_OUT_CLR, clr_mask, -1, -1))
        if not actions:
            self.append_log("[INFO] Bank{0} 无输出引脚可翻转".format(b))
            return
        self._batch_apply(actions, "Invert OUT -> Bank{0}".format(b))

    def _on_mask_write_clicked(self):
        if not self._ready():
            self.append_log("[WARN] 未连接 DUT，无法写入掩码")
            return
        mask = _parse_hex(self.mask_edit.text())
        if mask is None:
            self._set_status("掩码格式非法（示例 0x000000FF）", err=True)
            return
        bank = self._cfg.banks[self._cur_bank]
        off = self.mask_target.currentData()
        addr = bank.base + off
        self._apply_actions(
            self._func_sel_mask_actions(self._cur_bank, mask)
            + [(OP_WRITE, addr, mask, -1, -1)],
            label="Mask inject {0} -> {1}".format(
                _fmt32(mask), self.mask_target.currentText()),
            on_done=lambda: self._queue_bank_read(self._cur_bank))

    def _on_poll_toggled(self):
        if self._poll_timer.isActive():
            self._stop_polling()
            return
        if not self._ready():
            self.append_log("[WARN] 未连接 DUT，无法启动轮询")
            return
        self._poll_timer.start(self.poll_combo.currentData())
        self.poll_btn.setText("Stop Poll")
        self.poll_btn.setProperty("on", "1")
        _repolish(self.poll_btn)
        self.append_log("[I2C] 0x50 定时轮询已启动（{0}）".format(
            self.poll_combo.currentText()))

    def _stop_polling(self):
        if self._poll_timer.isActive():
            self._poll_timer.stop()
            self.append_log("[I2C] 0x50 定时轮询已停止")
        self.poll_btn.setText("Start Poll")
        self.poll_btn.setProperty("on", "0")
        _repolish(self.poll_btn)

    def _on_poll_interval_changed(self):
        if self._poll_timer.isActive():
            self._poll_timer.start(self.poll_combo.currentData())

    def _on_poll_tick(self):
        if self._busy() or not self._ready():
            return
        self._start_read_bank(self._cur_bank)

    # ================================================================ 事件：读取

    def _on_read_bank_clicked(self):
        if not self._ready():
            self.append_log("[WARN] 未连接 DUT，无法读取")
            return
        self._start_read_bank(self._cur_bank)

    def _start_read_all_banks(self):
        """全量回读可读状态：各 bank 0x50 电平 + PU/PD + drv + func_sel。"""
        if self._cfg is None or self._dev_addr is None:
            return
        cfg = self._cfg
        pairs = []
        for i, bank in enumerate(cfg.banks):
            pairs.append((i, bank.base + OFFSET_IN_READ))
            for addr in (cfg.pull_up_bases[i] if i < len(cfg.pull_up_bases) else None,
                         cfg.pull_down_bases[i] if i < len(cfg.pull_down_bases) else None):
                if addr is not None:
                    pairs.append(("reg_{0:08X}".format(addr), addr))
        seen = set()
        for addr, _first in cfg.drv_registers():
            if addr not in seen:
                seen.add(addr)
                pairs.append(("reg_{0:08X}".format(addr), addr))
        for g in range(cfg.group_count):
            field_ = cfg.func_sel_field(g, 0)
            if field_ is not None and field_[0] not in seen:
                seen.add(field_[0])
                pairs.append(("reg_{0:08X}".format(field_[0]), field_[0]))
        self.append_log("[I2C] 回读全部 IO 状态（电平/上下拉/drv/func_sel）...")
        self._read_registers(pairs)

    def _start_read_bank(self, bank_idx):
        if self._cfg is None or bank_idx >= len(self._cfg.banks):
            return
        bank = self._cfg.banks[bank_idx]
        self._read_registers([(bank_idx, bank.base + OFFSET_IN_READ)])

    def _on_refresh_readable(self):
        if not self._ready():
            return
        pairs = []
        bank = self._cfg.banks[self._cur_bank]
        pairs.append((self._cur_bank, bank.base + OFFSET_IN_READ))
        b = self._cur_bank
        for addr in (self._cfg.pull_up_bases[b] if b < len(self._cfg.pull_up_bases) else None,
                     self._cfg.pull_down_bases[b] if b < len(self._cfg.pull_down_bases) else None):
            if addr is not None:
                pairs.append(("reg_{0:08X}".format(addr), addr))
        for card in self._reg_cards:
            if card["kind"] in ("drv", "fsel") and card["addr"] is not None:
                pairs.append(("reg_{0:08X}".format(card["addr"]), card["addr"]))
        self._read_registers(pairs)

    def _on_raw_write(self):
        if not self._ready():
            self.append_log("[WARN] 未连接 DUT，无法写入")
            return
        addr = _parse_hex(self.raw_addr.text())
        data = _parse_hex(self.raw_data.text())
        if addr is None or data is None:
            self._set_status("Raw 地址 / 数据格式非法", err=True)
            return
        self._apply_actions([(OP_WRITE, addr, data, -1, -1)],
                            label="Raw write {0} = {1}".format(
                                _fmt32(addr), _fmt32(data)))

    def _on_raw_read(self):
        if not self._ready():
            self.append_log("[WARN] 未连接 DUT，无法读取")
            return
        addr = _parse_hex(self.raw_addr.text())
        if addr is None:
            self._set_status("Raw 地址格式非法", err=True)
            return
        self._read_registers(
            [("raw", addr)],
            on_done=lambda values: self.raw_result.setText(
                _fmt32(values.get("raw", 0))))

    def _on_reg_read(self, kind, addr):
        if not self._ready():
            return
        if kind == "val_in":
            self._start_read_bank(self._cur_bank)
        else:
            self._read_registers([("reg_{0:08X}".format(addr), addr)])

    # ================================================================ 事件：引脚操作

    def _on_pin_clicked(self, group, pin):
        self._selected = (group, pin)
        for key in self._pin_cards:
            self._refresh_pin_card(*key)
        self._refresh_inspector()

    def _on_card_dir(self, group, pin):
        if not self._ready():
            return
        self._selected = (group, pin)
        bank_idx = self._cfg.bank_index(group)
        bit = self._cfg.bit_in_bank(group, pin)
        out_now = bool(self._dir_bit(bank_idx, bit))
        addr = (self._cfg.dir_clr_addr(group) if out_now
                else self._cfg.dir_set_addr(group))
        name = self._cfg.gpio_name(group, pin)
        self._apply_actions(
            self._func_sel_pin_actions(group, pin)
            + [(OP_WRITE, addr, 1 << bit, -1, -1)],
            label="{0} -> {1}".format(name, "INPUT" if out_now else "OUTPUT"),
            on_done=lambda: self._queue_bank_read(bank_idx))

    def _on_card_level(self, group, pin):
        if not self._ready():
            return
        self._selected = (group, pin)
        bank_idx = self._cfg.bank_index(group)
        bit = self._cfg.bit_in_bank(group, pin)
        name = self._cfg.gpio_name(group, pin)
        if not self._dir_bit(bank_idx, bit):
            self._on_input_read(group, pin)
            return
        high_now = bool(self._out_bit(bank_idx, bit))
        addr = (self._cfg.out_clr_addr(group) if high_now
                else self._cfg.out_set_addr(group))
        self._apply_actions(
            self._func_sel_pin_actions(group, pin)
            + [(OP_WRITE, addr, 1 << bit, -1, -1)],
            label="{0} -> {1}".format(name, "LOW" if high_now else "HIGH"),
            on_done=lambda: self._queue_bank_read(bank_idx))

    def _on_input_read(self, group, pin):
        """输入脚点击：触发所属 Bank 0x50 输入电平回读。"""
        if not self._ready():
            return
        self._start_read_bank(self._cfg.bank_index(group))

    def _on_card_pull(self, group, pin):
        if not self._ready() or not self._cfg.pull_supported(group):
            return
        self._selected = (group, pin)
        bit = self._cfg.bit_in_bank(group, pin)
        nxt = (self._pull_state(group, bit) + 1) % 3
        self._apply_pull(group, pin, nxt)

    def _apply_pull(self, group, pin, state):
        bit = self._cfg.bit_in_bank(group, pin)
        pu = self._cfg.pull_up_addr(group)
        pd = self._cfg.pull_down_addr(group)
        name = self._cfg.gpio_name(group, pin)
        label = {0: "Hi-Z", 1: "Pull-Up", 2: "Pull-Down"}[state]
        actions = self._func_sel_pin_actions(group, pin)
        if state == 0:
            actions.append((OP_BITS, pu, 0, bit, bit))
            actions.append((OP_BITS, pd, 0, bit, bit))
        elif state == 1:
            actions.append((OP_BITS, pd, 0, bit, bit))
            actions.append((OP_BITS, pu, 1, bit, bit))
        else:
            actions.append((OP_BITS, pu, 0, bit, bit))
            actions.append((OP_BITS, pd, 1, bit, bit))
        self._apply_actions(
            actions, label="{0} pull -> {1}".format(name, label),
            on_done=lambda: self._queue_bank_read(self._cfg.bank_index(group)))

    def _on_drv_step(self, delta):
        if self._selected is None:
            return
        group, pin = self._selected
        cur = self._drv_field_value(group, pin)
        if cur is None:
            return
        self._apply_drv(group, pin, cur + delta)

    def _apply_drv(self, group, pin, level):
        if not self._ready():
            return
        actions = self._cfg.build_drv_actions(group, pin, level)
        name = self._cfg.gpio_name(group, pin)
        if actions is None:
            self.append_log("[WARN] {0} 不支持 drv 配置".format(name))
            return
        level = actions[0][2]
        ohm = self._drv_ohm_text(level)
        actions = self._func_sel_pin_actions(group, pin) + actions
        self._apply_actions(
            actions, label="{0} drv -> Lv{1}{2}".format(
                name, level, " ({0})".format(ohm) if ohm else ""))

    def _on_insp_dir(self, output):
        if self._selected is None or not self._ready():
            return
        group, pin = self._selected
        addr = (self._cfg.dir_set_addr(group) if output
                else self._cfg.dir_clr_addr(group))
        bit = self._cfg.bit_in_bank(group, pin)
        name = self._cfg.gpio_name(group, pin)
        self._apply_actions(
            self._func_sel_pin_actions(group, pin)
            + [(OP_WRITE, addr, 1 << bit, -1, -1)],
            label="{0} dir -> {1}".format(name, "OUTPUT" if output else "INPUT"),
            on_done=lambda: self._queue_bank_read(self._cfg.bank_index(group)))

    def _on_insp_level(self, high):
        if self._selected is None or not self._ready():
            return
        group, pin = self._selected
        addr = (self._cfg.out_set_addr(group) if high
                else self._cfg.out_clr_addr(group))
        bit = self._cfg.bit_in_bank(group, pin)
        name = self._cfg.gpio_name(group, pin)
        self._apply_actions(
            self._func_sel_pin_actions(group, pin)
            + [(OP_WRITE, addr, 1 << bit, -1, -1)],
            label="{0} level -> {1}".format(name, "HIGH" if high else "LOW"),
            on_done=lambda: self._queue_bank_read(self._cfg.bank_index(group)))

    def _on_insp_pull(self, state):
        if self._selected is None or not self._ready():
            return
        group, pin = self._selected
        if not self._cfg.pull_supported(group):
            self.append_log("[WARN] 该 Bank 上下拉地址未配置")
            return
        self._apply_pull(group, pin, state)

    def _on_alias_edited(self):
        if self._selected is None or self._cfg is None:
            return
        group, pin = self._selected
        alias = self.alias_edit.text().strip()
        self._meta(group, pin)["alias"] = alias
        self._refresh_pin_card(group, pin)
        if alias:
            self.append_log("[INFO] {0} 别名 -> {1}".format(
                self._cfg.gpio_name(group, pin), alias))

    # ================================================================ 事件：寄存器视图

    def _on_reg_bit(self, kind, addr, bit):
        if not self._ready():
            return
        bank = self._cfg.banks[self._cur_bank]
        mask = 1 << bit
        if kind == "val_set":
            self._apply_actions(
                [(OP_WRITE, bank.base + OFFSET_OUT_SET, mask, -1, -1)],
                label="Bit flip VAL_SET bit{0}".format(bit),
                on_done=lambda: self._queue_bank_read(self._cur_bank))
        elif kind == "val_clr":
            self._apply_actions(
                [(OP_WRITE, bank.base + OFFSET_OUT_CLR, mask, -1, -1)],
                label="Bit flip VAL_CLR bit{0}".format(bit),
                on_done=lambda: self._queue_bank_read(self._cur_bank))
        elif kind == "dir_set":
            self._apply_actions(
                [(OP_WRITE, bank.base + OFFSET_DIR_SET, mask, -1, -1)],
                label="Bit flip DIR_SET bit{0}".format(bit),
                on_done=lambda: self._queue_bank_read(self._cur_bank))
        elif kind == "dir_clr":
            self._apply_actions(
                [(OP_WRITE, bank.base + OFFSET_DIR_CLR, mask, -1, -1)],
                label="Bit flip DIR_CLR bit{0}".format(bit),
                on_done=lambda: self._queue_bank_read(self._cur_bank))
        elif kind == "val_in":
            self._start_read_bank(self._cur_bank)
        elif kind in ("drv", "fsel"):
            bits = (self._cfg.drv_bits_per_gpio if kind == "drv"
                    else self._cfg.func_sel_bits_per_gpio)
            low = bit - (bit % bits)
            high = low + bits - 1
            fmask = (1 << bits) - 1
            cur = (self._reg_shadow.get(addr, 0) >> low) & fmask
            new = cur ^ (1 << (bit - low))
            new_txt = ("Lv{0}".format(new) if kind == "drv"
                       else "0x{0:X}".format(new))
            self._apply_actions(
                [(OP_BITS, addr, new, high, low)],
                label="Bit flip {0} [{1}:{2}] -> {3}".format(
                    kind.upper(), high, low, new_txt))
        elif kind in ("pu", "pd"):
            cur = (self._reg_shadow.get(addr, 0) >> bit) & 1
            self._apply_actions(
                [(OP_BITS, addr, 0 if cur else 1, bit, bit)],
                label="Bit flip {0} bit{1}".format(kind.upper(), bit),
                on_done=lambda: self._queue_bank_read(self._cur_bank))

    # ================================================================ JSON 配置视图

    def _config_path(self, chip_name):
        import chips
        return os.path.join(
            os.path.dirname(os.path.abspath(chips.__file__)),
            "gpio_configs", "{0}.json".format(chip_name.lower()))

    def _load_json_editor(self):
        self.json_err_label.setText("")
        if self._cfg is None:
            self.json_edit.setPlainText("")
            self.json_file_label.setText("chips/gpio_configs/--.json")
            self._json_path = None
            return
        path = self._config_path(self._cfg.chip)
        self._json_path = path
        self.json_file_label.setText(
            "chips/gpio_configs/{0}.json".format(self._cfg.chip.lower()))
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.json_edit.setPlainText(f.read())
        except OSError as e:
            logger.error("read gpio json failed: %s", e, exc_info=True)
            self.json_edit.setPlainText("")
            self.json_err_label.setText("读取失败: {0}".format(e))

    def _on_json_reload(self):
        self._load_json_editor()
        self.append_log("[INFO] JSON 配置已从磁盘重新载入")

    def _on_json_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入芯片 JSON 配置", "", "JSON Files (*.json);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.json_edit.setPlainText(f.read())
            self.json_err_label.setText("")
            self.append_log("[INFO] 已导入 JSON: {0}（未生效，需 Apply Config）".format(path))
        except OSError as e:
            logger.error("import gpio json failed: %s", e, exc_info=True)
            self.json_err_label.setText("导入失败: {0}".format(e))

    def _on_json_export(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        chip = self._cfg.chip.lower() if self._cfg else "dut"
        path, _ = QFileDialog.getSaveFileName(
            self, "导出芯片 JSON 配置",
            "{0}_gpio_config_{1}.json".format(chip, ts),
            "JSON Files (*.json);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.json_edit.toPlainText())
            self.append_log("[EXPORT] JSON 配置已导出: {0}".format(path))
        except OSError as e:
            logger.error("export gpio json failed: %s", e, exc_info=True)
            self.json_err_label.setText("导出失败: {0}".format(e))

    def _on_json_apply(self):
        text = self.json_edit.toPlainText()
        try:
            raw = json.loads(text)
        except ValueError as e:
            self.json_err_label.setText("JSON 语法错误: {0}".format(e))
            self.append_log("[ERROR] JSON 语法校验失败: {0}".format(e))
            return
        banks = raw.get("gpio_banks")
        if not isinstance(banks, list) or not banks:
            self.json_err_label.setText("校验失败: gpio_banks 缺失或为空")
            return
        chip = str(raw.get("chip") or self.profile_combo.currentData() or "dut")
        path = self._config_path(chip)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(raw, f, indent=2, ensure_ascii=False)
                f.write("\n")
        except OSError as e:
            logger.error("apply gpio json failed: %s", e, exc_info=True)
            self.json_err_label.setText("写回失败: {0}".format(e))
            self.append_log("[ERROR] JSON 写回失败: {0}".format(e))
            return
        self.json_err_label.setText("")
        cfg = load_gpio_config(chip)
        if cfg is None:
            self.json_err_label.setText("配置已写盘但解析失败，请检查字段")
            return
        self._cfg = cfg
        idx = self.profile_combo.findData(chip.lower())
        if idx < 0:
            self.profile_combo.addItem(chip.upper(), chip.lower())
            idx = self.profile_combo.findData(chip.lower())
        self.profile_combo.blockSignals(True)
        self.profile_combo.setCurrentIndex(idx)
        self.profile_combo.blockSignals(False)
        self._reset_session_state()
        self._set_status("配置已生效: {0} · {1} banks".format(chip, len(cfg.banks)),
                         ok=True)
        self.append_log("[I2C] Apply Config 生效: {0}，引脚图谱与寄存器映射已重算"
                        .format(chip))
        self._sniff("CHIP_CHECK", None, None,
                    "Apply JSON Config -> {0}".format(chip))
        self._load_json_editor()
        self._refresh_all_views()
        self._start_read_all_banks()

    # ================================================================ Export Manager

    def _on_pin_context_menu(self, group, pin, pos):
        """Pin Matrix 卡片右键：Export Config 二级菜单收集导出配置。"""
        if not self._ready():
            return
        self._on_pin_clicked(group, pin)
        menu = QMenu(self)
        sub = menu.addMenu("Export Config")
        for label, mode in self.EXPORT_MODES:
            act = sub.addAction(label)
            if (mode in (MODE_IN_PULL_UP, MODE_IN_PULL_DOWN)
                    and not self._cfg.pull_supported(group)):
                act.setEnabled(False)
            act.triggered.connect(
                lambda checked=False, g=group, p=pin, m=mode:
                self._add_export_item(g, p, m))
        menu.exec(pos)

    def _add_export_item(self, group, pin, mode):
        item = (group, pin, mode)
        name = self._cfg.gpio_name(group, pin)
        label = self._EXPORT_MODE_LABELS[mode]
        if item in self._export_items:
            self.append_log("[INFO] {0}（{1}）已在导出列表".format(name, label))
            return
        self._export_items.append(item)
        self._save_export_items()
        self._refresh_export_manager()
        self.append_log("[EXPORT] 加入导出：{0}（{1}）".format(name, label))

    def _remove_export_item(self, index):
        if not (0 <= index < len(self._export_items)):
            return
        group, pin, mode = self._export_items.pop(index)
        self._save_export_items()
        self._refresh_export_manager()
        self.append_log("[EXPORT] 移出导出：{0}（{1}）".format(
            self._cfg.gpio_name(group, pin), self._EXPORT_MODE_LABELS[mode]))

    def _clear_export_items(self):
        if not self._export_items:
            return
        self._export_items = []
        self._save_export_items()
        self._refresh_export_manager()
        self.append_log("[EXPORT] 导出列表已清空")

    def _export_store_path(self):
        return os.path.join(get_user_data_dir("gpio"), "export_items.json")

    def _save_export_items(self):
        """导出列表按芯片持久化到 user_data（重开窗口自动恢复）。"""
        if self._cfg is None:
            return
        path = self._export_store_path()
        data = {}
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError) as e:
                logger.warning("读取 GPIO 导出列表存档失败: %s", e, exc_info=True)
        if not isinstance(data, dict):
            data = {}
        if self._export_items:
            data[self._cfg.chip] = [list(it) for it in self._export_items]
        else:
            data.pop(self._cfg.chip, None)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
        except OSError as e:
            logger.warning("保存 GPIO 导出列表失败: %s", e, exc_info=True)

    def _load_export_items(self):
        """按当前芯片恢复导出列表（校验脚位范围 / mode / 上下拉支持）。"""
        if self._cfg is None:
            return []
        path = self._export_store_path()
        if not os.path.isfile(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            logger.warning("读取 GPIO 导出列表失败: %s", e, exc_info=True)
            return []
        raw = data.get(self._cfg.chip, []) if isinstance(data, dict) else []
        items = []
        for entry in raw if isinstance(raw, list) else []:
            try:
                group, pin, mode = entry
                group, pin = int(group), int(pin)
            except (TypeError, ValueError):
                continue
            if not (0 <= group < self._cfg.group_count
                    and 0 <= pin < PINS_PER_GROUP):
                continue
            if mode not in self._EXPORT_MODE_LABELS:
                continue
            if (mode in (MODE_IN_PULL_UP, MODE_IN_PULL_DOWN)
                    and not self._cfg.pull_supported(group)):
                continue
            item = (group, pin, mode)
            if item not in items:
                items.append(item)
        return items

    def _refresh_export_manager(self):
        has = self._cfg is not None and bool(self._export_items)
        self._export_panel.setVisible(has)
        if not has:
            return
        self._export_count.setText("({0})".format(len(self._export_items)))
        while self._export_list_lay.count():
            item = self._export_list_lay.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        for idx, (group, pin, mode) in enumerate(self._export_items):
            row = QFrame()
            row.setObjectName("exportRow")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(6, 0, 4, 0)
            rl.setSpacing(6)
            name = QLabel(self._cfg.gpio_name(group, pin))
            name.setObjectName("pinName")
            rl.addWidget(name)
            mode_lb = QLabel(self._EXPORT_MODE_LABELS[mode])
            mode_lb.setObjectName("exportMode")
            rl.addWidget(mode_lb, 1)
            del_btn = QPushButton()
            del_btn.setObjectName("exportDel")
            del_btn.setIcon(_icon("x-close.svg", "#94A3B8", 10))
            del_btn.setToolTip("移出导出列表")
            del_btn.clicked.connect(
                lambda checked=False, i=idx: self._remove_export_item(i))
            rl.addWidget(del_btn)
            self._export_list_lay.addWidget(row)
        self._export_list_lay.addStretch(1)
        self._export_preview.setPlainText(self._gen_export_script())

    def _gen_export_script(self):
        """导出列表 -> 单段合并 WRITE_BITS 脚本。

        段名合并全部 GPIO 编号（如 GPIO05_62_63_Config，同脚去重）；
        每脚动作块前以 `  - //GPIO名_mode` 注释标注来源。
        """
        if self._cfg is None or not self._export_items:
            return ""
        lines = ["# WRITE_BITS <reg_addr_hex> <high_bit> <low_bit> <value_hex>"
                 "  # 写入特定位"]
        names = list(dict.fromkeys(
            self._cfg.gpio_name(group, pin)
            for group, pin, _ in self._export_items))
        title = names[0] + "".join("_" + n[4:] for n in names[1:])
        lines.append(title + "_Config:")
        for group, pin, mode in self._export_items:
            lines.append("  - //{0}_{1}".format(
                self._cfg.gpio_name(group, pin), mode))
            actions = self._cfg.build_func_sel_actions(group, pin) or []
            if mode in (MODE_OUT_HIGH, MODE_OUT_LOW):
                # 输出模式显式关闭上下拉，避免残留输入上下拉状态
                bit = self._cfg.bit_in_bank(group, pin)
                pu = self._cfg.pull_up_addr(group)
                pd = self._cfg.pull_down_addr(group)
                if pu is not None:
                    actions.append((OP_BITS, pu, 0, bit, bit))
                if pd is not None:
                    actions.append((OP_BITS, pd, 0, bit, bit))
            actions += self._cfg.build_mode_actions(group, pin, mode) or []
            for op, addr, value, hi, lo in actions:
                lines.append("  - " + _write_bits_line(op, addr, value, hi, lo))
        return "\n".join(lines)

    def _on_export_copy(self):
        text = self._export_preview.toPlainText()
        if not text:
            return
        QApplication.clipboard().setText(text)
        self.append_log("[EXPORT] GPIO 配置脚本已复制到剪贴板（{0} 项）".format(
            len(self._export_items)))

    # ================================================================ 确认清单视图

    def _refresh_notes(self):
        cfg = self._cfg
        # 1. PU/PD 地址
        if cfg is None:
            self._note_bodies[0].setText("加载 DUT 配置后显示上下拉寄存器地址确认状态。")
            self._set_note_status(0, "--", False)
        else:
            lines = []
            all_ok = True
            for i in range(len(cfg.banks)):
                pu = cfg.pull_up_bases[i] if i < len(cfg.pull_up_bases) else None
                pd = cfg.pull_down_bases[i] if i < len(cfg.pull_down_bases) else None
                if pu is None or pd is None:
                    all_ok = False
                lines.append("Bank{0}: PU={1} PD={2}".format(
                    i,
                    _fmt32(pu) if pu is not None else "TBD",
                    _fmt32(pd) if pd is not None else "TBD"))
            self._note_bodies[0].setText(
                "PU/PD 各一个独立寄存器区（1bit/GPIO，与 gpio_banks 平行）；"
                "地址为 null 时 UI 自动禁用上下拉按钮。\n" + "\n".join(lines))
            self._set_note_status(0, "已确认" if all_ok else "待确认 (TBD)", all_ok)
        # 2. drv 档位与阻抗
        if cfg is None or not cfg.drv_supported:
            self._note_bodies[1].setText(
                "当前芯片 JSON 未配置 drv_sel。")
            self._set_note_status(1, "待确认", False)
        else:
            lines = ["Group{0}: {1}".format(first // PINS_PER_GROUP,
                                            _fmt32(addr))
                     for addr, first in cfg.drv_registers()]
            ohm_txt = ("已配置 0~{0} 档输出阻抗表（UI 取整显示 Ω）。"
                       .format(cfg.drv_max_level)
                       if cfg.drv_out_high_ohm and cfg.drv_out_low_ohm
                       else "未配置档位阻抗表（仅显示档位号）。")
            self._note_bodies[1].setText(
                "drv_sel per-group 寄存器：每 32bit 寄存器 8 脚 × {0}bit，"
                "pin N 位域 [N*{0}+{1}:N*{0}]，档位 0~{2}（阻值越小驱动越强）；"
                "地址不连续时由 JSON group_bases 显式给出。\n{3}\n{4}"
                .format(cfg.drv_bits_per_gpio, cfg.drv_bits_per_gpio - 1,
                        cfg.drv_max_level, "\n".join(lines), ohm_txt))
            self._set_note_status(1, "已确认", True)
        # 3. I2C 地址
        dev_txt = ("0x{0:02X}".format(self._dev_addr)
                   if self._dev_addr is not None else "--")
        self._note_bodies[2].setText(
            "Main-die 32bit 地址空间（GPIO 寄存器位于 0x4008xxxx）；"
            "设备地址由 bes_chip_check() 返回的 main_die_i2c_addr 决定"
            "（0x11 / 0x31 自适应），位宽固定 BIT_32。\n"
            "当前会话 dev = {0}。".format(dev_txt))
        self._set_note_status(
            2, "已连接" if self._dev_addr is not None else "未连接",
            self._dev_addr is not None)
        # 4. 桥接
        self._note_bodies[3].setText(
            "当前：USB-I2C 物理工装桥接（I2CInterface DLL，经 "
            "core/gpio/ Worker 异步收发，页面无阻塞 I2C）。")
        self._set_note_status(3, "USB-I2C", True)
        # 5. func sel
        if cfg is None or not cfg.func_sel_supported:
            self._note_bodies[4].setText("当前芯片 JSON 未配置 func_sel。")
            self._set_note_status(4, "待确认", False)
        else:
            per_reg = 32 // cfg.func_sel_bits_per_gpio
            n = cfg.func_sel_groups or cfg.group_count
            self._note_bodies[4].setText(
                "pin function 复用选择：base {0}，每寄存器 {1} 脚 × {2}bit，"
                "有效 Group0~{3}；控制 GPIO 状态（方向/电平/上下拉/drv/批处理/"
                "掩码）前页面自动把对应脚位域写 0x{4:X} 选为 GPIO 功能，"
                "影子已为 0x{4:X} 时跳过。\n"
                "注意：RegMap 位翻转 / Raw 为底层调试入口，不自动前置 func sel。"
                .format(_fmt32(cfg.func_sel_base), per_reg,
                        cfg.func_sel_bits_per_gpio, n - 1,
                        cfg.func_sel_gpio_value))
            self._set_note_status(4, "已确认", True)

    def _set_note_status(self, idx, text, ok):
        lbl = self._note_status_labels[idx]
        lbl.setText(text)
        lbl.setProperty("ok", "1" if ok else "0")
        _repolish(lbl)

    # ================================================================ 通用

    def _set_status(self, text, ok=False, err=False):
        self.status_label.setText(text)
        self.status_label.setProperty("ok", "1" if ok else "0")
        self.status_label.setProperty("err", "1" if err else "0")
        _repolish(self.status_label)

    def append_log(self, msg):
        self.execution_logs.append_log(msg)

    def cleanup_threads(self):
        """关停定时器并等待 Worker 线程退出（CleanupMixin 契约）。

        MainWindow 关闭时经 _perform_close_cleanup 调用；closeEvent 复用。
        """
        try:
            self._stop_polling()
            self._spin_timer.stop()
            self._deferred_timer.stop()
            self._deferred_read_fn = None
            self._worker_done_cb = None
            if self._thread is not None and self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(2000)
        except Exception:
            logger.error("GPIO page cleanup wait failed", exc_info=True)

    def closeEvent(self, event):
        self.cleanup_threads()
        super().closeEvent(event)


if __name__ == "__main__":
    """独立运行：python ui/pages/gpio/gpio_control_ui.py"""
    from ui.standalone import run_standalone_widget

    def _create_window():
        window = GpioControlUI()
        icon_path = os.path.join(
            get_resource_base(), "resources", "icons", "kk_lab.ico")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            window.setWindowIcon(icon)
            app = QApplication.instance()
            if app is not None:
                app.setWindowIcon(icon)
        return window

    sys.exit(run_standalone_widget(
        _create_window, "BES GPIO Workbench", size=(1600, 950)))

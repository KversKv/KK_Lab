# -*- coding: utf-8 -*-
"""BES GPIO Workbench 页面样式与共享常量（调色板 QSS / 等宽字体 / 图标目录）。"""

import os

from resource_path import get_resource_base

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

/* ---- Export Manager Exec 执行按钮 ---- */
QPushButton#gpioExec {
    background-color: #14532D;
    color: #BBF7D0;
    border: 1px solid #22C55E;
    border-radius: 4px;
    padding: 0px 14px;
    font-family: """ + _MONO + """;
    font-size: 12px;
    font-weight: 600;
    min-height: 26px;
    max-height: 26px;
}
QPushButton#gpioExec:hover { background-color: #166534; }
QPushButton#gpioExec:disabled {
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
QScrollArea#multiSelList { min-height: 108px; max-height: 108px; }
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

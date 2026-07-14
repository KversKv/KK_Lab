# I2C 通用控制模块框架
#python -m ui.modules.i2c_module_frame

import os
import sys
import json
import re
import copy

if __name__ == "__main__" and __package__ in (None, ""):
    _PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from ui.resource_path import get_user_data_dir
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QSizePolicy, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFileDialog, QMessageBox, QMenu, QScrollArea, QStackedWidget,
    QButtonGroup
)
from PySide6.QtCore import (
    Qt, QThread, Signal, QObject, QTimer, QDateTime, QRegularExpression
)
from PySide6.QtGui import (
    QColor, QAction, QRegularExpressionValidator
)

from ui.widgets.dark_combobox import DarkComboBox
from log_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

I2C_BTN_HEIGHT = 22

_I2C_WIDTH_META = {}


def _load_width_meta():
    from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag
    return {
        I2CWidthFlag.BIT_8: ("8-bit", 8, 16),
        I2CWidthFlag.BIT_10: ("16-bit", 16, 16),
        I2CWidthFlag.BIT_32: ("32-bit", 32, 32),
    }


def _load_speed_options():
    from lib.i2c.Bes_I2CIO_Interface import I2CSpeedMode
    return [
        (I2CSpeedMode.SPEED_20K, "20 kHz"),
        (I2CSpeedMode.SPEED_100K, "100 kHz"),
        (I2CSpeedMode.SPEED_400K, "400 kHz"),
        (I2CSpeedMode.SPEED_750K, "750 kHz"),
    ]


# UI 数据位宽（8 / 16 / 32）→ I2CWidthFlag
_I2C_UI_WIDTHS = [(8, "8-bit"), (16, "16-bit"), (32, "32-bit")]


def _ui_width_to_flag(bits):
    from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag
    if bits == 8:
        return I2CWidthFlag.BIT_8
    if bits == 32:
        return I2CWidthFlag.BIT_32
    return I2CWidthFlag.BIT_10


def _width_label(flag):
    meta = _I2C_WIDTH_META.get(flag)
    return meta[0] if meta else str(flag)


def _reg_addr_bits(flag):
    meta = _I2C_WIDTH_META.get(flag)
    return meta[1] if meta else 16


def _data_bits(flag):
    meta = _I2C_WIDTH_META.get(flag)
    return meta[2] if meta else 16


def _hex_digits(bits):
    return max(1, (bits + 3) // 4)


def _fmt_hex(value, bits):
    return "0x%0{0}X".format(_hex_digits(bits)) % (int(value) & ((1 << bits) - 1))


def _fmt_bin(value, bits):
    return format(int(value) & ((1 << bits) - 1), "0{0}b".format(bits))


def _fmt_bin_grouped(value, bits):
    raw = _fmt_bin(value, bits)
    return " ".join(raw[i:i + 4] for i in range(0, len(raw), 4))


def _parse_hex_int(text):
    t = (text or "").strip()
    if not t:
        return 0
    neg = False
    if t.startswith("-"):
        neg = True
        t = t[1:]
    if t.lower().startswith("0x"):
        t = t[2:]
    if not re.fullmatch(r"[0-9a-fA-F]*", t):
        return None
    val = int(t, 16) if t else 0
    return -val if neg else val


def _i2c_template_dir():
    return get_user_data_dir("i2c_templates")


# ---------------------------------------------------------------------------
# 主题色（Tailwind Slate / Indigo / Emerald）
# ---------------------------------------------------------------------------

SLATE_950 = "#020617"
SLATE_900 = "#0f172a"
SLATE_800 = "#1e293b"
SLATE_700 = "#334155"
INDIGO = "#6366f1"
INDIGO_LIGHT = "#c7d2fe"
EMERALD = "#10b981"
EMERALD_LIGHT = "#34d399"
TEXT_MAIN = "#e2e8f0"
TEXT_MUTED = "#94a3b8"


# ---------------------------------------------------------------------------
# 样式
# ---------------------------------------------------------------------------

def _i2c_input_style():
    return (
        "QLineEdit {"
        f" background-color:{SLATE_950}; border:1px solid {SLATE_800};"
        " border-radius:6px; color:#e2e8f0;"
        " min-height:22px; max-height:22px; padding:0 8px;"
        " selection-background-color:#4f46e5;"
        " font-family:Consolas,'Cascadia Mono',monospace;"
        "}"
        f" QLineEdit:focus {{ border:1px solid {INDIGO}; }}"
        " QLineEdit:disabled { background-color:#0b1120; color:#475569;"
        " border:1px solid #1e293b; }"
    )


def _i2c_read_btn_style():
    return (
        "QPushButton {"
        f" background-color: rgba(16,185,129,0.12); border:1px solid {EMERALD};"
        " border-radius:6px; color:#34d399; font-weight:bold;"
        " min-height:22px; max-height:22px; padding:0 16px;"
        "}"
        " QPushButton:hover { background-color: rgba(16,185,129,0.22); }"
        " QPushButton:pressed { background-color: rgba(16,185,129,0.08); }"
        " QPushButton:disabled { background-color:#0b1120; color:#334155;"
        " border:1px solid #1e293b; }"
    )


def _i2c_write_btn_style():
    return (
        "QPushButton {"
        f" background-color: rgba(99,102,241,0.15); border:1px solid {INDIGO};"
        " border-radius:6px; color:#c7d2fe; font-weight:bold;"
        " min-height:22px; max-height:22px; padding:0 16px;"
        "}"
        " QPushButton:hover { background-color: rgba(99,102,241,0.28); }"
        " QPushButton:pressed { background-color: rgba(99,102,241,0.08); }"
        " QPushButton:disabled { background-color:#0b1120; color:#334155;"
        " border:1px solid #1e293b; }"
    )


def _i2c_subtle_btn_style():
    return (
        "QPushButton {"
        f" background-color:{SLATE_900}; border:1px solid {SLATE_800};"
        " border-radius:6px; color:#cbd5e1; font-weight:bold;"
        " min-height:22px; max-height:22px; padding:0 12px;"
        "}"
        f" QPushButton:hover {{ background-color:#1b2840; border:1px solid {INDIGO};"
        " color:#e2e8f0; }"
        " QPushButton:disabled { background-color:#0b1120; color:#475569;"
        " border:1px solid #1e293b; }"
    )


def _bit_val_style(on):
    if on:
        return (
            "QPushButton {"
            " background-color: rgba(16,185,129,0.20); border:1px solid #10b981;"
            " border-radius:4px; color:#34d399; font-weight:bold;"
            " min-height:22px; max-height:22px;"
            "}"
            " QPushButton:hover { background-color: rgba(16,185,129,0.34); }"
        )
    return (
        "QPushButton {"
        f" background-color:{SLATE_950}; border:1px solid {SLATE_800};"
        " border-radius:4px; color:#64748b; font-weight:bold;"
        " min-height:22px; max-height:22px;"
        "}"
        f" QPushButton:hover {{ background-color:{SLATE_900}; color:{TEXT_MUTED}; }}"
    )


def _i2c_table_qss():
    return (
        f"QTableWidget {{ background-color:{SLATE_950}; border:1px solid {SLATE_800};"
        " border-radius:8px; gridline-color:#1e293b; color:#e2e8f0; }"
        f"QHeaderView::section {{ background-color:{SLATE_900}; color:{TEXT_MUTED};"
        " border:0; border-right:1px solid #1e293b; padding:6px;"
        " font-weight:bold; font-size:11px; }"
        "QTableWidget::item { padding:2px 6px; }"
        "QTableWidget::item:selected { background-color: rgba(99,102,241,0.25); }"
        "QTableCornerButton::section { background:#0f172a; border:0; }"
    )


def _i2c_scrollbar_qss():
    return (
        "QScrollBar:vertical { background:transparent; width:8px; margin:0; }"
        "QScrollBar::handle:vertical { background:#334155; border-radius:4px;"
        " min-height:24px; }"
        "QScrollBar::handle:vertical:hover { background:#475569; }"
        "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }"
        "QScrollBar:horizontal { background:transparent; height:8px; margin:0; }"
        "QScrollBar::handle:horizontal { background:#334155; border-radius:4px;"
        " min-width:24px; }"
        "QScrollBar::handle:horizontal:hover { background:#475569; }"
        "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0; }"
    )


def _nav_tab_style():
    return (
        "QPushButton#navTab { background:transparent; border:none;"
        " border-bottom:2px solid transparent; color:#94a3b8;"
        " padding:8px 18px; font-size:11px; font-weight:bold; letter-spacing:1px;"
        "}"
        "QPushButton#navTab:hover { color:#e2e8f0; }"
        "QPushButton#navTab:checked { color:#c7d2fe;"
        " border-bottom:2px solid #6366f1; background: rgba(99,102,241,0.08); }"
    )


_I2C_DARK_STYLE = (
    f"QWidget {{ background-color:{SLATE_950}; color:{TEXT_MAIN}; }}"
    f"QLabel {{ background:transparent; color:{TEXT_MAIN}; border:none; }}"
    "QLabel#cardTitle { font-size:11px; font-weight:bold; color:#f8fafc;"
    " letter-spacing:1px; background:transparent; }"
    "QLabel#sectionTitle { font-size:10px; font-weight:bold; color:#94a3b8;"
    " letter-spacing:1px; background:transparent; }"
    "QLabel#appTitle { font-size:14px; font-weight:bold; color:#f8fafc;"
    " letter-spacing:1px; background:transparent; }"
    "QLabel#appBadge { background-color:#6366f1; color:#ffffff; border-radius:6px;"
    " font-weight:bold; font-size:10px; letter-spacing:1px; }"
    "QLabel#muted { color:#64748b; background:transparent; }"
    "QLabel#mono { font-family:Consolas,'Cascadia Mono',monospace;"
    f" background:transparent; color:{INDIGO_LIGHT}; }}"
    "QLabel#activityVal { font-family:Consolas,'Cascadia Mono',monospace;"
    " font-weight:bold; background:transparent; }"
    f"QFrame#card {{ background-color:{SLATE_900}; border:1px solid {SLATE_800};"
    " border-radius:12px; }"
    f"QFrame#navBar {{ background-color:{SLATE_900}; border:1px solid {SLATE_800};"
    " border-radius:12px; }"
    f"QFrame#workspace {{ background-color:{SLATE_900}; border:1px solid {SLATE_800};"
    " border-radius:12px; }"
    f"QFrame#footer {{ background-color:{SLATE_950}; border:1px solid {SLATE_800};"
    " border-radius:10px; }"
) + _i2c_scrollbar_qss()


# ---------------------------------------------------------------------------
# 异步 Worker（每次操作自建/销毁 I2CInterface）
# ---------------------------------------------------------------------------

class _I2cReadWorker(QObject):
    finished = Signal(int)
    error = Signal(str)

    def __init__(self, dll_path, speed_mode, device_addr, reg_addr,
                 width_flag, use_raw=False):
        super().__init__()
        self._dll = dll_path
        self._speed = speed_mode
        self._dev = device_addr
        self._reg = reg_addr
        self._width = width_flag
        self._raw = use_raw

    def run(self):
        from lib.i2c.i2c_interface_x64 import I2CInterface
        i2c = I2CInterface(dll_path=self._dll, speed_mode=self._speed)
        try:
            if not i2c.initialize():
                self.error.emit("I2C 接口初始化失败 (DLL 加载或设备打开失败)")
                return
            if self._raw:
                val = i2c.raw.read(
                    self._speed, self._dev, self._reg, self._width)
            else:
                val = i2c.read(self._dev, self._reg, self._width)
            self.finished.emit(int(val))
        except Exception as e:
            logger.error("I2C read failed: %s", e, exc_info=True)
            self.error.emit(str(e))
        finally:
            try:
                i2c.close()
            except Exception:
                pass


class _I2cWriteWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(self, dll_path, speed_mode, device_addr, reg_addr,
                 write_data, width_flag, high_bit=-1, low_bit=-1, use_raw=False):
        super().__init__()
        self._dll = dll_path
        self._speed = speed_mode
        self._dev = device_addr
        self._reg = reg_addr
        self._data = write_data
        self._width = width_flag
        self._high = high_bit
        self._low = low_bit
        self._raw = use_raw

    def run(self):
        from lib.i2c.i2c_interface_x64 import I2CInterface
        i2c = I2CInterface(dll_path=self._dll, speed_mode=self._speed)
        try:
            if not i2c.initialize():
                self.error.emit("I2C 接口初始化失败 (DLL 加载或设备打开失败)")
                return
            if self._raw:
                i2c.raw.write(
                    self._speed, self._dev, self._reg, self._data,
                    self._width, self._high, self._low)
            else:
                i2c.write(
                    self._dev, self._reg, self._data, self._width,
                    self._high, self._low)
            self.finished.emit()
        except Exception as e:
            logger.error("I2C write failed: %s", e, exc_info=True)
            self.error.emit(str(e))
        finally:
            try:
                i2c.close()
            except Exception:
                pass


class _I2cChipCheckWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, dll_path, speed_mode):
        super().__init__()
        self._dll = dll_path
        self._speed = speed_mode

    def run(self):
        from lib.i2c.i2c_interface_x64 import I2CInterface
        i2c = I2CInterface(dll_path=self._dll, speed_mode=self._speed)
        try:
            if not i2c.initialize():
                self.error.emit("I2C 接口初始化失败 (DLL 加载或设备打开失败)")
                return
            result = i2c.bes_chip_check()
            self.finished.emit(result)
        except Exception as e:
            logger.error("I2C chip check failed: %s", e, exc_info=True)
            self.error.emit(str(e))
        finally:
            try:
                i2c.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# 自定义控件：十六进制输入框（设备地址等）
# ---------------------------------------------------------------------------

class HexLineEdit(QLineEdit):
    """支持 0x 前缀的十六进制输入框，按 bit_count 限定取值范围。"""
    value_changed = Signal(int)

    def __init__(self, bit_count=16, parent=None):
        super().__init__(parent)
        self._bit_count = bit_count
        self._updating = False
        self.setAlignment(Qt.AlignCenter)
        self.set_value(0)
        self.textChanged.connect(self._on_text_changed)

    def set_bit_count(self, bit_count):
        self._bit_count = bit_count
        self.set_value(self.value())

    def _mask(self):
        return (1 << self._bit_count) - 1

    def _on_text_changed(self, text):
        if self._updating:
            return
        v = _parse_hex_int(text)
        if v is None:
            return
        self.value_changed.emit(v & self._mask())

    def value(self):
        v = _parse_hex_int(self.text())
        if v is None:
            return 0
        return v & self._mask()

    def set_value(self, v, emit=False):
        v = int(v) & self._mask()
        self._updating = True
        self.setText(_fmt_hex(v, self._bit_count))
        self._updating = False
        if emit:
            self.value_changed.emit(v)


# ---------------------------------------------------------------------------
# 自定义控件：寄存器地址输入框（智能 0x 前缀 / 大写 / 剥离非法字符）
# ---------------------------------------------------------------------------

class RegAddrInput(QLineEdit):
    """寄存器地址输入：自动剥离非法字符、固定 0x 前缀、自动大写。"""
    value_changed = Signal(int)

    def __init__(self, bit_count=16, parent=None):
        super().__init__(parent)
        self._bit_count = bit_count
        self._updating = False
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(_i2c_input_style())
        self.set_value(0)
        self.textChanged.connect(self._on_text_changed)

    def set_bit_count(self, bit_count):
        self._bit_count = bit_count
        self.set_value(self.value())

    def _mask(self):
        return (1 << self._bit_count) - 1

    def _on_text_changed(self, text):
        if self._updating:
            return
        clean = re.sub(r"[^0-9a-fA-F]", "", text)
        up = clean.upper()
        # 限定长度，避免超出位宽
        max_len = _hex_digits(self._bit_count)
        if len(up) > max_len:
            up = up[-max_len:]
        self._updating = True
        self.setText("0x" + up if up else "0x")
        self._updating = False
        val = int(up, 16) if up else 0
        self.value_changed.emit(val & self._mask())

    def value(self):
        t = self.text()
        if t.lower().startswith("0x"):
            t = t[2:]
        v = _parse_hex_int(t)
        return (v or 0) & self._mask()

    def set_value(self, v, emit=False):
        v = int(v) & self._mask()
        digits = _hex_digits(self._bit_count)
        self._updating = True
        self.setText("0x" + format(v, "0{0}X".format(digits)))
        self._updating = False
        if emit:
            self.value_changed.emit(v)


# ---------------------------------------------------------------------------
# 自定义控件：多进制数据值输入框（0x Hex / Dec / 0o Oct + 字符过滤）
# ---------------------------------------------------------------------------

_BASE_ITEMS = [("hex", "0x  Hex"), ("dec", "Dec"), ("oct", "0o  Oct")]
_BASE_VALIDATORS = {
    "hex": QRegularExpressionValidator(QRegularExpression("[0-9a-fA-F]{0,8}")),
    "dec": QRegularExpressionValidator(QRegularExpression("[0-9]{0,10}")),
    "oct": QRegularExpressionValidator(QRegularExpression("[0-7]{0,11}")),
}


class DataValueInput(QWidget):
    """数据总值输入：左侧进制切换下拉，右侧数值输入（按进制过滤字符）。"""
    value_changed = Signal(int)

    def __init__(self, bit_count=16, parent=None):
        super().__init__(parent)
        self._bit_count = bit_count
        self._base = "hex"
        self._updating = False

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self.base_combo = DarkComboBox(bg=SLATE_950, border=SLATE_800,
                                       hover_color=INDIGO)
        self.base_combo.setObjectName("dataBaseCombo")
        self.base_combo.setFixedHeight(I2C_BTN_HEIGHT)
        self.base_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        for key, text in _BASE_ITEMS:
            self.base_combo.addItem(text, userData=key)
        self.base_combo.setCurrentIndex(0)
        row.addWidget(self.base_combo)

        self.edit = QLineEdit()
        self.edit.setObjectName("dataValueEdit")
        self.edit.setFixedHeight(I2C_BTN_HEIGHT)
        self.edit.setAlignment(Qt.AlignCenter)
        self.edit.setStyleSheet(_i2c_input_style())
        self.edit.setValidator(_BASE_VALIDATORS["hex"])
        row.addWidget(self.edit, 1)

        self.base_combo.currentIndexChanged.connect(self._on_base_changed)
        self.edit.textChanged.connect(self._on_text_changed)
        self.set_value(0)

    def set_bit_count(self, bit_count):
        self._bit_count = bit_count
        self.set_value(self.value())

    def _mask(self):
        return (1 << self._bit_count) - 1

    def _format(self, v):
        v = int(v) & self._mask()
        if self._base == "hex":
            return format(v, "0{0}X".format(_hex_digits(self._bit_count)))
        if self._base == "oct":
            return format(v, "o")
        return str(v)

    def _parse(self, text):
        t = (text or "").strip()
        if not t:
            return 0
        try:
            if self._base == "hex":
                return int(t, 16) & self._mask()
            if self._base == "oct":
                return int(t, 8) & self._mask()
            return int(t, 10) & self._mask()
        except ValueError:
            return None

    def _on_base_changed(self, _idx):
        new_base = self.base_combo.currentData() or "hex"
        old_val = self.value()  # 用旧进制解析当前值
        self._base = new_base
        self.edit.setValidator(_BASE_VALIDATORS[new_base])
        self._updating = True
        self.edit.setText(self._format(old_val))
        self._updating = False

    def _on_text_changed(self, text):
        if self._updating:
            return
        v = self._parse(text)
        if v is None:
            return
        self.value_changed.emit(v)

    def value(self):
        return self._parse(self.edit.text()) or 0

    def set_value(self, v, emit=False):
        v = int(v) & self._mask()
        self._updating = True
        self.edit.setText(self._format(v))
        self._updating = False
        if emit:
            self.value_changed.emit(v)


# ---------------------------------------------------------------------------
# 自定义控件：位操作表格（Bit / Val / Field / Description / Hex + 字段合并）
# ---------------------------------------------------------------------------

class BitsTable(QTableWidget):
    """单段位表格。bit_offset/bit_count 决定显示区间（MSB 在上）。
    同一字段的多个 Bit 自动合并 Field/Description/Hex 单元格（rowSpan）。"""
    bit_toggled = Signal(int)  # 绝对位索引

    def __init__(self, bit_offset, bit_count, parent=None):
        super().__init__(0, 5, parent)
        self._offset = bit_offset
        self._count = bit_count
        self._fields = []
        self.setObjectName("bitsTable")
        self.setHorizontalHeaderLabels(["Bit", "Val", "Field", "Desc", "Hex"])
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet(_i2c_table_qss())
        hdr = self.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._build_rows()

    def _abs_bit(self, row):
        # row 0 = 本表最高位
        return self._offset + self._count - 1 - row

    def _row_of(self, abs_bit):
        return self._count - 1 - (abs_bit - self._offset)

    def _build_rows(self):
        self.setRowCount(0)
        for i in range(self._count):
            self.insertRow(i)
            bit = self._abs_bit(i)
            bi = QTableWidgetItem(str(bit))
            bi.setTextAlignment(Qt.AlignCenter)
            bi.setForeground(QColor(TEXT_MUTED))
            self.setItem(i, 0, bi)
            btn = QPushButton("0")
            btn.setObjectName("bitValBtn")
            btn.setFixedHeight(I2C_BTN_HEIGHT)
            btn.setStyleSheet(_bit_val_style(False))
            btn.clicked.connect(lambda _=False, b=bit: self.bit_toggled.emit(b))
            self.setCellWidget(i, 1, btn)
            for c in (2, 3, 4):
                it = QTableWidgetItem("")
                if c == 4:
                    it.setTextAlignment(Qt.AlignCenter)
                    it.setForeground(QColor(EMERALD_LIGHT))
                self.setItem(i, c, it)

    def set_bit_range(self, offset, count):
        self._offset = offset
        self._count = count
        self._build_rows()
        self._apply_fields()

    def set_value(self, full_value):
        for i in range(self._count):
            bit = self._abs_bit(i)
            on = bool((full_value >> bit) & 1)
            btn = self.cellWidget(i, 1)
            if btn is not None:
                btn.setText("1" if on else "0")
                btn.setStyleSheet(_bit_val_style(on))
        self._refresh_field_hex(full_value)

    def set_fields(self, all_fields):
        hi = self._offset + self._count - 1
        lo = self._offset
        self._fields = [f for f in all_fields
                        if int(f["high_bit"]) >= lo and int(f["low_bit"]) <= hi]
        self._apply_fields()

    def _apply_fields(self):
        self.clearSpans()
        tint = QColor(INDIGO)
        tint.setAlpha(38)
        base_bg = QColor(SLATE_900)
        base_bg.setAlpha(120)
        for i in range(self._count):
            for c in (2, 3, 4):
                it = self.item(i, c)
                if it is not None:
                    it.setText("")
                    it.setBackground(base_bg)
        hi = self._offset + self._count - 1
        lo = self._offset
        for f in self._fields:
            fhi = int(f["high_bit"])
            flo = int(f["low_bit"])
            if fhi < flo:
                fhi, flo = flo, fhi
            c_hi = min(fhi, hi)
            c_lo = max(flo, lo)
            row_top = self._row_of(c_hi)
            row_bot = self._row_of(c_lo)
            if row_top > row_bot:
                row_top, row_bot = row_bot, row_top
            span = row_bot - row_top + 1
            name_it = self.item(row_top, 2)
            desc_it = self.item(row_top, 3)
            if name_it is not None:
                name_it.setText(f["name"])
                name_it.setForeground(QColor(INDIGO_LIGHT))
            if desc_it is not None:
                desc_it.setText(f.get("description", ""))
                desc_it.setForeground(QColor(TEXT_MUTED))
            for r in range(row_top, row_bot + 1):
                for c in (2, 3, 4):
                    it = self.item(r, c)
                    if it is not None:
                        it.setBackground(tint)
            for c in (2, 3, 4):
                self.setSpan(row_top, c, span, 1)

    def _refresh_field_hex(self, full_value):
        for f in self._fields:
            fhi = int(f["high_bit"])
            flo = int(f["low_bit"])
            if fhi < flo:
                fhi, flo = flo, fhi
            width = fhi - flo + 1
            mask = (1 << width) - 1
            val = (full_value >> flo) & mask
            c_hi = min(fhi, self._offset + self._count - 1)
            row_top = self._row_of(c_hi)
            it = self.item(row_top, 4)
            if it is not None:
                it.setText(_fmt_hex(val, width))


# ---------------------------------------------------------------------------
# 自定义控件：位表容器（8/16-bit 单栏，32-bit 双栏并排）
# ---------------------------------------------------------------------------

class BitsTableContainer(QWidget):
    """位表容器：n<=16 单栏，n>16 自动拆分为双栏（高位左、低位右）。"""
    bit_toggled = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tables = []
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(10)

    def set_bit_count(self, n):
        for t in self._tables:
            t.bit_toggled.disconnect()
            self._layout.removeWidget(t)
            t.deleteLater()
        self._tables = []
        if n <= 16:
            t = BitsTable(0, n)
            t.bit_toggled.connect(self.bit_toggled)
            self._layout.addWidget(t, 1)
            self._tables.append(t)
        else:
            half = (n + 1) // 2  # 高位段位数
            hi_t = BitsTable(half, n - half)
            lo_t = BitsTable(0, half)
            for t in (hi_t, lo_t):
                t.bit_toggled.connect(self.bit_toggled)
            self._layout.addWidget(hi_t, 1)
            sep = QFrame()
            sep.setFrameShape(QFrame.VLine)
            sep.setStyleSheet(f"color:{SLATE_800}; background:transparent;")
            self._layout.addWidget(sep, 0)
            self._layout.addWidget(lo_t, 1)
            self._tables = [hi_t, lo_t]

    def set_value(self, full_value):
        for t in self._tables:
            t.set_value(full_value)

    def set_fields(self, fields):
        for t in self._tables:
            t.set_fields(fields)

    def refresh_fields(self, fields):
        for t in self._tables:
            t.set_fields(fields)


# ---------------------------------------------------------------------------
# 主 Mixin
# ---------------------------------------------------------------------------

class I2cMixin:
    """通用 I2C 控制 Mixin：按需初始化 I2C / 寄存器读写 / 位宽切换 /
    位域合并 / 寄存器映射 / 模板持久化 / 顶部导航 + 工作区布局。"""

    def init_i2c(self):
        global _I2C_WIDTH_META
        if not _I2C_WIDTH_META:
            _I2C_WIDTH_META = _load_width_meta()
        self._i2c_speed_options = _load_speed_options()

        self._i2c_read_thread = None
        self._i2c_read_worker = None
        self._i2c_write_thread = None
        self._i2c_write_worker = None
        self._i2c_chipcheck_thread = None
        self._i2c_chipcheck_worker = None
        self._i2c_custom_dll = None

        self._i2c_width = _ui_width_to_flag(16)
        self._i2c_data_bits = 16
        self._i2c_speed_mode = self._i2c_speed_options[1][0]  # 100K
        self._i2c_data_value = 0

        self._i2c_registers = []
        self._i2c_active_reg_index = None
        self._i2c_fields = []
        self._i2c_suppress_field_refresh = False
        self._i2c_readall_queue = []
        self._i2c_readall_results = {}
        self._i2c_pending_readall_idx = None

    def _i2c_dll_path(self):
        return getattr(self, "_i2c_custom_dll", None)

    # ---- UI 构建：整体框架（顶部导航 + 配置卡片 + 工作区） ----

    def build_i2c_widgets(self, layout, title_row=None):
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self._build_i2c_nav_bar(root)

        self.i2c_stack = QStackedWidget()
        self.i2c_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.i2c_ctrl_page = self._build_i2c_control_page()
        self.i2c_tpl_page = self._build_i2c_template_page()
        self.i2c_set_page = self._build_i2c_settings_page()
        self.i2c_stack.addWidget(self.i2c_ctrl_page)
        self.i2c_stack.addWidget(self.i2c_tpl_page)
        self.i2c_stack.addWidget(self.i2c_set_page)
        root.addWidget(self.i2c_stack, 1)

        layout.addLayout(root)
        self._i2c_sync_width_ui()

    def _build_i2c_nav_bar(self, layout):
        bar = QFrame()
        bar.setObjectName("navBar")
        bar.setFixedHeight(48)
        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 6, 10, 6)
        row.setSpacing(12)

        badge = QLabel("I2C")
        badge.setObjectName("appBadge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedHeight(26)
        badge.setFixedWidth(40)
        row.addWidget(badge)

        title = QLabel("I2C Console")
        title.setObjectName("appTitle")
        row.addWidget(title)
        row.addStretch()

        self.i2c_nav_group = QButtonGroup(self)
        self.i2c_nav_group.setExclusive(True)
        self.i2c_nav_tabs = []
        for text, idx in (("Control", 0), ("Templates", 1), ("Settings", 2)):
            btn = QPushButton(text)
            btn.setObjectName("navTab")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_nav_tab_style())
            btn.clicked.connect(lambda _=False, i=idx: self._on_i2c_nav_tab(i))
            self.i2c_nav_group.addButton(btn, idx)
            row.addWidget(btn)
            self.i2c_nav_tabs.append(btn)
        self.i2c_nav_tabs[0].setChecked(True)
        layout.addWidget(bar)

    def _on_i2c_nav_tab(self, idx):
        self.i2c_stack.setCurrentIndex(idx)

    # ---- 控制页：顶部配置卡片组 + 主工作区 ----

    def _build_i2c_control_page(self):
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self._build_i2c_top_cards(root)
        self._build_i2c_workspace(root)
        root.addStretch(0)
        return page

    def _build_i2c_top_cards(self, layout):
        row = QHBoxLayout()
        row.setSpacing(10)
        row.setContentsMargins(0, 0, 0, 0)
        self._build_i2c_device_config_card(row)
        self._build_i2c_activity_card(row)
        layout.addLayout(row)

    def _build_i2c_device_config_card(self, layout):
        card = QFrame()
        card.setObjectName("card")
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)

        t = QLabel("Device Config")
        t.setObjectName("cardTitle")
        v.addWidget(t)

        dev_row = QHBoxLayout()
        dev_row.setSpacing(8)
        dev_lbl = QLabel("Device Addr")
        dev_lbl.setObjectName("muted")
        dev_lbl.setFixedWidth(80)
        dev_row.addWidget(dev_lbl)
        self.i2c_dev_edit = HexLineEdit(_reg_addr_bits(self._i2c_width))
        self.i2c_dev_edit.setStyleSheet(_i2c_input_style())
        self.i2c_dev_edit.set_value(0x27)
        dev_row.addWidget(self.i2c_dev_edit, 1)
        v.addLayout(dev_row)

        w_row = QHBoxLayout()
        w_row.setSpacing(8)
        w_lbl = QLabel("Data Width")
        w_lbl.setObjectName("muted")
        w_lbl.setFixedWidth(80)
        w_row.addWidget(w_lbl)
        self.i2c_width_combo = DarkComboBox(bg=SLATE_950, border=SLATE_800,
                                            hover_color=INDIGO)
        self.i2c_width_combo.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_width_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for bits, text in _I2C_UI_WIDTHS:
            self.i2c_width_combo.addItem(text, userData=bits)
        self.i2c_width_combo.setCurrentIndex(1)
        w_row.addWidget(self.i2c_width_combo, 1)
        v.addLayout(w_row)

        layout.addWidget(card, 1)

    def _build_i2c_activity_card(self, layout):
        card = QFrame()
        card.setObjectName("card")
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)

        t = QLabel("Activity")
        t.setObjectName("cardTitle")
        v.addWidget(t)

        op_row = QHBoxLayout()
        op_row.setSpacing(8)
        op_lbl = QLabel("Last Op")
        op_lbl.setObjectName("muted")
        op_lbl.setFixedWidth(80)
        op_row.addWidget(op_lbl)
        self.i2c_activity_op = QLabel("—")
        self.i2c_activity_op.setObjectName("mono")
        op_row.addWidget(self.i2c_activity_op, 1)
        v.addLayout(op_row)

        time_row = QHBoxLayout()
        time_row.setSpacing(8)
        time_lbl = QLabel("Timestamp")
        time_lbl.setObjectName("muted")
        time_lbl.setFixedWidth(80)
        time_row.addWidget(time_lbl)
        self.i2c_activity_time = QLabel("—")
        self.i2c_activity_time.setObjectName("muted")
        time_row.addWidget(self.i2c_activity_time, 1)
        v.addLayout(time_row)

        val_row = QHBoxLayout()
        val_row.setSpacing(8)
        val_lbl = QLabel("Data Value")
        val_lbl.setObjectName("muted")
        val_lbl.setFixedWidth(80)
        val_row.addWidget(val_lbl)
        self.i2c_result_label = QLabel("—")
        self.i2c_result_label.setObjectName("activityVal")
        self.i2c_result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.i2c_result_label.setStyleSheet("color:#34d399;")
        val_row.addWidget(self.i2c_result_label, 1)
        v.addLayout(val_row)

        layout.addWidget(card, 1)

    # ---- 主工作区：Header（标题 + 二进制预览） + Body（位表） + Footer（操作栏） ----

    def _build_i2c_workspace(self, layout):
        ws = QFrame()
        ws.setObjectName("workspace")
        ws.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        v = QVBoxLayout(ws)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(10)

        # Header
        header = QHBoxLayout()
        header.setSpacing(10)
        h_title = QLabel("Payload Data Bits")
        h_title.setObjectName("cardTitle")
        header.addWidget(h_title)
        header.addStretch()
        bin_lbl = QLabel("BIN")
        bin_lbl.setObjectName("muted")
        bin_lbl.setFixedWidth(30)
        header.addWidget(bin_lbl, 0, Qt.AlignVCenter)
        self.i2c_bin_label = QLabel("")
        self.i2c_bin_label.setObjectName("mono")
        self.i2c_bin_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.i2c_bin_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        header.addWidget(self.i2c_bin_label, 1)
        v.addLayout(header)

        # Body：位操作表格
        body_wrap = QWidget()
        body_wrap.setStyleSheet("background:transparent;")
        bv = QVBoxLayout(body_wrap)
        bv.setContentsMargins(0, 0, 0, 0)
        bv.setSpacing(6)
        self.i2c_bits = BitsTableContainer()
        self.i2c_bits.set_bit_count(self._i2c_data_bits)
        bv.addWidget(self.i2c_bits, 1)
        v.addWidget(body_wrap, 1)

        # Footer：Register Addr + Data Value + Read/Write
        footer = QFrame()
        footer.setObjectName("footer")
        f_row = QHBoxLayout(footer)
        f_row.setContentsMargins(12, 8, 12, 8)
        f_row.setSpacing(10)

        reg_lbl = QLabel("Reg Addr")
        reg_lbl.setObjectName("muted")
        f_row.addWidget(reg_lbl)
        self.i2c_reg_edit = RegAddrInput(_reg_addr_bits(self._i2c_width))
        self.i2c_reg_edit.set_value(0x0000)
        self.i2c_reg_edit.setMinimumWidth(110)
        self.i2c_reg_edit.setMaximumWidth(160)
        f_row.addWidget(self.i2c_reg_edit)

        dv_lbl = QLabel("Data Value")
        dv_lbl.setObjectName("muted")
        f_row.addWidget(dv_lbl)
        self.i2c_data_edit = DataValueInput(self._i2c_data_bits)
        f_row.addWidget(self.i2c_data_edit, 1)

        self.i2c_read_btn = QPushButton("Read")
        self.i2c_read_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_read_btn.setCursor(Qt.PointingHandCursor)
        self.i2c_read_btn.setStyleSheet(_i2c_read_btn_style())
        self.i2c_write_btn = QPushButton("Write")
        self.i2c_write_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_write_btn.setCursor(Qt.PointingHandCursor)
        self.i2c_write_btn.setStyleSheet(_i2c_write_btn_style())
        f_row.addWidget(self.i2c_read_btn)
        f_row.addWidget(self.i2c_write_btn)
        v.addWidget(footer)

        layout.addWidget(ws, 1)

    # ---- 模板页：寄存器映射 + 位字段编辑 ----

    def _build_i2c_template_page(self):
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        root = QVBoxLayout(inner)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # Register Map
        map_card = QFrame()
        map_card.setObjectName("card")
        mv = QVBoxLayout(map_card)
        mv.setContentsMargins(14, 12, 14, 12)
        mv.setSpacing(8)
        mt = QLabel("Register Map")
        mt.setObjectName("cardTitle")
        mv.addWidget(mt)
        map_btn_row = QHBoxLayout()
        map_btn_row.setSpacing(6)
        self.i2c_save_tpl_btn = QPushButton("Save")
        self.i2c_load_tpl_btn = QPushButton("Load")
        self.i2c_add_reg_btn = QPushButton("+ Reg")
        self.i2c_readall_btn = QPushButton("Read All")
        for btn in (self.i2c_save_tpl_btn, self.i2c_load_tpl_btn,
                    self.i2c_add_reg_btn, self.i2c_readall_btn):
            btn.setFixedHeight(I2C_BTN_HEIGHT)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_i2c_subtle_btn_style())
            map_btn_row.addWidget(btn)
        map_btn_row.addStretch()
        mv.addLayout(map_btn_row)
        self.i2c_reg_table = QTableWidget(0, 5)
        self.i2c_reg_table.setHorizontalHeaderLabels(
            ["Name", "Reg Addr", "Width", "Fields", "Description"])
        self.i2c_reg_table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.i2c_reg_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.i2c_reg_table.verticalHeader().setVisible(False)
        self.i2c_reg_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.i2c_reg_table.setStyleSheet(_i2c_table_qss())
        rh = self.i2c_reg_table.horizontalHeader()
        rh.setSectionResizeMode(0, QHeaderView.Stretch)
        rh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        rh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        rh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        rh.setSectionResizeMode(4, QHeaderView.Stretch)
        self.i2c_reg_table.setMinimumHeight(160)
        mv.addWidget(self.i2c_reg_table)
        root.addWidget(map_card)

        # Bit Fields
        f_card = QFrame()
        f_card.setObjectName("card")
        fv = QVBoxLayout(f_card)
        fv.setContentsMargins(14, 12, 14, 12)
        fv.setSpacing(8)
        ft_row = QHBoxLayout()
        ft_row.setSpacing(6)
        ft = QLabel("Bit Fields")
        ft.setObjectName("cardTitle")
        ft_row.addWidget(ft)
        ft_row.addStretch()
        self.i2c_add_field_btn = QPushButton("+ Field")
        self.i2c_add_field_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_add_field_btn.setCursor(Qt.PointingHandCursor)
        self.i2c_add_field_btn.setStyleSheet(_i2c_subtle_btn_style())
        ft_row.addWidget(self.i2c_add_field_btn)
        fv.addLayout(ft_row)
        self.i2c_fields_table = QTableWidget(0, 5)
        self.i2c_fields_table.setHorizontalHeaderLabels(
            ["Field", "High", "Low", "Value", "Description"])
        self.i2c_fields_table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.i2c_fields_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.i2c_fields_table.verticalHeader().setVisible(False)
        self.i2c_fields_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.i2c_fields_table.setStyleSheet(_i2c_table_qss())
        fh = self.i2c_fields_table.horizontalHeader()
        fh.setSectionResizeMode(0, QHeaderView.Stretch)
        fh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        fh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        fh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        fh.setSectionResizeMode(4, QHeaderView.Stretch)
        self.i2c_fields_table.setMinimumHeight(140)
        fv.addWidget(self.i2c_fields_table)
        root.addWidget(f_card)
        root.addStretch()

        scroll.setWidget(inner)
        wrap = QVBoxLayout(page)
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.addWidget(scroll)
        return page

    # ---- 设置页：DLL + 速率 + 芯片检测 ----

    def _build_i2c_settings_page(self):
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        root = QVBoxLayout(inner)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        card = QFrame()
        card.setObjectName("card")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(14, 12, 14, 12)
        cv.setSpacing(8)

        dt = QLabel("DLL Path")
        dt.setObjectName("cardTitle")
        cv.addWidget(dt)
        dll_row = QHBoxLayout()
        dll_row.setSpacing(6)
        self.i2c_dll_edit = QLineEdit()
        self.i2c_dll_edit.setReadOnly(True)
        self.i2c_dll_edit.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_dll_edit.setStyleSheet(_i2c_input_style())
        self.i2c_dll_edit.setPlaceholderText("Auto resolve DLL path")
        self._i2c_refresh_dll_display()
        dll_row.addWidget(self.i2c_dll_edit, 1)
        self.i2c_dll_browse_btn = QPushButton("Browse")
        self.i2c_dll_browse_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_dll_browse_btn.setStyleSheet(_i2c_subtle_btn_style())
        dll_row.addWidget(self.i2c_dll_browse_btn)
        self.i2c_dll_reset_btn = QPushButton("Reset")
        self.i2c_dll_reset_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_dll_reset_btn.setStyleSheet(_i2c_subtle_btn_style())
        dll_row.addWidget(self.i2c_dll_reset_btn)
        cv.addLayout(dll_row)

        st = QLabel("Default Speed")
        st.setObjectName("cardTitle")
        cv.addWidget(st)
        self.i2c_speed_combo = DarkComboBox(bg=SLATE_950, border=SLATE_800,
                                            hover_color=INDIGO)
        self.i2c_speed_combo.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_speed_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for mode, text in self._i2c_speed_options:
            self.i2c_speed_combo.addItem(text, userData=mode)
        self.i2c_speed_combo.setCurrentIndex(1)
        cv.addWidget(self.i2c_speed_combo)

        ct = QLabel("Chip Check")
        ct.setObjectName("cardTitle")
        cv.addWidget(ct)
        self.i2c_chipcheck_btn = QPushButton("BES Chip Check")
        self.i2c_chipcheck_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_chipcheck_btn.setCursor(Qt.PointingHandCursor)
        self.i2c_chipcheck_btn.setStyleSheet(_i2c_read_btn_style())
        cv.addWidget(self.i2c_chipcheck_btn)

        root.addWidget(card)
        root.addStretch()
        scroll.setWidget(inner)
        wrap = QVBoxLayout(page)
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.addWidget(scroll)
        return page

    # ---- 信号绑定 ----

    def bind_i2c_signals(self):
        self.i2c_dll_browse_btn.clicked.connect(self._on_i2c_browse_dll)
        self.i2c_dll_reset_btn.clicked.connect(self._on_i2c_reset_dll)
        self.i2c_chipcheck_btn.clicked.connect(self._on_i2c_chip_check)
        self.i2c_read_btn.clicked.connect(self._on_i2c_read)
        self.i2c_write_btn.clicked.connect(self._on_i2c_write)
        self.i2c_data_edit.value_changed.connect(self._on_i2c_data_edited)
        self.i2c_bits.bit_toggled.connect(self._on_i2c_bit_toggled)
        self.i2c_width_combo.currentIndexChanged.connect(
            self._on_i2c_width_changed)
        self.i2c_speed_combo.currentIndexChanged.connect(
            self._on_i2c_default_speed_changed)
        self.i2c_add_field_btn.clicked.connect(self._on_i2c_add_field)
        self.i2c_fields_table.cellChanged.connect(self._on_i2c_field_cell_changed)
        self.i2c_fields_table.customContextMenuRequested.connect(
            self._on_i2c_field_context_menu)
        self.i2c_save_tpl_btn.clicked.connect(self._on_i2c_save_template)
        self.i2c_load_tpl_btn.clicked.connect(self._on_i2c_load_template)
        self.i2c_add_reg_btn.clicked.connect(self._on_i2c_add_register)
        self.i2c_readall_btn.clicked.connect(self._on_i2c_read_all)
        self.i2c_reg_table.cellDoubleClicked.connect(self._on_i2c_reg_double_clicked)
        self.i2c_reg_table.customContextMenuRequested.connect(
            self._on_i2c_reg_context_menu)

    # ---- 状态反馈 ----

    def _i2c_set_result(self, text, ok=True):
        self.i2c_result_label.setText(text)
        self.i2c_result_label.setStyleSheet(
            "color:#34d399;" if ok else "color:#ff5e7a;")

    def append_log(self, msg):
        """供页面覆写：默认转发到 logger。"""
        logger.info(msg)

    def _i2c_set_busy(self, busy):
        for attr in ("i2c_read_btn", "i2c_write_btn", "i2c_chipcheck_btn",
                     "i2c_readall_btn"):
            w = getattr(self, attr, None)
            if w is not None:
                w.setEnabled(not busy)

    def _i2c_set_activity(self, op, value=None, ok=True):
        self.i2c_activity_op.setText(op)
        self.i2c_activity_op.setStyleSheet(
            "color:#34d399;" if ok else "color:#ff5e7a;")
        self.i2c_activity_time.setText(
            QDateTime.currentDateTime().toString("HH:mm:ss"))
        if value is not None:
            bits = self._i2c_data_bits
            self._i2c_set_result(
                f"{_fmt_hex(value, bits)}   ({value})", ok=ok)

    # ---- DLL 路径 ----

    def _i2c_refresh_dll_display(self):
        display = getattr(self, "_i2c_custom_dll", None)
        if not display:
            try:
                from lib.i2c.i2c_interface_x64 import _resolve_default_dll_path
                display = _resolve_default_dll_path() or "(auto, not found)"
            except Exception:
                display = "(auto)"
        self.i2c_dll_edit.setText(display)

    def _on_i2c_browse_dll(self):
        start = getattr(self, "_i2c_custom_dll", None) or ""
        start_dir = os.path.dirname(start) if start else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 I2C DLL", start_dir, "DLL (*.dll);;All (*.*)")
        if path:
            self._i2c_custom_dll = path
            self.i2c_dll_edit.setText(path)
            self.append_log(f"[I2C] DLL 路径已设为: {path}")

    def _on_i2c_reset_dll(self):
        self._i2c_custom_dll = None
        self._i2c_refresh_dll_display()
        self.append_log("[I2C] DLL 路径已重置为自动查找")

    # ---- 速率 / 位宽 ----

    def _on_i2c_default_speed_changed(self, _idx):
        mode = self.i2c_speed_combo.currentData()
        if mode is None:
            return
        self._i2c_speed_mode = mode
        self.append_log(f"[I2C] 默认速率切换为 {self.i2c_speed_combo.currentText()}")

    def _on_i2c_width_changed(self, _idx):
        bits = self.i2c_width_combo.currentData()
        if bits is None:
            return
        self._i2c_data_bits = int(bits)
        self._i2c_width = _ui_width_to_flag(int(bits))
        self._i2c_sync_width_ui()
        self.append_log(f"[I2C] 数据位宽切换为 {bits}-bit")

    def _i2c_sync_width_ui(self):
        reg_bits = _reg_addr_bits(self._i2c_width)
        self.i2c_dev_edit.set_bit_count(reg_bits)
        self.i2c_reg_edit.set_bit_count(reg_bits)
        self.i2c_data_edit.set_bit_count(self._i2c_data_bits)
        self.i2c_bits.set_bit_count(self._i2c_data_bits)
        self._i2c_data_value &= (1 << self._i2c_data_bits) - 1
        self.i2c_data_edit.set_value(self._i2c_data_value)
        self.i2c_bits.set_value(self._i2c_data_value)
        self.i2c_bits.set_fields(self._i2c_fields)
        self._i2c_refresh_bin_label()
        self._i2c_refresh_field_values()

    # ---- 双向数据绑定 ----

    def _on_i2c_data_edited(self, value):
        self._i2c_data_value = int(value) & ((1 << self._i2c_data_bits) - 1)
        self.i2c_bits.set_value(self._i2c_data_value)
        self._i2c_refresh_bin_label()
        self._i2c_refresh_field_values()

    def _on_i2c_bit_toggled(self, bit_idx):
        mask = (1 << self._i2c_data_bits) - 1
        self._i2c_data_value = (self._i2c_data_value ^ (1 << bit_idx)) & mask
        self.i2c_data_edit.set_value(self._i2c_data_value)
        self.i2c_bits.set_value(self._i2c_data_value)
        self._i2c_refresh_bin_label()
        self._i2c_refresh_field_values()

    def _i2c_refresh_bin_label(self):
        v = self._i2c_data_value
        self.i2c_bin_label.setText(
            f"{_fmt_bin_grouped(v, self._i2c_data_bits)}    ({v})")

    # ---- 读写操作（按需初始化 I2C） ----

    def _i2c_current_dev(self):
        return self.i2c_dev_edit.value()

    def _i2c_current_reg(self):
        return self.i2c_reg_edit.value()

    def _start_i2c_read(self, dev, reg, use_raw, tag=""):
        if (self._i2c_read_thread is not None
                and self._i2c_read_thread.isRunning()):
            return
        self._i2c_set_busy(True)
        self._i2c_set_activity("Reading…", ok=True)
        self.append_log(
            f"[I2C] Read{tag} dev=0x{dev:02X} reg=0x{reg:X} "
            f"width={_width_label(self._i2c_width)} raw={use_raw}")
        worker = _I2cReadWorker(
            self._i2c_dll_path(), self._i2c_speed_mode, dev, reg,
            self._i2c_width, use_raw)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_i2c_read_done)
        worker.error.connect(self._on_i2c_read_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_i2c_read_thread_cleanup)
        self._i2c_read_worker = worker
        self._i2c_read_thread = thread
        thread.start()

    def _on_i2c_read(self):
        if (self._i2c_read_thread is not None
                and self._i2c_read_thread.isRunning()):
            return
        self._start_i2c_read(self._i2c_current_dev(),
                             self._i2c_current_reg(), False)

    def _on_i2c_read_thread_cleanup(self):
        self._i2c_read_thread = None
        self._i2c_read_worker = None

    def _on_i2c_read_done(self, value):
        bits = self._i2c_data_bits
        value = int(value) & ((1 << bits) - 1)
        self._i2c_data_value = value
        self.i2c_data_edit.set_value(value)
        self.i2c_bits.set_value(value)
        self._i2c_refresh_bin_label()
        self._i2c_refresh_field_values()
        self._i2c_set_activity("Read", value=value, ok=True)
        self._i2c_set_busy(False)
        self.append_log(f"[I2C] Read => {_fmt_hex(value, bits)} ({value})")
        idx = getattr(self, "_i2c_pending_readall_idx", None)
        if idx is not None:
            self._i2c_readall_results[idx] = value
            self._i2c_pending_readall_idx = None
            if getattr(self, "_i2c_readall_queue", None):
                QTimer.singleShot(10, self._i2c_readall_next)

    def _on_i2c_read_error(self, err):
        self._i2c_set_activity("Read", ok=False)
        self._i2c_set_result(f"Read Failed: {err}", ok=False)
        self._i2c_set_busy(False)
        self.append_log(f"[I2C] Read 失败: {err}")
        if getattr(self, "_i2c_readall_queue", None):
            self._i2c_pending_readall_idx = None
            QTimer.singleShot(10, self._i2c_readall_next)

    def _start_i2c_write(self, dev, reg, data, high, low, use_raw, tag=""):
        if (self._i2c_write_thread is not None
                and self._i2c_write_thread.isRunning()):
            return
        self._i2c_set_busy(True)
        bit_desc = "full" if high < 0 else f"[{high}:{low}]"
        self._i2c_set_activity("Writing…", ok=True)
        self.append_log(
            f"[I2C] Write{tag} dev=0x{dev:02X} reg=0x{reg:X} "
            f"data={_fmt_hex(data, self._i2c_data_bits)} "
            f"width={_width_label(self._i2c_width)} bits={bit_desc} raw={use_raw}")
        worker = _I2cWriteWorker(
            self._i2c_dll_path(), self._i2c_speed_mode, dev, reg, data,
            self._i2c_width, high, low, use_raw)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_i2c_write_done)
        worker.error.connect(self._on_i2c_write_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_i2c_write_thread_cleanup)
        self._i2c_write_worker = worker
        self._i2c_write_thread = thread
        thread.start()

    def _on_i2c_write_thread_cleanup(self):
        self._i2c_write_thread = None
        self._i2c_write_worker = None

    def _on_i2c_write(self):
        if (self._i2c_write_thread is not None
                and self._i2c_write_thread.isRunning()):
            return
        dev = self._i2c_current_dev()
        reg = self._i2c_current_reg()
        data = self._i2c_data_value
        self._start_i2c_write(dev, reg, data, -1, -1, False)

    def _on_i2c_write_done(self):
        self._i2c_set_activity("Write", value=self._i2c_data_value, ok=True)
        self._i2c_set_busy(False)
        self.append_log("[I2C] Write 完成")

    def _on_i2c_write_error(self, err):
        self._i2c_set_activity("Write", ok=False)
        self._i2c_set_result(f"Write Failed: {err}", ok=False)
        self._i2c_set_busy(False)
        self.append_log(f"[I2C] Write 失败: {err}")

    # ---- 位字段表 ----

    def _on_i2c_add_field(self):
        bits = self._i2c_data_bits
        self._i2c_fields.append({
            "name": f"FIELD{len(self._i2c_fields)}",
            "high_bit": min(7, bits - 1),
            "low_bit": 0,
            "description": "",
        })
        self._i2c_rebuild_fields_table()
        self._i2c_sync_active_register_fields()
        self.i2c_bits.set_fields(self._i2c_fields)
        self._i2c_refresh_field_values()

    def _i2c_rebuild_fields_table(self):
        self._i2c_suppress_field_refresh = True
        self.i2c_fields_table.setRowCount(0)
        for f in self._i2c_fields:
            row = self.i2c_fields_table.rowCount()
            self.i2c_fields_table.insertRow(row)
            self.i2c_fields_table.setItem(row, 0, QTableWidgetItem(f["name"]))
            self.i2c_fields_table.setItem(row, 1, QTableWidgetItem(str(f["high_bit"])))
            self.i2c_fields_table.setItem(row, 2, QTableWidgetItem(str(f["low_bit"])))
            val_item = QTableWidgetItem("")
            val_item.setFlags(val_item.flags() & ~Qt.ItemIsEditable)
            val_item.setForeground(QColor(EMERALD_LIGHT))
            self.i2c_fields_table.setItem(row, 3, val_item)
            self.i2c_fields_table.setItem(row, 4, QTableWidgetItem(f["description"]))
        self._i2c_suppress_field_refresh = False
        self._i2c_refresh_field_values()

    def _on_i2c_field_cell_changed(self, row, col):
        if self._i2c_suppress_field_refresh:
            return
        if row >= len(self._i2c_fields):
            return
        item = self.i2c_fields_table.item(row, col)
        if item is None:
            return
        if col == 0:
            self._i2c_fields[row]["name"] = item.text()
        elif col == 1:
            v = _parse_hex_int(item.text())
            self._i2c_fields[row]["high_bit"] = max(0, v or 0)
        elif col == 2:
            v = _parse_hex_int(item.text())
            self._i2c_fields[row]["low_bit"] = max(0, v or 0)
        elif col == 4:
            self._i2c_fields[row]["description"] = item.text()
        self._i2c_sync_active_register_fields()
        self.i2c_bits.set_fields(self._i2c_fields)
        self._i2c_refresh_field_values()

    def _i2c_refresh_field_values(self):
        if not hasattr(self, "i2c_fields_table"):
            return
        value = self._i2c_data_value
        self._i2c_suppress_field_refresh = True
        for row, f in enumerate(self._i2c_fields):
            if row >= self.i2c_fields_table.rowCount():
                break
            high = int(f["high_bit"])
            low = int(f["low_bit"])
            if high < low:
                high, low = low, high
            width = max(high - low + 1, 1)
            field_mask = (1 << width) - 1
            field_val = (value >> low) & field_mask
            item = self.i2c_fields_table.item(row, 3)
            if item is not None:
                item.setText(f"{_fmt_hex(field_val, width)}  ({field_val})")
        self._i2c_suppress_field_refresh = False
        self.i2c_bits.set_value(value)

    def _on_i2c_field_context_menu(self, pos):
        row = self.i2c_fields_table.rowAt(pos.y())
        menu = QMenu(self.i2c_fields_table)
        menu.setStyleSheet(
            f"QMenu {{ background-color:{SLATE_950}; color:{TEXT_MAIN};"
            f" border:1px solid {SLATE_800}; }}"
            "QMenu::item:selected { background-color: rgba(99,102,241,0.35); }")
        act_del = QAction("Delete Field", self.i2c_fields_table)
        act_del.triggered.connect(lambda: self._i2c_delete_field(row))
        menu.addAction(act_del)
        if row < 0:
            act_del.setEnabled(False)
        menu.exec(self.i2c_fields_table.viewport().mapToGlobal(pos))

    def _i2c_delete_field(self, row):
        if row < 0 or row >= len(self._i2c_fields):
            return
        self._i2c_fields.pop(row)
        self._i2c_rebuild_fields_table()
        self._i2c_sync_active_register_fields()
        self.i2c_bits.set_fields(self._i2c_fields)
        self._i2c_refresh_field_values()

    def _i2c_sync_active_register_fields(self):
        if (self._i2c_active_reg_index is not None
                and 0 <= self._i2c_active_reg_index < len(self._i2c_registers)):
            self._i2c_registers[self._i2c_active_reg_index]["bit_fields"] = \
                copy.deepcopy(self._i2c_fields)

    # ---- 寄存器映射 / 模板 ----

    def _on_i2c_add_register(self):
        reg = {
            "name": f"REG{len(self._i2c_registers)}",
            "reg_addr": _fmt_hex(self._i2c_current_reg(),
                                 _reg_addr_bits(self._i2c_width)),
            "data_bits": self._i2c_data_bits,
            "description": "",
            "bit_fields": copy.deepcopy(self._i2c_fields),
        }
        self._i2c_registers.append(reg)
        self._i2c_active_reg_index = len(self._i2c_registers) - 1
        self._i2c_rebuild_reg_table()
        self.append_log(f"[I2C] 添加寄存器 {reg['name']} @ {reg['reg_addr']}")

    def _i2c_rebuild_reg_table(self):
        self.i2c_reg_table.setRowCount(0)
        for reg in self._i2c_registers:
            row = self.i2c_reg_table.rowCount()
            self.i2c_reg_table.insertRow(row)
            self.i2c_reg_table.setItem(row, 0, QTableWidgetItem(reg["name"]))
            self.i2c_reg_table.setItem(row, 1, QTableWidgetItem(reg["reg_addr"]))
            self.i2c_reg_table.setItem(row, 2, QTableWidgetItem(str(reg.get("data_bits", 16))))
            nf = len(reg.get("bit_fields", []))
            self.i2c_reg_table.setItem(row, 3, QTableWidgetItem(str(nf)))
            self.i2c_reg_table.setItem(row, 4, QTableWidgetItem(reg["description"]))

    def _on_i2c_reg_double_clicked(self, row, _col):
        self._i2c_load_register(row)

    def _i2c_load_register(self, row):
        if row < 0 or row >= len(self._i2c_registers):
            return
        reg = self._i2c_registers[row]
        self._i2c_active_reg_index = row
        bits = int(reg.get("data_bits", 16))
        if bits not in (8, 16, 32):
            bits = 16
        self._i2c_set_data_bits(bits)
        self.i2c_reg_edit.set_value(_parse_hex_int(reg["reg_addr"]) or 0)
        self._i2c_fields = copy.deepcopy(reg.get("bit_fields", []))
        self._i2c_rebuild_fields_table()
        self.i2c_bits.set_fields(self._i2c_fields)
        self.append_log(
            f"[I2C] 加载寄存器 {reg['name']} (addr={reg['reg_addr']}, "
            f"fields={len(self._i2c_fields)})")

    def _i2c_set_data_bits(self, bits):
        for i in range(self.i2c_width_combo.count()):
            if self.i2c_width_combo.itemData(i) == bits:
                self.i2c_width_combo.blockSignals(True)
                self.i2c_width_combo.setCurrentIndex(i)
                self.i2c_width_combo.blockSignals(False)
                break
        self._i2c_data_bits = bits
        self._i2c_width = _ui_width_to_flag(bits)
        self._i2c_sync_width_ui()

    def _on_i2c_reg_context_menu(self, pos):
        row = self.i2c_reg_table.rowAt(pos.y())
        menu = QMenu(self.i2c_reg_table)
        menu.setStyleSheet(
            f"QMenu {{ background-color:{SLATE_950}; color:{TEXT_MAIN};"
            f" border:1px solid {SLATE_800}; }}"
            "QMenu::item:selected { background-color: rgba(99,102,241,0.35); }")
        act_load = QAction("Load (edit fields)", self.i2c_reg_table)
        act_read = QAction("Read", self.i2c_reg_table)
        act_write = QAction("Write current value", self.i2c_reg_table)
        act_del = QAction("Delete", self.i2c_reg_table)
        act_load.triggered.connect(lambda: self._i2c_load_register(row))
        act_read.triggered.connect(lambda: self._i2c_read_register(row))
        act_write.triggered.connect(lambda: self._i2c_write_register(row))
        act_del.triggered.connect(lambda: self._i2c_delete_register(row))
        menu.addAction(act_load)
        menu.addAction(act_read)
        menu.addAction(act_write)
        menu.addSeparator()
        menu.addAction(act_del)
        if row < 0:
            for a in (act_load, act_read, act_write, act_del):
                a.setEnabled(False)
        menu.exec(self.i2c_reg_table.viewport().mapToGlobal(pos))

    def _i2c_read_register(self, row):
        if row < 0 or row >= len(self._i2c_registers):
            return
        reg = self._i2c_registers[row]
        bits = int(reg.get("data_bits", 16))
        if bits not in (8, 16, 32):
            bits = 16
        self._i2c_set_data_bits(bits)
        dev = self._i2c_current_dev()
        reg_addr = _parse_hex_int(reg["reg_addr"]) or 0
        self.i2c_reg_edit.set_value(reg_addr)
        self._start_i2c_read(dev, reg_addr, False, tag=f" ({reg['name']})")

    def _i2c_write_register(self, row):
        if (self._i2c_write_thread is not None
                and self._i2c_write_thread.isRunning()):
            return
        if row < 0 or row >= len(self._i2c_registers):
            return
        reg = self._i2c_registers[row]
        bits = int(reg.get("data_bits", 16))
        if bits not in (8, 16, 32):
            bits = 16
        self._i2c_set_data_bits(bits)
        dev = self._i2c_current_dev()
        reg_addr = _parse_hex_int(reg["reg_addr"]) or 0
        self.i2c_reg_edit.set_value(reg_addr)
        data = self._i2c_data_value
        self._start_i2c_write(dev, reg_addr, data, -1, -1, False,
                              tag=f" ({reg['name']})")

    def _i2c_delete_register(self, row):
        if row < 0 or row >= len(self._i2c_registers):
            return
        name = self._i2c_registers[row]["name"]
        self._i2c_registers.pop(row)
        if self._i2c_active_reg_index == row:
            self._i2c_active_reg_index = None
        elif (self._i2c_active_reg_index is not None
              and self._i2c_active_reg_index > row):
            self._i2c_active_reg_index -= 1
        self._i2c_rebuild_reg_table()
        self.append_log(f"[I2C] 删除寄存器 {name}")

    def _on_i2c_read_all(self):
        if not self._i2c_registers:
            self.append_log("[I2C] 寄存器映射为空，无法 Read All")
            return
        self._i2c_readall_queue = list(enumerate(self._i2c_registers))
        self._i2c_readall_results = {}
        self.append_log(f"[I2C] Read All: {len(self._i2c_readall_queue)} 个寄存器")
        self._i2c_readall_next()

    def _i2c_readall_next(self):
        if not getattr(self, "_i2c_readall_queue", None):
            summary = "\n".join(
                f"  {reg['name']} @ {reg['reg_addr']} = "
                f"{_fmt_hex(self._i2c_readall_results.get(i, 0), self._i2c_data_bits)}"
                for i, reg in enumerate(self._i2c_registers)
            ) if self._i2c_registers else "(空)"
            self.append_log(f"[I2C] Read All 完成:\n{summary}")
            self._i2c_set_busy(False)
            return
        idx, reg = self._i2c_readall_queue.pop(0)
        bits = int(reg.get("data_bits", 16))
        if bits not in (8, 16, 32):
            bits = 16
        self._i2c_set_data_bits(bits)
        dev = self._i2c_current_dev()
        reg_addr = _parse_hex_int(reg["reg_addr"]) or 0
        self.i2c_reg_edit.set_value(reg_addr)
        self._i2c_pending_readall_idx = idx
        self._start_i2c_read(dev, reg_addr, False, tag=f" ({reg['name']})")

    # ---- 芯片检测 ----

    def _on_i2c_chip_check(self):
        if (self._i2c_chipcheck_thread is not None
                and self._i2c_chipcheck_thread.isRunning()):
            return
        self._i2c_set_busy(True)
        self._i2c_set_activity("Chip check…", ok=True)
        self.append_log("[I2C] BES 芯片检测中...")
        worker = _I2cChipCheckWorker(self._i2c_dll_path(), self._i2c_speed_mode)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_i2c_chipcheck_done)
        worker.error.connect(self._on_i2c_chipcheck_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_i2c_chipcheck_thread_cleanup)
        self._i2c_chipcheck_worker = worker
        self._i2c_chipcheck_thread = thread
        thread.start()

    def _on_i2c_chipcheck_thread_cleanup(self):
        self._i2c_chipcheck_thread = None
        self._i2c_chipcheck_worker = None

    def _on_i2c_chipcheck_done(self, result):
        self._i2c_set_activity("Chip check", ok=True)
        self._i2c_set_result("Chip check OK", ok=True)
        self._i2c_set_busy(False)
        lines = ["[I2C] 芯片检测结果:"]
        for k, v in result.items():
            lines.append(f"  {k}: {v}")
        self.append_log("\n".join(lines))
        QMessageBox.information(
            self, "BES 芯片检测",
            "\n".join(f"{k}: {v}" for k, v in result.items()))

    def _on_i2c_chipcheck_error(self, err):
        self._i2c_set_activity("Chip check", ok=False)
        self._i2c_set_result(f"Chip check failed: {err}", ok=False)
        self._i2c_set_busy(False)
        self.append_log(f"[I2C] 芯片检测失败: {err}")

    # ---- 模板保存 / 加载 ----

    def _i2c_serialize_template(self):
        return {
            "name": "I2C Template",
            "device_addr": _fmt_hex(self._i2c_current_dev(),
                                    _reg_addr_bits(self._i2c_width)),
            "speed_mode": int(self._i2c_speed_mode),
            "data_bits": self._i2c_data_bits,
            "registers": copy.deepcopy(self._i2c_registers),
        }

    def _on_i2c_save_template(self):
        data = self._i2c_serialize_template()
        default_path = os.path.join(_i2c_template_dir(), "i2c_template.json")
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 I2C 模板", default_path, "JSON (*.json);;All (*.*)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.append_log(f"[I2C] 模板已保存: {path}")
        except Exception as e:
            logger.error("I2C save template failed: %s", e, exc_info=True)
            QMessageBox.critical(self, "保存失败", str(e))

    def _on_i2c_load_template(self):
        start_dir = _i2c_template_dir()
        path, _ = QFileDialog.getOpenFileName(
            self, "加载 I2C 模板", start_dir, "JSON (*.json);;All (*.*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error("I2C load template failed: %s", e, exc_info=True)
            QMessageBox.critical(self, "加载失败", str(e))
            return

        from lib.i2c.Bes_I2CIO_Interface import I2CSpeedMode
        self._i2c_registers = copy.deepcopy(data.get("registers", []))
        self._i2c_active_reg_index = None
        self._i2c_rebuild_reg_table()

        try:
            speed = I2CSpeedMode(int(data.get("speed_mode", 1)))
            for i in range(self.i2c_speed_combo.count()):
                if self.i2c_speed_combo.itemData(i) == speed:
                    self.i2c_speed_combo.blockSignals(True)
                    self.i2c_speed_combo.setCurrentIndex(i)
                    self.i2c_speed_combo.blockSignals(False)
                    break
            self._i2c_speed_mode = speed
        except Exception:
            pass
        bits = int(data.get("data_bits", 16))
        if bits not in (8, 16, 32):
            bits = 16
        self._i2c_set_data_bits(bits)
        dev = data.get("device_addr")
        if dev is not None:
            self.i2c_dev_edit.set_value(_parse_hex_int(dev) or 0)
        self.append_log(
            f"[I2C] 模板已加载: {path} "
            f"({len(self._i2c_registers)} 个寄存器)")

    # ---- 资源释放 ----

    def close_i2c(self):
        """I2C 按需初始化/销毁，无需持久资源释放；保留接口供页面统一调用。"""
        pass


# ---------------------------------------------------------------------------
# 独立运行 Demo
# ---------------------------------------------------------------------------

class _DemoI2cWidget(I2cMixin, QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_i2c()
        self.setStyleSheet(_I2C_DARK_STYLE)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)
        self.build_i2c_widgets(root)
        self.bind_i2c_signals()

    def append_log(self, msg):
        logger.info(msg)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from ui.standalone import resize_and_center_window

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = _DemoI2cWidget()
    w.setWindowTitle("I2C 控制台")
    resize_and_center_window(w, size=(960, 760))
    w.show()
    sys.exit(app.exec())

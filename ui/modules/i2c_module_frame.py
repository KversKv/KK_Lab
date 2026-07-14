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

from ui.resource_path import get_resource_base, get_user_data_dir
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QSizePolicy, QToolTip, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFileDialog, QMessageBox, QMenu, QScrollArea, QTabWidget
)
from PySide6.QtCore import (
    Qt, QThread, Signal, QObject, QSize, QRect, QRectF, QTimer
)
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QAction

from ui.widgets.dark_combobox import DarkComboBox
from debug_config import DEBUG_MOCK
from log_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

I2C_BTN_HEIGHT = 22

I2C_OP_READ = "read"
I2C_OP_WRITE = "write"
I2C_OP_BIT_WRITE = "bit_write"
I2C_OP_READ_DATA = "read_data"
I2C_OP_WRITE_DATA = "write_data"

_I2C_OP_OPTIONS = [
    (I2C_OP_READ, "Read"),
    (I2C_OP_WRITE, "Write (Full)"),
    (I2C_OP_BIT_WRITE, "Write (Bit)"),
    (I2C_OP_READ_DATA, "ReadData (Raw)"),
    (I2C_OP_WRITE_DATA, "WriteData (Raw)"),
]

_I2C_WIDTH_META = {}


def _load_width_meta():
    from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag
    return {
        I2CWidthFlag.BIT_8: ("8-bit  (8b addr / 16b data)", 8, 16),
        I2CWidthFlag.BIT_10: ("10-bit (16b addr / 16b data)", 16, 16),
        I2CWidthFlag.BIT_32: ("32-bit (32b addr / 32b data)", 32, 32),
    }


def _load_speed_options():
    from lib.i2c.Bes_I2CIO_Interface import I2CSpeedMode
    return [
        (I2CSpeedMode.SPEED_20K, "20 kHz"),
        (I2CSpeedMode.SPEED_100K, "100 kHz"),
        (I2CSpeedMode.SPEED_400K, "400 kHz"),
        (I2CSpeedMode.SPEED_750K, "750 kHz"),
    ]


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


def _i2c_action_style(h=I2C_BTN_HEIGHT):
    return f"""
        QPushButton {{
            background-color: #13254b;
            border: 1px solid #22376A;
            border-radius: 6px;
            color: #dce7ff;
            font-weight: 600;
            min-height: {h}px;
            max-height: {h}px;
            padding: 2px 8px;
        }}
        QPushButton:hover {{
            background-color: #1C2D55;
            border: 1px solid #3A5A9F;
        }}
        QPushButton:pressed {{
            background-color: #102040;
        }}
        QPushButton:disabled {{
            background-color: #0b1430;
            color: #5c7096;
            border: 1px solid #1a2850;
        }}
    """


def _i2c_accent_style(h=I2C_BTN_HEIGHT):
    return f"""
        QPushButton {{
            background-color: #053b38;
            border: 1px solid #08c9a5;
            border-radius: 6px;
            color: #10e7bc;
            font-weight: 700;
            min-height: {h}px;
            max-height: {h}px;
            padding: 2px 10px;
        }}
        QPushButton:hover {{
            background-color: #064744;
            border: 1px solid #19f0c5;
            color: #43f3d0;
        }}
        QPushButton:pressed {{
            background-color: #042f2d;
        }}
        QPushButton:disabled {{
            background-color: #0D1734;
            color: #3a4a6a;
            border: 1px solid #18264A;
        }}
    """


def _i2c_input_style(h=I2C_BTN_HEIGHT):
    return f"""
        QLineEdit {{
            background-color: #091426;
            border: 1px solid #17345f;
            border-radius: 6px;
            color: #dce7ff;
            min-height: {h}px;
            max-height: {h}px;
            padding: 0px 6px;
            selection-background-color: #1f4a8a;
        }}
        QLineEdit:focus {{
            border: 1px solid #3A5A9F;
        }}
        QLineEdit:disabled {{
            background-color: #0b1430;
            color: #5c7096;
            border: 1px solid #1a2850;
        }}
    """


def _i2c_tab_style():
    return """
        QTabWidget::pane {
            border: 1px solid #1a2b52;
            border-radius: 8px;
            background-color: #071127;
            top: -1px;
        }
        QTabBar::tab {
            background-color: #0b1430;
            color: #7e96bf;
            border: 1px solid #1a2b52;
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 6px 16px;
            margin-right: 2px;
            font-weight: 600;
        }
        QTabBar::tab:selected {
            background-color: #13254b;
            color: #dce7ff;
            border-color: #3A5A9F;
        }
        QTabBar::tab:hover:!selected {
            background-color: #112040;
            color: #b8c8e8;
        }
    """


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
# 自定义控件：十六进制输入框
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
# 自定义控件：位网格视图（自适应宽度，水平居中）
# ---------------------------------------------------------------------------

class BitGridView(QWidget):
    """将寄存器值以 bit 网格可视化，MSB 在左；单元格宽度随窗口宽度自适应，
    整体水平居中，点击切换 bit 值。"""
    value_changed = Signal(int)

    def __init__(self, bit_count=16, parent=None):
        super().__init__(parent)
        self._bit_count = bit_count
        self._value = 0
        self._cell_h = 42
        self._row_gap = 6
        self._min_cell_w = 20.0
        self._max_cell_w = 44.0
        self._one_bg = QColor("#0c4a42")
        self._one_fg = QColor("#19f0c5")
        self._zero_bg = QColor("#091426")
        self._zero_fg = QColor("#5F77AE")
        self._border = QColor("#22376A")
        self._idx_fg = QColor("#7e96bf")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(self._compute_height())

    def _compute_height(self):
        rows = (self._bit_count + 15) // 16
        return rows * self._cell_h + (rows - 1) * self._row_gap

    def _cell_w(self):
        """按当前控件宽度计算单元格宽度（每行 16 列），并居中钳位。"""
        cols = min(16, self._bit_count)
        if cols <= 0:
            return self._min_cell_w
        w = float(self.width()) / cols
        if w < self._min_cell_w:
            return self._min_cell_w
        if w > self._max_cell_w:
            return self._max_cell_w
        return w

    def _grid_origin_x(self):
        cols = min(16, self._bit_count)
        grid_w = cols * self._cell_w()
        return (self.width() - grid_w) / 2.0

    def set_bit_count(self, bit_count):
        self._bit_count = bit_count
        self._value &= (1 << bit_count) - 1
        self.setMinimumHeight(self._compute_height())
        self.update()

    def value(self):
        return self._value

    def set_value(self, v, emit=False):
        self._value = int(v) & ((1 << self._bit_count) - 1)
        self.update()
        if emit:
            self.value_changed.emit(self._value)

    def _bit_rect(self, i):
        cw = self._cell_w()
        row = (self._bit_count - 1 - i) // 16
        col = (self._bit_count - 1 - i) % 16
        x = self._grid_origin_x() + col * cw
        y = row * (self._cell_h + self._row_gap)
        return QRectF(x, y, cw, self._cell_h)

    def _bit_at(self, x, y):
        rows = (self._bit_count + 15) // 16
        row = y // (self._cell_h + self._row_gap)
        if row < 0 or row >= rows:
            return None
        origin_x = self._grid_origin_x()
        rel_x = x - origin_x
        cw = self._cell_w()
        if rel_x < 0 or rel_x >= 16 * cw:
            return None
        col = int(rel_x // cw)
        if col < 0 or col >= 16:
            return None
        idx = (self._bit_count - 1) - (row * 16 + col)
        if idx < 0 or idx >= self._bit_count:
            return None
        return idx

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def mousePressEvent(self, event):
        if not self.isEnabled():
            super().mousePressEvent(event)
            return
        if event.button() == Qt.LeftButton:
            idx = self._bit_at(int(event.position().x()), int(event.position().y()))
            if idx is not None:
                self._value ^= (1 << idx)
                self.update()
                self.value_changed.emit(self._value)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.45)

        font_idx = QFont()
        font_idx.setPixelSize(9)
        font_val = QFont()
        font_val.setPixelSize(13)
        font_val.setBold(True)

        for i in range(self._bit_count):
            rect = self._bit_rect(i)
            bit_on = bool((self._value >> i) & 1)

            p.setPen(QPen(self._border, 1))
            p.setBrush(self._one_bg if bit_on else self._zero_bg)
            p.drawRoundedRect(rect, 4, 4)

            p.setPen(self._idx_fg)
            p.setFont(font_idx)
            p.drawText(
                QRectF(rect.x(), rect.y() + 2, rect.width(), 12),
                Qt.AlignCenter, str(i),
            )
            p.setPen(self._one_fg if bit_on else self._zero_fg)
            p.setFont(font_val)
            p.drawText(
                QRectF(rect.x(), rect.y() + 14, rect.width(), rect.height() - 14),
                Qt.AlignCenter, "1" if bit_on else "0",
            )

            col = (self._bit_count - 1 - i) % 16
            if col % 4 == 3 and col != 15:
                sep_x = rect.right() + 1
                p.setPen(QPen(QColor("#2a3f6e"), 1))
                p.drawLine(sep_x, rect.y(), sep_x, rect.bottom())

        p.end()

    def sizeHint(self):
        rows = (self._bit_count + 15) // 16
        return QSize(16 * int(self._cell_w()),
                     rows * self._cell_h + (rows - 1) * self._row_gap)

    def event(self, ev):
        if ev.type() == ev.Type.ToolTip:
            idx = self._bit_at(int(ev.pos().x()), int(ev.pos().y()))
            if idx is not None:
                bit_on = bool((self._value >> idx) & 1)
                QToolTip.showText(
                    ev.globalPos(), f"bit[{idx}] = {1 if bit_on else 0}", self)
                return True
        return super().event(ev)


# ---------------------------------------------------------------------------
# 主 Mixin
# ---------------------------------------------------------------------------

class I2cMixin:
    """通用 I2C 控制 Mixin：按需初始化 I2C / 寄存器读写 / 位宽切换 /
    按位写 / 位域解释 / 寄存器映射 / 模板持久化 / 标签页布局。"""

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

        from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag
        self._i2c_width = I2CWidthFlag.BIT_10
        self._i2c_speed_mode = self._i2c_speed_options[1][0]  # 100K

        self._i2c_registers = []
        self._i2c_active_reg_index = None
        self._i2c_fields = []
        self._i2c_suppress_field_refresh = False
        self._i2c_readall_queue = []
        self._i2c_readall_results = {}
        self._i2c_pending_readall_idx = None

    # ---- 当前 DLL 路径（每次操作传入 worker） ----

    def _i2c_dll_path(self):
        return getattr(self, "_i2c_custom_dll", None)

    # ---- UI 构建：标签页 ----

    def build_i2c_widgets(self, layout, title_row=None):
        self.i2c_tab_widget = QTabWidget()
        self.i2c_tab_widget.setStyleSheet(_i2c_tab_style())
        self.i2c_tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        ctrl_tab = self._build_i2c_control_tab()
        self.i2c_tab_widget.addTab(ctrl_tab, "控制")

        tpl_tab = self._build_i2c_template_tab()
        self.i2c_tab_widget.addTab(tpl_tab, "模板")

        settings_tab = self._build_i2c_settings_tab()
        self.i2c_tab_widget.addTab(settings_tab, "设置")

        layout.addWidget(self.i2c_tab_widget)
        self._i2c_sync_width_ui()

    def _build_i2c_control_tab(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        root = QVBoxLayout(inner)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        self._build_i2c_access_card(root)
        self._build_i2c_bitview_card(root)
        root.addStretch()

        scroll.setWidget(inner)
        wrap = QVBoxLayout(page)
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.addWidget(scroll)
        return page

    def _build_i2c_template_tab(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        root = QVBoxLayout(page)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        self._build_i2c_register_map_card(root)
        root.addStretch()
        return page

    def _build_i2c_settings_tab(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        root = QVBoxLayout(page)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # DLL 路径
        dll_title = QLabel("DLL")
        dll_title.setObjectName("cardTitle")
        root.addWidget(dll_title)
        dll_row = QHBoxLayout()
        dll_row.setSpacing(6)
        self.i2c_dll_edit = QLineEdit()
        self.i2c_dll_edit.setReadOnly(True)
        self.i2c_dll_edit.setPlaceholderText("Auto resolve DLL path")
        self.i2c_dll_edit.setStyleSheet(_i2c_input_style())
        self._i2c_refresh_dll_display()
        dll_row.addWidget(self.i2c_dll_edit, 1)
        self.i2c_dll_browse_btn = QPushButton("Browse")
        self.i2c_dll_browse_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_dll_browse_btn.setStyleSheet(_i2c_action_style())
        self.i2c_dll_browse_btn.setToolTip("选择自定义 I2C DLL 路径")
        dll_row.addWidget(self.i2c_dll_browse_btn)
        self.i2c_dll_reset_btn = QPushButton("Reset")
        self.i2c_dll_reset_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_dll_reset_btn.setStyleSheet(_i2c_action_style())
        self.i2c_dll_reset_btn.setToolTip("恢复自动查找 DLL 路径")
        dll_row.addWidget(self.i2c_dll_reset_btn)
        root.addLayout(dll_row)

        # 默认速率
        speed_title = QLabel("Default Speed")
        speed_title.setObjectName("cardTitle")
        root.addWidget(speed_title)
        self.i2c_speed_combo = DarkComboBox(bg="#091426", border="#17345f")
        self.i2c_speed_combo.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_speed_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for mode, text in self._i2c_speed_options:
            self.i2c_speed_combo.addItem(text, userData=mode)
        self.i2c_speed_combo.setCurrentIndex(1)
        root.addWidget(self.i2c_speed_combo)

        # 默认位宽
        width_title = QLabel("Default Width")
        width_title.setObjectName("cardTitle")
        root.addWidget(width_title)
        self.i2c_width_combo = DarkComboBox(bg="#091426", border="#17345f")
        self.i2c_width_combo.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_width_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for flag, (text, _a, _d) in _I2C_WIDTH_META.items():
            self.i2c_width_combo.addItem(text, userData=flag)
        self.i2c_width_combo.setCurrentIndex(1)
        root.addWidget(self.i2c_width_combo)

        # 芯片检测
        cc_title = QLabel("Chip Check")
        cc_title.setObjectName("cardTitle")
        root.addWidget(cc_title)
        self.i2c_chipcheck_btn = QPushButton("BES Chip Check")
        self.i2c_chipcheck_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_chipcheck_btn.setStyleSheet(_i2c_accent_style())
        self.i2c_chipcheck_btn.setToolTip("BES 芯片检测 (mainDie / PMU)")
        root.addWidget(self.i2c_chipcheck_btn)

        root.addStretch()
        return page

    def _build_i2c_access_card(self, layout):
        access_title = QLabel("Register Access")
        access_title.setObjectName("cardTitle")
        layout.addWidget(access_title)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        row1.setContentsMargins(0, 2, 0, 0)
        dev_lbl = QLabel("Dev Addr")
        dev_lbl.setFixedWidth(64)
        row1.addWidget(dev_lbl, 0, Qt.AlignVCenter)
        self.i2c_dev_edit = HexLineEdit(_reg_addr_bits(self._i2c_width))
        self.i2c_dev_edit.setStyleSheet(_i2c_input_style())
        self.i2c_dev_edit.set_value(0x27)
        row1.addWidget(self.i2c_dev_edit, 1)
        reg_lbl = QLabel("Reg Addr")
        reg_lbl.setFixedWidth(64)
        row1.addWidget(reg_lbl, 0, Qt.AlignVCenter)
        self.i2c_reg_edit = HexLineEdit(_reg_addr_bits(self._i2c_width))
        self.i2c_reg_edit.setStyleSheet(_i2c_input_style())
        self.i2c_reg_edit.set_value(0x0000)
        row1.addWidget(self.i2c_reg_edit, 1)
        width_lbl = QLabel("Width")
        width_lbl.setFixedWidth(48)
        row1.addWidget(width_lbl, 0, Qt.AlignVCenter)
        self.i2c_access_width_combo = DarkComboBox(bg="#091426", border="#17345f")
        self.i2c_access_width_combo.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_access_width_combo.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        for flag, (text, _a, _d) in _I2C_WIDTH_META.items():
            self.i2c_access_width_combo.addItem(text, userData=flag)
        self.i2c_access_width_combo.setCurrentIndex(1)
        row1.addWidget(self.i2c_access_width_combo, 1)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        row2.setContentsMargins(0, 2, 0, 0)
        op_lbl = QLabel("Op")
        op_lbl.setFixedWidth(64)
        row2.addWidget(op_lbl, 0, Qt.AlignVCenter)
        self.i2c_op_combo = DarkComboBox(bg="#091426", border="#17345f")
        self.i2c_op_combo.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_op_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for key, text in _I2C_OP_OPTIONS:
            self.i2c_op_combo.addItem(text, userData=key)
        self.i2c_op_combo.setCurrentIndex(0)
        row2.addWidget(self.i2c_op_combo, 1)
        data_lbl = QLabel("Data")
        data_lbl.setFixedWidth(48)
        row2.addWidget(data_lbl, 0, Qt.AlignVCenter)
        self.i2c_data_edit = HexLineEdit(_data_bits(self._i2c_width))
        self.i2c_data_edit.setStyleSheet(_i2c_input_style())
        row2.addWidget(self.i2c_data_edit, 1)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.setSpacing(6)
        row3.setContentsMargins(0, 2, 0, 0)
        self.i2c_bitrange_lbl = QLabel("Bit Range")
        self.i2c_bitrange_lbl.setFixedWidth(64)
        row3.addWidget(self.i2c_bitrange_lbl, 0, Qt.AlignVCenter)
        self.i2c_high_edit = HexLineEdit(6)
        self.i2c_high_edit.setStyleSheet(_i2c_input_style())
        self.i2c_high_edit.set_value(7)
        sep_lbl = QLabel(":")
        sep_lbl.setFixedWidth(8)
        sep_lbl.setAlignment(Qt.AlignCenter)
        self.i2c_low_edit = HexLineEdit(6)
        self.i2c_low_edit.setStyleSheet(_i2c_input_style())
        self.i2c_low_edit.set_value(0)
        row3.addWidget(self.i2c_high_edit, 1)
        row3.addWidget(sep_lbl, 0, Qt.AlignVCenter)
        row3.addWidget(self.i2c_low_edit, 1)
        layout.addLayout(row3)

        action_row = QHBoxLayout()
        action_row.setSpacing(6)
        action_row.setContentsMargins(0, 4, 0, 0)
        self.i2c_read_btn = QPushButton("Read")
        self.i2c_read_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_read_btn.setStyleSheet(_i2c_accent_style())
        self.i2c_write_btn = QPushButton("Write")
        self.i2c_write_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_write_btn.setStyleSheet(_i2c_accent_style())
        action_row.addWidget(self.i2c_read_btn, 1)
        action_row.addWidget(self.i2c_write_btn, 1)
        layout.addLayout(action_row)

        result_row = QHBoxLayout()
        result_row.setSpacing(6)
        result_row.setContentsMargins(0, 2, 0, 0)
        result_lbl = QLabel("Last Op")
        result_lbl.setFixedWidth(64)
        result_row.addWidget(result_lbl, 0, Qt.AlignVCenter)
        self.i2c_result_label = QLabel("—")
        self.i2c_result_label.setObjectName("statusOk")
        self.i2c_result_label.setStyleSheet(
            "color:#15d1a3; font-weight:600; background:transparent;")
        self.i2c_result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        result_row.addWidget(self.i2c_result_label, 1)
        layout.addLayout(result_row)

    def _build_i2c_bitview_card(self, layout):
        bv_title = QLabel("Bit Field View")
        bv_title.setObjectName("cardTitle")
        layout.addWidget(bv_title)

        val_row = QHBoxLayout()
        val_row.setSpacing(6)
        val_row.setContentsMargins(0, 2, 0, 0)
        val_lbl = QLabel("Value")
        val_lbl.setFixedWidth(64)
        val_row.addWidget(val_lbl, 0, Qt.AlignVCenter)
        self.i2c_value_edit = HexLineEdit(_data_bits(self._i2c_width))
        self.i2c_value_edit.setStyleSheet(_i2c_input_style())
        val_row.addWidget(self.i2c_value_edit, 1)
        self.i2c_value_read_btn = QPushButton("Read")
        self.i2c_value_read_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_value_read_btn.setStyleSheet(_i2c_action_style())
        self.i2c_value_write_btn = QPushButton("Write")
        self.i2c_value_write_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_value_write_btn.setStyleSheet(_i2c_action_style())
        val_row.addWidget(self.i2c_value_read_btn)
        val_row.addWidget(self.i2c_value_write_btn)
        layout.addLayout(val_row)

        self.i2c_bit_grid = BitGridView(_data_bits(self._i2c_width))
        grid_container = QWidget()
        grid_container.setStyleSheet("background:transparent;")
        gl = QHBoxLayout(grid_container)
        gl.setContentsMargins(0, 4, 0, 4)
        gl.addWidget(self.i2c_bit_grid, 1)
        layout.addWidget(grid_container)

        self.i2c_bin_label = QLabel("")
        self.i2c_bin_label.setAlignment(Qt.AlignCenter)
        self.i2c_bin_label.setStyleSheet(
            "color:#7e96bf; font-family:Consolas,monospace; background:transparent;")
        self.i2c_bin_label.setWordWrap(False)
        layout.addWidget(self.i2c_bin_label)

        fields_title_row = QHBoxLayout()
        fields_title_row.setSpacing(6)
        fields_title = QLabel("Bit Fields")
        fields_title.setStyleSheet(
            "color:#7e96bf; font-size:11px; background:transparent;")
        fields_title_row.addWidget(fields_title)
        fields_title_row.addStretch()
        self.i2c_add_field_btn = QPushButton("+ Field")
        self.i2c_add_field_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_add_field_btn.setStyleSheet(_i2c_action_style())
        fields_title_row.addWidget(self.i2c_add_field_btn)
        layout.addLayout(fields_title_row)

        self.i2c_fields_table = QTableWidget(0, 5)
        self.i2c_fields_table.setHorizontalHeaderLabels(
            ["Field", "High", "Low", "Value", "Description"])
        self.i2c_fields_table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.i2c_fields_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.i2c_fields_table.verticalHeader().setVisible(False)
        self.i2c_fields_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.i2c_fields_table.setStyleSheet(self._i2c_table_qss())
        header = self.i2c_fields_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        self.i2c_fields_table.setMinimumHeight(120)
        layout.addWidget(self.i2c_fields_table)

    def _build_i2c_register_map_card(self, layout):
        map_title = QLabel("Register Map (Template)")
        map_title.setObjectName("cardTitle")
        layout.addWidget(map_title)

        map_btn_row = QHBoxLayout()
        map_btn_row.setSpacing(6)
        map_btn_row.setContentsMargins(0, 2, 0, 0)
        self.i2c_save_tpl_btn = QPushButton("Save")
        self.i2c_load_tpl_btn = QPushButton("Load")
        self.i2c_add_reg_btn = QPushButton("+ Reg")
        self.i2c_readall_btn = QPushButton("Read All")
        for btn in (self.i2c_save_tpl_btn, self.i2c_load_tpl_btn,
                    self.i2c_add_reg_btn, self.i2c_readall_btn):
            btn.setFixedHeight(I2C_BTN_HEIGHT)
            btn.setStyleSheet(_i2c_action_style())
            map_btn_row.addWidget(btn)
        layout.addLayout(map_btn_row)

        self.i2c_reg_table = QTableWidget(0, 5)
        self.i2c_reg_table.setHorizontalHeaderLabels(
            ["Name", "Reg Addr", "Width", "Fields", "Description"])
        self.i2c_reg_table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.i2c_reg_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.i2c_reg_table.verticalHeader().setVisible(False)
        self.i2c_reg_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.i2c_reg_table.setStyleSheet(self._i2c_table_qss())
        rheader = self.i2c_reg_table.horizontalHeader()
        rheader.setSectionResizeMode(0, QHeaderView.Stretch)
        rheader.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        rheader.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        rheader.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        rheader.setSectionResizeMode(4, QHeaderView.Stretch)
        self.i2c_reg_table.setMinimumHeight(140)
        layout.addWidget(self.i2c_reg_table)

    @staticmethod
    def _i2c_table_qss():
        return (
            "QTableWidget { background-color:#091426; border:1px solid #17345f;"
            " border-radius:6px; gridline-color:#1a2850; color:#dce7ff; }"
            "QHeaderView::section { background-color:#0b1430; color:#7e96bf;"
            " border:0; padding:4px; font-weight:600; }"
            "QTableWidget::item { padding:2px 4px; }"
            "QTableWidget::item:selected { background-color:#1f4a8a; }"
        )

    # ---- 信号绑定 ----

    def bind_i2c_signals(self):
        self.i2c_dll_browse_btn.clicked.connect(self._on_i2c_browse_dll)
        self.i2c_dll_reset_btn.clicked.connect(self._on_i2c_reset_dll)
        self.i2c_chipcheck_btn.clicked.connect(self._on_i2c_chip_check)
        self.i2c_read_btn.clicked.connect(self._on_i2c_read)
        self.i2c_write_btn.clicked.connect(self._on_i2c_write)
        self.i2c_value_read_btn.clicked.connect(self._on_i2c_value_read)
        self.i2c_value_write_btn.clicked.connect(self._on_i2c_value_write)
        self.i2c_value_edit.value_changed.connect(self._on_i2c_value_edited)
        self.i2c_bit_grid.value_changed.connect(self._on_i2c_bit_toggled)
        self.i2c_add_field_btn.clicked.connect(self._on_i2c_add_field)
        self.i2c_fields_table.cellChanged.connect(self._on_i2c_field_cell_changed)
        self.i2c_fields_table.customContextMenuRequested.connect(
            self._on_i2c_field_context_menu)
        self.i2c_access_width_combo.currentIndexChanged.connect(
            self._on_i2c_access_width_changed)
        self.i2c_width_combo.currentIndexChanged.connect(
            self._on_i2c_default_width_changed)
        self.i2c_speed_combo.currentIndexChanged.connect(
            self._on_i2c_default_speed_changed)
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
            "color:#15d1a3; font-weight:600; background:transparent;"
            if ok else
            "color:#ff5e7a; font-weight:600; background:transparent;")

    def append_log(self, msg):
        """供页面覆写：默认转发到 logger。"""
        logger.info(msg)

    def _i2c_set_busy(self, busy):
        for attr in ("i2c_read_btn", "i2c_write_btn", "i2c_value_read_btn",
                     "i2c_value_write_btn", "i2c_chipcheck_btn",
                     "i2c_readall_btn"):
            w = getattr(self, attr, None)
            if w is not None:
                w.setEnabled(not busy)

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

    def _on_i2c_default_width_changed(self, _idx):
        from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag
        flag = self.i2c_width_combo.currentData()
        if flag is None:
            return
        self._i2c_width = flag
        # 同步控制页的位宽下拉
        for i in range(self.i2c_access_width_combo.count()):
            if self.i2c_access_width_combo.itemData(i) == flag:
                self.i2c_access_width_combo.blockSignals(True)
                self.i2c_access_width_combo.setCurrentIndex(i)
                self.i2c_access_width_combo.blockSignals(False)
                break
        self._i2c_sync_width_ui()
        self.append_log(f"[I2C] 默认位宽切换为 {_width_label(flag)}")

    def _on_i2c_access_width_changed(self, _idx):
        from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag
        flag = self.i2c_access_width_combo.currentData()
        if flag is None:
            return
        self._i2c_width = flag
        for i in range(self.i2c_width_combo.count()):
            if self.i2c_width_combo.itemData(i) == flag:
                self.i2c_width_combo.blockSignals(True)
                self.i2c_width_combo.setCurrentIndex(i)
                self.i2c_width_combo.blockSignals(False)
                break
        self._i2c_sync_width_ui()

    def _i2c_sync_width_ui(self):
        reg_bits = _reg_addr_bits(self._i2c_width)
        data_bits = _data_bits(self._i2c_width)
        self.i2c_dev_edit.set_bit_count(reg_bits)
        self.i2c_reg_edit.set_bit_count(reg_bits)
        self.i2c_data_edit.set_bit_count(data_bits)
        self.i2c_value_edit.set_bit_count(data_bits)
        self.i2c_bit_grid.set_bit_count(data_bits)
        self.i2c_value_edit.set_value(self.i2c_value_edit.value())
        self.i2c_bit_grid.set_value(self.i2c_value_edit.value())
        self._i2c_refresh_bin_label()
        self._i2c_refresh_field_values()

    # ---- 读写操作（按需初始化 I2C） ----

    def _i2c_current_dev(self):
        return self.i2c_dev_edit.value()

    def _i2c_current_reg(self):
        return self.i2c_reg_edit.value()

    def _i2c_current_op(self):
        return self.i2c_op_combo.currentData() or I2C_OP_READ

    def _start_i2c_read(self, dev, reg, use_raw, tag=""):
        if (self._i2c_read_thread is not None
                and self._i2c_read_thread.isRunning()):
            return
        self._i2c_set_busy(True)
        self._i2c_set_result(f"Reading 0x{dev:02X} @ 0x{reg:X}...", ok=True)
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
        op = self._i2c_current_op()
        if op in (I2C_OP_WRITE, I2C_OP_BIT_WRITE, I2C_OP_WRITE_DATA):
            self._on_i2c_write()
            return
        use_raw = op == I2C_OP_READ_DATA
        self._start_i2c_read(self._i2c_current_dev(),
                             self._i2c_current_reg(), use_raw)

    def _on_i2c_read_thread_cleanup(self):
        self._i2c_read_thread = None
        self._i2c_read_worker = None

    def _on_i2c_read_done(self, value):
        bits = _data_bits(self._i2c_width)
        self._i2c_set_result(
            f"{_fmt_hex(value, bits)}  ({value})  bin {_fmt_bin_grouped(value, bits)}",
            ok=True)
        self.i2c_value_edit.set_value(value)
        self.i2c_bit_grid.set_value(value)
        self._i2c_refresh_bin_label()
        self._i2c_refresh_field_values()
        self._i2c_set_busy(False)
        self.append_log(f"[I2C] Read => {_fmt_hex(value, bits)} ({value})")
        idx = getattr(self, "_i2c_pending_readall_idx", None)
        if idx is not None:
            self._i2c_readall_results[idx] = value
            self._i2c_pending_readall_idx = None
            if getattr(self, "_i2c_readall_queue", None):
                QTimer.singleShot(10, self._i2c_readall_next)

    def _on_i2c_read_error(self, err):
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
        self._i2c_set_result(
            f"Writing 0x{dev:02X} @ 0x{reg:X} bits={bit_desc}...", ok=True)
        self.append_log(
            f"[I2C] Write{tag} dev=0x{dev:02X} reg=0x{reg:X} "
            f"data={_fmt_hex(data, _data_bits(self._i2c_width))} "
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
        op = self._i2c_current_op()
        if op in (I2C_OP_READ, I2C_OP_READ_DATA):
            self._on_i2c_read()
            return
        dev = self._i2c_current_dev()
        reg = self._i2c_current_reg()
        data = self.i2c_data_edit.value()
        use_raw = op == I2C_OP_WRITE_DATA
        if op == I2C_OP_BIT_WRITE:
            high = self.i2c_high_edit.value()
            low = self.i2c_low_edit.value()
            if high < low:
                high, low = low, high
            width = max(high - low + 1, 1)
            field_mask = (1 << width) - 1
            data = data & field_mask
            self._start_i2c_write(dev, reg, data, high, low, use_raw)
        else:
            self._start_i2c_write(dev, reg, data, -1, -1, use_raw)

    def _on_i2c_write_done(self):
        self._i2c_set_result("Write OK", ok=True)
        self._i2c_set_busy(False)
        self.append_log("[I2C] Write 完成")

    def _on_i2c_write_error(self, err):
        self._i2c_set_result(f"Write Failed: {err}", ok=False)
        self._i2c_set_busy(False)
        self.append_log(f"[I2C] Write 失败: {err}")

    # ---- Bit Field View 交互 ----

    def _on_i2c_value_read(self):
        self._start_i2c_read(self._i2c_current_dev(),
                             self._i2c_current_reg(), False, tag=" (BitView)")

    def _on_i2c_value_write(self):
        if (self._i2c_write_thread is not None
                and self._i2c_write_thread.isRunning()):
            return
        dev = self._i2c_current_dev()
        reg = self._i2c_current_reg()
        data = self.i2c_bit_grid.value()
        self.i2c_data_edit.set_value(data)
        self._start_i2c_write(dev, reg, data, -1, -1, False, tag=" (BitView)")

    def _on_i2c_value_edited(self, value):
        self.i2c_bit_grid.set_value(value)
        self._i2c_refresh_bin_label()
        self._i2c_refresh_field_values()

    def _on_i2c_bit_toggled(self, value):
        self.i2c_value_edit.set_value(value)
        self._i2c_refresh_bin_label()
        self._i2c_refresh_field_values()

    def _i2c_refresh_bin_label(self):
        bits = _data_bits(self._i2c_width)
        v = self.i2c_bit_grid.value()
        self.i2c_bin_label.setText(
            f"bin: {_fmt_bin_grouped(v, bits)}    ({v})")

    # ---- 位域表 ----

    def _on_i2c_add_field(self):
        bits = _data_bits(self._i2c_width)
        self._i2c_fields.append({
            "name": f"FIELD{len(self._i2c_fields)}",
            "high_bit": min(7, bits - 1),
            "low_bit": 0,
            "description": "",
        })
        self._i2c_rebuild_fields_table()
        self._i2c_sync_active_register_fields()

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
        self._i2c_refresh_field_values()

    def _i2c_refresh_field_values(self):
        if not hasattr(self, "i2c_fields_table"):
            return
        value = self.i2c_bit_grid.value()
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

    def _on_i2c_field_context_menu(self, pos):
        row = self.i2c_fields_table.rowAt(pos.y())
        menu = QMenu(self.i2c_fields_table)
        menu.setStyleSheet(
            "QMenu { background-color:#091426; color:#dce7ff;"
            " border:1px solid #17345f; }"
            "QMenu::item:selected { background-color:#1f4a8a; }")
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
            "width": int(self._i2c_width),
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
            self.i2c_reg_table.setItem(row, 2, QTableWidgetItem(str(reg["width"])))
            nf = len(reg.get("bit_fields", []))
            self.i2c_reg_table.setItem(row, 3, QTableWidgetItem(str(nf)))
            self.i2c_reg_table.setItem(row, 4, QTableWidgetItem(reg["description"]))

    def _on_i2c_reg_double_clicked(self, row, _col):
        self._i2c_load_register(row)

    def _i2c_load_register(self, row):
        from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag
        if row < 0 or row >= len(self._i2c_registers):
            return
        reg = self._i2c_registers[row]
        self._i2c_active_reg_index = row
        try:
            width = I2CWidthFlag(int(reg.get("width", 1)))
        except Exception:
            width = I2CWidthFlag.BIT_10
        self._i2c_set_width_combo(width)
        self.i2c_reg_edit.set_value(_parse_hex_int(reg["reg_addr"]) or 0)
        self._i2c_fields = copy.deepcopy(reg.get("bit_fields", []))
        self._i2c_rebuild_fields_table()
        self.append_log(
            f"[I2C] 加载寄存器 {reg['name']} (addr={reg['reg_addr']}, "
            f"fields={len(self._i2c_fields)})")

    def _i2c_set_width_combo(self, width_flag):
        for i in range(self.i2c_width_combo.count()):
            if self.i2c_width_combo.itemData(i) == width_flag:
                self.i2c_width_combo.blockSignals(True)
                self.i2c_width_combo.setCurrentIndex(i)
                self.i2c_width_combo.blockSignals(False)
                break
        for i in range(self.i2c_access_width_combo.count()):
            if self.i2c_access_width_combo.itemData(i) == width_flag:
                self.i2c_access_width_combo.blockSignals(True)
                self.i2c_access_width_combo.setCurrentIndex(i)
                self.i2c_access_width_combo.blockSignals(False)
                break
        self._i2c_width = width_flag
        self._i2c_sync_width_ui()

    def _on_i2c_reg_context_menu(self, pos):
        row = self.i2c_reg_table.rowAt(pos.y())
        menu = QMenu(self.i2c_reg_table)
        menu.setStyleSheet(
            "QMenu { background-color:#091426; color:#dce7ff;"
            " border:1px solid #17345f; }"
            "QMenu::item:selected { background-color:#1f4a8a; }")
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
        from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag
        try:
            width = I2CWidthFlag(int(reg.get("width", 1)))
        except Exception:
            width = I2CWidthFlag.BIT_10
        self._i2c_set_width_combo(width)
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
        from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag
        try:
            width = I2CWidthFlag(int(reg.get("width", 1)))
        except Exception:
            width = I2CWidthFlag.BIT_10
        self._i2c_set_width_combo(width)
        dev = self._i2c_current_dev()
        reg_addr = _parse_hex_int(reg["reg_addr"]) or 0
        self.i2c_reg_edit.set_value(reg_addr)
        data = self.i2c_bit_grid.value()
        self.i2c_data_edit.set_value(data)
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
                f"{_fmt_hex(self._i2c_readall_results.get(i, 0), _data_bits(self._i2c_width))}"
                for i, reg in enumerate(self._i2c_registers)
            ) if self._i2c_registers else "(空)"
            self.append_log(f"[I2C] Read All 完成:\n{summary}")
            self._i2c_set_busy(False)
            return
        idx, reg = self._i2c_readall_queue.pop(0)
        from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag
        try:
            width = I2CWidthFlag(int(reg.get("width", 1)))
        except Exception:
            width = I2CWidthFlag.BIT_10
        self._i2c_set_width_combo(width)
        dev = self._i2c_current_dev()
        reg_addr = _parse_hex_int(reg["reg_addr"]) or 0
        self._i2c_pending_readall_idx = idx
        self._start_i2c_read(dev, reg_addr, False, tag=f" ({reg['name']})")

    # ---- 芯片检测 ----

    def _on_i2c_chip_check(self):
        if (self._i2c_chipcheck_thread is not None
                and self._i2c_chipcheck_thread.isRunning()):
            return
        self._i2c_set_busy(True)
        self._i2c_set_result("Chip checking...", ok=True)
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
            "default_width": int(self._i2c_width),
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

        from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag, I2CSpeedMode
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
        try:
            width = I2CWidthFlag(int(data.get("default_width", 1)))
            self._i2c_set_width_combo(width)
        except Exception:
            pass
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

_I2C_DARK_STYLE = """
    QWidget {
        background-color: #020817;
        color: #dbe7ff;
    }
    QLabel {
        background-color: transparent;
        color: #dbe7ff;
        border: none;
    }
    QLabel#cardTitle {
        font-size: 11px;
        font-weight: 700;
        color: #f4f7ff;
        letter-spacing: 0.5px;
        background-color: transparent;
    }
"""


class _DemoI2cWidget(I2cMixin, QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_i2c()
        self.setStyleSheet(_I2C_DARK_STYLE)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
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
    resize_and_center_window(w, size=(720, 760))
    w.show()
    sys.exit(app.exec())
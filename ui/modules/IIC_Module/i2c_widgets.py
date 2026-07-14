# I2C 自定义控件

import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QFrame, QSizePolicy, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QCheckBox,
)
from PySide6.QtCore import Qt, Signal, QRegularExpression
from PySide6.QtGui import QColor, QRegularExpressionValidator, QPainter

from ui.widgets.dark_combobox import DarkComboBox
from ui.modules.IIC_Module.i2c_constants import (
    I2C_BTN_HEIGHT, SLATE_950, SLATE_900, SLATE_800,
    INDIGO, INDIGO_LIGHT, EMERALD_LIGHT, TEXT_MUTED,
    _fmt_hex, _hex_digits, _parse_hex_int,
)
from ui.modules.IIC_Module.i2c_styles import (
    _i2c_input_style, _bit_val_style, _i2c_table_qss,
)


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

    def wheelEvent(self, event):
        """滚轮调整数值：默认 ±1，Ctrl=±16，Shift=±0x100。"""
        delta = event.angleDelta().y()
        if delta == 0:
            return
        step = 1
        if event.modifiers() & Qt.ControlModifier:
            step = 16
        elif event.modifiers() & Qt.ShiftModifier:
            step = 0x100
        if delta < 0:
            step = -step
        new_val = (self.value() + step) & self._mask()
        self.set_value(new_val, emit=True)
        event.accept()


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

    def wheelEvent(self, event):
        """滚轮调整数值：默认 ±1，Ctrl=±16，Shift=±0x100。"""
        delta = event.angleDelta().y()
        if delta == 0:
            return
        step = 1
        if event.modifiers() & Qt.ControlModifier:
            step = 16
        elif event.modifiers() & Qt.ShiftModifier:
            step = 0x100
        if delta < 0:
            step = -step
        new_val = (self.value() + step) & self._mask()
        self.set_value(new_val, emit=True)
        event.accept()


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

    def wheelEvent(self, event):
        """滚轮调整数值：默认 ±1，Ctrl=±16，Shift=±0x100。"""
        delta = event.angleDelta().y()
        if delta == 0:
            return
        step = 1
        if event.modifiers() & Qt.ControlModifier:
            step = 16
        elif event.modifiers() & Qt.ShiftModifier:
            step = 0x100
        if delta < 0:
            step = -step
        new_val = (self.value() + step) & self._mask()
        self.set_value(new_val, emit=True)
        event.accept()


# ---------------------------------------------------------------------------
# 自定义控件：位操作表格（Bit / Val / Field / Description / Hex + 字段合并）
# ---------------------------------------------------------------------------

class BitsTable(QTableWidget):
    """单段位表格。bit_offset/bit_count 决定显示区间（MSB 在上）。
    同一字段的多个 Bit 自动合并 Field/Description/Hex 单元格（rowSpan）。"""
    bit_toggled = Signal(int)  # 绝对位索引
    field_edited = Signal(int, int, str)  # (field_index, column, text) col: 2=name 3=desc

    def __init__(self, bit_offset, bit_count, parent=None):
        super().__init__(0, 5, parent)
        self._offset = bit_offset
        self._count = bit_count
        self._fields = []
        self._edit_mode = False
        self.setObjectName("bitsTable")
        self.setHorizontalHeaderLabels(["Bit", "Val", "Field", "Desc", "Hex"])
        self.verticalHeader().setVisible(False)
        # Val 列是 bit 切换按钮,点击只应切换该 bit,不应选中整行
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.NoSelection)
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
        self.cellChanged.connect(self._on_cell_changed)

    def set_edit_mode(self, enabled):
        """开启/关闭 Field/Desc 列的内联编辑。"""
        self._edit_mode = enabled
        if enabled:
            self.setEditTriggers(
                QAbstractItemView.DoubleClicked
                | QAbstractItemView.EditKeyPressed)
        else:
            self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._apply_field_edit_flags()

    def _apply_field_edit_flags(self):
        """根据编辑模式设置 Field/Desc 单元格的可编辑标志。"""
        editable = self._edit_mode
        for i in range(self._count):
            for c in (2, 3):
                it = self.item(i, c)
                if it is not None:
                    flags = it.flags()
                    if editable:
                        flags |= Qt.ItemIsEditable
                    else:
                        flags &= ~Qt.ItemIsEditable
                    it.setFlags(flags)

    def _on_cell_changed(self, row, col):
        """Field(col 2) / Desc(col 3) 内联编辑 → 通知 mixin 更新字段数据。"""
        if not self._edit_mode:
            return
        if col not in (2, 3):
            return
        fidx = self._field_index_at_row(row)
        if fidx is None:
            return
        it = self.item(row, col)
        text = it.text() if it is not None else ""
        self.field_edited.emit(fidx, col, text)

    def _field_index_at_row(self, row):
        """返回该行所属 field 在 self._fields 中的索引，无则 None。"""
        bit = self._abs_bit(row)
        for i, f in enumerate(self._fields):
            fhi = int(f["high_bit"])
            flo = int(f["low_bit"])
            if fhi < flo:
                fhi, flo = flo, fhi
            if flo <= bit <= fhi:
                return i
        return None

    def field_at_row(self, row):
        """返回该行所属 field 的 (index, dict)，无则 (None, None)。"""
        idx = self._field_index_at_row(row)
        if idx is None:
            return None, None
        return idx, self._fields[idx]

    def abs_bit_at_row(self, row):
        """返回该行对应的绝对位索引。"""
        if 0 <= row < self._count:
            return self._abs_bit(row)
        return None

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
        self._apply_field_edit_flags()

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
    field_edited = Signal(int, int, str)  # (field_index, column, text)
    field_context_menu = Signal(object, int)  # (bits_table, row)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tables = []
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(10)

    def _connect_table(self, t):
        t.bit_toggled.connect(self.bit_toggled)
        t.field_edited.connect(self.field_edited)
        t.setContextMenuPolicy(Qt.CustomContextMenu)
        t.customContextMenuRequested.connect(
            lambda pos, tbl=t: self._on_context_menu(tbl, pos))

    def _on_context_menu(self, tbl, pos):
        row = tbl.rowAt(pos.y())
        if row >= 0:
            self.field_context_menu.emit(tbl, row)

    def set_bit_count(self, n):
        for t in self._tables:
            t.bit_toggled.disconnect()
            self._layout.removeWidget(t)
            t.deleteLater()
        self._tables = []
        if n <= 16:
            t = BitsTable(0, n)
            self._connect_table(t)
            self._layout.addWidget(t, 1)
            self._tables.append(t)
        else:
            half = (n + 1) // 2  # 高位段位数
            hi_t = BitsTable(half, n - half)
            lo_t = BitsTable(0, half)
            for t in (hi_t, lo_t):
                self._connect_table(t)
            self._layout.addWidget(hi_t, 1)
            sep = QFrame()
            sep.setFrameShape(QFrame.VLine)
            sep.setStyleSheet(f"color:{SLATE_800}; background:transparent;")
            self._layout.addWidget(sep, 0)
            self._layout.addWidget(lo_t, 1)
            self._tables = [hi_t, lo_t]

    def set_edit_mode(self, enabled):
        for t in self._tables:
            t.set_edit_mode(enabled)

    def set_value(self, full_value):
        for t in self._tables:
            t.set_value(full_value)

    def set_fields(self, fields):
        for t in self._tables:
            t.set_fields(fields)

    def refresh_fields(self, fields):
        for t in self._tables:
            t.set_fields(fields)


class _ToggleSwitch(QCheckBox):
    """滑动开关：基于 QCheckBox 自绘，左侧 OFF / 右侧 ON 时滑块位移。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(40, 22)
        self.setText("")

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        h = self.height()
        w = self.width()
        track_r = h / 2
        knob_d = h - 6
        # Track
        if self.isChecked():
            p.setBrush(QColor(INDIGO))
        else:
            p.setBrush(QColor(SLATE_800))
        p.drawRoundedRect(0, 0, w, h, track_r, track_r)
        # Knob
        knob_x = w - knob_d - 3 if self.isChecked() else 3
        p.setBrush(QColor("#e2e8f0"))
        p.drawEllipse(int(knob_x), 3, int(knob_d), int(knob_d))

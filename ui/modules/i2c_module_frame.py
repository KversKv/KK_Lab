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
    QButtonGroup, QPlainTextEdit
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


def _parse_int_safe(text):
    """安全解析十进制整数（用于位索引、延时等），失败返回 0。"""
    try:
        return int((text or "").strip())
    except (ValueError, TypeError):
        return 0


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


class _I2cSequenceWorker(QObject):
    """按需初始化 I2C → 解析 DSL → 执行（支持变量/循环/条件）。

    commands 为字符串列表，每条是一行 DSL 指令。
    """
    progress = Signal(str)   # 执行日志
    finished = Signal()       # 正常结束
    error = Signal(str)       # 致命异常

    def __init__(self, dll_path, speed_mode, device_addr, width_flag,
                 commands, script_name=""):
        super().__init__()
        self._dll = dll_path
        self._speed = speed_mode
        self._dev = device_addr
        self._width = width_flag
        self._commands = commands or []
        self._name = script_name
        self._stop = False
        self._vars = {}

    def request_stop(self):
        self._stop = True

    def run(self):
        from lib.i2c.i2c_interface_x64 import I2CInterface
        i2c = I2CInterface(dll_path=self._dll, speed_mode=self._speed)
        try:
            if not i2c.initialize():
                self.error.emit("I2C 接口初始化失败 (DLL 加载或设备打开失败)")
                return
            ast_nodes, err = _build_ast(self._commands)
            if err:
                self.error.emit(err)
                return
            total = len(self._commands)
            if self._name:
                self.progress.emit("--- {0} ({1} 行) ---".format(
                    self._name, total))
            else:
                self.progress.emit("序列开始: {0} 行".format(total))
            self._exec_block(i2c, ast_nodes, "")
            if self._stop:
                self.progress.emit("已用户停止")
            else:
                self.progress.emit("序列执行完成")
            self.finished.emit()
        except Exception as e:
            logger.error("I2C sequence failed: %s", e, exc_info=True)
            self.error.emit(str(e))
        finally:
            try:
                i2c.close()
            except Exception:
                pass

    def _exec_block(self, i2c, nodes, prefix):
        for node in nodes:
            if self._stop:
                return
            kind = node[0]
            if kind == "CMD":
                self._exec_cmd(i2c, node[1], prefix)
            elif kind == "LOOP":
                _, count_expr, body = node
                count = _resolve_token(count_expr, 10, self._vars)
                self.progress.emit("{0}LOOP x{1}".format(prefix, count))
                for it in range(count):
                    if self._stop:
                        return
                    self._exec_block(i2c, body,
                                     "{0}[{1}/{2}] ".format(prefix, it + 1, count))
            elif kind == "IF":
                _, cond, body = node
                try:
                    result = _eval_condition(i2c, self._dev, self._width,
                                             cond, self._vars,
                                             self.progress.emit)
                except Exception as e:
                    self.progress.emit("{0}IF 条件求值失败: {1}".format(prefix, e))
                    raise
                if result:
                    self._exec_block(i2c, body, prefix)

    def _exec_cmd(self, i2c, cmd, prefix):
        op = str(cmd.get("type", "")).upper()
        reg_bits = _reg_addr_bits(self._width)
        data_bits = _data_bits(self._width)
        if op == "DELAY":
            ms = _resolve_token(cmd.get("ms", "0"), 10, self._vars)
            self.progress.emit("{0}DELAY {1} ms".format(prefix, ms))
            QThread.msleep(max(0, ms))
            return
        if op == "WRITE_BITS":
            addr = _resolve_token(cmd["addr"], 16, self._vars)
            high = _resolve_token(cmd["high"], 10, self._vars)
            low = _resolve_token(cmd["low"], 10, self._vars)
            value = _resolve_token(cmd["value"], 16, self._vars)
            self.progress.emit(
                "{0}WRITE_BITS addr={1} [{2}:{3}] = {4}".format(
                    prefix, _fmt_hex(addr, reg_bits), high, low,
                    _fmt_hex(value, data_bits)))
            i2c.write(self._dev, addr, value, self._width, high, low)
            return
        if op == "WRITE":
            addr = _resolve_token(cmd["addr"], 16, self._vars)
            value = _resolve_token(cmd["value"], 16, self._vars)
            self.progress.emit(
                "{0}WRITE addr={1} = {2}".format(
                    prefix, _fmt_hex(addr, reg_bits),
                    _fmt_hex(value, data_bits)))
            i2c.write(self._dev, addr, value, self._width, -1, -1)
            return
        if op == "READ":
            addr = _resolve_token(cmd["addr"], 16, self._vars)
            val = i2c.read(self._dev, addr, self._width)
            to_var = cmd.get("to")
            if to_var:
                self._vars[to_var] = val
                self.progress.emit(
                    "{0}READ addr={1} => {2} ({3}) -> ${4}".format(
                        prefix, _fmt_hex(addr, reg_bits),
                        _fmt_hex(val, data_bits), val, to_var))
            else:
                self.progress.emit(
                    "{0}READ addr={1} => {2} ({3})".format(
                        prefix, _fmt_hex(addr, reg_bits),
                        _fmt_hex(val, data_bits), val))
            return
        if op == "READ_RANGE":
            start = _resolve_token(cmd["start"], 16, self._vars)
            stop = _resolve_token(cmd["stop"], 16, self._vars)
            step = _resolve_token(cmd.get("step", "1"), 10, self._vars) or 1
            delay = _resolve_token(cmd.get("delay", "0"), 10, self._vars)
            self.progress.emit(
                "{0}READ_RANGE {1}..{2} step={3} delay={4}ms".format(
                    prefix, _fmt_hex(start, reg_bits),
                    _fmt_hex(stop, reg_bits), step, delay))
            addr = start
            while addr <= stop:
                if self._stop:
                    return
                val = i2c.read(self._dev, addr, self._width)
                self.progress.emit(
                    "  {0} => {1} ({2})".format(
                        _fmt_hex(addr, reg_bits),
                        _fmt_hex(val, data_bits), val))
                addr += step
                if delay > 0 and addr <= stop:
                    QThread.msleep(delay)
            return
        self.progress.emit("{0}未知指令(跳过): {1}".format(prefix, op))


# ---------------------------------------------------------------------------
# 序列脚本 DSL 解析（变量 / 循环 / 条件 / 批量读取）
# ---------------------------------------------------------------------------


def _strip_dsl_line(raw):
    """剥离注释与列表标记，返回净指令文本；空行返回 ''。"""
    # 行内注释 // 或 # （# 必须在行首或前面是空白才视为整行注释，行内 # 也剥）
    line = raw
    # 整行注释
    stripped = line.strip()
    if stripped.startswith("#") or stripped.startswith("//"):
        return ""
    # 行内 // 注释
    if "//" in line:
        line = line.split("//", 1)[0]
    line = line.strip()
    # 去掉前导 "- " 列表标记
    if line.startswith("-"):
        line = line[1:].strip()
    return line


def _parse_dsl_line(raw):
    """解析一行 DSL，返回指令 dict；空行/注释返回 None。

    数值解析规则（在执行时按 default_base 解析，这里只保留 token 字符串）：
      地址/寄存器相关参数 → 默认十六进制
      步长/延时/循环次数/位号 → 默认十进制
      0x 前缀 → 强制十六进制
      $ 前缀 → 变量
    """
    line = _strip_dsl_line(raw)
    if not line:
        return None
    parts = line.split()
    op = parts[0].upper()
    if op == "WRITE" and len(parts) >= 3:
        return {"type": "WRITE", "addr": parts[1], "value": parts[2]}
    if op == "READ":
        # READ addr  或  READ addr TO $var
        if len(parts) >= 4 and parts[2].upper() == "TO":
            var = parts[3]
            if var.startswith("$"):
                var = var[1:]
            return {"type": "READ", "addr": parts[1], "to": var}
        if len(parts) >= 2:
            return {"type": "READ", "addr": parts[1], "to": None}
        return None
    if op == "WRITE_BITS" and len(parts) >= 5:
        return {"type": "WRITE_BITS", "addr": parts[1],
                "high": parts[2], "low": parts[3], "value": parts[4]}
    if op == "DELAY" and len(parts) >= 2:
        return {"type": "DELAY", "ms": parts[1]}
    if op == "READ_RANGE" and len(parts) >= 3:
        cmd = {"type": "READ_RANGE", "start": parts[1], "stop": parts[2]}
        if len(parts) >= 4:
            cmd["step"] = parts[3]
        if len(parts) >= 5:
            cmd["delay"] = parts[4]
        return cmd
    if op == "LOOP" and len(parts) >= 2:
        return {"type": "LOOP", "count_expr": parts[1]}
    if op == "END_LOOP":
        return {"type": "END_LOOP"}
    if op == "IF" and len(parts) >= 2:
        # IF 后面全部为条件表达式
        cond = line[len(parts[0]):].strip()
        return {"type": "IF", "condition": cond}
    if op == "END_IF":
        return {"type": "END_IF"}
    # 无法识别 → 原样保留为注释型指令
    return {"type": "UNKNOWN", "raw": line}


def _build_ast(command_lines):
    """将 DSL 字符串列表解析为嵌套 AST。

    返回 (nodes, error_msg)。error_msg 非空表示语法错误。
    节点类型：
      ("CMD", parsed_dict)
      ("LOOP", count_expr, [body_nodes])
      ("IF", condition_str, [body_nodes])
    """
    parsed = []
    for raw in command_lines:
        p = _parse_dsl_line(raw)
        if p is not None:
            parsed.append(p)

    def parse_block(start, end_tokens):
        """返回 (nodes, end_index, error_msg)。"""
        nodes = []
        i = start
        while i < len(parsed):
            p = parsed[i]
            op = p["type"]
            if op in end_tokens:
                return nodes, i, None
            if op == "LOOP":
                body, end_i, err = parse_block(i + 1, {"END_LOOP"})
                if err:
                    return nodes, end_i, err
                if end_i >= len(parsed):
                    return nodes, len(parsed), "LOOP 缺少 END_LOOP"
                nodes.append(("LOOP", p["count_expr"], body))
                i = end_i + 1
            elif op == "IF":
                body, end_i, err = parse_block(i + 1, {"END_IF"})
                if err:
                    return nodes, end_i, err
                if end_i >= len(parsed):
                    return nodes, len(parsed), "IF 缺少 END_IF"
                nodes.append(("IF", p["condition"], body))
                i = end_i + 1
            elif op in ("END_LOOP", "END_IF"):
                # 多余的结束符
                return nodes, i, None
            else:
                nodes.append(("CMD", p))
                i += 1
        return nodes, i, None

    nodes, _end, err = parse_block(0, set())
    return nodes, err


# ---- 表达式 / 条件求值 ----

_SEQ_COND_OPS = ["==", "!=", ">=", "<=", ">", "<", "&", "|", "^"]


def _resolve_token(token, default_base, variables):
    """解析单个 token 为 int。

    - $var → 变量值（不存在为 0）
    - 0x 前缀 → 十六进制
    - 否则按 default_base 解析（16=十六进制默认, 10=十进制默认）
    """
    if token is None:
        return 0
    t = str(token).strip()
    if not t:
        return 0
    if t.startswith("$"):
        return int(variables.get(t[1:], 0))
    if t.lower().startswith("0x"):
        return int(t, 16)
    return int(t, default_base)


def _eval_expr(i2c, dev, width, expr, variables, emit):
    """求值表达式，返回 int。

    支持：
      $var              → 变量值
      READ <addr>       → 执行读取，返回结果
      <number>          → 字面量（默认十六进制）
    """
    e = expr.strip()
    if not e:
        return 0
    if e.startswith("$"):
        return int(variables.get(e[1:], 0))
    up = e.upper()
    if up.startswith("READ "):
        # READ <addr>
        sub = _parse_dsl_line(e)
        if sub and sub.get("type") == "READ":
            addr = _resolve_token(sub["addr"], 16, variables)
            val = i2c.read(dev, addr, width)
            data_bits = _data_bits(width)
            emit("    (IF-READ addr={0} => {1})".format(
                _fmt_hex(addr, _reg_addr_bits(width)),
                _fmt_hex(val, data_bits)))
            return val
        return 0
    # 字面量，默认十六进制
    return _resolve_token(e, 16, variables)


def _eval_condition(i2c, dev, width, cond_str, variables, emit):
    """求值 IF 条件，返回 bool。"""
    cond = cond_str.strip()
    # 查找操作符（先查双字符）
    op_found = None
    left_str = cond
    right_str = ""
    for op in _SEQ_COND_OPS:
        # 用空格或直接连接都要匹配，找最早出现
        idx = _find_operator(cond, op)
        if idx >= 0:
            op_found = op
            left_str = cond[:idx].strip()
            right_str = cond[idx + len(op):].strip()
            break
    if op_found is None:
        # 无操作符：非零即真
        val = _eval_expr(i2c, dev, width, cond, variables, emit)
        return val != 0
    left = _eval_expr(i2c, dev, width, left_str, variables, emit)
    right = _eval_expr(i2c, dev, width, right_str, variables, emit)
    if op_found == "==":
        return left == right
    if op_found == "!=":
        return left != right
    if op_found == ">":
        return left > right
    if op_found == "<":
        return left < right
    if op_found == ">=":
        return left >= right
    if op_found == "<=":
        return left <= right
    if op_found == "&":
        return (left & right) != 0
    if op_found == "|":
        return (left | right) != 0
    if op_found == "^":
        return (left ^ right) != 0
    return False


def _find_operator(text, op):
    """在 text 中查找操作符 op 的位置，避免拆散 0x 等；返回 -1 表示未找到。

    优先匹配带空格包围的形式；若无空格也接受。需保证双字符操作符先于单字符。
    """
    # 先找带空格的 " op "
    spaced = " {0} ".format(op)
    idx = text.find(spaced)
    if idx >= 0:
        return idx + 1
    # 再找无空格的（但避免匹配到 0x 中的字符等：& | ^ 不会出现在数字里，> < 也安全）
    idx = text.find(op)
    if idx >= 0:
        return idx
    return -1


# ---------------------------------------------------------------------------
# 序列脚本序列化 / 持久化（YAML，commands 为字符串列表）
# ---------------------------------------------------------------------------

_SEQ_CMD_TYPES = ["WRITE", "READ", "WRITE_BITS", "DELAY", "READ_RANGE",
                  "LOOP", "END_LOOP", "IF", "END_IF"]


def _i2c_sequence_dir():
    return get_user_data_dir("i2c_sequences")


try:
    import yaml as _yaml
except Exception:
    _yaml = None


def _seq_filename_for(name):
    """根据脚本名称生成安全的文件名（不含扩展名）。"""
    safe = re.sub(r'[^\w\-.]', '_', name or "sequence").strip('_')
    if not safe:
        safe = "sequence"
    return safe


def _load_all_sequences():
    """扫描序列目录，返回 [(filepath, script_dict), ...]，按名称排序。"""
    if _yaml is None:
        return []
    result = []
    seq_dir = _i2c_sequence_dir()
    if not os.path.isdir(seq_dir):
        return result
    for fn in os.listdir(seq_dir):
        if not (fn.endswith(".yaml") or fn.endswith(".yml")):
            continue
        path = os.path.join(seq_dir, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = _yaml.safe_load(f)
            if isinstance(data, dict):
                data.setdefault("name", "")
                data.setdefault("description", "")
                cmds = data.get("commands", []) or []
                data["commands"] = [str(c) for c in cmds]
                result.append((path, data))
        except Exception as e:
            logger.error("Load sequence %s failed: %s", fn, e, exc_info=True)
    result.sort(key=lambda x: str(x[1].get("name", x[0])))
    return result


def _save_sequence_file(script_dict):
    """将脚本 dict 写入 YAML 文件，返回文件路径。"""
    if _yaml is None:
        return None
    name = script_dict.get("name", "sequence")
    seq_dir = _i2c_sequence_dir()
    os.makedirs(seq_dir, exist_ok=True)
    filename = _seq_filename_for(name) + ".yaml"
    path = os.path.join(seq_dir, filename)
    out = {
        "name": str(script_dict.get("name", "")),
        "description": str(script_dict.get("description", "")),
        "commands": [str(c) for c in script_dict.get("commands", [])],
    }
    with open(path, "w", encoding="utf-8") as f:
        _yaml.dump(out, f, allow_unicode=True, default_flow_style=False,
                   sort_keys=False)
    return path


def _delete_sequence_file(path):
    try:
        if path and os.path.isfile(path):
            os.remove(path)
    except Exception as e:
        logger.error("Delete sequence %s failed: %s", path, e, exc_info=True)


def _serialize_script_yaml(script_dict):
    """脚本 dict → YAML 字符串。"""
    if _yaml is None:
        return ""
    out = {
        "name": str(script_dict.get("name", "")),
        "description": str(script_dict.get("description", "")),
        "commands": [str(c) for c in script_dict.get("commands", [])],
    }
    return _yaml.dump(out, allow_unicode=True, default_flow_style=False,
                      sort_keys=False)


def _parse_script_yaml(text):
    """YAML 字符串 → 脚本 dict，失败抛异常。"""
    if _yaml is None:
        raise RuntimeError("PyYAML 未安装")
    data = _yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("YAML 顶层必须为字典")
    data.setdefault("name", "")
    data.setdefault("description", "")
    cmds = data.get("commands", []) or []
    data["commands"] = [str(c) for c in cmds]
    return data


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
        self._i2c_script_thread = None
        self._i2c_script_worker = None
        self._i2c_custom_dll = None

        # 序列脚本管理器状态
        self._i2c_sequences = []          # [(filepath, script_dict), ...]
        self._i2c_seq_current_index = None  # 当前选中的列表项索引
        self._i2c_seq_suppress_sync = False  # 防止表/YAML 互相同步时递归

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
        self._build_i2c_script_card(root)
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
        # I2C 设备地址固定为 7-bit（2 位十六进制）
        self.i2c_dev_edit = HexLineEdit(7)
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

    # ---- 脚本管理器卡片（Payload Data Bits 下方） ----

    def _build_i2c_script_card(self, layout):
        card = QFrame()
        card.setObjectName("card")
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)

        t = QLabel("Sequence Script Manager")
        t.setObjectName("cardTitle")
        v.addWidget(t)

        hint = QLabel(
            "寄存器操作序列脚本管理 · 双击列表项执行 · 支持 GUI 表格 / YAML 双模式编辑 · "
            "指令: WRITE/READ/WRITE_BITS/DELAY/READ_RANGE/LOOP/END_LOOP/IF/END_IF · "
            "变量: READ 0x40 TO $status · 条件: IF $status & 0x01")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        v.addWidget(hint)

        # 主区域：左列表 + 右编辑器
        main_row = QHBoxLayout()
        main_row.setSpacing(8)

        # ---- 左侧：脚本列表 ----
        left = QVBoxLayout()
        left.setSpacing(6)
        list_title = QLabel("Scripts")
        list_title.setObjectName("sectionTitle")
        left.addWidget(list_title)
        list_btn_row = QHBoxLayout()
        list_btn_row.setSpacing(4)
        self.i2c_seq_new_btn = QPushButton("New")
        self.i2c_seq_dup_btn = QPushButton("Dup")
        self.i2c_seq_del_btn = QPushButton("Del")
        for btn in (self.i2c_seq_new_btn, self.i2c_seq_dup_btn,
                    self.i2c_seq_del_btn):
            btn.setFixedHeight(I2C_BTN_HEIGHT)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_i2c_subtle_btn_style())
            list_btn_row.addWidget(btn)
        left.addLayout(list_btn_row)
        self.i2c_seq_list = QTableWidget(0, 2)
        self.i2c_seq_list.setHorizontalHeaderLabels(["Name", "Cmds"])
        self.i2c_seq_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.i2c_seq_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.i2c_seq_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.i2c_seq_list.verticalHeader().setVisible(False)
        self.i2c_seq_list.setStyleSheet(_i2c_table_qss())
        lh = self.i2c_seq_list.horizontalHeader()
        lh.setSectionResizeMode(0, QHeaderView.Stretch)
        lh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.i2c_seq_list.setMinimumWidth(200)
        left.addWidget(self.i2c_seq_list, 1)
        main_row.addLayout(left, 0)

        # ---- 右侧：编辑器（Tab: GUI 表格 / YAML） ----
        right = QVBoxLayout()
        right.setSpacing(6)

        # 名称 / 描述行
        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)
        name_lbl = QLabel("Name")
        name_lbl.setObjectName("muted")
        name_lbl.setFixedWidth(50)
        meta_row.addWidget(name_lbl)
        self.i2c_seq_name_edit = QLineEdit()
        self.i2c_seq_name_edit.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_seq_name_edit.setStyleSheet(_i2c_input_style())
        self.i2c_seq_name_edit.setPlaceholderText("脚本名称")
        meta_row.addWidget(self.i2c_seq_name_edit, 1)
        desc_lbl = QLabel("Desc")
        desc_lbl.setObjectName("muted")
        desc_lbl.setFixedWidth(40)
        meta_row.addWidget(desc_lbl)
        self.i2c_seq_desc_edit = QLineEdit()
        self.i2c_seq_desc_edit.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_seq_desc_edit.setStyleSheet(_i2c_input_style())
        self.i2c_seq_desc_edit.setPlaceholderText("描述（可选）")
        meta_row.addWidget(self.i2c_seq_desc_edit, 1)
        right.addLayout(meta_row)

        # Tab 切换
        self.i2c_seq_tabs = QStackedWidget()
        # -- 表格编辑器 --
        table_page = QWidget()
        table_page.setStyleSheet("background:transparent;")
        tv = QVBoxLayout(table_page)
        tv.setContentsMargins(0, 0, 0, 0)
        tv.setSpacing(4)
        # 单列可编辑命令表（支持 WRITE/READ/WRITE_BITS/DELAY/READ_RANGE/LOOP/END_LOOP/IF/END_IF）
        self.i2c_seq_cmd_table = QTableWidget(0, 2)
        self.i2c_seq_cmd_table.setHorizontalHeaderLabels(["#", "Command"])
        self.i2c_seq_cmd_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.i2c_seq_cmd_table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.AnyKeyPressed)
        self.i2c_seq_cmd_table.verticalHeader().setVisible(False)
        self.i2c_seq_cmd_table.setStyleSheet(_i2c_table_qss())
        ch = self.i2c_seq_cmd_table.horizontalHeader()
        ch.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        ch.setSectionResizeMode(1, QHeaderView.Stretch)
        tv.addWidget(self.i2c_seq_cmd_table, 1)
        cmd_btn_row = QHBoxLayout()
        cmd_btn_row.setSpacing(4)
        self.i2c_seq_add_cmd_btn = QPushButton("+ Cmd")
        self.i2c_seq_del_cmd_btn = QPushButton("- Cmd")
        for btn in (self.i2c_seq_add_cmd_btn, self.i2c_seq_del_cmd_btn):
            btn.setFixedHeight(I2C_BTN_HEIGHT)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_i2c_subtle_btn_style())
            cmd_btn_row.addWidget(btn)
        cmd_btn_row.addStretch()
        tv.addLayout(cmd_btn_row)
        self.i2c_seq_tabs.addWidget(table_page)
        # -- YAML 编辑器 --
        yaml_page = QWidget()
        yaml_page.setStyleSheet("background:transparent;")
        yv = QVBoxLayout(yaml_page)
        yv.setContentsMargins(0, 0, 0, 0)
        self.i2c_seq_yaml_edit = QPlainTextEdit()
        self.i2c_seq_yaml_edit.setObjectName("i2cSeqYamlEdit")
        self.i2c_seq_yaml_edit.setStyleSheet(
            "QPlainTextEdit#i2cSeqYamlEdit {"
            f" background-color:{SLATE_950}; border:1px solid {SLATE_800};"
            " border-radius:6px; color:#e2e8f0;"
            " font-family:Consolas,'Cascadia Mono',monospace;"
            " font-size:12px; padding:6px;"
            " selection-background-color:#4f46e5;"
            "}"
            f" QPlainTextEdit#i2cSeqYamlEdit:focus"
            f" {{ border:1px solid {INDIGO}; }}"
        )
        yv.addWidget(self.i2c_seq_yaml_edit)
        self.i2c_seq_tabs.addWidget(yaml_page)
        right.addWidget(self.i2c_seq_tabs, 1)

        # 模式切换按钮 + 执行按钮
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)
        self.i2c_seq_mode_btn = QPushButton("YAML")
        self.i2c_seq_mode_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_seq_mode_btn.setCursor(Qt.PointingHandCursor)
        self.i2c_seq_mode_btn.setStyleSheet(_i2c_subtle_btn_style())
        bottom_row.addWidget(self.i2c_seq_mode_btn)
        bottom_row.addStretch()
        self.i2c_seq_save_btn = QPushButton("Save")
        self.i2c_seq_save_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_seq_save_btn.setCursor(Qt.PointingHandCursor)
        self.i2c_seq_save_btn.setStyleSheet(_i2c_subtle_btn_style())
        bottom_row.addWidget(self.i2c_seq_save_btn)
        self.i2c_seq_stop_btn = QPushButton("Stop")
        self.i2c_seq_stop_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_seq_stop_btn.setCursor(Qt.PointingHandCursor)
        self.i2c_seq_stop_btn.setStyleSheet(_i2c_subtle_btn_style())
        self.i2c_seq_stop_btn.setEnabled(False)
        bottom_row.addWidget(self.i2c_seq_stop_btn)
        self.i2c_seq_run_btn = QPushButton("Run")
        self.i2c_seq_run_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_seq_run_btn.setCursor(Qt.PointingHandCursor)
        self.i2c_seq_run_btn.setStyleSheet(_i2c_write_btn_style())
        bottom_row.addWidget(self.i2c_seq_run_btn)
        right.addLayout(bottom_row)

        main_row.addLayout(right, 1)
        v.addLayout(main_row)

        # 加载已存脚本
        self._i2c_seq_reload_list()
        layout.addWidget(card)

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
        self.i2c_seq_new_btn.clicked.connect(self._on_i2c_seq_new)
        self.i2c_seq_dup_btn.clicked.connect(self._on_i2c_seq_duplicate)
        self.i2c_seq_del_btn.clicked.connect(self._on_i2c_seq_delete)
        self.i2c_seq_list.itemSelectionChanged.connect(
            self._on_i2c_seq_list_selected)
        self.i2c_seq_list.doubleClicked.connect(
            self._on_i2c_seq_list_double_clicked)
        self.i2c_seq_add_cmd_btn.clicked.connect(self._on_i2c_seq_add_cmd)
        self.i2c_seq_del_cmd_btn.clicked.connect(self._on_i2c_seq_del_cmd)
        self.i2c_seq_cmd_table.cellChanged.connect(
            self._on_i2c_seq_cmd_cell_changed)
        self.i2c_seq_mode_btn.clicked.connect(self._on_i2c_seq_toggle_mode)
        self.i2c_seq_save_btn.clicked.connect(self._on_i2c_seq_save)
        self.i2c_seq_run_btn.clicked.connect(self._on_i2c_seq_run)
        self.i2c_seq_stop_btn.clicked.connect(self._on_i2c_seq_stop)

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
                     "i2c_readall_btn", "i2c_seq_run_btn"):
            w = getattr(self, attr, None)
            if w is not None:
                w.setEnabled(not busy)
        # Stop 按钮只在序列执行中可用
        stop_btn = getattr(self, "i2c_seq_stop_btn", None)
        if stop_btn is not None:
            stop_btn.setEnabled(busy and self._i2c_script_thread is not None)

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
        # Device Addr 固定 7-bit，不随位宽切换
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

    # ---- 序列脚本管理器（列表 + GUI 表格 / YAML 双模式编辑 + 执行） ----

    def _i2c_seq_reload_list(self):
        """重新扫描序列目录并刷新左侧列表。"""
        self._i2c_sequences = _load_all_sequences()
        self.i2c_seq_list.setRowCount(0)
        for _path, script in self._i2c_sequences:
            row = self.i2c_seq_list.rowCount()
            self.i2c_seq_list.insertRow(row)
            name_item = QTableWidgetItem(str(script.get("name", "")))
            cmds = script.get("commands", []) or []
            cnt_item = QTableWidgetItem(str(len(cmds)))
            cnt_item.setTextAlignment(Qt.AlignCenter)
            self.i2c_seq_list.setItem(row, 0, name_item)
            self.i2c_seq_list.setItem(row, 1, cnt_item)
        self._i2c_seq_current_index = None
        self._i2c_seq_clear_editor()

    def _i2c_seq_clear_editor(self):
        self._i2c_seq_suppress_sync = True
        self.i2c_seq_name_edit.setText("")
        self.i2c_seq_desc_edit.setText("")
        self.i2c_seq_cmd_table.setRowCount(0)
        self.i2c_seq_yaml_edit.setPlainText("")
        self._i2c_seq_suppress_sync = False

    def _on_i2c_seq_list_selected(self):
        """列表选中 → 加载到右侧编辑器。"""
        rows = self.i2c_seq_list.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if row < 0 or row >= len(self._i2c_sequences):
            return
        self._i2c_seq_current_index = row
        _path, script = self._i2c_sequences[row]
        self._i2c_seq_load_to_editor(script)

    def _on_i2c_seq_list_double_clicked(self, _index):
        """双击列表项 → 直接执行该脚本。"""
        rows = self.i2c_seq_list.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if row < 0 or row >= len(self._i2c_sequences):
            return
        _path, script = self._i2c_sequences[row]
        self._i2c_seq_execute(script)

    def _i2c_seq_load_to_editor(self, script):
        """将脚本 dict 载入右侧编辑器（表格 + YAML 同步）。"""
        self._i2c_seq_suppress_sync = True
        self.i2c_seq_name_edit.setText(str(script.get("name", "")))
        self.i2c_seq_desc_edit.setText(str(script.get("description", "")))
        # 表格：每行是一条 DSL 指令字符串
        cmds = script.get("commands", []) or []
        self.i2c_seq_cmd_table.setRowCount(0)
        for cmd_line in cmds:
            self._i2c_seq_append_cmd_row(str(cmd_line))
        self._i2c_seq_renumber_rows()
        # YAML
        self.i2c_seq_yaml_edit.setPlainText(_serialize_script_yaml(script))
        self._i2c_seq_suppress_sync = False

    def _i2c_seq_append_cmd_row(self, cmd_line=""):
        """在命令表格末尾追加一行（cmd_line 为 DSL 文本）。"""
        row = self.i2c_seq_cmd_table.rowCount()
        self.i2c_seq_cmd_table.insertRow(row)
        idx_item = QTableWidgetItem(str(row + 1))
        idx_item.setTextAlignment(Qt.AlignCenter)
        idx_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        cmd_item = QTableWidgetItem(str(cmd_line))
        self.i2c_seq_cmd_table.setItem(row, 0, idx_item)
        self.i2c_seq_cmd_table.setItem(row, 1, cmd_item)

    def _i2c_seq_renumber_rows(self):
        """重新编号 # 列。"""
        for row in range(self.i2c_seq_cmd_table.rowCount()):
            item = self.i2c_seq_cmd_table.item(row, 0)
            if item is not None:
                item.setText(str(row + 1))

    def _i2c_seq_collect_from_table(self):
        """从右侧 Name/Desc/表格收集出脚本 dict（commands 为字符串列表）。"""
        commands = []
        for row in range(self.i2c_seq_cmd_table.rowCount()):
            item = self.i2c_seq_cmd_table.item(row, 1)
            if item is None:
                continue
            text = item.text().strip()
            if text:
                commands.append(text)
        return {
            "name": self.i2c_seq_name_edit.text().strip(),
            "description": self.i2c_seq_desc_edit.text().strip(),
            "commands": commands,
        }

    def _on_i2c_seq_cmd_cell_changed(self, _row, _col):
        """表格编辑 → 同步到 YAML（当前处于表格模式时）。"""
        if self._i2c_seq_suppress_sync:
            return
        if self.i2c_seq_tabs.currentIndex() != 0:
            return
        script = self._i2c_seq_collect_from_table()
        self._i2c_seq_suppress_sync = True
        self.i2c_seq_yaml_edit.setPlainText(_serialize_script_yaml(script))
        self._i2c_seq_suppress_sync = False

    def _on_i2c_seq_toggle_mode(self):
        """切换 表格 ↔ YAML 模式。"""
        if self.i2c_seq_tabs.currentIndex() == 0:
            # 表格 → YAML：先把表格内容同步到 YAML
            script = self._i2c_seq_collect_from_table()
            self._i2c_seq_suppress_sync = True
            self.i2c_seq_yaml_edit.setPlainText(_serialize_script_yaml(script))
            self._i2c_seq_suppress_sync = False
            self.i2c_seq_tabs.setCurrentIndex(1)
            self.i2c_seq_mode_btn.setText("Table")
        else:
            # YAML → 表格：先尝试解析 YAML 并回填表格
            try:
                script = _parse_script_yaml(self.i2c_seq_yaml_edit.toPlainText())
            except Exception as e:
                QMessageBox.warning(self, "YAML 解析失败", str(e))
                return
            self._i2c_seq_suppress_sync = True
            self.i2c_seq_name_edit.setText(str(script.get("name", "")))
            self.i2c_seq_desc_edit.setText(str(script.get("description", "")))
            self.i2c_seq_cmd_table.setRowCount(0)
            for cmd_line in script.get("commands", []) or []:
                self._i2c_seq_append_cmd_row(str(cmd_line))
            self._i2c_seq_renumber_rows()
            self._i2c_seq_suppress_sync = False
            self.i2c_seq_tabs.setCurrentIndex(0)
            self.i2c_seq_mode_btn.setText("YAML")

    def _on_i2c_seq_new(self):
        """新建空脚本。"""
        self.i2c_seq_list.clearSelection()
        self._i2c_seq_current_index = None
        self._i2c_seq_clear_editor()
        self.i2c_seq_name_edit.setText("NewSequence")
        self.i2c_seq_name_edit.setFocus()
        self.i2c_seq_name_edit.selectAll()
        self.append_log("[I2C] 新建序列脚本（未保存）")

    def _on_i2c_seq_duplicate(self):
        """复制当前选中脚本。"""
        if self._i2c_seq_current_index is None:
            QMessageBox.information(self, "提示", "请先在列表中选择一个脚本")
            return
        _path, script = self._i2c_sequences[self._i2c_seq_current_index]
        new_script = copy.deepcopy(script)
        new_script["name"] = str(script.get("name", "")) + "_copy"
        self.i2c_seq_list.clearSelection()
        self._i2c_seq_current_index = None
        self._i2c_seq_load_to_editor(new_script)
        self.append_log("[I2C] 已复制脚本，请修改名称后保存")

    def _on_i2c_seq_delete(self):
        """删除当前选中脚本文件。"""
        if self._i2c_seq_current_index is None:
            QMessageBox.information(self, "提示", "请先在列表中选择一个脚本")
            return
        path, script = self._i2c_sequences[self._i2c_seq_current_index]
        name = script.get("name", "")
        ret = QMessageBox.question(
            self, "删除确认", "确定删除脚本 '{0}'?".format(name))
        if ret != QMessageBox.Yes:
            return
        _delete_sequence_file(path)
        self.append_log(f"[I2C] 已删除脚本: {name}")
        self._i2c_seq_reload_list()

    def _on_i2c_seq_add_cmd(self):
        """在表格末尾新增一行指令。"""
        if self.i2c_seq_tabs.currentIndex() != 0:
            QMessageBox.information(self, "提示", "请切换到 Table 模式编辑指令")
            return
        self._i2c_seq_append_cmd_row("WRITE 0x00 0x00")
        self._i2c_seq_renumber_rows()
        # 选中并进入编辑
        new_row = self.i2c_seq_cmd_table.rowCount() - 1
        self.i2c_seq_cmd_table.selectRow(new_row)
        self.i2c_seq_cmd_table.editItem(self.i2c_seq_cmd_table.item(new_row, 1))

    def _on_i2c_seq_del_cmd(self):
        """删除表格中选中的指令行。"""
        if self.i2c_seq_tabs.currentIndex() != 0:
            return
        rows = self.i2c_seq_cmd_table.selectionModel().selectedRows()
        if not rows:
            return
        # 从后往前删，避免索引错位
        for idx in sorted([r.row() for r in rows], reverse=True):
            self.i2c_seq_cmd_table.removeRow(idx)
        self._i2c_seq_renumber_rows()
        # 触发同步
        self._on_i2c_seq_cmd_cell_changed(0, 0)

    def _on_i2c_seq_save(self):
        """保存当前编辑器内容到 YAML 文件。"""
        # 如果当前在 YAML 模式，先尝试解析
        if self.i2c_seq_tabs.currentIndex() == 1:
            try:
                script = _parse_script_yaml(self.i2c_seq_yaml_edit.toPlainText())
            except Exception as e:
                QMessageBox.warning(self, "YAML 解析失败", str(e))
                return
        else:
            script = self._i2c_seq_collect_from_table()
        name = script.get("name", "").strip()
        if not name:
            QMessageBox.warning(self, "名称无效", "请填写脚本名称")
            return
        try:
            path = _save_sequence_file(script)
            self.append_log(f"[I2C] 序列脚本已保存: {path}")
            # 保存后刷新列表并选中新保存的项
            self._i2c_seq_reload_list()
            for i, (_p, s) in enumerate(self._i2c_sequences):
                if s.get("name") == name:
                    self.i2c_seq_list.selectRow(i)
                    break
        except Exception as e:
            logger.error("I2C save sequence failed: %s", e, exc_info=True)
            QMessageBox.critical(self, "保存失败", str(e))

    def _i2c_seq_execute(self, script):
        """执行指定脚本 dict。"""
        if (self._i2c_script_thread is not None
                and self._i2c_script_thread.isRunning()):
            QMessageBox.information(self, "正在执行", "请等待当前序列执行结束")
            return
        # 如果在 YAML 模式，先解析确保最新
        if self.i2c_seq_tabs.currentIndex() == 1:
            try:
                script = _parse_script_yaml(self.i2c_seq_yaml_edit.toPlainText())
            except Exception as e:
                QMessageBox.warning(self, "YAML 解析失败", str(e))
                return
        commands = script.get("commands", []) or []
        if not commands:
            QMessageBox.information(self, "脚本为空", "该脚本没有可执行指令")
            return
        dev = self._i2c_current_dev()
        name = script.get("name", "")
        self._i2c_set_busy(True)
        self._i2c_set_activity("Sequence…", ok=True)
        self.append_log(
            f"[I2C] Sequence '{name}' 开始 dev=0x{dev:02X} "
            f"width={_width_label(self._i2c_width)} 指令数={len(commands)}")
        worker = _I2cSequenceWorker(
            self._i2c_dll_path(), self._i2c_speed_mode, dev,
            self._i2c_width, commands, script_name=name)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_i2c_seq_progress)
        worker.finished.connect(self._on_i2c_seq_finished)
        worker.error.connect(self._on_i2c_seq_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_i2c_seq_thread_cleanup)
        self._i2c_script_worker = worker
        self._i2c_script_thread = thread
        self.i2c_seq_stop_btn.setEnabled(True)
        thread.start()

    def _on_i2c_seq_run(self):
        """Run 按钮：执行当前编辑器中的脚本。"""
        if self.i2c_seq_tabs.currentIndex() == 1:
            try:
                script = _parse_script_yaml(self.i2c_seq_yaml_edit.toPlainText())
            except Exception as e:
                QMessageBox.warning(self, "YAML 解析失败", str(e))
                return
        else:
            script = self._i2c_seq_collect_from_table()
        self._i2c_seq_execute(script)

    def _on_i2c_seq_stop(self):
        worker = getattr(self, "_i2c_script_worker", None)
        if worker is not None:
            worker.request_stop()
            self.append_log("[I2C] 已请求停止序列执行")
        self.i2c_seq_stop_btn.setEnabled(False)

    def _on_i2c_seq_progress(self, text):
        self.append_log(f"[I2C] {text}")

    def _on_i2c_seq_thread_cleanup(self):
        self._i2c_script_thread = None
        self._i2c_script_worker = None

    def _on_i2c_seq_finished(self):
        self._i2c_set_activity("Sequence", ok=True)
        self._i2c_set_result("Sequence Done", ok=True)
        self._i2c_set_busy(False)
        self.append_log("[I2C] 序列执行结束")

    def _on_i2c_seq_error(self, err):
        self._i2c_set_activity("Sequence", ok=False)
        self._i2c_set_result(f"Sequence Failed: {err}", ok=False)
        self._i2c_set_busy(False)
        self.append_log(f"[I2C] 序列执行失败: {err}")

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

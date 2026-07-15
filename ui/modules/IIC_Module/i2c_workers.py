# I2C 异步 Worker（每次操作自建/销毁 I2CInterface）

from PySide6.QtCore import QThread, Signal, QObject

from log_config import get_logger

from ui.modules.IIC_Module.i2c_constants import (
    _fmt_hex, _reg_addr_bits, _data_bits,
)
from ui.modules.IIC_Module.i2c_dsl import (
    _build_ast, _resolve_token,
)

logger = get_logger(__name__)


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
    cmd_read = Signal(str, int)  # (addr_token, value) READ 指令结果

    def __init__(self, dll_path, speed_mode, device_addr, width_flag,
                 commands, script_name="", data_bits=16):
        super().__init__()
        self._dll = dll_path
        self._speed = speed_mode
        self._dev = device_addr
        self._width = width_flag
        self._data_bits = data_bits
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
                    from ui.modules.IIC_Module.i2c_dsl import _eval_condition
                    result = _eval_condition(i2c, self._dev, self._width,
                                             cond, self._vars,
                                             self.progress.emit,
                                             self._data_bits)
                except Exception as e:
                    self.progress.emit("{0}IF 条件求值失败: {1}".format(prefix, e))
                    raise
                if result:
                    self._exec_block(i2c, body, prefix)

    def _exec_cmd(self, i2c, cmd, prefix):
        op = str(cmd.get("type", "")).upper()
        reg_bits = _reg_addr_bits(self._width)
        data_bits = self._data_bits
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
            self.cmd_read.emit(str(cmd.get("addr", "")), int(val))
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

"""Module Config — 测试前模块 I2C 配置的解析 / 执行 / 后台 Worker。

指令文本格式与 Consumption Test 电源轨一致（``WRITE`` / ``WRITE_BITS`` /
``READ``，可带 ``DUT:`` 前缀）。与 consumption_test 不同的是：module_test 的
目标地址 / 位宽直接取 DUT 配置区的 ``device_addr`` / ``width_flag``，无需
``bes_chip_check`` 解析芯片信息，因此执行链路更直接。

分层约束：解析 / 执行为纯函数（无 Qt），``ModuleConfigWorker`` 走 QThread
（仅 QtCore），UI 层通过 Signal/Slot 触发与接收日志，不阻塞主线程。
"""
from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject, Signal

from debug_config import DEBUG_MOCK
from log_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------- 解析
def _to_int(token: str) -> int:
    """宽容解析整数：支持 0x 十六进制、带前导零的十进制（如 01/00）与普通十进制。

    ``int(token, 0)`` 对 ``'01'`` 这类带前导零的字面量会抛 ValueError，
    这里显式分派：``0x`` 前缀走 16 进制，其余按 10 进制（允许前导零）。
    """
    t = (token or "").strip()
    if t.lower().startswith("0x"):
        return int(t, 16)
    return int(t, 10)


def parse_config_commands(text: str) -> list[dict[str, Any]]:
    """把指令文本解析为命令字典列表（忽略空行 / 注释 / 无法识别行）。

    支持：``WRITE reg value``、``WRITE_BITS reg msb lsb value``、``READ reg``；
    行首可带 ``-`` 列表符与 ``DUT:`` 等前缀（前缀仅作标注，目标地址由调用方
    统一给定）；``//`` 之后为注释。
    """
    commands: list[dict[str, Any]] = []
    for raw_line in (text or "").strip().splitlines():
        line = raw_line.strip()
        if line.startswith("-"):
            line = line[1:].strip()
        if line.startswith("'") or line.startswith('"'):
            line = line[1:]
        if line.endswith("'") or line.endswith('"'):
            line = line[:-1]
        line = line.strip()

        comment_idx = line.find("//")
        if comment_idx >= 0:
            line = line[:comment_idx].strip()
        if not line:
            continue

        # 去掉 "DUT:" 等前缀（目标地址统一由 DUT 配置给定，前缀仅标注）
        if ":" in line:
            prefix, rest = line.split(":", 1)
            rest_upper = rest.strip().upper()
            if any(kw in rest_upper for kw in ("WRITE_BITS", "WRITE", "READ")):
                line = rest.strip()

        upper = line.upper()
        if not any(kw in upper for kw in ("WRITE_BITS", "WRITE", "READ")):
            continue

        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            op = parts[0].upper()
            if op == "WRITE_BITS" and len(parts) >= 5:
                commands.append({
                    "op": "WRITE_BITS",
                    "reg_addr": _to_int(parts[1]),
                    "msb": _to_int(parts[2]),
                    "lsb": _to_int(parts[3]),
                    "value": _to_int(parts[4]),
                })
            elif op == "WRITE" and len(parts) >= 3:
                commands.append({
                    "op": "WRITE",
                    "reg_addr": _to_int(parts[1]),
                    "value": _to_int(parts[2]),
                })
            elif op == "READ" and len(parts) >= 2:
                commands.append({
                    "op": "READ",
                    "reg_addr": _to_int(parts[1]),
                })
        except ValueError:
            # 无法解析为数值的行跳过，不中断整体
            logger.warning("Module Config 跳过无法解析的行：%s", line)
            continue
    return commands


# ---------------------------------------------------------------------- 执行
def _create_i2c(is_mock: bool, n6705c: Any):
    """创建 I2C 接口（Mock 复用 n6705c 挂载的 MockI2C，与 _common.create_i2c 一致）。"""
    if is_mock:
        from instruments.mock.mock_instruments import MockI2C
        if getattr(n6705c, "_mock_i2c", None) is not None:
            return n6705c._mock_i2c
        i2c = MockI2C()
        if hasattr(n6705c, "_mock_i2c"):
            n6705c._mock_i2c = i2c
        return i2c
    from lib.i2c.i2c_interface_x64 import I2CInterface
    return I2CInterface()


def run_module_config(*, config_text: str, device_addr: int, width_flag: int,
                      is_mock: bool, n6705c: Any,
                      log_fn: Callable[[str], None]) -> tuple[bool, str]:
    """同步执行一段 Module Config（在调用线程内执行，应由 Worker 调用）。

    返回 ``(ok, message)``；``log_fn`` 逐条回报执行明细（已切回 UI 线程）。
    """
    commands = parse_config_commands(config_text)
    if not commands:
        return False, "Module Config 无可执行指令（为空或全部无法解析）"

    try:
        i2c = _create_i2c(is_mock, n6705c)
    except Exception as exc:  # noqa: BLE001
        logger.error("Module Config 创建 I2C 接口失败", exc_info=True)
        return False, f"I2C 接口初始化失败：{exc}"

    if not is_mock and hasattr(i2c, "initialize"):
        try:
            if not i2c.initialize():
                return False, "I2C 接口初始化失败（initialize 返回 False）"
        except Exception as exc:  # noqa: BLE001
            logger.error("Module Config I2C initialize 异常", exc_info=True)
            return False, f"I2C 接口初始化异常：{exc}"

    log_fn(f"[MODCFG] 开始执行模块配置（{len(commands)} 条，"
           f"dev=0x{device_addr:02X}, width={width_flag}）")
    failed = 0
    for idx, cmd in enumerate(commands):
        op = cmd["op"]
        reg = cmd["reg_addr"]
        try:
            if op == "WRITE_BITS":
                msb, lsb, value = cmd["msb"], cmd["lsb"], cmd["value"]
                cur = i2c.read(device_addr, reg, width_flag)
                mask = ((1 << (msb - lsb + 1)) - 1) << lsb
                new = (cur & ~mask) | ((value << lsb) & mask)
                i2c.write(device_addr, reg, new, width_flag)
                log_fn(f"[MODCFG] #{idx + 1} WRITE_BITS reg=0x{reg:X} "
                       f"[{msb}:{lsb}]=0x{value:X} (0x{cur:X}->0x{new:X})")
            elif op == "WRITE":
                i2c.write(device_addr, reg, cmd["value"], width_flag)
                log_fn(f"[MODCFG] #{idx + 1} WRITE reg=0x{reg:X} "
                       f"data=0x{cmd['value']:X}")
            elif op == "READ":
                val = i2c.read(device_addr, reg, width_flag)
                log_fn(f"[MODCFG] #{idx + 1} READ reg=0x{reg:X} => 0x{val:X}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            logger.error("Module Config 第 %d 条执行失败", idx + 1, exc_info=True)
            log_fn(f"[MODCFG] [ERROR] 第 {idx + 1} 条（{op} reg=0x{reg:X}）失败：{exc}")

    if failed:
        return False, f"模块配置完成，但 {failed}/{len(commands)} 条失败"
    return True, f"模块配置执行完成（{len(commands)} 条全部成功）"


# ---------------------------------------------------------------------- Worker
class ModuleConfigWorker(QObject):
    """QThread Worker：后台执行 Module Config，日志经 Signal 回 UI 线程。"""

    log = Signal(str)
    finished = Signal(bool, str)  # ok, message

    def __init__(self, *, config_text: str, device_addr: int, width_flag: int,
                 is_mock: bool, n6705c: Any, parent: QObject | None = None):
        super().__init__(parent)
        self._config_text = config_text
        self._device_addr = device_addr
        self._width_flag = width_flag
        self._is_mock = is_mock
        self._n6705c = n6705c

    def run(self) -> None:
        ok, msg = run_module_config(
            config_text=self._config_text,
            device_addr=self._device_addr,
            width_flag=self._width_flag,
            is_mock=self._is_mock,
            n6705c=self._n6705c,
            log_fn=self.log.emit,
        )
        self.finished.emit(ok, msg)

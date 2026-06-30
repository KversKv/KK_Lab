import os
import sys
import time

import pyvisa

if __name__ == "__main__" and __package__ is None:
    _PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from log_config import get_logger

logger = get_logger(__name__)


class CMWBase:
    """罗德与施瓦茨 CMW 系列无线综测仪通用基类。

    CMW270 / CMW500 共享同一套 SCPI 指令集（同平台固件），仅射频硬件 / 选件
    支持范围不同。本基类封装 VISA 通信、IEEE 488.2 公共指令、系统/RF 通用配置，
    各无线制式（BT / BLE / LTE / WIFI）的指令通过 Mixin 组合到具体型号类中。

    默认连接地址: TCPIP0::10.31.31.236::hislip0::INSTR
    """

    DEFAULT_RESOURCE = "TCPIP0::10.31.31.236::hislip0::INSTR"
    MODEL = "CMW"

    def __init__(self, resource=None, visa_library=None, timeout_ms=10000):
        resource = resource or self.DEFAULT_RESOURCE
        logger.debug("%s __init__: resource=%s", self.MODEL, resource)
        try:
            if visa_library:
                self.rm = pyvisa.ResourceManager(visa_library)
            else:
                self.rm = pyvisa.ResourceManager()
        except (OSError, ValueError) as e:
            logger.warning(
                "%s: 系统 VISA 不可用(%s)，回退到 pyvisa-py('@py')", self.MODEL, e
            )
            self.rm = pyvisa.ResourceManager('@py')
        logger.debug("%s visalib=%s", self.MODEL, self.rm.visalib)
        resource_str = str(resource).strip()
        upper = resource_str.upper()
        visa_prefixes = ("TCPIP", "USB", "GPIB", "ASRL", "VXI", "PXI", "HISLIP")
        is_visa_resource = (
            "::" in resource_str
            and (upper.endswith("::INSTR") or upper.endswith("::SOCKET")
                 or upper.startswith(visa_prefixes))
        )
        if is_visa_resource:
            self.instr = self.rm.open_resource(resource_str)
        else:
            self.instr = self.rm.open_resource(f'TCPIP0::{resource_str}::hislip0::INSTR')
        self.instr.timeout = int(timeout_ms)
        self.instr.encoding = 'utf-8'
        logger.debug("%s connected, timeout=%d ms", self.MODEL, self.instr.timeout)

    # =========================
    # 基础 IO
    # =========================

    def _ensure_connected(self):
        if self.instr is None:
            raise RuntimeError(f"{self.MODEL}: instrument not connected")

    def write(self, cmd):
        self._ensure_connected()
        logger.debug("%s WRITE: %s", self.MODEL, cmd)
        self.instr.write(cmd)

    def query(self, cmd):
        self._ensure_connected()
        logger.debug("%s QUERY: %s", self.MODEL, cmd)
        resp = self.instr.query(cmd)
        logger.debug("%s RESP : %s", self.MODEL,
                     resp.strip() if isinstance(resp, str) else resp)
        return resp

    def query_float(self, cmd):
        raw = self.query(cmd).strip()
        try:
            return float(raw)
        except ValueError as e:
            raise ValueError(f"无法将返回值解析为浮点数: {raw!r}") from e

    def query_int(self, cmd):
        return int(float(self.query(cmd).strip()))

    def query_values(self, cmd):
        """查询逗号分隔的返回值，按 float 列表返回（不可解析项保留为原字符串）。"""
        raw = self.query(cmd).strip()
        out = []
        for item in raw.split(','):
            item = item.strip()
            try:
                out.append(float(item))
            except ValueError:
                out.append(item)
        return out

    # =========================
    # IEEE 488.2 公共指令
    # =========================

    def identify(self):
        return self.query("*IDN?").strip()

    def reset(self):
        self.write("*RST")
        self.query_opc(timeout_s=30.0)

    def clear_status(self):
        self.write("*CLS")

    def self_test(self):
        return self.query("*TST?").strip()

    def wait(self):
        self.write("*WAI")

    def operation_complete(self):
        self.write("*OPC")

    def query_opc(self, timeout_s=10.0):
        old_timeout = self.instr.timeout
        try:
            self.instr.timeout = int(timeout_s * 1000)
            resp = self.query("*OPC?").strip()
            return resp.startswith("1")
        finally:
            self.instr.timeout = old_timeout

    def get_errors(self, max_count=50):
        """读取系统错误队列，返回错误字符串列表。"""
        errors = []
        for _ in range(max_count):
            err = self.query("SYSTem:ERRor?").strip()
            errors.append(err)
            if err.startswith("0,") or err.startswith("+0,") or "No error" in err:
                break
        return errors

    def get_options(self):
        """返回已安装选件列表。"""
        raw = self.query("*OPT?").strip()
        return [opt.strip() for opt in raw.split(',') if opt.strip()]

    # =========================
    # 系统 / 通用配置
    # =========================

    def set_remote(self):
        self.write("&GTR")

    def go_to_local(self):
        self.write("&GTL")

    def get_firmware_version(self):
        """获取基础固件版本。

        不同 CMW 固件对版本查询支持不一: 优先尝试 SYSTem:BASE:VERSion?,
        失败 (不识别 / 超时) 则回退到 *IDN? 的版本字段, 保证不中断流程。
        """
        try:
            return self.query("SYSTem:BASE:VERSion?").strip()
        except Exception:
            logger.warning(
                "%s SYSTem:BASE:VERSion? 不可用, 回退 *IDN? 版本字段",
                self.MODEL,
                exc_info=True,
            )
            self.clear_status()
            idn = self.identify()
            # *IDN? 格式: <厂商>,<型号>,<序列号>,<版本>
            parts = [p.strip() for p in idn.split(',')]
            return parts[-1] if len(parts) >= 4 else idn

    def set_timeout(self, timeout_ms):
        self._ensure_connected()
        self.instr.timeout = int(timeout_ms)
        logger.debug("%s timeout set to %d ms", self.MODEL, self.instr.timeout)

    # =========================
    # 通用测量控制 (适用于各信令/非信令应用)
    # =========================

    @staticmethod
    def _app_prefix(application):
        """将应用名映射为 SCPI 子系统根，例如 'gprfMeas' / 'bluetoothMeas'。"""
        return application

    def init_measurement(self, application):
        """启动指定测量应用 (INITiate)。"""
        self.write(f"INITiate:{application}")

    def stop_measurement(self, application):
        self.write(f"STOP:{application}")

    def abort_measurement(self, application):
        self.write(f"ABORt:{application}")

    def fetch(self, application_path):
        """通用 FETCh，返回逗号分隔结果列表。"""
        return self.query_values(f"FETCh:{application_path}?")

    def read(self, application_path):
        """通用 READ，返回逗号分隔结果列表。"""
        return self.query_values(f"READ:{application_path}?")

    def get_measurement_state(self, application):
        """返回测量状态: OFF / RUN / RDY 等。"""
        return self.query(f"FETCh:{application}:STATe?").strip()

    def wait_for_ready(self, application, timeout_s=30.0, poll_s=0.5):
        """轮询等待测量进入 RDY 状态。"""
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            state = self.get_measurement_state(application)
            if state.upper().startswith("RDY"):
                return True
            time.sleep(poll_s)
        logger.warning("%s wait_for_ready timeout: %s", self.MODEL, application)
        return False

    # =========================
    # 连接管理
    # =========================

    def disconnect(self):
        logger.debug("%s disconnect called", self.MODEL)
        if getattr(self, "instr", None) is not None:
            try:
                self.instr.close()
            except Exception:
                logger.warning("%s 关闭 instr 失败", self.MODEL, exc_info=True)
            self.instr = None
        if getattr(self, "rm", None) is not None:
            try:
                self.rm.close()
            except Exception:
                logger.warning("%s 关闭 rm 失败", self.MODEL, exc_info=True)
            self.rm = None

    def is_connected(self):
        return getattr(self, "instr", None) is not None

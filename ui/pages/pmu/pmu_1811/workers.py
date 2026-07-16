# -*- coding: utf-8 -*-
"""1811 PMU 驱动中间层: 异步 I2C Worker (每次操作自建/销毁控制器)。

遵循 ui/modules/IIC_Module/i2c_workers.py 的模式:
每个 Worker 在 QThread 内创建独立的 I2CInterface, 避免跨线程共享。
"""

from PySide6.QtCore import QThread, Signal, QObject

from log_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 读取全部 LDO 状态
# ---------------------------------------------------------------------------
class LdoReadAllWorker(QObject):
    finished = Signal(dict)   # {ldo_id: LdoState}
    error = Signal(str)
    log = Signal(str)         # (level, message) 已格式化为 "[LEVEL] msg"

    def __init__(self, dll_path=None, speed_mode=None):
        super().__init__()
        self._dll = dll_path
        self._speed = speed_mode

    def _make_log_cb(self):
        def _cb(level: str, msg: str):
            self.log.emit(f"[{level}] {msg}")
        return _cb

    def run(self):
        from core.bes1811_pmu_controller import Bes1811PmuController
        ctrl = Bes1811PmuController(
            dll_path=self._dll, speed_mode=self._speed,
            log_callback=self._make_log_cb(),
        )
        try:
            if not ctrl.connect():
                self.error.emit("I2C 接口初始化失败 (DLL 加载或设备打开失败)")
                return
            # 同时读取全部 LDO + BUCK 状态, 合并返回 {id: LdoState|BuckState}
            states = ctrl.read_all_modules()
            self.finished.emit(states)
        except Exception as e:
            logger.error("1811 PMU 读取失败: %s", e, exc_info=True)
            self.error.emit(str(e))
        finally:
            ctrl.disconnect()


# ---------------------------------------------------------------------------
# 读取单个 LDO 状态
# ---------------------------------------------------------------------------
class LdoReadOneWorker(QObject):
    finished = Signal(object)  # LdoState
    error = Signal(str)
    log = Signal(str)

    def __init__(self, ldo_id, dll_path=None, speed_mode=None):
        super().__init__()
        self._ldo_id = ldo_id
        self._dll = dll_path
        self._speed = speed_mode

    def _make_log_cb(self):
        def _cb(level: str, msg: str):
            self.log.emit(f"[{level}] {msg}")
        return _cb

    def run(self):
        from core.bes1811_pmu_controller import Bes1811PmuController
        from chips.bes1811_pmu import is_buck
        ctrl = Bes1811PmuController(
            dll_path=self._dll, speed_mode=self._speed,
            log_callback=self._make_log_cb(),
        )
        try:
            if not ctrl.connect():
                self.error.emit("I2C 接口初始化失败")
                return
            # 按 ID 类型派发: BUCK 走 read_buck, LDO 走 read_ldo
            if is_buck(self._ldo_id):
                st = ctrl.read_buck(self._ldo_id)
            else:
                st = ctrl.read_ldo(self._ldo_id)
            self.finished.emit(st)
        except Exception as e:
            logger.error("1811 PMU 读取 %s 失败: %s", self._ldo_id, e, exc_info=True)
            self.error.emit(str(e))
        finally:
            ctrl.disconnect()


# ---------------------------------------------------------------------------
# 写入 LDO 配置 (使能/模式/电压)
# ---------------------------------------------------------------------------
class LdoWriteWorker(QObject):
    finished = Signal(str)    # ldo_id
    error = Signal(str)
    log = Signal(str)

    def __init__(self, ldo_id, action, value, dll_path=None, speed_mode=None):
        """
        Args:
            action: "enable" / "mode" / "voltage"
            value:  bool / str / float
        """
        super().__init__()
        self._ldo_id = ldo_id
        self._action = action
        self._value = value
        self._dll = dll_path
        self._speed = speed_mode

    def _make_log_cb(self):
        def _cb(level: str, msg: str):
            self.log.emit(f"[{level}] {msg}")
        return _cb

    def run(self):
        from core.bes1811_pmu_controller import Bes1811PmuController
        from chips.bes1811_pmu import is_buck
        ctrl = Bes1811PmuController(
            dll_path=self._dll, speed_mode=self._speed,
            log_callback=self._make_log_cb(),
        )
        try:
            if not ctrl.connect():
                self.error.emit("I2C 接口初始化失败")
                return
            # 按 ID 类型派发: BUCK 走 set_buck_*, LDO 走 set_ldo_*
            if is_buck(self._ldo_id):
                if self._action == "enable":
                    ctrl.set_buck_enabled(self._ldo_id, bool(self._value))
                elif self._action == "voltage":
                    ctrl.set_buck_voltage(self._ldo_id, float(self._value))
                elif self._action == "mode":
                    # BUCK 模式控制 (Normal/LP/ULP) 后续补全, 当前忽略
                    logger.warning("1811 PMU: BUCK 模式切换尚未实现, 忽略 %s/mode",
                                   self._ldo_id)
                else:
                    raise ValueError(f"未知操作: {self._action}")
            else:
                if self._action == "enable":
                    ctrl.set_ldo_enabled(self._ldo_id, bool(self._value))
                elif self._action == "mode":
                    ctrl.set_ldo_mode(self._ldo_id, str(self._value))
                elif self._action == "voltage":
                    ctrl.set_ldo_voltage(self._ldo_id, float(self._value))
                else:
                    raise ValueError(f"未知操作: {self._action}")
            self.finished.emit(self._ldo_id)
        except Exception as e:
            logger.error("1811 PMU 写入 %s/%s 失败: %s",
                         self._ldo_id, self._action, e, exc_info=True)
            self.error.emit(str(e))
        finally:
            ctrl.disconnect()

# -*- coding: utf-8 -*-
"""BES1811 PMU 控制器: 通过 I2C 对 1811 PMU 的 LDO 进行归一化控制。

本模块为纯 Python 业务逻辑, 无 Qt 依赖。
上层 (UI Worker) 负责 connect/disconnect 生命周期与线程管理。
"""

from dataclasses import dataclass
from typing import Optional

from log_config import get_logger

from chips.bes1811_pmu import (
    BitField, LdoRegMap,
    LDO_REG_MAPS, LDO_IDS,
    I2C_DEVICE_ADDR, I2C_WIDTH,
    vbit_to_voltage, voltage_to_vbit, get_voltage_range, get_reg_map,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# LDO 状态快照
# ---------------------------------------------------------------------------
@dataclass
class LdoState:
    """读取到的 LDO 实时状态。"""
    ldo_id: str
    enabled: bool               # pu 位 (驱动位=1 时有效)
    pu_dr: int                  # pu 驱动位
    mode: str                   # "Normal" / "LP" / "Unknown"
    lp_dr: int                  # lp 驱动位
    vbit_normal: int            # 唤醒电压控制字
    vbit_dsleep: int            # 睡眠电压控制字
    vbit_rc: int                # RC 电压控制字
    res_sel_dr: int             # 电压调整生效位
    voltage: Optional[float]    # 当前唤醒模式电压 (V), 由 vbit_normal 查表得到


# ---------------------------------------------------------------------------
# 控制器
# ---------------------------------------------------------------------------
class Bes1811PmuController:
    """BES1811 PMU LDO 归一化控制器。

    用法::

        ctrl = Bes1811PmuController()
        ctrl.connect()
        state = ctrl.read_ldo("LDO_01")
        ctrl.set_ldo_enabled("LDO_01", True)
        ctrl.set_ldo_voltage("LDO_01", 1.2)
        ctrl.disconnect()
    """

    def __init__(self, dll_path=None, speed_mode=None):
        self._dll_path = dll_path
        self._speed_mode = speed_mode
        self._i2c = None

    # ---- 连接管理 ----
    def connect(self) -> bool:
        """初始化 I2C 接口; 返回是否成功。"""
        if self._i2c is not None:
            return True
        from lib.i2c.i2c_interface_x64 import I2CInterface, I2CSpeedMode
        speed = self._speed_mode or I2CSpeedMode.SPEED_100K
        self._i2c = I2CInterface(dll_path=self._dll_path, speed_mode=speed)
        if not self._i2c.initialize():
            logger.error("1811 PMU: I2C 接口初始化失败")
            self._i2c = None
            return False
        logger.info("1811 PMU: I2C 已连接 (addr=0x%02X, %d-bit)", I2C_DEVICE_ADDR, I2C_WIDTH)
        return True

    def disconnect(self):
        """释放 I2C 接口。"""
        if self._i2c is not None:
            try:
                self._i2c.close()
            except Exception:
                pass
            self._i2c = None
            logger.info("1811 PMU: I2C 已断开")

    @property
    def is_connected(self) -> bool:
        return self._i2c is not None and self._i2c.initialized

    # ---- 底层寄存器读写 ----
    def read_register(self, addr: int) -> int:
        """读取 16 位寄存器。"""
        self._ensure_connected()
        return int(self._i2c.read(I2C_DEVICE_ADDR, addr, I2C_WIDTH))

    def write_register(self, addr: int, value: int):
        """整寄存器写。"""
        self._ensure_connected()
        self._i2c.write(I2C_DEVICE_ADDR, addr, value, I2C_WIDTH)

    def write_field(self, addr: int, high: int, low: int, value: int):
        """位域写 (底层 RMW, 仅修改 [high:low] 位)。"""
        self._ensure_connected()
        self._i2c.write(I2C_DEVICE_ADDR, addr, value, I2C_WIDTH, high, low)

    def _ensure_connected(self):
        if not self.is_connected:
            raise RuntimeError("1811 PMU: I2C 未连接, 请先调用 connect()")

    # ---- LDO 读取 ----
    def read_ldo(self, ldo_id: str) -> Optional[LdoState]:
        """读取单个 LDO 的完整状态。"""
        rm = get_reg_map(ldo_id)
        if rm is None:
            logger.warning("1811 PMU: %s 无寄存器映射", ldo_id)
            return None
        pu = self._read_field(rm.pu)
        pu_dr = self._read_field(rm.pu_dr)
        lp = self._read_field(rm.lp)
        lp_dr = self._read_field(rm.lp_dr)
        vbit_n = self._read_field(rm.vbit_normal)
        vbit_d = self._read_field(rm.vbit_dsleep)
        vbit_r = self._read_field(rm.vbit_rc)
        res_sel = self._read_field(rm.res_sel_dr)

        enabled = bool(pu) if pu_dr else False
        if lp_dr and lp:
            mode = "LP"
        elif lp_dr and not lp:
            mode = "Normal"
        else:
            mode = "Unknown"

        volt = vbit_to_voltage(ldo_id, vbit_n)
        return LdoState(
            ldo_id=ldo_id, enabled=enabled, pu_dr=pu_dr,
            mode=mode, lp_dr=lp_dr,
            vbit_normal=vbit_n, vbit_dsleep=vbit_d, vbit_rc=vbit_r,
            res_sel_dr=res_sel, voltage=volt,
        )

    def read_all_ldos(self) -> dict[str, LdoState]:
        """读取所有 LDO 状态。"""
        result = {}
        for ldo_id in LDO_IDS:
            try:
                st = self.read_ldo(ldo_id)
                if st is not None:
                    result[ldo_id] = st
            except Exception as e:
                logger.error("1811 PMU: 读取 %s 失败: %s", ldo_id, e, exc_info=True)
        return result

    # ---- LDO 控制 ----
    def set_ldo_enabled(self, ldo_id: str, enabled: bool):
        """使能/禁用 LDO (同时置驱动位=1)。"""
        rm = get_reg_map(ldo_id)
        if rm is None:
            raise ValueError(f"{ldo_id} 无寄存器映射")
        self.write_field(rm.pu_dr.reg_addr, rm.pu_dr.high_bit, rm.pu_dr.low_bit, 1)
        self.write_field(rm.pu.reg_addr, rm.pu.high_bit, rm.pu.low_bit, 1 if enabled else 0)
        logger.info("1811 PMU: %s %s", ldo_id, "使能" if enabled else "禁用")

    def set_ldo_mode(self, ldo_id: str, mode: str):
        """设置 LDO 模式 ("Normal" / "LP")。"""
        rm = get_reg_map(ldo_id)
        if rm is None:
            raise ValueError(f"{ldo_id} 无寄存器映射")
        mode = mode.capitalize()
        if mode not in ("Normal", "Lp", "LP"):
            raise ValueError(f"不支持的模式: {mode}")
        lp_val = 1 if mode in ("Lp", "LP") else 0
        self.write_field(rm.lp_dr.reg_addr, rm.lp_dr.high_bit, rm.lp_dr.low_bit, 1)
        self.write_field(rm.lp.reg_addr, rm.lp.high_bit, rm.lp.low_bit, lp_val)
        logger.info("1811 PMU: %s 模式 → %s", ldo_id, "LP" if lp_val else "Normal")

    def set_ldo_voltage(self, ldo_id: str, voltage: float):
        """设置 LDO 唤醒模式电压 (V)。

        自动将电压转换为最接近的 vbit, 并写入 vbit_normal 位域。
        若 res_sel_dr=0 则同时置 1 以使电压调整生效。
        """
        rm = get_reg_map(ldo_id)
        if rm is None:
            raise ValueError(f"{ldo_id} 无寄存器映射")
        vbit = voltage_to_vbit(ldo_id, voltage)
        if vbit is None:
            raise ValueError(f"{ldo_id} 无电压查找表")
        actual_v = vbit_to_voltage(ldo_id, vbit)
        self.write_field(
            rm.vbit_normal.reg_addr, rm.vbit_normal.high_bit,
            rm.vbit_normal.low_bit, vbit,
        )
        # 确保 res_sel_dr=1 使电压调整生效
        if self._read_field(rm.res_sel_dr) == 0:
            self.write_field(
                rm.res_sel_dr.reg_addr, rm.res_sel_dr.high_bit,
                rm.res_sel_dr.low_bit, 1,
            )
            logger.info("1811 PMU: %s res_sel_dr → 1", ldo_id)
        logger.info("1811 PMU: %s 电压 → %.4f V (vbit=0x%X)", ldo_id, actual_v, vbit)

    def set_ldo_vbit_dsleep(self, ldo_id: str, voltage: float):
        """设置 LDO 睡眠模式电压 (V)。"""
        rm = get_reg_map(ldo_id)
        if rm is None:
            raise ValueError(f"{ldo_id} 无寄存器映射")
        vbit = voltage_to_vbit(ldo_id, voltage)
        if vbit is None:
            raise ValueError(f"{ldo_id} 无电压查找表")
        self.write_field(
            rm.vbit_dsleep.reg_addr, rm.vbit_dsleep.high_bit,
            rm.vbit_dsleep.low_bit, vbit,
        )

    def set_ldo_vbit_rc(self, ldo_id: str, voltage: float):
        """设置 LDO RC 模式电压 (V)。"""
        rm = get_reg_map(ldo_id)
        if rm is None:
            raise ValueError(f"{ldo_id} 无寄存器映射")
        vbit = voltage_to_vbit(ldo_id, voltage)
        if vbit is None:
            raise ValueError(f"{ldo_id} 无电压查找表")
        self.write_field(
            rm.vbit_rc.reg_addr, rm.vbit_rc.high_bit,
            rm.vbit_rc.low_bit, vbit,
        )

    def enable_voltage_adjustment(self, ldo_id: str, enabled: bool = True):
        """单独控制 res_sel_dr 位。"""
        rm = get_reg_map(ldo_id)
        if rm is None:
            raise ValueError(f"{ldo_id} 无寄存器映射")
        self.write_field(
            rm.res_sel_dr.reg_addr, rm.res_sel_dr.high_bit,
            rm.res_sel_dr.low_bit, 1 if enabled else 0,
        )

    # ---- 内部工具 ----
    def _read_field(self, bf: BitField) -> int:
        """读取指定位域的值 (右移到 0 起始)。"""
        val = self.read_register(bf.reg_addr)
        return (val >> bf.low_bit) & ((1 << bf.width) - 1)

# -*- coding: utf-8 -*-
"""BES1811 PMU 控制器: 通过 I2C 对 1811 PMU 的 LDO 进行归一化控制。

本模块为纯 Python 业务逻辑, 无 Qt 依赖。
上层 (UI Worker) 负责 connect/disconnect 生命周期与线程管理。
"""

from dataclasses import dataclass
from typing import Callable, Optional
import time

from log_config import get_logger

from chips.bes1811_pmu import (
    BitField, LdoRegMap,
    LDO_REG_MAPS, LDO_IDS,
    BUCK_REG_MAPS, BUCK_IDS,
    I2C_DEVICE_ADDR, I2C_WIDTH,
    vbit_to_voltage, voltage_to_vbit, get_voltage_range, get_reg_map,
    is_buck,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 日志回调类型: (level, message) -> None
# ---------------------------------------------------------------------------
LogCallback = Callable[[str, str], None]


# ---------------------------------------------------------------------------
# LDO 状态快照
# ---------------------------------------------------------------------------
@dataclass
class LdoState:
    """读取到的 LDO 实时状态。"""
    ldo_id: str
    enabled: bool               # 实际使能状态 (dig_ldo_XX_pu 状态位, 1=打开)
    pu_status: int              # dig_ldo_XX_pu 状态位 (0/1)
    pu_dr: int                  # pu 驱动位 (reg_pu_ldo_XX_dr)
    mode: str                   # "Normal" / "LP" / "Unknown"
    lp_dr: int                  # lp 驱动位
    vbit_normal: int            # 唤醒电压控制字
    vbit_dsleep: int            # 睡眠电压控制字
    vbit_rc: int                # RC 电压控制字
    res_sel_dr: int             # 电压调整生效位
    voltage: Optional[float]    # 当前唤醒模式电压 (V), 由 vbit_normal 查表得到
    voltage_dsleep: Optional[float] = None  # 睡眠模式电压 (V), 由 vbit_dsleep 查表得到
    voltage_rc: Optional[float] = None      # RC 模式电压 (V), 由 vbit_rc 查表得到


@dataclass
class BuckState:
    """读取到的 BUCK 实时状态。

    与 ``LdoState`` 的差异: 无 ``lp_dr`` (BUCK 寄存器无 lp/lp_dr 字段);
    ``res_sel_dr`` 与 LDO 一样存在 (BUCK_01~06 在 0x2F0[0..5]), 但此处未单独读出
    (UI 不展示); ``mode`` 当前固定为 ``"Normal"`` (BUCK 模式切换 Normal/LP/ULP 后续补全)。
    UI 侧 (``page.py._on_read_all_done``) 仅访问 ``enabled`` / ``mode`` / ``voltage*``
    等字段, 因此 ``LdoState`` 与 ``BuckState`` 可互换使用。
    """
    ldo_id: str                 # 沿用 ldo_id 字段名, 实际存 BUCK_XX, 兼容 UI dict[id]
    enabled: bool               # 实际使能状态 (dig_buck_XX_pu 状态位, 1=打开)
    pu_status: int              # dig_buck_XX_pu 状态位 (0/1)
    pu_dr: int                  # pu 驱动位 (reg_pu_buck_XX_dr)
    mode: str                   # 当前固定 "Normal" (BUCK 模式控制后续补全)
    vbit_normal: int            # 唤醒电压控制字
    vbit_dsleep: int            # 睡眠电压控制字
    vbit_rc: int                # RC 电压控制字
    voltage: Optional[float]    # 当前唤醒模式电压 (V), 由 vbit_normal 查表得到
    voltage_dsleep: Optional[float] = None  # 睡眠模式电压 (V), 由 vbit_dsleep 查表得到
    voltage_rc: Optional[float] = None      # RC 模式电压 (V), 由 vbit_rc 查表得到


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

    def __init__(self, dll_path=None, speed_mode=None, log_callback: Optional[LogCallback] = None):
        self._dll_path = dll_path
        self._speed_mode = speed_mode
        self._i2c = None
        self._log_cb = log_callback

    def _emit_log(self, level: str, msg: str):
        """向 UI 推送一条操作日志 (不依赖 Qt)。"""
        if self._log_cb is not None:
            try:
                self._log_cb(level, msg)
            except Exception:
                logger.debug("1811 PMU: log_callback 异常", exc_info=True)

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
            self._emit_log("ERROR", "I2C 接口初始化失败 (DLL 加载或设备打开失败)")
            self._i2c = None
            return False
        logger.info("1811 PMU: I2C 已连接 (addr=0x%02X, %d-bit)", I2C_DEVICE_ADDR, I2C_WIDTH)
        self._emit_log(
            "INFO",
            f"I2C 已连接: dev=0x{I2C_DEVICE_ADDR:02X}, addr_width={I2C_WIDTH}-bit",
        )
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
            self._emit_log("INFO", "I2C 已断开")

    @property
    def is_connected(self) -> bool:
        return self._i2c is not None and self._i2c.initialized

    # ---- 底层寄存器读写 ----
    def read_register(self, addr: int) -> int:
        """读取 16 位寄存器。"""
        self._ensure_connected()
        val = int(self._i2c.read(I2C_DEVICE_ADDR, addr, I2C_WIDTH))
        self._emit_log(
            "INFO",
            f"I2C 读  dev=0x{I2C_DEVICE_ADDR:02X}  @0x{addr:03X} → 0x{val:04X}",
        )
        return val

    def write_register(self, addr: int, value: int):
        """整寄存器写。"""
        self._ensure_connected()
        self._i2c.write(I2C_DEVICE_ADDR, addr, value, I2C_WIDTH)
        self._emit_log(
            "INFO",
            f"I2C 写  dev=0x{I2C_DEVICE_ADDR:02X}  @0x{addr:03X} ← 0x{value:04X}  bits[15:0]",
        )

    def write_field(self, addr: int, high: int, low: int, value: int):
        """位域写 (底层 RMW, 仅修改 [high:low] 位)。"""
        self._ensure_connected()
        self._i2c.write(I2C_DEVICE_ADDR, addr, value, I2C_WIDTH, high, low)
        width = high - low + 1
        self._emit_log(
            "INFO",
            f"I2C 写  dev=0x{I2C_DEVICE_ADDR:02X}  @0x{addr:03X} ← 0x{value:0{width}X}"
            f"  bits[{high}:{low}]",
        )

    def _ensure_connected(self):
        if not self.is_connected:
            raise RuntimeError("1811 PMU: I2C 未连接, 请先调用 connect()")

    # ---- LDO 读取 ----
    def read_ldo(self, ldo_id: str) -> Optional[LdoState]:
        """读取单个 LDO 的完整状态。

        使能判定依据: dig_ldo_XX_pu 状态寄存器 (R, 1=打开, 0=关闭)。
        """
        rm = get_reg_map(ldo_id)
        if rm is None:
            logger.warning("1811 PMU: %s 无寄存器映射", ldo_id)
            return None
        self._emit_log(
            "STEP",
            f"读取 {ldo_id} 状态  "
            f"(pu_status@0x{rm.pu_status.reg_addr:03X}[{rm.pu_status.high_bit}:{rm.pu_status.low_bit}], "
            f"vbit@0x{rm.vbit_normal.reg_addr:03X})",
        )
        # 优先读取状态位 (dig_ldo_XX_pu), 它反映硬件实际使能状态
        pu_status = self._read_field(rm.pu_status)
        pu = self._read_field(rm.pu)
        pu_dr = self._read_field(rm.pu_dr)
        lp = self._read_field(rm.lp)
        lp_dr = self._read_field(rm.lp_dr)
        vbit_n = self._read_field(rm.vbit_normal)
        vbit_d = self._read_field(rm.vbit_dsleep)
        vbit_r = self._read_field(rm.vbit_rc)
        res_sel = self._read_field(rm.res_sel_dr)

        # 真实使能状态: dig_ldo_XX_pu 状态位 (1=打开, 0=关闭)
        enabled = bool(pu_status)
        if lp_dr and lp:
            mode = "LP"
        elif lp_dr and not lp:
            mode = "Normal"
        else:
            mode = "Unknown"

        volt = vbit_to_voltage(ldo_id, vbit_n)
        volt_dsleep = vbit_to_voltage(ldo_id, vbit_d)
        volt_rc = vbit_to_voltage(ldo_id, vbit_r)
        self._emit_log(
            "INFO",
            f"{ldo_id} 状态: en={'On' if enabled else 'Off'} (dig_pu={pu_status}, cfg_pu={pu}, pu_dr={pu_dr}, {mode}), "
            f"vbit_n=0x{vbit_n:X}→{volt if volt is not None else 'N/A'} V, "
            f"vbit_d=0x{vbit_d:X}→{volt_dsleep if volt_dsleep is not None else 'N/A'} V, "
            f"vbit_rc=0x{vbit_r:X}→{volt_rc if volt_rc is not None else 'N/A'} V",
        )
        return LdoState(
            ldo_id=ldo_id, enabled=enabled, pu_status=pu_status, pu_dr=pu_dr,
            mode=mode, lp_dr=lp_dr,
            vbit_normal=vbit_n, vbit_dsleep=vbit_d, vbit_rc=vbit_r,
            res_sel_dr=res_sel, voltage=volt,
            voltage_dsleep=volt_dsleep, voltage_rc=volt_rc,
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
        self._emit_log(
            "STEP",
            f"{ldo_id} {'使能' if enabled else '禁用'}  "
            f"(pu_dr@0x{rm.pu_dr.reg_addr:03X}[{rm.pu_dr.high_bit}:{rm.pu_dr.low_bit}]=1, "
            f"pu@0x{rm.pu.reg_addr:03X}[{rm.pu.high_bit}:{rm.pu.low_bit}]={1 if enabled else 0})",
        )
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
        mode_text = "LP" if lp_val else "Normal"
        self._emit_log(
            "STEP",
            f"{ldo_id} 模式 → {mode_text}  "
            f"(lp_dr@0x{rm.lp_dr.reg_addr:03X}[{rm.lp_dr.high_bit}:{rm.lp_dr.low_bit}]=1, "
            f"lp@0x{rm.lp.reg_addr:03X}[{rm.lp.high_bit}:{rm.lp.low_bit}]={lp_val})",
        )
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
        self._emit_log(
            "STEP",
            f"{ldo_id} 电压 → {actual_v:.4f} V (target={voltage:.4f} V, vbit=0x{vbit:X})  "
            f"(vbit_normal@0x{rm.vbit_normal.reg_addr:03X}"
            f"[{rm.vbit_normal.high_bit}:{rm.vbit_normal.low_bit}])",
        )
        self.write_field(
            rm.vbit_normal.reg_addr, rm.vbit_normal.high_bit,
            rm.vbit_normal.low_bit, vbit,
        )
        # 确保 res_sel_dr=1 使电压调整生效
        self._ensure_res_sel_dr(ldo_id, rm)
        logger.info("1811 PMU: %s 电压 → %.4f V (vbit=0x%X)", ldo_id, actual_v, vbit)

    def set_ldo_vbit_dsleep(self, ldo_id: str, voltage: float):
        """设置 LDO 睡眠模式电压 (V)。

        流程与 set_ldo_voltage 一致: 写 vbit_dsleep 后, 若 res_sel_dr=0 则置 1 生效。
        """
        rm = get_reg_map(ldo_id)
        if rm is None:
            raise ValueError(f"{ldo_id} 无寄存器映射")
        vbit = voltage_to_vbit(ldo_id, voltage)
        if vbit is None:
            raise ValueError(f"{ldo_id} 无电压查找表")
        actual_v = vbit_to_voltage(ldo_id, vbit)
        self._emit_log(
            "STEP",
            f"{ldo_id} dsleep 电压 → {actual_v:.4f} V (target={voltage:.4f} V, vbit=0x{vbit:X})  "
            f"(vbit_dsleep@0x{rm.vbit_dsleep.reg_addr:03X}"
            f"[{rm.vbit_dsleep.high_bit}:{rm.vbit_dsleep.low_bit}])",
        )
        self.write_field(
            rm.vbit_dsleep.reg_addr, rm.vbit_dsleep.high_bit,
            rm.vbit_dsleep.low_bit, vbit,
        )
        self._ensure_res_sel_dr(ldo_id, rm)
        logger.info("1811 PMU: %s dsleep 电压 → %.4f V (vbit=0x%X)", ldo_id, actual_v, vbit)

    def set_ldo_vbit_rc(self, ldo_id: str, voltage: float):
        """设置 LDO RC 模式电压 (V)。

        流程与 set_ldo_voltage 一致: 写 vbit_rc 后, 若 res_sel_dr=0 则置 1 生效。
        """
        rm = get_reg_map(ldo_id)
        if rm is None:
            raise ValueError(f"{ldo_id} 无寄存器映射")
        vbit = voltage_to_vbit(ldo_id, voltage)
        if vbit is None:
            raise ValueError(f"{ldo_id} 无电压查找表")
        actual_v = vbit_to_voltage(ldo_id, vbit)
        self._emit_log(
            "STEP",
            f"{ldo_id} RC 电压 → {actual_v:.4f} V (target={voltage:.4f} V, vbit=0x{vbit:X})  "
            f"(vbit_rc@0x{rm.vbit_rc.reg_addr:03X}"
            f"[{rm.vbit_rc.high_bit}:{rm.vbit_rc.low_bit}])",
        )
        self.write_field(
            rm.vbit_rc.reg_addr, rm.vbit_rc.high_bit,
            rm.vbit_rc.low_bit, vbit,
        )
        self._ensure_res_sel_dr(ldo_id, rm)
        logger.info("1811 PMU: %s RC 电压 → %.4f V (vbit=0x%X)", ldo_id, actual_v, vbit)

    def enable_voltage_adjustment(self, ldo_id: str, enabled: bool = True):
        """单独控制 res_sel_dr 位。"""
        rm = get_reg_map(ldo_id)
        if rm is None:
            raise ValueError(f"{ldo_id} 无寄存器映射")
        self.write_field(
            rm.res_sel_dr.reg_addr, rm.res_sel_dr.high_bit,
            rm.res_sel_dr.low_bit, 1 if enabled else 0,
        )

    # ---- BUCK 读取 ----
    def read_buck(self, buck_id: str) -> Optional[BuckState]:
        """读取单个 BUCK 的完整状态。

        使能判定依据: dig_buck_XX_pu 状态位 (与 LDO 同, 1=打开)。
        模式当前固定 "Normal" (BUCK 模式控制后续补全)。
        """
        rm = BUCK_REG_MAPS.get(buck_id)
        if rm is None:
            logger.warning("1811 PMU: %s 无 BUCK 寄存器映射", buck_id)
            return None
        self._emit_log(
            "STEP",
            f"读取 {buck_id} 状态  "
            f"(pu_status@0x{rm.pu_status.reg_addr:03X}[{rm.pu_status.high_bit}:{rm.pu_status.low_bit}], "
            f"vbit@0x{rm.vbit_normal.reg_addr:03X})",
        )
        pu_status = self._read_field(rm.pu_status)
        pu = self._read_field(rm.pu)
        pu_dr = self._read_field(rm.pu_dr)
        vbit_n = self._read_field(rm.vbit_normal)
        vbit_d = self._read_field(rm.vbit_dsleep)
        vbit_r = self._read_field(rm.vbit_rc)

        enabled = bool(pu_status)
        # BUCK 模式控制 (Normal/LP/ULP) 后续补全, 当前固定 Normal
        mode = "Normal"
        volt = vbit_to_voltage(buck_id, vbit_n)
        volt_dsleep = vbit_to_voltage(buck_id, vbit_d)
        volt_rc = vbit_to_voltage(buck_id, vbit_r)
        self._emit_log(
            "INFO",
            f"{buck_id} 状态: en={'On' if enabled else 'Off'} (dig_pu={pu_status}, cfg_pu={pu}, pu_dr={pu_dr}), "
            f"vbit_n=0x{vbit_n:X}→{volt if volt is not None else 'N/A'} V, "
            f"vbit_d=0x{vbit_d:X}→{volt_dsleep if volt_dsleep is not None else 'N/A'} V, "
            f"vbit_rc=0x{vbit_r:X}→{volt_rc if volt_rc is not None else 'N/A'} V",
        )
        return BuckState(
            ldo_id=buck_id, enabled=enabled, pu_status=pu_status, pu_dr=pu_dr,
            mode=mode,
            vbit_normal=vbit_n, vbit_dsleep=vbit_d, vbit_rc=vbit_r,
            voltage=volt,
            voltage_dsleep=volt_dsleep, voltage_rc=volt_rc,
        )

    def read_all_bucks(self) -> dict[str, BuckState]:
        """读取所有 BUCK 状态。"""
        result = {}
        for buck_id in BUCK_IDS:
            try:
                st = self.read_buck(buck_id)
                if st is not None:
                    result[buck_id] = st
            except Exception as e:
                logger.error("1811 PMU: 读取 %s 失败: %s", buck_id, e, exc_info=True)
        return result

    def read_all_modules(self) -> dict:
        """读取全部 LDO + BUCK 状态, 合并为 {id: LdoState|BuckState}。"""
        result: dict = {}
        result.update(self.read_all_ldos())
        result.update(self.read_all_bucks())
        return result

    # ---- BUCK 控制 ----
    def set_buck_enabled(self, buck_id: str, enabled: bool):
        """使能/禁用 BUCK (同时置驱动位=1)。

        与 LDO 写入流程完全一致 (pu_dr=1 → pu=val); BUCK 无 res_sel_dr。
        """
        rm = BUCK_REG_MAPS.get(buck_id)
        if rm is None:
            raise ValueError(f"{buck_id} 无 BUCK 寄存器映射")
        self._emit_log(
            "STEP",
            f"{buck_id} {'使能' if enabled else '禁用'}  "
            f"(pu_dr@0x{rm.pu_dr.reg_addr:03X}[{rm.pu_dr.high_bit}:{rm.pu_dr.low_bit}]=1, "
            f"pu@0x{rm.pu.reg_addr:03X}[{rm.pu.high_bit}:{rm.pu.low_bit}]={1 if enabled else 0})",
        )
        self.write_field(rm.pu_dr.reg_addr, rm.pu_dr.high_bit, rm.pu_dr.low_bit, 1)
        self.write_field(rm.pu.reg_addr, rm.pu.high_bit, rm.pu.low_bit, 1 if enabled else 0)
        logger.info("1811 PMU: %s %s", buck_id, "使能" if enabled else "禁用")

    def set_buck_voltage(self, buck_id: str, voltage: float):
        """设置 BUCK 唤醒模式电压 (V)。

        完整流程 (5 步):
        1. bg_en_dr=1, bg_en=1; delay 1ms
        2. sw_en_dr=1, sw_en=1
        3. 调整 vbit_normal (含 res_sel_dr=1 生效位)
        4. sw_en_dr=0, sw_en=0; delay 1ms
        5. bg_en_dr=0, bg_en=0
        """
        rm = BUCK_REG_MAPS.get(buck_id)
        if rm is None:
            raise ValueError(f"{buck_id} 无 BUCK 寄存器映射")
        vbit = voltage_to_vbit(buck_id, voltage)
        if vbit is None:
            raise ValueError(f"{buck_id} 无电压查找表")
        actual_v = vbit_to_voltage(buck_id, vbit)
        self._emit_log(
            "STEP",
            f"{buck_id} 电压 → {actual_v:.4f} V (target={voltage:.4f} V, vbit=0x{vbit:X})  "
            f"(vbit_normal@0x{rm.vbit_normal.reg_addr:03X}"
            f"[{rm.vbit_normal.high_bit}:{rm.vbit_normal.low_bit}])",
        )
        # BUCK 调压前置序列 (bg_en / sw_en)
        self._buck_voltage_pre_seq(buck_id, rm)
        # 调整 vbit_normal
        self.write_field(
            rm.vbit_normal.reg_addr, rm.vbit_normal.high_bit,
            rm.vbit_normal.low_bit, vbit,
        )
        # 确保 res_sel_dr=1 使电压调整生效 (与 LDO 一致)
        self._ensure_res_sel_dr(buck_id, rm)
        # BUCK 调压后置序列 (sw_en / bg_en 复位)
        self._buck_voltage_post_seq(buck_id, rm)
        logger.info("1811 PMU: %s 电压 → %.4f V (vbit=0x%X)", buck_id, actual_v, vbit)

    def set_buck_vbit_dsleep(self, buck_id: str, voltage: float):
        """设置 BUCK 睡眠模式电压 (V)。

        完整流程与 set_buck_voltage 一致 (5 步 bg_en/sw_en 序列 + 写 vbit_dsleep + res_sel_dr)。
        """
        rm = BUCK_REG_MAPS.get(buck_id)
        if rm is None:
            raise ValueError(f"{buck_id} 无 BUCK 寄存器映射")
        vbit = voltage_to_vbit(buck_id, voltage)
        if vbit is None:
            raise ValueError(f"{buck_id} 无电压查找表")
        actual_v = vbit_to_voltage(buck_id, vbit)
        self._emit_log(
            "STEP",
            f"{buck_id} dsleep 电压 → {actual_v:.4f} V (target={voltage:.4f} V, vbit=0x{vbit:X})  "
            f"(vbit_dsleep@0x{rm.vbit_dsleep.reg_addr:03X}"
            f"[{rm.vbit_dsleep.high_bit}:{rm.vbit_dsleep.low_bit}])",
        )
        self._buck_voltage_pre_seq(buck_id, rm)
        self.write_field(
            rm.vbit_dsleep.reg_addr, rm.vbit_dsleep.high_bit,
            rm.vbit_dsleep.low_bit, vbit,
        )
        self._ensure_res_sel_dr(buck_id, rm)
        self._buck_voltage_post_seq(buck_id, rm)
        logger.info("1811 PMU: %s dsleep 电压 → %.4f V (vbit=0x%X)", buck_id, actual_v, vbit)

    def set_buck_vbit_rc(self, buck_id: str, voltage: float):
        """设置 BUCK RC 模式电压 (V)。

        完整流程与 set_buck_voltage 一致 (5 步 bg_en/sw_en 序列 + 写 vbit_rc + res_sel_dr)。
        """
        rm = BUCK_REG_MAPS.get(buck_id)
        if rm is None:
            raise ValueError(f"{buck_id} 无 BUCK 寄存器映射")
        vbit = voltage_to_vbit(buck_id, voltage)
        if vbit is None:
            raise ValueError(f"{buck_id} 无电压查找表")
        actual_v = vbit_to_voltage(buck_id, vbit)
        self._emit_log(
            "STEP",
            f"{buck_id} RC 电压 → {actual_v:.4f} V (target={voltage:.4f} V, vbit=0x{vbit:X})  "
            f"(vbit_rc@0x{rm.vbit_rc.reg_addr:03X}"
            f"[{rm.vbit_rc.high_bit}:{rm.vbit_rc.low_bit}])",
        )
        self._buck_voltage_pre_seq(buck_id, rm)
        self.write_field(
            rm.vbit_rc.reg_addr, rm.vbit_rc.high_bit,
            rm.vbit_rc.low_bit, vbit,
        )
        self._ensure_res_sel_dr(buck_id, rm)
        self._buck_voltage_post_seq(buck_id, rm)
        logger.info("1811 PMU: %s RC 电压 → %.4f V (vbit=0x%X)", buck_id, actual_v, vbit)

    # ---- BUCK 调压 bg_en / sw_en 前置/后置序列 ----
    # 完整逻辑 (以 BUCK_01 为例):
    #   1. bg_en_dr=1, bg_en=1; delay 1ms
    #   2. sw_en_dr=1, sw_en=1
    #   (中间: 调整 vbit + res_sel_dr)
    #   4. sw_en_dr=0, sw_en=0; delay 1ms
    #   5. bg_en_dr=0, bg_en=0
    # 若 rm 无 bg_en / sw_en 字段 (例如 LDO 误调用), 则跳过序列。
    _BUCK_SEQ_DELAY_SEC = 0.001  # 1 ms

    def _buck_voltage_pre_seq(self, buck_id: str, rm: LdoRegMap):
        """BUCK 调压前置序列: 步骤 1~2 (bg_en → delay → sw_en)。"""
        if rm.bg_en is None or rm.sw_en is None:
            return
        # Step 1: bg_en_dr=1, bg_en=1
        self._emit_log(
            "STEP",
            f"{buck_id} 调压前置 [1/2] bg_en_dr=1, bg_en=1  "
            f"(@0x{rm.bg_en.reg_addr:03X}[{rm.bg_en_dr.high_bit}:{rm.bg_en_dr.low_bit},"
            f"{rm.bg_en.high_bit}:{rm.bg_en.low_bit}])",
        )
        self.write_field(rm.bg_en_dr.reg_addr, rm.bg_en_dr.high_bit, rm.bg_en_dr.low_bit, 1)
        self.write_field(rm.bg_en.reg_addr, rm.bg_en.high_bit, rm.bg_en.low_bit, 1)
        # delay 1ms
        time.sleep(self._BUCK_SEQ_DELAY_SEC)
        # Step 2: sw_en_dr=1, sw_en=1
        self._emit_log(
            "STEP",
            f"{buck_id} 调压前置 [2/2] sw_en_dr=1, sw_en=1  "
            f"(@0x{rm.sw_en.reg_addr:03X}[{rm.sw_en_dr.high_bit}:{rm.sw_en_dr.low_bit},"
            f"{rm.sw_en.high_bit}:{rm.sw_en.low_bit}])",
        )
        self.write_field(rm.sw_en_dr.reg_addr, rm.sw_en_dr.high_bit, rm.sw_en_dr.low_bit, 1)
        self.write_field(rm.sw_en.reg_addr, rm.sw_en.high_bit, rm.sw_en.low_bit, 1)

    def _buck_voltage_post_seq(self, buck_id: str, rm: LdoRegMap):
        """BUCK 调压后置序列: 步骤 4~5 (sw_en=0 → delay → bg_en=0)。"""
        if rm.bg_en is None or rm.sw_en is None:
            return
        # Step 4: sw_en_dr=0, sw_en=0
        self._emit_log(
            "STEP",
            f"{buck_id} 调压后置 [1/2] sw_en_dr=0, sw_en=0  "
            f"(@0x{rm.sw_en.reg_addr:03X})",
        )
        self.write_field(rm.sw_en_dr.reg_addr, rm.sw_en_dr.high_bit, rm.sw_en_dr.low_bit, 0)
        self.write_field(rm.sw_en.reg_addr, rm.sw_en.high_bit, rm.sw_en.low_bit, 0)
        # delay 1ms
        time.sleep(self._BUCK_SEQ_DELAY_SEC)
        # Step 5: bg_en_dr=0, bg_en=0
        self._emit_log(
            "STEP",
            f"{buck_id} 调压后置 [2/2] bg_en_dr=0, bg_en=0  "
            f"(@0x{rm.bg_en.reg_addr:03X})",
        )
        self.write_field(rm.bg_en_dr.reg_addr, rm.bg_en_dr.high_bit, rm.bg_en_dr.low_bit, 0)
        self.write_field(rm.bg_en.reg_addr, rm.bg_en.high_bit, rm.bg_en.low_bit, 0)

    # ---- 内部工具 ----
    def _read_field(self, bf: BitField) -> int:
        """读取指定位域的值 (右移到 0 起始)。"""
        val = self.read_register(bf.reg_addr)
        return (val >> bf.low_bit) & ((1 << bf.width) - 1)

    def _ensure_res_sel_dr(self, module_id: str, rm: LdoRegMap):
        """确保 res_sel_dr=1, 使 vbit_normal/dsleep/rc 写入生效 (LDO 与 BUCK 通用)。

        若 res_sel_dr 已为 1 或寄存器映射中无该字段 (rm.res_sel_dr is None), 则跳过。
        """
        if rm.res_sel_dr is None:
            return
        if self._read_field(rm.res_sel_dr) == 0:
            self.write_field(
                rm.res_sel_dr.reg_addr, rm.res_sel_dr.high_bit,
                rm.res_sel_dr.low_bit, 1,
            )
            logger.info("1811 PMU: %s res_sel_dr → 1", module_id)

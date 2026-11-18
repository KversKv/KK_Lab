# -*- coding: utf-8 -*-
"""生成 BES1811 / BES1860 Output Voltage Check 校准芯片库（一次性工具，可重跑）。

基准: Temp_Docs/docs/BT1811_BT1860_FT_Efuse_V01.xlsx (pmu_efuse 表)
Vbit 寄存器: chips/bes1811_pmu.py（1860 与 1811 共用 PMU 寄存器映射，dev 0x17）
EFUSE 读取: lib/i2c/config/best1811/efuse_scripts/efuse_1811_pmu.py 与
           best1860/efuse_scripts/efuse_1860_pmu.py（厂商脚本，字索引×4 物理字节）

trim 格式为 sign-magnitude（幅度位域 + 独立符号位，1=负），mode=offset：
code = FT 基准码 + signed(EFUSE trim)。目标电压取 FT 标称值（config）。
小 BG trim（0x2/0x3）；大 BG 变体把 efuse 地址改 0x4/0x5 即可。
GPADC_Vref(0x12[3:0]) 无对应 Vbit 寄存器映射，未纳入。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chips.bes1811_pmu import BUCK_REG_MAPS, LDO_REG_MAPS
from core.pmu_test.ft_calib_ov.ft_calib_ov_analysis import validate_chip_config
from core.pmu_test.ft_calib_ov.ft_calib_ov_store import (
    load_library,
    merge_import,
    save_library,
)

# (rail 名, 类型, 寄存器映射键, EFUSE 地址, 幅度 msb, lsb, 符号位,
#  FT 标称 mV, FT 基准码, 步进 mV) —— 转录自 BT1811_BT1860_FT_Efuse_V01.xlsx
_RAILS = [
    ("BUCK1", "DCDC", "BUCK_01", 0x2, 4, 0, 5, 800.0, 0x86, 3.69),
    ("BUCK2", "DCDC", "BUCK_02", 0x2, 9, 6, 10, 1200.0, 0x50, 7.35),
    ("BUCK3", "DCDC", "BUCK_03", 0x2, 14, 11, 15, 1800.0, 0xA0, 7.35),
    ("BUCK4", "DCDC", "BUCK_04", 0x3, 4, 0, 5, 850.0, 0x93, 3.89),
    ("BUCK5", "DCDC", "BUCK_05", 0x3, 9, 6, 10, 850.0, 0x93, 3.56),
    ("BUCK6", "DCDC", "BUCK_06", 0x3, 14, 11, 15, 1000.0, 0xBE, 3.89),
    ("VREG_L7", "LDO", "LDO_07", 0xD, 14, 11, 15, 1100.0, 0x64, 4.9),
    ("VREG_L8", "LDO", "LDO_08", 0xE, 14, 11, 15, 1100.0, 0x64, 4.9),
    ("VREG_L9", "LDO", "LDO_09", 0xF, 14, 11, 15, 1700.0, 0xA0, 4.9),
    ("VREG_L10", "LDO", "LDO_10", 0x10, 14, 11, 15, 1100.0, 0x28, 4.9),
    ("VREG_L11", "LDO", "LDO_11", 0x11, 14, 11, 15, 1100.0, 0x28, 4.9),
]

_TOLERANCE_MV = 20.0
_SETTLE_MS = 20


def _build_rail(spec):
    name, rtype, map_key, efuse_addr, msb, lsb, sign_bit, nominal_mv, base_code, step_mv = spec
    reg_map = (BUCK_REG_MAPS if rtype == "DCDC" else LDO_REG_MAPS)[map_key]
    vbit = reg_map.vbit_normal
    return {
        "name": name,
        "type": rtype,
        "enabled": True,
        "vbit": {
            "reg_addr": f"0x{vbit.reg_addr:03X}",
            "msb": vbit.high_bit,
            "lsb": vbit.low_bit,
            "width_flag": None,
        },
        "efuse_field": {
            "reg_addr": f"0x{efuse_addr:X}",
            "msb": msb,
            "lsb": lsb,
            "signed": False,
            "sign_bit": sign_bit,
        },
        "mode": "offset",
        "base_code": f"0x{base_code:X}",
        "offset_lsb": 0,
        "step_mv": step_mv,
        "base_voltage_mv": round(nominal_mv - base_code * step_mv, 3),
        "target": {"source": "config", "voltage_mv": nominal_mv},
        "tolerance_mv": _TOLERANCE_MV,
        "settle_ms": _SETTLE_MS,
    }


def build_chip(chip_name, efuse_chip_name, script_rel):
    return {
        "name": chip_name,
        "i2c": {"device_addr": "0x17", "width_flag": 10, "speed_khz": 100},
        "efuse": {
            "link": "script",
            "script_filename": script_rel,
            "chip_name": efuse_chip_name,
            "device_addr": "0x17",
            "width_flag": 10,
            "speed_khz": 100,
        },
        "rails": [_build_rail(spec) for spec in _RAILS],
    }


def main():
    chips = [
        build_chip("BES1811", "1811",
                   "best1811/efuse_scripts/efuse_1811_pmu.py"),
        build_chip("BES1860", "1860",
                   "best1860/efuse_scripts/efuse_1860_pmu.py"),
    ]
    for chip in chips:
        validate_chip_config(chip)
        print(f"{chip['name']}: {len(chip['rails'])} rails validated")
    merged, conflicts = merge_import(load_library(), chips)
    save_library(merged)
    print(f"saved {len(merged)} chips (overwritten: {conflicts or 'none'})")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""1811 PMU 算法层: 模块数据模型 / 拓扑布局 / 默认状态工厂。

封装 1811 PMIC 的领域逻辑:
- `PmuModule` / `LayoutRow` 数据模型
- `_LAYOUT_ROWS` 拓扑定义 (VSYS → BUCK/LDO, 二级支路级联)
- `_default_modules()` 从芯片寄存器表构建初始模块状态
"""

from dataclasses import dataclass

from chips.bes1811_pmu import (
    get_voltage_range, get_reg_map, is_module_controllable,
    get_module_step, align_to_step, snap_range_to_step,
)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class PmuModule:
    id: str
    name: str
    type: str  # "LDO" / "BUCK"
    enabled: bool = True
    mode: str = "Normal"
    voltage: float = 1.8                # 唤醒模式电压 (vbit_normal)
    min_voltage: float = 0.5
    max_voltage: float = 3.3
    step: float = 0.05
    input: str = "VSYS"
    controllable: bool = True   # 是否支持 I2C 寄存器控制
    voltage_dsleep: float = 1.8         # 睡眠模式电压 (vbit_dsleep)
    voltage_rc: float = 1.8             # RC 模式电压 (vbit_rc)

    @property
    def modes(self):
        return ["Normal", "LP", "ULP"] if self.type == "BUCK" else ["Normal", "LP"]

    @property
    def reg_map(self):
        """返回芯片寄存器映射 (LdoRegMap 或 None)。"""
        return get_reg_map(self.id) if self.controllable else None


# 布局行：id / level(1=主轨,2=二级) / input / bus(虚拟母线名)
@dataclass
class LayoutRow:
    kind: str  # "module" / "bus"
    id: str    # 模块 id 或母线名
    level: int
    input: str
    bus_name: str = ""


_LAYOUT_ROWS = [
    # Column 1: 直连 VSYS (按数字顺序: BUCK_01-06, LDO_01/02/03/06/07/08/09/10/11)
    LayoutRow("module", "BUCK_01", 1, "VSYS"),
    LayoutRow("module", "LDO_12", 2, "BUCK_01"),
    LayoutRow("module", "BUCK_02", 1, "VSYS"),
    LayoutRow("module", "BUCK_03", 1, "VSYS"),
    LayoutRow("module", "BUCK_04", 1, "VSYS"),
    LayoutRow("module", "BUCK_05", 1, "VSYS"),
    LayoutRow("module", "BUCK_06", 1, "VSYS"),
    LayoutRow("module", "LDO_01", 1, "VSYS"),
    LayoutRow("module", "LDO_02", 1, "VSYS"),
    LayoutRow("module", "LDO_03", 1, "VSYS"),
    LayoutRow("module", "LDO_06", 1, "VSYS"),
    LayoutRow("module", "LDO_07", 1, "VSYS"),
    LayoutRow("module", "LDO_08", 1, "VSYS"),
    LayoutRow("module", "LDO_09", 1, "VSYS"),
    LayoutRow("module", "LDO_10", 1, "VSYS"),
    LayoutRow("module", "LDO_11", 1, "VSYS"),
    # Column 2: 二级支路 (按数字顺序: LDO_12 → LDO_14/15 → LDO_05/13)
    LayoutRow("bus", "vdd_l14_15", 1, "VSYS", "vdd_l14_15"),
    LayoutRow("module", "LDO_14", 2, "vdd_l14_15"),
    LayoutRow("module", "LDO_15", 2, "vdd_l14_15"),
    LayoutRow("module", "LDO_VMIC1", 2, "vdd_l14_15"),
    LayoutRow("module", "LDO_VMIC2", 2, "vdd_l14_15"),
    LayoutRow("bus", "vdd_l5", 1, "VSYS", "vdd_l5"),
    LayoutRow("module", "LDO_05", 2, "vdd_l5"),
    LayoutRow("module", "LDO_13", 2, "vdd_l5"),
]


def _default_modules() -> dict:
    mods = {}
    buck_ids = {"BUCK_01", "BUCK_02", "BUCK_03", "BUCK_04", "BUCK_05", "BUCK_06"}
    for row in _LAYOUT_ROWS:
        if row.kind != "module":
            continue
        is_buck = row.id in buck_ids
        # 统一通过 is_module_controllable 同时识别 LDO 和 BUCK
        controllable = is_module_controllable(row.id)
        # 从芯片数据获取实际电压范围
        v_min, v_max = (None, None)
        if controllable:
            v_min, v_max = get_voltage_range(row.id)
        if v_min is None:
            v_min = 0.5
            v_max = 1.5 if is_buck else 3.3
        # 取真实平均 step; 无表回退 0.01
        step = 0.01
        if controllable:
            s = get_module_step(row.id)
            if s is not None and s > 0:
                step = s
                # 把 [v_min, v_max] 对齐到 step 整数倍 (min 向下, max 向上)
                v_min, v_max = snap_range_to_step(v_min, v_max, step)
        # 默认电压: BUCK 1.0V, LDO 取范围中点偏下, 并吸附到 step
        if is_buck:
            default_v = 1.0
        elif controllable:
            default_v = v_min + (v_max - v_min) * 0.3
            default_v = align_to_step(default_v, step)
        else:
            default_v = 1.8
        mods[row.id] = PmuModule(
            id=row.id,
            name=row.id.replace("_", " "),
            type="BUCK" if is_buck else "LDO",
            enabled=True,
            mode="Normal",
            voltage=round(default_v, 4),
            min_voltage=v_min,
            max_voltage=v_max,
            step=step,
            input=row.input,
            controllable=controllable,
            # dsleep / rc 默认与 normal 一致 (UI 初始未读 DUT 时显示)
            voltage_dsleep=round(default_v, 4),
            voltage_rc=round(default_v, 4),
        )
    return mods

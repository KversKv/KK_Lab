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
    is_sw, get_sw_reg_map,
)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class PmuModule:
    id: str
    name: str
    type: str  # "LDO" / "BUCK" / "SW"
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
    # SW (Power Switch) 专用: 导通电阻 (mΩ) 与输出节点; 非 SW 模块留空
    rdson: float = 0.0                  # 导通电阻 Rdson (mΩ)
    output: str = ""                    # 输出节点 (SW 的负载侧)

    @property
    def modes(self):
        if self.type == "BUCK":
            return ["Normal", "LP", "ULP"]
        if self.type == "SW":
            return []                   # SW 无模式 (仅有闭合/开路两态)
        return ["Normal", "LP"]

    @property
    def reg_map(self):
        """返回芯片寄存器映射 (LdoRegMap 或 None)。

        SW 类型无 LdoRegMap (走 ``get_sw_reg_map`` 单独查询)。
        """
        if self.type == "SW" or not self.controllable:
            return None
        return get_reg_map(self.id)

    @property
    def sw_reg_map(self):
        """返回 SW 寄存器映射 (SwRegMap 或 None); 非 SW 返回 None。"""
        return get_sw_reg_map(self.id) if self.type == "SW" else None


# 布局行：id / level(1=主轨,2=二级) / input / bus(虚拟母线名)
@dataclass
class LayoutRow:
    kind: str  # "module" / "bus"
    id: str    # 模块 id 或母线名
    level: int
    input: str
    bus_name: str = ""
    pair: str = ""           # 并联对偶的伙伴模块 ID (输出短接, 互斥使能)
    pair_layout: str = ""    # "vertical" (相邻行上下, 输出端短接)


# 输出并联对偶表: BUCK ↔ LDO 同一轨冗余, 使能互斥 (开一个则关另一个)
_PAIRS = {
    "BUCK_01": "LDO_01", "LDO_01": "BUCK_01",
    "BUCK_02": "LDO_02", "LDO_02": "BUCK_02",
    "BUCK_03": "LDO_03", "LDO_03": "BUCK_03",
    "BUCK_06": "LDO_06", "LDO_06": "BUCK_06",
}


def get_pair_partner(mod_id: str) -> str:
    """返回模块的并联对偶伙伴 ID, 无则返回空串。"""
    return _PAIRS.get(mod_id, "")


_LAYOUT_ROWS = [
    # 并联对偶组 1: BUCK_01 / LDO_01 (上下相邻并联, 输出短接)
    LayoutRow("module", "BUCK_01", 1, "VSYS"),
    LayoutRow("module", "LDO_01", 1, "VSYS", pair="BUCK_01", pair_layout="vertical"),
    # SW1, SW7 (VIN: LDO_01&BUCK_01) — 紧跟 VIN 源模块块
    LayoutRow("module", "SW1", 1, "LDO_01&BUCK_01"),
    LayoutRow("module", "SW7", 1, "LDO_01&BUCK_01"),
    # 并联对偶组 2: BUCK_02 / LDO_02 (上下相邻并联)
    LayoutRow("module", "BUCK_02", 1, "VSYS"),
    LayoutRow("module", "LDO_02", 1, "VSYS", pair="BUCK_02", pair_layout="vertical"),
    # LDO_12 VIN: LDO_02&BUCK_02 对偶输出轨 (取 BUCK_02 半 id, 由 _draw_vin_tree 渲染)
    LayoutRow("module", "LDO_12", 2, "BUCK_02"),
    # SW2 (VIN: LDO_02&BUCK_02)
    LayoutRow("module", "SW2", 1, "LDO_02&BUCK_02"),
    # 并联对偶组 6: BUCK_06 / LDO_06 (跨列输出并联)
    # LDO_06 (L2, 由 LDO_02&BUCK_02 供电) 置于 BUCK_06 (L1, VSYS) 上方;
    # BUCK_06 输出横跨第二列后与 LDO_06 输出紫色短接 (pair 关系保留)
    # LDO_12/SW2 放 LDO_06 上方, 使 VIN 干线止于 LDO_06, BUCK_06 横线不跨干线
    LayoutRow("module", "LDO_06", 2, "LDO_02&BUCK_02", pair="BUCK_06"),
    LayoutRow("module", "BUCK_06", 1, "VSYS"),
    # 并联对偶组 3: BUCK_03 / LDO_03 (上下相邻并联)
    LayoutRow("module", "BUCK_03", 1, "VSYS"),
    LayoutRow("module", "LDO_03", 1, "VSYS", pair="BUCK_03", pair_layout="vertical"),
    LayoutRow("module", "LDO_07", 2, "BUCK_03"),
    LayoutRow("module", "LDO_08", 2, "BUCK_03"),
    LayoutRow("module", "LDO_09", 2, "BUCK_03"),
    LayoutRow("module", "LDO_10", 2, "BUCK_03"),
    LayoutRow("module", "LDO_11", 2, "BUCK_03"),
    # SW3, SW4 (VIN: LDO_03&BUCK_03)
    LayoutRow("module", "SW3", 1, "LDO_03&BUCK_03"),
    LayoutRow("module", "SW4", 1, "LDO_03&BUCK_03"),
    LayoutRow("module", "BUCK_04", 1, "VSYS"),
    LayoutRow("module", "BUCK_05", 1, "VSYS"),
    # Column 2: 二级支路 (按数字顺序: LDO_12 → LDO_14/15 → LDO_05/13)
    LayoutRow("bus", "vdd_l14_15", 1, "VSYS", "vdd_l14_15"),
    LayoutRow("module", "LDO_14", 2, "vdd_l14_15"),
    LayoutRow("module", "LDO_15", 2, "vdd_l14_15"),
    LayoutRow("module", "LDO_VMIC1", 2, "vdd_l14_15"),
    LayoutRow("module", "LDO_VMIC2", 2, "vdd_l14_15"),
    LayoutRow("bus", "vdd_l5", 1, "VSYS", "vdd_l5"),
    LayoutRow("module", "LDO_05", 2, "vdd_l5"),
    # LDO_13 VIN: VSYS 直连 (level 1), 作为 SW5/SW6 单模块源
    LayoutRow("module", "LDO_13", 1, "VSYS"),
    # SW5, SW6 (VIN: LDO_13) — 紧跟 LDO_13
    LayoutRow("module", "SW5", 1, "LDO_13"),
    LayoutRow("module", "SW6", 1, "LDO_13"),
]


# Power Switch 元数据: (id, 显示名, VIN 节点, Rdson mΩ, 域)
# 寄存器映射见 chips.bes1811_pmu.SW_REG_MAPS; en/en_dr 两位域控制闭合/开路。
_SW_DEFS = [
    ("SW1", "LDO_01 SW1", "LDO_01&BUCK_01", 1994.553028, "1p8"),
    ("SW7", "LDO_01 SW7", "LDO_01&BUCK_01", 1504.332478, "1p8"),
    ("SW2", "LDO_02 SW2", "LDO_02&BUCK_02", 506.7093932, "1p8"),
    ("SW3", "LDO_03 SW3", "LDO_03&BUCK_03", 412.5445588, "1p8"),
    ("SW4", "LDO_03 SW4", "LDO_03&BUCK_03", 823.587135, "1p8"),
    ("SW5", "3p3 SW5", "LDO_13", 861.1453233, "vusb33"),
    ("SW6", "3p3 SW6", "LDO_13", 1427.899106, "vusb33"),
]

# SW 默认闭合/开路 (规则不匹配时的 fallback): SW1/3/5/6 闭合, SW7/2/4 开路。
# 可控 SW (在 SW_REG_MAPS 中, 即"规则匹配") 在 Check 成功后按此表主动写
# en_dr=1, en=1/0; 不可控 SW 仅以此作本地默认显示。
_SW_DEFAULT_ENABLED = {
    "SW1": True,
    "SW2": False,
    "SW3": True,
    "SW4": False,
    "SW5": True,
    "SW6": True,
    "SW7": False,
}


def sw_default_enabled(sw_id: str) -> bool:
    """返回 SW 默认闭合状态 (True=闭合 / False=开路); 未知 ID 默认开路。"""
    return _SW_DEFAULT_ENABLED.get(sw_id, False)


def _default_modules() -> dict:
    mods = {}
    buck_ids = {"BUCK_01", "BUCK_02", "BUCK_03", "BUCK_04", "BUCK_05", "BUCK_06"}
    for row in _LAYOUT_ROWS:
        if row.kind != "module":
            continue
        # SW 由下方 _SW_DEFS 单独构建 (无电压/模式), 跳过 LDO/BUCK 逻辑
        if is_sw(row.id):
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
    # Power Switch (SW): 无电压/模式, 仅闭合/开路两态 + Rdson + 输入输出节点
    for sw_id, sw_name, sw_input, sw_rdson, _domain in _SW_DEFS:
        mods[sw_id] = PmuModule(
            id=sw_id,
            name=sw_name,
            type="SW",
            enabled=sw_default_enabled(sw_id),
            mode="Normal",          # 占位, SW 无模式 (modes 返回 [])
            voltage=0.0,
            min_voltage=0.0,
            max_voltage=0.0,
            step=0.0,
            input=sw_input,
            controllable=is_sw(sw_id),
            rdson=sw_rdson,
            output="",              # 输出节点未指定, 留空待用户配置
        )
    return mods

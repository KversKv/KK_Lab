# BES1811 PMU 电源连接关系完整描述

> 本文档基于 [page.py](pmu_1811/page.py) 引用的算法层 [models.py](pmu_1811/models.py) 与芯片数据层 [chips/bes1811_pmu.py](../../../chips/bes1811_pmu.py) 自动汇总, 描述 BES1811 PMIC 在该工具中的全部电源连接关系、模块元信息、寄存器映射与电压范围。

---

## 1. 全局总线与硬件参数

| 项目 | 值 | 说明 |
|---|---|---|
| 设备类型 | BES1811 PMIC | DUT |
| I2C 设备地址 | `0x17` | 7 位地址 |
| 寄存器地址位宽 | 10 bit | 范围 `0x000`~`0x3FF` |
| 数据位宽 | 16 bit | 每次读写 16 位 |
| Chip ID 校验 | `0x0000==0x18F0` 且 `0x0001==0x1100` | Check 流程首步, 不符则判定 DUT 非 1811 |
| 主输入轨 | `VSYS` | 系统电源, 所有 L1 模块直接取电 |
| 子母线 1 | `vdd_l14_15` | VSYS 分支, 供 LDO_14 / LDO_15 / LDO_VMIC1 / LDO_VMIC2 |
| 子母线 2 | `vdd_l5` | VSYS 分支, 供 LDO_05 |
| 默认 I2C 速度 | 100K | `speed_mode=None` 时使用 |

---

## 2. 模块分类总览

工具中 1811 PMIC 被建模为 **3 类模块**, 共 **29 个独立单元**:

| 类型 | 数量 | ID 范围 | 控制维度 |
|---|---|---|---|
| LDO (普通线性稳压器) | 15 个 | LDO_01/02/03/05/06/07/08/09/10/11/12/13/14/15 + LDO_VMIC1/VMIC2 | 使能 / 模式 (Normal/LP) / 三档电压 (Normal/DeepSleep/RC) |
| BUCK (DCDC 开关稳压器) | 6 个 | BUCK_01~BUCK_06 | 使能 / 模式 (Normal/LP/ULP, 模式切换**待补全**) / 三档电压 + bandgap/switch 前置流程 |
| SW (Power Switch 电源开关) | 7 个 | SW1~SW7 | 仅闭合/开路两态 (无电压/无模式), 由 `en` + `en_dr` 两位控制 |
| VMIC (麦克风偏置 LDO) | 2 个 | LDO_VMIC1 / LDO_VMIC2 | 特例: MIC_LDO + MIC_BIAS 组合, 无 pu_status / 无三档电压, 单档 vsel 电压 + 共用 VCM 开启序列 |

其中:
- **可控模块** (有 I2C 寄存器映射): 全部 29 个 (LDO 15 + BUCK 6 + SW 7 + VMIC 2 = 30, 但 VMIC 不在 LDO_REG_MAPS, 独立走 VMIC_REG_MAPS)
- **不可控模块**: 仅当 `is_module_controllable(id)==False` 时跳过 I2C 写入, 仅本地显示

---

## 3. 完整模块清单 (按 _LAYOUT_ROWS 顺序)

下表为画布从上到下排列的全部模块 + 母线, 共 31 行 (含 2 个 bus 行):

| 行序 | ID | 类型 | level | 输入源 (VIN) | pair (对偶) | 画布列 | 备注 |
|---|---|---|---|---|---|---|---|
| 0 | BUCK_01 | BUCK | 1 | VSYS | LDO_01 | L1 | 对偶组 1, vertical 布局 |
| 1 | LDO_01 | LDO | 1 | VSYS | BUCK_01 | L1 | 同列垂直, 输出紫色短接 |
| 2 | SW1 | SW | 1 | LDO_01&BUCK_01 | — | L2 | 1p8 域, VIN 源为 L1 对偶 → SW 居 L2 |
| 3 | SW7 | SW | 1 | LDO_01&BUCK_01 | — | L2 | 1p8 域 |
| 4 | BUCK_02 | BUCK | 1 | VSYS | LDO_02 | L1 | 对偶组 2 |
| 5 | LDO_02 | LDO | 1 | VSYS | BUCK_02 | L1 | 同列垂直 |
| 6 | LDO_12 | LDO | 2 | BUCK_02 (取对偶轨半 id) | — | L2 | 由 `_draw_vin_tree` 渲染 |
| 7 | SW2 | SW | 1 | LDO_02&BUCK_02 | — | L2 | 1p8 域 |
| 8 | LDO_06 | LDO | 2 | LDO_02&BUCK_02 | BUCK_06 | L2 | **跨列对偶** (BUCK_06@L1) |
| 9 | BUCK_06 | BUCK | 1 | VSYS | LDO_06 | L1 | 输出横跨第二列与 LDO_06 紫色短接 |
| 10 | BUCK_03 | BUCK | 1 | VSYS | LDO_03 | L1 | 对偶组 3 |
| 11 | LDO_03 | LDO | 1 | VSYS | BUCK_03 | L1 | 同列垂直 |
| 12 | LDO_07 | LDO | 2 | BUCK_03 | — | L2 | 级联子树 |
| 13 | LDO_08 | LDO | 2 | BUCK_03 | — | L2 | 级联子树 |
| 14 | LDO_09 | LDO | 2 | BUCK_03 | — | L2 | 级联子树 |
| 15 | LDO_10 | LDO | 2 | BUCK_03 | — | L2 | 级联子树 |
| 16 | LDO_11 | LDO | 2 | BUCK_03 | — | L2 | 级联子树 |
| 17 | SW3 | SW | 1 | LDO_03&BUCK_03 | — | L2 | 1p8 域 |
| 18 | SW4 | SW | 1 | LDO_03&BUCK_03 | — | L2 | 1p8 域 |
| 19 | BUCK_04 | BUCK | 1 | VSYS | — | L1 | 独立 BUCK, 无对偶 |
| 20 | BUCK_05 | BUCK | 1 | VSYS | — | L1 | 独立 BUCK, 无对偶 |
| 21 | vdd_l14_15 | bus | 1 | VSYS | — | — | 子母线药丸, 由 `_draw_subtree` 渲染 |
| 22 | LDO_14 | LDO | 2 | vdd_l14_15 | — | L2 | 挂 vdd_l14_15 |
| 23 | LDO_15 | LDO | 2 | vdd_l14_15 | — | L2 | 挂 vdd_l14_15 |
| 24 | LDO_VMIC1 | LDO (VMIC) | 2 | vdd_l14_15 | — | L2 | 麦克风偏置 A 侧 |
| 25 | LDO_VMIC2 | LDO (VMIC) | 2 | vdd_l14_15 | — | L2 | 麦克风偏置 B 侧 |
| 26 | vdd_l5 | bus | 1 | VSYS | — | — | 子母线药丸 |
| 27 | LDO_05 | LDO | 2 | vdd_l5 | — | L2 | 挂 vdd_l5 |
| 28 | LDO_13 | LDO | 1 | VSYS | — | L1 | 作为 SW5/SW6 单模块源 |
| 29 | SW5 | SW | 1 | LDO_13 | — | L2 | vusb33 域 |
| 30 | SW6 | SW | 1 | LDO_13 | — | L2 | vusb33 域 |

> **画布列定义**: L1=`CARD_X_L1` (主轨左列) / L2=`CARD_X_L2` (二级中列) / L3=`CARD_X_L3` (右列, 仅用于"由 L2 单模块供电的 SW"); 实际 SW 在本表中均居 L2 (因 VIN 源全是 L1 对偶或 L1 单模块)。

---

## 4. 电源连接关系图 (按 VIN 树分组)

### 4.1 主轨 VSYS 直接下挂

```
VSYS ──┬── BUCK_01 (L1, 对偶 LDO_01)
       ├── LDO_01  (L1, 对偶 BUCK_01)
       ├── BUCK_02 (L1, 对偶 LDO_02)
       ├── LDO_02  (L1, 对偶 BUCK_02)
       ├── BUCK_03 (L1, 对偶 LDO_03)
       ├── LDO_03  (L1, 对偶 BUCK_03)
       ├── BUCK_06 (L1, 跨列对偶 LDO_06)
       ├── BUCK_04 (L1, 独立)
       ├── BUCK_05 (L1, 独立)
       ├── vdd_l14_15 (子母线) ──┬── LDO_14
       │                          ├── LDO_15
       │                          ├── LDO_VMIC1
       │                          └── LDO_VMIC2
       ├── vdd_l5 (子母线) ─────── LDO_05
       └── LDO_13 (L1, 单模块源) ──┬── SW5
                                   └── SW6
```

### 4.2 对偶短接轨 (紫色短接) 下挂

对偶输出短接后形成的虚拟轨, 由 `_draw_vin_tree` 从短接点引出蓝色干线 (`SUB_BUS_X`):

| 对偶组 | 输出短接节点 | 下挂模块 |
|---|---|---|
| `BUCK_01&LDO_01` | LDO_01&BUCK_01 | SW1, SW7 |
| `BUCK_02&LDO_02` | LDO_02&BUCK_02 | LDO_12 (取 BUCK_02 半 id 渲染), SW2, LDO_06 |
| `BUCK_03&LDO_03` | LDO_03&BUCK_03 | SW3, SW4 |
| `BUCK_06&LDO_06` | (跨列对偶, 无下挂) | — |

### 4.3 单模块源下挂

| 源模块 | 类型 | 下挂模块 | 渲染函数 |
|---|---|---|---|
| BUCK_03 (对偶轨半 id) | BUCK | LDO_07, LDO_08, LDO_09, LDO_10, LDO_11 (L2 级联子树) | `_draw_vin_tree` 内部 |
| LDO_13 | LDO | SW5, SW6 | `_draw_sw_connections` |

---

## 5. 并联对偶组 (输出短接 + 互斥使能)

4 组对偶由 [models._PAIRS](pmu_1811/models.py) 定义, 由 `get_pair_partner(id)` 查询; 输出在画布以**紫色短线**短接, 使能由 `PairWriteWorker` 在单次 I2C 会话内**互锁写入** (开一个则关另一个):

| 对偶组 | 布局类型 | 输入差异 |
|---|---|---|
| `BUCK_01 ↔ LDO_01` | 同列垂直 (L1) | 均 VSYS |
| `BUCK_02 ↔ LDO_02` | 同列垂直 (L1) | 均 VSYS |
| `BUCK_03 ↔ LDO_03` | 同列垂直 (L1) | 均 VSYS |
| `BUCK_06 ↔ LDO_06` | **跨列对偶** | BUCK_06=VSYS@L1, LDO_06=LDO_02&BUCK_02@L2 |

互锁语义:
- **开启**对偶成员 A → `PairWriteWorker` 一次会话先开 A 再关 B (`_apply` 按 `is_buck()` 派发到 `set_buck_enabled` / `set_ldo_enabled`)
- **关闭**对偶成员 → 普通 `LdoWriteWorker` (enable=False), 不影响对偶 (用户可自由关闭)
- 未连接 (`_i2c_connected==False`) 时仅本地更新 (`_apply_local_disable`)

---

## 6. Power Switch (SW1~SW7) 完整元信息

SW 仅闭合/开路两态, 无电压/无模式; 状态由配置位 `en` (使能配置) + `en_dr` (使能驱动位) 决定:

| ID | 显示名 | VIN (输入) | Rdson (mΩ) | 域 | 寄存器 (en / en_dr) | 默认态 |
|---|---|---|---|---|---|---|
| SW1 | LDO_01 SW1 | LDO_01&BUCK_01 | 1994.553028 | 1p8 | 0x063[15] / 0x063[14] | **闭合** |
| SW2 | LDO_02 SW2 | LDO_02&BUCK_02 | 506.7093932 | 1p8 | 0x063[13] / 0x063[12] | 开路 |
| SW3 | LDO_03 SW3 | LDO_03&BUCK_03 | 412.5445588 | 1p8 | 0x063[11] / 0x063[10] | **闭合** |
| SW4 | LDO_03 SW4 | LDO_03&BUCK_03 | 823.587135 | 1p8 | 0x063[9] / 0x063[8] | 开路 |
| SW5 | 3p3 SW5 | LDO_13 | 861.1453233 | vusb33 | 0x06B[1] / 0x06B[0] | **闭合** |
| SW6 | 3p3 SW6 | LDO_13 | 1427.899106 | vusb33 | 0x06B[9] / 0x06B[8] | **闭合** |
| SW7 | LDO_01 SW7 | LDO_01&BUCK_01 | 1504.332478 | 1p8 | 0x06C[3] / 0x06C[2] | 开路 |

**SW 默认规则** (`models._SW_DEFAULT_ENABLED`): **SW1 / SW3 / SW5 / SW6 闭合; SW2 / SW4 / SW7 开路**

**Check 流程默认规则应用**: `LdoReadAllWorker._apply_sw_defaults` 对每个**可控 SW** (在 `SW_REG_MAPS` 中) 主动写 `en_dr=1, en=1/0` 强制到默认态, 单个失败仅 WARN 不中断; 不可控 SW 仅本地默认显示。

**SW 闭合/开路控制语义**:
- 强制闭合: `en_dr=1` 且 `en=1`
- 强制开路: `en_dr=1` 且 `en=0`
- `en_dr=0` 的两种组合 (软件释放, 由硬件默认/自动控制) 语义后续讨论

**域分配**: SW1/2/3/4/7 在 `1p8` 域 (寄存器 0x063 / 0x06C); SW5/6 在 `vusb33` 域 (寄存器 0x06B)。

---

## 7. LDO 寄存器映射详表 (15 个普通 LDO)

> 数据源: [chips/bes1811_pmu.py LDO_REG_MAPS](../../../chips/bes1811_pmu.py) `LDO_VOLTAGE_TABLES`; vbit 索引为 **十六进制**。

每个 LDO 寄存器映射 (`LdoRegMap`) 包含 9 个位域: `pu` / `pu_dr` / `pu_status` / `vbit_normal` / `vbit_dsleep` / `vbit_rc` / `lp` / `lp_dr` / `res_sel_dr`。

| LDO | pu (使能) | pu_dr | pu_status (状态位) | vbit_normal | vbit_dsleep | vbit_rc | lp | lp_dr | res_sel_dr |
|---|---|---|---|---|---|---|---|---|---|
| LDO_01 | 0x00D[12]=1 | 0x00D[13] | 0x05F[0] | 0x00D[5:0]=0x14 | 0x00D[11:6]=0x0C | 0x072[13:8]=0x12 | 0x00D[14] | 0x00D[15] | 0x2F0[6] |
| LDO_02 | 0x003[2]=1 | 0x003[3] | 0x05F[1] | 0x007[4:0]=0x03 | 0x007[9:5]=0x03 | 0x071[4:0]=0x03 | 0x007[11] | 0x007[12] | 0x2F0[7] |
| LDO_03 | 0x00A[10]=1 | 0x00A[11] | 0x05F[2] | 0x00A[9:5]=0x06 | 0x00A[4:0]=0x06 | 0x073[4:0]=0x06 | 0x00A[13] | 0x00A[14] | 0x2F0[8] |
| LDO_05 | 0x008[9] | 0x008[10] | 0x05F[3] | 0x068[4:0]=0x15 | 0x068[9:5]=0x15 | 0x068[14:10]=0x15 | 0x008[12] | 0x008[13] | 0x2F0[10] |
| LDO_06 | 0x009[10]=1 | 0x009[11] | 0x05F[4] | 0x088[5:0]=0x10 | 0x089[5:0]=0x10 | 0x071[10:5]=0x10 | 0x009[13] | 0x009[14] | 0x2F0[11] |
| LDO_07 | 0x24E[9] | 0x24E[10] | 0x05F[5] | 0x250[7:0]=0x64 | 0x24F[15:8]=0x64 | 0x24F[7:0]=0x64 | 0x24E[12] | 0x24E[13] | 0x2F0[12] |
| LDO_08 | 0x11D[3] | 0x11D[4] | 0x05F[6] | 0x11C[7:0]=0x64 | 0x11C[15:8]=0x64 | 0x11D[15:8]=0x64 | 0x11D[0] | 0x11D[1] | 0x2F0[13] |
| LDO_09 | 0x067[13] | 0x067[14] | 0x05F[7] | 0x08A[7:0]=0xA0 | 0x08B[7:0]=0x00 | 0x073[12:5]=0xA0 | 0x067[10] | 0x067[11] | 0x2F0[14] |
| LDO_10 | 0x247[9] | 0x247[10] | 0x060[0] | 0x248[7:0]=0x28 | 0x249[7:0]=0x28 | 0x24A[7:0]=0x28 | 0x247[12] | 0x247[13] | 0x2F0[15] |
| LDO_11 | 0x066[13] | 0x066[14] | 0x060[1] | 0x010[15:8]=0x28 | 0x010[7:0]=0x28 | 0x066[7:0]=0x28 | 0x066[10] | 0x066[11] | 0x2F1[0] |
| LDO_12 | 0x210[9] | 0x210[10] | 0x060[2] | 0x215[10:5]=0x0C | 0x211[11:6]=0x00 | 0x211[5:0]=0x0A | 0x210[12] | 0x210[13] | 0x2F1[1] |
| LDO_13 | 0x00C[10] | 0x00C[11] | 0x060[3] | 0x085[4:0]=0x15 | 0x086[4:0]=0x15 | 0x087[4:0]=0x15 | 0x00C[13] | 0x00C[14] | 0x2F1[2] |
| LDO_14 | 0x202[9] | 0x202[10] | 0x060[4] | 0x203[4:0]=0x06 | 0x204[4:0]=0x06 | 0x205[4:0]=0x06 | 0x202[12] | 0x202[13] | 0x2F1[3] |
| LDO_15 | 0x20A[9] | 0x20A[10] | 0x060[5] | 0x20B[14:10]=0x06 | 0x20B[9:5]=0x06 | 0x20B[4:0]=0x06 | 0x20A[12] | 0x20A[13] | 0x2F1[4] |

**关键约定**:
- **使能判定读 `pu_status` 状态位** (R, 1=打开), 不读配置位 `pu` (pu=1 但 pu_dr=0 时硬件未必真开)
- **写入两步固定顺序**: 先置 `pu_dr=1` (或 `lp_dr=1`) → 再写配置位 `pu` (或 `lp`)
- **三档电压**: Normal / Deep Sleep / RC 分别对应 `vbit_normal` / `vbit_dsleep` / `vbit_rc`, 共用同一查找表
- **vbit 索引进制**: LDO = **十六进制** (源 xlsx 含 A-F), BUCK = **十进制** (256 档连续)
- **电压写入 3 步**: 查表取 vbit → 写 `vbit_normal` → 若 `res_sel_dr==0` 则置 1 (生效)

---

## 8. LDO 电压范围与步进 (15 个普通 LDO)

下表电压范围由 `get_voltage_range(id)` 从 `LDO_VOLTAGE_TABLES` 取真实最小/最大, 并用 `snap_range_to_step` 对齐到 step 整数倍:

| LDO | 电压档位数 | 最低 (V) | 最高 (V) | 步进 step (V) | 步进 (mV) | 默认电压 (V) |
|---|---|---|---|---|---|---|
| LDO_01 | 64 | 0.3030 | 1.8864 | 0.025 | 25 | ~0.79 (范围中点偏下) |
| LDO_02 | 11 | 0.8195 | 1.8051 | 0.099 | 99 | ~1.04 |
| LDO_03 | 11 | 1.1978 | 2.1926 | 0.099 | 99 | ~1.46 |
| LDO_05 | 26 | 1.2070 | 3.7120 | 0.100 | 100 | ~1.97 |
| LDO_06 | 26 | 0.5985 | 1.2188 | 0.025 | 25 | ~0.74 |
| LDO_07 | 200 | 0.5955 | 1.4990 | 0.005 | 5 | ~0.85 |
| LDO_08 | 199 | 0.5975 | 1.4997 | 0.005 | 5 | ~0.85 |
| LDO_09 | 256 | 0.8993 | 2.0905 | 0.005 | 5 | ~1.20 |
| LDO_10 | 232 | 0.9011 | 2.1186 | 0.005 | 5 | ~1.18 |
| LDO_11 | 200 | 0.9009 | (查表) | 0.005 | 5 | ~1.18 |
| LDO_12 | 26 | (查表) | (查表) | 0.025 | 25 | (查表) |
| LDO_13 | 21 | (查表) | (查表) | 0.100 | 100 | ~1.78 |
| LDO_14 | 11 | (查表) | (查表) | 0.100 | 100 | (查表) |
| LDO_15 | 11 | (查表) | (查表) | 0.100 | 100 | (查表) |

> 完整 vbit→电压对应表见 [chips/bes1811_pmu.py LDO_VOLTAGE_TABLES](../../../chips/bes1811_pmu.py); 部分档位存在 None 槽位 (该 vbit 无效), `voltage_to_vbit` / `neighbor_vbit` 自动跳过。

**默认电压生成逻辑** (`_default_modules()`):
1. BUCK: 默认 `1.0V`
2. LDO: `v_min + (v_max - v_min) * 0.3` (范围中点偏下) 再 `align_to_step` 吸附到 step
3. 不可控模块: 默认 `1.8V`

---

## 9. BUCK 寄存器映射详表 (6 个 BUCK)

> 数据源: [chips/bes1811_pmu.py BUCK_REG_MAPS](../../../chips/bes1811_pmu.py); vbit 索引为 **十进制**, 共 256 档连续 (无 None)。

BUCK 寄存器映射除 LDO 9 个位域外, 额外有 4 个**调压前置/后置流程位**: `bg_en` / `bg_en_dr` / `sw_en` / `sw_en_dr`。

| BUCK | pu | pu_dr | pu_status | vbit_normal | vbit_dsleep | vbit_rc | res_sel_dr | bg_en / bg_en_dr | sw_en / sw_en_dr | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|
| BUCK_01 | 0x015[0]=0 | 0x015[1] | 0x05F[8] | 0x046[7:0]=0x86 | 0x046[15:8]=0x86 | 0x074[7:0]=0x86 | 0x2F0[0] | 0x322[14]=1 / 0x322[15] | 0x323[14]=1 / 0x323[15] | vbit_normal[7:0] 与 vbit_dsleep[15:8] 共用 0x046; vbit_rc 在 0x074 (RWS) |
| BUCK_02 | 0x145[0]=0 | 0x145[1] | 0x05F[9] | 0x146[7:0]=0x50 | 0x147[7:0]=0x50 | 0x148[7:0]=0x50 | 0x2F0[1] | 0x14D[14]=1 / 0x14D[15] | 0x14E[14]=1 / 0x14E[15] | — |
| BUCK_03 | 0x1E5[0]=0 | 0x1E5[1] | 0x05F[10] | 0x1E6[7:0]=0xA0 | 0x1E7[7:0]=0xA0 | 0x1E8[7:0]=0xA0 | 0x2F0[2] | 0x1ED[14]=1 / 0x1ED[15] | 0x1EE[14]=1 / 0x1EE[15] | — |
| BUCK_04 | 0x155[0]=0 | 0x155[1] | 0x05F[11] | 0x156[7:0]=0x93 | 0x157[7:0]=0x93 | 0x158[7:0]=0x93 | 0x2F0[3] | 0x15D[14]=1 / 0x15D[15] | 0x15E[14]=1 / 0x15E[15] | 独立 BUCK, 无对偶 |
| BUCK_05 | 0x1D5[0]=0 | 0x1D5[1] | 0x05F[12] | 0x1D6[7:0]=0x93 | 0x1D7[7:0]=0x93 | 0x1D8[7:0]=0x93 | 0x2F0[4] | 0x1DD[14]=1 / 0x1DD[15] | 0x1DE[14]=1 / 0x1DE[15] | 独立 BUCK, 无对偶 |
| BUCK_06 | 0x35F[0]=0 | 0x35F[1] | 0x05F[13] | 0x35A[7:0]=0xBB | 0x35C[7:0]=0xBB | 0x35D[7:0]=0xBB | 0x2F0[5] | 0x31D[14]=1 / 0x31D[15] | 0x31E[14]=1 / 0x31E[15] | vbit_dsleep 地址 0x35C 跳过 0x35B; 跨列对偶 LDO_06 |

**状态位 0x05F 共享布局**: bit[0..7] = LDO_01~08, bit[8..13] = BUCK_01~06; `res_sel_dr` 共享 0x2F0 (BUCK 占 bit[0..5], LDO 占 bit[6..15] 散布在 0x2F0 / 0x2F1)。

**BUCK 电压写入 5 步专用流程** (调压前置/后置, `_buck_voltage_pre_seq` / `_buck_voltage_post_seq`):
1. `bg_en_dr=1, bg_en=1` (bandgap 使能) + delay 1ms
2. `sw_en=1` (开关使能)
3. 写 vbit + `res_sel_dr=1` (电压生效)
4. `sw_en=0` + delay
5. `bg_en=0` (bandgap 关闭)

LDO 无此字段, 控制器会自动跳过 `pre_seq` / `post_seq`。

---

## 10. BUCK 电压范围与步进 (6 个 BUCK)

| BUCK | 电压档位数 | 最低 (V) | 最高 (V) | 步进 step (V) | 步进 (mV) | 默认电压 (V) |
|---|---|---|---|---|---|---|
| BUCK_01 | 128 (表中) | 0.3129 | 1.2340 | 0.0036 | 3.6 | 1.0 |
| BUCK_02 | 256 | 0.6049 | (查表最高) | 0.0073 | 7.3 | 1.0 |
| BUCK_03 | 256 | (查表最低) | (查表最高) | 0.0073 | 7.3 | 1.0 |
| BUCK_04 | 256 | (查表) | (查表) | 0.0036 | 3.6 | 1.0 |
| BUCK_05 | 256 | (查表) | (查表) | 0.0037 | 3.7 | 1.0 |
| BUCK_06 | 256 | (查表) | (查表) | 0.0036 | 3.6 | 1.0 |

> 完整 vbit→电压对应表见 `BUCK_VOLTAGE_TABLES`; BUCK_02/03 为高输出档 (步进 ~7.3mV), 其余为低输出档 (~3.6mV)。

---

## 11. VMIC (LDO_VMIC1/2) 特例详表

VMIC 是麦克风偏置 LDO, 与普通 LDO 模型不同: 由 MIC_LDO + MIC_BIAS 组合而成。

### 11.1 寄存器映射

> 数据源: [chips/bes1811_pmu.py VMIC_REG_MAPS](../../../chips/bes1811_pmu.py)

| VMIC | ldo_en | ldo_dr | bias_en | bias_lpf [12:10] | bias_lp_enable | vsel [13:9] |
|---|---|---|---|---|---|---|
| LDO_VMIC1 | 0x039[11] | 0x06D[0] | 0x03B[13] | 0x03B[12:10] | 0x122[10] | 0x074[13:9]=0x09 |
| LDO_VMIC2 | 0x039[10] | 0x06D[1] | 0x03C[13] | 0x03C[12:10] | 0x122[11] | 0x075[13:9]=0x09 |

**VCM 共用位域** (VMIC1/2 共用, 开启任一 VMIC 前都需配置一次):

| 位域名 | 寄存器 | 默认值 | 说明 |
|---|---|---|---|
| `VCM_PULL_DOWN` | 0x365[13] | 1 | `reg_vcm_pull_down`, 开启时写 0 (关闭下拉) |
| `VCM_LP_EN` | 0x365[12] | 0 | `reg_vcm_lp_en`, 开启时写 1 |
| `VCM_EN` | 0x364[13] | 0 | `reg_vcm_en`, 开启时写 1 |

### 11.2 VMIC 电压表 (单档 vsel, VMEM=1.8V 工况)

vsel 5 bit, 范围 0x00~0x11 (18 档), 部分槽位为 None:

| VMIC | 档位数 | 最低 (V) | 最高 (V) | 步进 (V) | 步进 (mV) |
|---|---|---|---|---|---|
| LDO_VMIC1 | 18 (含 2 个 None) | 1.0719 | 3.3138 | 0.143 | 143 |
| LDO_VMIC2 | 18 (含 2 个 None) | 1.0712 | 3.2242 | 0.143 | 143 |

> VMEM=1.7V 工况列见 data CSV, 本表未收录; VMIC2 的 vsel 0x10/0x11 无数据为 None。

### 11.3 VMIC 特例语义

- **无 pu_status / lp / res_sel_dr / vbit 三档**, 使能 = `ldo_en` (reg_mic_ldoX_en) + `bias_en` (reg_mic_biasX_en) 双配置位**均 1** (读配置位判定, 同 SW 语义)
- **开启序列** (`set_vmic_enabled(True)`, 与脚本 vmicX_on 一致):
  1. EN VCM (共用): `0x365[13]=0` → `0x365[12]=1` → `0x364[13]=1`
  2. EN MIC_LDO: `0x122 lp_enable=1` → `0x06D dr=1` → `0x039 en=1`
  3. EN MIC_BIAS: `0x03B/C[12:10]=0x4` → `en=1`
- **关闭**: 仅写 `mic_ldoX_en=0` + `mic_biasX_en=0` (VCM / dr / lp_enable 不动)
- **电压仅一档**: `reg_mic_biasX_vsel` (5 bit), 共用 `VMIC_VOLTAGE_TABLES`
- **重要 RMW 不冲突**: `0x074[7:0]` 与 BUCK_01 vbit_rc 同寄存器不同位 (BUCK_01 用 [7:0], VMIC1 用 [13:9]), RMW 互不影响
- **UI 行为**: `modes=["Normal"]` (无 LP 切换); 属性面板隐藏 dsleep/rc 电压卡; Worker 仅支持 `enable` / `voltage`, 其余 action WARN 忽略

---

## 12. 使能 / 模式 / 电压语义约定

### 12.1 使能语义

| 模块类型 | 使能判定方式 | 写入两步顺序 |
|---|---|---|
| LDO (普通) | 读 `pu_status` 状态位 (1=真打开) | `pu_dr=1` → `pu=1` |
| BUCK | 读 `pu_status` 状态位 (0x05F[8..13]) | `pu_dr=1` → `pu=1` (+ 电压写入另有 5 步前置/后置) |
| SW | 读配置位 `en` (无独立状态位) | `en_dr=1` → `en=1/0` |
| VMIC | 读配置位 `ldo_en` AND `bias_en` (两位均 1 才算开) | 见 §11.3 开启序列 |

> ⚠️ **关键坑**: LDO/BUCK 不读配置位 `pu`, 因为 `pu=1` 但 `pu_dr=0` 时硬件未必真开; `pu_status` 才是真实反馈。

### 12.2 模式语义

| 模块类型 | 支持模式 | 写入实现状态 |
|---|---|---|
| LDO (普通) | `Normal` / `LP` | 已实现 (`set_ldo_mode`) |
| BUCK | `Normal` / `LP` / `ULP` | **待补全** (Worker 接收到 `mode` action 时 WARN 忽略) |
| SW | 无模式 (`modes=[]`) | — |
| VMIC | `Normal` (单模式) | — |

### 12.3 电压三档

普通 LDO 与 BUCK 共有 3 档电压, 共用同一查找表 (`LDO_VOLTAGE_TABLES` / `BUCK_VOLTAGE_TABLES`):

| 档位 | 位域 | 用途 |
|---|---|---|
| Normal (vbit_normal) | `vbit_normal` | 唤醒模式电压 |
| Deep Sleep (vbit_dsleep) | `vbit_dsleep` | 睡眠模式电压 |
| RC (vbit_rc) | `vbit_rc` | RC 模式电压 |

VMIC 无三档概念, 仅单档 `vsel`。

---

## 13. 数据流与写入保护

### 13.1 三种写入动作 (LdoWriteWorker.action)

| action | 调用 | 适用模块 |
|---|---|---|
| `"enable"` | `set_ldo_enabled` / `set_buck_enabled` / `set_sw_enabled` / `set_vmic_enabled` | 全部 |
| `"mode"` | `set_ldo_mode` | 仅普通 LDO (BUCK 待补全, 其余忽略) |
| `"voltage"` | `set_ldo_voltage` / `set_buck_voltage` / `set_vmic_voltage` | LDO / BUCK / VMIC |
| `"voltage_dsleep"` | `set_ldo_vbit_dsleep` / `set_buck_vbit_dsleep` | LDO / BUCK |
| `"voltage_rc"` | `set_ldo_vbit_rc` / `set_buck_vbit_rc` | LDO / BUCK |

### 13.2 写入保护 (`_start_write`)

1. `mod.controllable == False` → 直接返回 (无寄存器映射, 不下发)
2. `_i2c_connected == False` → 仅本地更新, debug 日志
3. `_worker_thread is not None` → 上次操作未完成, 丢弃并 WARN

### 13.3 Worker 完成清理

`_cleanup_worker`: `thread.quit() + wait()` → 重置 `_worker_thread=None / _worker=None` → 恢复 Check 按钮为 "Check"。

### 13.4 每次操作自建/销毁 controller

`workers.py` 中每个 Worker 在 `run()` 内 `Bes1811PmuController(dll_path, speed_mode, log_callback)` 新建, `finally` 中 `ctrl.disconnect()` 销毁, 不持持久 I2C 连接, 避免跨线程共享。

---

## 14. Check 流程

[page.py](pmu_1811/page.py) `_on_check` 触发 `LdoReadAllWorker`:

1. **首次显示自动 Check**: `showEvent` 用 `QTimer.singleShot(0, self._on_check)` 等 UI 完全布局后启动
2. **Check 内部 4 步**:
   - `ctrl.connect()` 初始化 I2C 接口
   - `ctrl.verify_chip_id()` 校验 Chip ID (0x0000==0x18F0, 0x0001==0x1100)
   - `ctrl.read_all_modules()` 读取全部 LDO + BUCK + SW 状态
   - `ctrl.init_pmu()` PMU 初始化序列
   - `_apply_sw_defaults(ctrl)` 按 `models._SW_DEFAULT_ENABLED` 主动写可控 SW 默认态, 写后重读 `read_sw` 回灌 `states`
3. **成功** (`_on_read_all_done`): 把状态写回 `_modules` (按 `pu_status` 判定使能, 按模式校验, 写入 voltage/dsleep/rc), 刷新全部卡片 + 当前选中模块属性面板; `_set_body_blocked(False)` 解锁画布
4. **失败** (`_on_i2c_error`): `_i2c_connected=False`, `_set_body_blocked(True)` 用 `_BlockedOverlay` 半透明遮罩盖住画布+属性面板拦截交互

---

## 15. 关键文件引用

| 文件 | 角色 |
|---|---|
| [pmu_1811/page.py](pmu_1811/page.py) | UI 层入口, `Pmu1811UI` 主页面 |
| [pmu_1811/models.py](pmu_1811/models.py) | 算法层, `PmuModule` / `LayoutRow` / `_LAYOUT_ROWS` / `_default_modules` / `_PAIRS` / `_SW_DEFS` |
| [pmu_1811/workers.py](pmu_1811/workers.py) | 驱动中间层, 4 个 QThread Worker (ReadAll/ReadOne/Write/PairWrite) |
| [pmu_1811/constants.py](pmu_1811/constants.py) | 配色 / 字体 / 画布几何常量 (VSYS_X / CARD_X_L1|L2|L3 / SUB_BUS_X / SW_BUS_X 等) |
| [pmu_1811/widgets/](pmu_1811/widgets/) | UI 控件 (DiagramCanvas / PropertyPanel / ModuleCard / SwitchWidget / ContextMenu) |
| [pmu_1811/AGENTS.md](pmu_1811/AGENTS.md) | 局部 AI 协作指引 (本模块单一事实源) |
| [chips/bes1811_pmu.py](../../../chips/bes1811_pmu.py) | 芯片寄存器映射 + 电压查找表 (LDO/BUCK/SW/VMIC 四表 + 辅助函数) |
| `core/bes1811_pmu_controller.py` | 控制器层, 实际 I2C 读写实现 (Bes1811PmuController) |
| `pmu_1811/data/1811 pmu inf reg.csv` | 寄存器位域定义原始数据 |
| `pmu_1811/data/BES1811 LDO输出电压范围.csv` | LDO 电压查找表原始数据 |

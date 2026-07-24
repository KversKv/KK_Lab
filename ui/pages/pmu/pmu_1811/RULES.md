# 1811 PMU 操作规则集合

> 📌 本文已整合迁移至 [AGENTS.md](./AGENTS.md)（单一事实源）。本文件保留详细位域地址表供人类查阅；AI 协作请读 AGENTS.md。

本文件汇总 1811 PMIC 各类模块（LDO / DCDC / BUCK 等）的实际硬件操作语义：使能状态如何判断、如何打开/关闭一个模块、如何切换模式与电压。所有底层操作由 `core/bes1811_pmu_controller.py::Bes1811PmuController` 实现，配置位定义在 `chips/bes1811_pmu.py`。

> 配套阅读：[README.md](./README.md) — 模块整体架构与分层。

## 目录

- [LDO](#ldo)
- [DCDC](#dcdc)（规划中）
- [BUCK](#buck)（使能 + 电压已补全；模式待补全）
- [SW](#sw)（Power Switch，闭合/开路两态）

---

## LDO

本节描述 14 个 LDO（LDO_01~15，缺 04）的实际硬件操作语义。配置位定义在 `chips/bes1811_pmu.py::LDO_REG_MAPS`。

### 1. 寄存器模型

每个 LDO 在芯片里有 9 个关键位域（见 `LdoRegMap`）：

| 字段 | 位域示例（LDO_01） | 含义 | 方向 |
|---|---|---|---|
| `pu` | `reg_pu_ldo_01` @0x00D[12] | 使能配置位（1=打开 / 0=关闭） | RW |
| `pu_dr` | `reg_pu_ldo_01_dr` @0x00D[13] | 使能驱动位（=1 才允许写 `pu`） | RW |
| `pu_status` | `dig_ldo_01_pu` @0x05F[0] | **实际使能状态位**（R，1=打开） | R |
| `lp` | `reg_lp_en_ldo_01` @0x00D[14] | LP 模式配置位（1=LP / 0=Normal） | RW |
| `lp_dr` | `reg_lp_en_ldo_01_dr` @0x00D[15] | LP 模式驱动位 | RW |
| `vbit_normal` | @0x00D[5:0] | 唤醒模式电压控制字（查 `LDO_VOLTAGE_TABLES`） | RW |
| `vbit_dsleep` | @0x00D[11:6] | 睡眠模式电压控制字 | RW |
| `vbit_rc` | @0x072[13:8] | RC 模式电压控制字 | RW |
| `res_sel_dr` | @0x2F0[6] | 电压调整生效位（=1 电压写入才生效） | RW |

**关键区别**：
- `pu` 是「软件想让它处于什么状态」（配置位）
- `pu_status` 是「硬件当前实际是否打开」（状态位） — UI 的 `enabled` 字段最终依据此位
- `pu_dr` / `lp_dr` / `res_sel_dr` 是各功能的驱动位，必须置 1 才能修改对应配置

### 2. 使能状态判断

UI 卡片上的 LED / 属性面板的开关状态 = `LdoState.enabled`，由 `read_ldo()` 返回。

判定依据（`core/bes1811_pmu_controller.py::read_ldo`）：

```python
pu_status = self._read_field(rm.pu_status)   # 读 dig_ldo_XX_pu 状态位
enabled = bool(pu_status)                      # 1 = 打开, 0 = 关闭
```

`pu_status` 寄存器分布：
- LDO_01 ~ LDO_08 → `0x05F` bit[0..7]
- LDO_09 ~ LDO_15 → `0x060` bit[0..5]

**不读配置位 `pu`**：因为 `pu=1` 但 `pu_dr=0` 时硬件未必真正打开。`pu_status` 才是硬件反馈的真实使能状态。

模式判定（同方法内）：

```python
if lp_dr and lp:        mode = "LP"
elif lp_dr and not lp:  mode = "Normal"
else:                   mode = "Unknown"   # lp_dr=0 表示未驱动, 状态不定
```

### 3. 打开 / 关闭一个 LDO

`set_ldo_enabled(ldo_id, enabled)` 两步写入（顺序固定）：

```
1. write_field(pu_dr, 1)                       # 先置驱动位=1, 允许改 pu
2. write_field(pu,    1 if enabled else 0)     # 再写配置位
```

例：打开 LDO_01

| 步骤 | 寄存器 | 位 | 写入值 |
|---|---|---|---|
| 1 | 0x00D | [13:13] | 1（pu_dr） |
| 2 | 0x00D | [12:12] | 1（pu） |

**注意**：写入后 `pu_status` 可能不会立即更新（硬件 LDO 稳定需要时间）。如需 UI 显示真实状态，应再次点击 **Check** 触发 `read_all_ldos()`。

### 4. 切换模式（Normal ↔ LP）

`set_ldo_mode(ldo_id, mode)` 两步写入：

```
1. write_field(lp_dr, 1)              # 先置驱动位=1
2. write_field(lp,    lp_val)         # Normal=0, LP=1
```

BUCK 类型还声明支持 `ULP`，但 controller 当前只实现 Normal/LP；其他模式值会抛 `ValueError`。

### 5. 设置电压

`set_ldo_voltage(ldo_id, voltage)` 三步：

```
1. vbit = voltage_to_vbit(ldo_id, voltage)    # 查表取最近 vbit
2. write_field(vbit_normal, vbit)             # 写电压控制字
3. if read_field(res_sel_dr) == 0:
       write_field(res_sel_dr, 1)             # 保证生效位=1
```

- 电压 → vbit 映射由 `chips/bes1811_pmu.py::LDO_VOLTAGE_TABLES` 提供
- 表索引即硬件 vbit（**注意是 16 进制**，例如 LDO_01 0.9V 对应 vbit=0x18）
- 写入后 vbit 是「最近邻档位」，与请求电压可能有 ±step/2 误差
- UI 中 `ModuleCard._step` / `PropertyPanel._on_spin` 在发送前已用 `align_to_step` 吸附，所以实际下发的电压永远落在档位上

> **Deep Sleep / RC 电压调整**: 属性面板除 Normal 电压外, 还提供 `Voltage - Deep Sleep (V)` 与 `Voltage - RC (V)` 两个 section, 分别对应 `vbit_dsleep` 与 `vbit_rc`。写入流程与 Normal 完全一致 (查表 → 写 vbit → 置 res_sel_dr=1), 由 `set_ldo_vbit_dsleep` / `set_ldo_vbit_rc` 实现。三档共用同一 `LDO_VOLTAGE_TABLES` 查找表, 因此 `min_voltage` / `max_voltage` / `step` 完全相同。读取流程通过 `read_ldo` 一次读出 3 个 vbit, 并分别查表得到 `voltage` / `voltage_dsleep` / `voltage_rc`。

### 6. 电压范围与档位

来自 `LDO_VOLTAGE_TABLES[ldo_id]` 列表（按 vbit 升序），共 14 个 LDO：

| LDO | 档位数 | 最低电压 | 最高电压 | 平均 step |
|---|---|---|---|---|
| LDO_01 | 64 | 0.3030 V | 1.8864 V | ~25 mV |
| LDO_02 | 11 | 0.8195 V | 1.8051 V | ~99 mV |
| LDO_03 | 11 | 1.1978 V | 2.1926 V | ~99 mV |
| LDO_05 | 26 | 1.2070 V | 3.7120 V | ~100 mV |
| LDO_06 | 26 | 0.5985 V | 1.2188 V | ~25 mV |
| LDO_07 | 184 | 0.5955 V | 1.4990 V | ~5 mV |
| LDO_08 | 183 | 0.5975 V | 1.4997 V | ~5 mV |
| LDO_09 | 240 | 0.8993 V | 2.0905 V | ~5 mV |
| LDO_10 | 246 | 0.9011 V | 2.1186 V | ~5 mV |
| LDO_11 | 256 | 0.9009 V | 2.1737 V | ~5 mV |
| LDO_12 | 32 | 0.3249 V | 1.0990 V | ~25 mV |
| LDO_13 | 29 | 1.2024 V | 4.0004 V | ~100 mV |
| LDO_14 | 32 | 1.2035 V | 4.2989 V | ~100 mV |
| LDO_15 | 32 | 1.1989 V | 4.2852 V | ~100 mV |

**档位分布特征**：
- **~5 mV 细粒度档位**：LDO_07 / 08 / 09 / 10 / 11（180~256 档），适合精细电压调节
- **~25 mV 中粒度档位**：LDO_01 / 06 / 12（26~64 档）
- **~100 mV 粗粒度档位**：LDO_02 / 03 / 05 / 13 / 14 / 15（11~32 档）
- LDO_04 不存在（1811 芯片未定义）
- LDO_VMIC1 / LDO_VMIC2 无寄存器映射（见 §9）

`_default_modules()` 启动时通过 `snap_range_to_step(v_min, v_max, step)` 把范围对齐到 step 整数倍，UI 的 SpinBox/Slider 也以 step 为最小单位。

### 7. 完整读取流程（Check 按钮）

`read_ldo()` 单个 LDO 读取顺序（共 9 次寄存器读 + 1 次条件读）：

1. `pu_status`（决定 `enabled`）
2. `pu`, `pu_dr`（参考用，未直接进 UI）
3. `lp`, `lp_dr`（决定 `mode`）
4. `vbit_normal`（决定 `voltage`，经 `vbit_to_voltage` 查表）
5. `vbit_dsleep`, `vbit_rc`（参考用）
6. `res_sel_dr`（参考用）

`read_all_ldos()` 遍历 `LDO_IDS`（14 个 LDO），单 LDO 异常会被捕获并跳过，不影响其他 LDO。

### 8. 控制位与状态位的语义对照

| 用户意图 | 写哪个位 | 读哪个位验证 |
|---|---|---|
| 打开 LDO | `pu_dr=1` → `pu=1` | `pu_status` 应为 1 |
| 关闭 LDO | `pu_dr=1` → `pu=0` | `pu_status` 应为 0 |
| 切到 LP | `lp_dr=1` → `lp=1` | `lp_dr=1 且 lp=1` |
| 切到 Normal | `lp_dr=1` → `lp=0` | `lp_dr=1 且 lp=0` |
| 改电压 (Normal) | `vbit_normal=vbit` → `res_sel_dr=1` | 重读 `vbit_normal` 验证 |
| 改电压 (Deep Sleep) | `vbit_dsleep=vbit` → `res_sel_dr=1` | 重读 `vbit_dsleep` 验证 |
| 改电压 (RC) | `vbit_rc=vbit` → `res_sel_dr=1` | 重读 `vbit_rc` 验证 |

**写入后 UI 立即更新本地状态**（`PmuModule.enabled / mode / voltage`），但这是「期望状态」；真实硬件状态需 Check 重新读取后才反映到 `pu_status`。这是为什么 `enabled` 字段在写入和读取两条路径上都会被赋值。

### 9. 不支持 I2C 控制的模块

- `LDO_VMIC1` / `LDO_VMIC2` 不在 `LDO_REG_MAPS` 中
- `_default_modules()` 把它们的 `controllable=False`
- UI 上仍会渲染卡片，但 `_start_write` 直接 `return`，不发起 I2C 写入
- 属性面板的 I2C 寄存器区显示 `Address: — (无寄存器映射)`

### 10. BUCK 与 LDO 的差异

| 项 | LDO | BUCK |
|---|---|---|
| 模式列表 | `["Normal", "LP"]` | `["Normal", "LP", "ULP"]`（声明） |
| I2C 控制 | 是 | 否（BUCK_01~06 不在 `LDO_REG_MAPS` 中） |
| 默认电压 | 范围中点偏下 | 1.0 V |
| 画布位置 | L1 或 L2 | 仅 L1（直连 VSYS） |
| 子母线级联 | 无 | `BUCK_01` 级联到 `LDO_12` |

> **注意**：BUCK_01~06 当前未在 `LDO_REG_MAPS` 中，因此 `controllable=False`，UI 上无法通过 I2C 控制它们；仅 `LDO_12` 通过级联关系显示在 BUCK_01 下方。

---

## DCDC

> 规划中：DCDC 模块的使能 / 模式 / 电压设置规则将在此补充。

---

## BUCK

本节描述 6 个 BUCK（BUCK_01~06）的使能与电压控制规则。**模式切换（Normal/LP/ULP）后续补全。**

> **数据来源**:
> - 寄存器位域定义: `userdata/1811 pmu inf reg.xlsx`
> - vbit ↔ 输出电压对应关系: `userdata/1811 DCDCVbit test.xlsx`（每个 BUCK 一个 sheet：`buck1-小bg`~`buck6-小bg`，每个 sheet 256 行 = vbit 0~255 全扫）

> **实现状态**：以下规则为目标语义。`chips/bes1811_pmu.py` 当前仅定义 `LDO_REG_MAPS` / `LDO_VOLTAGE_TABLES`，BUCK_01~06 未在映射表中（`is_ldo_controllable` 返回 `False`），controller 尚未实现 BUCK 读写方法。本节作为后续编码的规格说明。

### 1. 寄存器模型

每个 BUCK 在芯片里有 11 个关键位域（与 LDO 类似, 仅少了 `lp` / `lp_dr` 两个字段; `res_sel_dr` 与 LDO 一样存在; 另有 4 个 BUCK 专用的 `bg_en` / `bg_en_dr` / `sw_en` / `sw_en_dr` 用于调压前置/后置序列, 使能开关和状态寄存器与 LDO 格式相同）：

| 字段 | 位域示例（BUCK_01） | 含义 | 方向 |
|---|---|---|---|
| `pu` | `reg_pu_buck_01` @0x015[0] | 使能配置位（1=打开 / 0=关闭） | RW |
| `pu_dr` | `reg_pu_buck_01_dr` @0x015[1] | 使能驱动位（=1 才允许写 `pu`） | RW |
| `pu_status` | `dig_buck_01_pu` @0x05F[8] | **实际使能状态位**（R，1=打开） | R |
| `vbit_normal` | `reg_buck_01_vbit_normal` @0x046[7:0] | 唤醒模式电压控制字 | RW |
| `vbit_dsleep` | `reg_buck_01_vbit_dsleep` @0x046[15:8] | 睡眠模式电压控制字 | RW |
| `vbit_rc` | `reg_buck_01_vbit_rc[7:0]` @0x074[7:0] | RC 模式电压控制字 | RWS（BUCK_01）/ RW（其余） |
| `res_sel_dr` | `reg_buck_01_res_sel_dr` @0x2F0[0] | 电压调整生效位（=1 才允许 vbit 生效） | RW |
| `bg_en` | `reg_buck_01_bg_en` @0x322[14] | bandgap 使能（调压前置序列用） | RW |
| `bg_en_dr` | `reg_buck_01_bg_en_dr` @0x322[15] | bandgap 使能驱动位（=1 才允许写 `bg_en`） | RW |
| `sw_en` | `reg_buck_01_sw_en` @0x323[14] | switch 使能（调压前置序列用） | RW |
| `sw_en_dr` | `reg_buck_01_sw_en_dr` @0x323[15] | switch 使能驱动位（=1 才允许写 `sw_en`） | RW |

**6 个 BUCK 的位域一览**（地址均为 10 位 I2C 寄存器地址）：

| BUCK | pu_dr @addr[bit] | pu @addr[bit] | pu_status @addr[bit] | vbit_normal @addr[bits] | vbit_dsleep @addr[bits] | vbit_rc @addr[bits] | res_sel_dr @addr[bit] | bg_en @addr[bit] | sw_en @addr[bit] |
|---|---|---|---|---|---|---|---|---|---|
| BUCK_01 | 0x015[1] | 0x015[0] | 0x05F[8] | 0x046[7:0] | 0x046[15:8] | 0x074[7:0] | 0x2F0[0] | 0x322[14] | 0x323[14] |
| BUCK_02 | 0x145[1] | 0x145[0] | 0x05F[9] | 0x146[7:0] | 0x147[7:0] | 0x148[7:0] | 0x2F0[1] | 0x14D[14] | 0x14E[14] |
| BUCK_03 | 0x1E5[1] | 0x1E5[0] | 0x05F[10] | 0x1E6[7:0] | 0x1E7[7:0] | 0x1E8[7:0] | 0x2F0[2] | 0x1ED[14] | 0x1EE[14] |
| BUCK_04 | 0x155[1] | 0x155[0] | 0x05F[11] | 0x156[7:0] | 0x157[7:0] | 0x158[7:0] | 0x2F0[3] | 0x15D[14] | 0x15E[14] |
| BUCK_05 | 0x1D5[1] | 0x1D5[0] | 0x05F[12] | 0x1D6[7:0] | 0x1D7[7:0] | 0x1D8[7:0] | 0x2F0[4] | 0x1DD[14] | 0x1DE[14] |
| BUCK_06 | 0x35F[1] | 0x35F[0] | 0x05F[13] | 0x35A[7:0] | 0x35C[7:0] | 0x35D[7:0] | 0x2F0[5] | 0x31D[14] | 0x31E[14] |

> `bg_en_dr` / `sw_en_dr` 分别与 `bg_en` / `sw_en` 共用同一寄存器, 在 bit[15] (上表略); 详见 §4 的"BUCK 调压序列寄存器"小表。

**关键差异点**：

- **BUCK_01 的 `vbit_normal` 与 `vbit_dsleep` 共用寄存器 0x046**：低字节 [7:0] 为 normal，高字节 [15:8] 为 dsleep；其余 BUCK 都是 3 个独立寄存器
- **BUCK_01 的 `vbit_rc` 寄存器在 0x074**（远离 0x046）；其余 BUCK 的 vbit_rc 与 vbit_normal / vbit_dsleep 在地址上相邻
- **BUCK_06 的 `vbit_dsleep` 地址 0x35C 跳过了 0x35B**（中间空一格）
- **BUCK_01 的 `vbit_rc` 类型为 RWS**（写后自动清零），其余 BUCK 为普通 RW；当前控制流不依赖该差异
- **BUCK_01 的 vbit_rc 位名带 `[7:0]` 后缀**（`reg_buck_01_vbit_rc[7:0]`），是芯片表的命名习惯，不代表位宽不同（实际 REG_BIT 也是 `7:0`）
- **状态位寄存器 0x05F 与 LDO 共用**：bits[0..7] 是 `dig_ldo_01~08_pu`，bits[8..13] 是 `dig_buck_01~06_pu`，bits[14..15] 未定义
- **`res_sel_dr` 与 LDO 共用 0x2F0 寄存器**：BUCK_01~06 占 bit[0..5]，LDO_01~15 占 bit[6..15] 与 0x2F1[0..4]；BUCK 电压写入流程与 LDO 一致（写 vbit_normal 后, 若 `res_sel_dr=0` 则置 1 生效）
- **BUCK 专有 `bg_en` / `sw_en` 调压序列**: LDO 无此字段; BUCK 改电压时需先打开 bandgap + switch, 调完后再关闭 (详见 §4)
- **没有 `lp` / `lp_dr` 字段**：BUCK 的模式切换使用其他寄存器（Normal/LP/ULP 三档），不在本节覆盖

### 2. 使能状态判断

UI 卡片 LED / 属性面板开关状态 = `PmuModule.enabled`，与 LDO 一致由 `dig_buck_XX_pu` 状态位决定。

```python
pu_status = read_field(dig_buck_XX_pu)   # 读 0x05F[8..13]
enabled = bool(pu_status)                  # 1 = 打开, 0 = 关闭
```

`pu_status` 寄存器分布（与 LDO 共用 0x05F）：

- LDO_01 ~ LDO_08 → `0x05F` bit[0..7]
- BUCK_01 ~ BUCK_06 → `0x05F` bit[8..13]

**不读配置位 `pu`**：原因同 LDO，`pu=1` 但 `pu_dr=0` 时硬件未必真正打开。`pu_status` 才是硬件反馈的真实使能状态。

### 3. 打开 / 关闭一个 BUCK

`set_buck_enabled(buck_id, enabled)` 两步写入（顺序固定，与 LDO 完全一致）：

```
1. write_field(pu_dr, 1)                       # 先置驱动位=1, 允许改 pu
2. write_field(pu,    1 if enabled else 0)     # 再写配置位
```

例：打开 BUCK_01

| 步骤 | 寄存器 | 位 | 写入值 |
|---|---|---|---|
| 1 | 0x015 | [1:1] | 1（pu_dr） |
| 2 | 0x015 | [0:0] | 1（pu） |

**注意**：写入后 `pu_status` 可能不会立即更新（硬件 BUCK 稳定需要时间）。如需 UI 显示真实状态，应再次点击 **Check** 触发 `read_all_ldos()`。

### 4. 设置电压

`set_buck_voltage(buck_id, voltage)` 完整 **5 步流程** (BUCK 专用, 与 LDO 不同 — 多了 bg_en / sw_en 前置/后置序列):

```
1. bg_en_dr=1, bg_en=1; delay 1ms           # 打开 bandgap, 等 1ms 稳定
2. sw_en_dr=1, sw_en=1                       # 打开 switch
3. vbit = voltage_to_vbit(buck_id, voltage)  # 查表取最近 vbit
   write_field(vbit_normal, vbit)            # 写电压控制字
   if read_field(res_sel_dr) == 0:
       write_field(res_sel_dr, 1)            # 保证生效位=1 (与 LDO 一致)
4. sw_en_dr=0, sw_en=0; delay 1ms            # 关闭 switch, 等 1ms 稳定
5. bg_en_dr=0, bg_en=0                       # 关闭 bandgap
```

- 步骤 1~2 由 `_buck_voltage_pre_seq` 实现, 步骤 4~5 由 `_buck_voltage_post_seq` 实现, 步骤 3 是核心 vbit 写入 + `res_sel_dr` 生效位
- `bg_en` / `sw_en` 在 `BUCK_REG_MAPS` 中定义为 Optional 字段, LDO 寄存器映射无此字段 (默认 None); 若误调用, 前置/后置序列自动跳过, 退化为 LDO 流程
- delay 用 `time.sleep(_BUCK_SEQ_DELAY_SEC)`, 默认 1 ms (常量在 `Bes1811PmuController` 类属性)
- 电压 → vbit 映射由 `BUCK_VOLTAGE_TABLES[buck_id]` 提供（256 档全扫）
- **vbit 直接作为列表索引**：8 bit = 0~255，全部 256 档均为有效测量值，无 `None` 槽位
- 与 LDO 不同的是，xlsx 中 vbit 列为十进制整数（`Register Value (Dec)`），不需要 `int(str, 16)` 解析
- 写入后 vbit 是「最近邻档位」，与请求电压可能有 ±step/2 误差
- UI 中 `ModuleCard._step` / `PropertyPanel._on_spin` 在发送前已用 `align_to_step` 吸附，所以实际下发的电压永远落在档位上

> **Deep Sleep / RC 电压调整**: 与 Normal 一致, 属性面板也提供 `Voltage - Deep Sleep (V)` / `Voltage - RC (V)` 两个 section, 分别对应 `vbit_dsleep` / `vbit_rc`。写入流程相同 (5 步 bg_en/sw_en 序列 + 写对应 vbit + 置 res_sel_dr=1), 由 `set_buck_vbit_dsleep` / `set_buck_vbit_rc` 实现, 共用 `_buck_voltage_pre_seq` / `_buck_voltage_post_seq`。读取流程通过 `read_buck` 一次读出 3 个 vbit 并分别查表。

**BUCK 调压序列寄存器 (bg_en / sw_en)**:

| BUCK | bg_en_dr @addr[bit] | bg_en @addr[bit] | sw_en_dr @addr[bit] | sw_en @addr[bit] |
|---|---|---|---|---|
| BUCK_01 | 0x322[15] | 0x322[14] | 0x323[15] | 0x323[14] |
| BUCK_02 | 0x14D[15] | 0x14D[14] | 0x14E[15] | 0x14E[14] |
| BUCK_03 | 0x1ED[15] | 0x1ED[14] | 0x1EE[15] | 0x1EE[14] |
| BUCK_04 | 0x15D[15] | 0x15D[14] | 0x15E[15] | 0x15E[14] |
| BUCK_05 | 0x1DD[15] | 0x1DD[14] | 0x1DE[15] | 0x1DE[14] |
| BUCK_06 | 0x31D[15] | 0x31D[14] | 0x31E[15] | 0x31E[14] |

- 每个 BUCK 的 `bg_en` / `bg_en_dr` 共用一个 16-bit 寄存器 (bit[14]=bg_en, bit[15]=bg_en_dr); `sw_en` / `sw_en_dr` 共用下一个寄存器 (bit[14]=sw_en, bit[15]=sw_en_dr)
- 复位默认值: `bg_en=1` / `sw_en=1` / `bg_en_dr=0` / `sw_en_dr=0` (即默认 bg/sw 打开但驱动位=0, 配置不生效)
- 调压流程通过置 `_dr=1` 让配置生效, 调压结束后再置 `_dr=0` 复位

### 5. 电压范围与档位

来自 `BUCK_VOLTAGE_TABLES[buck_id]`（共 256 档，vbit 0~255 连续），实测数据来自 `1811 DCDCVbit test.xlsx` 的 `小bg` 子表：

| BUCK | 档位数 | 最低电压 | 最高电压 | 平均 step |
|---|---|---|---|---|
| BUCK_01 | 256 | 0.3129 V | 1.2340 V | ~3.6 mV |
| BUCK_02 | 256 | 0.6049 V | 2.4727 V | ~7.3 mV |
| BUCK_03 | 256 | 0.6108 V | 2.4843 V | ~7.3 mV |
| BUCK_04 | 256 | 0.3177 V | 1.2421 V | ~3.6 mV |
| BUCK_05 | 256 | 0.3156 V | 1.2486 V | ~3.7 mV |
| BUCK_06 | 256 | 0.3090 V | 1.2293 V | ~3.6 mV |

**档位分布特征**：

- 全部 6 个 BUCK 均为 **8-bit vbit（256 档）**，覆盖完整 0~255 范围
- **BUCK_02 / 03** 是高输出档（最高 2.47~2.48V，~7.3 mV 步进），覆盖范围最广
- **BUCK_01 / 04 / 05 / 06** 是低输出档（最高 1.23~1.25V，~3.6 mV 步进）
- `_default_modules()` 中 BUCK 默认电压 1.0V（落在所有 BUCK 范围内）；`min/max_voltage` 需通过 `snap_range_to_step` 对齐到 step 整数倍

### 6. 完整读取流程

单个 BUCK 读取顺序（共 6 次寄存器读，比 LDO 少 2 次因无 `lp` / `lp_dr`；`res_sel_dr` UI 不展示, 不读）：

1. `pu_status`（决定 `enabled`）
2. `pu`, `pu_dr`（参考用，未直接进 UI）
3. `vbit_normal`（决定 `voltage`，经 `vbit_to_voltage` 查表）
4. `vbit_dsleep`, `vbit_rc`（参考用）

### 7. 控制位与状态位的语义对照

| 用户意图 | 写哪个位 | 读哪个位验证 |
|---|---|---|
| 打开 BUCK | `pu_dr=1` → `pu=1` | `pu_status` 应为 1 |
| 关闭 BUCK | `pu_dr=1` → `pu=0` | `pu_status` 应为 0 |
| 改电压 (Normal) | `vbit_normal=vbit` → `res_sel_dr=1` | 重读 `vbit_normal` 验证 |
| 改电压 (Deep Sleep) | `vbit_dsleep=vbit` → `res_sel_dr=1` | 重读 `vbit_dsleep` 验证 |
| 改电压 (RC) | `vbit_rc=vbit` → `res_sel_dr=1` | 重读 `vbit_rc` 验证 |
| 切模式 | （后续补全） | （后续补全） |

**写入后 UI 立即更新本地状态**（`PmuModule.enabled / voltage`），但这是「期望状态」；真实硬件状态需 Check 重新读取后才反映到 `pu_status`。这是为什么 `enabled` 字段在写入和读取两条路径上都会被赋值。

### 8. BUCK 与 LDO 的差异

| 项 | LDO | BUCK |
|---|---|---|
| 模式列表 | `["Normal", "LP"]` | `["Normal", "LP", "ULP"]`（声明，模式控制后续补全） |
| 寄存器字段数 | 9（含 `lp` / `lp_dr` / `res_sel_dr`） | 11（无 `lp` / `lp_dr`, 有 `res_sel_dr` + 4 个 `bg_en` / `sw_en` 系列） |
| 电压写入流程 | 3 步 (写 vbit → res_sel_dr=1) | **5 步** (bg_en/sw_en 前置 → 写 vbit + res_sel_dr=1 → sw_en/bg_en 后置), 详见 §4 |
| 调压 delay | 无 | 前后各 `time.sleep(1ms)` (bg_en 打开/关闭后) |
| vbit 位宽 | 多数 5~8 bit，档位数 11~256 不等 | 固定 8 bit，全部 256 档连续 |
| vbit 索引进制 | **十六进制**（`LDO_VOLTAGE_TABLES` 索引 = hex vbit，源 xlsx 含 A-F） | **十进制**（`BUCK_VOLTAGE_TABLES` 索引 = dec vbit，源 xlsx 为纯数字） |
| 电压数据来源 | `BES1811 LDO输出电压范围.xlsx` | `1811 DCDCVbit test.xlsx` |
| 状态位分布 | `0x05F[0..7]` + `0x060[0..5]` | `0x05F[8..13]`（与 LDO 共用 0x05F） |
| 默认电压 | 范围中点偏下 | 1.0 V |
| 画布位置 | L1 或 L2 | 仅 L1（直连 VSYS） |
| 子母线级联 | 无 | `BUCK_01` 级联到 `LDO_12` |
| BUCK_01 特例 | — | vbit_normal / vbit_dsleep 共用 0x046；vbit_rc 在 0x074（RWS） |

### 9. 模式切换（Normal / LP / ULP）

> 规划中：BUCK 模式切换的寄存器映射与写入流程将在此补充。当前 BUCK 类型声明支持 `["Normal", "LP", "ULP"]` 三档，但 controller 仅实现 LDO 的 Normal/LP，BUCK 的模式控制尚未实现。

---

## SW

本节描述 7 个 Power Switch（SW1~SW7）的操作语义。SW 是电源开关，仅有**闭合（导通）/ 开路（断开）**两态，无电压 / 模式控制。配置位定义在 `chips/bes1811_pmu.py::SW_REG_MAPS`（`SwRegMap`）。

### 1. 寄存器模型

每个 SW 只有 2 个关键位域（极简，区别于 LDO 9 个 / BUCK 11 个）：

| 字段 | 含义 | 方向 |
|---|---|---|
| `en` | `reg_en_swXX_<domain>` — 使能配置位（1=导通 / 0=断开） | RW |
| `en_dr` | `reg_en_swXX_<domain>_dr` — 使能驱动位（=1 才允许写 `en`） | RW |

**无独立状态位**：区别于 LDO/BUCK 的 `pu_status`（`dig_ldo_XX_pu` / `dig_buck_XX_pu`），SW 没有专用的硬件状态寄存器，闭合/开路状态直接由配置位 `en` 决定。

**7 个 SW 的位域一览**（10 位 I2C 寄存器地址）：

| SW | 域 | en @addr[bit] | en_dr @addr[bit] | VIN 节点 | Rdson/mΩ |
|---|---|---|---|---|---|
| SW1 | 1p8 | 0x063[15] | 0x063[14] | LDO_01&BUCK_01 | 1994.553028 |
| SW2 | 1p8 | 0x063[13] | 0x063[12] | LDO_02&BUCK_02 | 506.7093932 |
| SW3 | 1p8 | 0x063[11] | 0x063[10] | LDO_03&BUCK_03 | 412.5445588 |
| SW4 | 1p8 | 0x063[9] | 0x063[8] | LDO_03&BUCK_03 | 823.587135 |
| SW5 | vusb33 | 0x06B[1] | 0x06B[0] | LDO_13 | 861.1453233 |
| SW6 | vusb33 | 0x06B[9] | 0x06B[8] | LDO_13 | 1427.899106 |
| SW7 | 1p8 | 0x06C[3] | 0x06C[2] | LDO_01&BUCK_01 | 1504.332478 |

> **域说明**：`1p8` = 1.8V 域（SW1~SW4 / SW7，寄存器 0x063 / 0x06C）；`vusb33` = 3.3V 域（SW5~SW6，寄存器 0x06B）。源 CSV 中字段名为 `reg_en_sw5_vusb33` / `reg_en_sw6_vusb33`（`vusb33`，非 `vsub33`）。
>
> **地址分布特征**：SW1~SW4 共用寄存器 0x063（各占 2 bit，含 `en` + `en_dr` + `pull_down`）；SW5~SW6 共用 0x06B；SW7 单独在 0x06C。

### 2. 闭合/开路状态判断

UI 卡片 LED / 属性面板开关状态 = `PmuModule.enabled`（True=闭合 / False=开路），由 `read_sw()` 返回。

判定依据（`core/bes1811_pmu_controller.py::read_sw`）：

```python
en = read_field(reg_en_swXX_<domain>)     # 读使能配置位
enabled = bool(en)                          # 1 = 闭合, 0 = 开路
```

**与 LDO/BUCK 的关键差异**：LDO/BUCK 读 `pu_status` 状态位（硬件反馈真实使能），SW 直接读 `en` 配置位（无独立状态位）。`en_dr=0` 时 `en` 配置不生效（软件释放，由硬件默认/自动控制），当前按 `en` 值显示，其语义后续讨论。

### 3. 强制闭合 / 强制开路

`set_sw_enabled(sw_id, closed)` 两步写入（顺序固定，与 LDO 的 `pu_dr→pu` 模式一致）：

```
1. write_field(en_dr, 1)                      # 先置驱动位=1, 允许改 en
2. write_field(en,    1 if closed else 0)     # 再写配置位 (闭合=1 / 开路=0)
```

例：强制闭合 SW1

| 步骤 | 寄存器 | 位 | 写入值 |
|---|---|---|---|
| 1 | 0x063 | [14:14] | 1（en_dr） |
| 2 | 0x063 | [15:15] | 1（en，闭合） |

强制开路 SW1：步骤 2 写 `en=0`。

### 4. 四种 (en_dr, en) 组合

| en_dr | en | 语义 | 当前实现 |
|---|---|---|---|
| 1 | 1 | 强制导通（闭合） | ✅ `set_sw_enabled(True)` |
| 1 | 0 | 强制开路（断开） | ✅ `set_sw_enabled(False)` |
| 0 | 0 | 软件释放（硬件默认） | ⏳ 后续讨论 |
| 0 | 1 | 软件释放（硬件默认） | ⏳ 后续讨论 |

> `en_dr=0` 的两种组合表示软件不驱动，由硬件默认/自动控制；其具体语义与 UI 呈现方式后续讨论。

### 5. SW 与 LDO/BUCK 的差异

| 项 | LDO | BUCK | SW |
|---|---|---|---|
| 状态位 | `pu_status`（dig_ldo_XX_pu） | `pu_status`（dig_buck_XX_pu） | 无（直接读 `en` 配置位） |
| 模式 | Normal/LP | Normal/LP/ULP（声明） | 无（仅闭合/开路两态） |
| 电压 | vbit_normal/dsleep/rc | vbit_normal/dsleep/rc | 无（导通时直通输入轨） |
| 寄存器字段数 | 9 | 11 | 2（en / en_dr） |
| UI 卡片 | 显示电压 +/− 步进 | 显示电压 +/− 步进 | ToggleSwitch 开关 (闭合=绿/开路=灰) |
| 属性面板 | 使能 + 模式 + 三档电压 | 使能 + 模式 + 三档电压 | 开关态 + Rdson + 输入/输出节点 |
| 画布连线 | VSYS 琥珀 / 子母线蓝 | VSYS 琥珀 | 对偶源(L2): 与 L2 共享蓝色干线, 分支玫红; 单模块源(L3): SW_BUS_X 竖线引至 L3 |
| 类型主题色 | 天蓝 `#38bdf8` | 琥珀 `#f59e0b` | 玫红 `#ec4899` |

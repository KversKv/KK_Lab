# 1811 PMU 操作规则集合

本文件汇总 1811 PMIC 各类模块（LDO / DCDC / BUCK 等）的实际硬件操作语义：使能状态如何判断、如何打开/关闭一个模块、如何切换模式与电压。所有底层操作由 `core/bes1811_pmu_controller.py::Bes1811PmuController` 实现，配置位定义在 `chips/bes1811_pmu.py`。

> 配套阅读：[README.md](./README.md) — 模块整体架构与分层。

## 目录

- [LDO](#ldo)
- [DCDC](#dcdc)（规划中）
- [BUCK](#buck)（规划中）

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

### 6. 电压范围与档位

来自 `LDO_VOLTAGE_TABLES[ldo_id]` 列表（按 vbit 升序）：

| LDO | 档位数 | 最低电压 | 最高电压 | 平均 step |
|---|---|---|---|---|
| LDO_01 | 64 (0x00–0x3F) | 0.3030 V | 1.8864 V | ~25 mV |
| LDO_02 | 11 | 0.8195 V | 1.8051 V | ~100 mV |
| LDO_05 | 26 | 1.2070 V | 3.7120 V | ~100 mV |
| LDO_07 | 200 | 0.5955 V | 1.4990 V | ~4.5 mV |
| LDO_12 | 32 | 0.3249 V | 1.0990 V | ~25 mV |
| LDO_13 | 29 | 1.2024 V | 4.0004 V | ~100 mV |
| LDO_14 | 32 | 1.2035 V | 4.2989 V | ~100 mV |
| ... | ... | ... | ... | ... |

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
| 改电压 | `vbit_normal=vbit` → `res_sel_dr=1` | 重读 `vbit_normal` 验证 |

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

> 规划中：BUCK_01~06 当前未在 `LDO_REG_MAPS` 中，无 I2C 控制；若后续支持，规则将在此补充。

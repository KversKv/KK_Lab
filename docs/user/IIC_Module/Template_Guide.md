# I2C 模板（Template）规则与编写指南

> 适用版本：KK_Lab IIC Module `MODULE_VERSION = 0.0.0`
>
> 本文面向使用者，说明 I2C 模块中 Template 的存储位置、JSON 结构、字段语义、位宽/速率约束、位域（bit_fields）规则，以及如何通过 UI 或手工编写一份合法可复用的模板。

---

## 1. 模板的作用

Template 是一份「设备寄存器映射描述文件」，用于把一次调试会话中的关键参数固化为可复用配置：

- 绑定 **设备地址 + 速率 + 位宽** 三项基础参数，避免每次手输。
- 预定义一组 **寄存器（registers）**，每个寄存器下可挂载若干 **位域（bit_fields）**。
- 在 `Sequence Script` 中可按模板名关联脚本，便于按芯片/项目组织脚本集。
- 模板切换会自动联动 Device Addr、Data Width、Speed、Reg Addr 与位表字段。

模板与脚本关系：模板负责「这是什么设备 / 寄存器长什么样」，脚本负责「按什么顺序读写」。两者均可独立存在，但推荐脚本通过 `template` 字段挂到一个模板上以便过滤。

---

## 2. 文件存储位置

| 项 | 路径 | 说明 |
|---|---|---|
| 模板目录 | `user_data/i2c_templates/` | 由 `get_user_data_dir("i2c_templates")` 解析，跨用户隔离 |
| 单文件命名 | `<safe_name>.json` | `safe_name` 由模板 `name` 经 `re.sub(r'[^\w\-.]', '_', name)` 生成 |
| 文件格式 | UTF-8 编码 JSON，缩进 2 空格，`ensure_ascii=False` | 支持中文字段值 |
| 状态文件 | `user_data/i2c_state/i2c_state.json` | 仅记录上次使用的模板名 / 速率 / 位宽等，不复制模板内容 |

> 打包后路径仍走 `get_user_data_dir`，与开发期一致；不要把模板放到 `lib/i2c/config/` 下，那是 DLL 与 eFuse Python 脚本的目录。

---

## 3. JSON 顶层结构

```json
{
  "name": "BES1503P_PMU",
  "device_addr": "0x27",
  "speed_mode": 1,
  "data_bits": 16,
  "reg_bits": 16,
  "registers": [ ... ]
}
```

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `name` | string | 是 | — | 模板显示名，同时用于生成文件名与脚本过滤键 |
| `device_addr` | string | 是 | `"0x00"` | 7-bit I2C 设备地址，**十六进制字符串**，最多 2 位 hex（`0x00`–`0x7F`） |
| `speed_mode` | int | 是 | `1` | `I2CSpeedMode` 枚举值，见下表 |
| `data_bits` | int | 是 | `16` | 单次读写的数据位宽，可选 `8 / 16 / 32` |
| `reg_bits` | int | 否 | 由 `data_bits` 推断 | 寄存器地址位宽，可选 `8 / 16 / 32`；旧文件未写时按 `_infer_reg_bits` 推断 |
| `registers` | array | 是 | `[]` | 寄存器列表，至少 1 条；空数组会在保存时被 UI 自动补一条 `REG0` |

### 3.1 `speed_mode` 取值

| 枚举名 | 值 | 含义 |
|---|---|---|
| `SPEED_20K` | 0 | 20 kHz |
| `SPEED_100K` | 1 | 100 kHz（标准模式，默认） |
| `SPEED_400K` | 2 | 400 kHz（快速模式） |
| `SPEED_750K` | 3 | 750 kHz |

### 3.2 `data_bits` × `reg_bits` 合法组合

UI 仅允许以下四种组合，超出会被拒绝：

| 显示文本 | `reg_bits` | `data_bits` | 底层 `I2CWidthFlag` |
|---|---|---|---|
| `8R / 8D` | 8 | 8 | `BIT_8`（读后掩码到 8 位） |
| `8R / 16D` | 8 | 16 | `BIT_8` |
| `16R / 16D` | 16 | 16 | `BIT_10` |
| `32R / 32D` | 32 | 32 | `BIT_32` |

> `BIT_10` 实为「16 位寄存器地址 + 16 位数据」，并非字面 10 位。底层 DLL 原生仅支持这三种 width flag，`8R/8D` 是在 `BIT_8` 基础上读后掩码实现的。

### 3.3 `device_addr` 格式

- 字符串形式，必须可被 `_parse_hex_int` 解析：
  - 允许 `0x` 前缀（推荐）：`"0x27"`
  - 允许纯 hex 字符串：`"27"`
  - 允许前导负号（不建议）：`"-0x10"`
- 范围限制 7-bit：`0x00`–`0x7F`（UI `HexLineEdit(bit_count=7)` 会自动掩码）。
- 不允许写十进制数字字符串如 `"39"`，会被按十六进制解析成 `0x39`。

---

## 4. `registers` 数组

```json
"registers": [
  {
    "name": "PMU_CTRL",
    "reg_addr": "0x0001",
    "data_bits": 16,
    "reg_bits": 16,
    "description": "PMU 使能寄存器",
    "bit_fields": [ ... ]
  },
  {
    "name": "PMU_STATUS",
    "reg_addr": "0x0002",
    "data_bits": 16,
    "reg_bits": 16,
    "description": "PMU 状态寄存器",
    "bit_fields": [ ... ]
  }
]
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | 寄存器显示名，建议大写下划线：`PMU_CTRL` |
| `reg_addr` | string | 是 | 寄存器地址，**十六进制字符串**；位宽需匹配模板 `reg_bits`（`8R` → 2 位 hex，`16R` → 4 位 hex，`32R` → 8 位 hex） |
| `data_bits` | int | 否 | 该寄存器数据位宽，缺省时回退到模板顶层 `data_bits` |
| `reg_bits` | int | 否 | 该寄存器地址位宽，缺省时回退到模板顶层 `reg_bits` |
| `description` | string | 否 | 自由文本描述 |
| `bit_fields` | array | 否 | 位域列表，可为空数组或省略 |

> 当前 UI 加载模板时仅把第一个寄存器载入工作区，后续寄存器在内存中保留但暂未在主工作区切换。手工编写时仍应把所有寄存器列出，便于后续 UI 扩展。

---

## 5. `bit_fields` 数组

```json
"bit_fields": [
  {
    "name": "EN",
    "high_bit": 0,
    "low_bit": 0,
    "description": "PMU 使能位"
  },
  {
    "name": "MODE",
    "high_bit": 3,
    "low_bit": 1,
    "description": "工作模式 0=Buck 1=Boost 2=Bypass"
  },
  {
    "name": "VDAC",
    "high_bit": 15,
    "low_bit": 8,
    "description": "VDAC 基准"
  }
]
```

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|---|---|---|
| `name` | string | 是 | 非空 | 位域名，UI 会显示在位表第 2 列 |
| `high_bit` | int | 是 | `0 ≤ high_bit < data_bits` | 位域高位 |
| `low_bit` | int | 是 | `0 ≤ low_bit < data_bits` | 位域低位 |
| `description` | string | 否 | — | 自由文本，UI 显示在位表第 3 列 |

### 5.1 位编号约定

- **LSB = bit 0**，MSB = `data_bits - 1`。
- `high_bit ≥ low_bit`，方向不可反；若 `high_bit < low_bit` UI 仍接受但语义错误。
- 允许 `high_bit == low_bit` 表示单 bit 字段。
- 不同字段允许位重叠（不做冲突检测），由用户自行保证语义正确。

### 5.2 字段值提取规则

UI 通过 `(value >> low_bit) & ((1 << (high_bit - low_bit + 1)) - 1)` 从当前 `Data Value` 中提取每个字段的当前值，并以 hex 显示在位表上。模板文件本身不存字段值，只存结构。

---

## 6. 完整示例

### 6.1 最小可用模板

```json
{
  "name": "Minimal",
  "device_addr": "0x50",
  "speed_mode": 1,
  "data_bits": 16,
  "reg_bits": 16,
  "registers": [
    {
      "name": "REG0",
      "reg_addr": "0x0000",
      "data_bits": 16,
      "reg_bits": 16,
      "description": "",
      "bit_fields": []
    }
  ]
}
```

### 6.2 EEPROM 24C02 模板（8R/8D）

```json
{
  "name": "EEPROM_24C02",
  "device_addr": "0x50",
  "speed_mode": 1,
  "data_bits": 8,
  "reg_bits": 8,
  "registers": [
    {
      "name": "BYTE0",
      "reg_addr": "0x00",
      "data_bits": 8,
      "reg_bits": 8,
      "description": "首字节",
      "bit_fields": []
    },
    {
      "name": "BYTE1",
      "reg_addr": "0x01",
      "data_bits": 8,
      "reg_bits": 8,
      "description": "第二字节",
      "bit_fields": []
    }
  ]
}
```

### 6.3 BES PMU 寄存器模板（16R/16D，含位域）

```json
{
  "name": "BES1503P_PMU",
  "device_addr": "0x27",
  "speed_mode": 1,
  "data_bits": 16,
  "reg_bits": 16,
  "registers": [
    {
      "name": "PMU_PWR_CTRL",
      "reg_addr": "0x0001",
      "data_bits": 16,
      "reg_bits": 16,
      "description": "PMU 电源控制",
      "bit_fields": [
        {"name": "EN",       "high_bit": 0,  "low_bit": 0,  "description": "PMU 使能"},
        {"name": "MODE",     "high_bit": 3,  "low_bit": 1,  "description": "0=Buck 1=Boost 2=Bypass"},
        {"name": "VDAC",      "high_bit": 11, "low_bit": 4,  "description": "VDAC 基准"},
        {"name": "OC_I_LIM", "high_bit": 15, "low_bit": 12, "description": "限流档位"}
      ]
    },
    {
      "name": "PMU_STATUS",
      "reg_addr": "0x0002",
      "data_bits": 16,
      "reg_bits": 16,
      "description": "PMU 状态",
      "bit_fields": [
        {"name": "PG",     "high_bit": 0, "low_bit": 0, "description": "Power Good"},
        {"name": "OCP",    "high_bit": 1, "low_bit": 1, "description": "过流保护触发"},
        {"name": "OVP",    "high_bit": 2, "low_bit": 2, "description": "过压保护触发"},
        {"name": "THERM",  "high_bit": 3, "low_bit": 3, "description": "过温告警"}
      ]
    }
  ]
}
```

### 6.4 32-bit 寄存器模板（32R/32D）

```json
{
  "name": "SOC_PLL_CFG",
  "device_addr": "0x40",
  "speed_mode": 2,
  "data_bits": 32,
  "reg_bits": 32,
  "registers": [
    {
      "name": "PLL_CTRL",
      "reg_addr": "0x00001000",
      "data_bits": 32,
      "reg_bits": 32,
      "description": "PLL 控制寄存器",
      "bit_fields": [
        {"name": "EN",      "high_bit": 0,  "low_bit": 0,  "description": "PLL 使能"},
        {"name": "BYPASS",  "high_bit": 1,  "low_bit": 1,  "description": "旁路"},
        {"name": "DIV_INT", "high_bit": 15, "low_bit": 2,  "description": "整数分频"},
        {"name": "DIV_FRAC","high_bit": 31, "low_bit": 16, "description": "小数分频"}
      ]
    }
  ]
}
```

---

## 7. UI 操作流程

### 7.1 新建模板（推荐路径）

1. 进入 **Control** 页。
2. 在 **Device Config** 卡片填写 `Device Addr` 与选择 `Data Width`。
3. 在 **Template** 卡片把下拉框选为 `(none)`。
4. 打开右侧 **Edit** 开关 → 位表进入可编辑状态：
   - 点 `+ Field` 添加默认字段（覆盖 `[7:0]`）。
   - 在位表上右键某 bit → `Create Field` 创建单 bit 字段。
   - 已有字段上右键 → `Edit Range` / `Delete Field`。
   - 双击位表第 2/3 列单元格可直接改 `name` / `description`。
5. 调整 `Reg Addr`（位表上方 Footer 区域）。
6. 点击 **Save** → 弹出输入框填模板名 → 写入 `user_data/i2c_templates/<name>.json`。

### 7.2 修改已有模板

1. 模板下拉选中目标模板（自动加载到工作区）。
2. 打开 **Edit** 开关，按需修改字段、位宽、设备地址、速率。
3. **Save** 覆盖原文件；如需另存改名，先 `(none)` → Edit → 改字段 → Save 输入新名。

### 7.3 导入 / 导出

- **Open** 按钮：从外部 JSON 文件导入（会复制一份到 `i2c_templates/` 目录）。
- **Export** 按钮：把当前模板导出到任意路径（默认 `i2c_templates/<name>.json`）。

### 7.4 切换模板的副作用

切换模板会触发以下 UI 同步（顺序固定）：

1. `_i2c_registers` 被深拷贝替换。
2. `speed_mode` 写入 Settings 页的 Speed combo（信号被阻塞，不触发副作用）。
3. `_i2c_set_width(reg_bits, data_bits)` 切换位宽，同步 Reg/Data 输入框、位表。
4. `device_addr` 写入 Device Addr 输入框。
5. 第一个寄存器的 `reg_addr` + `bit_fields` 加载到工作区。
6. 脚本列表按新模板名重新过滤（若 Linked Only 开启）。

---

## 8. 编写 Checklist

写完一份模板后请逐项核对：

- [ ] `name` 非空且不含 `\ / : * ? " < > |` 等非法字符（会被替换为 `_`）。
- [ ] `device_addr` 是 `0x` 前缀的 2 位 hex，`0x00`–`0x7F`。
- [ ] `speed_mode` ∈ {0, 1, 2, 3}。
- [ ] `data_bits` 与 `reg_bits` 在四种合法组合中。
- [ ] `registers` 至少 1 条。
- [ ] 每条寄存器 `reg_addr` 的 hex 位数与 `reg_bits` 匹配（`8R` → 2 位，`16R` → 4 位，`32R` → 8 位）。
- [ ] `bit_fields` 中 `high_bit ≥ low_bit`，且均 `< data_bits`。
- [ ] 文件以 UTF-8 + 缩进 2 空格保存，扩展名 `.json`。
- [ ] 如需被脚本关联，`name` 与脚本 YAML 中的 `template` 字段严格一致（大小写敏感）。

---

## 9. 常见错误

| 现象 | 原因 | 解决 |
|---|---|---|
| 模板下拉里看不到新模板 | 文件不在 `i2c_templates/` 或扩展名不是 `.json` | 移到目录内，刷新列表（重新点开下拉） |
| 加载后位宽错乱 | `data_bits/reg_bits` 写了非法组合如 `(8, 32)` | 改为四种合法组合之一 |
| `reg_addr` 显示异常 | hex 位数与 `reg_bits` 不匹配，或写了十进制字符串 | 全部用 `0x` 前缀，位数补齐 |
| 切到模板后脚本列表空 | Linked Only 开启但脚本 `template` 字段与模板名不一致 | 关闭 Linked Only 或修正脚本 `template` 字段 |
| 保存后字段丢失 | `bit_fields` 没写在 `registers[i]` 下而是写在了顶层 | 移到寄存器对象内 |
| 字段 hex 值显示为 `0x????` | `high_bit/low_bit` 超出 `data_bits` 范围 | 校正为 `0 ≤ bit < data_bits` |

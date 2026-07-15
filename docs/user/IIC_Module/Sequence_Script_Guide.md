# I2C 序列脚本（Sequence Script）规则与编写指南

> 适用版本：KK_Lab IIC Module `MODULE_VERSION = 0.0.0`
>
> 本文面向使用者，说明 I2C 模块中 Sequence Script 的存储位置、YAML 结构、DSL 指令语法、变量与表达式、循环/条件/批量读取用法，以及如何通过 UI 或手工编写一份合法可执行的脚本。

---

## 1. 脚本的作用

Sequence Script 是一份「按顺序执行的 I2C 操作清单」，用一条条 DSL 指令描述读/写/位写/延时/批量读/循环/条件，由 `_I2cSequenceWorker` 在独立 `QThread` 中解析执行，全程不阻塞 UI，日志实时回显到底部 `ExecutionLogsFrame`。

与 Template 的关系：

- Template 描述「设备长什么样」（地址、位宽、寄存器、位域）。
- Script 描述「按什么顺序操作设备」。
- 多个脚本组织成一个**集合（Collection）**存放在一个 YAML 文件里，便于按芯片/模板集中维护。
- 脚本可通过 `template` 字段挂到一个模板名上，便于在 UI 列表中按模板过滤；建议集合文件名与模板名一致。

---

## 2. 文件存储位置（集合架构）

一个 YAML 文件 = 一个**脚本集合（Collection）**，可含多个脚本，便于按芯片/模板集中维护。

| 项 | 路径 | 说明 |
|---|---|---|
| 脚本目录 | `user_data/i2c_sequences/` | 由 `get_user_data_dir("i2c_sequences")` 解析 |
| 集合文件命名 | `<collection_name>.yaml` | `collection_name` 经 `re.sub(r'[^\w\-.]', '_', name)` 生成安全文件名 |
| 文件格式 | UTF-8 YAML，`default_flow_style=False`，`sort_keys=False` | 由 PyYAML 序列化，保留中文字段值与字段顺序 |
| 依赖 | 需要安装 `PyYAML`；未安装时列表为空且无法保存 | `_yaml is None` 时所有读写静默失败 |

> **集合与模板的对应约定**：默认按模板名分文件，例如模板 `SY6105` 的所有脚本放在 `SY6105.yaml` 内。这并非强制——一个集合可含不同 `template` 的脚本，但按模板分文件最利于维护。

### 2.1 向后兼容（旧单脚本文件）

加载器对旧格式自动兼容：若 YAML 顶层**没有** `scripts` 键，则把整个顶层视为单个脚本，包装成只含 1 个脚本的集合（集合名取 `template` 或 `name`）。旧文件无需手动迁移，但建议逐步迁移到集合格式。

### 2.2 目录结构示例

```
user_data/i2c_sequences/
├── SY6105.yaml          # 集合：SY6105 充电器全部脚本
├── BES1503P_PMU.yaml            # 集合：PMU 全部脚本
└── EEPROM_24C02.yaml            # 集合：EEPROM 全部脚本
```

---

## 3. YAML 结构

### 3.1 集合文件顶层结构

```yaml
name: SY6105              # 集合名（= 文件名，用于 UI 列表 Collection 列）
description: SY6105 充电器序列脚本集合
scripts:                           # 脚本列表，每项是一个脚本 dict
  - name: SY6105_ReadStatus
    description: 读取芯片ID及状态寄存器
    template: SY6105
    commands:
      - READ 0x0C TO $id
      - READ 0x08 TO $stat0
  - name: SY6105_Init
    description: 上电初始化
    template: SY6105
    commands:
      - WRITE 0x02 0x40
      - DELAY 10
```

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `name` | string | 是 | `""` | 集合名，同时用于生成文件名；建议与模板名一致 |
| `description` | string | 否 | `""` | 集合说明 |
| `scripts` | list[dict] | 是 | `[]` | 脚本列表；空集合加载时会被忽略 |

### 3.2 单个脚本字段（`scripts` 列表元素）

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `name` | string | 是 | `""` | 脚本显示名；在**同一集合内**必须唯一 |
| `description` | string | 否 | `""` | 自由文本描述 |
| `template` | string | 否 | `""` | 关联模板名，用于 UI 过滤；大小写敏感；为空或不匹配时仍可执行 |
| `commands` | list[string] | 是 | `[]` | 指令列表，每条是一行 DSL；空列表执行时提示「脚本为空」 |

> `commands` 必须是字符串数组。即使写整数也会被强转 `str(c)`，但推荐显式写字符串以便 YAML 高亮。

### 3.3 脚本唯一标识

脚本的唯一标识为 **(集合名, 脚本名)**。不同集合可有同名脚本。UI 保存时按此规则 upsert：同一集合内同名脚本会被覆盖，不同集合互不影响。

---

## 4. DSL 指令集

### 4.1 指令总览

| 指令 | 语法 | 作用 | 表格 Action |
|---|---|---|---|
| `WRITE` | `WRITE <addr> <value>` | 全寄存器写入 | `W` |
| `READ` | `READ <addr> [TO $var]` | 读取，可写入变量 | `R` |
| `WRITE_BITS` | `WRITE_BITS <addr> <high> <low> <value>` | 位域写入 | `WR` |
| `DELAY` | `DELAY <ms>` | 延时 | `DELAY` |
| `READ_RANGE` | `READ_RANGE <start> <stop> [step] [delay]` | 批量读取连续地址 | `READ_RANGE` |
| `LOOP` | `LOOP <count>` ... `END_LOOP` | 循环块 | `LOOP` / `END_LOOP` |
| `IF` | `IF <condition>` ... `END_IF` | 条件块 | `IF` / `END_IF` |

### 4.2 数值字面量解析规则

DSL 解析分两层：解析期（`_parse_dsl_line`）只切 token，执行期（`_resolve_token`）才把 token 转 int。执行期按字段默认进制：

| 字段 | 默认进制 | 示例 |
|---|---|---|
| `addr` / `reg_addr` / `start` / `stop` / `value` | 16 进制 | `WRITE 0x10 0xFF`、`WRITE 10 FF` 均等价 |
| `high` / `low`（位号） | 10 进制 | `WRITE_BITS 0x01 7 0 0x02` 中 7/0 是十进制 |
| `ms`（延时） | 10 进制 | `DELAY 100` 表示 100 毫秒 |
| `step`（步长） | 10 进制 | `READ_RANGE 0x00 0x0F 1 10` 中 1 是十进制 |
| `count`（LOOP 次数） | 10 进制 | `LOOP 3` |

强制规则：

- `0x` / `0X` 前缀 → 一律按十六进制（覆盖默认进制）。
- `$` 前缀 → 变量引用（见下一节）。
- 负数字面量仅在变量场景出现（如 `$x` 可能 < 0），指令参数不建议写负数字面量。

### 4.3 变量

- 声明：通过 `READ <addr> TO $var` 把读到的值写入变量。
- 引用：`$var`，未声明变量默认值为 `0`。
- 作用域：单次脚本执行全局共享，LOOP / IF 块内外同名变量互通。
- 变量值来源：只有 `READ ... TO $var`，无 `LET` / `SET` 赋值指令（保持 DSL 极简）。

```yaml
- READ 0x0002 TO $status
- IF $status == 0x0001
- WRITE 0x0003 0xAA
- END_IF
```

### 4.4 注释

- `#` 行首整行注释：从行首 `#` 开始到行尾，整行跳过。
- `//` 行内注释：从 `//` 开始到行尾，剩余部分被剥离。
- `-` 列表标记：行首的 `-` 会被剥除（兼容 YAML list 语法）。

```yaml
- # 这是一条整行注释
- WRITE 0x00 0x01 // 行内注释：写使能位
- - WRITE 0x01 0x02  # 也会被识别（行首 - 被剥）
```

---

## 5. 指令详解

### 5.1 WRITE — 全寄存器写

```
WRITE <addr> <value>
```

- `addr`：寄存器地址，默认 16 进制，位宽取自模板/当前 width。
- `value`：写入数据，默认 16 进制，位宽取自模板/当前 `data_bits`。
- 等价底层调用：`i2c.write(dev, addr, value, width, -1, -1)`（`high=low=-1` 表示非位写）。
- 执行日志：`WRITE addr=0x01 = 0x0001`。

```
WRITE 0x0001 0x0001
WRITE 0x10 0xFF      # addr=0x10, data=0xFF
```

### 5.2 READ — 单次读

```
READ <addr>
READ <addr> TO $var
```

- 不带 `TO`：读取后仅打日志，不保存。
- 带 `TO $var`：把读到的值写入变量，供后续 `IF` / 表达式使用。
- 执行日志：
  - 无变量：`READ addr=0x01 => 0x0001 (1)`
  - 有变量：`READ addr=0x01 => 0x0001 (1) -> $status`

```
- READ 0x0002 TO $status
- READ 0x0010
```

### 5.3 WRITE_BITS — 位域写

```
WRITE_BITS <addr> <high> <low> <value>
```

- `high` / `low`：位号，**十进制**，范围 `0 ≤ bit < data_bits`。
- `value`：要写入该位域的值，**16 进制**，会被自动左移 `low` 位并与原值合并。
- 等价底层调用：`i2c.write(dev, addr, value, width, high, low)`（DLL 内部按 read-modify-write 实现，仅修改 `[high:low]` 区间，其他位保持原值）。
- 执行日志：`WRITE_BITS addr=0x01 [3:0] = 0x0002`。

```
- WRITE_BITS 0x0001 7 0 0x55    # 写 [7:0] = 0x55
- WRITE_BITS 0x0001 3 0 0x02    # 写 [3:0] = 0x02
- WRITE_BITS 0x01 0 0 0x01      # 单 bit：bit0 = 1
```

> 与 `WRITE` 区别：`WRITE` 覆盖整个寄存器，`WRITE_BITS` 仅修改指定位区间，其余位由 DLL 在硬件层 read-modify-write 保持。

### 5.4 DELAY — 延时

```
DELAY <ms>
```

- `ms`：毫秒数，**十进制**，会被 `max(0, ms)` 保护。
- 实现方式：`QThread.msleep(ms)`，在 worker 线程中阻塞，不影响 UI 线程。
- 执行日志：`DELAY 100 ms`。

```
- DELAY 100
- DELAY 0      # 等同空指令
```

### 5.5 READ_RANGE — 批量读

```
READ_RANGE <start> <stop> [step] [delay]
```

- `start` / `stop`：起止寄存器地址，**16 进制**，含两端，必须 `start ≤ stop`。
- `step`：步长，**十进制**，默认 `1`；`step ≤ 0` 时按 `1` 处理。
- `delay`：每次读取之间的延时毫秒，**十进制**，默认 `0`。
- 实现：从 `start` 到 `stop`，每次 `addr += step`，读到 `addr > stop` 停止；`delay > 0` 且未到末尾时插入 `msleep(delay)`。
- 执行日志：
  - 头行：`READ_RANGE 0x00..0x0F step=1 delay=10ms`
  - 每行：`  0x00 => 0x1234 (4660)`

```
- READ_RANGE 0x0000 0x000F 1 10
- READ_RANGE 0x00 0xFF            # step=1, delay=0
- READ_RANGE 0x00 0x10 2          # 读 0,2,4,...,16
```

### 5.6 LOOP / END_LOOP — 循环

```
LOOP <count>
  ...body...
END_LOOP
```

- `count`：循环次数，**十进制**；可为变量如 `LOOP $N`。
- 嵌套：支持任意层嵌套，每个 `LOOP` 必须配一个 `END_LOOP`，否则报错 `LOOP 缺少 END_LOOP`。
- 执行日志：
  - 进入：`LOOP x3`
  - 每轮：`[1/3] ...`、`[2/3] ...`、`[3/3] ...`
- 中断：用户点 Stop 或 `count ≤ 0` 时立即退出当前及所有外层循环。

```
- LOOP 3
- WRITE 0x0001 0x01
- DELAY 50
- READ 0x0002
- END_LOOP
- LOOP $N
- READ 0x0010 TO $v
- END_LOOP
```

### 5.7 IF / END_IF — 条件

```
IF <condition>
  ...body...
END_IF
```

- `condition`：表达式，见下一节「条件表达式」。
- 仅当条件为真时执行 body；不支持 `ELSE`（如需二分支，写两个互补 `IF`）。
- 嵌套：可与 `LOOP` 任意嵌套，但每个 `IF` 必须配一个 `END_IF`。
- 执行日志：IF 本身不打日志；若条件中含 `READ <addr>`，会输出 `(IF-READ addr=... => ...)`。

```
- READ 0x0002 TO $status
- IF $status & 0x0001
- WRITE 0x0003 0xAA
- END_IF
- IF $status == 0
- WRITE 0x0003 0xBB
- END_IF
```

---

## 6. 条件表达式

### 6.1 表达式原子

| 形式 | 含义 | 示例 |
|---|---|---|
| `$var` | 变量值，未定义为 0 | `$status` |
| `0x...` | 十六进制字面量 | `0x0001` |
| `<digits>` | 默认十六进制字面量 | `1` 等价 `0x1` |
| `READ <addr>` | 现场读取，返回结果 | `READ 0x0002` |

### 6.2 操作符

按优先级从高到低匹配（先双字符再单字符，先匹配带空格形式）：

| 操作符 | 语义 | 返回 bool |
|---|---|---|
| `==` | 相等 | `left == right` |
| `!=` | 不等 | `left != right` |
| `>=` | 大于等于 | `left >= right` |
| `<=` | 小于等于 | `left <= right` |
| `>` | 大于 | `left > right` |
| `<` | 小于 | `left < right` |
| `&` | 位与，**结果非零为真** | `(left & right) != 0` |
| `\|` | 位或，**结果非零为真** | `(left \| right) != 0` |
| `^` | 位异或，**结果非零为真** | `(left ^ right) != 0` |

### 6.3 无操作符形式

若条件中无上述任一操作符，直接对整个表达式求值：

- 表达式值非零 → 真
- 表达式值为零 → 假

```
- IF $status                 # $status != 0 即真
- IF READ 0x0002             # 读寄存器，非零即真
```

### 6.4 算术表达式

**不支持**算术运算（`+ - * /` 等）。条件两侧只能是「变量 / 字面量 / `READ`」，不能写 `$x + 1 == 3` 这类复合表达式。需要算术时请在脚本外预处理或多次 `READ` 后比较。

### 6.5 示例

```yaml
- IF $status == 0x0001
- IF $status & 0x00FF
- IF $status != 0
- IF READ 0x0010 >= 0x10
- IF $mask ^ 0x55
- IF $v
```

---

## 7. 执行环境与设备参数

### 7.1 设备参数来源

脚本执行时，`device_addr` 与 `width_flag` 取自 UI 当前状态，**不**从 YAML 读取。这是设计上的「模板/设备现场优先」：

| 参数 | 来源 | 说明 |
|---|---|---|
| `device_addr` | UI Device Addr 输入框 | 执行时通过 `self._i2c_current_dev()` 获取，默认 `0x27` |
| `width_flag` | UI Data Width 下拉 | 取自当前模板或用户手选，决定 `reg_bits` / `data_bits` |
| `speed_mode` | UI Default Speed 下拉 | 默认 100 kHz |
| `dll_path` | UI Settings → DLL Path | None 时自动查找 |
| `data_bits` | UI 当前 `data_bits` | 用于日志格式化 |

> 含义：脚本只描述「操作语义」，不携带设备现场信息。换芯片/换板子时改 UI 即可，脚本可复用。

### 7.2 执行流程

1. 主线程：UI 点 Run 或双击列表项 → `_i2c_seq_execute(script)`。
2. 创建 `_I2cSequenceWorker` 并 `moveToThread`。
3. Worker `run()`：
   a. `I2CInterface(dll_path, speed_mode).initialize()`，失败立即 `error.emit`。
   b. `_build_ast(commands)` 解析为 AST，语法错误 `error.emit`。
   c. 递归 `_exec_block` 遍历 AST 节点，遇 `CMD` 调 `_exec_cmd`、遇 `LOOP` 重复执行 body、遇 `IF` 求值后可选执行 body。
   d. 每条指令通过 `progress.emit(text)` 回传日志。
   e. 用户点 Stop → `worker.request_stop()` → `_stop = True` → 下一次循环检查时退出。
   f. `i2c.close()` 在 `finally` 中执行，确保 DLL 句柄释放。
4. 结束信号：`finished` 或 `error`，UI 解除 busy 状态。

### 7.3 I2C 接口按需初始化

每次执行脚本都会**新建**一个 `I2CInterface` 并在结束时 `close()`，不复用上次连接。这保证了：

- 跨脚本不会残留速率 / 位宽状态。
- DLL 异常时下次执行自动重新初始化。
- UI 切换设备/速率立即生效，无需「重连」按钮。

---

## 8. 完整示例

以下示例展示**单个集合文件**内含多个脚本的写法。每个集合文件对应一个 `.yaml` 文件。

### 8.1 PMU 集合（多脚本）

```yaml
name: BES1503P_PMU
description: BES1503P PMU 全部序列脚本
scripts:
  - name: PMU_INIT
    description: BES1503P PMU 上电初始化
    template: BES1503P_PMU
    commands:
      - WRITE 0x0001 0x0001      # 使能 PMU
      - DELAY 10                 # 等 10ms 稳定
      - READ 0x0002 TO $status   # 读状态
      - IF $status & 0x0001      # PG=1 时继续
      - WRITE_BITS 0x0001 3 0 0x0002   # MODE=01 (Boost)
      - WRITE_BITS 0x0001 15 12 0x0005 # OC_I_LIM=5
      - END_IF
      - READ 0x0002              # 回读确认

  - name: WAIT_PG
    description: 等待 PMU PG 置位，最多轮询 100 次
    template: BES1503P_PMU
    commands:
      - LOOP 100
      - READ 0x0002 TO $st
      - IF $st & 0x0001
      - END_LOOP
      - END_IF
      - DELAY 5
      - END_LOOP
```

> 注意：`IF` 内嵌 `END_LOOP` 是「提前跳出」的惯用写法。当 `IF` 命中时执行 `END_LOOP` 之前的指令序列，但因为 DSL 不支持 `BREAK`，这里实际是利用 `IF` 体内无操作 + `END_LOOP` 在 IF 外闭合的结构来表达「满足条件时本轮什么都不做」。**实际上 DSL 无法跳出循环**，`LOOP 100` 必然跑满 100 次。需要真正提前退出请拆成多个小脚本或调整 `count`。

### 8.2 EEPROM 集合

```yaml
name: EEPROM_24C02
description: 24C02 EEPROM 脚本集
scripts:
  - name: EEPROM_DUMP
    description: 读取 24C02 前 16 字节
    template: EEPROM_24C02
    commands:
      - READ_RANGE 0x00 0x0F 1 5
  - name: EEPROM_WRITE_BYTE
    description: 向 0x10 写入 0xAA
    template: EEPROM_24C02
    commands:
      - WRITE 0x10 0xAA
      - DELAY 5
      - READ 0x10              # 回读校验
```

### 8.3 多寄存器配置 + 校验

```yaml
name: PLL_CFG_Collection
description: PLL 配置与校验脚本集
scripts:
  - name: PLL_CFG
    description: 配置 PLL 并校验
    template: PLL Chip
    commands:
      - WRITE 0x1000 0x00000001   # PLL_EN=1
      - DELAY 50
      - WRITE_BITS 0x1000 15 2 0x3F  # DIV_INT=63
      - WRITE_BITS 0x1000 31 16 0x1000  # DIV_FRAC=0x1000
      - READ 0x1000 TO $cfg
      - IF $cfg == 0x1000FC01
      - READ 0x1004 TO $lock
      - IF $lock & 0x1
      - END_IF
      - END_IF
```

### 8.4 单脚本集合（兼容旧格式）

若一个集合只含一个脚本，也可直接用旧格式（顶层无 `scripts` 键），加载器会自动包装：

```yaml
name: EEPROM_DUMP
description: 读取 24C02 前 16 字节
template: EEPROM_24C02
commands:
  - READ_RANGE 0x00 0x0F 1 5
```

等价于：

```yaml
name: EEPROM_24C02
scripts:
  - name: EEPROM_DUMP
    description: 读取 24C02 前 16 字节
    template: EEPROM_24C02
    commands:
      - READ_RANGE 0x00 0x0F 1 5
```

---

## 9. UI 操作流程

### 9.1 脚本列表

左侧列表显示所有已加载脚本，4 列：

| 列 | 说明 |
|---|---|
| **Collection** | 脚本所属集合名（即 `.yaml` 文件名） |
| **Name** | 脚本名 |
| **Tpl** | 关联模板名 |
| **Cmds** | 指令条数 |

列表按 Collection → Name 排序。同一集合的脚本会连续显示。

### 9.2 新建脚本

1. 在 Sequence Script Manager 卡片（默认折叠，点 `▼` 展开）。
2. 点 **New** → 编辑器清空，Name 默认 `NewSequence`，Tpl 默认关联当前活动模板。
3. 切到 **YAML** 模式（点右上角 `YAML` 按钮切换）直接粘 DSL。
4. 修改 Name / Desc / Tpl。
5. 点 **Save**：
   - 新建脚本无来源集合时，默认写入与 `template` 同名的集合文件（如 `SY6105.yaml`）。
   - 若该集合文件已存在，脚本会 upsert 进去（同名覆盖、异名追加）。
   - 列表自动刷新并选中刚保存的项。

### 9.3 编辑现有脚本

1. 左侧列表单击选中 → 自动载入右侧编辑器。
2. **Table** 模式：只读展示，通过 `+ / −` 按钮增删指令行（新增默认 `WRITE 0x00 0x00`）。
3. **YAML** 模式：自由编辑文本，切回 Table 模式会自动解析 YAML；解析失败弹窗提示。
4. 修改后点 **Save**：脚本写回**原所属集合**文件（保持集合归属不变）。

### 9.4 删除脚本

1. 列表选中脚本 → 点 **Del**。
2. 脚本从所属集合文件中移除；若移除后集合为空，整个 `.yaml` 文件会被删除。

### 9.5 复制脚本

1. 列表选中脚本 → 点 **Dup**。
2. 编辑器载入副本，Name 自动加 `_copy` 后缀。
3. 保存时默认写入当前活动模板同名的集合（不沿用原集合，避免误覆盖）。

### 9.6 执行

- **Run**：执行右侧编辑器当前内容（不保存直接跑，便于快速试）。
- **双击列表项**：直接执行该已保存脚本。
- **Stop**：仅脚本执行中可用，请求当前 worker 停止；下一次循环检查时退出，不会立即打断当前指令。

### 9.7 表格 / YAML 双向同步

- Table → YAML：切到 YAML 模式或点 Save 时，把表格内容序列化为 YAML（单脚本 YAML，不含集合外壳）。
- YAML → Table：切回 Table 模式时解析 YAML 刷新表格。
- Name / Desc / Tpl 三个输入框与脚本字段双向绑定，任一处修改都会同步。
- 同步过程通过 `_i2c_seq_suppress_sync` 标志防止递归。

> 编辑器内 YAML 是**单脚本格式**（`name/commands` 顶层），不是集合格式。集合外壳由保存逻辑自动包装。

### 9.8 与模板联动

- **Linked Only** 按钮（默认开启）：列表仅显示 `template` 字段等于当前活动模板名的脚本。
- 关闭后显示所有集合的所有脚本。
- 切换模板时若 Linked Only 开启，列表自动按新模板名过滤。

---

## 10. 编写 Checklist

- [ ] 集合文件顶层含 `name` / `description` / `scripts` 三键。
- [ ] `scripts` 列表中每个脚本 `name` 非空，且**同一集合内**不重复。
- [ ] `commands` 是字符串列表，每条一行指令。
- [ ] 所有 `LOOP` 都配对 `END_LOOP`，所有 `IF` 都配对 `END_IF`。
- [ ] `addr` / `value` / `start` / `stop` 用 `0x` 前缀或纯 hex 字符串。
- [ ] `high` / `low` / `ms` / `step` / `count` 用十进制。
- [ ] `WRITE_BITS` 的 `high ≥ low` 且 `0 ≤ bit < data_bits`。
- [ ] `READ_RANGE` 的 `start ≤ stop`，`step ≥ 1`。
- [ ] 变量先 `READ ... TO $var` 再引用，避免恒为 0。
- [ ] `IF` 条件中若用 `READ`，注意每次求值都会真的发起 I2C 读，可能拖慢执行。
- [ ] 如需关联模板，`template` 字段与模板 `name` 严格一致（大小写敏感）。
- [ ] 集合文件名建议与主模板名一致（如 `SY6105.yaml`），便于 UI 过滤。
- [ ] YAML 文件以 UTF-8 保存，扩展名 `.yaml` 或 `.yml`。

---

## 11. DSL 语法 BNF 速查

```
collection   := yaml_document
yaml_document := { name, description, scripts: [script*] }
script       := { name, description, template, commands: [line*] }
line         := comment | directive
comment      := '#' rest_of_line
             |  directive '//' rest_of_line
directive    := WRITE addr value
             |  READ addr ['TO' '$' var]
             |  WRITE_BITS addr high low value
             |  DELAY ms
             |  READ_RANGE start stop [step] [delay]
             |  LOOP count_expr
             |  END_LOOP
             |  IF condition
             |  END_IF

addr         := hex_token | '$' var
value        := hex_token | '$' var
high         := dec_token | '$' var
low          := dec_token | '$' var
ms           := dec_token | '$' var
step         := dec_token | '$' var
delay        := dec_token | '$' var
count_expr   := dec_token | '$' var
condition    := expr [op expr]
op           := '==' | '!=' | '>=' | '<=' | '>' | '<' | '&' | '|' | '^'
expr         := '$' var | '0x' hex_digits | hex_digits | 'READ' addr
hex_token    := '0x' hex_digits | hex_digits
dec_token    := ['0x' hex_digits] | decimal_digits
```

---

## 12. 常见错误

| 现象 | 原因 | 解决 |
|---|---|---|
| 脚本列表为空 | PyYAML 未安装；或目录无 `.yaml/.yml` 文件 | `pip install pyyaml`，或检查 `user_data/i2c_sequences/` |
| 集合文件被忽略 | 顶层 `scripts` 为空列表，或文件 YAML 语法错误 | 检查 `scripts` 至少含 1 个脚本；看日志 `Load sequence collection ... failed` |
| 保存后脚本进了错集合 | 新建脚本保存时 `_collection` 为空，fallback 到 `template` 名 | 这是预期行为；若想放入指定集合，先在列表选中该集合中任意脚本再 New |
| 同集合内脚本互相覆盖 | 同一 `scripts` 列表内出现重复 `name` | 保证同一集合内 `name` 唯一；保存是 upsert，同名会被替换 |
| 执行报 `LOOP 缺少 END_LOOP` | 嵌套不闭合 | 检查每个 `LOOP` 都有配对 `END_LOOP` |
| 执行报 `IF 缺少 END_IF` | 嵌套不闭合 | 检查每个 `IF` 都有配对 `END_IF` |
| `WRITE_BITS` 写入值与预期不符 | `value` 写成了十进制 | `value` 是 16 进制，位号才是十进制 |
| `READ_RANGE` 只读了一个地址 | `step` 写成了 `0x1` 被解析为 1，但 `delay` 缺省导致无停顿；或 `stop < start` | 检查 `start ≤ stop`，`step` 用十进制 |
| 变量始终为 0 | 忘记 `READ ... TO $var` 或变量名拼写不一致 | 先 `READ addr TO $var` 再引用 |
| `IF` 永远不成立 | 条件中 `&` 误用为逻辑与 | DSL 中 `&` 是位与，结果非零为真；如需逻辑相等用 `==` |
| 切到 YAML 模式报错 | YAML 语法错误（缩进 / 引号 / 特殊字符） | 用 4 空格缩进，字符串加引号；Table 模式下编辑可避免 |
| 脚本执行中无法停止 | `Stop` 只置标志位，需等当前指令完成 | 拆分长 `READ_RANGE` 或减小 `LOOP` 次数 |
| 日志中地址显示为 `0x????` | UI 位宽与脚本期望不符 | 检查 UI 当前 `Data Width` 是否与设备匹配 |
| 切模板后脚本不显示 | Linked Only 开启但 `template` 字段与模板名不一致 | 关闭 Linked Only 或修正 `template` 字段 |
| 旧单脚本文件不显示 | 旧格式顶层无 `scripts` 键，但 `name`/`template` 都为空导致集合名兜底为 "sequence" | 给脚本补上 `template` 或 `name` 字段，或迁移到集合格式 |

---

## 13. 与 eFuse Python 脚本的区别

I2C 模块还存在另一套基于 Python 的 eFuse 脚本机制（`lib/i2c/config/EFUSE_SCRIPTS/*.py`，由 `EFuseScriptCaller` 动态加载），与本文 DSL 脚本**不是同一套**：

| 维度 | DSL 序列脚本（本文） | eFuse Python 脚本 |
|---|---|---|
| 文件格式 | YAML（`*.yaml`） | Python（`*.py`） |
| 存储位置 | `user_data/i2c_sequences/` | `lib/i2c/config/EFUSE_SCRIPTS/` |
| 编写方式 | 文本 DSL，UI 内编辑 | Python 函数，外部 IDE 编辑 |
| 执行入口 | `_I2cSequenceWorker` | `EFuseScriptCaller.call_efuse_script_function` |
| 注入上下文 | 仅设备参数（dev/width/speed） | `i2c_interface` 实例 + UI 值 + 枚举类 |
| 控制流 | LOOP / IF / READ_RANGE | 完整 Python 语法 |
| 适用场景 | 通用寄存器读写序列、批量配置 | 复杂 eFuse 烧写流程、需要算法逻辑 |

DSL 脚本设计目标是「简单可复现的寄存器序列」，**不**追求图灵完备。需要复杂逻辑（条件分支嵌套、算术、循环退出、函数调用）时，请改用 eFuse Python 脚本路径，或在 DSL 之外用 Python 预处理生成 commands 列表。

---

## 14. 进阶：用 Python 预生成 DSL commands

DSL 不支持算术，但可以通过外部脚本生成 commands 列表后塞进集合 YAML：

```python
import yaml

# 生成 0x00..0x3F 共 64 个寄存器的 READ_RANGE 拆分
commands = []
for blk_start in range(0x00, 0x40, 0x10):
    commands.append(f"READ_RANGE 0x{blk_start:02X} 0x{blk_start+0x0F:02X} 1 5")

# 集合格式：顶层 name + scripts 列表
out = {
    "name": "EEPROM_24C02",
    "description": "24C02 EEPROM 脚本集",
    "scripts": [
        {
            "name": "EEPROM_FULL_DUMP",
            "description": "全空间分块读",
            "template": "EEPROM_24C02",
            "commands": commands,
        },
    ],
}
with open("user_data/i2c_sequences/EEPROM_24C02.yaml", "w", encoding="utf-8") as f:
    yaml.dump(out, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
```

生成后直接放入 `user_data/i2c_sequences/` 即可被 UI 列表识别。也可只生成单脚本字段（不含 `scripts` 外壳），加载器会自动包装。

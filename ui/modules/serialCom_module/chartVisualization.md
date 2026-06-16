# Serial RX 数据可视化（Chart）使用说明

> 适用模块：`ui/modules/serialCom_module`
> 入口：串口模块顶部工具栏 **Chart** 按钮 → 打开 `Serial RX Chart` 弹窗。

---

## 1. 核心概念（三层模型）

数据从「串口接收文本」到「图上的一条曲线」，要经过三层：

| 层 | 名称 | 作用 | 一句话 |
|---|---|---|---|
| 1 | **Rule（规则）** | 从每行 RX 文本里**抓出数值** | 「怎么取数据」 |
| 2 | **Field（字段）** | 规则里抓出的**每个量** | 「取到的是什么量」 |
| 3 | **Series（曲线）** | 把某个字段**画成一条线** | 「怎么画」 |

> 一条 Rule 可以产出多个 Field；每个 Field 可被一条或多条 Series 引用。
> 想画几条线，就建几个 Series。

弹窗布局：
- **左侧 Rules 栏**：管理规则（顶部按钮 `Rules` 可隐藏/显示）。
- **右侧 Series 栏**：管理曲线（顶部按钮 `Series` 可隐藏/显示）。
- **中间 Plot / Events 标签页**：实时曲线 + 命中事件表（图表区右上角有可拖动的悬浮**统计面板**，顶部按钮 `Stats` 可隐藏/显示）。

顶部工具栏按钮：

| 按钮 | 作用 |
|---|---|
| `Rules` | 显示 / 隐藏左侧规则栏 |
| `Series` | 显示 / 隐藏右侧曲线栏 |
| `Stats` | 显示 / 隐藏图表上的悬浮统计面板 |
| `Pause` / `Run` | 暂停 / 恢复绘制刷新（暂停时缓冲仍继续接收，不丢数据） |
| `Clear` | 清空所有缓冲数据、事件表与统计 |
| `Export` | 导出当前已采集数据为 JSON（每条曲线 / 通道的 x、y 数组） |
| `Import CFG` | 从 JSON 导入图表配置（规则 + 曲线 + 统计列等） |
| `Export CFG` | 导出当前图表配置为 JSON |

---

## 2. 实战：给 `Vmin/max=[947, 950]` 画两条线

目标日志行（来自 `tests/log.log`）：

```
Exit gpadc_continue_get_volt(), ch=0, cnt=10000, Vmin/max=[947, 950]
Exit gpadc_continue_get_volt(), ch=1, cnt=10000, Vmin/max=[947, 950]
```

要把方括号里的两个数 `947`（Vmin）和 `950`（Vmax）分别画成线，并且按 `ch` 区分通道。

### 步骤 A — 新建规则 Rule

1. 左侧 **Rules** 栏点 **`+`**，打开 Rule 编辑框。
2. 填写：
   - **Name**：`gpadc_minmax`
   - **Match mode**：选 `regex`
   - **Regex**（核心，使用命名组）：
     ```
     ch=(?P<channel>\d+),\s*cnt=\d+,\s*Vmin/max=\[(?P<vmin>\d+),\s*(?P<vmax>\d+)\]
     ```
   - 其余保持默认（Input mode=`line`、Emit policy=`each_match`、Timestamp=`rx_time`）。
3. 在 **Preview** 框粘贴一行真实日志：
   ```
   Exit gpadc_continue_get_volt(), ch=0, cnt=10000, Vmin/max=[947, 950]
   ```
   下方应显示命中并解析出 `channel=0, vmin=947, vmax=950`。

> **命名组说明**：`(?P<名字>...)` 里的「名字」就是字段名。
> 规则强制约定两个特殊名字：
> - `channel` → 自动作为「通道」，供曲线按通道分组。
> - `key` → 自动作为「分类键」。
> 其它名字（如 `vmin`、`vmax`）就是普通数据字段。

### 步骤 B — 声明字段 Field

在同一个 Rule 编辑框下方的 **Fields** 区，点 **`+ Field`** 分别添加：

| Field name | Type | Unit |
|---|---|---|
| `vmin` | `float`（或 `int`） | `mV` |
| `vmax` | `float`（或 `int`） | `mV` |

> `channel` 是特殊组，**不需要**单独建 Field。
> 若不手动建 Field，引擎会把所有命名组按 `float` 自动当作字段，但**显式建 Field 更可控**（可设单位、类型）。

点 **OK** 保存规则。

### 步骤 C — 新建两条曲线 Series

回到右侧 **Series** 栏，点两次 **`+`**，分别配置：

**曲线 1（Vmin）**
- **Name**：`Vmin`
- **Source type**：`field`
- **Rule**：选 `gpadc_minmax`
- **Field**：选 `vmin`
- **Group by**：`channel`（这样 ch=0 / ch=1 各自一条线）
- **Chart type**：`line`
- **Y axis**：`left`
- **Color**：任选

**曲线 2（Vmax）**
- **Name**：`Vmax`
- 其余同上，**Field** 改选 `vmax`
- **Color**：换一个颜色

点 **OK** 保存。回到中间 **Plot** 页即可看到实时曲线；按通道分组时每个通道自动用不同颜色、图例显示 `Vmin 0`、`Vmin 1` 等。

> **`channel` 是「角色名」，不是字面词**：引擎只认正则里名为 `channel` 的命名组，与日志里写的是 `ch=`、`channel=`、`case=`、`sence=` 还是别的**毫无关系**。
> 只要把代表通道的那段写成 `(?P<channel>...)`，引擎就当通道处理。例如：
> - `ch=0` → `ch=(?P<channel>\d+)`
> - `channel:2` → `channel:(?P<channel>\d+)`
> - `case A` → `case\s+(?P<channel>\w+)`

### 步骤 E — 只看部分通道 + 合并/分轴显示

实际可能有 6 个以上通道全挤在一张图上，且不同通道数值差异很大（如 ch0/ch1 在 ~950，ch2~ch6 在 ~100）。用 Series 上的两个选项解决：

**只展示 ch0、ch1（通道白名单）**
- 在 Series 编辑框的 **Channels** 填：`0,1`
- 留空 = 显示全部通道；多个用逗号隔开（如 `0,1,3`）
- 白名单外的通道**不进缓冲、不画线**

**合并显示 / 分开显示（独立坐标轴）/ 拆分子图**
- Series 编辑框的 **Channel display**：
  - `merged`：所有通道**共用同一 Y 轴**，适合数值量级相近、想直接比较的场景。
  - `split_axis`：按通道顺序**交替分配到左轴 / 右轴**（第 1 个通道走左轴，第 2 个走右轴，依次交替）。差异大的两组各占一根轴、各自自适应缩放，互不挤压。
  - `split`：每个通道**分离为独立子图**，纵向堆叠在图表区，彻底避免多通道曲线数据重合、看不清的问题。各子图带独立标题栏与坐标轴，X 轴自动联动（缩放 / 平移一个子图，其余同步），便于跨通道对齐查看。
    - **拖拽分隔条调高度**：子图之间是可拖拽的水平分隔条，按住上下拖动即可改变各子图占用的高度比例。
    - **标题栏 ↑ / ↓ 调顺序**：每个子图标题栏右侧有上移 / 下移按钮，点击即可改变子图的排列顺序。

> 例：`Channels=0,1` + `Channel display=split_axis` → ch0 用左轴、ch1 用右轴，两条线都铺满各自量程，不再像之前那样一条贴顶一条贴底。
> 例：`Channels=0,1` + `Channel display=split` → ch0、ch1 各占一张独立子图上下堆叠，互不遮挡；拖动中间分隔条调高度，点标题栏 ↑/↓ 调顺序。

> **切换显示模式不丢数据**：只改 `Channel display`（merged ↔ split_axis ↔ split）或颜色等**显示类**设置、不改解析规则时，已采集的曲线会原样重绘，无需重新记录。只有改动 Rule 正则 / 字段 / `Max points` / `Time window` 等会影响缓冲结构的设置，或手动点 `Clear`，才会重置数据。

### 步骤 F — 看统计量（悬浮统计面板）

图表区右上角有一块**半透明悬浮统计面板**，叠在曲线上方，每条曲线（含每个通道子线）一行，实时显示统计量：

| 列 | 含义 |
|---|---|
| Count | 有效数据点数 |
| Mean | 平均值 |
| Max / Min | 最大 / 最小值 |
| Std | 标准差（总体） |
| Last | 最新一个值 |
| Peak-Peak | 极差（Max − Min） |

- 顶部工具栏的 **Stats** 按钮可一键显示 / 隐藏该悬浮面板（默认显示）。
- 面板内右上角 **Columns...** 按钮，勾选要显示哪些统计列（至少选一项），选择会随配置一起保存。
- 面板大小**根据内容自动适应**（行数 / 列数变化时自动收放）。
- 按住面板顶部「☰ Statistics」标题栏可**拖动**到任意位置；拖动后会停在你放置的地方，不再自动回到右上角（默认未拖动时停靠在图表区右上角）。

### 步骤 D — 保存配置

点顶部 **Export CFG** 导出 JSON 留存，或直接关闭弹窗——配置会随串口模块状态一起持久化，下次自动恢复。

---

## 3. 常用用例库

### 用例 1：`KEY=VALUE` 单值（最常见）

日志：`VBAT=3.812` 或 `temperature=24C`

- Match mode：`regex`，或直接用 **Preset → `KEY=FLOAT` → Apply**
- Regex：
  ```
  (?P<key>[A-Za-z_][\w-]*)\s*[=:]\s*(?P<value>[+-]?\d+(?:\.\d+)?)
  ```
- Series：Field 选 `value`，**Group by** 选 `key`，即可让 `VBAT`、`temperature` 各成一条线。

### 用例 2：带通道号 `CHx KEY=VALUE`

日志：`CH2 volt=948`

- Preset → `CHx KEY=FLOAT` → Apply
- Regex：
  ```
  CH(?P<channel>\d+)\s+(?P<key>[A-Za-z_][\w-]*)[=:](?P<value>[+-]?\d+(?:\.\d+)?)
  ```
- Series：Field=`value`，Group by=`channel`。

### 用例 3：一行多个字段同时画

日志：`gpadc_ch0_irq_cb: raw/volt=32601/1067 sample_time=1014us`

- Regex：
  ```
  raw/volt=(?P<raw>\d+)/(?P<volt>\d+)\s+sample_time=(?P<t>\d+)us
  ```
- Fields：`raw`(int)、`volt`(int, mV)、`t`(int, us)
- 建 3 条 Series 分别绑 `raw`/`volt`/`t`；量纲差异大的可把某条放 **Y axis = right**（右轴）。

### 用例 4：迭代序号采样（`i=00 volt=134`）

日志：`ch=2, i=00, volt=134`

- 这类「按采样序号」的数据，建议把 Rule 的 **Timestamp** 设为 `sequence_index`，X 轴按命中顺序递增，而不是接收时间。
- Regex：
  ```
  ch=(?P<channel>\d+),\s*i=(?P<idx>\d+),\s*volt=(?P<volt>\d+)
  ```
- Series：Field=`volt`，Group by=`channel`。

### 用例 5：PASS/FAIL 测试结果

日志：`!!!error:0x1` 或 `result: PASS`

- Match mode：`regex`
- Field type 选 `pass_fail`：自动把 `PASS/OK/SUCCESS→1`，`FAIL/NG/ERROR→0`，便于在图上看 0/1 跳变。
- 自定义映射可在 Field 的 **Pass/Fail map** 填 JSON，例如 `{"0x1": 0, "0x0": 1}`。

### 用例 6：枚举状态机

日志：`STATE=CHARGING`

- Preset → `ENUM STATE`
- Field type 选 `enum`，在 **Enum map** 填：
  ```json
  {"values": {"IDLE": 0, "CHARGING": 1, "DONE": 2}, "labels": {"0": "IDLE", "1": "CHARGING", "2": "DONE"}}
  ```

### 用例 7：派生运算（差值 / 滑动平均 / 命中率）

不直接取数据，而是对**已有 Series**做计算：

- Series 的 **Source type** 选 `derived`。
- **Operation** 可选：

  | Operation | 公式 / 含义 | 用到的参数 |
  |---|---|---|
  | `add` | Source A + Source B | Source A、Source B |
  | `subtract` | Source A − Source B | Source A、Source B |
  | `multiply` | Source A × Source B | Source A、Source B |
  | `divide` | Source A ÷ Source B（除数≈0 时跳过该点） | Source A、Source B |
  | `rolling_avg` | Source A 最近 N 点的滑动平均 | Source A、Window N |
  | `rolling_rate` | Source A 最近 N 点中**等于 Match value 的比例**（0~1） | Source A、Window N、Match value |

- **Scale**：最终结果再乘以该系数（默认 1.0），用于单位换算或缩放。
- **Source A / Source B**：从下拉里选**其它已存在的曲线**（不能选自己）。
- 例 1：画 `Vmax − Vmin`（电压抖动幅度）→ Operation=`subtract`，Source A=`Vmax`，Source B=`Vmin`。
- 例 2：画某状态命中率 → Operation=`rolling_rate`，Source A=状态曲线，Window N=`50`，Match value=`1`（统计最近 50 点里值为 1 的占比）。

> 派生曲线在每次有新数据进入时按「源曲线最新点」实时计算追加，X 取源 A 的最新时间戳。

---

## 4. 字段与匹配速查

### Match mode（匹配方式）
| 模式 | 用途 | 用到的输入框 |
|---|---|---|
| `contains` | 仅判断是否包含关键字（命中也几乎无数值，常用于配合 frame 或纯标记） | Keyword before |
| `prefix_suffix` | 取「Keyword before」与「Keyword after」之间的内容，作为 `value` 字段 | Keyword before / after |
| `regex` | 正则命名组提取（最常用、最灵活） | Regex |
| `frame` | 跨多行帧：Keyword before=帧起始、Keyword after=帧结束，**整帧拼成多行文本后再用 Regex 提取** | Keyword before / after + Regex |
| `custom_enum` | 正则提取 + 字段类型用 `enum` 做枚举映射 | Regex + Field 的 Enum map |

> - `prefix_suffix` 不填 before 则从行首起，不填 after 则到行尾止；取出的内容会被 `strip()`。
> - `frame` 有保护上限：单帧最多 64 行 / 64KB，超时 5s 自动丢弃未闭合的帧。
> - 匿名捕获组（无 `?P<name>`）会回退成名为 `value` 的字段。

### Input mode（输入来源）
| 模式 | 含义 |
|---|---|
| `line` | 按文本行接收（最常用，适合可读日志） |
| `bytes_hex` | 把收到的原始字节转成空格分隔的十六进制串（如 `0a 1f 30`）再做匹配 |
| `bytes_raw` | 把原始字节按 `latin-1` 解码为字符再做匹配（用于二进制/不可见字符协议） |

> `line` 规则只吃文本行；`bytes_hex` / `bytes_raw` 规则只吃原始字节流，两者来源不同、互不干扰。

### Source session（数据来源会话）
- `active`：只接收**当前活动连接**的数据（默认）。
- `all`：接收所有会话的数据。
- 也可填具体的会话 ID 只收该会话（输入框可编辑）。

### Field（字段编辑框）
| 项 | 说明 |
|---|---|
| **Field name** | 必须与正则命名组同名（如 `vmin`）才能取到值 |
| **Type** | `int` / `float` / `bool` / `pass_fail` / `enum` / `string`（数值自动识别十进制、十六进制 `0x..`、科学计数法） |
| **Unit** | 单位，仅作展示（如 `mV`、`us`） |
| **Group** | 字段自定义分组标签（选填，便于在多字段规则里归类） |
| **Enum map** | 仅 `enum` 类型用，填 `IDLE=0, CC=2, CV=3`，把字符串映射成数值并在图例/标签显示原名 |
| **Pass/Fail map** | 仅 `pass_fail` 类型用，覆盖默认映射，填 `GOOD=1, BAD=0` |

> `pass_fail` 默认映射：`PASS/OK/SUCCESS/TRUE/GOOD/1 → 1`，`FAIL/NG/ERROR/FALSE/BAD/0 → 0`（大小写不敏感）。

### Preset（正则模板，Rule 编辑框内一键套用）
| 模板名 | 适用日志 |
|---|---|
| `KEY=FLOAT` | `VBAT=3.812`、`temp:24` 这类 `键=值` |
| `CHx KEY=FLOAT` | `CH2 volt=948` 这类带通道前缀 |
| `PASS/FAIL` | 含 `PASS` / `FAIL` / `OK` / `NG` 的结果行 |
| `ENUM STATE` | `STATE=CHARGING` 这类状态行 |
| `XML-LIKE TAG` | `<key>value</key>` 这类标签对 |

> 选模板后点 **Apply** 会把对应正则填入 Regex 框，可再手动微调。

### Emit policy（命中策略）
- `each_match`：一行内每个匹配都出点（默认）
- `first_match`：只取首个匹配
- `last_match_per_line`：只取最后一个匹配

### Timestamp（X 轴时间）
- `rx_time`：用串口接收时间（默认，适合时序数据）
- `sequence_index`：用命中序号递增（适合「第 i 次采样」类数据）

### Group by（分组）
同一字段按分组键拆成多条线，每条自动用不同颜色：

| 选项 | 拆分依据 |
|---|---|
| `none` | 不拆分，全部数据画成一条线 |
| `channel` | 按正则里 `channel` 命名组的值分组（每个通道一条线） |
| `key` | 按正则里 `key` 命名组的值分组（每个键一条线，适合 `KEY=VALUE` 多变量） |
| `session` | 按数据来源会话分组 |

> 与 `channel` 一样，`key` 也是「角色名」：把代表分类名的那段写成 `(?P<key>...)` 即可。

### Channels（通道白名单）
仅 `Group by=channel` 生效。填 `0,1` 只画这两个通道；留空=全部。多个用逗号隔开。

### Channel display（通道显示模式）
仅 `Group by=channel` 生效。`merged`=所有通道共用同一 Y 轴；`split_axis`=按通道顺序交替分到左 / 右轴，应对通道间量纲差异大、互相挤压的情况；`split`=每通道分离为纵向堆叠的独立子图（X 轴联动），可拖拽分隔条调高度、用标题栏 ↑/↓ 调顺序，彻底避免多通道数据重合看不清。

### 其它选项

**Rule 级**
| 选项 | 说明 |
|---|---|
| `Enabled` | 取消勾选则该规则停用，不再解析数据 |
| `Case sensitive` | 正则 / 关键字是否区分大小写（默认不区分） |

**Series 级**
| 选项 | 说明 |
|---|---|
| `Enabled` | 取消勾选则该曲线不绘制、不统计 |
| `Chart type` | `line`（折线）/ `scatter`（散点）/ `step`（阶梯） |
| `Y axis` | `left` / `right`，把量纲差异大的曲线分到不同轴 |
| `Color` | 曲线颜色（按通道分组时各通道自动分色，此项作为基准/单线色） |
| `Max points` | 该曲线缓冲最多保留的点数（超出丢弃最旧点），默认 5000 |
| `Time window (s)` | 只保留最近 N 秒的数据，0=不限制 |

> 改 `Max points` / `Time window` 会影响缓冲结构，切换时会重置该曲线已采集数据（参见步骤 E 的提示）。

### 统计列（Stat metrics）
悬浮统计面板可显示的列（在面板 `Columns...` 里勾选）：`Count` / `Mean` / `Max` / `Min` / `Std`（总体标准差）/ `Last` / `Peak-Peak`（极差）。默认显示前 5 项，选择随配置持久化。

---

## 5. 小贴士

- **先用 Preview 验证再保存**：在 Rule 编辑框 Preview 粘贴一行真实日志，确认能解析出期望字段，再去建 Series。
- **正则用命名组**：必须写 `(?P<name>...)`，匿名组只会回退成 `value`。
- **量纲差异大用双 Y 轴**：把小量纲（如温度）放 `left`，大量纲（如 raw 码值）放 `right`。
- **数据量大用 Max points / Time window**：限制每条线点数或时间窗，避免内存与卡顿。
- **配置可复用**：`Export CFG` 导出 JSON，换台机器 `Import CFG` 导入即可。
- **暂停不丢数据**：点 `Pause` 仅停止刷新绘制，曲线缓冲仍按规则继续接收。

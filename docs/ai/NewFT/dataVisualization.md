# SerialCom RX 数据可视化框架与实现计划

> 目标：在 `ui/modules/serialCom_module/serialCom_module_frame.py` 串口工具中新增可配置的 RX 数据可视化能力，持续监听符合条件的接收内容，将数值、状态、枚举等数据按通道独立出图、混合出图或运算出图。

---

## 1. 功能范围

### 1.1 用户入口

在完整串口控制台顶部工具栏中新增 `Chart` 按钮，位置放在 `Settings` 左侧：

```text
Connect  Pause  Stop  Refresh │ + − │ Sidebar                 Chart  Settings
```

点击 `Chart` 后弹出图表配置与实时显示窗口，窗口负责：

- 管理 RX 匹配规则、数据字段解析规则、通道/曲线/运算曲线配置；
- 实时展示折线图、散点图、阶梯状态图、枚举状态轨道、Pass/Fail 统计等；
- 支持启用/暂停采集、清空缓存、导出当前采集数据；
- 支持配置持久化，随 SerialCom 用户设置保存/恢复。

### 1.2 数据来源

数据只消费串口 RX 已经收到的 bytes/text，不新增串口读线程，不直接操作 `serial.Serial`。

推荐挂载点：

- 主接收入口：`SerialComMixin._sc_on_data_received(data: bytes)`；
- 文本行生成点：`_sc_rx_line_buf` 按 `\n` 切行后追加日志前；
- 自动 flush 点：`_sc_flush_rx_line_buf()`；
- 多串口长期兼容：未来可从 `SerialSessionManager.session_data_received(session_id, data)` 路由。

### 1.3 不在本阶段做的事

- 不替换现有日志、过滤、脚本等待关键字机制；
- 不修改串口底层 IO 模型；
- 不新增大型第三方依赖，优先复用项目已有 `pyqtgraph`；
- 不把数据可视化逻辑耦合到仪器层或 `instruments/`。

---

## 2. 当前 SerialCom 相关上下文

### 2.1 UI 结构

当前完整控制台由 `complete_serialComWidget(parent_layout)` 创建：

```text
outer
├── _build_sc_toolbar()
└── body_splitter
    ├── _build_sc_sidebar()
    └── center_splitter
        ├── top_section
        │   ├── _build_sc_log_area()
        │   └── _build_sc_send_area()
        └── _build_sc_quick_commands()
```

新增 `Chart` 按钮应只影响 `_build_sc_toolbar()` 与 `_bind_sc_signals()`，图表配置窗口作为独立 `QDialog`/`QWidget` 弹出，避免挤占当前日志区域。

### 2.2 RX 处理现状

当前 `_sc_on_data_received(data: bytes)` 已完成：

- pause 状态判断；
- 脚本等待关键字 feed；
- RX 字节计数与状态栏更新；
- HEX / ASCII 展示；
- ASCII 模式下基于换行拆行并调用 `_sc_append_log(f"[RX] {line}", _CLR_RX)`；
- 自动波特率监测 feed。

数据可视化应在“原始 bytes 进入后”和“规范化 text line 生成后”分别提供 hook：

```text
bytes hook：适合二进制帧、HEX 协议、无换行数据
line hook：适合日志文本、关键字前后跟随数值、Pass/Fail、枚举状态
```

---

## 3. 总体架构

### 3.1 分层原则

```text
SerialComMixin（UI 宿主）
    ├── Chart 按钮 / 窗口生命周期 / RX hook
    ↓ Signal/方法调用
SerialChartController（UI 层轻量控制器）
    ├── 配置管理 / 数据缓存 / pyqtgraph 刷新节流
    ↓ 纯 Python 解析
SerialChartParser / RuleEngine
    ├── 条件检测 / 字段匹配 / 类型转换 / 通道路由 / 运算曲线
    ↓ 数据点
ChartSeriesBuffer
    ├── 环形缓存 / 时间轴 / 导出快照
```

所有解析与缓存逻辑建议先放在 `ui/modules/serialCom_module/serialCom_module_frame.py` 内部类中，便于与现有单文件风格保持一致；当类数量膨胀或复用需求明确后，再拆到 `serial_chart.py`。

### 3.2 核心类建议

| 类 / 数据结构 | 位置 | 职责 |
|---|---|---|
| `_SerialChartDialog` | `serialCom_module_frame.py` | 图表窗口，包含规则列表、曲线列表、预览图、控制按钮 |
| `_SerialChartController` | 同文件内部类 | 接收 RX 文本/bytes，调用解析器，维护缓存，节流刷新 UI |
| `_SerialChartRule` | dataclass / dict | 一条 RX 匹配规则，描述触发条件、字段模式、输出通道 |
| `_SerialChartSeries` | dataclass / dict | 一条曲线/状态轨道配置，描述数据来源、图形类型、颜色、轴、聚合 |
| `_SerialChartParser` | 纯 Python 类 | 把 line/bytes 转成标准数据事件 |
| `_SerialChartBuffer` | 纯 Python 类 | 每条 series 的环形数据缓存，支持 max points / time window |
| `_SerialChartRuleDialog` | `QDialog` | 新增/编辑匹配规则 |
| `_SerialChartSeriesDialog` | `QDialog` | 新增/编辑曲线/运算曲线 |

如果后续拆文件，建议目录：

```text
ui/modules/serialCom_module/
├── serialCom_module_frame.py
├── serial_chart_model.py
├── serial_chart_parser.py
└── serial_chart_dialog.py
```

拆文件时需同步 `DIRECTORY_STRUCTURE.txt`，但本设计阶段不强制拆。

---

## 4. 条件检测机制

### 4.1 典型场景

用户提到“关键字前后跟着数据内容”，实际可以归纳为 4 类：

| 场景 | 示例 RX | 推荐模式 |
|---|---|---|
| 关键字后数值 | `VBAT=3.812V` | Prefix / Regex capture |
| 关键字前数值 | `3.812 V VBAT` | Suffix / Regex capture |
| 起止标记帧 | `[MEAS] temp=26.4 cur=12.8 [/MEAS]` | Start/End frame |
| 多行上下文 | `PMU_RESULT\nVBAT: 3.8\nPASS` | Context window / stateful frame |

### 4.2 匹配规则维度

每条 `_SerialChartRule` 建议包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `rule_id` | str | UUID，持久化稳定标识 |
| `name` | str | UI 显示名 |
| `enabled` | bool | 是否启用 |
| `source_session` | str | `active` / `all` / 指定 session_id，为多串口预留 |
| `input_mode` | str | `line` / `bytes_hex` / `bytes_raw` |
| `match_mode` | str | `contains` / `prefix_suffix` / `regex` / `frame` / `custom_enum` |
| `keyword_before` | str | 前置关键字或起始标记 |
| `keyword_after` | str | 后置关键字或结束标记 |
| `regex` | str | 正则表达式，支持命名捕获组 |
| `case_sensitive` | bool | 是否大小写敏感 |
| `field_specs` | list[dict] | 字段解析定义 |
| `emit_policy` | str | `each_match` / `first_match` / `last_match_per_line` |
| `timestamp_mode` | str | `rx_time` / `field_time` / `sequence_index` |

### 4.3 条件模式

#### 4.3.1 contains

适合只要行里包含某关键字就解析：

```text
Input:  CH1 ADC=1024
Rule:   contains "CH1"
Field:  regex "ADC=(?P<adc>\d+)"
Output: ch1_adc = 1024
```

#### 4.3.2 prefix_suffix

适合关键字前后包住数据：

```text
Input:  <VBAT>3.812</VBAT>
Rule:   before="<VBAT>", after="</VBAT>"
Type:   float
Output: VBAT = 3.812
```

如果只配置 `before`，则取 before 后面到行尾或分隔符前的内容；只配置 `after`，则取 after 前最近 token。

#### 4.3.3 regex

适合最通用场景，支持多个字段：

```regex
CH(?P<channel>\d+)\s+V=(?P<voltage>[+-]?\d+(?:\.\d+)?)\s+I=(?P<current>[+-]?\d+(?:\.\d+)?)
```

解析事件：

```json
{
  "channel": "1",
  "voltage": 3.812,
  "current": 12.5
}
```

#### 4.3.4 frame

适合关键信息跨多行或有起止符：

```text
[PMU]
VBAT=3.8
TEMP=26.5
RESULT=PASS
[/PMU]
```

规则维护内部状态：

- 见到 `start_marker` 后开始累计 frame buffer；
- 见到 `end_marker` 或超出 `max_lines/max_bytes/timeout_ms` 后结束；
- 对整个 frame 执行 regex / field_specs；
- 超时或超长时丢弃并记录一次 warning 到系统日志。

#### 4.3.5 custom_enum

适合用户自定义状态词：

```text
State: IDLE / PRECHG / CC / CV / DONE / FAULT
```

配置：

```json
{
  "enum_map": {
    "IDLE": 0,
    "PRECHG": 1,
    "CC": 2,
    "CV": 3,
    "DONE": 4,
    "FAULT": -1
  },
  "unknown_policy": "ignore"
}
```

---

## 5. 数据内容匹配与类型系统

### 5.1 内置字段类型

| 类型 | 示例 | 解析结果 | 展示方式 |
|---|---|---|---|
| `int` | `123`, `-5`, `0x1A` | int | 折线 / 柱状 / 计数 |
| `float` | `3.14`, `-1.2e-3`, `26.5C` | float | 折线 / 散点 |
| `bool` | `true`, `false`, `1`, `0`, `on`, `off` | 0/1 | 阶梯线 / 状态轨道 |
| `pass_fail` | `PASS`, `FAIL`, `OK`, `NG` | 1/0 | 状态点 / 统计率 |
| `enum` | `IDLE`, `CC`, `CV` | number + label | 状态轨道 / 阶梯线 |
| `string` | 任意文本 | str | 标签 / tooltip / 表格 |
| `timestamp` | `12:00:01.234`, `123456ms` | float / datetime | X 轴或字段 |

### 5.2 数字解析策略

数字字段需要兼容常见工程日志：

```text
VBAT=3.812V
I_CHG: -12.5 mA
temp=26.4C
adc=0x03FF
ratio=98.2%
```

建议规则：

- 默认提取第一个有效数字 token；
- 支持 `0x` 十六进制整数；
- 支持科学计数法；
- 支持可选单位后缀，单位仅存入 metadata，不参与数值换算；
- 后续可扩展 `unit_scale`，如 `mA → A`、`mV → V`。

### 5.3 Pass/Fail 映射

默认映射：

```text
PASS / OK / SUCCESS / TRUE / 1  → 1
FAIL / NG / ERROR / FALSE / 0   → 0
```

UI 中允许用户覆盖映射，例如：

```text
GOOD=1, BAD=0, TIMEOUT=-1
```

### 5.4 自定义枚举

枚举配置支持两种输入：

```text
IDLE=0, PRECHG=1, CC=2, CV=3, DONE=4, FAULT=-1
```

或多行：

```text
IDLE 0
PRECHG 1
CC 2
CV 3
DONE 4
FAULT -1
```

UI 解析后统一保存为：

```json
{
  "labels": {"0": "IDLE", "1": "PRECHG"},
  "values": {"IDLE": 0, "PRECHG": 1}
}
```

---

## 6. 多关键字 / 多通道管理

### 6.1 三层模型

```text
Rule（怎么从 RX 中取数据）
  → Channel（数据归属，如 CH1/CH2/VBAT/TEMP）
    → Series（怎么画，如独立曲线、混合曲线、运算曲线）
```

Rule 不直接等于曲线。一个 Rule 可以输出多个字段，一个字段可以被多个 Series 复用。

### 6.2 独立出图

场景：多个通道独立曲线。

```text
RX: CH1 V=3.80
RX: CH2 V=1.82
```

配置：

- Rule：捕获 `channel` 与 `voltage`；
- Series A：source=`voltage`, group_by=`channel`, chart=`line`; 
- 输出：CH1 voltage、CH2 voltage 两条曲线。

### 6.3 混合出图

场景：多个关键字共享一个图表，例如 voltage/current/temp 同时展示。

```text
VBAT=3.8
IBAT=12.5
TEMP=26.4
```

配置：

- Rule A：VBAT → field `vbat`；
- Rule B：IBAT → field `ibat`；
- Rule C：TEMP → field `temp`；
- Chart View：同一 PlotWidget 中启用多个 Series，可按单位决定左/右 Y 轴。

### 6.4 运算出图

场景：多个通道运算得到新曲线。

示例：功率曲线

```text
P = VBAT * IBAT
```

示例：差分曲线

```text
Delta = CH1 - CH2
```

示例：Pass Rate

```text
PassRate = rolling_sum(pass_fail == 1, 100) / count(100)
```

建议先支持安全表达式白名单，不直接 `eval` 用户输入。第一阶段可提供固定运算模板：

| 模板 | 参数 | 输出 |
|---|---|---|
| `A + B` | series_a, series_b | float |
| `A - B` | series_a, series_b | float |
| `A * B` | series_a, series_b | float |
| `A / B` | series_a, series_b | float，B=0 时跳过 |
| `rolling_avg(A, N)` | series_a, window | float |
| `rolling_rate(A == value, N)` | series_a, value, window | float |

第二阶段再扩展表达式解析，使用 `ast` 白名单节点实现。

### 6.5 多串口兼容

规则需要预留 `source_session`：

| 值 | 说明 |
|---|---|
| `active` | 仅当前激活串口 |
| `all` | 所有串口 RX 均参与 |
| `primary` / session_id | 指定串口 |

数据事件统一带上：

```json
{
  "session_id": "primary",
  "rx_time": 1710000000.123,
  "line": "CH1 V=3.8",
  "fields": {...}
}
```

---

## 7. 图表窗口设计

### 7.1 窗口布局

```text
_SERIAL_CHART_DIALOG
├── Header: Serial RX Chart / Run Pause / Clear / Export / Settings
├── Left Panel: Rules
│   ├── + Rule / Edit / Duplicate / Delete / Enable
│   └── rule list
├── Center: Chart Tabs
│   ├── Plot 1: Line / Scatter / Step
│   ├── Plot 2: Status / Enum
│   └── Data Table / Events
└── Right Panel: Series
    ├── + Series / Edit / Delete
    ├── source field / chart type / axis / color
    └── buffer / aggregation settings
```

弹窗必须显式传 `parent=self`：

```python
dlg = _SerialChartDialog(self)
```

按钮 default / autoDefault 显式二元化，避免回车误触发。

### 7.2 图表类型

| 图表类型 | 适用数据 | pyqtgraph 实现 |
|---|---|---|
| `line` | 连续 float/int | `PlotDataItem` |
| `scatter` | 离散采样点 | `ScatterPlotItem` 或 symbol |
| `step` | bool/pass_fail/enum | `PlotDataItem(..., stepMode=...)` 或重复点 |
| `bar` | 计数/分布 | `BarGraphItem` |
| `status_track` | 多状态枚举 | Y 值 + 自定义 tick label |
| `table` | string / 原始事件 | `QTableWidget` |

第一阶段建议实现 `line`、`scatter`、`step/status_track`，即可覆盖数值、Pass/Fail、枚举状态。

### 7.3 刷新策略

串口 RX 高频时不能每条数据都重绘。建议：

- RX hook 只解析并写入 buffer；
- `_SerialChartController` 内部用 `QTimer` 每 100~200 ms 刷新一次图表；
- 每条 series 采用环形缓存，默认 `max_points=5000`；
- PlotDataItem 使用 `setData(x, y)` 批量更新；
- 图表窗口关闭后停止刷新 timer，但可选择继续采集或暂停采集。

---

## 8. 配置模型与持久化

### 8.1 顶层配置

建议挂到 SerialCom 持久化状态中：

```json
{
  "chart": {
    "enabled": true,
    "capture_when_dialog_closed": false,
    "max_points_default": 5000,
    "rules": [],
    "series": [],
    "views": []
  }
}
```

### 8.2 Rule 示例

```json
{
  "rule_id": "rule_vbat",
  "name": "VBAT voltage",
  "enabled": true,
  "source_session": "active",
  "input_mode": "line",
  "match_mode": "regex",
  "regex": "VBAT[=:]\\s*(?P<vbat>[+-]?\\d+(?:\\.\\d+)?)\\s*(?P<unit>mV|V)?",
  "case_sensitive": false,
  "field_specs": [
    {"name": "vbat", "type": "float", "unit": "V", "group": "VBAT"}
  ],
  "emit_policy": "each_match",
  "timestamp_mode": "rx_time"
}
```

### 8.3 Series 示例

```json
{
  "series_id": "series_vbat",
  "name": "VBAT (V)",
  "enabled": true,
  "source": {"type": "field", "rule_id": "rule_vbat", "field": "vbat"},
  "chart_type": "line",
  "view_id": "main",
  "axis": "left",
  "color": "#15d1a3",
  "max_points": 5000,
  "time_window_s": 300
}
```

### 8.4 运算 Series 示例

```json
{
  "series_id": "series_power",
  "name": "Power (mW)",
  "enabled": true,
  "source": {
    "type": "derived",
    "operation": "multiply",
    "a": "series_vbat",
    "b": "series_ibat",
    "scale": 1.0
  },
  "chart_type": "line",
  "view_id": "main",
  "axis": "right",
  "color": "#ffb84d"
}
```

---

## 9. 数据流

### 9.1 Line 模式数据流

```text
_serial read worker
    ↓ bytes signal
SerialComMixin._sc_on_data_received(data)
    ↓ decode / clean / line split
SerialComMixin._sc_chart_feed_line(line, session_id, rx_time)
    ↓
SerialChartController.feed_line(event)
    ↓
SerialChartParser.match_rules(event)
    ↓ emits parsed field events
SerialChartBuffer.append(series_id, x, y, metadata)
    ↓ QTimer 100~200ms
SerialChartDialog.refresh_plots()
```

### 9.2 Bytes/HEX 模式数据流

```text
SerialComMixin._sc_on_data_received(data)
    ↓
SerialComMixin._sc_chart_feed_bytes(data, session_id, rx_time)
    ↓
Rule(input_mode=bytes_hex/bytes_raw)
    ↓
Parser frame buffer / regex over hex string / binary decoder hook
```

第一阶段可以只实现 `line` 模式；bytes/hex 规则保留 UI 与配置字段，第二阶段补齐。

---

## 10. UI 交互细节

### 10.1 Rule 新建向导

建议用 3 步表单：

1. 条件：输入模式、匹配模式、关键字/regex/frame marker；
2. 字段：字段名、类型、单位、枚举映射、默认值策略；
3. 预览：输入 sample RX，立即显示匹配结果。

### 10.2 Series 新建向导

建议用 2 步表单：

1. 数据源：选择 Rule + Field，或选择运算模板；
2. 展示：图表类型、颜色、Y 轴、最大点数、时间窗口。

### 10.3 预设模板

内置模板能降低配置门槛：

| 模板 | Regex / 规则 |
|---|---|
| `KEY=FLOAT` | `(?P<key>[A-Za-z_][\w-]*)\s*[=:]\s*(?P<value>[+-]?\d+(?:\.\d+)?)` |
| `CHx KEY=FLOAT` | `CH(?P<channel>\d+)\s+(?P<key>[A-Za-z_][\w-]*)[=:](?P<value>[+-]?\d+(?:\.\d+)?)` |
| `PASS/FAIL` | `(?P<result>PASS|FAIL|OK|NG)` |
| `ENUM STATE` | `STATE[=:]\s*(?P<state>[A-Za-z_][\w-]*)` |
| `XML-LIKE TAG` | `<(?P<key>\w+)>(?P<value>.*?)</(?P=key)>` |

---

## 11. 安全与可靠性

### 11.1 Regex 防护

- 用户 regex 编译失败时在 UI 显示错误，不影响串口接收；
- 每条 line 的匹配规则数量较多时应限制最大规则数或做启用开关；
- 避免灾难性回溯：对单行最大长度做限制，超过阈值只截取前 N 字符进入 chart parser；
- frame buffer 限制 `max_lines` / `max_bytes` / `timeout_ms`。

### 11.2 表达式安全

运算曲线禁止直接 `eval` 用户字符串。阶段一使用固定模板；阶段二如需表达式，使用 `ast.parse` 白名单：

- 允许：`Expression`、`BinOp`、`UnaryOp`、`Name`、`Constant`、`Call` 中的白名单函数；
- 禁止：属性访问、下标、导入、lambda、comprehension、任意函数调用。

### 11.3 异常处理

- Parser 异常只禁用当前 rule 或记录错误计数，不中断 RX；
- UI 层异常通过 logger 记录 `exc_info=True`，必要时弹出用户可读提示；
- 图表窗口关闭时停止 timer，释放 pyqtgraph items，避免悬挂引用。

---

## 12. 性能预算

| 项 | 建议值 |
|---|---|
| 默认刷新周期 | 100~200 ms |
| 单 series 默认缓存 | 5000 points |
| 单 line parser 最大长度 | 4096 chars |
| frame 最大累计 | 64 lines / 64 KB |
| 单次 UI 刷新最大更新 series | 只更新 dirty series |
| 默认启用规则数提醒 | 超过 50 条提示性能风险 |

---

## 13. 实现计划

### Phase 0：设计落地与接口预留

- 新增 Chart 顶部按钮，位置在 `Settings` 左侧；
- 新增 `_sc_open_chart_dialog()`；
- 初始化 `self._sc_chart_config`、`self._sc_chart_controller`、`self._sc_chart_dialog`；
- 在 `_sc_on_data_received()` 和 `_sc_flush_rx_line_buf()` 中预留 line feed hook；
- 接入持久化字段但默认空配置。

验收：点击 Chart 可打开空窗口，不影响串口连接、收发、日志显示。

### Phase 1：单规则单曲线 MVP

- 实现 `_SerialChartDialog` 基础布局；
- 支持 regex 捕获一个 float 字段；
- 支持 line chart 实时绘制；
- 支持 pause / clear；
- 支持 sample line 预览匹配结果；
- 使用 `pyqtgraph.PlotWidget` 和 `PlotDataItem.setData()`。

验收示例：RX 行 `VBAT=3.812V` 能实时画出 VBAT 曲线。

### Phase 2：类型系统与多曲线

- 支持 int / float / pass_fail / enum / bool；
- 支持一条 regex 输出多个字段；
- 支持多 series 同图展示；
- 支持颜色、轴、最大点数配置；
- 支持数据表查看最近事件。

验收示例：`CH1 V=3.8 I=12.5 RESULT=PASS` 同时输出 V/I/RESULT。

### Phase 3：多关键字与通道分组

- 支持 `group_by=channel/key/session`；
- 支持 CH1/CH2 自动生成独立曲线；
- 支持同一 Plot View 中混合多条曲线；
- 支持启用/禁用 rule 和 series；
- 支持配置导入/导出 JSON。

验收示例：`CH1 V=...`、`CH2 V=...` 自动生成两条曲线。

### Phase 4：运算曲线

- 支持固定模板：A+B、A-B、A*B、A/B、rolling_avg、rolling_rate；
- 支持按最近时间戳对齐两个 series；
- 支持运算结果单独 series 绘制；
- 除零、缺值、过期数据时跳过并计数。

验收示例：VBAT 和 IBAT 输入后自动生成 Power 曲线。

### Phase 5：Frame / Bytes / 多串口增强

- 支持 frame start/end 多行解析；
- 支持 bytes_hex 匹配；
- 接入 `SerialSessionManager.session_data_received(session_id, data)`；
- Rule 的 `source_session` 生效；
- 多串口 All / Active / 指定串口可视化。

验收示例：COM1/COM2 RX 可分别入图或合并入同一视图。

---

## 14. 关键改动点清单

### 14.1 `serialCom_module_frame.py`

需要新增/修改：

- import：已有 `pyqtgraph` 依赖可用，建议局部 import，避免无图表窗口时增加初始化成本；
- `_build_sc_toolbar()`：新增 `_sc_chart_btn`，添加到 `_sc_settings_btn` 左侧；
- `_bind_sc_signals()`：连接 `_sc_chart_btn.clicked` 到 `_sc_open_chart_dialog()`；
- `complete_serialComWidget()`：初始化 chart 配置、控制器、窗口引用；
- `_sc_on_data_received()`：ASCII line 生成后调用 `_sc_chart_feed_line(line, session_id, rx_time)`；
- `_sc_flush_rx_line_buf()`：flush 残留行时同样 feed；
- 持久化：`_sc_collect_persisted_state()` / `_sc_apply_persisted_state()` 纳入 chart 配置；
- 清空日志：可选择同步清空 chart buffer，或由 Chart 窗口独立 Clear。

### 14.2 样式

短期可复用现有 dialog/button/input 样式函数：

- `_DLG_STYLE`
- `dialog_line_edit_style()`
- `dialog_ok_button_style()`
- `dialog_cancel_button_style()`
- `log_toolbar_button_style()`
- `thin_scrollbar_style()`

如需要新增样式，应分别补齐 dark / apple 两套 `serialCom_*_style.py` 导出，避免 `_SERIALCOM_STYLE_EXPORTS` 动态导入失败。

### 14.3 资源

Chart 按钮可优先复用已有 SVG 图标，若没有合适图标再新增 `resources/modules/SVG_Serial/chart.svg`。新增资源子目录或运行时资源时必须同步 `spec/kk_lab.spec`；仅新增同目录 SVG 通常无需新增 datas 条目，但仍需确认 spec 是否按目录收集。

---

## 15. 验证计划

### 15.1 静态验证

- 检查无 `print()`；
- 检查无裸 `except:`；
- 检查 QDialog 均显式传 parent；
- 检查新增按钮 default / autoDefault 设置；
- 检查未在 UI 主线程新增阻塞 IO；
- 检查 pyqtgraph 已在 requirements/spec hook 中存在，无新增依赖。

### 15.2 功能验证用例

| 用例 | RX 输入 | 期望 |
|---|---|---|
| float | `VBAT=3.812V` | 曲线新增一个点 |
| int | `ADC=1024` | 曲线新增一个点 |
| pass_fail | `RESULT=PASS` / `RESULT=FAIL` | 状态值 1/0 |
| enum | `STATE=CC` | 状态轨道显示 CC 对应值 |
| 多字段 | `CH1 V=3.8 I=12.5` | 两条 series 同时更新 |
| 多通道 | `CH2 V=1.8` | CH2 曲线更新 |
| 无匹配 | `hello world` | 不新增点、不报错 |
| regex 错误 | 非法 regex | UI 提示错误，不影响 RX |
| 高频 RX | 1000 lines/s | UI 不明显卡顿，图表按 timer 节流刷新 |

### 15.3 回归范围

- 串口搜索、连接、断开；
- ASCII/HEX RX 显示；
- Auto Flush；
- 日志过滤、复制、导出、保存；
- Quick Commands / Scripts 等待关键字；
- 多 LOG 面板；
- 独立运行入口。

---

## 16. 风险与决策

| 风险 | 影响 | 建议 |
|---|---|---|
| 高频 RX + 多 regex 导致 UI 卡顿 | 日志和图表卡顿 | parser 限长、规则启用开关、刷新节流、dirty series 更新 |
| 用户 regex 复杂或错误 | 匹配异常 | 编译时校验，运行时隔离异常 |
| 运算表达式安全 | 任意代码执行风险 | 不用 eval，先固定模板，后 AST 白名单 |
| 多串口数据归属不清 | 曲线混入错误来源 | 所有事件带 session_id，Rule 必有 source_session |
| 图表窗口关闭后对象悬挂 | 内存泄漏/崩溃 | closeEvent 停 timer，宿主引用置空 |
| 样式动态导入缺字段 | 启动失败 | 新样式函数必须 dark/apple 双文件同时导出 |

---

## 17. 推荐最小落地方案

第一轮实现建议只做“够用且稳定”的 MVP：

1. 顶部新增 `Chart` 按钮；
2. 弹出 Chart 窗口；
3. 支持新增 regex rule，捕获一个命名 float 字段；
4. 支持一条或多条 line series；
5. ASCII 行 feed，按 100~200ms 刷新 pyqtgraph；
6. 支持 pause / clear / max_points；
7. 配置随 SerialCom 状态持久化。

完成 MVP 后再扩展 pass_fail、enum、多通道自动分组、运算曲线和 frame/bytes 模式，避免一次性改动过大影响现有串口工具稳定性。

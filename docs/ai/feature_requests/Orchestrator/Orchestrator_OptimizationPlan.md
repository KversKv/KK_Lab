# Custom Test 优化方案与任务跟踪

> 基于 2026-05-28 对 `ui/pages/custom_test/custom_test_ui.py` 及其上下游执行链路的审计结果。
> 2026-05-28 已二次对照 `ui/pages/custom_test/`、`core/instruments/` 与内置模板做查漏补缺。
> 本文只定义优化方案、工作量和会话窗口，不代表已经开始代码改造。

---

## 1. 结论摘要

Custom Test 当前已经具备“自定义测试流”的产品雏形：节点库、序列画布、参数面板、变量上下文、循环/分支/延时、仪器操作、数据记录、导出、日志和曲线展示都已存在。

但从 KK_Lab 的分层规范看，当前实现不是最佳设计。主要问题是：执行引擎、上下文、节点模型、仪器节点都位于 `ui/pages/custom_test/` 下，UI 页面同时负责布局、仪器解析、运行准备、结果展示和部分底层连接。这让功能继续扩展时容易变成“页面级大脚本”，后续会在回归、Mock、批处理、统一仪器管理和长时间稳定性上付出代价。

推荐优化方向：保留现有 UI 交互形态，逐步把“测试流执行内核”迁移到 `core/custom_test/`，让 UI 只负责编辑、展示和发起运行；仪器来源统一走 `InstrumentManager` / factory / adapter；节点变成可校验、可序列化、可测试的测试流 DSL。

### 1.1 本次查漏补缺结论

原方案的主方向正确，但还需要补上以下关键约束：

1. **序列格式已经混用**：内置模板同时存在顶层 list 与 `{version, sequence, instruments}` 两种格式，且 `CustomTestUI.load_template()` 只支持 list，`SequenceCanvas._on_load()` 才支持 dict。迁移前必须先统一读取入口。
2. **节点注册依赖 import 副作用**：`NODE_REGISTRY` 由 `ui.pages.custom_test.nodes.__init__` 间接导入所有节点触发注册。迁移到 core 时必须保留 shim 与注册初始化顺序，不能只移动文件。
3. **InstrumentManager 已有 capability / busy lease 基础**：优化方案不应另起一套仪器会话模型，应复用 `InstrumentSnapshot.capabilities`、`InstrumentLease`、`find_sessions()`，只在 Custom Test 层做 capability 映射与 adapter 包装。
4. **当前 adapter 接口不一致**：manager 中 `bes_usb_i2c`、`serial_port`、页面内 `I2CInterface`、`SerialComMixin` 暴露的方法不同，而节点当前直接调用 `read/write/serial_send/get_serial_connection`。统一 adapter 是 Phase 2 的硬前置，不只是锦上添花。
5. **PromptUser 当前缺接收端**：节点通过 `QApplication._custom_test_prompt` 发起主线程提示，但仓库内未发现该方法实现，当前功能大概率会等待到超时。应提高优先级，纳入可用性验收。
6. **结果视图与原始 records 是两套状态**：Data 表支持用户重命名、删除列、排序、格式化；自动 CSV 直接导出 `context.records`。后续 ResultStore 需要区分 canonical data 与 visible table view。
7. **未实现/半实现节点需要产品决策**：CMW270/RF Analyzer 在 palette 中可见但驱动未接入；Frequency Counter 已在 manager/profile/context 中出现，却没有 Custom Test 节点。需要决定隐藏、禁用、preflight 阻止，还是补齐实现。

---

## 2. 当前流程梳理

### 2.1 UI 初始化

入口文件：

- `ui/pages/custom_test/custom_test_ui.py`
- `ui/pages/custom_test/sequence_canvas.py`
- `ui/pages/custom_test/property_panel.py`
- `ui/pages/custom_test/node_palette.py`

当前页面初始化流程：

1. `CustomTestUI.__init__()` 接收 `n6705c_top`、`mso64b_top`、`chamber_ui`、`instrument_manager`。
2. 初始化 N6705C / Chamber / UART 连接 Mixin。
3. 创建 `ExecutorThread` 和运行时 `ExecutionContext` 占位。
4. 构建三栏 UI：
   - 左侧：Instrument Connections + Node Palette。
   - 中间：SequenceCanvas 节点树。
   - 右侧：PropertyPanel 参数编辑。
   - 底部：Logs / Data / Chart。
5. 绑定运行、暂停、停止、保存、加载、参数变化、序列变化等信号。

### 2.2 序列编辑

核心对象：

- `BaseNode`: 节点基类，提供 `node_type`、`PARAM_SCHEMA`、`children`、`to_dict()`、`from_dict()`。
- `SequenceCanvas`: 用 `QTreeWidget` 表示节点树，负责拖拽、排序、保存、加载。
- `PropertyPanel`: 根据 `PARAM_SCHEMA` 生成参数编辑控件。
- `NodePalette`: 根据节点注册表和仪器注册表展示可添加节点。

当前序列文件格式：

- JSON。
- 当前仓库中实际存在两种格式：
  - 旧/轻量格式：顶层就是节点 list，例如 `case1_power_vs_temp.json`。
  - v1 格式：顶层包含 `version`、`sequence`、`instruments`，例如 `GPADC_Vsys_Channel.json`。
- `sequence` 是节点树的递归字典列表。
- `instruments` 保存 N6705C / Chamber / UART / MCU IO 等连接 meta。
- 注意：`SequenceCanvas._on_load()` 已兼容 list / dict 两种格式，但 `CustomTestUI.load_template()` 当前只按 list 解析。后续应先抽出统一 `load_sequence_file()`，否则内置 dict 模板无法通过该入口加载。

### 2.3 运行执行

入口：

- `CustomTestUI._on_run()`

当前运行流程：

1. 从 `canvas.get_sequence()` 获取节点树。
2. 调用 `_get_used_instrument_ids()` 扫描序列中用到的仪器类型。
3. 新建 `ExecutionContext(instrument_manager=...)`。
4. `context.populate_instruments_from_manager()` 从 manager 获取部分仪器。
5. 对缺失仪器做 UI 级 fallback：
   - N6705C 从 `self.n6705c` 注入。
   - Chamber 从 `self.chamber` 注入。
   - Scope 从 `_mso64b_top_ref.mso64b` 注入。
   - I2C 在 UI 内即时创建 `I2CInterface()` 并初始化。
   - UART 将 `self` 作为 uart 对象注入。
   - MCU IO 从当前页面状态注入。
6. 清空表格、曲线、日志和进度。
7. `ExecutorThread.start(sequence, context)` 启动后台线程。
8. 执行器通过 signal 把日志、进度、当前步骤、记录数据发回 UI。

### 2.4 节点执行

核心文件：

- `ui/pages/custom_test/executor.py`
- `ui/pages/custom_test/context.py`
- `ui/pages/custom_test/nodes/instrument_nodes.py`
- `ui/pages/custom_test/nodes/logic_nodes.py`
- `ui/pages/custom_test/nodes/io_nodes.py`
- `ui/pages/custom_test/nodes/value_nodes.py`

执行模型：

1. `CustomTestExecutor.run()` 在线程中执行。
2. `_run_nodes()` 顺序执行顶层节点。
3. `_execute_node()` 调用 `node.execute(context)`。
4. 容器节点内部再 import `_execute_children()` 递归执行子节点。
5. `ExecutionContext` 保存：
   - `variables`
   - `records`
   - `instruments`
   - stop / pause 状态
   - step 回调
   - pass/fail 状态

---

## 3. 主要优点

1. 功能覆盖面较完整：节点编辑、运行控制、变量、逻辑、仪器、记录、导出和可视化都已具备。
2. UI 体验方向正确：三栏布局适合自定义流程搭建，底部 Logs/Data/Chart 适合测试运行观察。
3. 执行线程方向正确：主运行逻辑已放入 QThread，UI 更新基本通过 Signal/Slot。
4. 数据模型具备扩展基础：`BaseNode.PARAM_SCHEMA` 可以支撑参数编辑器、保存加载、后续校验和文档生成。
5. 已有序列持久化：JSON 保存加载为后续模板库、版本迁移和导入导出打下基础。
6. 结果落盘已存在：运行成功后自动导出 CSV，也支持手动导出 Data 表格。

---

## 4. 主要问题

### 4.1 分层问题

当前执行内核位于 UI 包：

- `ui/pages/custom_test/executor.py`
- `ui/pages/custom_test/context.py`
- `ui/pages/custom_test/nodes/*`

这些文件本质属于 core/test-flow 逻辑。放在 UI 层会导致：

- 难以写无界面单元测试。
- 难以做命令行批处理或后台自动执行。
- 节点实现容易直接依赖 Qt / UI。
- 业务能力无法被其它页面复用。

### 4.2 仪器来源混杂

同一次运行中，仪器可能来自：

- `instrument_manager`
- top page reference
- 页面 Mixin 成员变量
- UI 内临时创建的 I2C
- `self` 作为 UART adapter

这会导致：

- 难以判断某个节点实际使用哪台仪器。
- 双 N6705C / 多串口 / 多 I2C 场景不好扩展。
- 连接失败时错误提示不够集中。
- Mock 与真机路径可能不一致。

### 4.3 节点和执行器反向耦合

多个容器节点内部直接 import `_execute_children()`。这说明节点不是纯节点，而是知道执行器内部函数。这会带来：

- 执行器实现难以替换。
- 节点单测需要牵引完整 UI 包。
- 后续要支持 step-by-step、dry-run、断点、并行分支时改动面大。

### 4.4 运行前校验不足

当前点击 Run 后才发现：

- 仪器未连接。
- 节点参数非法。
- 表达式引用不存在。
- CMW270 未实现。
- 循环参数异常。
- 结果字段冲突。

这对长流程测试不友好。自定义测试流应在执行前给出完整的 preflight report。

### 4.5 停止和暂停不够强

当前 stop / pause 是协作式检查。对于长时间仪器 IO、温箱等待、串口读取、I2C 遍历等阻塞调用，停止响应取决于节点内部是否检查 `context.should_stop`。

需要将 stop_check / timeout / cancellation 变成所有长耗时节点和 adapter 的统一协议。

### 4.6 结果模型不统一

当前 UI 表格按第一条 record 的 keys 建列，后续如果出现新字段，表格不会自然扩列。CSV 自动导出会汇总所有 keys，导致 UI 展示与导出文件可能不一致。

结果数据应引入统一模型：

- 字段名
- 类型
- 单位
- 精度
- 是否导出
- 是否绘图
- 来源节点 uid
- PASS / FAIL / WARNING 状态

### 4.7 页面职责过重

`custom_test_ui.py` 目前承担：

- 页面布局
- 仪器连接区域动态构建
- 仪器 meta 读写
- 自动连接
- MCU IO 连接
- 运行上下文拼装
- 表格显示
- 图表显示
- 导出
- 节点添加菜单

后续继续扩展会明显影响可维护性。

### 4.8 序列加载入口不一致

当前保存逻辑会写出 `{version, sequence, instruments}`，但部分内置模板仍是顶层 list；同时：

- `SequenceCanvas._on_load()` 兼容两种格式。
- `CustomTestUI.load_template()` 只支持顶层 list。
- `load_template()` 没有回放 `instruments` meta。

这会导致某些模板在不同入口加载结果不一致。迁移前必须统一 serialization 入口，并给模板格式做兼容测试。

### 4.9 节点注册与隐藏节点依赖 import 顺序

`NODE_REGISTRY` 当前是全局 dict，节点类通过 `@register_node` 在 import 时注册。`IfBranch` / `ElseIfBranch` / `ElseBranch` 这类结构节点需要存在于 registry，但不应直接出现在普通节点菜单中；`IfElse` / `IfThenElse` 又承担 legacy 兼容。

迁移到 `core/custom_test/nodes/` 时必须明确：

- registry 由哪个模块负责初始化。
- UI palette 与 core registry 的边界。
- 隐藏节点、legacy 节点、未实现节点如何标记。
- 旧 import path 如何 shim，避免旧模板/外部脚本断裂。

### 4.10 Adapter 接口不一致

当前节点直接使用原始对象方法，例如：

- I2C 节点调用 `read(dev, reg, width)` / `write(dev, reg, data, width)`。
- UART 节点兼容 `serial_send()`、`get_serial_connection()`、`read()`。
- Scope 节点按方法名探测 `get_channel_frequency()` / `get_dvm_frequency()`。
- MCU IO 节点调用 `out()` / `in_pull()` / `read()`。

但 `InstrumentManager` 中的 session instance 未必暴露同一套方法，特别是 `bes_usb_i2c` 与当前 UI 内临时创建的 `lib.i2c.i2c_interface_x64.I2CInterface` 不是同一抽象。Phase 2 必须先定义 Custom Test runtime adapter protocol，再让节点只依赖 adapter。

### 4.11 Manager busy / lease 未纳入运行期

`InstrumentManager` 已提供 `try_set_busy()` 与 `InstrumentLease`，但当前 Custom Test run 只拿 instance，不标记 busy。长流程运行中，其它页面仍可能复用同一仪器，导致状态互相污染。

运行期 resolver 应在启动前为所有会话申请 lease，执行完成、停止、异常时统一释放。preflight 也要把“仪器正在被其它 owner 占用”作为阻塞项。

### 4.12 PromptUser 当前缺 UI 接收端

`PromptUser` 通过 `QMetaObject.invokeMethod(app, "_custom_test_prompt", ...)` 请求主线程弹窗，但当前仓库内未找到 `_custom_test_prompt` 实现。实际运行时可能无法弹窗并等待到超时。

这不是单纯的优化项，而是现有节点可用性问题。建议提前加入 Phase 0 / Phase 1 的 smoke，至少先决定：

- 先隐藏该节点；
- 或补齐 UI prompt signal/dialog；
- 或在 preflight 中标记为 unsupported。

### 4.13 变量生产者分析已有局部实现但未沉到 core

`RecordDataPointEditor` 已经实现 `_detect_variables_in_node()`，但它只服务 UI 表单，且覆盖节点不完整。后续 preflight、字段映射、结果模型、文档生成都需要同一份变量生产者分析。

建议把“节点会产生哪些变量 / 隐式变量 / 默认是否导出”提升为 `NodeDefinition` 元数据或 core 分析器，避免 UI 与执行器各写一套。

### 4.14 结果视图状态与原始数据状态混杂

Data 表目前支持重命名列、删除列、排序、格式化和按可见顺序导出；自动 CSV 与 `ExportResult` 节点则直接使用 `context.records`。这意味着：

- UI 手动导出反映“用户当前看到的表格”。
- 自动导出反映“原始 records”。
- Chart 会尝试绘制所有可转成 float 的字段，包括不适合绘图的状态/地址字段。

ResultStore 需要同时保存 canonical result schema 与 view state，明确手动导出、自动导出、节点导出的语义。

### 4.15 功能边界不完整

当前页面暴露了 CMW270/RF Analyzer 节点，但驱动未接入；`core/instruments` 已有 Keysight 53230A profile 与 context `freq_counter` 槽位，但 Custom Test 没有频率计节点和 palette 入口。

建议在 Phase 0 做产品边界决策：

- 未实现节点默认禁用或隐藏，preflight 给出明确提示。
- 已接入 manager 的仪器，如果要进 Custom Test，需要补齐节点、adapter、Mock 和模板。

---

## 5. 目标架构

### 5.1 推荐目录结构

```text
core/custom_test/
├── __init__.py
├── model.py                 # dataclass: sequence, node spec, validation issue, result row
├── context.py               # ExecutionContext, variables, records, cancellation
├── executor.py              # CustomTestExecutor / runner（可用 QtCore Signal，禁止 QtWidgets）
├── runtime.py               # NodeRuntime / execute_children / control-flow 协议
├── resolver.py              # InstrumentResolver, required instrument analysis
├── registry.py              # node registry, node metadata registry
├── validation.py            # preflight validation
├── serialization.py         # JSON versioning, migrate v1 -> v2
├── result_store.py          # CSV/XLSX export, result schema
├── variable_analysis.py     # 变量生产者 / 隐式变量 / 导出字段分析
├── adapters/
│   ├── base.py              # Custom Test runtime adapter protocol
│   ├── n6705c_adapter.py
│   ├── scope_adapter.py
│   ├── chamber_adapter.py
│   ├── frequency_counter_adapter.py
│   ├── i2c_adapter.py
│   ├── uart_adapter.py
│   └── mcu_io_adapter.py
└── nodes/
    ├── base.py              # BaseNode / NodeDefinition / PARAM_SCHEMA
    ├── instrument_nodes.py
    ├── logic_nodes.py
    ├── io_nodes.py
    └── value_nodes.py
```

UI 保留：

```text
ui/pages/custom_test/
├── custom_test_ui.py        # 页面组装和信号连接
├── node_palette.py          # 节点展示
├── sequence_canvas.py       # 节点树编辑
├── property_panel.py        # 参数编辑
└── record_data_editor.py

userdata/custom_test_templates/
└── *.json                   # Custom Test 模板，不放在 UI 包内
```

### 5.2 分层职责

| 层级 | 职责 | 禁止 |
|---|---|---|
| `ui/pages/custom_test/` | 编辑序列、展示日志/结果/图表、选择模板、提示用户 | 直接创建底层 I2C、直接决定仪器 fallback、执行业务节点 |
| `core/custom_test/` | 序列模型、校验、执行、结果、节点注册、仪器解析 | 引入 Qt Widgets、依赖具体页面对象 |
| `core/instruments/` / `instruments/factory.py` | 仪器会话、连接、实例创建 | 被 UI 绕过 |
| `instruments/` | 纯驱动能力 | 依赖 UI |

> 说明：`core/custom_test/adapters/` 是“测试流节点面向的运行时协议”，不是新仪器驱动层。真实驱动仍归 `instruments/`；会话与连接状态仍优先归 `core/instruments/InstrumentManager`。

### 5.3 运行目标流程

```text
用户点击 Run
  ↓
UI 从 SequenceCanvas 得到 CustomTestSequence
  ↓
core/custom_test.validation.preflight(sequence, manager_snapshot)
  ↓
若失败：UI 展示缺失仪器/非法参数/未实现节点
  ↓
InstrumentResolver 生成 ExecutionContext
  ↓
CustomTestRunner 在线程中执行
  ↓
Signal: log / progress / step / result / finished
  ↓
UI 展示，ResultStore 统一导出
```

### 5.4 节点设计目标

节点分两层：

1. Node Definition
   - 节点类型、名称、分类、图标、参数 schema、是否接受 children、需要哪些 capability。
2. Node Handler
   - 输入 `ExecutionContext`。
   - 调用 adapter，而不是直接调用原始仪器对象。
   - 返回 `NodeResult` 或写入 `context`。

示意：

```python
class N6705CMeasureNode(BaseNode):
    node_type = "N6705CMeasure"
    required_capabilities = ["power_analyzer.measure"]

    def execute(self, context):
        pa = context.adapters.power_analyzer
        value = pa.measure(channel, measure_type)
        context.set_variable(result_var, value, export=export_var)
```

### 5.5 仪器能力模型

不要让节点知道具体来源是 N6705C A、N6705C B、top page 还是 manager session。节点只声明 capability。

建议 capability：

| Capability | 示例节点 |
|---|---|
| `power_analyzer.set_voltage` / `power_analyzer.measure` | SetVoltage / Measure / ChannelOn |
| `scope.basic` | SetScale / Trigger / RunStop |
| `scope.measurement` / `scope.frequency` / `scope.dvm` | ScopeMeasure / ScopeMeasureFreq / ScopeGetDvmDC |
| `chamber.temperature` / `chamber.stabilize_wait` | ChamberSetTemp / WaitStable / GetTemp |
| `counter.frequency` | FrequencyCounterMeasure（待补） |
| `i2c.register` | I2CRead / I2CWrite / I2CTraverse |
| `uart.session` | UARTSend / UARTReceive |
| `mcu_io.gpio` | GPIO Output / Read / Pulse |
| `rf_analyzer.basic` | RFAnalyzerMeasure（当前 unsupported） |

落地时建议通过一层映射兼容现有 `InstrumentProfile.capabilities`：

| Custom Test capability | 现有 manager capability 示例 |
|---|---|
| `power_analyzer.set_voltage` | `set_voltage` |
| `power_analyzer.measure` | `measure_current` / `measure_voltage` |
| `scope.measurement` | `measure_waveform` |
| `scope.frequency` | `measure_frequency` / `dvm_frequency` |
| `chamber.stabilize_wait` | `stabilize_wait` |
| `i2c.register` | `i2c_read` / `i2c_write` |
| `uart.session` | `serial_tx` / `serial_rx` |
| `mcu_io.gpio` | `gpio_out` / `gpio_input` / `gpio_read` / `gpio_pulse` |

### 5.6 运行期契约

优化后每次运行应遵守以下契约：

1. UI 只提交 `CustomTestSequence`、运行选项和可选 legacy refs。
2. preflight 基于 sequence + manager snapshot 生成完整 issue list。
3. resolver 将 capability 解析为 `ResolvedInstrument`，并为真实 session 申请 `InstrumentLease`。
4. runner 只接收 adapters，不直接接收页面对象。
5. 所有长耗时等待走 `context.sleep()` / adapter timeout / stop_check。
6. `finally` 中释放 lease、flush records、恢复 UI 状态。

---

## 6. 分阶段实施计划

## Phase 0: 保护现状和建立基线

目标：先不重构，建立可回归基线，避免后续迁移时破坏现有序列；同时把当前已经混用的模板格式、未实现节点入口和 prompt 节点可用性摸清楚。

### Task 0.1: 梳理现有节点清单和模板兼容表

- **目标**: 生成当前节点类型、参数 schema、输出变量、隐式变量、所需仪器清单。
- **详细内容**:
  - 统计 `nodes/*.py` 中所有 `node_type`。
  - 标记隐藏节点、legacy 节点、未实现节点。
  - 标记每个节点的 required instrument / capability。
  - 标记每个节点是否会 `record_data`。
- **涉及文件**:
  - `ui/pages/custom_test/nodes/*.py`
  - `ui/pages/custom_test/node_palette.py`
  - `userdata/custom_test_templates/*.json`
- **预计工作量**: 0.5 会话
- **预计会话**: 会话 1
- **完成日期**: 2026-05-28
- **完成文件**: `ui/pages/custom_test/node_metadata.py`、`tests/test_custom_test_phase0.py`、`docs/ai/feature_requests/Orchestrator/Orchestrator_OptimizationPlan.md`
- **风险备注**: `build_node_inventory()` 已形成 Phase 0 节点清单入口；输出/隐式变量仍是迁移前基线快照，后续 Phase 1/3 需沉淀为 `NodeDefinition` / Result Model。
- **状态**: ✅ 已完成

### Task 0.2: 添加最小无 UI 回归用例

- **目标**: 用现有执行器跑通纯 value / logic / io 序列，为迁移建立测试基线。
- **详细内容**:
  - 覆盖 SetVariable、LoopCount、IfBlock、RecordDataPoint、ExportResult。
  - 覆盖 stop、pause 基本状态。
  - 覆盖旧 JSON 加载。
- **涉及文件**:
  - 新增或补充测试文件，位置按项目现有测试约定决定。
  - 若项目没有测试目录，优先使用轻量 smoke 脚本，不引入新测试框架。
- **预计工作量**: 0.5 ~ 1 会话
- **预计会话**: 会话 1
- **完成日期**: 2026-05-28
- **完成文件**: `tests/test_custom_test_phase0.py`
- **风险备注**: 已覆盖 SetVariable、LoopCount、IfBlock、RecordDataPoint、ExportResult、pause/stop 状态和旧 JSON 加载；真实仪器、PromptUser 弹窗和长阻塞 stop 不在 Phase 0 覆盖范围内。
- **状态**: ✅ 已完成

### Task 0.3: 统一序列读取入口和模板格式盘点

- **目标**: 在不改变保存格式的前提下，先保证所有入口都能读取当前 list / dict 两类序列文件。
- **详细内容**:
  - 抽出轻量 `load_sequence_data(data)` 或等价 helper，兼容顶层 list 与 `{version, sequence, instruments}`。
  - `SequenceCanvas._on_load()` 与 `CustomTestUI.load_template()` 复用同一解析逻辑。
  - 加载 dict 模板时回放 `instruments` meta。
  - 统计内置模板格式，标记后续迁移目标。
- **涉及文件**:
  - `ui/pages/custom_test/sequence_canvas.py`
  - `ui/pages/custom_test/custom_test_ui.py`
  - `userdata/custom_test_templates/*.json`
- **依赖**: Task 0.1
- **预计工作量**: 0.5 会话
- **预计会话**: 会话 1
- **完成日期**: 2026-05-28
- **完成文件**: `ui/pages/custom_test/sequence_io.py`、`ui/pages/custom_test/sequence_canvas.py`、`ui/pages/custom_test/custom_test_ui.py`、`tests/test_custom_test_phase0.py`
- **风险备注**: 仅统一读取入口，不改变保存格式；dict 模板的 `instruments` meta 复用现有 `_on_metadata_loaded()` 回放。
- **状态**: ✅ 已完成

### Task 0.4: 未实现/半实现节点可用性决策

- **目标**: 防止用户把明显跑不通的节点放入长流程后才失败。
- **详细内容**:
  - 确认 `RFAnalyzerMeasure` 是隐藏、禁用还是仅 preflight 阻止。
  - 确认 `PromptUser` 当前是否补齐 UI 接收端；若暂不补，需 preflight 标记 unsupported。
  - 确认 Keysight 53230A 是否进入 Custom Test；若进入，后续补节点与 adapter。
  - 在节点清单中增加 `status`: stable / legacy / hidden / unsupported / planned。
- **涉及文件**:
  - `ui/pages/custom_test/node_palette.py`
  - `ui/pages/custom_test/nodes/*.py`
  - 可选 `helps/custom_test.html`
- **依赖**: Task 0.1
- **预计工作量**: 0.5 会话
- **预计会话**: 会话 1 ~ 2
- **完成日期**: 2026-05-28
- **完成文件**: `ui/pages/custom_test/node_metadata.py`、`ui/pages/custom_test/node_palette.py`、`ui/pages/custom_test/custom_test_ui.py`、`tests/test_custom_test_phase0.py`
- **风险备注**: `RFAnalyzerMeasure` 与 `PromptUser` 标记为 unsupported 并从 palette / Add 菜单隐藏；旧序列仍可加载以保留兼容，后续 preflight 需要继续明确阻止运行。
- **状态**: ✅ 已完成

### Phase 0 产出快照（2026-05-28）

- **节点基线**: 当前注册节点 67 个；`stable` 60 个、`hidden` 3 个、`legacy` 2 个、`unsupported` 2 个。
- **hidden 节点**: `IfBranch`、`ElseIfBranch`、`ElseBranch`，仅作为 `IfBlock` 结构子节点使用，不直接出现在 palette。
- **legacy 节点**: `IfElse`、`IfThenElse`，保留旧序列加载兼容，不在 palette 暴露。
- **unsupported 节点**: `RFAnalyzerMeasure`、`PromptUser`。前者缺 CMW270/RF Analyzer 驱动与 adapter；后者缺 UI prompt 接收端。两者先隐藏，Phase 2/4 再纳入 preflight / signal dialog。
- **planned 能力**: Keysight 53230A 已在 InstrumentManager 有 `freq_counter` 槽位，但 Custom Test 暂无节点；后续若进入 Custom Test，需要补节点、adapter、Mock 和模板。
- **模板兼容表**: 内置模板 7 个，其中 list 格式 5 个（`case1_power_vs_temp.json`、`case2_gpadc_vs_temp_vout.json`、`case3_clk_vs_temp.json`、`case4.json`、`case5_clk_vs_vout.json`），dict 格式 2 个（`bes1505Icore_test.json`、`GPADC_Vsys_Channel.json`）。`SequenceCanvas._on_load()` 与 `CustomTestUI.load_template()` 现均复用 `load_sequence_file()`。
- **回归基线**: `tests/test_custom_test_phase0.py` 使用标准库 `unittest`，在项目 `.venv` 下已跑通；系统 Python 缺 PySide6 时按测试类 skip。

## Phase 1: 抽离执行内核到 core

目标：先做“移动和兼容”，不大改行为。

### Task 1.1: 新建 `core/custom_test/` 并迁移模型文件

- **目标**: 将执行内核从 UI 包移动到 core 包。
- **详细内容**:
  - 迁移 `context.py` 到 `core/custom_test/context.py`。
  - 迁移 `executor.py` 到 `core/custom_test/executor.py`。
  - 迁移 `nodes/base_node.py` 到 `core/custom_test/nodes/base.py`。
  - 抽出 `runtime.py` 承载 `execute_children()`，避免节点继续 import executor 私有函数。
  - 保留 `ui/pages/custom_test/context.py`、`executor.py`、`nodes/base_node.py` shim，短期只 re-export core 对象。
  - 明确 registry 初始化入口，避免 `NODE_REGISTRY` 因 import 顺序不同而为空。
  - UI 侧保留兼容 import 或一次性替换 import。
  - 保证现有 JSON `node_type` 不变。
- **涉及文件**:
  - 新增 `core/custom_test/`
  - 修改 `ui/pages/custom_test/custom_test_ui.py`
  - 修改 `ui/pages/custom_test/sequence_canvas.py`
  - 修改 `ui/pages/custom_test/property_panel.py`
  - 修改 `ui/pages/custom_test/record_data_editor.py`
  - 修改 `ui/pages/custom_test/node_palette.py`
- **依赖**: Task 0.1, Task 0.2, Task 0.3
- **预计工作量**: 1 会话
- **预计会话**: 会话 2
- **完成日期**: 2026-05-28
- **完成摘要**: 新增 `core/custom_test/`；`ExecutionContext`、`CustomTestExecutor`、`BaseNode` 已迁移到 core；旧 UI 路径保留 re-export shim；registry 由 `core.custom_test.nodes` 初始化。
- **风险备注**: `core/__init__.py` 改为惰性导出，避免仅导入 `core.custom_test` 时触发 PySide6 依赖；旧路径 shim 已保留 Phase 0 兼容。
- **状态**: ✅ 已完成

### Task 1.2: 迁移节点实现到 `core/custom_test/nodes/`

- **目标**: 将 logic / value / io / instrument 节点迁移到 core。
- **详细内容**:
  - 移动 `logic_nodes.py`、`value_nodes.py`、`io_nodes.py`、`instrument_nodes.py`。
  - 修正 import。
  - 保留旧路径 shim，避免一次性破坏模板和外部引用。
  - 明确禁止节点 import Qt Widgets。
- **涉及文件**:
  - `core/custom_test/nodes/*.py`
  - `ui/pages/custom_test/nodes/*.py`
  - `ui/pages/custom_test/*`
- **依赖**: Task 1.1
- **预计工作量**: 1 ~ 1.5 会话
- **预计会话**: 会话 3
- **完成日期**: 2026-05-28
- **完成摘要**: `logic_nodes.py`、`value_nodes.py`、`io_nodes.py`、`instrument_nodes.py` 已迁移到 `core/custom_test/nodes/`；旧 `ui/pages/custom_test/nodes/*` 文件改为 shim；UI 主要 import 已切到 core。
- **风险备注**: 节点实现不再 import Qt Widgets；`PromptUser` 改走 `ExecutionContext.request_user_prompt()`，当前无 UI handler 时按 Phase 0 unsupported 决策阻止静默等待。
- **状态**: ✅ 已完成

### Task 1.3: 消除节点对 `_execute_children()` 的反向 import

- **目标**: 让容器节点不再依赖 executor 内部函数。
- **详细内容**:
  - 引入 `NodeRuntime` 或在 `ExecutionContext` 注入 `execute_children(children)` 回调。
  - 容器节点调用 runtime/context 提供的执行接口。
  - Break / Continue 行为保持兼容。
  - 覆盖 `LoopRange`、`LoopList`、`IfBlock`、`IfElse`、`IfThenElse`、`Group`、`LoopCount`、`LoopDuration`、`WhileLoop`、`RepeatUntil`、`I2CTraverse`。
- **涉及文件**:
  - `core/custom_test/executor.py`
  - `core/custom_test/context.py`
  - `core/custom_test/runtime.py`
  - `core/custom_test/nodes/logic_nodes.py`
  - `core/custom_test/nodes/instrument_nodes.py` 中 `I2CTraverse`
- **依赖**: Task 1.2
- **预计工作量**: 1 会话
- **预计会话**: 会话 4
- **完成日期**: 2026-05-28
- **完成摘要**: 新增 `core/custom_test/runtime.py`，提供 `execute_node()` / `execute_children()`；容器节点统一调用 `context.execute_children()`；旧 `_execute_children` 仅在 UI shim 中保留兼容导出。
- **风险备注**: 已覆盖 `LoopRange`、`LoopList`、`IfBlock`、`IfElse`、`IfThenElse`、`Group`、`LoopCount`、`LoopDuration`、`WhileLoop`、`RepeatUntil`、`I2CTraverse` 的反向 import 清理。
- **状态**: ✅ 已完成

## Phase 2: 统一仪器解析和运行前校验

目标：让 Run 前就知道能不能跑，以及到底用哪些仪器。

### Task 2.1: 建立节点 capability 声明

- **目标**: 每个仪器节点声明所需 capability。
- **详细内容**:
  - 为 BaseNode 增加 `required_capabilities` 或 `required_instruments()`。
  - N6705C、Scope、Chamber、I2C、UART、MCU IO、RF Analyzer 节点全部标记。
  - capability 命名使用 Custom Test 语义层；resolver 内部再映射到现有 `InstrumentProfile.capabilities`。
  - 对 `ScopeGetDvmDC` 这类型号特定能力，标记 `scope.dvm`，避免 DSOX4034A 被错误匹配。
  - 逻辑/IO/value 节点标记为空。
- **涉及文件**:
  - `core/custom_test/nodes/base.py`
  - `core/custom_test/nodes/instrument_nodes.py`
  - `core/custom_test/nodes/io_nodes.py`
  - `core/custom_test/nodes/logic_nodes.py`
- **依赖**: Phase 1
- **预计工作量**: 0.5 ~ 1 会话
- **预计会话**: 会话 5
- **完成日期**: 2026-05-28
- **完成内容**: `BaseNode` 增加 `required_capabilities` / `required_instruments()`；仪器节点按 Custom Test 语义层声明 capability，`ScopeGetDvmDC` 独立标记 `scope.dvm`；`RFAnalyzerMeasure` 标记 unsupported。
- **风险备注**: capability 先集中声明在 `instrument_nodes.py` 尾部，后续如新增仪器节点需同步补表；逻辑/IO/value 节点默认无仪器 capability。
- **状态**: ✅ 已完成

### Task 2.2: 新建 `InstrumentResolver`

- **目标**: 统一把 sequence 所需 capability 解析为运行时 adapters。
- **详细内容**:
  - 从 `instrument_manager` snapshot/session 解析优先。
  - 对 legacy top refs 提供过渡兼容，但标记为 fallback。
  - I2C / UART / MCU IO 不再由 UI 临时拼装，统一通过 resolver。
  - resolver 负责把不同来源实例包装成统一 adapter：
    - `I2CInterface` / `BesUsbI2C` → `I2CAdapter.read/write`
    - `SerialComMixin` / `serial.Serial` → `UARTAdapter.send/receive`
    - raw N6705C / Scope / Chamber / MCU IO → 对应 typed adapter
  - 输出 resolved source：manager / legacy_top / page_mixin / mock / missing。
  - 返回 `ResolvedInstruments` 和缺失列表。
- **涉及文件**:
  - 新建 `core/custom_test/resolver.py`
  - 修改 `ui/pages/custom_test/custom_test_ui.py`
  - 参考 `core/instruments/instrument_manager.py`
- **依赖**: Task 2.1
- **预计工作量**: 1 ~ 1.5 会话
- **预计会话**: 会话 5 ~ 6
- **完成日期**: 2026-05-28
- **完成内容**: 新增 `core/custom_test/resolver.py`，实现 manager 优先解析、legacy fallback、I2C/UART adapter wrapper、resolved source/missing/warning 输出与 lease session 列表。
- **风险备注**: legacy fallback 会显式 warning 且无法 lease；I2C 自动创建已从 UI 移入 resolver，但真实 DLL/硬件仍需真机 smoke 验证。
- **状态**: ✅ 已完成

### Task 2.3: 建立 preflight validation

- **目标**: Run 前一次性提示所有阻塞项。
- **详细内容**:
  - 校验空序列。
  - 校验未知节点类型。
  - 校验必需仪器缺失。
  - 校验未实现 capability，例如 RF Analyzer。
  - 校验 unsupported 节点，例如未接收端的 PromptUser。
  - 校验明显非法参数：循环 step=0、负 timeout、空 result_var、非法表达式。
  - 校验变量引用：引用不存在时 warning/error 分级；运行期才产生的循环变量需由变量分析器识别。
  - 校验模板格式与版本：未知 version 给出 migration issue。
  - 输出 `ValidationIssue(severity, node_uid, message, fix_hint)`。
- **涉及文件**:
  - 新建 `core/custom_test/validation.py`
  - 修改 `custom_test_ui.py` Run 流程
  - 可选新增 UI validation panel 或复用 logs + QMessageBox
- **依赖**: Task 2.1, Task 2.2
- **预计工作量**: 1 会话
- **预计会话**: 会话 6
- **完成日期**: 2026-05-28
- **完成内容**: 新增 `core/custom_test/validation.py`，覆盖空序列、unsupported 节点、必需仪器缺失/busy、明显非法参数、表达式语法和基础变量引用 warning；UI Run 入口复用 Logs + QMessageBox 展示。
- **风险备注**: 变量分析为 Phase 2 基础版，动态外部注入变量会以 warning 呈现；正式可点击 issue 面板留到 Phase 4.3。
- **状态**: ✅ 已完成

### Task 2.4: 运行上下文只接收 resolver 输出

- **目标**: 删除 `_on_run()` 中散落的仪器注入逻辑。
- **详细内容**:
  - `ExecutionContext` 改为接收 `adapters` / `resolved_instruments`。
  - `_on_run()` 只负责调用 resolver 和 runner。
  - 保留一层兼容参数，确保旧页面仍可创建 Custom Test。
- **涉及文件**:
  - `core/custom_test/context.py`
  - `core/custom_test/resolver.py`
  - `ui/pages/custom_test/custom_test_ui.py`
- **依赖**: Task 2.2, Task 2.3
- **预计工作量**: 1 会话
- **预计会话**: 会话 7
- **完成日期**: 2026-05-28
- **完成内容**: `ExecutionContext` 接收 resolver 输出的 adapters / `ResolvedInstruments` / lease session ids；`CustomTestUI._on_run()` 删除散落的仪器注入逻辑，只负责 resolver、preflight、context 和 runner 启动。
- **风险备注**: 保留 legacy source 兼容旧页面状态；`populate_instruments_from_manager()` 仍保留给旧调用方。
- **状态**: ✅ 已完成

### Task 2.5: 运行期 Instrument Lease 管理

- **目标**: Custom Test 运行期间独占已解析的 manager session，避免其它页面同时操作同一仪器。
- **详细内容**:
  - resolver 返回需要 lease 的 session_id 列表。
  - runner 启动前调用 `InstrumentManager.create_lease(session_id, owner="custom_test")`。
  - 任一 lease 申请失败时 preflight/Run 阻止执行，并显示 busy owner。
  - 执行完成、异常、用户 Stop、窗口关闭时在 `finally` 释放全部 lease。
  - legacy fallback 无法 lease 时，在日志中显式标记风险。
- **涉及文件**:
  - `core/custom_test/resolver.py`
  - `core/custom_test/executor.py`
  - `ui/pages/custom_test/custom_test_ui.py`
  - `core/instruments/instrument_manager.py`（仅按需复用，不优先改）
- **依赖**: Task 2.2, Task 2.4
- **预计工作量**: 0.5 ~ 1 会话
- **预计会话**: 会话 7
- **完成日期**: 2026-05-28
- **完成内容**: resolver 返回 manager session id；`ExecutionContext.acquire_leases()` 在 runner 启动前申请 lease；`CustomTestExecutor.run()` 在 `finally` 统一释放 lease 与 resolver 持有的 owned runtime 资源。
- **风险备注**: manager session lease 路径已由 fake manager 单测覆盖；真实多页面并发占用仍需 UI/真机回归。
- **状态**: ✅ 已完成

## Phase 3: 结果模型和导出统一

目标：Data 表、Chart、自动导出、手动导出都使用同一份结果模型。

### Task 3.1: 新建 Result Model

- **目标**: 定义统一结果行、字段 schema 和格式化规则。
- **详细内容**:
  - `ResultField`: name, unit, dtype, precision, plot, export。
  - `ResultRow`: values, source_node_uid, timestamp, status。
  - `ResultStore`: canonical records + field registry + append/update API。
  - `ResultViewState`: visible columns, display name, order, format, hidden state。
  - 支持动态列扩展。
  - 支持十六进制值和数值值并存。
- **涉及文件**:
  - 新建 `core/custom_test/result_store.py`
  - 修改 `core/custom_test/context.py`
  - 修改 `core/custom_test/nodes/io_nodes.py`
- **依赖**: Phase 1
- **预计工作量**: 1 会话
- **预计会话**: 会话 8
- **完成日期**: 2026-05-29
- **完成内容**: 新增 `core/custom_test/result_store.py`，定义 `ResultField` / `ResultRow` / `ResultStore` / `ResultViewState`，支持动态字段注册、字段格式推断、可绘图字段筛选、visible view state 与 canonical records 分离；`ExecutionContext` 通过 `result_store` 记录数据并保留 `context.records` 兼容旧调用。
- **风险备注**: source node uid 已由 `runtime.execute_node()` 注入；sequence hash 仍预留为空，正式序列版本迁移时再补稳定 hash 来源。
- **状态**: ✅ 已完成

### Task 3.2: UI Data / Chart 绑定 Result Model

- **目标**: UI 不再自行推断第一行 keys 和精度。
- **详细内容**:
  - Data 表收到新字段时自动扩列。
  - Chart 只绘制标记为可绘图的数值字段。
  - 用户重命名/隐藏/格式化列不破坏原始 records。
  - 手动导出默认按当前 visible view；自动导出和 ExportResult 默认按 canonical records。
- **涉及文件**:
  - `ui/pages/custom_test/custom_test_ui.py`
  - `core/custom_test/result_store.py`
- **依赖**: Task 3.1
- **预计工作量**: 1 ~ 1.5 会话
- **预计会话**: 会话 9
- **完成日期**: 2026-05-29
- **完成内容**: `CustomTestUI` 的 Data 表与 Chart 改为从 `ResultStore` 渲染；新字段会自动扩列；Chart 只绘制 `ResultField.plot=True` 的数值字段；列重命名、隐藏、格式化和排序写入 `ResultViewState`，不修改 canonical records。
- **风险备注**: Data 表当前采用整表刷新策略，保证动态列一致性；超大数据量下后续可在 Phase 4.2 拆分结果面板时优化为增量渲染。
- **状态**: ✅ 已完成

### Task 3.3: 统一 CSV/XLSX 导出

- **目标**: 自动导出、ExportResult 节点、手动 Export 按钮走同一套导出函数。
- **详细内容**:
  - 支持 UTF-8-SIG CSV。
  - 支持 XLSX 样式。
  - 支持输出 manifest：sequence hash、start/end time、instrument snapshot。
  - 文件名统一：`custom_test_<chip_or_profile>_<YYYYMMDD_HHMMSS>.csv`。
- **涉及文件**:
  - `core/custom_test/result_store.py`
  - `core/custom_test/nodes/io_nodes.py`
  - `ui/pages/custom_test/custom_test_ui.py`
- **依赖**: Task 3.1, Task 3.2
- **预计工作量**: 1 会话
- **预计会话**: 会话 10
- **完成日期**: 2026-05-29
- **完成内容**: `ResultStore.export_csv()` / `export_xlsx()` / `export()` 统一负责 UTF-8-SIG CSV、XLSX 样式和 manifest 输出；`ExportResult` 节点、自动导出、手动 Export 按钮均复用同一导出 API；默认自动文件名改为 `custom_test_<chip_or_profile>_<YYYYMMDD_HHMMSS>.csv`。
- **风险备注**: XLSX 导出依赖现有 `openpyxl`；若节点导出 XLSX 失败会回退 CSV 并记录 warning。已新增 `tests/test_custom_test_phase3.py` 覆盖 ResultStore、视图导出、ExportResult 节点导出和 manifest。
- **状态**: ✅ 已完成

## Phase 4: UI 拆分和体验完善

目标：降低 `custom_test_ui.py` 体积，提高可维护性。

### Task 4.1: 拆分仪器连接区域

- **目标**: 把 `_refresh_instrument_connections()`、meta 应用、自动连接、MCU IO UI 拆出。
- **建议新文件**:
  - `ui/pages/custom_test/instrument_connection_panel.py`
  - 或 `ui/pages/custom_test/panels/instrument_connection_panel.py`
- **详细内容**:
  - 该 panel 只展示 resolver/preflight 需要的仪器状态。
  - 过渡期仍支持现有连接 Mixin。
  - 自动连接逻辑迁移到 resolver 或 manager 后，UI 只触发请求。
- **涉及文件**:
  - `custom_test_ui.py`
  - 新增 panel 文件
- **依赖**: Phase 2
- **预计工作量**: 1 会话
- **预计会话**: 会话 11
- **完成日期**: 2026-05-29
- **完成内容**: 新增 `ui/pages/custom_test/instrument_connection_panel.py`，承接仪器连接区刷新、模板 instruments meta 应用、自动连接、MCU IO 搜索/连接状态与 manager 事件处理；`CustomTestUI` 保留连接 Mixin 兼容入口，只负责面板组装与少量委托。
- **风险备注**: 过渡期仍复用现有 N6705C / Chamber / UART Mixin 与 legacy top ref；后续若连接 Mixin 信号绑定语义变化，需要回归连接区重复刷新场景。
- **状态**: ✅ 已完成

### Task 4.2: 拆分结果面板

- **目标**: 把 Logs / Data / Chart 相关逻辑拆出页面。
- **建议新文件**:
  - `ui/pages/custom_test/result_panel.py`
- **详细内容**:
  - `append_log`
  - `set_progress`
  - `append_result_row`
  - `clear_results`
  - `export_visible_table`
  - `plot_result_fields`
- **涉及文件**:
  - `custom_test_ui.py`
  - 新增 `result_panel.py`
- **依赖**: Phase 3
- **预计工作量**: 1 会话
- **预计会话**: 会话 12
- **完成日期**: 2026-05-29
- **完成内容**: 新增 `ui/pages/custom_test/result_panel.py`，承接 Logs / Data / Chart 构建、进度、结果行渲染、可见表格导出、列重命名/隐藏/排序/格式化与 ResultStore 绘图字段渲染；`CustomTestUI` 仅切换当前运行的 `ResultStore` 并转发执行信号。
- **风险备注**: Data 表仍沿用 Phase 3 的整表刷新策略；超大结果集的增量渲染可留到 Phase 5 稳定性优化。
- **状态**: ✅ 已完成

### Task 4.3: 运行前校验 UI

- **目标**: 用户点击 Run 后，如果有阻塞问题，用结构化 UI 告知。
- **详细内容**:
  - Error 阻止运行。
  - Warning 允许继续，但需要用户确认。
  - 点击 issue 可定位到对应节点。
  - 对缺失仪器给出“去连接/刷新/选择 session”的引导。
- **涉及文件**:
  - `custom_test_ui.py`
  - `sequence_canvas.py`
  - 可选新增 `validation_panel.py`
- **依赖**: Task 2.3
- **预计工作量**: 1 会话
- **预计会话**: 会话 13
- **完成日期**: 2026-05-29
- **完成内容**: 新增 `ui/pages/custom_test/validation_panel.py`，将 preflight issues 以结构化表格展示；Error 阻止运行，Warning 可由用户确认继续；点击含 `node_uid` 的 issue 会调用 `SequenceCanvas.locate_node()` 定位到对应节点。
- **风险备注**: 当前缺失仪器引导主要依赖 `ValidationIssue.fix_hint` 文案和左侧连接区，尚未实现一键跳转/刷新 session 的专用动作按钮。
- **状态**: ✅ 已完成

### Task 4.4: PromptUser 正规化

- **目标**: 移除节点内对 QApplication 私有方法的隐藏依赖。
- **详细内容**:
  - 先补一条 smoke：包含 PromptUser 的序列必须能弹窗/取消/超时/停止。
  - `ExecutionContext` 提供 `request_user_prompt(message)` 抽象回调。
  - UI runner 接收 prompt signal，显示 QMessageBox 或专用 dialog。
  - worker 等待线程安全响应对象。
  - 支持 timeout、cancel、stop。
- **涉及文件**:
  - `core/custom_test/context.py`
  - `core/custom_test/nodes/logic_nodes.py`
  - `ui/pages/custom_test/custom_test_ui.py`
- **依赖**: Phase 1
- **预计工作量**: 0.5 ~ 1 会话
- **预计会话**: 会话 13
- **完成日期**: 2026-05-29
- **完成内容**: `CustomTestUI` 为 `ExecutionContext` 注入线程安全 prompt handler，通过 `prompt_requested` signal 在主线程显示 `QMessageBox`；worker 通过 `_PromptRequest` 等待响应，支持确认、取消、超时和 Stop 关闭弹窗；移除 `PromptUser.unsupported_reason`，并将 PromptUser 从 unsupported 节点清单恢复为可选节点。
- **风险备注**: 已覆盖 handler smoke 与 UI 实例化 smoke；真实人工弹窗交互仍需在桌面运行时手测确认多屏/焦点体验。
- **状态**: ✅ 已完成

## Phase 5: 稳定性、Mock 和长期能力

目标：让 Custom Test 能成为稳定的自动化测试平台能力。

### Task 5.1: 为长耗时节点建立统一 cancellation 协议

- **目标**: Stop 在长等待、长轮询、长串口读取时可预测地生效。
- **详细内容**:
  - `ExecutionContext` 提供 `sleep(seconds, poll=0.1)`。
  - adapter 长操作接收 `stop_check`。
  - 所有 `time.sleep()` 替换为 context sleep 或 adapter wait。
  - 温箱等待、UARTReceive、I2CTraverse、Delay、LoopDuration 重点覆盖。
- **涉及文件**:
  - `core/custom_test/context.py`
  - `core/custom_test/nodes/logic_nodes.py`
  - `core/custom_test/nodes/instrument_nodes.py`
- **依赖**: Phase 1
- **预计工作量**: 1 会话
- **预计会话**: 会话 14
- **完成日期**: 2026-05-29
- **完成内容**: `ExecutionContext` 新增 `sleep(seconds, poll=0.1)` 统一可取消等待入口；`Delay`、`WaitUntil`、`LoopDuration` 相关等待、温箱等待、`MCUIOPulse`、`UARTReceive` 与 executor/runtime pause loop 改为使用 context sleep；I2C adapter read/write 与 UART adapter read_available 支持 `stop_check`。
- **风险备注**: 真实仪器单次阻塞 IO 仍受底层驱动超时限制；本阶段保证长等待/轮询/Mock adapter 路径可预测响应 Stop。
- **状态**: ✅ 已完成

### Task 5.2: 建立 Mock Instrument Adapters

- **目标**: Custom Test 能在 `DEBUG_MOCK=True` 或测试环境下完整跑通。
- **详细内容**:
  - N6705C mock adapter。
  - Scope mock adapter。
  - Chamber mock adapter。
  - I2C / UART / MCU IO mock adapter。
  - manager session mock 与 legacy fallback mock 都要覆盖。
  - 形成 3 条 smoke sequence：纯逻辑、仪器测量、温箱循环。
- **涉及文件**:
  - `core/custom_test/adapters/*`
  - `instruments/mock/mock_instruments.py`
  - 测试或 smoke 脚本
- **依赖**: Phase 2
- **预计工作量**: 1 ~ 1.5 会话
- **预计会话**: 会话 15
- **完成日期**: 2026-05-29
- **完成内容**: 新增 `core/custom_test/adapters/`，将 passthrough、I2C、UART adapter 独立为 core runtime adapter；新增 Mock adapter 工厂并接入 `InstrumentResolver(allow_mock=True)` / `DEBUG_MOCK=True` fallback；`instruments/mock/mock_instruments.py` 新增 `MockUART`；新增 `tests/test_custom_test_phase5.py` 覆盖纯逻辑、Mock 仪器测量、温箱循环 3 条 smoke。
- **风险备注**: RF Analyzer 仍按既有 unsupported 决策处理，不提供 Mock fallback；Mock fallback 默认只在 `DEBUG_MOCK=True` 或显式 `allow_mock=True` 下启用，不改变真机默认解析路径。
- **状态**: ✅ 已完成

### Task 5.3: 序列版本迁移

- **目标**: 后续 schema 调整不破坏旧模板。
- **详细内容**:
  - Phase 0 先做读取兼容；本任务再做正式 schema 版本迁移。
  - 当前 JSON 视为 v1。
  - 新格式视为 v2。
  - `serialization.py` 提供 `load_sequence()`、`save_sequence()`、`migrate_sequence()`.
  - 对未知节点和缺失参数给出可读 issue。
- **涉及文件**:
  - 新建 `core/custom_test/serialization.py`
  - 修改 `sequence_canvas.py`
  - 修改模板加载逻辑
- **依赖**: Phase 1
- **预计工作量**: 1 会话
- **预计会话**: 会话 16
- **完成日期**: 2026-05-29
- **完成内容**: 新增 `core/custom_test/serialization.py`，提供 `load_sequence()`、`save_sequence()`、`migrate_sequence()` 以及 data/file 细分入口；list/v1 dict 自动迁移为 v2；保存序列默认写 `version: 2` 与 `metadata.required_capabilities`；未知节点、非 dict 节点、缺失参数、非法 children 均生成可读 issue；`ui/pages/custom_test/sequence_io.py` 改为兼容 shim，`sequence_canvas.py` 保存/加载改走 core serialization。
- **风险备注**: 未知节点当前会生成 issue 并跳过加载，避免整个模板崩溃；如未来需要无损 round-trip，可追加 UnknownNode 占位模型。
- **状态**: ✅ 已完成

### Task 5.4: 模板库和样例流程

- **目标**: 给用户可直接使用的 Custom Test 样例。
- **详细内容**:
  - N6705C 电压扫描模板。
  - I2C register sweep 模板。
  - 温箱温度循环 + N6705C 测量模板。
  - UART send/receive 验证模板。
  - 每个模板附 required capabilities。
- **涉及文件**:
  - `userdata/custom_test_templates/*.json`
  - 可选 `helps/custom_test.html`
- **依赖**: Phase 2, Phase 3
- **预计工作量**: 0.5 ~ 1 会话
- **预计会话**: 会话 16
- **完成日期**: 2026-05-29
- **完成内容**: 新增 4 个 v2 样例模板：`sample_n6705c_voltage_sweep.json`、`sample_i2c_register_sweep.json`、`sample_chamber_n6705c_loop.json`、`sample_uart_send_receive.json`，每个模板均带 `metadata.required_capabilities`；模板目录后续应统一为 `userdata/custom_test_templates`，并由打包配置按该目录收集运行时数据。
- **风险备注**: 样例参数偏 smoke/入门，真实产品流程仍需按芯片和实验条件调整；未新增 help 文档，仅复用现有 Custom Test 页面入口。
- **状态**: ✅ 已完成

---

## 7. 会话窗口评估

### 7.1 最小可交付版本

目标：修正最大架构问题，但尽量不改变 UI 行为。

| 范围 | 包含任务 | 预计会话 |
|---|---|---|
| 基线保护 | Phase 0 | 1 ~ 2 |
| core 迁移 | Phase 1 | 3 |
| 简化仪器解析 | Task 2.1 ~ 2.2 + 2.5 | 2 |
| 基础 preflight | Task 2.3 | 1 |
| 合计 | 约 10 个任务 | 7 ~ 8 会话 |

适合目标：先把 Custom Test 从“UI 内嵌执行器”升级为“core 执行能力”，后续再慢慢完善结果和 UI。

### 7.2 推荐完整版本

目标：完整解决分层、仪器解析、结果模型、UI 拆分和稳定性。

| 范围 | 包含任务 | 预计会话 |
|---|---|---|
| Phase 0 | 基线保护 | 1 ~ 2 |
| Phase 1 | 执行内核迁移 | 3 |
| Phase 2 | 仪器解析 + preflight + lease | 3 ~ 4 |
| Phase 3 | 结果模型 + 导出统一 | 3 |
| Phase 4 | UI 拆分 + PromptUser | 3 |
| Phase 5 | 稳定性 + Mock + 版本迁移 + 模板 | 3 |
| 合计 | 全量优化 | 17 ~ 19 会话 |

适合目标：把 Custom Test 做成后续长期扩展的稳定平台能力。

### 7.3 保守完整版本

如果每个阶段都要求真机验证、打包验证、模板迁移、回归 PMU/Charger/Consumption 对共享仪器管理的影响，则建议预留：

- **20 ~ 24 会话**
- 每会话完成 1 个中等任务或 2 个小任务。
- 每 3 ~ 4 会话做一次集中回归。

---

## 8. 推荐执行顺序

推荐按以下节奏推进：

| 会话 | 任务 | 预计产出 |
|---|---|---|
| 会话 1 | Task 0.1 + 0.3 | 节点清单 + 统一序列读取入口 |
| 会话 2 | Task 0.2 + 0.4 | 最小执行回归 + unsupported/legacy 节点决策 |
| 会话 3 | Task 1.1 | `core/custom_test/context.py` + `executor.py` 初步迁移 |
| 会话 4 | Task 1.2 | nodes 迁移到 core，旧路径兼容 |
| 会话 5 | Task 1.3 | 消除 `_execute_children` 反向 import |
| 会话 6 | Task 2.1 + 2.2 起步 | capability 声明 + resolver / adapter 雏形 |
| 会话 7 | Task 2.2 完成 + 2.3 | manager 优先解析 + preflight |
| 会话 8 | Task 2.4 + 2.5 | `_on_run()` 瘦身 + Instrument Lease |
| 会话 9 | Task 3.1 | Result Model / ResultStore |
| 会话 10 | Task 3.2 | Data/Chart 绑定结果模型 |
| 会话 11 | Task 3.3 | 导出统一 |
| 会话 12 | Task 4.1 | 仪器连接区域拆分 |
| 会话 13 | Task 4.2 | 结果面板拆分 |
| 会话 14 | Task 4.3 + 4.4 | 校验 UI + PromptUser 正规化 |
| 会话 15 | Task 5.1 | cancellation 协议 |
| 会话 16 | Task 5.2 | Mock adapters + smoke sequences |
| 会话 17 | Task 5.3 | 序列迁移 |
| 会话 18 | Task 5.4 | 模板库 |

---

## 9. 风险评估

### 9.1 高风险点

1. 旧模板兼容性
   - 风险：节点路径迁移后旧 JSON 加载失败。
   - 缓解：`node_type` 保持不变，旧路径保留 shim，添加 migration。

2. 仪器 manager 兼容性
   - 风险：部分页面仍依赖 legacy top ref。
   - 缓解：resolver 先 manager 优先，legacy fallback 过渡，日志标记 fallback 来源。

3. 长流程停止响应
   - 风险：真实仪器 IO 阻塞导致 stop 不及时。
   - 缓解：adapter timeout + stop_check，长等待统一 context sleep。

4. 结果模型改造影响 UI
   - 风险：Data/Chart/Export 三处行为不一致。
   - 缓解：先引入 ResultStore，再逐个切 UI。

5. 一次性移动文件过多
   - 风险：import 链断裂，难以定位。
   - 缓解：Phase 1 分三次迁移，每次做 smoke test。

6. Adapter 表面不一致
   - 风险：manager session 实例和当前节点期望方法不一致，迁移后“有连接但节点不可调用”。
   - 缓解：先定义 runtime adapter protocol，对每类来源做 wrapper 测试。

7. PromptUser 无 UI 接收端
   - 风险：流程运行到 PromptUser 后无弹窗，等待超时或无法继续。
   - 缓解：Phase 0 决定隐藏/禁用/补齐；Phase 4 正规化 signal/dialog。

8. 仪器并发占用
   - 风险：Custom Test 长流程运行时其它页面同时操作同一 session。
   - 缓解：resolver + runner 申请 `InstrumentLease`，异常路径释放。

### 9.2 中风险点

1. PySide6 环境不完整时无法本地启动 UI。
2. I2C / MCU IO / UART 的当前实际连接路径可能依赖页面对象。
3. RF Analyzer 节点当前属于占位功能，需要明确是隐藏、禁用还是实现。
4. `PromptUser` 需要线程安全交互，不能让 worker 直接操作 QMessageBox。
5. 内置模板存在 list / dict 两种格式，必须保证所有加载入口兼容。
6. Frequency Counter 已接入 manager 但未接入 Custom Test 节点，容易造成能力预期不一致。

---

## 10. 验收标准

### 10.1 架构验收

- `core/custom_test/` 存放执行引擎、上下文、节点、校验、结果模型。
- `ui/pages/custom_test/` 不再直接保存核心执行逻辑。
- 节点不 import Qt Widgets。
- 节点不 import executor 内部函数。
- UI 不在 Run 流程里临时创建底层 I2C。
- UI 不把页面对象作为 UART / I2C / MCU IO runtime 直接注入节点；必须通过 adapter。
- runner 能对 manager session 申请并释放 lease。

### 10.2 功能验收

- 旧 JSON 序列可加载。
- 顶层 list 模板与 `{version, sequence, instruments}` 模板均可加载。
- 纯逻辑序列可运行。
- N6705C 测量序列可运行。
- I2C read/write 序列可运行。
- 温箱 wait stable 序列可停止。
- UART send/receive 序列可运行。
- PromptUser 节点要么可用，要么在 preflight 中明确 unsupported，不能运行时静默等待。
- Data 表和自动 CSV 导出字段一致。
- Run 前缺失仪器能提示，不进入半执行状态。
- 仪器 busy / 被其它页面占用时 Run 前提示。

### 10.3 回归验收

- `DEBUG_MOCK=True` 下至少 3 条 smoke sequence 跑通。
- 主程序可打开 Custom Test 页面。
- 保存/加载序列正常。
- Run / Pause / Resume / Stop 正常。
- 关闭主窗口时执行线程能清理。
- 若新增资源或 help，按同步矩阵更新 spec / helps / DIRECTORY_STRUCTURE。

---

## 11. 每次会话执行规则

1. 每次会话开始先读本文档，确认当前 Phase 和 Task。
2. 单次会话优先完成一个闭环任务，不跨太多层。
3. 每次涉及迁移都必须保持旧模板兼容。
4. 每次涉及执行器都至少跑纯逻辑 smoke。
5. 每次涉及仪器解析都至少跑 Mock 或 manager snapshot smoke。
6. 每次结束更新本文档的 Task 状态、完成日期、涉及文件和风险备注。
7. 未经用户明确要求，不主动 git commit。

---

## 12. 变更履历

| 日期 | 会话 | 内容 | 状态 |
|---|---|---|---|
| 2026-05-28 | 规划 | 建立 Custom Test 优化总方案、工作量评估和会话窗口 | ✅ 已记录 |
| 2026-05-28 | 查漏补缺 | 补充模板格式混用、registry import 副作用、manager capability/lease、adapter 接口差异、PromptUser 接收端、结果 view state、RF/Frequency Counter 边界等风险；调整 Phase 0/2 与会话估算 | ✅ 已记录 |
| 2026-05-28 | Phase 0 | 完成节点清单/状态基线、list/dict 序列统一读取入口、最小无 UI smoke、RFAnalyzerMeasure/PromptUser unsupported 决策；新增 `node_metadata.py`、`sequence_io.py`、`tests/test_custom_test_phase0.py` | ✅ 已完成 |
| 2026-05-28 | Phase 1 | 完成 `core/custom_test/` 执行内核迁移、节点实现迁移、旧路径 shim、`runtime.py` 子节点执行入口与 `_execute_children` 反向 import 清理；`core/__init__.py` 改为惰性导出以保持无 UI smoke 可导入 | ✅ 已完成 |
| 2026-05-28 | Phase 2 | 完成节点 capability 声明、`InstrumentResolver`、preflight validation、`_on_run()` resolver 化、manager session lease 申请/释放；新增 `tests/test_custom_test_phase2.py` | ✅ 已完成 |
| 2026-05-29 | Phase 3 | 完成 Result Model / ResultStore、Data/Chart 绑定统一结果模型、自动/手动/节点导出统一；新增 `core/custom_test/result_store.py` 与 `tests/test_custom_test_phase3.py` | ✅ 已完成 |
| 2026-05-29 | Phase 4 | 完成仪器连接区、结果面板、运行前校验 UI 拆分；PromptUser 改为 UI signal/dialog 正规化路径；新增 `instrument_connection_panel.py`、`result_panel.py`、`validation_panel.py` 与 `tests/test_custom_test_phase4.py` | ✅ 已完成 |
| 2026-05-29 | Phase 5 | 完成 cancellation 协议、Mock runtime adapters、序列 v2 迁移/保存入口、4 个样例模板与 Phase 5 smoke；新增 `core/custom_test/adapters/`、`core/custom_test/serialization.py`、`tests/test_custom_test_phase5.py` 与 `sample_*.json` 模板 | ✅ 已完成 |

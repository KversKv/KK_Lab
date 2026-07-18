# Orchestrator

Orchestrator 是**节点式可视化测试序列编辑器与执行器**：通过拖拽节点（仪器控制、IO 操作、逻辑分支、变量赋值等）编排测试流程，支持模板复用、变量传递、运行历史、结果存储。

> 详细架构与扩展指引见 `docs/ai/feature_requests/Orchestrator/Orchestrator_OptimizationPlan.md` 与 `docs/user/CustomTestStructure.md`。

## 页面入口

- 导航栏 → `ORCHESTRATION` → `Orchestrator`
- 对应源码：`ui/pages/orchestrator/orchestrator_ui.py`
- 节点定义：`ui/pages/orchestrator/nodes/`（`base_node.py` / `instrument_nodes.py` / `io_nodes.py` / `logic_nodes.py` / `value_nodes.py`）
- 执行引擎：`core/orchestrator/executor.py`

## 界面布局

三栏 + 顶部工具栏 + 底部结果面板：

### 1. 顶部工具栏
- **New**：新建空白序列。
- **Open**：加载序列文件（`.json`）。
- **Save / Save As**：保存当前序列。
- **Template Gallery**：打开模板库对话框，选择预置模板（位于 `get_primary_template_dir()`）。
- **Validate**：执行 `preflight_validate` 预检（仪器可用性、节点连线完整性、变量引用合法性等），有 issue 时弹 `ValidationIssuesDialog`。
- **Run / Pause / Stop**：执行控制。
- **Recent**：最近使用序列（`record_recent_sequence` 记录）。

### 2. 左侧 — Node Palette（节点库）
按分类折叠展示（`CollapsibleSection`）：
- **Instruments**：N6705C 设置、示波器捕获、温箱控温等节点（来自 `instrument_nodes.py`）。
- **IO**：MCU IO 脉冲、串口发送、I2C 读写等节点（来自 `io_nodes.py`）。
- **Logic**：If / For / While / Delay / Break 等流程控制节点（来自 `logic_nodes.py`）。
- **Values**：常量、变量赋值、表达式求值等节点（来自 `value_nodes.py`）。
- 拖拽节点到中间画布添加。

### 3. 中间 — Sequence Canvas（序列画布）
- 节点矩形 + 连线箭头，可视化展示测试流程。
- 支持拖拽移动节点、点击连线删除、右键节点删除/复制。
- `is_node_selectable` / `filter_selectable_ops` 控制哪些节点可选/可连接。

### 4. 右侧 — Property Panel（属性面板）
- 选中节点后显示其可编辑属性（来自 `node_metadata.py`）。
- 不同节点类型属性不同（如 N6705C 设置节点：通道、电压、电流）。

### 5. 右下 — Instrument Connection Panel（仪器连接面板）
- 列出当前序列需要的所有仪器（`collect_required_instrument_keys`）。
- `InstrumentResolver` 解析每台仪器的连接方式。
- 提供 Connect All / Disconnect All 按钮。

### 6. 底部 — Result Panel（结果面板）
- 执行时实时显示每个节点的执行状态（待执行 / 执行中 / 完成 / 失败 / 跳过）。
- 节点输出值、运行时长、错误信息。
- 执行完成可保存结果到 `ResultStore`（路径由 `build_default_result_path` 生成）。

## 典型操作流程

### 流程一：从模板新建并运行
1. 点击 Template Gallery → 选择模板（如 `pmu_quick_check.json`）→ OK。
2. 画布加载模板节点。
3. 在右下 Instrument Connection Panel 点击 Connect All → 等待所有仪器连接。
4. 点击 Validate → 预检通过。
5. 点击 Run → `ExecutorThread` 启动，逐节点执行。
6. 底部结果面板实时更新；遇 `StopExecution` 异常或失败节点则停止。
7. 执行完成自动写入 `RunHistoryWriter` 与 `ResultStore`。

### 流程二：手动编排新序列
1. 点击 New → 空白画布。
2. 从左侧 Node Palette 拖入：
   - 一个 `N6705C Set Voltage` 节点 → 在右侧设通道 1、电压 3.3V。
   - 一个 `MCU IO Pulse` 节点 → 设引脚 GPIO0、极性 Rising。
   - 一个 `Delay` 节点 → 设 1000ms。
   - 一个 `Serial Send` 节点 → 发送 `version`。
   - 一个 `N6705C Read Current` 节点 → 输出变量 `i_meas`。
   - 一个 `If` 节点 → 判断 `i_meas < 0.5`。
3. 连线：按上述顺序连接节点输出到下一节点输入。
4. Save → 输入文件名 → 保存到序列目录。
5. Validate → Run。

### 流程三：复用变量与表达式
1. 用 `Value: Variable Set` 节点定义变量 `v_target = 3.3`。
2. 后续 `N6705C Set Voltage` 节点的电压属性填 `$v_target`（变量引用语法）。
3. 用 `Value: Expression` 节点写 `v_target * 1.1` 作为过冲测试电压。
4. 执行时 `ExecutionContext` 维护变量字典，节点间可传递。

### 流程四：暂停与续跑
1. Run 后点击 Pause → 当前节点完成后暂停。
2. 修改某些属性 → Resume 续跑（保留变量与已执行节点状态）。
3. 也可 Stop 终止 → 重新 Run 从头开始。

## 关键概念说明

| 概念 | 说明 |
|---|---|
| Node | 序列中的一个操作步骤，继承 `BaseNode` |
| Edge | 节点间的连线，定义执行顺序与数据流 |
| Variable | 序列内的变量，由 `ExecutionContext` 维护 |
| Template | 预置序列，位于 `get_primary_template_dir()` |
| Run History | 每次执行的快照，由 `RunHistoryWriter` 写入 |
| Result Store | 节点输出值的持久化存储，由 `build_default_result_path` 生成路径 |
| Preflight | 运行前预检，由 `preflight_validate` 实现 |

## 注意事项

- **仪器需求收集**：序列加载后自动调用 `collect_required_instrument_keys` 收集所需仪器，未连接的仪器在 Instrument Connection Panel 标红。
- **InstrumentResolver**：解析仪器 key（如 `n6705c:a`）到具体 InstrumentManager 会话，未注册的 key 会导致执行失败。
- **序列哈希**：`build_sequence_hash` 用于 Run History 去重与版本追踪。
- **变量引用语法**：`$var_name` 引用变量；表达式节点支持 Python 表达式求值。
- **StopExecution**：节点可抛 `StopExecution` 异常主动终止序列（如 `Break` 节点）。
- **AI 集成**：本页面实现完整的 AI 契约：
  - `CAP_LIST_STEPS` — 列出序列步骤
  - `CAP_GET_CONFIG` / `CAP_APPLY_CONFIG` — 读写序列配置
  - `CAP_START_TEST` / `CAP_STOP_TEST` / `CAP_PAUSE_TEST` — 启停暂停
  - `CAP_RUN_SINGLE_STEP` — 单步执行
  - `CAP_SET_VARIABLE` — 设置变量
  - `CAP_GET_RESULT` — 读取结果
  AI 助手可通过自然语言操作序列。
- **结果文件**：输出到 `Results/orchestrator/<序列名>/<时间戳>/`，含 JSON 结果 + Run History 记录。
- **Mock 模式**：`DEBUG_MOCK=True` 时所有仪器走 Mock，序列可在无硬件环境跑通。
- **不要硬编码仪器 key**：节点属性中的仪器引用必须来自 Instrument Connection Panel 的下拉框，禁止写入代码。

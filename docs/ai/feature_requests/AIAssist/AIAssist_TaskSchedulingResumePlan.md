# AI Assistant 进阶能力设计：任务调度 + 异步结果回灌

> 范围：在现有「受控动作体系（[AIAssist_ActionCatalog.md](./AIAssist_ActionCatalog.md)）+ agent 多轮 tool-calling 循环」之上，补齐两块当前缺失的能力——
> **① 定时 / 延迟任务调度（Scheduler）**、**② 异步 / 跨回合任务完成后的结果自动回灌（Resume 续跑）**。
> 目标：让「AI 决策 → 发起长任务 / 定时任务 → 任务完成后自动反馈 → AI 继续决策」形成完整闭环。
>
> 原则（与现有架构一致，不破坏分层）：
> 1. **LLM 出计划，确定性引擎管执行**——定时 / 长任务绝不让模型挂在执行回路里。
> 2. **每一步过 `ActionDispatcher`**——异步 / 定时触发的动作仍走风险判定 / 确认 / 审计，不因「机器触发」而绕过。
> 3. **core 不反向依赖 ui**——定时触发器（QTimer）/ 完成事件（Signal）落在 UI 层，core 仅提供纯逻辑注册表 + 续跑入口。
> 4. **禁 import Qt 的模块保持纯逻辑**：新增注册表仿 [draft_registry.py](../../../core/ai/draft_registry.py) 风格（线程安全 + FIFO 上限）。

---

## 1. 现状与缺口（结论先行）

| 能力 | 现状 | 位置 |
|---|---|---|
| AI 多轮 tool-calling（看结果再决策） | ✅ 已有 | [`_handle_agent_round`](../../../core/ai/ai_service.py) |
| **回合内**同步动作结果自动回灌 | ✅ 已有（`role=tool` 消息 + `clip_context_block`） | [`_execute_tool_call`](../../../core/ai/ai_service.py) |
| 阻塞式长任务回灌（如 `chamber_wait_stable`） | ✅ 已有（worker 阻塞等到结果，dispatch 同步返回） | [`chamber.py`](../../../core/ai/actions/handlers/chamber.py) |
| 顺序 + 条件 + 循环任务流引擎 | ✅ 已有（给 custom_test 用） | [`logic_nodes.py`](../../../core/custom_test/nodes/logic_nodes.py) / [`executor.py`](../../../core/custom_test/executor.py) |
| AI 生成测试序列草案 → 预览确认 → 落地 | ✅ 已有 | [`draft_registry.py`](../../../core/ai/draft_registry.py) |
| **定时 / 延迟 / "半小时后执行"调度** | ❌ 缺失 | 本文 §3 |
| **异步 / 跨回合任务完成后的结果自动回灌** | ❌ 缺失 | 本文 §4 |

**两个缺口的本质**：现有反馈闭环依赖 `dispatch()` **同步返回** + **当前 agent 循环仍存活**。一旦「任务完成时刻 ≠ 调用时刻」（定时、超长、异步），结果就回不到 AI。

---

## 2. 总体架构

```
                          用户自然语言意图
                                 │
                                 ▼
              ┌───────────────────────────────────┐
              │        AIService（agent 循环）       │
              │  build_messages → tool-calling 多轮  │
              └───────────────────────────────────┘
                   │ dispatch（同步）        ▲ resume（异步唤醒，新增）
                   ▼                         │
        ┌────────────────────┐   ┌──────────────────────────┐
        │  ActionDispatcher   │   │ AIService.resume_with_    │
        │ 风险/确认/审计 闭环   │   │ task_result()（新增入口）  │
        └────────────────────┘   └──────────────────────────┘
            │                                 ▲
   同步动作  │  pending 动作                    │ task_finished(task_id,result)
   立即返回  │  返回 {status:pending,task_id}    │  信号（UI 层连接）
            ▼                                 │
   ┌──────────────────┐    ┌──────────────────────────────────┐
   │ ScheduledTask    │    │ PendingTaskRegistry（新增·纯逻辑）  │
   │ Registry（新增）  │───▶│ task_id → {session_key,kind,...}   │
   │ 定时/延迟登记表    │    └──────────────────────────────────┘
   └──────────────────┘                 ▲
            │ 到点                        │ 完成
            ▼                            │
   ┌──────────────────────────────────────────────┐
   │ 执行运行时（确定性，已有）：                       │
   │  ActionDispatcher 单动作 / custom_test executor │
   │  QThread worker / QTimer（UI 层）               │
   └──────────────────────────────────────────────┘
                     │
                     ▼
                 AuditLog（审计，已有）
```

两块新增能力共用 **`PendingTaskRegistry` + `resume` 续跑入口**：
- **调度（§3）**：解决「**何时**执行」——延迟 / 定时触发。
- **回灌（§4）**：解决「执行完**怎样告诉 AI**」——异步完成 → 主动唤醒模型续跑。

---

## 3. 能力一：定时 / 延迟任务调度（Scheduler）

### 3.1 范式选择

- 采用 **Plan-then-Execute**：AI 只把意图编译成一份「计划（trigger + steps）」，登记进调度表后**本轮立即结束、不占 token 等待**。
- 触发与执行由确定性层负责：UI 层 `QTimer` 到点 → 经 `ActionDispatcher` 执行已登记的目标动作。

### 3.2 数据结构（`ScheduledTask`）

```
ScheduledTask:
  task_id: str                # "sched_001"
  session_key: str            # 归属会话（回灌定位用，见 §4）
  trigger: dict               # {type:"delay", seconds:1800} | {type:"at", iso:"..."}
  action: dict                # {name:"set_instrument_output", arguments:{...}}
  status: str                 # pending / running / done / failed / cancelled
  created_at / fire_at: str
  result: dict | None
```

> 注：`action` 仍是一个**已注册的受控动作名 + 参数**，到点执行时走 `dispatcher.dispatch(name, args)`，**风险 / 确认 / 审计一律照旧**（high 动作到点仍会请求确认，除非用户在登记时已显式授权——见 §5）。

### 3.3 新增受控动作（category=schedule）

| 动作 | 风险 | 需确认 | 说明 |
|---|---|---|---|
| `schedule_action` | high | 是 | 登记「延迟/定时 + 目标动作」到 `ScheduledTaskRegistry`，返回 `task_id`；**不立即执行** |
| `list_scheduled_tasks` | low | 否 | 列出待执行 / 历史调度任务摘要 |
| `cancel_scheduled_task` | medium | 是 | 取消一个未触发的调度任务 |

> `schedule_action` 的 `action.name` 必须是注册表中已存在的动作；登记时即校验，避免登记「不可执行」的任务。

### 3.4 落地组件

| 组件 | 放哪 | 说明 |
|---|---|---|
| `ScheduledTaskRegistry` | `core/ai/scheduled_task_registry.py` | 纯逻辑、线程安全、FIFO 上限；仿 `DraftRegistry` |
| `schedule` handlers | `core/ai/actions/handlers/schedule.py` | `SPECS` + `build_handlers(deps)`，禁 import Qt |
| `CATEGORY_SCHEDULE` | [`registry.py`](../../../core/ai/actions/registry.py) | 新增 category 常量 |
| QTimer 触发器 | UI 层（MainWindow） | 到点回调 → `dispatcher.dispatch(action)` → 完成后发 `task_finished` |
| `ActionDeps` 新增字段 | [`deps.py`](../../../core/ai/actions/handlers/deps.py) | `scheduled_task_registry` 句柄 + `schedule_register_callback`（UI 注入启动 QTimer） |

### 3.5 示例：「半小时后关闭 N6705C-A 的通道 1」

```
AI → schedule_action({
        trigger:{type:"delay", seconds:1800},
        action:{name:"set_instrument_output",
                arguments:{session_id:"N6705C-A", channel:1, enabled:false}}
     })
   → 用户确认（high）→ 登记 task_id="sched_001" → 本轮结束（0 token 等待）
   ... 30 分钟后 QTimer 触发 ...
   → dispatcher.dispatch("set_instrument_output", {...}) → 执行 + 审计
   → task_finished("sched_001", result) → 经 §4 回灌 AI（可选）
```

---

## 4. 能力二：异步任务完成结果自动回灌（Resume 续跑）

### 4.1 范式选择

业内三种异步结果回灌范式：
- **A 阻塞等待**：tool 同步等到结果（已有，适合秒~分钟级）。
- **B 轮询句柄**：工具返回 `task_id`，AI 之后调 `get_task_result(task_id)`（兜底）。
- **C 事件续跑**：任务完成事件 → **系统主动发起新一轮模型调用**，把结果喂回 AI 续跑（核心）。

本设计 **以 C 为主、B 兜底**，对齐 OpenAI Assistants `run` 状态机 / Temporal signal 的标准做法。

### 4.2 核心流程（Resume 续跑）

```
长任务/定时动作 dispatch
   │ 立即返回 {status:"pending", task_id:"T-001"}（不阻塞）
   ▼
PendingTaskRegistry.register(task_id, session_key, kind)
   │  ... 后台 worker / QTimer / custom_test executor 执行 ...
   ▼
完成 → UI 层发 task_finished(task_id, result)
   ▼
AIService.resume_with_task_result(task_id, result)   ← 新增入口
   ① 按 task_id 取回 session_key，定位归属会话的 _agent_messages
   ② 把结果包成一条消息（role="tool" 续 tool_call_id，或 role="user" 系统提示）塞入
   ③ 主动发起一轮 _start_agent_round()（受 _MAX_TOOL_ROUNDS / token 预算约束）
   ▼
AI 收到「任务 T-001 已完成，结果=…」→ 自动继续决策下一步
```

### 4.3 数据结构（`PendingTask`）

```
PendingTask:
  task_id: str
  session_key: str            # 绑定发起会话，防串台
  kind: str                   # "scheduled" / "test_sequence" / "scan" / ...
  status: str                 # pending / done / failed / consumed
  created_at: str
  result: dict | None
  resumed: bool               # 幂等：是否已回灌续跑过
```

### 4.4 新增动作（B 兜底，category=query 或 schedule）

| 动作 | 风险 | 说明 |
|---|---|---|
| `get_task_result` | low | 按 `task_id` 主动查结果（C 未触发时兜底） |
| `list_pending_tasks` | low | 列出进行中 / 已完成未消费的任务 |

### 4.5 落地组件

| 组件 | 放哪 | 说明 |
|---|---|---|
| `PendingTaskRegistry` | `core/ai/pending_task_registry.py` | 纯逻辑、线程安全、FIFO；存 `task_id → PendingTask` |
| `resume_with_task_result()` | [`AIService`](../../../core/ai/ai_service.py) | **核心新增**：定位会话 → 塞结果 → 主动起一轮 |
| `task_finished` 信号连接 | UI 层 | worker/QTimer/executor 完成 → emit → 调 resume |
| 续跑安全阀 | `AIService` | resume 复用 `_MAX_TOOL_ROUNDS` + `_budget_for` + `clip_context_block` |

### 4.6 把现有「发起即返回旧缓存」的动作升级为 pending

- `scan_instruments`：当前发起异步扫描后返回**上次缓存**，新结果靠下次再调。升级为：返回 `pending+task_id`，`scan_finished` 信号 → resume 自动回灌最新候选。
- `start_test_sequence`：序列跑完（`CustomTestExecutor.finished`）→ resume 回灌 PASS/FAIL + 数据行数摘要，AI 可据此决定下一步（如生成报告 / 重测）。

---

## 5. 安全边界（必须守住）

1. **会话归属隔离**：结果必须回灌到**发起任务的那个 `session_key` / page profile**，禁止串台。
2. **续跑受预算与轮数约束**：异步唤醒不得绕过 `_MAX_TOOL_ROUNDS` 与 token 预算，防失控自循环。
3. **幂等回灌**：`task_id` + `resumed` 标志保证同一结果只续跑一次。
4. **仍走 dispatcher 审计**：定时 / 异步完成的动作结果一律写 [`AuditLog`](../../../core/ai/actions/audit.py)。
5. **AI 已"睡着"的降级**：若用户已关闭对话 / 会话失效，resume 优雅降级——仅记审计 + 通知 UI，不强行拉起模型。
6. **定时动作的确认策略**：`schedule_action` 登记时按 high 确认一次；到点执行的目标动作默认**仍走其自身风险确认**。如需「登记时一次性授权、到点免确认」，须在 `schedule_action` 参数显式声明 `pre_authorized=true`，且仅允许非 critical 动作。
7. **关闭即清理**：进程退出 / 会话清空时，`ScheduledTaskRegistry` 与 `PendingTaskRegistry` 一并清理（或按需持久化，见 §7）。

---

## 6. Token 成本模型

| 范式 | 等待期 | 执行期 | 完成回灌 |
|---|---|---|---|
| A 阻塞等待（已有） | 0 token（worker 在等，模型没跑） | 0 token | 同回合内，0 额外调用 |
| C 事件续跑（新增） | 0 token | 0 token | **每次完成 = 一次新模型调用**（重发 system+历史+tools+结果摘要） |
| 定时调度（新增） | 0 token（QTimer 在等） | 0 token | 同 C |

**成本要点**：异步唤醒次数 = 额外模型调用次数。优化手段（部分已有）：
- 回灌只发**结果摘要 + artifact_id**，经 [`clip_context_block`](../../../core/ai/ai_service.py) 裁剪（已有）。
- 续跑时**裁剪 tools**，避免每次重发全部动作的 JSON schema（当前 `to_tools()` 全量发送，建议按场景裁剪）。
- 合并回灌：同一会话短时间多个任务完成时，可合并为一次 resume，减少调用次数。

---

## 7. 页面定位与导航归类（Custom Test → Orchestrator）

### 7.1 结论先行

综合型 / 多仪器调用的测试任务**不新开第二套页面**，而是把现有 **Custom Test 重新定位为独立的「编排器（Orchestrator）」**：
- **载体不变**：仍复用 Custom Test 现有的多仪器连接 Mixin、节点引擎（If/While/Loop/PassFail）、`ExecutorThread`、preflight、租约、AI 集成方法——避免重复造轮子与 AI 集成割裂。
- **定位升级**：它与 PMU/Charger/Consumption 等「固定流程测试」本质不同——后者是**预设单一测试**，前者是**用户/AI 自由编排的多仪器综合调度**，理应**单独成类**。
- **本设计（§3 调度 / §4 异步回灌）正是 Orchestrator 的核心增量**：定时调度、长任务异步回灌、AI 续跑，都挂载在这个页面上。

### 7.2 更名

| 项 | 原 | 新 |
|---|---|---|
| 侧边栏显示名 | `Custom Test` | `Orchestrator` |
| 页面 key（`page_key` / `current_instrument_ui` 判定值） | `custom_test` | `orchestrator`（含 AI 集成方法判定，见下表） |
| 目录 / 类名 | `ui/pages/custom_test/CustomTestUI` | 保留实现路径，显示名与 page_key 切到 orchestrator（实现层是否同步改名见 §9.5） |

> page_key 改动牵涉 AI 集成方法判定（[`main_window`](../../../ui/main_window.py) 的 `_get_ai_test_*` / `_ai_test_run` 均判 `current_instrument_ui == "custom_test"`）与 [`custom_test_ui`](../../../ui/pages/custom_test/custom_test_ui.py) 的 `get_ai_test_config` 返回 `page_key="custom_test"`，须一并更新，且 `_ai_open_page` 的 `button_map` 同步。

### 7.3 导航归类：在 TOOLS 下方新增 `ORCHESTRATION` 分组

当前侧边栏分组顺序（[`nav_controller.py`](../../../ui/nav_controller.py)）：

```
INSTRUMENTS   → N6705C / Oscilloscope / Chamber
AUTOMATION    → PMU / Charger / Consumption / VminHunter / Custom Test  ← 待迁出
TOOLS         → KK Serials / Collection
```

调整为——把 Custom Test 从 AUTOMATION 迁出，在 **TOOLS 下方**新增 `ORCHESTRATION` 分组承接：

```
INSTRUMENTS   → N6705C / Oscilloscope / Chamber
AUTOMATION    → PMU / Charger / Consumption / VminHunter
TOOLS         → KK Serials / Collection
ORCHESTRATION → Orchestrator   ← 新分组（位于 TOOLS 下方）
```

### 7.4 落地改动点（导航 / 命名层）

| 改动 | 位置 | 说明 |
|---|---|---|
| 删除 AUTOMATION 中的 `custom_test_btn` 摆放 | [`create_left_nav`](../../../ui/nav_controller.py) | 从 `automation` 区移除 |
| 新增 `ORCHESTRATION` 分组标题 QLabel | 同上，置于 TOOLS 区之后 | 复用现有分组标题 QSS（color `#7b93bf` / 10px / 700 / letter-spacing 1px） |
| 新增 `orchestrator_btn`（原 custom_test_btn，显示名 `Orchestrator`） | 同上，置于 ORCHESTRATION 区 | 图标可沿用 `network.svg` |
| `nav_button_group.addButton` / `_refresh_nav_arrow_state` 名单同步 | 同上 | 把 custom_test_btn 改为 orchestrator_btn |
| `_create_custom_test_ui` / 懒加载字段 / `_ai_open_page` button_map | [`main_window`](../../../ui/main_window.py) | 改名与 page_key 同步 |
| AI 集成判定值 `"custom_test"` → `"orchestrator"` | `main_window` `_get_ai_test_*` / `_ai_test_run` · `custom_test_ui` `get_ai_test_*` 返回值 | page_key 全链路统一 |
| 同步矩阵 | `DIRECTORY_STRUCTURE.txt` / `helps/` / 本文 | 按 [08_CHECKLISTS](../../08_CHECKLISTS.md) 同步矩阵核对 |

### 7.5 命名范围决策（实现层是否物理改名）

两种力度，建议**先做轻量（A）**，避免大范围目录/导入改名带来的回归风险：

- **A · 轻量（推荐先行）**：仅改**显示名 + page_key + 导航分组**；目录 `ui/pages/custom_test/` 与类名 `CustomTestUI` 暂留，内部加注释标明「对外定位为 Orchestrator」。改动面小、可快速上线，与本文 §3/§4 的调度/回灌增量解耦。
- **B · 彻底（可作为后续重构）**：连目录 `custom_test/` → `orchestrator/`、类名 `CustomTestUI` → `OrchestratorUI`、`core/custom_test/` 一并改名。牵涉大量 import 与 spec/同步矩阵，单列一次重构任务执行。

> 与实施计划（§10）的关系：本节（§7）属**定位 / 导航 / 命名**调整，可独立于其余阶段提前或并行落地；其中 page_key 统一应在接入 §4 resume 续跑（需按 session/page profile 定位会话）之前完成，避免续跑时 page_key 口径不一致。

---

## 8. 工作流在 AI Assistant 面板 UI 上的体现

> 调度（§3）与异步回灌（§4）是后台机制，但用户感知它们的唯一窗口是 **AI Assistant 面板**（[`ai_assist_panel.py`](../../../ui/ai/ai_assist_panel.py) / [`chat_view.py`](../../../ui/ai/chat_view.py)）。
> 若任务"在后台默默跑、完成后 AI 突然冒出一句话"，用户会困惑。本节定义这些工作流如何在面板里**可见、可控、可追溯**。

### 8.1 现有面板结构（落点）

`AIAssistPanel(QFrame#aiAssistPanel)` 自上而下：
```
Header(aiHeaderBar)  → 标题 + Clear/Settings/×
ChatView(QScrollArea) → AI气泡(aiBubbleAI) / 用户气泡(aiBubbleUser) / system 消息
PreviewArea(QStackedWidget, 默认隐藏) → ConfigPreview / ScriptPreview
QuickActionRow(aiQuickBtn) → 动态快捷指令
BottomBar(aiBottomBar) → 输入框 + Send/Stop
```
工作流的 UI 体现**复用并扩展上述区域**，不另起独立窗口（与 §7「不新开页面」一致）。

### 8.2 三类工作流状态 → 三种 UI 呈现

| 工作流阶段 | 触发机制 | 面板 UI 呈现 | 落点组件 |
|---|---|---|---|
| **① 登记定时/延迟任务** | `schedule_action` 确认通过 | ChatView 插入一条 **system 卡片**：「⏱ 已登记：30 分钟后关闭 N6705C-A CH1（task=sched_001）[取消]」 | `chat_view` 新增 `add_task_card` |
| **② 任务进行中（pending）** | 长任务 / scan / 序列返回 `pending+task_id` | 顶部新增 **TaskTray（任务托盘条）**：常驻显示「进行中 N 个 / 待触发 M 个」，可展开列表 | 新增 `aiTaskTray`（见 §9.3） |
| **③ 任务完成 → AI 续跑** | `task_finished` → `resume_with_task_result` | 先插一条 system 卡片「✅ task=sched_001 已完成」，**紧接 AI 气泡自动续跑发言**（视觉上接续，不突兀） | `chat_view.add_task_card` + 现有 AI 气泡 |

### 8.3 新增组件：TaskTray（任务托盘条）

- **位置**：Header 下、ChatView 上方，常驻细条（仅在有活动任务时显示，无任务时折叠为 0 高）。
- **objectName**：`aiTaskTray`，背景 `#0b1428`，底边框 `1px #1e293b`，与面板暗色一致。
- **内容**：左侧状态摘要「⏱ 待触发 M · ⟳ 进行中 N」；右侧 `[展开]` 按钮 → 弹出/下拉任务列表（每行：图标 + 名称 + 倒计时/进度 + `[取消]`/`[查看结果]`）。
- **数据源**：`list_scheduled_tasks` / `list_pending_tasks`（§3.3 / §4.4 已规划的只读动作），UI 定时轮询或经信号刷新。
- **交互**：`[取消]` → 调 `cancel_scheduled_task`（medium，二次确认）；`[查看结果]` → 调 `get_task_result` 并在 ChatView 展开摘要。

### 8.4 ChatView 内联任务卡片（add_task_card）

在对话流里以 **system 消息卡片**形式内联，区别于普通 AI/用户气泡：
- 样式：浅色边框卡片（非气泡），左侧状态图标（⏱待触发 / ⟳进行中 / ✅完成 / ✖失败/取消），灰蓝底 `#121629`。
- 关键：**完成卡片 + AI 续跑气泡视觉相邻**，让用户理解"这条 AI 发言是任务完成自动触发的"，必要时卡片加角标「自动续跑」。
- 幂等：同一 `task_id` 的卡片随状态原地更新（pending→done），不重复堆叠。

### 8.5 状态可见性与控制（守住"可控"）

1. **登记即反馈**：`schedule_action` 一确认，立刻在 ChatView 出现"已登记"卡片 + TaskTray 计数 +1（不让用户怀疑是否生效）。
2. **随时可取消**：TaskTray 与卡片均提供 `[取消]`，对应 `cancel_scheduled_task`（守 §5.6 确认策略）。
3. **续跑可感知**：自动续跑的 AI 气泡前必有"✅ 完成"卡片做铺垫，避免"AI 凭空说话"。
4. **降级提示**：若用户已 Clear 会话 / 关闭面板（§5.5 降级），任务完成只更新 TaskTray + 记审计，**重新打开面板时**在 TaskTray 显示「N 个任务已完成（未回灌）」，点开可 `get_task_result` 补看，不强行拉起模型。
5. **会话隔离**：TaskTray 只展示**当前 page profile / session** 名下的任务（守 §5.1），切换页面时刷新。

### 8.6 落地改动点（UI 层）

| 改动 | 位置 | 说明 |
|---|---|---|
| 新增 `aiTaskTray` 容器 + 摘要/展开逻辑 | [`ai_assist_panel.py`](../../../ui/ai/ai_assist_panel.py) `_build_*` | 置于 Header 与 ChatView 之间；无任务时 0 高 |
| 新增 `add_task_card(task_id, status, text)` | [`chat_view.py`](../../../ui/ai/chat_view.py) | system 卡片样式 + 按 task_id 原地更新 |
| 连接 `task_finished` → 刷新 TaskTray + 插完成卡片 | `ai_assist_panel.py` | 经 AIService 信号（UI 层连接，core 不依赖 ui） |
| `resume_with_task_result` 续跑发言走现有 AI 气泡通道 | [`ai_service.py`](../../../core/ai/ai_service.py) → 面板 | 复用 `assistant_message` 信号，无需新通道 |
| 取消/查看结果接 `cancel_scheduled_task`/`get_task_result` | `ai_assist_panel.py` | 复用现有动作 dispatch 链路（含确认/审计） |

> 设计约束（守铁律）：TaskTray/卡片均属 **ui/ai/**，仅消费 AIService 信号与只读动作结果；`core/ai/` 不感知任何 Widget。所有刷新走 Signal/Slot，禁阻塞 IO。

---

## 9. 与现有文档的关系

- 受控动作总册：[AIAssist_ActionCatalog.md](./AIAssist_ActionCatalog.md)（本文新增的 `schedule_action` 等动作落地后，需回写其 §1 动作总览与 §2 `ActionDeps`；§7 的 Orchestrator 更名落地后，若动作描述/示例中引用了 `custom_test` page_key，亦需同步为 `orchestrator`）。
- 本文聚焦「调度 + 异步回灌」两块**新机制**，不重复动作清单细节；动作级 schema 在实现阶段补入 `handlers/schedule.py` 的 `SPECS`。

---

## 10. 实施计划（详细 · 分阶段 · 每阶段独立进度表）

> 本章是全文的落地总纲，置于文末便于持续更新进度。
> 状态图例：⬜ 未开始 · 🟡 进行中 · ✅ 已完成 · ⏸ 阻塞/挂起 · ➖ 不适用。
> 覆盖三条主线：**A 后端机制（调度 + 回灌，§3/§4/§5/§6）**、**B 页面定位与导航（§7）**、**C AI Assistant 面板 UI（§8）**。

### 10.0 阶段总览与依赖拓扑

| 阶段 | 主线 | 内容 | 依赖 | 风险 |
|---|---|---|---|---|
| **S1 注册表底座** | A | `PendingTaskRegistry` + `ScheduledTaskRegistry`（纯逻辑，仿 draft_registry，含单测） | 无 | 低 |
| **S2 Resume 续跑入口** | A | `AIService.resume_with_task_result()` + 会话定位 + 安全阀（轮数/预算/幂等/降级） | S1 | 中（触及 agent 循环核心） |
| **S3 异步动作升级** | A | `scan_instruments` / `start_test_sequence` 改 pending + 完成信号 → resume；新增 `get_task_result` / `list_pending_tasks` | S1·S2 | 中 |
| **S4 调度能力** | A | `schedule.py` handlers + `CATEGORY_SCHEDULE` + UI 层 QTimer 触发器 + `ActionDeps` 字段 | S1·S2 | 中 |
| **S5 安全与审计** | A | §5 全部边界落地；定时/异步完成动作写 AuditLog；`pre_authorized` 策略 | S2·S4 | 中 |
| **S6 页面定位与导航** | B | Custom Test → Orchestrator 更名 + page_key 统一 + TOOLS 下新增 ORCHESTRATION 分组（§7 轻量 A 方案） | 独立（建议先于 S7 完成 page_key 统一） | 低 |
| **S7 面板 UI · TaskTray + 任务卡片** | C | `aiTaskTray` 容器 + `chat_view.add_task_card` + 状态轮询/信号刷新（§8.3/§8.4） | S3·S4·S6 | 中 |
| **S8 面板 UI · 续跑可视化与降级提示** | C | 完成卡片→AI 续跑气泡视觉接续、降级"未回灌"提示、会话隔离刷新（§8.5） | S2·S7 | 中 |
| **S9 持久化（可选）** | A | 调度任务落盘（重启不丢）、pending 任务恢复 | S4 | 高（生命周期与一致性） |

依赖拓扑（简）：
```
S1 ─┬─ S2 ─┬─ S3 ─┐
    │      ├─ S4 ─┼─ S5
    │      │      │
    S6（独立，page_key 统一须早于 S7）
                   └─ S7 ─ S8
S4 ─ S9（可选）
```

---

### 10.1 S1 注册表底座

| # | 任务 | 文件/位置 | 状态 |
|---|---|---|---|
| S1-1 | `PendingTaskRegistry`（线程安全 + FIFO 上限，仿 draft_registry） | `core/ai/pending_task_registry.py` | ✅ |
| S1-2 | `ScheduledTaskRegistry`（同上 + trigger/fire_at 字段） | `core/ai/scheduled_task_registry.py` | ✅ |
| S1-3 | `PendingTask` / `ScheduledTask` 数据结构（§3.2/§4.3） | 同上 | ✅ |
| S1-4 | 单测：注册/获取/列举/取消/FIFO 淘汰/线程安全 | `tests/core/ai/` | ✅ |
| S1-5 | `ActionDeps` 新增句柄字段占位（不接线） | `core/ai/actions/handlers/deps.py` | ✅ |

### 10.2 S2 Resume 续跑入口

| # | 任务 | 文件/位置 | 状态 |
|---|---|---|---|
| S2-1 | `AIService.resume_with_task_result(task_id, result)` 入口 | `core/ai/ai_service.py` | ✅ |
| S2-2 | 按 task_id→session_key 定位归属会话 `_agent_messages` | 同上 | ✅ |
| S2-3 | 结果包成消息塞入 + 主动起一轮 `_start_agent_round` | 同上 | ✅ |
| S2-4 | 安全阀：复用 `_MAX_TOOL_ROUNDS` + `_budget_for` + `clip_context_block` | 同上 | ✅ |
| S2-5 | 幂等：`resumed` 标志保证同结果只续跑一次 | 同上 + registry | ✅ |
| S2-6 | 降级：会话失效/面板关闭时只记审计 + 通知 UI | 同上 | ✅ |
| S2-7 | 单测：定位/幂等/预算/降级分支 | `tests/core/ai/` | ✅ |

### 10.3 S3 异步动作升级

| # | 任务 | 文件/位置 | 状态 |
|---|---|---|---|
| S3-1 | `scan_instruments` 改返回 `pending+task_id`，`scan_finished`→resume | `core/ai/actions/handlers/instrument.py` | ✅ |
| S3-2 | `start_test_sequence` 完成（executor.finished）→resume 回灌 PASS/FAIL+行数 | `handlers/test.py` · `ui` 信号 | ✅ |
| S3-3 | 新增 `get_task_result`（low，B 兜底） | `handlers/query.py` | ✅ |
| S3-4 | 新增 `list_pending_tasks`（low） | `handlers/query.py` | ✅ |
| S3-5 | 回写 [AIAssist_ActionCatalog.md](./AIAssist_ActionCatalog.md) 动作总览（+2 动作） | 文档 | ✅ |

### 10.4 S4 调度能力

| # | 任务 | 文件/位置 | 状态 |
|---|---|---|---|
| S4-1 | `schedule.py`：`SPECS` + `build_handlers(deps)`（禁 Qt） | `core/ai/actions/handlers/schedule.py` | ✅ |
| S4-2 | `schedule_action`（high）/`list_scheduled_tasks`（low）/`cancel_scheduled_task`（medium） | 同上 | ✅ |
| S4-3 | `CATEGORY_SCHEDULE` 常量 | `core/ai/actions/registry.py` | ✅ |
| S4-4 | `builder._HANDLER_MODULES` 纳入 schedule | `core/ai/actions/builder.py` | ✅ |
| S4-5 | `ActionDeps` 接 `scheduled_task_registry` + `schedule_register_callback` | `handlers/deps.py` | ✅ |
| S4-6 | UI 层 QTimer 触发器：到点 dispatch + emit `task_finished` | `ui/main_window.py` | ✅ |
| S4-7 | 登记时校验 `action.name` 在注册表存在 | `handlers/schedule.py` | ✅ |
| S4-8 | 回写 [AIAssist_ActionCatalog.md](./AIAssist_ActionCatalog.md)（+3 动作 + category） | 文档 | ✅ |

### 10.5 S5 安全与审计

| # | 任务 | 文件/位置 | 状态 |
|---|---|---|---|
| S5-1 | 会话归属隔离（防串台，§5.1） | `ai_service.py` · registry | ✅ |
| S5-2 | 定时/异步完成动作一律写 `AuditLog`（§5.4） | `core/ai/actions/audit.py` · dispatcher | ✅ |
| S5-3 | `pre_authorized` 策略（仅非 critical，§5.6） | `handlers/schedule.py` · permission | ✅ |
| S5-4 | 关闭即清理：进程退出/会话清空清两注册表（§5.7） | `ai_service.py` · UI | ✅ |
| S5-5 | 续跑轮数/预算硬约束回归测试 | `tests/core/ai/` | ✅ |

### 10.6 S6 页面定位与导航（Orchestrator）

| # | 任务 | 文件/位置 | 状态 |
|---|---|---|---|
| S6-1 | AUTOMATION 移除 `orchestrator_btn`，新增 `ORCHESTRATION` 分组标题 | `ui/nav_controller.py` | ✅ |
| S6-2 | 新增 `orchestrator_btn`（显示名 Orchestrator）+ button_group/箭头名单同步 | 同上 | ✅ |
| S6-3 | `_create_orchestrator_ui`/懒加载字段/`_ai_open_page` button_map 同步 | `ui/main_window.py` | ✅ |
| S6-4 | page_key `custom_test`→`orchestrator` 全链路统一（含 AI 集成判定 + 磁盘目录/字面量） | `main_window.py` · `orchestrator_ui.py` · `core/orchestrator/` | ✅ |
| S6-5 | 同步矩阵：`DIRECTORY_STRUCTURE.txt` / `helps/` / `spec/` / 资源目录 | 文档/资源 | ✅ |

### 10.7 S7 面板 UI · TaskTray + 任务卡片

| # | 任务 | 文件/位置 | 状态 |
|---|---|---|---|
| S7-1 | `aiTaskTray` 容器（Header 与 ChatView 间，无任务 0 高） | `ui/ai/ai_assist_panel.py` | ✅ |
| S7-2 | TaskTray 摘要（⏱待触发 M · ⟳进行中 N）+ 展开列表 | 同上 | ✅ |
| S7-3 | `chat_view.add_task_card(task_id, status, text)`（system 卡片 + 原地更新） | `ui/ai/chat_view.py` | ✅ |
| S7-4 | 数据源接 `list_scheduled_tasks`/`list_pending_tasks`（QTimer 轮询刷新） | `ai_assist_panel.py` | ✅ |
| S7-5 | 行内 `[取消]`→`cancel_scheduled_task`；`[查看结果]`→`get_task_result` | 同上 | ✅ |
| S7-6 | QSS 与暗色一致（`#0b1428`/`#121629`/边框 `#1e293b`）；走 Signal/Slot 禁阻塞 | 同上 | ✅ |

### 10.8 S8 面板 UI · 续跑可视化与降级提示

| # | 任务 | 文件/位置 | 状态 |
|---|---|---|---|
| S8-1 | `task_resumed`→插"✅完成"卡片，紧接 AI 续跑气泡（视觉接续） | `ai_assist_panel.py` · `chat_view.py` | ✅ |
| S8-2 | 续跑发言复用现有 `response_*`/`add_ai_message` 通道（resume 走 `_run_next_agent_round`，不新建通道） | `ai_service.py`→面板 | ✅ |
| S8-3 | 完成卡片"自动续跑"角标 | `chat_view.py` | ✅ |
| S8-4 | 降级：`task_resume_skipped` 提示 + Clear/切页后 TaskTray 显示「N 个已完成（未回灌）」 | `ai_assist_panel.py` | ✅ |
| S8-5 | 会话隔离：按 `current_session_key()` 过滤，`on_page_changed` 切页刷新 | 同上 | ✅ |

### 10.9 S9 持久化（可选）

| # | 任务 | 文件/位置 | 状态 |
|---|---|---|---|
| S9-1 | `ScheduledTaskRegistry` 落盘（重启不丢） | `core/ai/` + user_data | ⬜ |
| S9-2 | pending 任务恢复策略（重启后状态判定） | 同上 | ⬜ |
| S9-3 | 生命周期/一致性回归测试 | `tests/core/ai/` | ⬜ |

---

### 10.10 总览进度

| 阶段 | 主线 | 状态 | 备注 |
|---|---|---|---|
| S1 注册表底座 | A | ✅ 已完成 | 纯逻辑，无依赖，可先行 |
| S2 Resume 续跑入口 | A | ✅ 已完成 | 触及 agent 循环核心 |
| S3 异步动作升级 | A | ✅ 已完成 | scan / 序列结果回灌 |
| S4 调度能力 | A | ✅ 已完成 | QTimer 在 UI 层 |
| S5 安全与审计 | A | ✅ 已完成 | 会话隔离/幂等/降级/回归测试 |
| S6 页面定位与导航 | B | ✅ 已完成 | page_key 统一须早于 S7 |
| S7 面板 UI · TaskTray | C | ✅ 已完成 | 依赖 S3/S4/S6 |
| S8 面板 UI · 续跑可视化 | C | ✅ 已完成 | 依赖 S2/S7 |
| S9 持久化（可选） | A | ➖ 不适用 | 本轮不做 |

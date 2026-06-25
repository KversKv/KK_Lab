# AI Assistant 页面级受控能力归一化方案：专项页可配置/可启动 + UI 回填可视化

> 范围：在现有「受控动作体系（[AIAssist_ActionCatalog.md](./AIAssist_ActionCatalog.md)）+ ActionDeps 注入 + MainWindow 分发枢纽」之上，解决两个结构性缺口——
> **① 专项测试页（如 `pmu_dcdc_efficiency`）无法被 AI 配置/启动**（写动作回调只接了 `orchestrator`，其它页一律返回「请切到 Orchestrator」）；
> **② AI 改动没有统一回填 UI 控件 + 可视化反馈通道**（轮询刷新与 AI 操作是两套，用户在主区看不到 AI 干了什么）。
>
> 目标：让「页面声明能力 → AI 按页能力裁剪工具 → 配置/启动经受控回调 → 回填主区控件并高亮」形成可复用闭环，**新增页面零改 core / 零改 handler**。
>
> 设计原则（与现有架构一致，不破坏分层）：
> 1. **core 不反向依赖 ui**——能力以通用回调声明在 [ActionDeps](../../../core/ai/actions/handlers/deps.py)，UI 侧实现。
> 2. **页面自描述能力**——页面实现哪些契约方法就支持哪些动作，不实现即优雅降级，枢纽只转发不写死页面名。
> 3. **控件写入单一入口**——AI 回填与轮询刷新复用同一 `apply_xxx()`，禁在 worker 线程直接操作控件。
> 4. **写动作仍走风险确认 + 审计**——按页能力裁剪只影响「可见与否」，不绕过 `PermissionChecker` / `AuditLog`。

---

## 0. 现状与缺口（结论先行）

| 能力 | 现状 | 位置 | 缺口 |
|---|---|---|---|
| 通用回调声明 | ✅ 已有 | [`ActionDeps`](../../../core/ai/actions/handlers/deps.py) | 无 |
| 配置草案落地分发（多页 ui_map） | ✅ 已有样板 | [`_apply_ai_config_draft`](../../../ui/main_window.py#L1132) | 仅 `apply_ai_config_draft`，无「启动/快照」对等通道 |
| 测试启动/暂停/停止/快照回调 | ⚠️ 仅 orchestrator | [`_ai_test_run` / `_get_ai_test_config`](../../../ui/main_window.py) | 写死 `current_instrument_ui == "orchestrator"`，专项页恒返回「请切到 Orchestrator」 |
| 页面能力自描述 | ❌ 缺失 | — | 无 `ai_capabilities()`，枢纽靠硬编码 if 判页 |
| 工具按页裁剪 | ❌ 缺失 | [`registry.to_tools()`](../../../core/ai/actions/registry.py) 全量 | 模型在专项页仍看到不可用动作 → 误调 → 沉默放弃 |
| AI 回填主区控件 | ⚠️ 部分（仅 config 草案 apply） | 页面 `apply_ai_config_draft` | 无统一写入口、无「AI 改了」高亮反馈 |
| 不可用即明示 | ❌ 缺失 | [`_handle_agent_round`](../../../core/ai/ai_service.py#L920) | 目标动作不可用/空回复时静默结束（本次故障现象） |

**故障复盘**：用户在 `pmu_dcdc_efficiency` 让 AI「测 1~200mA 效率」，AI 连串只读探查（`get_*`/`measure_*`）后输出空回复静默退出。根因：该页未注册任何写回调，`start_test_sequence`/`apply_test_config_draft` 对本页恒不可用，模型无路可走且无兜底引导。详见会话导出 `tests/ai_session_20260625_132726.md`。

---

## 1. 总体架构

```
                       用户在专项页的自然语言意图
                                  │
                                  ▼
              ┌─────────────────────────────────────┐
              │  AIService（agent 循环 + 按页裁剪 tools） │
              └─────────────────────────────────────┘
                   │ dispatch（受控动作）
                   ▼
        ┌────────────────────────────────────────┐
        │  ActionDispatcher（风险/确认/审计 闭环）      │
        └────────────────────────────────────────┘
                   │ 通用回调（ActionDeps）
                   ▼
        ┌────────────────────────────────────────┐
        │  MainWindow 分发枢纽（按当前页解析，去硬编码）  │
        │  resolve_active_ai_page() → 鸭子调用契约方法  │
        └────────────────────────────────────────┘
                   │ 契约方法（AIControllablePage）
                   ▼
        ┌────────────────────────────────────────┐
        │  具体页面（pmu_dcdc_efficiency 等）           │
        │  ai_get_config / ai_apply_config /         │
        │  ai_start_test / ai_stop_test /            │
        │  ai_capabilities                           │
        │      └─ apply_xxx() 单一控件写入口 + 高亮     │
        └────────────────────────────────────────┘
```

### 1.1 三个核心新增/改造点

1. **页面契约（Protocol）`AIControllablePage`**：定义专项页向 AI 暴露的标准方法集；页面按需实现，`ai_capabilities()` 声明子集。
2. **枢纽去硬编码**：`MainWindow` 的 `_ai_test_*` / `_get_ai_test_*` 改为先 `resolve_active_ai_page()`，再鸭子调用契约方法；不再写死 `orchestrator`。
3. **工具按页裁剪 + 不可用兜底**：`to_tools()` 接受当前页 capabilities 过滤；agent 循环在「目标动作不可用 / 空回复」时强制输出可执行引导。

---

## 2. 页面契约设计（AIControllablePage）

> 放置：`core/ai/page_contract.py`（纯逻辑，仅 `typing.Protocol` + 能力常量，禁 import Qt）。页面在 ui 层 implements，鸭子类型即可，不强制继承。

```python
# 能力标识常量（与动作名解耦，便于裁剪 tools）
CAP_GET_CONFIG   = "get_config"     # 读当前页配置快照
CAP_APPLY_CONFIG = "apply_config"   # 落地配置草案到控件
CAP_START_TEST   = "start_test"     # 启动本页测试
CAP_STOP_TEST    = "stop_test"      # 停止本页测试
CAP_GET_RESULT   = "get_result"     # 读最近结果摘要

class AIControllablePage(Protocol):
    def ai_capabilities(self) -> set[str]: ...
    def ai_get_config(self) -> dict | None: ...
    def ai_apply_config(self, payload: dict) -> tuple[bool, str]: ...
    def ai_start_test(self) -> tuple[bool, str]: ...
    def ai_stop_test(self) -> tuple[bool, str]: ...
    def ai_get_result_summary(self) -> dict | None: ...
```

- **可选实现**：页面只实现支持的方法，`ai_capabilities()` 返回真实子集；枢纽据此降级。
- **`pmu_dcdc_efficiency` 落地为薄封装**（已存在底层方法，无需重写）：
  - `ai_get_config` → 复用 [`get_test_config()`](../../../ui/pages/pmu_test/pmu_dcdc_efficiency.py#L1511)
  - `ai_apply_config` → 把 `start/end/step_current_a` 等写回 spin 控件（见 §4 单一写入口）
  - `ai_start_test` → 复用 [`_on_start_test()`](../../../ui/pages/pmu_test/pmu_dcdc_efficiency.py#L1192)（先校验连接/未运行）
  - `ai_stop_test` → 复用 `_on_stop_test()`
- **子页面定位**：`pmu_test` 是 `QTabWidget` 容器，当前子页经 `tab_widget.currentWidget()` 解析；`page_key` 经 `_get_current_help_key()` 已返回 `pmu_dcdc_efficiency` 等子页 key，与裁剪逻辑对齐。

---

## 3. 枢纽去硬编码（MainWindow）

### 3.1 统一的当前页解析

```python
def resolve_active_ai_page(self) -> "AIControllablePage | None":
    """返回当前可被 AI 控制的页面对象（含 Tab 子页下钻），无则 None。"""
    # 复用现有 _current_active_page + 子页 currentWidget 下钻
```

### 3.2 通用回调改写（示例：start）

```python
def _ai_test_run(self):
    page = self.resolve_active_ai_page()
    if page is None or CAP_START_TEST not in _caps(page):
        return False, "当前页面不支持由 AI 启动测试。"  # 明示而非沉默
    return _safe_call(page.ai_start_test)
```

- `_get_ai_test_config` / `_ai_test_stop` / `_apply_ai_config_draft` 同此模式。
- `orchestrator` 仍是其中一个实现者（实现全部契约方法），**不再是唯一硬编码分支**。

### 3.3 新增页面成本

| 步骤 | 改动 | 是否碰 core |
|---|---|---|
| 实现 5 个契约方法（多为薄封装） | 页面类 | 否 |
| `ai_capabilities()` 声明支持集 | 页面类 | 否 |
| 在 `resolve_active_ai_page` 的页面表注册一行 | MainWindow | 否 |
| handler / ActionDeps / registry | 无需改 | — |

---

## 4. UI 回填单一写入口 + 可视化（疑问 3）

### 4.1 数据流（AI 与轮询复用同一出口）

```
AI 动作(core,QThread) → dispatch → 契约 ai_apply_config(payload)
                                        │ (主线程 Slot)
                                        ▼
                          页面 apply_config_to_controls(cfg)  ← 唯一写控件入口
                                        │
                          ┌────────────┴────────────┐
                          ▼                          ▼
                   spin.setValue(...)        临时高亮 + 执行日志
                   （轮询刷新也走此入口）       「[AI] 扫描范围 1~200mA 已应用」
```

### 4.2 规范要点

1. **唯一写入口**：页面提供 `apply_config_to_controls(cfg)`，**AI 回填与轮询/手动刷新共用**，杜绝两套逻辑漂移（呼应仪器轮询回填场景）。
2. **线程边界**：AI 决策在 QThread，回填经 Signal/Slot 切回主线程；**禁在 worker 直接 `setValue`**（项目铁律：instruments/core 禁 Qt，UI 禁阻塞）。
3. **可视化反馈**：被 AI 修改的控件加临时高亮（如边框闪烁 1~2s）；并向 `ExecutionLogsFrame` 追加 `[AI] ...` 一行，使用户在主区即可见，而非只在 AI 面板。
4. **确认后才回填**：写动作经 `confirm_action` 确认 + 写 `AuditLog` 后，才执行回填。

---

## 5. 工具按页裁剪 + 不可用兜底

### 5.1 按页裁剪 tools（省 Token，呼应专项页定位初衷）

- `registry.to_tools(capabilities: set[str] | None)`：当 capabilities 给定时，写类动作只保留页面声明支持者；通用只读动作（`get_*`/`measure_*`）始终保留。
- `AIService` 在组装 tools 时传入当前页 capabilities（经 `page_key_getter` + 页面 `ai_capabilities()`）。
- 效果：专项页模型只看到「本页能干的事」，不再误调 `start_test_sequence` 然后放弃。

### 5.2 不可用 / 空回复兜底

- 扩展 [`_handle_agent_round`](../../../core/ai/ai_service.py#L920)：当 `not tool_calls` 且 `content` 为空，至少回一句状态说明，禁止静默结束。
- 当目标写动作回调返回「当前页面不支持…」时，注入一次轻量 nudge，引导模型给用户可执行替代（点 START / 切到 Orchestrator），而非沉默。

---

## 5b. AI 触发 UI 按钮：`ui_invoke` 受控 UI 动作注册表（疑问扩展）

> 解决「页面上有按钮但没专用接口（如 N6705C 的 **Auto Set** / Zero / Calibrate / Auto Fit），AI 偶尔要用」的普适性问题。
> **不采用盲扫 Widget 树 + 模拟 click 的 RPA 路径**（脆弱、绕过确认/审计、跨线程点击有崩溃风险、不可解释），改用「页面声明式登记具名 UI 动作 + 统一 `ui_invoke` 触发」。

### 5b.1 两条路径的边界（先分清，避免误用）

| 场景 | 正确做法 | 禁止 |
|---|---|---|
| 有 manager/接口（连接、测量、设输出） | 走专用受控动作；UI 经 manager 信号自动投影刷新 | ❌ 让 AI 去「点连接按钮」（按钮槽夹带读下拉框等 UI 取值，脆弱绕路） |
| 无接口的页面级按钮（Auto Set 等） | `ui_invoke(action_id)` + 页面声明式注册 + 复用按钮原槽 | ❌ 枚举控件树按文案找按钮模拟 click |

> **核心原则**：AI 与按钮是「同级输入」，都喂给同一底层逻辑（manager / 槽函数）；UI 只反映状态，**永不反映「谁触发的」**。连接类能力因此天然同步，无需额外架构（见 §5b.4）。

### 5b.2 注册表与数据结构（声明式白名单）

> 放置：`core/ai/ui_action_registry.py`（纯逻辑，线程安全，禁 import Qt；`handler` 为 UI 注入的 Callable）。

```python
@dataclass
class UIActionSpec:
    id: str                      # 全局唯一，建议 "<page>.<action>"，如 "n6705c.auto_set"
    label: str                   # 给模型/用户看的可读名，如 "Auto Set"
    page_key: str                # 归属页面（裁剪 + 防串台）
    handler: Callable[[], "tuple[bool, str]"]  # 复用按钮已绑定的槽
    risk: str = "medium"         # low/medium/high；沿用 PermissionChecker
    confirm: bool = True         # 是否需二次确认
    enabled_when: Callable[[], bool] | None = None   # 不满足→明示不可用，AI 不盲点
    description: str = ""        # 可选，补充语义供模型判断何时用
```

- 页面在构建控件后一次性登记，**`handler` 直接指向按钮原 `clicked.connect` 的槽**（如 `_on_auto_set`），零重复实现、行为与人点完全一致。
- 注册随页面生命周期；切页时按 `page_key` 裁剪可见集。

### 5b.3 两个通用动作（AI 侧只新增这两个，不为每个按钮写 ActionSpec）

| 动作 | 风险 | 说明 |
|---|---|---|
| `list_ui_actions` | low | 列当前页**可触发**的 UI 动作（经 `enabled_when` 过滤），含 id/label/risk/description |
| `ui_invoke` | 按目标项 risk | 触发指定 `action_id`：校验归属页 + enabled → 风险/确认 → 主线程 Slot 调 handler → 写 AuditLog → 回灌结构化结果 |

普适性来源：**新增任何「想给 AI 用的按钮」= 页面 `register_ui_action(...)` 一行**，AI 工具集恒定（始终只有 `list_ui_actions` + `ui_invoke`），无需扩 ActionSpec / 改 registry。

### 5b.4 执行链路

```
AI: ui_invoke(action_id="n6705c.auto_set")
   → 枢纽查当前页 UIActionRegistry（page_key 匹配 + enabled_when）
   → 不满足 → 明示「不可用：未连接仪器」（不盲点）
   → 满足 → PermissionChecker 判 risk + 必要时 ConfirmDialog
   → 主线程 Slot 调 spec.handler()  ← 就是按钮原来的槽
   → 写 AuditLog + 回灌 {ok,message} 结构化结果
   → 控件状态照常经原有信号/轮询投影刷新 + 执行日志追加 [AI] ...
```

### 5b.5 安全要点（在 §6 通用红线之上额外强调）

1. **白名单制**：只有显式 `register_ui_action` 的按钮可被 AI 触发；未登记的控件 AI 无任何途径操作。
2. **复用受控闭环**：`ui_invoke` 仍过 `PermissionChecker` + `ConfirmDialog` + `AuditLog`，与专用动作同级。
3. **线程边界**：handler 一律主线程 Slot 执行；AI 决策在 QThread，禁直接调槽。
4. **enabled_when 前置校验**：不满足条件返回明确不可用，杜绝盲点导致的无效/危险操作。
5. **页面隔离**：`ui_invoke` 仅能触发 `page_key == 当前页` 的动作，禁跨页派发。

---

## 6. 安全与边界（必须守住）

1. **能力裁剪 ≠ 越权**：裁剪只控制工具「可见性」，所有写动作仍过 `PermissionChecker`（high 需确认）+ `AuditLog`。
2. **页面降级安全**：契约方法缺失 / capabilities 未声明 → 明确返回不支持，绝不臆造执行。
3. **回填线程安全**：跨线程回填一律 Signal/Slot；运行中（`is_test_running`）拒绝 AI 改配置/重复启动。
4. **不臆造数据**：`ai_get_config` / `ai_get_result_summary` 只读真实控件/结果，无数据返回 `available=False`。
5. **子页隔离**：Tab 容器页按当前子页解析能力，禁止把 A 子页动作派发到 B 子页。

---

## 7. 分阶段实施计划与进度表

> 状态图例：`☐ 未开始` / `◐ 进行中` / `☑ 已完成` / `— 不涉及`。每阶段可独立验收、独立回归。

### Phase 1 — 页面契约 + 枢纽去硬编码（打通专项页写链路）

| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| 1.1 | 新增 `AIControllablePage` Protocol + 能力常量 | `core/ai/page_contract.py` | ☐ |
| 1.2 | `MainWindow.resolve_active_ai_page()`（含 Tab 子页下钻） | `ui/main_window.py` | ☐ |
| 1.3 | 改写 `_ai_test_run/_ai_test_stop/_get_ai_test_config` 去 orchestrator 硬编码 | `ui/main_window.py` | ☐ |
| 1.4 | `_apply_ai_config_draft` 统一走契约（保留 orchestrator 兼容） | `ui/main_window.py` | ☐ |
| 1.5 | 回归：orchestrator 现有 AI 流程不退化 | — | ☐ |

**验收**：orchestrator 全流程不变；专项页调用写动作不再恒返回「请切到 Orchestrator」（而是按能力判定）。

### Phase 2 — `pmu_dcdc_efficiency` 接入契约（首个专项页样板）

| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| 2.1 | 实现 `ai_capabilities()` 声明支持集 | `ui/pages/pmu_test/pmu_dcdc_efficiency.py` | ☐ |
| 2.2 | `ai_get_config` 复用 `get_test_config()` | 同上 | ☐ |
| 2.3 | `apply_config_to_controls(cfg)` 单一写入口 + `ai_apply_config` | 同上 | ☐ |
| 2.4 | `ai_start_test/ai_stop_test` 复用 `_on_start_test/_on_stop_test`（含连接/运行态校验） | 同上 | ☐ |
| 2.5 | 在 `resolve_active_ai_page` 页面表注册子页 | `ui/main_window.py` | ☐ |
| 2.6 | 端到端：「测 1~200mA 效率」可配置→确认→启动 | — | ☐ |

**验收**：复现本次故障场景，AI 能配置扫描范围（1~200mA）→ 弹确认 → 启动本页测试。

### Phase 3 — UI 回填可视化（AI 操作主区可见）

| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| 3.1 | 回填经 Signal/Slot 切主线程，规范写入口 | `ui/pages/pmu_test/pmu_dcdc_efficiency.py` | ☐ |
| 3.2 | 被 AI 改动控件临时高亮（复用既有 QSS/动效） | 同上 | ☐ |
| 3.3 | `[AI] ...` 行追加到 `ExecutionLogsFrame` | 同上 | ☐ |
| 3.4 | 轮询刷新与 AI 回填共用 `apply_config_to_controls` 验证 | — | ☐ |

**验收**：AI 改参数后，用户在主区控件即时看到变化 + 高亮 + 执行日志标记。

### Phase 4 — 工具按页裁剪 + 不可用兜底（省 Token + 防静默）

| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| 4.1 | `to_tools(capabilities)` 支持按能力过滤写类动作 | `core/ai/actions/registry.py` | ☐ |
| 4.2 | `AIService` 组装 tools 时注入当前页 capabilities | `core/ai/ai_service.py` | ☐ |
| 4.3 | 空回复 / 动作不可用兜底引导 | `core/ai/ai_service.py` | ☐ |
| 4.4 | 各专项页 Profile system_prompt 声明能力边界（呼应专一/省 Token） | `core/ai/profiles.py` | ☐ |
| 4.5 | Token 对比：专项页 tools 体积下降验证 | — | ☐ |

**验收**：专项页请求 tools 体积显著下降；模型不再误调不可用动作；无静默失败。

### Phase 5 — 推广其余专项页 + 文档同步

| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| 5.1 | `output_voltage` / `is_gain` / `oscp` / `gpadc` 等接入契约 | `ui/pages/pmu_test/*` | ☐ |
| 5.2 | charger / consumption 等专项页评估接入 | `ui/pages/*` | ☐ |
| 5.3 | 更新 [AIAssist_ActionCatalog.md](./AIAssist_ActionCatalog.md) 动作-页面能力矩阵 | 文档 | ☐ |
| 5.4 | 同步 [.ai/memory.md](../../../.ai/memory.md) / quick_actions | 文档 | ☐ |
| 5.5 | 全量回归 + lint | — | ☐ |

**验收**：新增专项页接入成本 = 实现契约方法 + 注册一行；core / handler 零改动。

### Phase 6 — `ui_invoke` 受控 UI 动作注册表（无接口按钮，对应 §5b）

| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| 6.1 | `UIActionSpec` + `UIActionRegistry`（纯逻辑，禁 Qt，线程安全） | `core/ai/ui_action_registry.py` | ☐ |
| 6.2 | 新增 `list_ui_actions` / `ui_invoke` 两个通用动作 handler | `core/ai/actions/handlers/` | ☐ |
| 6.3 | 枢纽按当前页 `page_key` 路由 + enabled_when 校验 + 主线程 Slot 调 handler | `ui/main_window.py` | ☐ |
| 6.4 | `ui_invoke` 接入 PermissionChecker / Confirm / AuditLog | `core/ai/...` | ☐ |
| 6.5 | N6705C 页登记 `auto_set` 等无接口按钮（handler 复用原槽） | `ui/pages/n6705c_power_analyzer/*` | ☐ |
| 6.6 | 触发后执行日志 `[AI] ...` + 控件经原信号/轮询投影刷新验证 | — | ☐ |
| 6.7 | 端到端：AI `list_ui_actions` → `ui_invoke("n6705c.auto_set")` → 确认 → 生效 | — | ☐ |

**验收**：未登记控件 AI 无法触发；登记按钮经确认后由 AI 触发，行为与人点一致，UI 自动同步且有 `[AI]` 标记。

---

## 8. 影响面与同步矩阵

| 改动 | 需同步 |
|---|---|
| 新增 `core/ai/page_contract.py` | `DIRECTORY_STRUCTURE.txt` |
| 新增 `core/ai/ui_action_registry.py` | `DIRECTORY_STRUCTURE.txt` |
| 专项页新增 AI 契约方法 | 对应 `helps/*.html`（如能力说明）、quick_actions |
| 页面登记 `register_ui_action` | `AIAssist_ActionCatalog.md`（UI 动作清单） |
| 动作-页面能力矩阵 | `AIAssist_ActionCatalog.md` |
| 决策（页面契约归一化 / ui_invoke） | `docs/ai/decisions/`（视需要） |

---

## 9. 待拍板项（开工前确认）

1. 专项页是否**复用** orchestrator 动作名（`start_test_sequence` 等，各页自解释语义）？本方案默认复用。
2. 契约采用 **Protocol 鸭子类型**（不强制继承）是否认可？
3. 高亮反馈形式（边框闪烁 / 背景渐变 / 仅日志标记）取哪种？
4. 工具裁剪粒度：仅裁「写类」动作，只读动作恒保留——是否认可？
5. `ui_invoke` 注册表（§5b）是否纳入本方案范围？默认纳入并排在 Phase 6（依赖 Phase 1 枢纽改造）。
6. 无接口按钮的默认风险等级与确认策略（Auto Set 类是否强制 `confirm=True`）？

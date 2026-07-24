# AI Assistant 优化方案：Prompt 分层 · 上下文管理 · 经验回流

> 状态：设计稿（内测阶段）
> 范围：`core/ai/` 下的 Prompt 拼装、会话上下文、经验沉淀与回流
> 阶段约定：内测阶段，经验回流采用 **服务器回归（telemetry 上报）** 方式
> 事实源：基于现有 `prompt_manager.py` / `ai_service.py` / `profiles.py` / `config.py` / `conversation_store.py`

---

## 0. 现状体检

| 能力 | 当前实现 | 短板 |
|---|---|---|
| 全局规则 | `profiles.py::_GLOBAL_SYSTEM_PROMPT` 写死常量 | 系统/项目/用户三层揉在一起，自用与分发冲突 |
| 页面级规则 | `AI_PROFILES[page_key]`（model/temperature/system_prompt/quick_actions） | 思路对，未外置 |
| 动态上下文 | `ContextProvider`（page/sequence/log/serial/waveform）注入 system 段 | 设计良好，每轮全量重拼，无限额 |
| 会话历史 | `conversation_store.py`，`_MAX_MESSAGES=40` 单文件全局流 | 按条数硬截断（非 token），无压缩，无会话隔离 |
| 多轮 tool-call | `ai_service.py::_agent_messages`，`_MAX_TOOL_ROUNDS=5` | messages 只增不控，大工具结果会膨胀 |
| 坑/序列沉淀 | `_FORCE_TOOL_NUDGE` 单点硬编码 | 无系统化片段库、无经验回流通道 |

---

## 1. 目标架构（四层 + 三回路）

```
┌──────────────────────────────────────────────────────────────┐
│  Prompt 分层            上下文管理             经验回流(服务器)   │
│  ──────────────        ──────────────        ────────────────  │
│  系统层 System(锁死)    token 预算            本地采集(脱敏)      │
│  项目层 Project(随包)   按页面/任务分会话      批量上报后台         │
│  用户层 User(本机)      滑动窗口 + 摘要压缩    后台 review         │
│  动态层 Context         工具结果裁剪          回灌项目层/eval      │
└──────────────────────────────────────────────────────────────┘
```

### 1.1 Prompt 分层（拼装顺序锁死）

```
系统层(代码常量, 不可改)
  → 项目层(resources/ai/project_prompt.md, 随包只读)
    → 页面 Profile(AI_PROFILES[page_key].system_prompt)
      → 用户层(user_data/ai/user_prompt.md, 本机, git 忽略)
        → 动态层(ContextProvider, 限额)
```

铁律：
- 安全红线永远在系统层、永远在最前；用户层无法覆盖系统层。
- 分发对象未定 → 现在就分层，分发策略（哪几层打包）留空，将来只切换打包清单。

### 1.2 会话边界：按页面/任务分会话

- 存储从单文件 `history.json` → 按 `page_key` 隔离的多会话。
- 切页面（`AIService.set_page_context()`）时切换对应会话历史。
- 好处：示波器页面历史不污染电源页面；单会话更短，天然缓解上下文膨胀。

---

## 2. 实现方案（按文件落点）

### 2.1 Prompt 三层外置

**新增资源/配置**

| 层 | 路径 | 打包 | git | 谁可改 |
|---|---|---|---|---|
| 系统层 | `core/ai/profiles.py::_GLOBAL_SYSTEM_PROMPT`（保留） | 随包 | 跟踪 | 出厂 |
| 项目层 | `resources/ai/project_prompt.md`（只读随包） | 随包 | 跟踪 | 出厂/版本 |
| 用户层 | `user_data/ai/user_prompt.md`（本机） | 不打包(给空模板) | 忽略 | 用户 |

**改动点**
- `profiles.py`：新增 `get_project_prompt()`（读 `resources/ai/project_prompt.md`，缺失回退空串）、`get_user_prompt()`（读 `user_data/ai/user_prompt.md`，缺失回退空串）。
- `prompt_manager.py::_build_system_text()`：在 `get_global_system_prompt()` 与 profile 之间插入项目层；在 profile 与 ContextProvider 之间插入用户层。
- `spec/kk_lab.spec`：把 `resources/ai/project_prompt.md` 纳入打包数据。
- 同步 `DIRECTORY_STRUCTURE.txt`。

**拼装伪代码（`_build_system_text`）**
```
parts = [系统层]
if 项目层: parts += 项目层
if profile.system_prompt: parts += profile.system_prompt
if 用户层: parts += 用户层
for p in providers: parts += p.build_context(page_key)  # 见 2.3 限额
return "\n\n".join(parts)
```

### 2.2 按页面/任务分会话（`conversation_store.py`）

**存储结构（向后兼容）**
```
user_data/ai/history/
  _default.json
  power_analyser.json
  oscilloscope.json
  ...
```
- 旧 `history.json` 存在时，首次迁移到 `history/_default.json`。
- 函数签名扩展：
  - `load_history(session_key: str = "_default")`
  - `save_history(messages, session_key="_default")`
  - `clear_history(session_key="_default")`
  - 新增 `list_sessions() -> list[str]`、`new_session(page_key) -> session_key`（任务级可加时间戳后缀）。
- `_MAX_MESSAGES` 保留为安全上限（条数兜底），实际裁剪交给 token 预算（2.3）。

**`ai_service.py` 配合**
- `set_page_context(page_key)`：切 `self._history = load_history(page_key)`，并记录当前 `session_key`。
- 落盘统一带 `session_key`。

### 2.3 token 预算与上下文裁剪（核心）

**新增模块 `core/ai/context_budget.py`**
- `estimate_tokens(text) -> int`：优先 `tiktoken`，缺失则启发式（中文≈1.5 token/字，英文≈1 token/4 字）。
- `fit_messages(system_text, history, user_text, *, window, reserve_output, ctx_blocks) -> messages`：
  1. 预算 = `window - reserve_output`；
  2. 固定保留 system 段 + 本轮 user；
  3. **动态上下文块（日志/波形）单独限额**，超额先裁它们（保头尾、中段省略）；
  4. 历史从最旧往前裁，直到落入预算；
  5. 触发裁剪/压缩时记一条 INFO 日志。

**模型上下文窗口（事实源，按模型而非全局固定）**

| 模型 | 上下文窗口 | 约合 token | 说明 |
|---|---|---|---|
| `glm-5.1-fp8` | 128k | 131072 | 推理模型，reasoning 先耗 token，`reserve_output` 要给足（≥2048，建议 4096） |
| `deepseekv4flash` | 1MB | ~1048576 | 超大窗口，正常对话几乎不会触窗；摘要/裁剪主要作为成本与延迟控制，而非防溢出 |

> 关键：窗口是「按模型」的，不能写死一个全局值。`fit_messages` 的 `window` 必须由「当前实际使用的模型」决定。
> 由于窗口巨大（尤其 DSV4flash 1MB），裁剪/摘要的首要目的从「防溢出」转为「控成本+控延迟+留早期关键约定」——所以默认按 `window` 的较低比例（如 50%）就开始软约束，而非等到撑满。

**配置项（`config.py::_DEFAULTS` 新增）**
```
"model_context_windows": {            # 按模型窗口表(事实源)
    "glm-5.1-fp8": 131072,
    "deepseekv4flash": 1048576
},
"default_context_window": 131072,     # 未知模型回退(取保守值=最小窗口)
"reserve_output_tokens": 4096,        # 给 glm 推理留足
"soft_budget_ratio": 0.5,             # 软预算: 超过窗口此比例即开始裁剪(控成本/延迟)
"max_context_block_tokens": 8192,     # 单个动态上下文块上限(日志/波形)
"summary_trigger_ratio": 0.7,         # 超窗口此比例触发摘要(硬阈值)
"enable_history_summary": True,
```

> 取窗口的逻辑：`window = model_context_windows.get(当前模型, default_context_window)`。
> 未知模型一律回退到「最小已知窗口」(=128k)，宁可保守也不溢出。

**`prompt_manager.build_messages` 改造**
- 拼好 system_text 后，调用 `context_budget.fit_messages` 产出最终 messages，替换"无脑全量拼接"。

**agent 模式（`ai_service.py::_agent_messages`）**
- 每轮 append 工具结果前，对超大 `tool` 内容做裁剪（保留摘要 + 落盘引用 ID）。
- 进入下一轮前对 `_agent_messages` 跑一次预算检查。

### 2.4 摘要压缩（阶段二）

- 触发：`fit_messages` 发现历史超 `summary_trigger_ratio` 仍放不下。
- 动作：后台用 `deepseekv4flash`（便宜快）将最旧 N 轮压成一段"前情提要"，以 `role=system` 的"[前情提要]"插入会话头部，替换原文。
- 红线：摘要内容必须经 `mask_sensitive`；摘要不得复述/覆盖系统层规则；摘要失败则退回纯滑动窗口。

### 2.5 纠偏片段库（坑的系统化）

- 把 `_FORCE_TOOL_NUDGE` 模式抽到 `resources/ai/nudges.json`：
```
[
  {"id": "force_tool", "when": "no_tool_call_but_claims_done", "text": "..."},
  {"id": "scpi_channel_syntax", "when": "page=power_analyser", "text": "通道须用 (@n)..."}
]
```
- `ai_service` 按触发条件按需注入对应 nudge（替代散落硬编码）。
- 新坑 → 加一条 → 随版本分发。

### 2.6 quick_action 参数化（序列沉淀）

- `AI_PROFILES[*].quick_actions` 从固定文案升级为模板：`"把通道{ch}设到{v}V"`。
- UI 侧对带占位符的项弹轻量输入再发送。

### 2.7 自用快捷：一键回归 + 一键沉淀（开发者本机回路）

> 场景区分：§3 的「服务器回归」是面向**内测用户群**的远程闭环（采集→上报→后台 review→随版本回灌）；本节是面向**你本人开发机**的**本地即时闭环**——绕过服务器，一键把当下经验固化进项目层/片段库/eval，立刻生效、立刻回归。两条回路共用底层数据（nudges.json / project_prompt.md / eval 用例），只是触发方式与时延不同。

#### 2.7.1 一键沉淀（把"刚才这次"固化下来）

目标：在对话气泡或设置页一个按钮，把当前这轮交互直接沉淀为可复用资产，**无需手改 json/md**。

| 入口（UI 动作） | 沉淀目标 | 落点文件 | 说明 |
|---|---|---|---|
| 「沉淀为纠偏」 | 一条 nudge | `resources/ai/nudges.json` | 选中"AI 答错→我纠正"的这轮，**AI 汇总润色**成 `{id,when,text}` 草稿，弹框微调后写入 |
| 「沉淀为快捷指令」 | 一条 quick_action 模板 | `profiles.py` 的 `AI_PROFILES[page_key].quick_actions`（或外置 `resources/ai/quick_actions.json`） | **AI** 把刚发的有效指令整理成模板，并将数值参数替换为 `{占位符}` |
| 「沉淀为项目规则」 | 项目层一段 | `resources/ai/project_prompt.md` | **AI** 把"这条约定"提炼成简洁规则，追加到项目层（带分隔标记，便于回滚） |
| 「沉淀为 eval 用例」 | 一条回归用例 | `tests/ai_eval/cases/*.json` | **AI** 从这轮提炼"输入→期望行为"草稿，下次改 prompt 前自动跑 |

**草稿生成：默认走 AI 汇总润色，按需降级回退**

> 前提：软件本身正在用 AI Assistant，即 AI 接口（NewAPI 客户端）天然可用。因此草稿生成**默认调一次便宜快的模型**（`deepseekv4flash`）做汇总/润色，产出更规整的草稿；不是先用规则硬凑。

```
选中的一轮 turn(user/assistant/page_key)
   │
   ▼ ① 默认：调 deepseekv4flash 汇总润色
   │     prompt 形如:"把这轮纠正整理成一条简洁的 AI 行为约束/快捷指令模板/规则/eval 用例,
   │                  输出结构化 JSON 草稿(id/when/text 等), ≤N 字, 祈使句"
   │
   ├─ 成功 → AI 草稿 → mask_sensitive 脱敏 → 弹框微调 → 写入
   │
   └─ 失败(无网络/超时/Key 失效/解析失败) → ② 降级：规则/模板兜底
         (page_key→when; 取原文→text; 正则替换数值→占位符) → 同样脱敏 → 弹框 → 写入
```

降级触发条件：AI 接口不可用、请求超时、返回无法解析为目标结构、或用户在设置里关闭"AI 辅助沉淀"。降级后功能不缺失，只是草稿更糙、更依赖弹框人工微调。

实现落点：
- 新增 `core/ai/curator.py`（本地沉淀器，写入/回退为本地文件操作，草稿生成默认借助 AI 接口）：
  - `as_nudge(turn) -> dict`、`as_quick_action(turn) -> dict`、`as_project_rule(text) -> None`、`as_eval_case(turn) -> dict`。
  - 内部 `_draft_via_ai(turn, kind) -> dict | None`：复用现有 NewAPI 客户端调 `deepseekv4flash`；失败返回 `None`。
  - `_draft_via_rule(turn, kind) -> dict`：规则/模板兜底，**永不依赖网络**，作为 `_draft_via_ai` 返回 `None` 时的回退。
  - 写入前去重（按 id/文本哈希）、**草稿（无论 AI 或规则来源）一律 `mask_sensitive`**、写入带时间戳与来源标记（`_src: ai|rule @ ts`，便于回滚与统计 AI 命中率）。
  - 全程 `log_config.get_logger`，异常 `exc_info=True`，禁裸 except；AI 调用失败只记 INFO 并降级，不向上抛断流程。
- 配置（`config.py`）：新增 `curator_ai_assist_enabled`（默认 True）、`curator_draft_model`（默认 `deepseekv4flash`），关闭后等价于强制走规则兜底。
- UI：对话气泡的「⋯」菜单加这 4 个动作（草稿生成期间显示 loading，不阻塞 UI，走 QThread）；设置页加「本机经验」管理入口（查看/删除已沉淀条目）+「AI 辅助沉淀」开关。
- 与 §3 telemetry 解耦：沉淀的**写入与回退不依赖服务器**（仅草稿润色这一步会用 AI 接口，失败即降级）；若 telemetry 开启，沉淀动作可附带上报一条 `curated` 事件（含 `_src` 来源，可选）。

#### 2.7.2 一键回归（沉淀后立刻验证没改坏）

目标：一个命令 / 一个按钮跑完 eval 回归集，红绿一目了然，改完 prompt/nudges 不慌。

- 入口一：命令行 `python -m core.ai.eval_runner`（开发常用，CI 也可挂）。
- 入口二：设置页「本机经验」面板的「一键回归」按钮 → 后台 QThread 跑 → 结果气泡/弹窗显示 `通过 X / 失败 Y`，失败项可展开看 diff。
- 新增 `core/ai/eval_runner.py`：
  - 读 `tests/ai_eval/cases/*.json`（输入 + 期望行为/期望工具调用/期望关键字）。
  - 逐条用当前 prompt+nudges 配置跑（可选真模型 / 可选 mock 离线），断言期望命中。
  - 输出汇总 + 失败明细；返回非零退出码供 CI/脚本判断。
- 与 Phase 7 的 `tests/ai_eval/` 同一套用例：§3.4/P7 定义用例格式与回归集，本节提供"一键触发器"。

#### 2.7.3 一键导出/重置经验包（本机维护）

- 「导出经验包」：把本机 `user_prompt.md` + 本地新增 nudges/quick_actions/eval 草稿打成一个 zip，便于换机迁移或提交回项目。
- 「重置为出厂」：清空用户层与本地沉淀，仅保留随包项目层（排障用，带二次确认）。
- 落点：`curator.py::export_pack()` / `reset_local()`；UI 设置页按钮（破坏性操作弹 `QDialog(parent=self)` 二次确认）。

#### 2.7.4 自用快捷与服务器回流的关系

```
┌──────────────── 本机即时回路 (§2.7) ────────────────┐
│ 对话中发现坑/好指令                                   │
│   └─[一键沉淀]→ nudges.json / project_prompt.md /     │
│                 quick_actions / eval 用例 (本地, 即时生效)│
│   └─[一键回归]→ eval_runner 跑回归 (本地, 立刻验证)      │
└───────────────────────────┬───────────────────────────┘
                            │ 价值高的本地资产, 提交回项目仓库
                            ▼
┌──────────────── 远程内测回路 (§3) ────────────────────┐
│ telemetry 采集内测用户经验 → 后台 review → 回灌同一批文件 │
│   → 随版本分发给所有内测用户                            │
└────────────────────────────────────────────────────────┘
```

> 一句话：**§2.7 是"你一个人当下就闭环"，§3 是"内测群随版本闭环"**；两者写入的是同一批资产文件，本机回路是远程回路的快进版与源头之一。

---

## 3. 经验回流：服务器回归（内测阶段重点）

### 3.1 闭环

```
用户本地使用
  │ 本地采集(脱敏): 坑反馈 / 高频指令统计 / 用户层 prompt 摘要 / nudge 命中
  ▼
本地缓冲队列(user_data/ai/telemetry/*.jsonl)
  │ 批量上报(HTTPS, 失败重试, 离线可堆积)
  ▼
回归服务器(内测后台)
  │ 你 review
  ▼
价值高 → 回灌项目层 project_prompt.md / nudges.json / eval 用例
  │
  └────────── 随下个版本分发回所有内测用户
```

### 3.2 采集内容（最小必要 + 脱敏）

| 事件 | 字段 | 用途 |
|---|---|---|
| 回答反馈 | `msg_id, page_key, rating(👍/👎), comment` | 质量评估 |
| 坑命中 | `nudge_id, page_key, before/after 行为` | 验证纠偏有效性 |
| 指令使用 | `page_key, action_template, count` | 提炼高频序列 |
| 错误事件 | `error_type, masked_message` | 定位共性问题 |
| 会话压缩 | `trigger_ratio, summarized_turns` | 调参 |

**强制脱敏**：复用 `mask_sensitive`；不上报原始日志/串口数据/API Key/设备序列号；上报体二次过滤。

### 3.3 实现落点

**配置（`config.py::_DEFAULTS` 新增）**
```
"telemetry_enabled": True,            # 内测默认开，正式版改默认值即可
"telemetry_endpoint": "",            # 回归服务器地址(env 可覆盖)
"telemetry_batch_size": 20,
"telemetry_flush_interval_s": 300,
"telemetry_client_id": "",           # 匿名机器标识(首启生成 UUID, 本机存)
```
- env 覆盖：`KK_LAB_AI_TELEMETRY_ENDPOINT`（与现有 `KK_LAB_AI_*` 一致风格）。

**新增模块 `core/ai/telemetry.py`**
- `TelemetryEvent` 数据类 + `record(event)`：写本地 `user_data/ai/telemetry/buffer.jsonl`。
- `TelemetryUploader`（QThread/定时器）：按 batch/interval 批量 POST；失败重试、离线堆积、上限滚动。
- 全程脱敏 + try/except + `exc_info=True`，禁裸 except；禁 `print`。
- **隐私开关**：`telemetry_enabled=False` 时彻底不采集不上报；UI 设置页提供开关与说明。

**接入点**
- `ai_service.py`：回答完成、nudge 命中、错误、压缩触发处 `telemetry.record(...)`。
- UI：回答气泡旁 👍/👎 → `record(rating)`；设置页加"参与内测数据回归"开关。

**服务器侧（内测后台，最小形态）**
- 单一 `POST /v1/telemetry`：校验 client_id、落库（jsonl 或轻量 DB）。
- 后台仅你访问，导出 → review → 回灌 `project_prompt.md` / `nudges.json` / `tests/ai_eval/`。

### 3.4 eval 回归集（防退化保险）

- `tests/ai_eval/` 存"输入 → 期望行为"用例（坑转用例）。
- 改 prompt / nudges 前跑一遍，防止修 A 坏 B。
- 与服务器回流联动：上报的坑 → 转 eval 用例 → 进回归。

---

## 4. 分 Phase 实施与进度看板

> 看板图例：状态 `⬜ 未开始` / `🟡 进行中` / `✅ 已完成` / `⏸️ 挂起` / `❌ 取消`
> 每次推进只更新对应 Phase 看板的「状态」列与「备注」列；Phase 全部 ✅ 后在总览看板勾选。

### 4.0 总览看板

| Phase | 主题 | 目标 | 依赖 | 状态 |
|---|---|---|---|---|
| P1 | 上下文地基 | token 预算裁剪，止住窗口溢出 | 无 | ✅ |
| P2 | Prompt 分层 | 系统/项目/用户三层外置，自用与分发解耦 | 无 | ✅ |
| P3 | 会话隔离 | 按页面/任务分会话 + 旧数据迁移 | P1 | ✅ |
| P4 | 坑沉淀 | 纠偏片段库 + quick_action 参数化 | P2 | ✅ |
| P5a | 自用快捷 | 一键沉淀 + 一键回归（本机即时回路） | P4,P7 | ✅ |
| P5b | 服务器回流 | telemetry 采集→上报→后台 review | P1-P4 | 🟡 |
| P6 | 智能压缩 | 历史摘要压缩（长会话） | P1,P3 | ✅ |
| P7 | 防退化 | eval 回归集 | P4 | ✅ |

里程碑：
- **M1（可用地基）** = P1 + P2 + P3 完成。✅
- **M2（自用顺手）** = M1 + P4 + P7 + P5a 完成（你本人当下就能一键沉淀/回归）。
- **M3（可分发内测）** = M2 + P5b 完成（telemetry 远程回流上线）。
- **M4（可持续优化）** = M3 + P6 完成。

> 说明：P5a（自用快捷）依赖 P4（片段库/快捷指令）与 P7（eval 用例格式），不依赖服务器，可先于 P5b 落地——优先让你自己用得顺手。

---

### Phase 1 · 上下文地基（token 预算裁剪）

目标：把 `_MAX_MESSAGES=40` 的条数硬截断替换为按 token 预算裁剪，动态上下文块单独限额。
依赖：无　风险：低（纯本地，不调模型）

| # | 任务 | 文件 | 状态 | 备注 |
|---|---|---|---|---|
| 1.1 | 新增 `estimate_tokens()`（tiktoken 优先，启发式回退） | `context_budget.py`(新) | ✅ | tiktoken 缺失自动回退中英文启发式 |
| 1.2 | 实现 `fit_messages()`（system+本轮固定保留，块限额，历史从旧裁） | `context_budget.py`(新) | ✅ | 软/硬预算取小，id() 身份判断保留项 |
| 1.3 | 按模型取窗口（glm 128k / dsv4flash 1MB），未知回退最小窗口 | `context_budget.py`(新) `config.py` | ✅ | `context_window_for()`，未知回退 131072 |
| 1.4 | `build_messages` 接入预算裁剪（按当前模型窗口） | `prompt_manager.py` | ✅ | `BudgetConfig` + 末端 `fit_messages` |
| 1.5 | 新增模型窗口表/预留/软预算/块上限等配置项 | `config.py` | ✅ | windows/reserve/soft_ratio/block 上限 |
| 1.6 | agent 模式 `_agent_messages` 每轮预算检查 | `ai_service.py` | ✅ | `_trim_agent_messages` + tool 结果 clip |
| 1.7 | 裁剪触发记 INFO 日志 + 自测 | — | ✅ | 4096 窗口实测裁到 [system, user] |

验收：长对话/大日志注入下不再溢出窗口；裁剪时有日志可观测。

---

### Phase 2 · Prompt 分层（三层外置）

目标：系统层锁死、项目层随包、用户层本机，拼装顺序固定。
依赖：无　风险：低

| # | 任务 | 文件 | 状态 | 备注 |
|---|---|---|---|---|
| 2.1 | 创建项目层默认文件 | `resources/ai/project_prompt.md`(新) | ✅ | KK_Lab 项目约定 + 拼装顺序说明 |
| 2.2 | 创建用户层空模板（git 忽略） | `user_data/ai/user_prompt.md`(新) | ✅ | 含填写指引注释，被 `user_data/` 整目录忽略 |
| 2.3 | 新增 `get_project_prompt()` / `get_user_prompt()` | `profiles.py` | ✅ | 缺失/OSError 回退空串 |
| 2.4 | `_build_system_text` 按序插入项目层/用户层 | `prompt_manager.py` | ✅ | 系统→项目→Profile→用户→动态 |
| 2.5 | 打包纳入 `resources/ai/` | `spec/kk_lab.spec` | ✅ | datas 新增 `resources/ai` |
| 2.6 | `.gitignore` 忽略 `user_prompt.md` + 同步目录结构 | `DIRECTORY_STRUCTURE.txt` | ✅ | `user_data/` 已整目录忽略；目录结构已同步 |

验收：删/改用户层文件不影响系统层红线；项目层随包生效。

---

### Phase 3 · 会话隔离（按页面/任务分会话）

目标：历史按 `page_key` 隔离，切页面切会话，旧 `history.json` 平滑迁移。
依赖：P1　风险：中（存储迁移）

| # | 任务 | 文件 | 状态 | 备注 |
|---|---|---|---|---|
| 3.1 | 存储改 `history/{session_key}.json` | `conversation_store.py` | ✅ | session_key 经 `_SAFE_KEY` 清洗 |
| 3.2 | `load/save/clear_history` 增 `session_key` 参数 | `conversation_store.py` | ✅ | 默认 `_default`，向后兼容 |
| 3.3 | 新增 `list_sessions()` / `new_session()` | `conversation_store.py` | ✅ | `new_session` 带时间戳后缀 |
| 3.4 | 旧 `history.json` → `history/_default.json` 一次性迁移 | `conversation_store.py` | ✅ | 实测迁移成功并删除旧文件 |
| 3.5 | `set_page_context` 切换对应会话历史 | `ai_service.py` | ✅ | 切前存旧会话、切后载新会话 |
| 3.6 | 回归：切页面历史互不污染 | — | ✅ | 实测 pmu_test 与 _default 互不串扰 |

验收：不同页面历史互不串扰；老用户升级后旧历史不丢。

---

### Phase 4 · 坑沉淀（纠偏片段库 + 快捷指令参数化）

目标：把 `_FORCE_TOOL_NUDGE` 系统化为片段库；quick_action 支持占位符模板。
依赖：P2　风险：低

| # | 任务 | 文件 | 状态 | 备注 |
|---|---|---|---|---|
| 4.1 | 创建片段库（含 force_tool / scpi 等） | `resources/ai/nudges.json`(新) | ✅ | 随包 + `nudges.local.json` 本机覆盖按 id 合并 |
| 4.2 | 按触发条件加载/注入 nudge，替换硬编码 | `ai_service.py` `nudges.py`(新) | ✅ | `force_tool_nudge`/`page_nudges` |
| 4.3 | quick_actions 升级为模板（`{ch}`/`{v}`） | `profiles.py` | ✅ | `quick_action_placeholders`/`fill_quick_action` |
| 4.4 | UI 对带占位符项弹轻量输入 | UI | ✅ | `_prompt_quick_action_values` QDialog |
| 4.5 | 打包纳入 nudges.json | `spec/kk_lab.spec` | ✅ | datas 含 `resources/ai` |

验收：新增坑只需加一条 json；快捷指令可带参下发。

---

### Phase 5a · 自用快捷（一键沉淀 + 一键回归，本机即时回路）

目标：让你本人在对话中一键把经验固化进 nudges/项目层/快捷指令/eval，并一键跑回归验证；全程本地、即时生效、不依赖服务器。
依赖：P4（片段库/快捷指令）、P7（eval 用例格式）　风险：低（纯本地文件 + QThread 回归）

| # | 任务 | 文件 | 状态 | 备注 |
|---|---|---|---|---|
| 5a.1 | 新增沉淀器（as_nudge/as_quick_action/as_project_rule/as_eval_case） | `core/ai/curator.py`(新) | ✅ | 去重+脱敏+时间戳/来源标记，写本机 .local 兼容 frozen 只读 |
| 5a.1b | 草稿生成默认走 AI 润色（`_draft_via_ai`），失败降级规则兜底（`_draft_via_rule`） | `core/ai/curator.py`(新) `config.py` | ✅ | `curator_ai_assist_enabled`/`curator_draft_model` |
| 5a.2 | 对话气泡「⋯」菜单加 4 个一键沉淀动作（润色走 QThread，不阻塞 UI） | UI | ✅ | `chat_view` footer + `ai_assist_panel` `_start_curate` + `curate_dialog` |
| 5a.3 | 新增回归执行器（读 eval 用例→逐条跑→红绿汇总） | `core/ai/eval_runner.py`(新) | ✅ | 支持 mock 离线 / 真模型 |
| 5a.4 | 命令行入口 `python -m core.ai.eval_runner` + 非零退出码 | `core/ai/eval_runner.py` | ✅ | 实测 `--mock` 通过 2/2 |
| 5a.5 | 设置页「本机经验」面板：一键回归按钮（QThread）+ 结果展示 | UI 设置页 | ✅ | `_build_experience_tab` + `_on_run_eval` 后台线程 |
| 5a.6 | 导出经验包 / 重置出厂（破坏性弹 `QDialog(parent=self)` 确认） | `curator.py` + UI | ✅ | `export_pack`/`reset_local` + 二次确认对话框 |
| 5a.7 | 本机经验条目查看/删除管理 | UI 设置页 | ✅ | `list_local`/`delete_nudge`/`delete_eval_case` |

验收：对话里一键即可把"刚纠正的坑"写进 nudges 并立刻生效；点一下"一键回归"能跑完 eval 看红绿；离线可用，不依赖 telemetry。

---

### Phase 5b · 服务器回流（telemetry）

目标：本地脱敏采集 → 缓冲 → 批量上报 → 后台 review 回灌。
依赖：P1-P4　风险：中

| # | 任务 | 文件 | 状态 | 备注 |
|---|---|---|---|---|
| 5.1 | 新增 telemetry 配置项 + env 覆盖 | `config.py` | ✅ | enabled/endpoint/batch/flush/client_id + `effective_telemetry_endpoint` |
| 5.2 | `TelemetryEvent` + `record()` 写本地 jsonl | `telemetry.py`(新) | ✅ | buffer.jsonl + 滚动上限 + `_mask_payload` |
| 5.3 | `TelemetryUploader`（QThread/定时，批量+重试+离线堆积） | `telemetry.py`(新) | ✅ | QTimer→短命 QThread→httpx POST，成功后重写剩余 |
| 5.4 | 接入点埋点（回答/nudge/错误/压缩） | `ai_service.py` | ✅ | answer/error/nudge_hit/summary/feedback 5 处 |
| 5.5 | UI：👍/👎 反馈 + 隐私开关 | UI 设置页 | ✅ | `chat_view` footer 反馈 + 常规页 `telemetry_enabled` 开关 |
| 5.6 | 服务器最小形态 `POST /v1/telemetry` + 落库 | 服务器 | ⏸️ | 服务器侧不在本仓库范围（仅客户端落地） |
| 5.7 | 全程脱敏校验 + 关闭开关彻底静默 | — | ✅ | `record` 开关关闭直接 return + `mask_sensitive` 二次脱敏 |

验收：开关关闭时零采集零上报；上报体无敏感原文；离线可堆积补传。

---

### Phase 6 · 智能压缩（历史摘要）

目标：超阈值时把最旧若干轮压成「前情提要」。
依赖：P1,P3　风险：中

| # | 任务 | 文件 | 状态 | 备注 |
|---|---|---|---|---|
| 6.1 | `fit_messages` 检测超 `summary_trigger_ratio` 触发 | `context_budget.py` | ✅ | `should_summarize` |
| 6.2 | 后台用 `deepseekv4flash` 生成摘要 | `ai_service.py` | ✅ | `_SummaryWorker` QThread + `summary_model` |
| 6.3 | 摘要走 `mask_sensitive`，失败回退滑动窗口 | `ai_service.py` | ✅ | `_on_summary_failed` 回退原历史 |
| 6.4 | 摘要以 system「[前情提要]」插入会话头 | `conversation_store.py` | ✅ | `save_summary`/`load_summary` + `build_messages(summary=)` |

验收：超长会话仍保留早期关键约定；摘要不覆盖系统层规则。

---

### Phase 7 · 防退化（eval 回归集）

目标：坑转用例，定义用例格式与回归集（一键回归触发器见 P5a）。
依赖：P4　风险：低

| # | 任务 | 文件 | 状态 | 备注 |
|---|---|---|---|---|
| 7.1 | 建 eval 目录与用例格式 | `tests/ai_eval/`(新) | ✅ | `cases/*.json` + `README.md` 格式说明 |
| 7.2 | 把已知坑转为「输入→期望行为」用例 | `tests/ai_eval/` | ✅ | force_tool_open_output / scpi_channel_syntax 两种子用例 |
| 7.3 | 上报坑→用例的转换约定 | 文档 | ✅ | curator `as_eval_case` 一键沉淀；README 说明格式 |

验收：改 prompt 后跑回归不破坏既有坑的修复。

---

## 5. 同步矩阵（改完必做）

- 目录变更 → `DIRECTORY_STRUCTURE.txt`
- 新资源(`resources/ai/*`) → `spec/kk_lab.spec`
- 新依赖(如 `tiktoken` 可选) → `requirements.txt`
- 决策记录 → `docs/ai/decisions/`
- 上下文沉淀 → `docs/ai/memory.md`
- 新坑 → `docs/ai/03_GOTCHAS.md`

---

## 6. 硬红线对齐（本方案自检）

- 禁 `print`，统一 `log_config.get_logger(__name__)`，异常 `exc_info=True`，禁裸 except。
- `instruments/` 不引入 Qt；telemetry/上下文逻辑置于 `core/ai/`，不阻塞 UI（上报走 QThread/定时器）。
- 不硬编码地址/Key：`telemetry_endpoint` 走 config + env 覆盖。
- 隐私：内测默认开但可关；全程脱敏；不上报敏感原文。
- 中文简体；不新增无关 `*.md`；改完跑 lint。

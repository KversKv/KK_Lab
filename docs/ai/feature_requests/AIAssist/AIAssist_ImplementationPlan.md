# AI Assist 实现计划与进度表

> 📚 **AI Assist 文档索引**
> | 文档 | 角色 |
> |---|---|
> | [AIAssist_Architecture.md](./AIAssist_Architecture.md) | 架构设计与规范（事实源） |
> | **[AIAssist_ImplementationPlan.md](./AIAssist_ImplementationPlan.md)**（本文） | 主实现计划与进度表（阶段 0~5） |
> | [AIAssist_FeatureExtension_V1.md](./AIAssist_FeatureExtension_V1.md) | 功能增补 V1（波形/控制/用量/序列/Markdown，Phase A~C） |

> 配套设计文档：[AIAssist_Architecture.md](./AIAssist_Architecture.md)（架构与规范的唯一事实源）
> 本文定位：把 AIAssist_Architecture.md §16 的 5 个阶段拆成**可执行、可勾选、可验收**的任务清单与进度表。
> 分层铁律：`main.py → ui/ ←→ core/ → instruments/ → lib/`；`instruments/` 禁 Qt；`ui/` 禁阻塞 IO（走 QThread + Signal/Slot）。
> 状态约定：`☐ 待办` / `◐ 进行中` / `☑ 完成` / `⊘ 阻塞` / `— 不适用`。

---

## 0. 总览进度表

| 阶段 | 主题 | 状态 | 关键交付 | 依赖 |
|---|---|---|---|---|
| 0 | 对接前置确认 | ☑ | 网关参数 / tools 支持 / 依赖选型 | — |
| 1 | 顶栏 + 面板 + 基础问答 | ☑ | 右面板可开关 + 能调通 New API | 阶段 0 |
| 2 | 日志分析与上下文增强 | ☑ | 软件日志 + 串口日志结构化分析 | 阶段 1 |
| 3 | 测试配置与脚本生成 | ☐ | 草案 → 预览 → 校验 → apply | 阶段 1、2 |
| 4 | Action Registry 与 UI/仪器控制 | ☑ | 受控动作闭环（权限/确认/审计） | 阶段 1~3 |
| 5 | 体验优化 | ☑ | 流式 / 历史 / 多模型 / 快捷指令 / 方案 B（标题栏，已确认实现） | 阶段 1~4 |

> 里程碑：**阶段 1 = 最小可用（MVP）**；阶段 1~3 = 核心价值闭环；阶段 4 = 受控操作上线；阶段 5 = 打磨。

---

## 阶段 0：对接前置确认（不写功能代码，扫清未知）

> 目标：在动手前消除"网关 / 模型 / 依赖"三类未知，避免阶段 1 卡接口。

| # | 任务 | 状态 | 备注 |
|---|---|---|---|
| 0.1 | 向内网运维确认 `base_url` 完整路径（`.../v1` 还是含 `/chat/completions`） | ☑ | `http://172.16.10.84:3000/v1`，`GET /v1/models` 实测 200，详见 [AIAssist_Architecture.md §5.0](./AIAssist_Architecture.md) |
| 0.2 | 确认鉴权头格式（标准 `Authorization: Bearer <key>` 或 New API 自定义头） | ☑ | 标准 `Authorization: Bearer <key>`，无需自定义头 |
| 0.3 | 获取可用 `model` 名称/别名清单，替换 §6 设想别名 | ☑ | 实测仅 `glm-5.1-fp8`（默认）、`deepseekv4flash`；Profile 先统一映射到 `glm-5.1-fp8` |
| 0.4 | 确认网关是否支持原生 `tools`（function calling）与 `stream` | ☑ | tools 支持（返回 `tool_calls`）、stream 支持（SSE 35 块）；第一版走原生 tools |
| 0.5 | HTTP 依赖选型：`httpx` vs `requests`（建议 `httpx`，支持超时/取消更优） | ☑ | 已选 `httpx>=0.27,<0.28`，写入 `requirements.txt` 并安装 0.27.2 验证可导入 |
| 0.6 | 用 curl/Postman 跑通一条最小 `/chat/completions` 请求（验证 0.1~0.4） | ☑ | `scripts/ai_smoke_test.py` 实测 200，`content="你好"`；样例与解析注意事项落 §5.0 |
| 0.7 | 标题栏方案最终拍板（方案 A 默认 / 方案 B 还原参考图） | ☑ | 拍板方案 A，落 [decisions/003-ai-assist-titlebar.md](../../decisions/003-ai-assist-titlebar.md) |

**阶段 0 验收**：上述参数全部明确，且有一条真实跑通的请求/响应样例。
> ✅ 阶段 0 已完成（2026-06-17）：网关 `http://172.16.10.84:3000/v1` 连通、Bearer 鉴权 OK、模型 `glm-5.1-fp8`/`deepseekv4flash`、tools+stream 均支持、`/chat/completions` 实测通过。真实 base_url/Key 落 `user_data/ai/config.json`（gitignored）。复测：`.\.venv\Scripts\python.exe scripts\ai_smoke_test.py`。
> ⚠️ 阶段 1 注意：`glm-5.1-fp8` 为推理模型，正文取 `message.content`、推理在 `message.reasoning`；`max_tokens` 须 ≥1024（过小会致 content 为空）。

---

## 阶段 1：顶栏 + 面板 + 基础问答（MVP）

> 目标：右面板能开关；能把用户消息发到 New API 并展示回复；「测试连接」可用；能识别当前页面切 Profile。

### 1.A 骨架与目录
| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| 1.A.1 | 建 `core/ai/` 包 + `MODULE_VERSION="0.0.0"` | `core/ai/__init__.py` | ☑ |
| 1.A.2 | 建 `ui/ai/` 包 + `MODULE_VERSION="0.0.0"` | `ui/ai/__init__.py` | ☑ |
| 1.A.3 | 新增 SVG 图标目录与右面板图标 | `resources/icons_svg/ai/ai_panel.svg`、`send.svg` | ☑ |

### 1.B core/ai 基础链路
| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| 1.B.1 | `AISettings` 读写（env 优先 + `user_data/ai/config.json`） | `core/ai/config.py` | ☑ |
| 1.B.2 | `NewAPIClient`：OpenAI 兼容 `/chat/completions`（非流式 + 超时/取消） | `core/ai/newapi_client.py` | ☑ |
| 1.B.3 | `profiles.py`：`AI_PROFILES`（页面 → model/温度/system_prompt） | `core/ai/profiles.py` | ☑ |
| 1.B.4 | `PromptManager`：拼装 system/page/task 段 | `core/ai/prompt_manager.py` | ☑ |
| 1.B.5 | `AIService(QObject)`：QThread 调用 + 信号（response_ready/busy_changed/error_occurred/connection_tested） | `core/ai/ai_service.py` | ☑ |
| 1.B.6 | `log_ring.py`：环形 logging Handler，挂 root logger | `core/ai/log_ring.py` | ☑ |
| 1.B.7 | `PageContextProvider`：读 `current_instrument_ui` + nav 子键 | `core/ai/providers/page_provider.py` | ☑ |

### 1.C UI：顶栏与面板
| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| 1.C.1 | `AppTopBar`（方案 A）：靠右放分隔线 + 右面板按钮 | `ui/app_top_bar.py` | ☑ |
| 1.C.2 | `AIPanelButton`：QPushButton checkable，`#aiPanelButton{min-height:22px}` | `ui/ai/ai_panel_button.py` | ☑ |
| 1.C.3 | `AIAssistPanel`：Header + ChatView + InputArea + 操作栏 | `ui/ai/ai_assist_panel.py` | ☑ |
| 1.C.4 | `ChatView`：消息气泡渲染（流式预留接口） | `ui/ai/chat_view.py` | ☑ |
| 1.C.5 | MainWindow 接线：`outer_splitter` 包裹 `main_splitter` + 面板 | `ui/main_window.py` | ☑ |
| 1.C.6 | 面板开关持久化 `user_data/ai/ui_state.json`（宽度 360，范围 300-600） | `ui/main_window.py`、`ui/ai/panel_state.py` | ☑ |
| 1.C.7 | 页面切换 → `AIService.set_page_context()` 切 Profile | `ui/main_window.py::_fade_in_widget`（切页唯一 chokepoint） | ☑ |

### 1.D 设置与连通
| # | 任务 | 状态 |
|---|---|---|
| 1.D.1 | AI 设置入口（base_url/api_key/model）+「测试连接」按钮 | ☑ |
| 1.D.2 | `enabled=false` 时不显示面板按钮 | ☑ |
| 1.D.3 | 基础日志分析（取 log_ring 最近 N 行喂模型） | ☑ |

**阶段 1 验收**（对应 AIAssist_Architecture.md §17 1~5、11~13、15）：
- ☑ 顶栏出现分隔线 + 右面板按钮（打开高亮）；点击可开关面板，不破坏业务布局；
- ☑ 「测试连接」成功；能发消息并展示回复（真机 ping `glm-5.1-fp8` content 非空）；
- ☑ 切页面时 Profile/Prompt 随之变化（经 `_fade_in_widget` → `set_page_context`）；
- ☑ 网络/解析在 QThread，UI 不卡；API Key 不硬编码（env>runtime>file）、config 不进版本库；
- ☑ 异常友好提示、`exc_info=True`、无裸 `except`（兜底 `# noqa: BLE001`）；`GetDiagnostics` 无错误。

---

## 阶段 2：日志分析与上下文增强

> 目标：把软件运行日志 + 串口接收日志接入上下文，支持范围选择/脱敏/等级过滤/摘要，并结构化输出分析结果。

| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| 2.1 | `LogContextProvider`：读 log_ring + ExecutionLogsFrame 缓存 | `core/ai/providers/log_provider.py` | ☑ |
| 2.2 | `SerialContextProvider`：读 SerialSessionManager 状态 + RX 缓存 | `core/ai/providers/serial_provider.py` | ☑ |
| 2.3 | `ContextBuilder`：聚合 Provider 输出为只读快照 | `core/ai/context_builder.py` | ☑ |
| 2.4 | 日志范围选择控件（InputArea 内）+ 上限保护 | `ui/ai/ai_assist_panel.py` | ☑ |
| 2.5 | 脱敏（序列号/IP/路径/token 正则掩码）+ 等级过滤 + 超限摘要 | `core/ai/context_builder.py` | ☑ |
| 2.6 | 分析结果 Schema（summary/severity/evidence/...）+ 渲染 | `core/ai/schemas.py` / ChatView | ☑ |

**阶段 2 验收**（§17 第 6 条）：
- ☑ 能分析最近串口日志与软件运行日志，输出结构化分析（含 severity/证据/建议）；
- ☑ 超长日志自动摘要+截断并提示；脱敏生效。

> ✅ 阶段 2 已完成（2026-06-17）：
> - core：新增 `serial_rx_cache.py`、`schemas.py`、`context_builder.py`、`providers/log_provider.py`、`providers/serial_provider.py`；`providers/__init__.py` 导出。
> - `AIService`：新增 `analysis_ready(object)` 信号、`analyze_logs(ContextOptions)`、`feed_serial_rx()`、`set_serial_status_getter()`/`set_execution_logs_getter()` 注入；`_parse_analysis` 把模型 JSON 解析为 `LogAnalysisResult`。
> - UI：`ai_assist_panel.py` 加日志等级下拉 + 最大行数 SpinBox（上限 1000）；`chat_view.py` 加 `add_analysis_message` 结构化渲染（severity 色阶 + 证据/原因/建议）。
> - 接线：`main_window.py` 把 `SerialSessionManager.session_data_received` 喂入 RX 缓存，并按当前页注入串口状态 / 执行日志 getter。
> - core 不依赖 ui/Qt（回调注入）；脱敏复用 `mask_sensitive` + 扩展 IP/PATH/SN；超 char_budget 自动摘要截断并加提示。

---

## 阶段 3：测试配置与脚本生成

> 目标：AI 只产草案；草案经预览 + 本地校验（preflight）+ 用户确认后才能 apply。

| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| 3.1 | `response_parser.py` 双模式（原生 tools / 降级 JSON）+ Schema 校验 + 重试 | `core/ai/response_parser.py` | ☑ |
| 3.2 | `ConfigPreview`：测试配置草案预览 + 应用 | `ui/ai/config_preview.py` | ☑ |
| 3.3 | `ScriptPreview`：脚本草案预览 + 校验 + 应用 | `ui/ai/script_preview.py` | ☑ |
| 3.4 | Custom Test 草案接 `core/custom_test` serialization + validation(preflight) | `core/ai/draft_validation.py` + main_window 接线 | ☑ |
| 3.5 | 其它页面配置走页面自身 import/校验逻辑 | main_window `_apply_ai_config_draft`（页面实现 `apply_ai_config_draft`） | ☑ |
| 3.6 | 流程闭环：生成 → 预览 → 校验(error阻止/warning可继续) → 确认 → apply | AIService.generate_draft + draft_ready → 预览弹窗 | ☑ |

**阶段 3 验收**（§17 第 7 条）：
- ☑ 能生成测试配置/脚本草案；
- ☑ 预览 + 本地校验通过后才能 apply；error 阻止、warning 可确认继续。

---

## 阶段 4：Action Registry 与 UI/仪器控制

> 目标：上线受控动作，覆盖查询/UI/串口/仪器/测试，闭环权限-风险-确认-审计。

| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| 4.1 | `ActionSpec` + `ActionRegistry`（注册/查找/渲染 tools） | `core/ai/actions/registry.py` | ☑ |
| 4.2 | `PermissionChecker / RiskPolicy`（low/medium/high/critical） | `core/ai/actions/permission.py` | ☑ |
| 4.3 | `ActionDispatcher`（按 name 路由 handlers） | `core/ai/actions/dispatcher.py` | ☑ |
| 4.4 | `AuditLog` 落 `user_data/ai/audit.log`（含拒绝/取消） | `core/ai/actions/audit.py` | ☑ |
| 4.5 | `ActionConfirmDialog`（parent=面板，OK/Cancel 二元化） | `ui/ai/action_confirm_dialog.py` | ☑ |
| 4.6 | handlers/query：page/serial/app_logs/instrument/test 状态 | `core/ai/actions/handlers/query.py` | ☑ |
| 4.7 | handlers/ui：open_page/toggle_ai_panel | `core/ai/actions/handlers/ui.py` | ☑ |
| 4.8 | handlers/serial：clear/send(需确认) 经 SerialSessionManager | `core/ai/actions/handlers/serial.py` | ☑ |
| 4.9 | handlers/instrument：query/disconnect 经 InstrumentManager；output=critical 默认禁 | `core/ai/actions/handlers/instrument.py` | ☑ |
| 4.10 | handlers/test：start/pause/stop 经 custom_test runner（需确认） | `core/ai/actions/handlers/test.py` | ☑ |
| 4.11 | 多轮 tool-calling：执行结果回灌 AIService | `core/ai/ai_service.py` | ☑ |

**阶段 4 验收**（§17 第 8~10、14 条）：
- ☑ 能读 InstrumentManager 快照查仪器状态（不主动 query 真机）；
- ☑ 能经受控 Action 操作 UI（跳页等）；
- ☑ 高风险动作（串口发送/仪器输出/测试启动/脚本运行）必须确认；critical 默认禁 AI 直接执行；
- ☑ 仪器一律经 InstrumentManager，AI 无法绕过 `instruments/`；
- ☑ 所有动作（含拒绝/取消）写审计。

**阶段 4 完成总结**：
- 新增动作层 `core/ai/actions/`（registry/permission/dispatcher/audit/builder + handlers/{deps,query,ui,serial,instrument,test}）；动作流：`Registry → JSON Schema 校验 → PermissionChecker → 必要时 ActionConfirmDialog → Dispatcher 路由 handler → AuditLog`。
- 共注册 16 个动作：查询类（6，low）、UI 类（2，low）、串口类（clear=low / send=high+确认）、仪器类（query=low / disconnect=medium / set_output=critical 默认禁）、测试类（start/pause=high+确认 / stop=high）。
- 风险分级双保险：`PermissionChecker(allow_critical=False)` 拦截 critical + instrument handler `set_instrument_output` 兜底返回禁止。
- `AIService` 进入 agent 多轮 tool-calling（`_MAX_TOOL_ROUNDS=5`，用 `QTimer.singleShot(0, ...)` 避免 QThread 竞态），执行结果回灌为 `role=tool` 消息续跑。
- `newapi_client.chat()` 支持原生 `tools`/`tool_choice`；确认对话框以 AI 面板为 parent，取消为默认按钮防误触。
- main_window 注入全套回调（页面/串口/日志/测试状态 getter + open_page/toggle/serial_send/clear/test run/pause/stop）。
- 冒烟验证通过：low→executed、critical→denied、high 无确认回调→cancelled，三态均写 audit.log（UTF-8）。

---

## 阶段 5：体验优化（打磨，可选项分批做）

| # | 任务 | 状态 | 落地说明 |
|---|---|---|---|
| 5.1 | 流式输出（SSE → assistant_message 增量信号） | ☑ | `newapi_client.chat_stream()`（SSE+`iter_lines`）；`AIService._StreamWorker` + `response_started/response_delta/response_finished` 信号；仅 chat 模式（无 tools）按 `settings.stream` 走流式，agent/analysis/draft 仍非流式；`ChatView.begin/append/end_stream_message` 增量渲染同一气泡 |
| 5.2 | 历史会话（多轮上下文持久化/恢复） | ☑ | 新增 `core/ai/conversation_store.py`（落 `user_data/ai/history.json`，仿 `panel_state.py`，上限 40 条）；`AIService` 启动 `_load_persisted_history()`、每轮对话后 `_save_persisted_history()`、`clear_history()` 调 `_clear_persisted_history()`；面板启动 `_replay_history()` 回放，顶栏「清空」按钮可清会话 |
| 5.3 | 多模型别名切换（按 Profile/手动） | ☑ | `config.available_models`（默认 `glm-5.1-fp8`/`deepseekv4flash`）；`AIService.set_model_override()/current_model()/available_models()`（覆盖>Profile>默认）；面板模型 `QComboBox#aiModelCombo`（ID 选择器钉高 22px，「自动（按页面）」+清单）；设置对话框可编辑可选模型 + 流式开关 |
| 5.4 | 快捷指令按页面动态化 + 远程 Prompt 配置 | ☑ | 各 Profile 加 `quick_actions` + `profiles.get_quick_actions(page_key)`；面板 `QuickActionRow`（`QPushButton#aiQuickBtn` 钉高 22px），按 `current_page_key()` 动态填充，`main_window._fade_in_widget` 切页时 `refresh_quick_actions()`；远程 Prompt 配置走既有 `PromptManager` provider 机制（按需扩展） |
| 5.5 | （可选）方案 B：无边框自绘标题栏，100% 还原参考图 | ☑ | **已实现并确认**：`main_window` `Qt.FramelessWindowHint` + `nativeEvent` 边缘 resize；`ui/app_top_bar.py` 自绘标题栏（CSD）：应用图标/标题、AI 面板按钮、最小化/最大化-还原/关闭（`winCtrlBtn/winCloseBtn` ID 选择器钉 46×36）、拖拽移动、双击最大化/还原、`sync_max_icon()` 状态同步。**与早期 ADR 003「方案 A」记录不一致，实际代码已落方案 B** |

**阶段 5 验收**：☑ 流式逐字可用；☑ 会话可恢复/可清空；☑ 模型可手动切换；☑ 快捷指令按页面刷新；☑ 标题栏（方案 B）拖拽/双击还原/边缘 resize/窗口控制全部正常。

---

## 通用收尾 Checklist（每阶段完成都要过）

| 项 | 说明 | 状态 |
|---|---|---|
| 同步矩阵 | 按 AIAssist_Architecture.md §18 同步 `DIRECTORY_STRUCTURE.txt`/`spec`/`requirements.txt`/`decisions/`/`.ai/memory.md` | ☑ 新增 `conversation_store.py`；无新增依赖（仍 httpx）；无新增 SVG；`history.json` gitignored |
| 分层 | `instruments/` 无 Qt；`ui/` 无阻塞 IO；仪器经 InstrumentManager | ☑ 流式 IO 走 `_StreamWorker`+QThread，UI 仅收信号增量渲染 |
| 日志 | 无 `print`；异常 `exc_info=True`；无裸 `except` | ☑ 兜底 `# noqa: BLE001`；`conversation_store` 仅捕获 `OSError`/`JSONDecodeError` |
| UI 规范 | QDialog 带 parent + OK/Cancel 二元化；控件高度 ID 选择器钉死；数值 QLabel 带单位 | ☑ 模型/快捷指令控件用 `#aiModelCombo`/`#aiQuickBtn` 钉 22px；设置对话框 parent + 二元化保留 |
| 安全 | API Key 不硬编码；config 不进版本库 | ☑ Key 仍走 env>runtime>file；`available_models` 仅模型名 |
| 模块版本 | 模块单独迭代时 `MODULE_VERSION` +1 | ☑ `core/ai` 与 `ui/ai` 均 0.3.0 → 0.4.0 |
| lint | 改完跑 lint | ☑ 仓库未装 ruff；已 `py_compile` 全过 + IDE 诊断无错 |

---

## 风险与依赖登记

| 风险/依赖 | 影响 | 缓解 |
|---|---|---|
| 网关不支持原生 tools | 阶段 4 动作能力 | 阶段 0 实测**已支持**原生 tools，走原生路径；降级 JSON 模式（§9）保留为后备 |
| 推理模型 `max_tokens` 过小致 content 空 | 阶段 1 问答质量 | Profile `max_tokens` ≥1024；正文取 `message.content`，`reasoning` 独立处理 |
| 内网模型上下文窗口小 | 日志分析质量 | 摘要 + 截断 + 等级过滤（§7/§11） |
| 标题栏方案（已拍板 A） | 阶段 1 UI | 方案 A 落地（ADR 003），B 留阶段 5 |
| 打包体积 | 发版 | 只引轻量 HTTP，不引 AI 框架/向量库（§17.15） |
| 仪器 session 抢占 | 阶段 4 | 复用 busy/lease 判断，运行期禁高风险抢占（§8） |

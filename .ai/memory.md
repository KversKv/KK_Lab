# KK_Lab - AI 长期记忆（Session Memory）

> 本文件用于 AI 在不同会话之间**沉淀项目关键上下文**。
> 写入规则：
> - 只记录**长期有效**的信息（约定、决策、踩过的坑、固定的偏好）；
> - 临时调试步骤 / 一次性任务 **不要**写进来；
> - 保持每条精炼（1-3 行）。

---

## 项目核心

- 项目：**KK_Lab** — PySide6 桌面工具，BES 芯片功耗 / PMU / Charger 测试。
- 平台：Windows 64-bit；Python ≥ 3.10；PowerShell 开发环境。
- 入口文档：[CLAUDE.md](../CLAUDE.md) → [docs/ai/](../docs/ai/)。
- 任务 SOP：[docs/ai/09_WORKFLOW.md](../docs/ai/09_WORKFLOW.md)（调用 / 执行 / 回归三阶段）。

## 必守铁律

1. 禁 `print`，统一 `log_config.get_logger`。
2. `instruments/` 不依赖 Qt；UI 不直调 VISA。
3. 仪器创建统一走 `instruments/factory.py`。
4. 新仪器必须同步 Mock（`instruments/mock/mock_instruments.py`）。
5. `DEBUG_MOCK` 改完需重启应用；不得热切换。
6. 跨线程只用 Signal/Slot。
7. 结果写 `Results/`，文件名带时间戳。
8. 未经用户许可不 `git commit`、不主动新建 `*.md`。
9. 工程清单同步矩阵（[project-rules.md §8](../.trae/rules/project-rules.md)）必遵守：改目录 → `DIRECTORY_STRUCTURE.txt`；改运行时资源 → `spec/kk_lab.spec`；新功能页 → `helps/`；新 import → `requirements.txt`。

## 打包

- 主程序：`python -m PyInstaller spec/kk_lab.spec --clean --noconfirm`
- 子工具：`python -m PyInstaller spec/n6705c_datalog.spec --clean --noconfirm`
- 资源路径：`sys._MEIPASS` fallback 到脚本目录。

## 常见坑（高优先级提醒）

- `sys.stdout / stderr` 在打包 `windowed` 下为 None，入口已兜底。
- `pyvisa.ResourceManager.__del__` 退出崩溃，入口已 patch，勿删。
- QPainter 警告已过滤。
- `HoverFixStyle` 用于 Fusion 风格 `:hover` 生效，勿替换。
- **驱动层严禁硬编码 `pyvisa.ResourceManager('@py')`**，默认走系统 VISA（NI-VISA），可选 `visa_library` 显式指定，失败再回退 `@py`。详见 [03_GOTCHAS.md §21](../docs/ai/03_GOTCHAS.md)。
- **QComboBox `setView()` 后首次 `showPopup()` 高度不足**：Qt 内部用未含 CSS padding 的 sizeHintForRow 计算 popup 高度。修复方式：自定义 delegate 确保 sizeHint 包含 padding + `showPopup()` 前设 view.setMinimumHeight + 隐藏多余 Scroller。见 `ui/widgets/dark_combobox.py`。
- **SVG 图标禁止 `setDevicePixelRatio`**：PySide6 中 QLabel/QIcon 不能正确处理带 DPR 标记的 pixmap，会只显示左上角。直接用 `QPixmap(size, size)` 逻辑大小渲染。详见 [03_GOTCHAS.md §23](../docs/ai/03_GOTCHAS.md)。
- **`get_page_base_qss()` 禁止全局 `min-height`**：会级联覆盖子控件的 `setFixedHeight()`，挤占布局间距。需要标准高度的控件在 `page_extra` 中按 objectName 单独设置。详见 [03_GOTCHAS.md §24](../docs/ai/03_GOTCHAS.md)。
- **Tab 状态样式盒模型必须一致**：用 `QPushButton` 模拟 tab 时，active/inactive 的 padding、border 宽度、margin 必须一致；视觉连接用同背景色 `border-bottom`，不要用 `border-bottom: none`。详见 [03_GOTCHAS.md §25](../docs/ai/03_GOTCHAS.md)。
- **AI Agent 历史回灌会自我污染**：模型"嘴上执行（声称已开启/已弹确认框）却不发 tool_call"的文本若入 history 回灌，会让后续轮照抄、仪器不动。须在真·首轮（`_agent_rounds==0`）强制回灌 nudge 逼其改用 tool_call。详见 [03_GOTCHAS.md §26](../docs/ai/03_GOTCHAS.md)。
- **worker `finished` 槽链里再起新 QThread worker 禁用 `singleShot(0)`**：会与上一轮线程 `finished→deleteLater` 清理竞态，导致**无声闪退**（faulthandler 抓不到栈=Qt 状态损坏 abort，非 segfault）；须用 `singleShot(≥50ms)`。详见 [03_GOTCHAS.md §26](../docs/ai/03_GOTCHAS.md)。

## 会话决策 / 偏好

- 回复语言：**简体中文**（随用户语言切换）。
- 代码注释：**不主动增删**，保留原文件风格。
- 新文档模板：沿用 `docs/ai/00_OVERVIEW.md` ~ `08_CHECKLISTS.md` 的编号与结构。

## 变更履历

| 日期 | 变更 | 备注 |
|---|---|---|
| 2026-04-28 | 建立 AI 协作文档体系（`docs/ai/`、`AGENTS.md`、`.trae/rules/`、`.ai/memory.md`） | 根据用户请求初始化 |
| 2026-04-28 | 新增 [docs/ai/09_WORKFLOW.md](../docs/ai/09_WORKFLOW.md)，落盘任务 SOP；CLAUDE.md / AGENTS.md / project-rules.md / 00_OVERVIEW.md 已同步引用 | 明确"调用 / 执行 / 回归"三阶段流程 |
| 2026-04-28 | 增补"工程清单同步矩阵"硬规则至 [project-rules.md §8](../.trae/rules/project-rules.md)、[08_CHECKLISTS.md](../docs/ai/08_CHECKLISTS.md) 通用勾项、[09_WORKFLOW.md §3.5.1](../docs/ai/09_WORKFLOW.md) | 封堵 `DIRECTORY_STRUCTURE.txt` / `requirements.txt` 盲区 |
| 2026-04-29 | 去除驱动层硬编码 `ResourceManager('@py')`：[keysight_53230A.py](../instruments/frequencyCounter/keysight_53230A.py)、[n6705c.py](../instruments/power/keysight/n6705c.py)、[mso64b.py](../instruments/scopes/tektronix/mso64b.py) 统一改为"默认系统 VISA + 可选 `visa_library` + 失败回退 `@py`"，并写入 [03_GOTCHAS.md §21](../docs/ai/03_GOTCHAS.md) | 修复 NI MAX 可通但 `pyvisa-py` 抛 `No device found.` |
| 2026-04-29 | 新增 53230A 频率计驱动 / Mock / 工厂 / UI 模组（[keysight_53230A.py](../instruments/frequencyCounter/keysight_53230A.py)、[mock_instruments.py](../instruments/mock/mock_instruments.py) `MockKeysight53230A`、[factory.py](../instruments/factory.py) `create_frequency_counter`、[keysight_53230a_module_frame.py](../ui/modules/keysight_53230a_module_frame.py)），`DIRECTORY_STRUCTURE.txt` 已同步 | 完整接入 53230A 通用计数器 |
| 2026-04-29 | 沉淀"UI 模组 Demo 入口需注入 `sys.path` 兼容直接运行"坑点：新增 [03_GOTCHAS.md §22](../docs/ai/03_GOTCHAS.md) 与 [08_CHECKLISTS.md 新增 UI 模组](../docs/ai/08_CHECKLISTS.md) 勾项 | 封堵 `ModuleNotFoundError: No module named 'ui'` 重复指令 |
| 2026-05-19 | 修复 `DarkComboBox` 首次展开下拉菜单高度不足（内容显示不全）的问题。方案：新增 `_ComboItemDelegate` 确保 delegate sizeHint 包含 padding；`showPopup` 中在 `super().showPopup()` 之前设置 `view.setMinimumHeight`；展开后隐藏不必要的 `QComboBoxPrivateScroller` | Qt `setView()` 自定义 QListView 后，首次 `showPopup()` 内部使用的 sizeHintForRow 不含 CSS padding，导致高度差约 3px/行 |
| 2026-05-22 | 修复全局 SVG 图标高 DPI 渲染问题：移除所有 `setDevicePixelRatio` 用法，改用 `QPixmap(size, size)` 逻辑大小直接渲染。影响 9 个文件（icon_utils / sidebar_nav_button / node_palette / custom_test_ui / sequence_canvas / oscilloscope_base_ui / n6705c_analyser_ui / n6705c_datalog_ui / vt6002_chamber_ui）。新增 [03_GOTCHAS.md §23](../docs/ai/03_GOTCHAS.md) | PySide6 QLabel/QIcon 不能正确处理带 DPR 标记的 pixmap |
| 2026-05-22 | 修复 Consumption Test 等页面间距问题：从 `get_page_base_qss()` 移除全局 `min-height`（QPushButton 32px / QComboBox 28px / QSpinBox 28px / QLineEdit 32px）。新增 [03_GOTCHAS.md §24](../docs/ai/03_GOTCHAS.md) | QSS `min-height` 级联覆盖子控件 `setFixedHeight()` 导致间距被挤占 |
| 2026-05-29 | 修复 N6705C Analyser 通道标签切到 CH4 时内容向上偏移几像素的问题；新增 [03_GOTCHAS.md §25](../docs/ai/03_GOTCHAS.md) | active/inactive tab QSS 盒模型不一致，`border-bottom: none` 与较小 padding 导致 Qt 重新计算 sizeHint |
| 2026-06-17 | AI Assist 阶段 0 完成：HTTP 依赖 `httpx>=0.27,<0.28`（装 0.27.2）入 `requirements.txt`；标题栏拍板方案 A 落 [decisions/003-ai-assist-titlebar.md](../docs/ai/decisions/003-ai-assist-titlebar.md)；网关实测 OK（New API `http://172.16.10.84:3000/v1` + Bearer，模型 `glm-5.1-fp8`/`deepseekv4flash`，tools+stream 均支持），结果落 [AI_Assist.md §5.0](../docs/ai/NewFT/AI_Assist.md)；新增冒烟脚本 `scripts/ai_smoke_test.py`；真实 base_url/Key 落 `user_data/ai/config.json`（gitignored） | 主窗口原生标题栏 → 方案 A 零风险；GLM 为推理模型，正文取 `message.content`、`reasoning` 独立，`max_tokens` 须 ≥1024；内网/localhost 直连需 httpx `trust_env=False` 绕系统代理 |
| 2026-06-17 | AI Assist 阶段 1（MVP）完成：新建 `core/ai/`（config/newapi_client/profiles/prompt_manager/ai_service/log_ring/providers）与 `ui/ai/`（ai_panel_button/ai_assist_panel/chat_view/ai_settings_dialog/panel_state）+ `ui/app_top_bar.py`（方案A 顶栏）；MainWindow 接 outer_splitter 包裹 main_splitter + 右侧 AIAssistPanel，面板开关/宽度持久化 `user_data/ai/ui_state.json`（宽度 300~600 默认 360）；`enabled=false` 隐藏面板按钮；页面切换经 `_fade_in_widget` → `AIService.set_page_context()` 切 Profile；`main.py` setup_logging 后 `install_log_ring()`；同步 DIRECTORY_STRUCTURE / spec(kk_lab.spec datas+hiddenimports)；真机 ping `glm-5.1-fp8` OK | AIService 用 QObject+QThread worker（每次请求新建线程，完成即回收）；ai_service 兜底 worker 异常转用户可读文案；`closeEvent` 须 `ai_service.shutdown()` 回收线程 |
| 2026-06-17 | AI Assist 阶段 2（日志分析与上下文增强）完成：新增 `core/ai/serial_rx_cache.py`（按 session_id 行缓存）/`context_builder.py`（聚合 Provider + 脱敏/等级过滤/超长摘要截断）/`schemas.py`（`LogAnalysisResult`）/`providers/log_provider.py`/`providers/serial_provider.py`；AIService 加 `analysis_ready` 信号 + `analyze_logs(ContextOptions)` + `feed_serial_rx()` + `set_serial_status_getter/set_execution_logs_getter` 回调注入；UI `ai_assist_panel` 加日志等级下拉 + 最大行数 SpinBox（上限 1000），`chat_view.add_analysis_message` severity 色阶富文本渲染；MainWindow 把 `SerialSessionManager.session_data_received` 喂入 RX 缓存并按当前页注入串口状态/执行日志 getter；core/ai 与 ui/ai MODULE_VERSION → 0.1.0 | core/ai 不依赖 ui/Qt：UI 状态全经轻量 Callable 回调注入；SerialSessionManager 是**每页面实例**非全局单例，须解析当前活动页的 `_sc_session_manager`；SerialSession 无文本缓存 → 独立 SerialRxCache；结构化分析靠 `_analysis_pending` 标志 + 让模型输出 JSON，正则提取 + `LogAnalysisResult.from_dict`，解析失败回退普通对话 |
| 2026-06-17 | AI Assist 阶段 3（测试配置与脚本生成）完成：`schemas.py` 加 `ConfigDraft/ScriptDraft` + JSON Schema；新增 `core/ai/response_parser.py`（双模式：原生 `tool_calls` / 降级 fenced/raw JSON + 轻量 Schema 子集校验 + `build_retry_hint`）、`core/ai/draft_validation.py`（`validate_script_draft` = `load_sequence_data` + `preflight_validate`，error/warning 语义）；`newapi_client.ChatResult` 增 `tool_calls`；AIService 用 `_pending_mode` 状态机替代 `_analysis_pending`，加 `draft_ready` 信号 + `generate_draft(kind, text)`；UI 新增 `ui/ai/config_preview.py`/`ui/ai/script_preview.py`（QDialog 预览 + 校验 + apply 回调），面板加「生成草案」按钮 + `set_config/script_apply_callback`；MainWindow `_update_ai_apply_callbacks`（custom_test 走 `canvas.load_from_nodes`，其它页面走页面自身 `apply_ai_config_draft(payload)`）；core/ai 与 ui/ai MODULE_VERSION → 0.2.0；同步 DIRECTORY_STRUCTURE / spec | 草案仅草案：生成→预览→本地校验→确认→apply；script 预览 error 禁 apply、warning 二次确认可继续；未引入 jsonschema（打包体积铁律），用自写 type/required/enum/items 子集校验；脚本草案 kind 决策：面板有 script_apply_cb（即 custom_test 页）→ script_draft，否则 config_draft；其它页面要接配置草案须实现 `apply_ai_config_draft(payload)->bool` |
| 2026-06-17 | AI Assist 阶段 4（Action Registry 与 UI/仪器控制）完成：新增 `core/ai/actions/`（registry/permission/dispatcher/audit/builder + handlers/{deps,query,ui,serial,instrument,test}）；动作链路 `Registry → JSON Schema 校验(复用 response_parser.validate_against_schema) → PermissionChecker → 必要时 ActionConfirmDialog → Dispatcher → AuditLog(user_data/ai/audit.log)`；16 个动作（查询6 low / UI2 low / serial clear=low send=high确认 / instrument query=low disconnect=medium set_output=critical默认禁 / test start,pause=high确认 stop=high）；`newapi_client.chat()` 加原生 `tools`/`tool_choice`；AIService agent 多轮 tool-calling（`_MAX_TOOL_ROUNDS=5` + `QTimer.singleShot(0,...)` 防 QThread 竞态，结果回灌 `role=tool`），加 `set_action_system`/`action_requested`/`action_result`；`ui/ai/action_confirm_dialog.py`（parent=面板，取消为默认按钮）；MainWindow `_setup_ai_action_system` 注入全套 getter/callback；MODULE_VERSION core/ai+ui/ai→0.3.0、core/ai/actions=0.1.0；ADR [004-ai-action-registry.md](../docs/ai/decisions/004-ai-action-registry.md)；同步 DIRECTORY_STRUCTURE/spec | actions 层禁 QtWidgets，handler 经 ActionDeps 注入回调间接操作 UI/仪器（守分层）；critical 双保险（PermissionChecker allow_critical=False + instrument handler 兜底禁）；仪器一律经 InstrumentManager，AI 无法绕过 instruments/；确认对话框模态全在主线程（worker.finished queued→主线程 dispatch→confirm_callback）；冒烟：low→executed/critical→denied/high无确认→cancelled 三态均写 audit.log(UTF-8 ensure_ascii=False)；env 无 ruff，用 py_compile 校验 |
| 2026-06-17 | AI Assist 阶段 5（体验优化）完成：5.1 流式 `newapi_client.chat_stream()`（SSE+`iter_lines`，`data:`/`[DONE]`，reasoning 不入正文）+ `AIService._StreamWorker` + `response_started/response_delta/response_finished` 信号，仅 chat 模式（无 tools）按 `settings.stream`(默认 True) 走流式，agent/analysis/draft 仍非流式；`ChatView.begin/append/end_stream_message` 同气泡增量 setText；5.2 新增 `core/ai/conversation_store.py`（`user_data/ai/history.json`，上限 40，仿 panel_state），AIService 启动加载/每轮保存/`clear_history` 清盘，面板 `_replay_history` 回放 + 顶栏「清空」；5.3 `config.available_models`(默认 glm-5.1-fp8/deepseekv4flash)+`AIService.set_model_override/current_model/available_models`(覆盖>Profile>默认)，面板 `QComboBox#aiModelCombo`+设置对话框可编辑模型清单/流式开关；5.4 各 Profile 加 `quick_actions`+`get_quick_actions(page_key)`，面板 `QuickActionRow`(`#aiQuickBtn`) 按 `current_page_key` 动态填充，切页 `_fade_in_widget→refresh_quick_actions`；5.5 标题栏方案 B（无边框+`app_top_bar.py` CSD）实测早已落地，文档标 ☑；MODULE_VERSION core/ai+ui/ai→0.4.0；同步 DIRECTORY_STRUCTURE | 流式只走 chat 模式；`_StreamWorker` 复用 `_teardown_thread`/`_cleanup_thread` 防 C++ 提前析构；ChatView 增量气泡用「文本+▍光标」end 时去光标；**ADR 003 记方案 A 但代码实际是方案 B（FramelessWindowHint+nativeEvent resize），以代码为准**；env 无 ruff 用 py_compile |
| 2026-06-18 | AI Assist 修复「多次设置仪器不生效 + 强制重试闪退」（[ai_service.py](../core/ai/ai_service.py)）：根因①上下文自我污染——AI 首轮真调工具后编造"系统已弹确认框/确认后即执行"叙述入 history 回灌，后续轮照抄、不发 tool_call→仪器不动；修复加 `_FORCE_TOOL_NUDGE`+`_looks_like_fake_execution`+`_agent_forced_retry`，仅 `_agent_rounds==0`（真·首轮）触发强制重试逼模型改用 tool_call。根因②强制重试在 worker `finished` 槽链里 `singleShot(0)` 再起新 worker，与首轮 QThread `finished→_cleanup_thread(deleteLater)` 清理竞态→无声闪退（faulthandler 空=Qt 状态损坏 abort 非 segfault）；修复改 `singleShot(50, _run_forced_retry)`（独立延后入口先 `_teardown_thread` 再 `_run_next_agent_round`）。新增 [03_GOTCHAS.md §26](../docs/ai/03_GOTCHAS.md)；用户实测不崩+每次可控仪器 | 诊断法：空 faulthandler→查 Qt 线程/对象生命周期；分步 `logger.warning` 夹逼（StreamHandler 每条 flush，末条可信）；worker finished 槽链里再起 QThread 须 `singleShot(≥50ms)`；env 无 ruff，用 import+IDE 诊断校验 |
| 2026-06-20 | AI Assist 波形解读修复「单位丢失 + 脉冲误计数 + Profile 语义缺失」：①单位事实源下沉——`parse_channel_label`/`unit_for_label`/`base_unit_for_label` 进 [n6705c_datalog_process.py](../instruments/power/keysight/n6705c_datalog_process.py)（无 Qt，守 core→instruments 方向），Viewer `_parse_ch_label`/`_unit_for_label` 与 provider `_infer_base_unit` 全委托复用，`F1-A-I1` 现正确识别电流→A→`_pick_scale` 显示 mA；②尖峰计数——[waveform_provider.py](../core/ai/providers/waveform_provider.py) 新增 `_cluster_spike_events`/`_build_event` 把超阈采样点按时间聚簇成事件，`schemas.WaveformStat` 加 `spike_events`，[prompt_manager.format_waveform_digest](../core/ai/prompt_manager.py) 输出"按时间聚簇计 N 处；超阈采样点共 M 个，非独立脉冲数"，消除 `[:10]` 截断诱导（实测 CSV 17 超阈点→4 尖峰）；③[profiles.py](../core/ai/profiles.py) datalog 补三条领域规则（按事件簇计数/直接采用摘要单位不自行换算/降采样点不可精确计数） | CSV 路径 `import_csv_file` 不×1000、dlog `import_dlog_file` ×1000，内存值语义统一为 mA/mV/mW，与 Viewer `_format_value(value_mA)` 一致；`_pick_scale` 仍÷1000 还原基本单位再 SI 选档，对两路径都正确；env 无 ruff 用 py_compile + `scripts/waveform_window_test.py` 回归 |
| 2026-06-20 | AI Assist 修复「重设 Marker A/B 后 AI 仍引用旧位置」：根因=波形摘要原注入 system 段，而首轮 AI 回答（含旧 Marker 具体数值结论）作为 assistant 历史回灌且离当前问题更近，模型锚定旧值。修复：[prompt_manager.build_messages](../core/ai/prompt_manager.py) 加 `waveform_context` 参数，把摘要从 system 段移到**本轮 user 消息开头**并附时效声明（"最新，以此为准；与历史冲突一律以本段为准，忽略旧波形"）；[ai_service.py](../core/ai/ai_service.py) `send` 加 `waveform_context` 透传、`send_with_waveform` 改走该参数（不再用 system 段 `extra_context`）；[ai_assist_panel.py](../ui/ai/ai_assist_panel.py) 新增 `_format_waveform_scope`，发送前在面板显示"本轮分析范围 — 可见范围 x0~x1 s；Marker A/B/时长"供用户核对 | history 仅存用户原文不残留波形大段文本（本就如此，未引入污染）；旧回答保留在 history（不破坏连续性）但被时效声明压制；agent 多轮/eval_runner 的 build_messages 不传 waveform_context（默认空，不受影响）；env 无 ruff 用 py_compile + 上下文结构断言验证 |

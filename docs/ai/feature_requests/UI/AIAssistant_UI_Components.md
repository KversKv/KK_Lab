# AI Assistant UI 组件与交互逻辑汇总

> 本文完整梳理 KK_Lab 中 AI Assistant（AI 助手）UI 层的全部组件、层级关系、对象名、信号槽与交互流程，作为 UI 维护与功能扩展的事实源。
> 代码事实源：[ui/ai/](../../../ui/ai/) + [ui/main_window.py](../../../ui/main_window.py) + [ui/app_top_bar.py](../../../ui/app_top_bar.py)。
> 配套文档：[AI_Assistant_Weight.md](../../../ui/ai/AI_Assistant_Weight.md)（配色与尺寸速查）、[AIAssist_Architecture.md](../AIAssist/AIAssist_Architecture.md)（整体架构）。

---

## 0. 文件清单

`ui/ai/` 目录下共 13 个 Python 文件 + 1 个配色文档，按职责分组：

| 类别 | 文件 | 类 / 模块 | 职责 |
|---|---|---|---|
| 主面板 | [ai_assist_panel.py](../../../ui/ai/ai_assist_panel.py) | `AIAssistPanel(QFrame)` | AI 助手右侧停靠面板的顶层容器，编排 Header / TaskTray / ChatView / 输入区 / 工具栏 |
| 主面板 | 同上 | `_TaskTray(QFrame)` | Header 与 ChatView 之间的任务托盘（待触发 / 进行中） |
| 主面板 | 同上 | `_InputEdit(QPlainTextEdit)` | Enter 发送、Shift+Enter 换行、聚焦蓝框、高度弹性自适应的输入框 |
| 主面板 | 同上 | `_PressScaleButton(QPushButton)` | 按下时几何缩放至 95% 的微动效按钮（Send） |
| 主面板 | 同上 | `_DigestWorker(QObject)` | 后台线程构建波形摘要，避免主线程卡顿 |
| 主面板 | 同上 | `_FlowLayout(QLayout)` / `_FlowWidget(QWidget)` | 自动换行的流式布局（Quick Row / Range / Action 行） |
| 聊天视图 | [chat_view.py](../../../ui/ai/chat_view.py) | `ChatView(QScrollArea)` | 消息列表展示，支持流式、Markdown、代码块、HTML 分析、任务卡、确认卡 |
| 聊天视图 | 同上 | `_MarkdownBubble(QWidget)` | AI 气泡：Markdown 段 + 代码块（带复制）混排 |
| 聊天视图 | 同上 | `ActionConfirmCard(QFrame)` | 聊天内联动作确认卡片（运行 / 拒绝 / 加白名单） |
| 顶栏按钮 | [ai_panel_button.py](../../../ui/ai/ai_panel_button.py) | `AIPanelButton(QPushButton)` | 顶栏右侧 checkable 开关按钮，控制面板显隐 |
| 设置对话框 | [ai_settings_dialog.py](../../../ui/ai/ai_settings_dialog.py) | `AISettingsDialog(QDialog)` | 4 标签页设置（常规 / 波形算法 / 白名单 / 本机经验）+ 测试连接 |
| 动作确认 | [action_confirm_dialog.py](../../../ui/ai/action_confirm_dialog.py) | `ActionConfirmDialog(QDialog)` | 模态确认对话框（high/critical 动作执行前弹） |
| 配置预览 | [config_preview.py](../../../ui/ai/config_preview.py) | `ConfigPreviewDialog(QDialog)` | 测试配置草案预览 + 应用 |
| 脚本预览 | [script_preview.py](../../../ui/ai/script_preview.py) | `ScriptPreviewDialog(QDialog)` | 测试脚本草案预览 + 校验 + before/after diff + 应用 |
| 沉淀对话框 | [curate_dialog.py](../../../ui/ai/curate_dialog.py) | `CurateDialog(QDialog)` | 通用沉淀草稿微调（纠偏 / 快捷指令 / 项目规则 / eval 用例） |
| 记忆对话框 | [kk_lab_memory_dialog.py](../../../ui/ai/kk_lab_memory_dialog.py) | `KKLabMemoryDialog(QDialog)` | 本页记忆归档草稿微调（5 类） |
| 记忆对话框 | 同上 | `KKLabMemoryManagerDialog(QDialog)` | 本页记忆管理（查看 / 删除 / 提升 / 转快捷指令 / 导出 eval） |
| 元素拾取 | [element_picker.py](../../../ui/ai/element_picker.py) | `ElementPicker(QObject)` + `_PickOverlay(QWidget)` | Ctrl+Shift+C 全局快捷键进入拾取模式，单击抽取控件内容注入 AI |
| 状态持久化 | [panel_state.py](../../../ui/ai/panel_state.py) | 模块函数 | `user_data/ai/ui_state.json` 读写（panel_open / panel_width） |
| 会话导出 | [transcript_exporter.py](../../../ui/ai/transcript_exporter.py) | `build_export_markdown(...)` | 把面板内扁平流水格式化为 Markdown 调试导出 |
| 模块版本 | [__init__.py](../../../ui/ai/__init__.py) | `MODULE_VERSION = "0.5.0"` | 模块子版本号 |

---

## 1. 顶层集成（与主窗口的关系）

### 1.1 集成位置

AI Assistant UI 通过 [MainWindow._setup_ai_panel()](../../../ui/main_window.py) 挂载到主窗口：

```
MainWindow
├── AppTopBar (self.top_bar)
│   └── AIPanelButton (self.top_bar.ai_panel_button)   ← 顶栏右侧开关
└── main_layout (QVBoxLayout)
    └── outer_splitter (QSplitter, Horizontal)          ← 拖拽分隔
        ├── main_splitter (左侧主内容区)
        └── AIAssistPanel (self.ai_panel)               ← 右侧 AI 面板
```

### 1.2 启用条件

- `MainWindow.with_ai=True` 且 `ai_settings.enabled=True` 时才创建面板与按钮；
- 否则 `AIPanelButton.setVisible(False)`、`AIAssistPanel` 不创建。

### 1.3 主窗口 ↔ 面板信号连接

| 主窗口 → 面板 | 面板 → 主窗口 |
|---|---|
| `set_config_apply_callback(self._apply_ai_config_draft)` | `request_close` → `_on_ai_panel_close_requested` |
| `set_script_apply_callback(self._apply_ai_script_draft)`（仅 Orchestrator 页） | `request_open` → `_on_ai_panel_open_requested` |
| `set_waveform_provider_callback(self._provide_ai_waveform_digest)`（仅 Datalog 页） | `pick_requested` → `_on_pick_requested` |
| `set_waveform_range_getter(self._provide_ai_waveform_range)` | |
| `set_waveform_marker_getter(self._provide_ai_waveform_marker)` | |
| `refresh_quick_actions()` / `on_page_changed()`（切页时） | |

### 1.4 面板宽度与持久化

- 宽度由 `outer_splitter` 拖拽控制，范围 240~600，默认 360（[panel_state.py](../../../ui/ai/panel_state.py) 钳制）；
- `panel_open` / `panel_width` 持久化到 `user_data/ai/ui_state.json`，启动时由 `load_panel_state()` 读回；
- `AIPanelButton.toggled` → `_on_ai_panel_toggled` → `_apply_ai_panel_visibility` 控制显隐与 splitter sizes。

### 1.5 元素拾取器挂载

- `MainWindow._setup_element_picker()` 创建 `ElementPicker(self, on_pick=self._on_element_picked)`；
- 全局快捷键 `Ctrl+Shift+C` 触发 `toggle()`；
- 拾取结果经 `_on_element_picked(label, content)` → `ai_panel.attach_picked_context(label, content)` 注入面板。

---

## 2. AIAssistPanel 主面板

### 2.1 顶层容器

| 项 | 值 |
|---|---|
| 类 | `AIAssistPanel(QFrame)` |
| objectName | `aiAssistPanel` |
| 根布局 | `QVBoxLayout`，`contentsMargins=(0,0,0,0)`，`spacing=0` |
| 背景色 | `#070709`（deep surface） |
| 左边框 | `1px solid #1e293b`（与主区分隔） |
| 最小宽度 | 240 |

### 2.2 根布局自上而下顺序

```
QVBoxLayout (root)  margins=(0,0,0,0) spacing=0
├── 1. Header 栏           _build_header()          QFrame#aiHeaderBar（高 56）
├── 2. TaskTray            _TaskTray()               QFrame#aiTaskTray（无任务 0 高）
├── 3. ChatView            ChatView()                QScrollArea  stretch=1
└── 4. 底部交互区          QFrame#aiBottomBar        margins=(16,12,16,12) spacing=12
    ├── 4.1 Quick Row      _build_quick_row()        _FlowWidget（快捷指令胶囊）
    ├── 4.2 ComposeBox     QFrame#aiComposeBox       输入框 + 控件区合体
    │   ├── aiInputArea    QFrame#aiInputArea        margins=(12,12,12,12)
    │   │   └── _InputEdit#aiInput                   弹性高 80~160
    │   └── aiControlsArea QFrame#aiControlsArea     margins=(12,10,12,12) spacing=10
    │       ├── Range 行   _build_range_bar()        _FlowLayout（Log Level / Max Lines）
    │       ├── Action 行  _build_action_bar()       _FlowWidget（拾取/分析/草稿/波形）
    │       └── Send 行    _build_send_bar()         QHBoxLayout（Model / Send）
    └── 4.3 Usage 行        _build_usage_bar()        QWidget（用量统计）
```

### 2.3 Header（标题栏）— `_build_header()`

容器 `QFrame#aiHeaderBar`：固定高 56，背景 `#020617`，底边框 `1px #1e293b`；内部 `QHBoxLayout`，`margins=(16,0,16,0)`，`spacing=6`，从左到右：

| 顺序 | 组件 | objectName | 说明 |
|---|---|---|---|
| 1 | `QLabel`（图标） | `aiPanelTitleIcon` | 18×18，渲染 `ai_panel.svg`，染色 `#3b82f6` |
| 2 | `QLabel("AI Assistant")` | `aiPanelTitle` | 标题，`#e2e8f0`，14px，bold |
| 3 | `addStretch(1)` | — | 弹性占位 |
| 4 | `QPushButton`（清空图标） | `aiIconBtn` | 清空当前会话历史，tooltip "Clear current conversation history" |
| 5 | `QPushButton`（导出图标） | `aiIconBtn` | 导出会话调试 Markdown，tooltip "Export this session's debug info..." |
| 6 | `QPushButton`（设置图标） | `aiIconBtn` | 打开 `AISettingsDialog` |
| 7 | `QLabel("｜")` | `aiHeaderSep` | 竖直分隔符 |
| 8 | `QPushButton`（关闭图标） | `aiCloseBtn` | 固定宽 28，触发 `request_close` 信号 |

> Header 按钮统一 28×28、圆角 6、hover 底 `#1e293b`；图标用 `tinted_svg_icon` 染色 `#94a3b8` 16px。

### 2.4 TaskTray（任务托盘）— `_TaskTray`

位置：Header 与 ChatView 之间。无任务时整体隐藏（0 高），不占聊天空间。

| 项 | 值 |
|---|---|
| objectName | `aiTaskTray` |
| 背景 | `#0b1428`，底边框 `1px #1e293b` |
| 摘要按钮 | `QPushButton#aiTaskTrayToggle`，文案 `▾/▸  ⏱ 待触发 M · ⟳ 进行中 N` |
| 列表容器 | `QFrame#aiTaskTrayList`，背景 `#121629`，圆角 8，默认隐藏 |
| 行控件 | `QLabel#aiTaskTrayRow` + `QPushButton#aiTaskTrayBtn`（取消 / 查看结果） |
| 信号 | `cancel_requested(task_id)` / `view_requested(task_id)` |
| 刷新机制 | 面板内 `QTimer` 1500ms 周期拉取 `scheduled_task_registry` + `pending_task_registry`（仅当前 session） |

**交互**：
- 点击摘要按钮展开/收起列表；
- 调度任务行：[取消] → `dispatcher.dispatch("cancel_scheduled_task", {"task_id": ...})`；
- 异步任务行：[查看结果] → `dispatcher.dispatch("get_task_result", {"task_id": ...})` → `chat.add_task_card(...)`。

### 2.5 ChatView（消息列表）

详见 §3。

### 2.6 Quick Row（快捷指令）— `_build_quick_row()`

- `_FlowWidget` + `_FlowLayout`，`spacing=6`，首尾 `addStretch`；
- 由 `refresh_quick_actions()` 按当前页面 Profile 动态重建按钮；
- 按钮 `QPushButton#aiQuickBtn`：胶囊样式（圆角 8），底 `#0f172a`，字 `#94a3b8`，边框 `#1e293b`，hover 底 `#1e293b` 字 `#cbd5e1`；
- 无快捷项时整行 `setVisible(False)`。

**交互**：
- 点击 → `_on_quick_clicked(text)`；
- 若模板带占位符（`{xxx}`）→ 弹轻量 `QDialog` 收集参数 → `fill_quick_action` 填充；
- 填入输入框 → 直接触发 `_on_send_clicked()`。

### 2.7 ComposeBox（输入区合体）

`QFrame#aiComposeBox` 圆角 12，边框 `#1e293b`，聚焦时边框变 `#3b82f6`（通过 `setProperty("focused", ...)` + `unpolish/polish` 切换）。内部分两层：

#### 2.7.1 aiInputArea（输入框层）

- `QFrame#aiInputArea`，margins=(12,12,12,12)，背景 `#070709`，顶圆角 11；
- 内含 `_InputEdit#aiInput`：
  - 高度弹性 80~160（`documentSizeChanged` 自适应）；
  - placeholder `Ask a question, Enter to send / Shift+Enter for new line`；
  - Enter → `submitted` 信号 → `_on_send_clicked`；Shift+Enter 换行；
  - `focus_changed` 信号驱动 ComposeBox 蓝色焦点环。

#### 2.7.2 aiControlsArea（控件层）

- `QFrame#aiControlsArea`，margins=(12,10,12,12)，背景 `#04060f`，顶边框 `1px #1e293b`，底圆角 11；
- 内含三行：Range 行 / Action 行 / Send 行。

### 2.8 Range 行 — `_build_range_bar()`

`_FlowLayout`，`spacing=6`，左对齐：

| 组件 | objectName | 说明 |
|---|---|---|
| `QLabel("Log Level")` | `aiRangeLabel` | `#64748b`，10px/700 |
| `QComboBox` | `aiLevelCombo` | 取值 `DEBUG/INFO/WARN/ERROR`，默认 `INFO` |
| `QLabel("Max Lines")` | `aiRangeLabel` | 同上 |
| `QSpinBox` | `aiLinesSpin` | 范围 20~1000（`_MAX_LINES_CAP`），步进 50，默认 300 |

> 仅在 Analyze 日志时使用，控制 `ContextOptions` 的 `max_app_lines/max_exec_lines/max_rx_lines` 与 `min_level`。

### 2.9 Action 行（工具栏）— `_build_action_bar()`

`_FlowWidget` + `_FlowLayout`，`spacing=8`：

| 组件 | objectName | 图标 | tooltip | 行为 |
|---|---|---|---|---|
| 拾取按钮 | `aiToolIconBtn` | `inspect.svg` 染 `#34d399` | "Pick any element/data on the page (Ctrl+Shift+C)..." | 触发 `pick_requested` 信号 |
| 分析按钮 | `aiToolIconBtn` | `activity.svg` 染 `#3b82f6` | "Analyze based on recent run logs" | `_on_analyze_clicked` → `service.analyze_logs(options)` |
| 草稿按钮 | `aiToolIconBtn` | `code.svg` 染 `#818cf8` | "Generate a test config/script draft..." | `_on_draft_clicked` → `service.generate_draft(kind, text)` |
| 波形按钮 | `aiAnalyzeBtn` | — | "Send the current page's waveform..." | 默认 `setVisible(False)`，仅当页面注入波形回调时显示 |

> 三个工具图标按钮统一 28×28、圆角 6、hover 底 `#1e293b`。

### 2.10 Send 行 — `_build_send_bar()`

`QHBoxLayout`，`spacing=8`：

| 组件 | objectName | 说明 |
|---|---|---|
| `QComboBox`（Model） | `aiModelCombo` | 透明背景线框，`minWidth=80`，`Expanding` 策略；首项 `Auto (Page)`，其余来自 `service.available_models()` |
| `_PressScaleButton("Send")` | `aiSendBtn` | 主操作高亮：白字 / 实心蓝 `#2563eb`，hover `#1d4fd0`；按下缩放 95% 微动效；禁用底 `#0f172a`/字 `#475569`；busy 时文案 "Processing…" |

**Model 切换交互**：
- `currentTextChanged` → `_on_model_changed` → `service.set_model_override(model or None)` + 系统消息提示；
- `AISettingsDialog` 保存后 → `_populate_models()` 重建下拉项。

### 2.11 Usage 行 — `_build_usage_bar()`

- `QWidget` + `QHBoxLayout`，`spacing=6`，末尾 `addStretch`；
- `QLabel#aiUsageLabel`，初始 `Usage (tokens): None`，可选中复制；
- 实时格式：`This turn ↑{prompt} ↓{completion} tokens @ {tps} tok·s⁻¹ | Session ↑{..} ↓{..} tokens ({requests} requests)`；
- 由 `service.usage_updated` 信号驱动 `_on_usage_updated`。

### 2.12 面板对外信号

| 信号 | 触发时机 |
|---|---|
| `request_close` | Header × 按钮点击 |
| `request_open` | 元素拾取后注入上下文时（自动展开面板） |
| `pick_requested` | Action 行拾取按钮点击 |

### 2.13 面板注入回调（由主窗口设置）

| 回调 | 用途 |
|---|---|
| `set_config_apply_callback(cb)` | `cb(ConfigDraft) -> (ok, message)`，配置草案应用 |
| `set_script_apply_callback(cb)` | `cb(nodes) -> (ok, message)`，脚本草案应用（仅 Orchestrator 页） |
| `set_waveform_provider_callback(cb)` | `cb(x_range, marker) -> WaveformDigest | None`（仅 Datalog 页） |
| `set_waveform_range_getter(getter)` | `getter() -> (x0, x1) | None` |
| `set_waveform_marker_getter(getter)` | `getter() -> {"a","b"} | None` |

### 2.14 面板 ↔ AIService 信号连接（`_wire_service`）

| Service 信号 | 面板槽 | 行为 |
|---|---|---|
| `response_ready` | `_on_response` | 添加 AI 消息气泡 |
| `response_started` | `_on_stream_started` | 开始流式气泡 |
| `response_delta` | `_on_stream_delta` | 追加流式增量 |
| `response_finished` | `_on_stream_finished` | 结束流式气泡 |
| `analysis_ready` | `_on_analysis` | 添加结构化日志分析气泡 |
| `draft_ready` | `_on_draft_ready` | 弹 Config/Script 预览对话框 |
| `error_occurred` | `_on_error` | 丢弃流式气泡 + 系统消息 |
| `busy_changed` | `_on_busy_changed` | 切换 Send/Analyze/Draft/Waveform 按钮启用态 |
| `connection_tested` | `_on_connection_tested` | 系统消息提示连接结果 |
| `action_requested` | `_on_action_requested` | 记录流水 |
| `action_result` | `_on_action_result` | 系统消息提示执行结果 |
| `usage_updated` | `_on_usage_updated` | 刷新 Usage 行 |
| `task_resumed` | `_on_task_resumed` | 添加任务卡（自动续跑角标） |
| `task_resume_skipped` | `_on_task_resume_skipped` | 添加任务卡（降级提示） |

---

## 3. ChatView 聊天视图

### 3.1 容器

| 项 | 值 |
|---|---|
| 类 | `ChatView(QScrollArea)` |
| `widgetResizable` | True |
| `FrameShape` | NoFrame |
| 水平滚动条 | AlwaysOff |
| 内部容器 | `QWidget` + `QVBoxLayout`，margins=(16,16,16,16)，spacing=20，末尾 `addStretch(1)` |
| 样式 | `SCROLLBAR_STYLE + _CHAT_VIEW_RESET_STYLE` |

### 3.2 消息气泡类型

| 类型 | 控件 | objectName | 对齐 | 背景 / 文字 | 圆角 |
|---|---|---|---|---|---|
| 用户消息 | `QLabel` | `aiBubbleUser` | 右对齐，最大宽 ≈ 可用宽 × 0.88 | `#18397a` / `#eff6ff` | 16（右下 2px） |
| AI 消息 | `_MarkdownBubble`（内含 `QTextBrowser#aiBubbleAI`） | `aiBubbleAI` | 铺满 | `#121629` / `#cbd5e1`，边框 `#1e293b` | 16（左下 2px） |
| 系统消息 | `QLabel` | `aiBubbleSys` | 居中 | 透明 / `#64748b`，11px | — |
| 代码块 | `QFrame` + `QPlainTextEdit` | `aiCodeFrame` / `aiCodeText` | — | `#070709`，边框 `#1e293b` | 12 |
| 日志分析 | `QTextBrowser`（HTML） | `aiBubbleAI` | — | 按严重度着色（info/low/medium/high/critical） | 16 |
| 任务卡片 | `QFrame` | `aiTaskCard` | — | `#0b1428`，边框 `#1e293b` | 12 |
| 确认卡片 | `ActionConfirmCard(QFrame)` | `aiConfirmFrame` | — | `#121629`，边框 `#1e293b` | 12 |

### 3.3 AI 气泡结构（`_MarkdownBubble`）

- 把 Markdown 文本按 ```` ``` ```` 围栏拆分为 `md` / `code` 块序列；
- `md` 块用 `QTextBrowser#aiBubbleAI` 渲染（`setMarkdown`），自动适配高度（`documentSizeChanged` + `QTimer.singleShot(0, _fit_height)`）；
- `code` 块用 `QFrame#aiCodeFrame` 包裹：
  - 顶部 header：`QLabel#aiCodeLang`（语言名）+ `QPushButton#aiCopyBtn`（复制按钮）；
  - 主体：`QPlainTextEdit#aiCodeText` 只读，等宽字，NoWrap，高度 `min(320, 18*lines+12)`；
- 链接点击：`http/https/mailto` 用 `QDesktopServices.openUrl`，其余忽略。

### 3.4 AI 气泡底部动作条（`_make_ai_footer`）

每条 AI 消息下方插入一条动作条：

| 按钮 | 图标 | 行为 |
|---|---|---|
| 👍 | `thumbs-up.svg` 染 `#cbd5e1` 12px | `feedback_submitted(msg_id, "up")` |
| 👎 | `thumbs-down.svg` 染 `#cbd5e1` 12px | `feedback_submitted(msg_id, "down")` |
| ⋯ | `more-horizontal.svg` 染 `#cbd5e1` 14px | 弹沉淀菜单（见 §3.5） |

### 3.5 沉淀菜单（`_show_curate_menu`）

`QMenu` 结构：

```
沉淀为纠偏            → curate_requested("nudge", "")
沉淀为快捷指令        → curate_requested("quick_action", "")
沉淀为项目规则        → curate_requested("project_rule", "")
沉淀为 eval 用例      → curate_requested("eval_case", "")
─────────────
归档到本页记忆 ▸
    本页长期记忆      → curate_requested("kk_memory", "")
    本页经验/排障     → curate_requested("kk_lesson", "")
    本页测试项        → curate_requested("kk_test_item", "")
    本页测试用例      → curate_requested("kk_test_case", "")
    本页快捷指令      → curate_requested("kk_quick_action", "")
─────────────
管理本页记忆…        → manage_memory_requested()
```

### 3.6 流式渲染

| 方法 | 说明 |
|---|---|
| `begin_stream_message()` | 创建空 `_MarkdownBubble`，初始内容 `"▍"` 光标 |
| `append_stream_delta(chunk)` | 累加到 `_stream_text`，整段重渲染 Markdown + 末尾 `" ▍"` 光标，滚动到底 |
| `discard_stream_message()` | 出错时保留已收文本，去掉光标，标记流式结束 |
| `end_stream_message(final_text)` | 写入最终全文，清理状态，追加 footer |

### 3.7 任务卡片（`add_task_card`）

- 同一 `task_id` 重复调用为原地更新（text/badge 变化即刷新），不重复插入；
- `auto_resume=True` 时显示 `aiTaskCardBadge` "自动续跑" 角标（绿底 `#122a1c` / 绿字 `#4ade80`）；
- 数据结构：`self._task_cards[task_id] = (card, text_label, badge_label)`。

### 3.8 内联动作确认卡片（`ActionConfirmCard`）

仅在 high/critical 动作需要确认时插入聊天流（由 `AIAssistPanel.confirm_action` 触发）：

| 元素 | objectName | 说明 |
|---|---|---|
| 标题 | `aiConfirmTitle` | `待确认动作 · {风险CN} · {action_name}`，橙 `#fbbf77` |
| 描述 | `aiConfirmDesc` | `description + reason` |
| 参数 | `aiConfirmArgs` | 只读 `QPlainTextEdit`，JSON pretty，高度 `min(140, 18*lines+14)` |
| 状态 | `aiConfirmDesc` | 收尾时显示，默认隐藏 |
| 运行按钮 | `aiConfirmRun` | 绿底 `#16a34a` |
| 拒绝按钮 | `aiConfirmReject` | 红底 `#2a1414` / 红字 `#fca5a5` |
| 加白名单按钮 | `aiConfirmAllow` | 蓝底 `#0e1b33` / 蓝字 `#3b82f6`，**仅 high 风险可见**（critical 不可白名单） |

**信号**：`run_clicked` / `reject_clicked` / `allow_clicked`。

**收尾**：`finalize(status_text)` 禁用所有按钮 + 显示状态文案。

### 3.9 ChatView 对外信号

| 信号 | 触发 |
|---|---|
| `feedback_submitted(msg_id, rating)` | 👍/👎 点击 |
| `curate_requested(kind, payload)` | 沉淀菜单项点击 |
| `manage_memory_requested()` | "管理本页记忆…" 点击 |

### 3.10 其他方法

| 方法 | 说明 |
|---|---|
| `add_user_message(text)` | 右对齐用户气泡，`QTimer.singleShot(0, _fit_user_bubble)` 二次刷新宽度 |
| `add_ai_message(text)` | Markdown 气泡 + footer |
| `add_system_message(text)` | 居中系统消息 |
| `add_system_action(text, button_text, callback)` | 系统消息 + 内联动作按钮（如"撤销"） |
| `add_analysis_message(result)` | 结构化日志分析 HTML（严重度色 + 证据/原因/建议列表） |
| `add_action_confirm(...)` | 插入 `ActionConfirmCard` |
| `clear()` | 清空所有气泡，恢复空白会话 |
| `resizeEvent` | 重新计算用户气泡最大宽度 |

---

## 4. 对话框

### 4.1 AISettingsDialog（设置对话框）

[ai_settings_dialog.py](../../../ui/ai/ai_settings_dialog.py)，4 标签页 + 测试连接：

| 标签页 | 内容 |
|---|---|
| 常规 | 启用开关 / Base URL / API Key（Password 模式）/ 模型模式（auto/fixed）/ 默认模型 / 可选模型 / 流式 / 超时 / 日志行数 / 脱敏 / 历史压缩 / AI 沉淀 / 遥测 |
| 波形算法 | 事件算法下拉（`kind=event` 自动列举）+ 动态参数表单（按算法 `params_cls` 重建，回填非默认覆盖值） |
| 白名单 | 常驻白名单 `QListWidget`（移除所选）+ 黑名单 `QListWidget`（加入/移除） |
| 本机经验 | 一键回归（mock）+ 本机沉淀列表（纠偏/快捷/eval）+ 删除/导出经验包/重置为出厂 |

**按钮栏**：测试连接 / 取消 / 保存（`aiOkBtn` 主蓝 `#5b3df5`）。
**约定**：所有 OK/Cancel/Test 按钮 `autoDefault/setDefault` 显式二元化；保存后调 `service.start_telemetry()`。

### 4.2 ActionConfirmDialog（模态确认对话框）

[action_confirm_dialog.py](../../../ui/ai/action_confirm_dialog.py)，high/critical 动作执行前弹：

| 元素 | 说明 |
|---|---|
| 标题 | `AI 动作确认` |
| 头部 | `AI 请求执行动作：{action_name}` |
| 描述 | `description` |
| 风险等级 | `aiRisk`，按风险等级染色（low 绿 / medium 黄 / high 橙 / critical 红） |
| 风险提示 | `aiHint`，橙 `#ffb27a` |
| 参数 | 只读 `QPlainTextEdit`，JSON pretty |
| 白名单勾选 | **仅 high 风险**：`本次会话内自动批准` + `以后始终自动批准`（互斥联动：勾常驻自动勾会话） |
| 按钮 | 取消（default）/ 确认执行（`aiOkBtn` 红底 `#b3422f`） |

**返回**：`remember_session` / `remember_resident` 属性。

> 注：当前主流程已改为内联 `ActionConfirmCard`（§3.8），此模态对话框作为备用/历史路径保留。

### 4.3 ConfigPreviewDialog（配置草案预览）

[config_preview.py](../../../ui/ai/config_preview.py)：

| 元素 | 说明 |
|---|---|
| 头部 | `目标页面：{target}　标题：{title}` |
| 备注 | `draft.notes`（`aiHint`） |
| 编辑器 | 只读 `QPlainTextEdit`，JSON pretty |
| 提示 | `aiHint`，应用失败时红 `#ff8a8a` |
| 按钮 | 取消 / 应用配置（`aiOkBtn` 主蓝 `#5b3df5`） |

**应用流程**：`_on_apply` → `apply_cb(draft)` → `(ok, message)`：
- `ok=True` → `accept()`；
- `ok=False` → 显示 `✗ {message}`，不关闭。

### 4.4 ScriptPreviewDialog（脚本草案预览）

[script_preview.py](../../../ui/ai/script_preview.py)，比 Config 多校验 + diff：

| 元素 | 说明 |
|---|---|
| 头部 | `标题：{title}　节点数：{len(sequence)}` |
| 主体 | `QTabWidget`：草案 JSON / 对比当前画布 (diff)（仅当提供 `before_sequence`） |
| diff 视图 | `QTextEdit` HTML，unified diff，增绿/删红/位置蓝/普通灰 |
| 校验 | `_run_validation` → `validate_script_draft(draft)` → `DraftValidationResult` |
| 问题标签 | `aiIssues`：error 红 / warning 黄 / 通过绿；error 禁用应用按钮，warning 改文案为"仍要应用" |
| 按钮 | 取消 / 应用到画布（`aiOkBtn`） |

**应用流程**：
1. error → 禁用按钮；
2. warning → 首次点击改文案"再次点击确认应用"，第二次点击才真应用；
3. 调 `apply_cb(result.nodes)` → `(ok, message)`。

### 4.5 CurateDialog（通用沉淀微调）

[curate_dialog.py](../../../ui/ai/curate_dialog.py)：

| 元素 | 说明 |
|---|---|
| 标题 | 按类型：`沉淀为纠偏片段` / `沉淀为快捷指令` / `沉淀为项目规则` / `沉淀为 eval 用例` |
| 来源提示 | `来源：{_src}` |
| 表单 | `QFormLayout`，按 draft 字段动态生成：`text/user/assistant/desc` 用多行 `QPlainTextEdit`（高 80），字符串用 `QLineEdit`，list/dict 用 JSON 编辑框（高 100） |
| 按钮 | 写入（OK）/ 取消（Cancel），`autoDefault/setDefault` 二元化 |

**返回**：`result_draft()` 收集编辑后的字段，保留 `_src` 等内部键。

### 4.6 KKLabMemoryDialog（本页记忆归档微调）

[kk_lab_memory_dialog.py](../../../ui/ai/kk_lab_memory_dialog.py)：

| 元素 | 说明 |
|---|---|
| 标题 | 按 `draft_kind`：`归档为本页长期记忆` / `经验` / `测试项` / `测试用例` / `快捷指令` |
| 信息行 | `页面 / 类型 / ID` |
| 来源提示 | `来源：{_src}`（灰 `#7b88a8`） |
| 表单 | 标题 `QLineEdit` + 按 `fields` 动态生成（多行键用 `QPlainTextEdit` 高 80） |
| 项目级勾选 | `写入项目级 docs（需二次确认，纳入版本控制）` |
| 按钮 | 写入 / 取消 |

**返回**：`result_draft()` 含 `fields` / `target`（`TARGET_LOCAL` 或 `TARGET_PROJECT`）。

### 4.7 KKLabMemoryManagerDialog（本页记忆管理）

同文件，Phase 3 管理入口：

| 元素 | 说明 |
|---|---|
| 信息行 | `页面：{page_key}    项目级 docs + 本机私有层合并展示` |
| 类型筛选 | `QComboBox`：全部 5 类 / 长期记忆 / 经验 / 测试项 / 测试用例 / 快捷指令 |
| 列表 | `QListWidget`，条目格式 `[kind] [本机/项目] entry_id - title (tags)`，右键菜单 |
| 按钮 | 删除选中 / 提升本机条目到项目级 / 从测试项生成快捷指令 / 导出测试用例为 eval 草稿 / 刷新 / 关闭 |

**右键菜单**：删除 / 提升到项目级（仅本机条目）/ 生成快捷指令（仅测试项）/ 导出 eval 草稿（仅测试用例）。
**操作均带 `QMessageBox.question` 二次确认**。

---

## 5. ElementPicker 元素拾取器

[element_picker.py](../../../ui/ai/element_picker.py)，类浏览器 F12 风格的页面元素拾取：

### 5.1 组成

| 类 | 职责 |
|---|---|
| `ElementPicker(QObject)` | 协调器，挂 MainWindow，注册全局快捷键 `Ctrl+Shift+C` |
| `_PickOverlay(QWidget)` | 主窗口内置顶遮罩，跟随鼠标高亮命中控件 |

### 5.2 交互流程

1. `Ctrl+Shift+C` → `toggle()` → `start()` 创建 `_PickOverlay`；
2. 遮罩半透明蓝底（`QColor(2,6,23,60)`），跟随鼠标高亮命中控件（蓝框 `#3b82f6` + badge 显示 `ClassName#objectName`）；
3. **左键单击** → `pick_at(global_pos)` → `_extract(widget)` → `cancel()` → `_on_pick(label, content)`；
4. **右键 / ESC** → `cancel()` 关闭遮罩。

### 5.3 内容抽取策略（`_extract`）

按控件类型优先级：

| 类型 | 抽取方式 | 限制 |
|---|---|---|
| pyqtgraph 曲线 | `getPlotItem()` → `listDataItems()` → `getData()`，格式化每条曲线统计 + 采样点 | 最多 400 点/曲线 |
| 表格（`QAbstractItemView`） | 遍历 model，` | ` 分隔，含表头 | 最多 200 行 × 40 列 |
| `QLabel` / `QPlainTextEdit` / `QTextEdit` / `QLineEdit` / `QComboBox` | `text()` / `toPlainText()` / `currentText()` | 最多 4000 字符 |
| 兜底 | `getattr(widget, "text", None)` | 同上 |

### 5.4 命中检测（`widget_at`）

- 限主窗口控件树内（`widget.window() is host.window()`）；
- 临时把遮罩设为 `WA_TransparentForMouseEvents` 后用 `QApplication.widgetAt` 命中，避免遮罩自身拦截；
- 排除遮罩自身及其子级。

---

## 6. AIPanelButton 顶栏开关

[ai_panel_button.py](../../../ui/ai/ai_panel_button.py)：

| 项 | 值 |
|---|---|
| 类 | `AIPanelButton(QPushButton)` |
| objectName | `aiPanelButton` |
| 尺寸 | 28×28 固定 |
| `checkable` | True |
| 图标 | `ai_panel.svg` 染 `#c6d4f2` 16px |
| 样式 | 透明底，hover `#1b2640`，checked `#5b3df5`（紫） |
| tooltip | "Open / close AI Assistant panel" |
| 位置 | `AppTopBar` 顶栏右侧，最小化按钮之前 |

---

## 7. PanelState 状态持久化

[panel_state.py](../../../ui/ai/panel_state.py)，纯模块函数：

| 函数 | 说明 |
|---|---|
| `load_panel_state() -> (panel_open, panel_width)` | 读 `user_data/ai/ui_state.json`，失败回退 `(False, 360)` |
| `save_panel_state(panel_open, panel_width)` | 写入 JSON |
| `clamp_width(width)` | 钳制 240~600，默认 360 |

> 与 `config.json`（功能配置）分离，仅存 UI 偏好。

---

## 8. TranscriptExporter 会话导出

[transcript_exporter.py](../../../ui/ai/transcript_exporter.py)，纯逻辑无 Qt 依赖：

`build_export_markdown(service, transcript, session_started_at, model_selection)` 输出包含：

1. 头部元信息（导出时间 / 会话开始 / page_key / 模型 / 手动选择模型）；
2. 系统提示（全局 + 页面 Profile）；
3. 会话流水（按轮次分组 + 步骤编号）：
   - 🧑 用户 / 🤖 AI 回复 / 📊 日志分析 / ⚠ 错误
   - ⚙ 请求执行指令 / ✅ 指令执行结果
   - ❓ 弹出确认卡片 / 🖱 确认决定
   - 📎 注入上下文（喂给模型的数据：波形摘要 / 拾取内容 / 无波形守卫）
   - 📈 用量
4. 持久化历史（`service.persisted_history`）；
5. 动作审计日志（`audit.log` 尾部 50 行）。

**触发**：Header 导出按钮 → `_on_export_clicked` → `QFileDialog.getSaveFileName` → 写文件 → 系统消息提示路径。

---

## 9. 完整交互流程

### 9.1 发送普通消息

```
用户在 _InputEdit 输入文本 → Enter
  → _on_send_clicked
    → text = input.toPlainText().strip()
    → input.clear()
    → 若有 waveform_provider_cb：走 _start_digest_send(via_button=False)（见 §9.4）
    → 否则：
        → _record("user", text)
        → chat.add_user_message(text)
        → picked = _take_picked_context()
        → _record_injected_context(picked=picked)
        → service.send(text, extra_context=picked)
  → service 异步发请求
    → response_started → chat.begin_stream_message()
    → response_delta × N → chat.append_stream_delta(chunk)
    → response_finished → chat.end_stream_message(content) + _record("assistant")
    → usage_updated → _on_usage_updated 刷新 Usage 行
  → 若出错：error_occurred → chat.discard_stream_message() + 系统消息
```

### 9.2 Analyze 日志

```
用户设置 Log Level + Max Lines → 点 Action 行分析按钮
  → _on_analyze_clicked
    → level = level_combo.currentText()
    → max_lines = min(lines_spin.value(), _MAX_LINES_CAP)
    → _record("user", text="[Analyze Logs] level≥{level}, ≤{max_lines} lines per type")
    → chat.add_user_message("Analyze recent logs (...)")
    → options = ContextOptions(max_app_lines, max_exec_lines, max_rx_lines, min_level, enable_masking)
    → service.analyze_logs(options)
  → service 异步分析
    → analysis_ready → _on_analysis → chat.add_analysis_message(result)
      （结构化 HTML：严重度色 + 证据/原因/建议列表）
```

### 9.3 生成草案（Config / Script）

```
用户在输入框描述需求 → 点 Action 行草稿按钮
  → _on_draft_clicked
    → text = input.toPlainText().strip()
    → kind = SCRIPT_DRAFT if script_apply_cb else CONFIG_DRAFT
    → _record("user", text="[Generate {label} Draft] {text}")
    → chat.add_user_message("Generate {label} draft: {text}")
    → input.clear()
    → service.generate_draft(kind, text)
  → service 异步生成
    → draft_ready(parsed) → _on_draft_ready
      → 若解析失败：系统消息 + AI 消息
      → 若 SCRIPT_DRAFT：_show_script_preview(payload) → ScriptPreviewDialog
      → 若 CONFIG_DRAFT：_show_config_preview(payload) → ConfigPreviewDialog
      → 用户确认应用 → apply_cb(draft/nodes) → (ok, message)
        → ok：dialog.accept() + 系统消息"已应用"
        → fail：显示错误，不关闭
```

### 9.4 发送波形（仅 Datalog 页）

```
用户点 Action 行 "Send Wave" 按钮（仅 Datalog 页可见）
  → _on_waveform_clicked
    → text = input.toPlainText() or 默认提示语
    → input.clear()
    → _start_digest_send(text, via_button=True)
      → 读 x_range = waveform_range_getter()
      → 读 marker = waveform_marker_getter()
      → 创建 _DigestWorker + QThread
      → worker.run() → waveform_provider_cb(x_range, marker) → WaveformDigest
      → finished → _on_digest_ready(digest)
        → 若 digest 为空：
            → via_button：系统消息"No waveform data"
            → 非 via_button：发普通消息 + _NO_WAVEFORM_GUARD 守卫（禁止 AI 编造数值）
        → 否则：
            → scope = _format_waveform_scope(digest)（可见范围 / Marker / 点数）
            → chat.add_system_message(scope)
            → picked = _take_picked_context()
            → via_button：chat.add_user_message("[Send Waveform] {text}")
            → _record_injected_context(digest, picked, scope)
            → service.send_with_waveform(text, digest, extra_context=picked)
  → 后续走 §9.1 的流式响应流程
```

### 9.5 元素拾取

```
用户按 Ctrl+Shift+C（或点 Action 行拾取按钮 → pick_requested → main_window._on_pick_requested）
  → ElementPicker.start() → 显示 _PickOverlay
  → 鼠标移动 → 高亮命中控件 + badge
  → 左键单击 → pick_at(global_pos)
    → widget = widget_at(global_pos)
    → cancel() 关闭遮罩
    → label, content = _extract(widget)（曲线/表格/文本/兜底）
    → _on_pick(label, content) → main_window._on_element_picked
      → ai_panel.attach_picked_context(label, content)
        → 累加到 _pending_picked_context
        → request_open.emit()（自动展开面板）
        → input.setFocus()
        → chat.add_system_message("已附加页面内容「{label}」，将随下一条消息发送给 AI。")
  → 下次 send 时 _take_picked_context() 取出并清空，随 extra_context 发出
```

### 9.6 动作确认（high/critical）

```
AI 回复中请求执行 high/critical 动作
  → service.action_requested → _on_action_requested（记录流水）
  → dispatcher 调 panel.confirm_action(spec, arguments, reason)
    → _record("confirm_prompt", ...)
    → card = chat.add_action_confirm(action_name, description, risk_level, arguments)
    → 局部 QEventLoop 阻塞等待用户选择
    → 用户点击：
        → 运行 → _finish(ConfirmResult(confirmed=True), "✓ Run selected")
        → 拒绝 → _finish(ConfirmResult(confirmed=False), "⛔ Execution rejected")
        → 加白名单（仅 high）→ _finish(ConfirmResult(confirmed=True, remember_resident=True), "✓ Added to whitelist and run")
    → card.finalize(status_text)
    → loop.quit()
    → 返回 ConfirmResult 给 dispatcher
  → dispatcher 执行/拒绝动作
  → service.action_result → _on_action_result
    → 系统消息：⚡ Auto-executed via whitelist / ✓ Executed / ⛔ Denied / ✗ Cancelled / ⚠ Execution failed
```

### 9.7 沉淀（Curate）

```
用户点 AI 气泡下方 ⋯ → 沉淀菜单
  → 选择沉淀类型 → chat.curate_requested(kind, "")
  → panel._on_curate_requested(kind, _payload)
    → 取 last_user_text + last_assistant_text + page_key 组成 turn
    → 若 kind 以 "kk_" 开头：_start_kk_lab_curate(kind, turn)
      → 后台 QThread + KKLabMemoryCurator.make_draft(turn, kind)
      → done → _on_kk_lab_draft_made → KKLabMemoryDialog 微调
        → 用户确认 → kk_lab_memory.append_entry(...) → 系统消息"已归档"
    → 否则：_start_curate(kind, turn)
      → 后台 QThread + Curator.make_draft(turn, kind)
      → done → _on_draft_made → CurateDialog 微调
        → 用户确认 → curator.as_nudge/as_quick_action/... → 系统消息"已沉淀并应用"
        → refresh_quick_actions() 刷新快捷指令
```

### 9.8 管理本页记忆

```
用户点 ⋯ → 管理本页记忆…
  → chat.manage_memory_requested()
  → panel._on_manage_memory_requested
    → 校验 page_key 白名单
    → KKLabMemoryManagerDialog(page_key).exec()
      → 列出当前页面 + _shared 全部条目（项目级 docs + 本机私有层合并）
      → 类型筛选 / 右键菜单 / 按钮操作（删除/提升/转快捷指令/导出 eval）
    → 关闭后 refresh_quick_actions()
```

### 9.9 任务调度与异步任务（TaskTray）

```
AI 在回合内调度任务（如 30 分钟后执行某动作）
  → dispatcher 登记到 scheduled_task_registry
  → 面板 _task_tray_timer（1500ms）周期刷新
    → _refresh_task_tray
      → scheduled = service.scheduled_task_registry.list(session_key=sk)
      → pending = service.pending_task_registry.list(session_key=sk)
      → _task_tray.set_tasks(scheduled, pending)
        → 有任务：显示摘要 "▾ ⏱ 待触发 M · ⟳ 进行中 N"
        → 无任务：setVisible(False)

用户在 TaskTray 行内操作：
  → 调度任务 [取消] → _on_task_cancel_requested(task_id)
    → dispatcher.dispatch("cancel_scheduled_task", {"task_id": task_id})
  → 异步任务 [查看结果] → _on_task_view_requested(task_id)
    → dispatcher.dispatch("get_task_result", {"task_id": task_id})
    → chat.add_task_card(task_id, status, text)

异步任务完成：
  → service.task_resumed(info) → _on_task_resumed
    → chat.add_task_card(task_id, "done", text, auto_resume=True)
  → service.task_resume_skipped(info) → _on_task_resume_skipped
    → chat.add_task_card(task_id, "done", text)（降级提示）
  → _refresh_task_tray
  → 若有未回灌任务：首次提示"有 N 个已完成任务（未回灌），可在任务托盘查看结果"
```

### 9.10 切页刷新

```
MainWindow 切页 → _fade_in_widget
  → ai_service.set_page_context(help_key)
  → _update_ai_apply_callbacks
    → 若 Orchestrator 页：set_script_apply_callback + service.set_sequence_data_getter
    → 若 Datalog 页：set_waveform_provider_callback + range_getter + marker_getter
    → 否则：清空上述回调
  → ai_panel.refresh_quick_actions()（按新页面 Profile 重建 Quick Row）
  → ai_panel.on_page_changed()（重置 _unconsumed_hint_shown + _refresh_task_tray）
```

### 9.11 设置对话框

```
用户点 Header 设置按钮 → _open_settings
  → AISettingsDialog(service).exec()
  → 若 Accepted：
    → _populate_models()（重建 Model 下拉项）
    → service.start_telemetry()（应用遥测开关）
```

### 9.12 导出会话

```
用户点 Header 导出按钮 → _on_export_clicked
  → QFileDialog.getSaveFileName（默认名 ai_session_YYYYMMDD_HHMMSS.md）
  → _build_export_markdown() → build_export_markdown(service, transcript, session_started_at, model)
  → 写文件
  → 系统消息"Session debug info exported: {path}"
```

### 9.13 清空会话

```
用户点 Header 清空按钮 → _on_clear_clicked
  → service.clear_history()
  → _transcript.clear()
  → _pending_picked_context = ""
  → _pending_waveform_text = ""
  → _pending_waveform_via_button = False
  → _session_started_at = datetime.now()
  → chat.clear()
  → chat.add_system_message("Conversation history cleared.")
  → _refresh_task_tray()
```

### 9.14 启动回放

```
AIAssistPanel.__init__ 末尾
  → _replay_history()
    → history = service.persisted_history()
    → 逐条 chat.add_user_message / add_ai_message
    → chat.add_system_message("(Restored previous conversation history)")
  → refresh_quick_actions()
  → _wire_service()
  → service.start_telemetry()
  → _task_tray_timer.start(1500)
  → _refresh_task_tray()
```

---

## 10. 配色速查（Slate/Blue 深色体系）

| 用途 | 颜色 |
|---|---|
| 面板 / 对话区 / 底部区背景（deep） | `#070709` |
| Header 背景（最深面） | `#020617` |
| 高亮面 / AI 气泡（elevated） | `#121629` |
| 卡片面 / 下拉 / 数字框背景 | `#0f172a` |
| 通用控件边框（slate-800） | `#1e293b` |
| hover 边框 / 分隔面（slate-700/600） | `#334155` / `#475569` |
| 标题文字（slate-200） | `#e2e8f0` |
| 正文文字（slate-300） | `#cbd5e1` |
| 次要 / 占位文字（slate-400/500） | `#94a3b8` / `#64748b` |
| 用户气泡 | 底 `#18397a` / 字 `#eff6ff` |
| AI 气泡 | 底 `#121629` / 字 `#cbd5e1` / 边框 `#1e293b` |
| 代码块 | 底 `#070709` / 字 `#cbd5e1` / 边框 `#1e293b` |
| Analyze（蓝） | 字 `#3b82f6` / 底 `#0e1b33` / 边框 `#1d2f52` |
| Script（靛 indigo） | 字 `#818cf8` / 底 `#171430` / 边框 `#2a2750` |
| Send（主按钮 blue-600） | 字 `#ffffff` / 底 `#2563eb` / hover `#1d4fd0` |
| 快捷胶囊 | 底 `#0f172a` / 字 `#94a3b8` / 边框 `#1e293b` |
| 输入框聚焦边框 | `#3b82f6` |
| 确认卡片运行按钮 | 绿底 `#16a34a` |
| 确认卡片拒绝按钮 | 红底 `#2a1414` / 红字 `#fca5a5` |
| 确认卡片白名单按钮 | 蓝底 `#0e1b33` / 蓝字 `#3b82f6` |
| 任务卡片自动续跑角标 | 绿底 `#122a1c` / 绿字 `#4ade80` |

---

## 11. 图标资源

位于 `resources/icons_svg/ai/`，统一通过 [icon_utils.py](../../../ui/utils/icon_utils.py) 的 `tinted_svg_icon` / `tinted_svg_pixmap` 染色：

| 文件 | 用途 |
|---|---|
| `ai_panel.svg` | 顶栏 AI 开关按钮 + 面板标题图标 |
| `send.svg` | Send 按钮图标 |
| `sparkles.svg` | Analyze / Script 按钮图标（旧版，现已改用下方独立图标） |
| `inspect.svg` | 拾取按钮图标（绿 `#34d399`） |
| `activity.svg` | 分析按钮图标（蓝 `#3b82f6`） |
| `code.svg` | 草稿按钮图标（靛 `#818cf8`） |
| `clear.svg` | Header 清空按钮图标 |
| `settings.svg` | Header 设置按钮图标 |
| `export.svg` | Header 导出按钮图标 |
| `close.svg` | Header 关闭按钮图标 |

`resources/icons/`（非 ai 子目录）：

| 文件 | 用途 |
|---|---|
| `thumbs-up.svg` | AI 气泡 👍 反馈 |
| `thumbs-down.svg` | AI 气泡 👎 反馈 |
| `more-horizontal.svg` | AI 气泡 ⋯ 沉淀菜单 |

---

## 12. 控件尺寸约定

- 可复用控件统一 `min-height: 22px`（项目"控件高度单一权威"规则，由各自 ID 选择器钉死）；
- 输入框弹性高 80~160（随内容自适应）；
- × 按钮固定宽 28；
- Model 下拉 `minWidth=80`，`Expanding` 策略；
- 面板整体宽度 240~600，默认 360（`outer_splitter` 拖拽，`panel_state.py` 钳制）；
- 用户气泡最大宽度 = 可用宽 × 0.88，`resizeEvent` 与 `QTimer.singleShot(0, ...)` 双重刷新；
- 气泡圆角 16px，尾侧（用户右下 / AI 左下）收为 2px 形成不对称小尾巴；
- 气泡内边距 `12px 16px`；
- 对话区上下间距 24（实现 `spacing=20`）、内边距 16；
- 代码块圆角 12，高度 `min(320, 18*lines+12)`；
- 任务卡 / 确认卡圆角 12。

---

## 13. 关键设计约束

1. **UI 禁阻塞 IO**：所有 AI 请求、波形摘要构建、沉淀草稿生成均走 `QThread` + `Signal/Slot`（`_DigestWorker` / `_DraftWorker` / `_KKDraftWorker`）。
2. **单向数据流**：`TaskTray` 不直接持有 service，由面板按需 `set_tasks` 推入。
3. **会话隔离**：TaskTray 仅展示当前 `session_key` 的任务（`service.current_session_key()`）。
4. **确认卡片同步语义**：`confirm_action` 用局部 `QEventLoop` 阻塞直到用户选择，对 dispatcher 保持同步返回 `ConfirmResult`。
5. **白名单护栏**：仅 `high` 风险动作可写白名单（会话/常驻），`critical` 不可白名单（隐藏白名单按钮）。
6. **波形守卫**：无波形数据时注入 `_NO_WAVEFORM_GUARD`，禁止 AI 编造任何波形读数。
7. **parent 必传**：所有 `QDialog` 构造均 `parent=self`（项目硬红线）。
8. **OK/Cancel 二元化**：所有对话框的 OK/Cancel 按钮 `autoDefault/setDefault` 显式二元化（项目硬红线）。
9. **不写死版本号**：模块版本走 `__init__.py` 的 `MODULE_VERSION`。
10. **图标仅 SVG**：所有图标走 `resources/icons_svg/` + `tinted_svg_icon` 染色，禁 `.ico`（仅打包用）。

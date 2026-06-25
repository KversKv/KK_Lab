# ADR 003 - AI Assist 顶栏与右面板开关方案

- **状态**：Accepted
- **日期**：2026-06-17
- **范围**：`ui/main_window.py`、`ui/app_top_bar.py`（新增）、`ui/ai/ai_panel_button.py`（新增）
- **关联**：[AIAssist_Architecture.md §4.1](../feature_requests/AIAssist/AIAssist_Architecture.md)、[AIAssist_ImplementationPlan.md 阶段 0/1](../feature_requests/AIAssist/AIAssist_ImplementationPlan.md)
- **参考图**：`docs/ai/feature_requests/20260617-161442.jpg`

---

## 背景

AI Assist 需要在主窗口提供一个「右面板开关按钮」+ 竖向分隔栏。参考图的形态为 IDE 风格标题栏：按钮靠右、紧邻系统最小化按钮一侧，与其余区域用竖线隔开。

核查现状（`ui/main_window.py`）：
- `MainWindow` 使用**原生 Windows 标题栏**——无 `setWindowFlags(Qt.FramelessWindowHint)`、无自绘窗口控制按钮；
- 仅个别子模块/弹窗（serialCom_module、toast、sidebar_submenu）局部用 Frameless，与主窗口无关；
- 原生标题栏的最小化按钮由系统绘制，**Qt 无法在其左侧插入控件**。

因此「按钮紧贴系统最小化按钮左侧」的字面效果，必须在两条路中二选一。

## 选项

### 方案 A：应用内顶栏 AppTopBar（低风险）

在 `central_widget` 顶部、`main_splitter` 之上新增一条应用内顶栏 `ui/app_top_bar.py`，靠右放置「竖分隔线 + 右面板开关按钮」。

- 位于原生标题栏**下方一行**，视觉上靠右、贴近最小化按钮一侧，与参考图形态接近；
- 不触碰窗口边框/拖拽/系统按钮，**零兼容风险**；
- `central_widget` 布局改动最小：`main_layout` 顶部 `addWidget(app_top_bar)`，其下仍是原 `main_splitter`。
- 唯一差异：按钮落在原生标题栏下方，而非系统最小化按钮的真正左侧。

### 方案 B：无边框自绘标题栏（100% 还原参考图）

`MainWindow.setWindowFlags(Qt.FramelessWindowHint)` + 自绘 `CustomTitleBar`，在系统最小化按钮真正左侧放分隔线 + 右面板按钮。

- 代价：需自行处理拖拽、Aero Snap、多屏 DPI、最大化边距、双击还原、焦点/激活态等，回归面大；
- 还需统一全应用标题栏配色与现有 QSS 主题，工作量与风险显著更高。

## 决策

**采用方案 A**，第一版（阶段 1）落地应用内顶栏 `AppTopBar`。

方案 B 列入 [AIAssist_ImplementationPlan.md 阶段 5](../feature_requests/AIAssist/AIAssist_ImplementationPlan.md)（体验优化，可选项），不在第一版强推。

## 理由

- 第一版目标是「最小可用 + 不显著改动外观」，方案 A 零兼容风险、改动面最小；
- 右面板开关按钮与开关逻辑（`AIPanelButton.toggled → MainWindow._toggle_ai_panel`）**独立于标题栏实现**，未来切到方案 B 时可平滑迁移，不需要重写面板/开关逻辑；
- 方案 B 的拖拽/Snap/DPI/双击还原等回归风险，不应在 AI 功能首版承担。

## 后果

### 优点
- 第一版 UI 改动可控、可回归；
- 架构对方案 B 保持开放（开关逻辑解耦于标题栏）。

### 代价
- 与参考图存在一处视觉差异：按钮在原生标题栏下方一行，而非系统最小化按钮的真正左侧；
- 若后续坚持 100% 还原参考图，需在阶段 5 另立工作项实现方案 B。

## 待复核触发条件

- 用户明确要求第一版即 100% 还原参考图 → 重新评估是否前置方案 B 到阶段 1。

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

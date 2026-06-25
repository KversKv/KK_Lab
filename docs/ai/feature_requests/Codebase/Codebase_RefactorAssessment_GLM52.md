# 代码体量评估与重构架构建议（Codebase Refactor Assessment · GLM-5.2 版）

> 评估对象：KK_Lab 全量 Python 源码（排除 `.venv` / `build` / `dist` / `.agents` / `.trae` / `MCU_IO` 驱动包）
> 评估日期：2026-06-23
> 评估方：GLM-5.2
> 目的：独立盘点"巨石文件"，给出**该不该拆、拆成什么、按什么架构拆**的结论，并输出**逐文件、逐阶段、带进度看板**的可执行计划。
> 阅读前置：[04_ARCHITECTURE.md](../../04_ARCHITECTURE.md) · [06_PAGE_GUIDE.md](../../06_PAGE_GUIDE.md) · [01_CONVENTIONS.md](../../01_CONVENTIONS.md) · [CLAUDE.md](../../../../CLAUDE.md)
>
> ⚠️ 本文件与同目录 [Codebase_RefactorAssessment.md](./Codebase_RefactorAssessment.md) 互为独立视角；行数以本文件实测为准（已修正原文件的 n6705c_analyser/datalog 行数对调问题）。

---

## 0. 总览数据（量化体检 · 实测）

| 指标 | 数值 |
|---|---|
| Python 文件总数（业务） | ~160 |
| 代码总行数（业务，估） | ~95,000 |
| > 800 行的文件（红区） | 28 个 |
| > 500 行的文件（黄区） | 42 个 |
| > 300 行的文件（关注区） | 60+ 个 |

> 结论：单文件 300 行以内是健康区，500~800 是黄区（需关注），**>800 行进入红区，必须评估拆分**。当前红区集中在 `ui/`，是本次重构主战场。

### 0.1 红区 Top 文件清单（按行数降序 · 实测）

| 行数 | 文件 | 层 | 类数 | 体检结论 |
|---:|---|---|---:|---|
| 8564 | [serialCom_module_frame.py](../../../ui/modules/serialCom_module/serialCom_module_frame.py) | ui/modules | 21 | 🔴 **必拆**（单 `SerialComMixin` 类 6262 行 + 17 个内联控件/对话框 + 3 Worker） |
| 7234 | [n6705c_datalog_ui.py](../../../ui/pages/n6705c_power_analyzer/n6705c_datalog_ui.py) | ui/pages | 12 | 🔴 **必拆**（8 个内联控件 + 3 Worker + 主 UI） |
| 3986 | [consumption_test.py](../../../ui/pages/consumption_test/consumption_test.py) | ui/pages | 6 | 🟠 Worker 已部分外移，UI 仍过大 + 3 个内联 Toggle 控件 |
| 3031 | [oscilloscope_base_ui.py](../../../ui/pages/oscilloscope/oscilloscope_base_ui.py) | ui/pages | — | 🔴 **建议拆**（测量编排/截图/波形处理混装） |
| 2192 | [clk_test_ui.py](../../../ui/pages/pmu_test/clk_test_ui.py) | ui/pages | 3 | 🔴 **建议拆**（`_CLKTestWorker` 870 行含纯算法 + UI 1287 行） |
| 2065 | [n6705c_analyser_ui.py](../../../ui/pages/n6705c_power_analyzer/n6705c_analyser_ui.py) | ui/pages | — | 🟠 关注（内联 `SlideToggle` 等控件） |
| 1998 | [gpadc_test_ui.py](../../../ui/pages/pmu_test/gpadc_test_ui.py) | ui/pages | — | 🔴 同 clk（Worker+算法+UI 混装） |
| 1981 | [pmu_dcdc_efficiency.py](../../../ui/pages/pmu_test/pmu_dcdc_efficiency.py) | ui/pages | — | 🔴 同 clk |
| 1881 | [serialCom_apple_gpt5p5_style.py](../../../ui/modules/serialCom_module/serialCom_apple_gpt5p5_style.py) | ui/modules | — | 🟠 样式常量集中文件（可接受，但应裁剪去重） |
| 1754 | [serialCom_dark_style.py](../../../ui/modules/serialCom_module/serialCom_dark_style.py) | ui/modules | — | 🟠 同上 |
| 1705 | [mcu_io_module_frame.py](../../../ui/modules/mcu_io_module_frame.py) | ui/modules | — | 🟠 关注 |
| 1657 | [ai_assist_panel.py](../../../ui/ai/ai_assist_panel.py) | ui/ai | — | 🟠 关注（已有 chat_view 等子组件可继续拆） |
| 1487 | [pmu_isGain_ui.py](../../../ui/pages/pmu_test/pmu_isGain_ui.py) | ui/pages | — | 🟠 同 clk |
| 1486 | [vmin_hunter_ui.py](../../../ui/pages/vmin_hunter/vmin_hunter_ui.py) | ui/pages | — | 🟠 关注 |
| 1428 | [serial_chart_dialog.py](../../../ui/modules/serialCom_module/serial_chart_dialog.py) | ui/modules | — | 🟠 关注 |
| 1360 | [main_window.py](../../../ui/main_window.py) | ui | — | 🟠 关注（导航 + 连接共享 + ~200 行 Win32 ctypes 污染） |
| 1321 | [pmu_oscp_ui.py](../../../ui/pages/pmu_test/pmu_oscp_ui.py) | ui/pages | — | 🟠 同 clk |
| 1321 | [chamber_control_ui.py](../../../ui/pages/chamber/chamber_control_ui.py) | ui/pages | — | 🟠 关注 |
| 1296 | [iterm_test.py](../../../ui/pages/charger_test/iterm_test.py) | ui/pages | — | 🟠 关注 |
| 1191 | [sequence_canvas.py](../../../ui/pages/custom_test/sequence_canvas.py) | ui/pages | — | 🟠 关注 |
| 1185 | [instrument_nodes.py](../../../core/custom_test/nodes/instrument_nodes.py) | core | — | 🟢 同质节点集合，可接受 |
| 1155 | [ai_service.py](../../../core/ai/ai_service.py) | core/ai | — | 🟢 单一职责，可接受 |
| 1134 | [wt2040_chamber.py](../../../instruments/chambers/wt2040_chamber.py) | instruments | — | 🟢 单驱动，可接受 |

> **勘误**：原 [Codebase_RefactorAssessment.md §0.1](./Codebase_RefactorAssessment.md) 将 `n6705c_analyser_ui.py` 标为 7234 行、`n6705c_datalog_ui.py` 标为 2065 行，实测**两者对调**。本文件已修正。

---

## 1. 当前代码的优点（先肯定）

1. **分层骨架是对的**：`main → ui ↔ core → instruments → lib` 的铁律清晰，且 `instruments/` 已严格无 Qt 依赖；这为后续拆分提供了稳定地基。
2. **核心域已经做了好榜样**，可作为"目标形态"的范本：
   - `core/custom_test/`：document / executor / compiler / nodes / adapters / result_store 各司其职，**这是全工程最干净的子系统**，22 个文件无一个超 1200 行且职责单一。
   - `core/ai/`：providers / algorithms / actions / handlers 分包，职责边界明确，无 QtWidgets。
   - `core/instruments/`：session / manager / registry / workers 分离到位。
3. **部分页面已经开始正确拆分**：
   - `consumption_test/consumption_test_workers/`：把 5 个 QThread Worker 拆出去了（`auto_test_worker` / `chip_check_worker` / `consumption_worker` / `download_worker` / `force_worker`）。
   - `pmu_test/` 各测试项独立成文件，没有挤进一个 god page。
   - `n6705c_power_analyzer/`：`n6705c_top.py`（连接共享）/ `n6705c_analyser_ui.py`（分析页）/ `n6705c_datalog_ui.py`（采集页）已做功能切分。
4. **Mixin 复用连接区域 UI** 的思路是合理的（避免每个页面重复写 VISA/串口搜索+连接+状态指示）。
5. **配置数据外置**：芯片参数走 `chips/*.yaml`，没有把魔法数字写死在业务代码里。
6. **`core/controllers/` 包已预留**（当前空），可直接承接 controller 化的产物，无需新建顶层目录。

---

## 2. 当前代码的缺点（问题诊断）

### 2.1 红区文件 = "UI 类把所有事都干了"（上帝对象）
红区几乎全部落在 `ui/`，根因是 **PySide6 的 `QWidget` 子类被当成了"上帝对象"**，一个类同时承担：
- 视图构建（`_create_layout` / `_build_xxx`，动辄上百行一坨）
- 业务编排（启动/停止/暂停测试流程）
- 数据处理（CSV 解析、频率分析、降采样、统计）
- 后台线程 Worker（`QObject.run`）
- 设备 IO（直接拼 SCPI / 读串口）
- 弹窗对话框、样式 QSS 字符串
- **内联自定义控件**（Toggle / TabBar / CardFrame 等）

以 [serialCom_module_frame.py](../../../ui/modules/serialCom_module/serialCom_module_frame.py)（8564 行）为例：
- 单个 `SerialComMixin` 类从 [L543 到 L6805](../../../ui/modules/serialCom_module/serialCom_module_frame.py#L543)，**一个类 6262 行**，内含至少 8 个独立职责。
- 文件内还塞了 **17 个内联控件/对话框类**（`_SerialSearchButton` / `_FramelessChromeDialog` / `_MixinSerialSettingsDialog` / `_MiniSlideToggle` / `_AddLogPanelDialog` / `_PanelSettingsDialog` / `_IndependentSerialWindow` / `_QuickCmdPreviewPopup` / `_QuickCmdButton` / `_ProjectTabBar` / `_QuickCommandPickerPopup` / `_SerialScriptStepDialog` / `_SerialScriptEditorDialog` / `_QuickTextInputDialog` / `_QuickCmdDialog` / `_SerialSaveDialog` / `_SerialSettingsDialog`）+ **3 个 Worker**（`_SearchSerialPortWorker` / `_NtpSyncWorker` / `_SerialReadWorker`）。

### 2.2 "Worker 与 UI 同住"违反分层
`ui/pages/pmu_test/clk_test_ui.py` 里 `_CLKTestWorker`（[L34-L904](../../../ui/pages/pmu_test/clk_test_ui.py#L34)，约 870 行，含 `_simulate_frequency` / `_read_frequency` / `_run_cap_freq` / `_run_temp_freq` / `_run_clk_perf` 等纯算法/流程）和 `CLKTestUI`（[L905+](../../../ui/pages/pmu_test/clk_test_ui.py#L905)）写在一起。
- 算法/解析本应在 `core/`（无 Qt、可单测），现在被 Qt 文件绑架，**无法脱离 UI 测试**。
- `gpadc_test_ui.py` / `pmu_dcdc_efficiency.py` / `pmu_isGain_ui.py` / `pmu_oscp_ui.py` 同病。

### 2.3 内联自定义控件遍地开花（重复造轮子）
多个红区文件在文件内部定义了本应放 `ui/widgets/` 的通用控件，导致：
- **重复实现**：`SlideToggle`（n6705c_analyser_ui）、`_MiniSlideToggle`（serialCom）、`DownloadModeToggle`/`ControlMethodToggle`/`PolarityToggle`（consumption_test）功能高度重叠。
- **无法复用**：`CardFrame` / `ClickableHeader` / `ChannelConfigTabBar` / `VerticalTextButton`（n6705c_datalog_ui）是通用容器，却被锁死在页面文件里。
- **命名混乱**：同类控件有的带下划线前缀（`_MiniSlideToggle`），有的不带（`SlideToggle`），无统一规范。

### 2.4 视图构建函数过长
`_create_setting_widget` / `_create_layout` 这类方法单个就有 150~500 行，缺乏"小组件工厂"分解，导致：
- 改一个控件要在巨函数里翻找。
- 控件命名/高度/单位规则（项目硬红线）难以审查。

### 2.5 样式字符串散落且重复
`serialCom_apple_gpt5p5_style.py`(1881) / `serialCom_dark_style.py`(1754) 是两套并行皮肤常量；与 `ui/styles/page_styles.py`、`ui/theme.py` 存在概念重叠，缺乏统一的 token/主题中枢。`serialCom_module_frame.py` 顶部还有一段 ~80 行的 `_select_serialcom_style_module` + `_SERIALCOM_STYLE_EXPORTS` 动态加载机制，增加了认知负担。

### 2.6 `main_window.py`(1360) 职责偏多 + Win32 污染
- 文件顶部 [L23-L200](../../../ui/main_window.py#L23) 塞了约 200 行 Win32 `ctypes` 结构体（`_RECT` / `_MONITORINFO` / `_MINMAXINFO`）和常量（`_WM_NCHITTEST` / `_DWMWA_*`），这些是无边框窗口的底层胶水，应抽到 `ui/utils/win32_frameless.py`。
- 导航 + 双 N6705C/示波器/温箱连接状态共享 + Signal 顶层宿主混在一起，"连接状态共享中枢"应下沉到 `core/instruments` 或独立 controller。

### 2.7 `consumption_test.py`(3986) 半成品拆分
Worker 已外移到 `consumption_test_workers/`，但**UI 本体仍是巨石**：页面布局、流程编排、结果表格、温度联动都还挤在一个文件里，且文件内还残留 2 个 Worker（`_SearchMcuPortWorker` / `_ConnectMcuWorker`）和 3 个 Toggle 控件未外移。

### 2.8 `tests/` 目录失序
`tests/` 下有 15+ 个 `_tmp.py` 临时脚本（`_plot_tmp.py` / `_swed_tmp.py` / `_verify_ai_fix_tmp.py` …）和散落的 `.csv` / `.dlog` / `.png` / `.svg` 数据文件，没有 `__init__.py`，没有 `conftest.py`，**重构期缺乏可回归的安全网**。

---

## 3. 哪些代码应该分离（优先级清单）

> 原则：**先动收益最大、风险可控的；先拆"非 Qt 可单测的逻辑"与"可复用控件"，再拆"视图"**。

### P0（必拆，单文件已失控）
| 文件 | 拆出什么 | 去向 |
|---|---|---|
| serialCom_module_frame.py (8564) | 见 §4.1 专项方案 | 拆为 `serialCom_module/` 子包：mixins/ + widgets/ + workers/ + styles/ |
| n6705c_datalog_ui.py (7234) | 8 个内联控件→`ui/widgets/`；3 Worker→`core/`；UI 拆 view 构建子模块 | widgets 复用 + Worker 下沉 + UI 瘦身 |

### P1（强烈建议，逻辑与 UI 耦合）
| 文件 | 拆出什么 | 去向 |
|---|---|---|
| clk_test_ui.py (2192) | `_CLKTestWorker` + 全部频率分析/模拟 | `core/pmu_test/clk/`，UI 只留视图+信号订阅 |
| gpadc_test_ui.py (1998) | Worker + 数据处理 | `core/pmu_test/gpadc/` |
| pmu_dcdc_efficiency.py (1981) | Worker + 效率计算 | `core/pmu_test/dcdc/` |
| pmu_isGain_ui.py (1487) / pmu_oscp_ui.py (1321) | Worker + 算法 | `core/pmu_test/isgain/` / `core/pmu_test/oscp/` |
| oscilloscope_base_ui.py (3031) | 测量编排 / 截图 / 波形处理 | controller 化到 `core/controllers/oscilloscope_controller.py` |

### P2（关注，逐步优化）
| 文件 | 动作 |
|---|---|
| consumption_test.py (3986) | 继续按 §4.2 把 UI 本体拆成 view + 流程控制器；残留 Worker/Toggle 外移 |
| n6705c_analyser_ui.py (2065) | 内联 `SlideToggle` 等控件→`ui/widgets/` |
| ai_assist_panel.py (1657) | 拆 panel 子组件（已有 chat_view 等可继续） |
| main_window.py (1360) | Win32 ctypes→`ui/utils/win32_frameless.py`；"连接共享中枢"抽出 |
| serialCom_*_style.py | 合入统一主题 token，去重 |
| mcu_io_module_frame.py (1705) | 参照 serialCom 套路拆 mixins |
| tests/ 目录 | 清理 `_tmp.py`，建 `conftest.py` + `tests/refactor/` |

### 不需要拆（保持现状）
- `core/custom_test/nodes/instrument_nodes.py`、`core/ai/ai_service.py`、各仪器单驱动（`wt2040_chamber.py` 等）：虽长但**单一职责、同质内容**，拆了反而增加跳转成本。**长度不是唯一标准，职责数量才是。**

---

## 4. 最佳架构建议

### 4.0 核心原则：把"巨石 QWidget"拆成 MVC/MVP 三角
对每个红区页面，统一切成三类文件（包内分文件，而非一个文件）：

```
ui/pages/<feature>/
  ├─ <feature>_ui.py        # View：只负责控件树、布局、样式应用、信号连线（瘦）
  ├─ <feature>_view_*.py    # View 子构建器（可选）：按区块拆 _build_xxx
  ├─ <feature>_widgets.py   # 该页面专属自定义控件（若无法通用）
  └─ workers/ → 迁出到 core/

core/<feature>/             # 业务+算法+Worker（无 QtWidgets，可单测）
  ├─ __init__.py            # 导出公共 API + MODULE_VERSION
  ├─ <feature>_controller.py  # 流程编排：start/stop/pause，发 Signal
  ├─ <feature>_worker.py      # QThread/QObject Worker（仅 QtCore，无 QtWidgets）
  └─ <feature>_analysis.py    # 纯算法/解析（无任何 Qt，pytest 可直测）

ui/widgets/                 # 跨页面复用的通用控件（单一权威来源）
  ├─ toggle.py              # SlideToggle / MiniSlideToggle 统一实现
  ├─ card_frame.py          # CardFrame / ClickableHeader
  ├─ tab_bar.py             # ChannelConfigTabBar / ProjectTabBar
  └─ ...
```

**判定红线**：
- 凡是 `_parse_*` / `_analyze_*` / `*_from_csv` / 统计/降采样/模拟 → 必须无 Qt，放 `core/.../*_analysis.py`。
- 凡是 `QObject` + `run()` 的 Worker → 放 `core/.../*_worker.py`（只依赖 QtCore）。
- 凡是 `_build_*` / `_create_*` 视图构建 → 留 `ui/`，但单个方法 > ~80 行就抽小工厂函数。
- 凡是被 ≥2 个页面使用的控件 → 必须落 `ui/widgets/`，页面内不得重复定义。
- View 不直接发 SCPI / 读串口，一律经 controller → factory（沿用现有铁律）。

### 4.1 专项：serialCom_module_frame.py 拆解蓝图
当前已有 `serial_session*.py` / `serial_chart_*.py`，应把 `SerialComMixin` 巨类按职责切成多个 Mixin/组件并组合：

```
ui/modules/serialCom_module/
  ├─ serialCom_module_frame.py   # 仅保留 SerialComMixin 的"装配"与对外 API（瘦壳，目标 < 500 行）
  ├─ mixins/
  │   ├─ __init__.py
  │   ├─ connection_mixin.py     # 搜索/连接/断开/状态（init_serial_connection 等）
  │   ├─ toolbar_mixin.py        # _build_sc_toolbar / sidebar / status_bar
  │   ├─ log_panel_mixin.py      # 日志区 + 多面板管理 + 焦点/右键菜单
  │   ├─ filter_save_mixin.py    # 过滤、高亮、保存/导出
  │   ├─ send_mixin.py           # 发送区 + quick commands
  │   ├─ chart_mixin.py          # 串口绘图接入（已有 serial_chart_* 复用）
  │   └─ script_mixin.py         # 脚本序列表格 UI 渲染
  ├─ widgets/                    # _SerialSearchButton / _FramelessChromeDialog / _MiniSlideToggle / _QuickCmd* 等
  │   └─ __init__.py
  ├─ dialogs/                    # _MixinSerialSettingsDialog / _AddLogPanelDialog / _PanelSettingsDialog / _SerialScriptEditorDialog / _SerialSaveDialog / _SerialSettingsDialog
  │   └─ __init__.py
  ├─ workers/                    # _SearchSerialPortWorker / _NtpSyncWorker / _SerialReadWorker
  │   └─ __init__.py
  ├─ styles/                     # 两套皮肤合并为 token + 主题切换
  │   └─ __init__.py
  └─ serial_session*.py          # 维持现状
```
> 脚本执行引擎（`_sc_script_*` 一大坨）逻辑部分应进一步下沉 `core/serialcom/script_engine.py`，UI 仅做表格渲染与按钮。

### 4.2 专项：n6705c_datalog_ui.py 拆解蓝图
```
ui/pages/n6705c_power_analyzer/
  ├─ n6705c_datalog_ui.py        # 仅保留 N6705CDatalogUI 视图装配（目标 < 800 行）
  ├─ n6705c_datalog_views/       # 视图子构建器
  │   ├─ __init__.py
  │   ├─ channel_tab_view.py     # 通道配置 Tab 区
  │   ├─ scan_view.py            # 扫描/连接区
  │   └─ datalog_toolbar_view.py # 工具栏
  └─ (控件外移到 ui/widgets/)

core/n6705c_datalog/             # Worker + 数据处理（无 QtWidgets）
  ├─ __init__.py
  ├─ datalog_worker.py           # _DatalogWorker（仅 QtCore）
  ├─ scan_worker.py              # _ScanWorker / _ConnectWorker
  └─ datalog_analysis.py         # 采集数据处理/导出（若有纯函数）

ui/widgets/                      # 从 datalog_ui 内联迁出的通用控件
  ├─ toggle_label.py             # ToggleLabel
  ├─ scale_offset_edit.py        # ScaleOffsetEdit
  ├─ channel_name_label.py       # ChannelNameLabel
  ├─ card_frame.py               # CardFrame + ClickableHeader
  ├─ vertical_text_button.py     # VerticalTextButton
  ├─ channel_tab_bar.py          # ChannelConfigTabBar
  └─ fixed_popup_combobox.py     # FixedPopupComboBox
```

### 4.3 专项：consumption_test 收尾
- 已有 `consumption_test_workers/`（保持）。
- 文件内残留 `_SearchMcuPortWorker` / `_ConnectMcuWorker` → 并入 `consumption_test_workers/`。
- 文件内 `DownloadModeToggle` / `ControlMethodToggle` / `PolarityToggle` → 合并到 `ui/widgets/toggle.py` 统一实现。
- 新增 `core/consumption_test/consumption_controller.py` 承接现 UI 内的流程编排。
- `consumption_test.py` 仅保留视图与信号订阅，目标 < 1000 行。

### 4.4 专项：main_window.py 瘦身
```
ui/
  ├─ main_window.py              # 仅保留导航 + 页面装配（目标 < 800 行）
  ├─ utils/
  │   └─ win32_frameless.py      # 🆕 抽出 ~200 行 Win32 ctypes 结构体 + 常量
  └─ ...
core/instruments/
  └─ connection_hub.py           # 🆕 "连接共享中枢"：N6705C A/B / 示波器 / 温箱连接状态集中管理
```

### 4.5 目标分层依赖（强化版）
沿用 [04_ARCHITECTURE §2](../../04_ARCHITECTURE.md) 铁律，**额外补两条**：
> 1. `ui/` 中**禁止**出现纯数据解析/算法/统计函数；此类一律落 `core/`。Worker 可留在 `ui→core` 之间，但只依赖 `QtCore`，不得 import `QtWidgets`。
> 2. `ui/pages/` 与 `ui/modules/` 中**禁止**定义被 ≥2 个文件使用的自定义控件；此类一律落 `ui/widgets/`。

### 4.6 渐进式落地路线（不大爆炸重构）
1. **织安全网**：先建 `tests/refactor/` + smoke import 测试 + 行数基线。
2. **抽通用控件**：把内联 Toggle/CardFrame/TabBar 等平移到 `ui/widgets/`（纯搬运，高复用收益）。
3. **抽算法**：把 P1 页面的 `_parse_*/_analyze_*` 平移到 `core/.../*_analysis.py`，补 pytest（零行为变更，最安全）。
4. **抽 Worker**：把 `QObject` Worker 迁 `core/.../*_worker.py`，UI 改 import。
5. **抽 Controller**：把 start/stop/pause 编排收敛到 controller，UI 只连 Signal。
6. **拆视图**：最后才拆 `_build_*` 视图构建（纯搬运，影响面最大放最后）。
7. 每步后跑 `python main.py` 冒烟 + lint，**一次只动一个文件家族**。

---

## 5. 一句话结论
- **优点**：分层骨架正确，`core/custom_test`、`core/ai`、`core/instruments` 已是干净范本，`core/controllers/` 包已预留。
- **缺点**：`ui/` 把"视图+编排+算法+Worker+IO+内联控件"全塞进 QWidget，产出 28 个红区巨石；`serialCom_module_frame.py` 单类 6262 行是全工程最大债务。
- **该拆的**：P0 两个（serialCom 8564 / n6705c_datalog 7234）必拆；P1 的 pmu_test/oscilloscope 把算法与 Worker 下沉 `core/`；内联通用控件统一收口 `ui/widgets/`。
- **最佳架构**：以 `core/custom_test` 为样板，对每个红区页面做 **View(ui) / Controller+Worker+Analysis(core)** 三层切分，按"安全网→控件→算法→Worker→controller→视图"的顺序渐进重构。

---

# 第二部分：完整更改计划（Change Plan）

> 本部分给出**逐文件、逐阶段、可执行**的重构计划。每个阶段独立可交付、可回滚，结束后必须满足"验收口径"才进入下一阶段。
> 通用约束（每阶段都适用）：
> - 沿用铁律：`ui/` 不出现纯算法/解析；Worker 仅依赖 `QtCore`；设备 IO 一律经 `factory`。
> - **不改行为**，只搬运/拆分；搬运后旧入口用 re-export 兼容，避免一次性改全部 import。
> - 每阶段收尾：`python main.py` 冒烟 + `lint` + 相关 pytest 全绿；同步 `DIRECTORY_STRUCTURE.txt`。
> - 严禁 `git commit`（由人工把关里程碑）。
> - 中文简体；不增删业务注释；不新建多余 `*.md`（本评估文件除外）。

## 6. 图例与符号

| 符号 | 含义 |
|---|---|
| 🆕 | 新建文件 |
| ✂️ | 拆出内容（源文件瘦身） |
| ♻️ | 修改（改 import / 改装配 / 加 re-export） |
| 🧪 | 新增/补充测试 |
| 🗂️ | 同步类文档（结构表/spec/help） |
| 🧹 | 清理（删除临时文件/死代码） |

**进度看板状态图例**：⬜ 未开始 · 🟦 进行中 · ✅ 已完成 · ⛔ 受阻 · 🔁 返工

---

## 7. 全局进度看板（Master Kanban）

> 单一事实源：每完成一个 Phase 就更新本表与该 Phase 内的子看板；负责人/日期由执行者填写。

| Phase | 名称 | 目标文件 | 主要产出 | 风险 | 依赖 | 状态 | 进度 | 负责人 | 完成日期 |
|---|---|---|---|---|---|---|---|---|---|
| **Phase 0** | 安全网 + 基线 | 全局 | `tests/refactor/` + smoke 测试 + 行数基线 + 清理 `_tmp.py` | 低 | 无 | ⬜ | 0% | — | — |
| **Phase 1** | 通用控件收口 | serialCom / n6705c_datalog / consumption / n6705c_analyser | `ui/widgets/` 统一 Toggle/CardFrame/TabBar | 中 | Phase 0 | ⬜ | 0% | — | — |
| **Phase 2** | PMU 算法/Worker 下沉 | clk / gpadc / dcdc / isGain / oscp | `core/pmu_test/*` analysis+worker | 中 | Phase 0 | ⬜ | 0% | — | — |
| **Phase 3** | 示波器 controller 化 | oscilloscope_base_ui | `core/controllers/oscilloscope_controller.py` | 中 | Phase 0 | ⬜ | 0% | — | — |
| **Phase 4** | n6705c_datalog 拆分（P0） | n6705c_datalog_ui | Worker→core，widgets/view 分文件 | 高 | Phase 1 | ⬜ | 0% | — | — |
| **Phase 5** | serialCom 巨石拆分（P0） | serialCom_module_frame | mixins/ + widgets/ + dialogs/ + workers/ + 脚本引擎下沉 | 高 | Phase 1 | ⬜ | 0% | — | — |
| **Phase 6** | consumption_test 收尾 | consumption_test | controller + 残留 Worker/Toggle 外移 | 中 | Phase 1, Phase 4 | ⬜ | 0% | — | — |
| **Phase 7** | main_window 瘦身 + 样式统一 + 收尾 | main_window / serialCom_*_style / ai_panel / mcu_io | Win32 抽出 + 连接中枢 + 皮肤 token 合并 | 中 | Phase 5, Phase 6 | ⬜ | 0% | — | — |

**整体进度**：0 / 8 Phase 完成（0%）

> 注：Phase 1 / Phase 2 / Phase 3 之间**无强依赖**，可并行；Phase 4、Phase 5 必须在 Phase 1 之后（依赖通用控件就位）；Phase 6 依赖 Phase 4 的 datalog 接口稳定；Phase 7 是收尾，依赖 Phase 5/6。

---

## 8. 各阶段详细文件清单（含进度看板）

### Phase 0 — 安全网与基线（前置）

**目标**：不动业务代码，先织好回归安全网，记录基线，清理测试目录。

**进度看板**

| # | 任务 | 状态 | 备注 |
|---|---|---|---|
| 0-1 | 🧹 清理 `tests/_*.py` 临时脚本与散落数据文件 | ⬜ | 移到 `tests/scratch/` 或删除 |
| 0-2 | 🆕 建 `tests/__init__.py` + `tests/conftest.py` | ⬜ | pytest 可发现 |
| 0-3 | 🆕 建 `tests/refactor/__init__.py` | ⬜ | 重构期测试目录 |
| 0-4 | 🧪🆕 建 `tests/refactor/test_smoke_import.py` | ⬜ | 遍历 import 所有页面/模块不报错 |
| 0-5 | 🧪🆕 建 `tests/refactor/test_no_qt_in_core_analysis.py` | ⬜ | 占位：后续校验 core 下 analysis 不 import QtWidgets |
| 0-6 | 🗂️ 记录行数基线到 `.ai/memory.md` | ⬜ | 28 个红区快照 |
| 0-7 | 验收：`python main.py` 冒烟 + `pytest tests/refactor/` 绿 | ⬜ | 退出 Phase 门禁 |

| 动作 | 文件 | 说明 |
|---|---|---|
| 🧹 | `tests/_*.py`（15+ 个） | 归档到 `tests/scratch/` 或删除 |
| 🧪🆕 | `tests/__init__.py` | 包标识 |
| 🧪🆕 | `tests/conftest.py` | pytest 配置 + 公共 fixture |
| 🧪🆕 | `tests/refactor/__init__.py` | 重构期测试包 |
| 🧪🆕 | `tests/refactor/test_smoke_import.py` | 遍历 import 所有 `ui.pages.*` / `ui.modules.*`，确保拆分后不破导入 |
| 🧪🆕 | `tests/refactor/test_no_qt_in_core_analysis.py` | 占位测试，后续 Phase 2 填充断言 |
| 🗂️ | `.ai/memory.md` | 记录"重构进行中"上下文与基线行数 |

---

### Phase 1 — 通用控件收口（P1，高复用收益）

**目标**：把散落在红区文件内的通用自定义控件统一迁到 `ui/widgets/`，消除重复实现，为后续 Phase 4/5/6 拆视图铺路。

**进度看板**

| # | 子任务 | 状态 | 备注 |
|---|---|---|---|
| 1-1 | 🆕 `ui/widgets/toggle.py` 统一 SlideToggle/MiniSlideToggle/Toggle 三件套 | ⬜ | 合并 n6705c_analyser 的 `SlideToggle` + serialCom 的 `_MiniSlideToggle` + consumption 的 3 个 Toggle |
| 1-2 | 🆕 `ui/widgets/card_frame.py`（CardFrame + ClickableHeader） | ⬜ | 从 n6705c_datalog 迁出 |
| 1-3 | 🆕 `ui/widgets/tab_bar.py`（ChannelConfigTabBar + ProjectTabBar） | ⬜ | 从 n6705c_datalog + serialCom 迁出 |
| 1-4 | 🆕 `ui/widgets/vertical_text_button.py` | ⬜ | 从 n6705c_datalog 迁出 |
| 1-5 | 🆕 `ui/widgets/toggle_label.py` + `scale_offset_edit.py` + `channel_name_label.py` + `fixed_popup_combobox.py` | ⬜ | 从 n6705c_datalog 迁出 |
| 1-6 | ♻️ 各源文件改 import + 旧类名 re-export 兼容 | ⬜ | 不破外部引用 |
| 1-7 | 验收：`python main.py` 冒烟 + 控件视觉无变化 | ⬜ | 退出 Phase 门禁 |

| 动作 | 文件 | 内容 |
|---|---|---|
| 🆕✂️ | `ui/widgets/toggle.py` | 统一 `SlideToggle`（含 accent_color/off_bg/off_border/knob_color 可配），消费方传参差异化 |
| 🆕✂️ | `ui/widgets/card_frame.py` | `CardFrame` + `ClickableHeader` |
| 🆕✂️ | `ui/widgets/tab_bar.py` | `ChannelConfigTabBar` + `ProjectTabBar`（若差异大则分文件） |
| 🆕✂️ | `ui/widgets/vertical_text_button.py` | `VerticalTextButton` |
| 🆕✂️ | `ui/widgets/toggle_label.py` | `ToggleLabel` |
| 🆕✂️ | `ui/widgets/scale_offset_edit.py` | `ScaleOffsetEdit` |
| 🆕✂️ | `ui/widgets/channel_name_label.py` | `ChannelNameLabel` |
| 🆕✂️ | `ui/widgets/fixed_popup_combobox.py` | `FixedPopupComboBox` |
| ♻️✂️ | [n6705c_datalog_ui.py](../../../ui/pages/n6705c_power_analyzer/n6705c_datalog_ui.py) | 删除 8 个内联控件类，改 `from ui.widgets.* import`；旧名 re-export |
| ♻️✂️ | [n6705c_analyser_ui.py](../../../ui/pages/n6705c_power_analyzer/n6705c_analyser_ui.py) | 删除 `SlideToggle`，改 import |
| ♻️✂️ | [serialCom_module_frame.py](../../../ui/modules/serialCom_module/serialCom_module_frame.py) | 删除 `_MiniSlideToggle` / `_ProjectTabBar`，改 import |
| ♻️✂️ | [consumption_test.py](../../../ui/pages/consumption_test/consumption_test.py) | 删除 3 个 Toggle，改 import |
| 🧪🆕 | `tests/refactor/test_widgets_import.py` | 校验 `ui.widgets.*` 可独立 import 且无业务依赖 |

**验收**：4 个源文件合计瘦身 ~600 行；`ui/widgets/` 新增 8 个文件；冒烟通过；控件外观无变化。

---

### Phase 2 — PMU 算法/Worker 下沉（P1）

**目标**：把 5 个 PMU 测试页里的 Worker 与纯算法搬到 `core/pmu_test/`，UI 仅保留视图 + 信号订阅。以 clk 为样板，其余四个复制套路。

**进度看板**

| # | 子任务 | 状态 | 备注 |
|---|---|---|---|
| 2-1 | clk 样板：analysis + worker 下沉 | ⬜ | 建立可复制模式 |
| 2-2 | gpadc 套用 | ⬜ | — |
| 2-3 | dcdc 套用 | ⬜ | — |
| 2-4 | isGain 套用 | ⬜ | — |
| 2-5 | oscp 套用 | ⬜ | — |
| 2-6 | 启用 `test_no_qt_in_core_analysis.py` 断言 | ⬜ | 校验 core/pmu_test 下无 QtWidgets |
| 2-7 | 验收：5 页行为不变 + analysis 单测绿 | ⬜ | 退出 Phase 门禁 |

#### Phase 2.1 clk（样板）
| 动作 | 文件 | 内容 |
|---|---|---|
| 🆕 | `core/pmu_test/__init__.py` | 包初始化 + `MODULE_VERSION = "0.0.0"` |
| 🆕 | `core/pmu_test/clk/__init__.py` | 导出 `ClkTestWorker` + analysis 公共函数 |
| 🆕✂️ | `core/pmu_test/clk/clk_analysis.py` | 搬 `_simulate_frequency` / `_read_frequency` 中的纯计算 / CSV 解析 / 频率分析（**纯函数，无 Qt**） |
| 🆕✂️ | `core/pmu_test/clk/clk_worker.py` | 搬 `_CLKTestWorker`（仅 `QtCore`），内部调用 `clk_analysis` |
| ♻️✂️ | [clk_test_ui.py](../../../ui/pages/pmu_test/clk_test_ui.py) | 删除已搬代码，改 `from core.pmu_test.clk import ClkTestWorker`；`CLKTestUI` 仅保留视图/信号 |
| 🧪🆕 | `tests/refactor/test_clk_analysis.py` | 针对 CSV 解析与频率分析的纯函数单测 |

#### Phase 2.2~2.5 其余四页（同套路）
| 动作 | 文件 | 拆出去向 |
|---|---|---|
| 🆕✂️♻️ | [gpadc_test_ui.py](../../../ui/pages/pmu_test/gpadc_test_ui.py) | `core/pmu_test/gpadc/{__init__.py, gpadc_analysis.py, gpadc_worker.py}` |
| 🆕✂️♻️ | [pmu_dcdc_efficiency.py](../../../ui/pages/pmu_test/pmu_dcdc_efficiency.py) | `core/pmu_test/dcdc/{__init__.py, dcdc_analysis.py, dcdc_worker.py}` |
| 🆕✂️♻️ | [pmu_isGain_ui.py](../../../ui/pages/pmu_test/pmu_isGain_ui.py) | `core/pmu_test/isgain/{__init__.py, isgain_analysis.py, isgain_worker.py}` |
| 🆕✂️♻️ | [pmu_oscp_ui.py](../../../ui/pages/pmu_test/pmu_oscp_ui.py) | `core/pmu_test/oscp/{__init__.py, oscp_analysis.py, oscp_worker.py}` |
| 🧪🆕 | `tests/refactor/test_pmu_analysis.py` | 四页算法纯函数单测 |

**验收**：5 个页面 UI 行为不变；`core/pmu_test/*/` 下 analysis 全部 `import` 无 Qt（`test_no_qt_in_core_analysis.py` 绿）。

---

### Phase 3 — 示波器 controller 化（P1）

**目标**：把 `oscilloscope_base_ui.py`(3031) 里的测量编排/截图/波形后处理下沉到 `core/controllers/`，UI 只留视图 + 信号订阅。

**进度看板**

| # | 任务 | 状态 | 备注 |
|---|---|---|---|
| 3-1 | 🆕 `core/controllers/oscilloscope_controller.py` 搬测量/截图/波形后处理 | ⬜ | 经 factory 取仪器 |
| 3-2 | ♻️ UI 改调用 controller + 抽小工厂 | ⬜ | `_build_*` 过长方法分解 |
| 3-3 | 🧪 controller mock 单测 | ⬜ | — |
| 3-4 | 验收：示波器页测量/截图正常 | ⬜ | 退出 Phase 门禁 |

| 动作 | 文件 | 内容 |
|---|---|---|
| 🆕✂️ | `core/controllers/oscilloscope_controller.py` | 搬测量编排 / 截图 / 波形后处理（粗粒度操作，经 factory 取仪器） |
| ♻️ | `core/controllers/__init__.py` | 导出 `OscilloscopeController` |
| ♻️✂️ | [oscilloscope_base_ui.py](../../../ui/pages/oscilloscope/oscilloscope_base_ui.py) | 改调用 controller；视图过长的 `_build_*` 抽小工厂函数到 `oscilloscope_views/` |
| 🆕 | `ui/pages/oscilloscope/oscilloscope_views/__init__.py` | 视图子构建器包 |
| 🧪🆕 | `tests/refactor/test_oscilloscope_controller.py` | controller mock 单测 |

---

### Phase 4 — n6705c_datalog 拆分（P0）

**目标**：把 7234 行的 `n6705c_datalog_ui.py` 拆成 view + workers + 复用控件（控件已在 Phase 1 迁出）。目标主文件 < 800 行。

**进度看板**

| # | 子任务 | 状态 | 备注 |
|---|---|---|---|
| 4-1 | 🆕 `core/n6705c_datalog/` 包：3 Worker 下沉 | ⬜ | `_ScanWorker`/`_ConnectWorker`/`_DatalogWorker` |
| 4-2 | 🆕 `ui/pages/n6705c_power_analyzer/n6705c_datalog_views/` 视图子构建器 | ⬜ | 按 channel_tab/scan/toolbar 分文件 |
| 4-3 | ♻️ 主文件改 import + 装配 | ⬜ | 仅保留 N6705CDatalogUI 视图壳 |
| 4-4 | 🧪 Worker 单测（mock） | ⬜ | — |
| 4-5 | 验收：datalog 采集/扫描/连接行为不变 | ⬜ | 退出 Phase 门禁 |

| 动作 | 文件 | 内容 |
|---|---|---|
| 🆕 | `core/n6705c_datalog/__init__.py` | 导出 3 Worker + `MODULE_VERSION` |
| 🆕✂️ | `core/n6705c_datalog/scan_worker.py` | 搬 `_ScanWorker` + `_ConnectWorker`（仅 QtCore） |
| 🆕✂️ | `core/n6705c_datalog/datalog_worker.py` | 搬 `_DatalogWorker`（仅 QtCore） |
| 🆕✂️ | `core/n6705c_datalog/datalog_analysis.py` | 若有纯数据处理/导出函数，搬此（无 Qt） |
| 🆕 | `ui/pages/n6705c_power_analyzer/n6705c_datalog_views/__init__.py` | 视图子构建器包 |
| 🆕✂️ | `n6705c_datalog_views/channel_tab_view.py` | 搬通道配置 Tab 区构建逻辑 |
| 🆕✂️ | `n6705c_datalog_views/scan_view.py` | 搬扫描/连接区构建逻辑 |
| 🆕✂️ | `n6705c_datalog_views/datalog_toolbar_view.py` | 搬工具栏构建逻辑 |
| ♻️✂️ | [n6705c_datalog_ui.py](../../../ui/pages/n6705c_power_analyzer/n6705c_datalog_ui.py) | 删除 Worker + 视图构建代码，改 import；仅保留 `N6705CDatalogUI` 装配与信号订阅 |
| 🧪🆕 | `tests/refactor/test_n6705c_datalog_worker.py` | Worker mock 单测 |

**验收**：主文件 7234 → < 800 行；3 Worker 在 `core/` 可单测；采集行为不变。

---

### Phase 5 — serialCom 巨石拆分（P0）

**目标**：把 8564 行的 `serialCom_module_frame.py`（含 6262 行的 `SerialComMixin`）拆成 mixins/ + widgets/ + dialogs/ + workers/ + styles/。目标主文件 < 500 行。

**进度看板**

| # | 子任务 | 状态 | 备注 |
|---|---|---|---|
| 5-1 | 🆕 `workers/`：3 Worker 下沉 | ⬜ | `_SearchSerialPortWorker`/`_NtpSyncWorker`/`_SerialReadWorker` |
| 5-2 | 🆕 `widgets/`：内联控件迁出（Phase 1 已迁 Toggle/TabBar，此处迁剩余） | ⬜ | `_SerialSearchButton`/`_QuickCmd*`/`_QuickCommandPickerPopup` 等 |
| 5-3 | 🆕 `dialogs/`：8 个对话框迁出 | ⬜ | `_MixinSerialSettingsDialog`/`_AddLogPanelDialog`/`_PanelSettingsDialog`/`_SerialScriptEditorDialog`/`_SerialSaveDialog`/`_SerialSettingsDialog`/`_SerialScriptStepDialog`/`_QuickCmdDialog`/`_QuickTextInputDialog` |
| 5-4 | 🆕 `mixins/`：SerialComMixin 按 7 职责拆分 | ⬜ | connection/toolbar/log_panel/filter_save/send/chart/script |
| 5-5 | 🆕 `core/serialcom/script_engine.py`：脚本执行引擎下沉 | ⬜ | `_sc_script_*` 逻辑部分 |
| 5-6 | ♻️ 主文件改装配 + re-export 兼容 | ⬜ | `SerialComMixin` 变成组合壳 |
| 5-7 | 🧪 各 mixin/worker 单测 | ⬜ | — |
| 5-8 | 验收：串口模块全功能不变（连接/收发/绘图/脚本/多面板） | ⬜ | 退出 Phase 门禁 |

| 动作 | 文件 | 内容 |
|---|---|---|
| 🆕 | `ui/modules/serialCom_module/workers/__init__.py` | Worker 包 |
| 🆕✂️ | `workers/search_port_worker.py` | 搬 `_SearchSerialPortWorker` |
| 🆕✂️ | `workers/ntp_sync_worker.py` | 搬 `_NtpSyncWorker` |
| 🆕✂️ | `workers/serial_read_worker.py` | 搬 `_SerialReadWorker` |
| 🆕 | `ui/modules/serialCom_module/widgets/__init__.py` | 控件包 |
| 🆕✂️ | `widgets/serial_search_button.py` | 搬 `_SerialSearchButton` |
| 🆕✂️ | `widgets/quick_cmd_button.py` | 搬 `_QuickCmdButton` + `_QuickCmdPreviewPopup` |
| 🆕✂️ | `widgets/quick_command_picker.py` | 搬 `_QuickCommandPickerPopup` |
| 🆕 | `ui/modules/serialCom_module/dialogs/__init__.py` | 对话框包 |
| 🆕✂️ | `dialogs/frameless_chrome_dialog.py` | 搬 `_FramelessChromeDialog`（基类） |
| 🆕✂️ | `dialogs/serial_settings_dialog.py` | 搬 `_MixinSerialSettingsDialog` + `_SerialSettingsDialog` |
| 🆕✂️ | `dialogs/log_panel_dialog.py` | 搬 `_AddLogPanelDialog` + `_PanelSettingsDialog` |
| 🆕✂️ | `dialogs/script_editor_dialog.py` | 搬 `_SerialScriptEditorDialog` + `_SerialScriptStepDialog` |
| 🆕✂️ | `dialogs/quick_cmd_dialog.py` | 搬 `_QuickCmdDialog` + `_QuickTextInputDialog` |
| 🆕✂️ | `dialogs/serial_save_dialog.py` | 搬 `_SerialSaveDialog` |
| 🆕 | `ui/modules/serialCom_module/mixins/__init__.py` | Mixin 包 |
| 🆕✂️ | `mixins/connection_mixin.py` | 搜索/连接/断开/状态 |
| 🆕✂️ | `mixins/toolbar_mixin.py` | `_build_sc_toolbar` / sidebar / status_bar |
| 🆕✂️ | `mixins/log_panel_mixin.py` | 日志区 + 多面板管理 + 焦点/右键菜单 |
| 🆕✂️ | `mixins/filter_save_mixin.py` | 过滤、高亮、保存/导出 |
| 🆕✂️ | `mixins/send_mixin.py` | 发送区 + quick commands |
| 🆕✂️ | `mixins/chart_mixin.py` | 串口绘图接入（复用 serial_chart_*） |
| 🆕✂️ | `mixins/script_mixin.py` | 脚本序列表格 UI 渲染 |
| 🆕✂️ | `core/serialcom/__init__.py` | 脚本引擎包 |
| 🆕✂️ | `core/serialcom/script_engine.py` | 搬 `_sc_script_*` 执行逻辑（无 QtWidgets） |
| ♻️✂️ | [serialCom_module_frame.py](../../../ui/modules/serialCom_module/serialCom_module_frame.py) | `SerialComMixin` 变为组合 7 个 mixin 的瘦壳；保留对外 API 与 re-export |
| 🧪🆕 | `tests/refactor/test_serialcom_mixins.py` | 各 mixin import + 基本行为 |
| 🧪🆕 | `tests/refactor/test_serialcom_script_engine.py` | 脚本引擎纯逻辑单测 |

**验收**：主文件 8564 → < 500 行；`SerialComMixin` 对外 API 不变；串口模块全功能冒烟通过。

---

### Phase 6 — consumption_test 收尾

**目标**：把 3986 行的 `consumption_test.py` 收尾——残留 Worker 并入 workers/、Toggle 已在 Phase 1 迁出、新增 controller 承接流程编排。目标主文件 < 1000 行。

**进度看板**

| # | 子任务 | 状态 | 备注 |
|---|---|---|---|
| 6-1 | ♻️ 残留 `_SearchMcuPortWorker`/`_ConnectMcuWorker` 并入 `consumption_test_workers/` | ⬜ | — |
| 6-2 | 🆕 `core/consumption_test/consumption_controller.py` 承接流程编排 | ⬜ | start/stop/pause |
| 6-3 | 🆕 `ui/pages/consumption_test/consumption_views/` 视图子构建器 | ⬜ | 按下载区/测试区/结果表格分文件 |
| 6-4 | ♻️ 主文件改 import + 装配 | ⬜ | 仅保留视图与信号订阅 |
| 6-5 | 🧪 controller 单测 | ⬜ | — |
| 6-6 | 验收：功耗测试全流程不变 | ⬜ | 退出 Phase 门禁 |

| 动作 | 文件 | 内容 |
|---|---|---|
| 🆕✂️ | `ui/pages/consumption_test/consumption_test_workers/search_mcu_worker.py` | 搬 `_SearchMcuPortWorker` + `_ConnectMcuWorker` |
| ♻️ | `ui/pages/consumption_test/consumption_test_workers/__init__.py` | 导出新 Worker |
| 🆕 | `core/consumption_test/__init__.py` | 包初始化 + `MODULE_VERSION` |
| 🆕✂️ | `core/consumption_test/consumption_controller.py` | 搬 start/stop/pause 流程编排 |
| 🆕 | `ui/pages/consumption_test/consumption_views/__init__.py` | 视图子构建器包 |
| 🆕✂️ | `consumption_views/download_view.py` | 搬下载区构建逻辑 |
| 🆕✂️ | `consumption_views/test_view.py` | 搬测试区构建逻辑 |
| 🆕✂️ | `consumption_views/result_table_view.py` | 搬结果表格构建逻辑 |
| ♻️✂️ | [consumption_test.py](../../../ui/pages/consumption_test/consumption_test.py) | 删除残留 Worker + 视图构建代码，改 import；仅保留 `ConsumptionTestUI` 装配与信号订阅 |
| 🧪🆕 | `tests/refactor/test_consumption_controller.py` | controller mock 单测 |

**验收**：主文件 3986 → < 1000 行；功耗测试全流程冒烟通过。

---

### Phase 7 — main_window 瘦身 + 样式统一 + 收尾

**目标**：收尾剩余黄区文件——main_window Win32 抽出 + 连接中枢、serialCom 皮肤 token 合并、ai_panel/mcu_io 拆分。

**进度看板**

| # | 子任务 | 状态 | 备注 |
|---|---|---|---|
| 7-1 | 🆕 `ui/utils/win32_frameless.py` 抽出 ~200 行 Win32 ctypes | ⬜ | 从 main_window 顶部迁出 |
| 7-2 | 🆕 `core/instruments/connection_hub.py` 连接共享中枢 | ⬜ | N6705C A/B / 示波器 / 温箱连接状态集中 |
| 7-3 | ♻️ main_window 改 import + 装配 | ⬜ | 目标 < 800 行 |
| 7-4 | 🆕 `ui/styles/tokens.py` 统一主题 token | ⬜ | 合并 serialCom 两套皮肤 + theme.py + page_styles.py 概念 |
| 7-5 | ♻️ serialCom_apple_gpt5p5_style / serialCom_dark_style 改用 token | ⬜ | 去重 |
| 7-6 | ♻️ ai_assist_panel 拆子组件 | ⬜ | 已有 chat_view，继续拆 |
| 7-7 | ♻️ mcu_io_module_frame 参照 serialCom 套路拆 mixins | ⬜ | 1705 行 |
| 7-8 | 🗂️ 同步 `DIRECTORY_STRUCTURE.txt` + `.ai/memory.md` | ⬜ | 最终结构 |
| 7-9 | 验收：全工程冒烟 + lint + 全部 pytest 绿 | ⬜ | 退出最终门禁 |

| 动作 | 文件 | 内容 |
|---|---|---|
| 🆕✂️ | `ui/utils/win32_frameless.py` | 搬 `_RECT`/`_MONITORINFO`/`_MINMAXINFO` + `_WM_*`/`_DWMWA_*` 常量 + 无边框窗口辅助函数 |
| 🆕✂️ | `core/instruments/connection_hub.py` | 搬 main_window 中的"连接状态共享中枢"逻辑 |
| ♻️✂️ | [main_window.py](../../../ui/main_window.py) | 改 import；仅保留导航 + 页面装配 + Signal 宿主 |
| 🆕 | `ui/styles/tokens.py` | 统一颜色/字号/圆角/间距 token |
| ♻️✂️ | [serialCom_apple_gpt5p5_style.py](../../../ui/modules/serialCom_module/serialCom_apple_gpt5p5_style.py) | 改用 token，去重 |
| ♻️✂️ | [serialCom_dark_style.py](../../../ui/modules/serialCom_module/serialCom_dark_style.py) | 改用 token，去重 |
| ♻️✂️ | [ai_assist_panel.py](../../../ui/ai/ai_assist_panel.py) | 拆 panel 子组件到 `ui/ai/ai_assist_views/` |
| ♻️✂️ | [mcu_io_module_frame.py](../../../ui/modules/mcu_io_module_frame.py) | 参照 serialCom 拆 `mcu_io_mixins/` |
| 🗂️ | `DIRECTORY_STRUCTURE.txt` | 同步最终目录结构 |
| 🗂️ | `.ai/memory.md` | 记录重构完成上下文 |

**验收**：main_window 1360 → < 800 行；serialCom 两套皮肤去重 ≥ 30%；全工程冒烟 + lint + pytest 全绿。

---

## 9. 风险与回滚策略

| 风险 | 缓解措施 |
|---|---|
| 拆分后 import 断裂 | 旧入口保留 re-export 兼容；Phase 0 smoke import 测试兜底 |
| Worker 迁移后 Signal 连线断 | 迁移时保持 Signal 名与签名不变；UI 侧只改 import 路径 |
| 控件合并后视觉差异 | Phase 1 每个控件迁移后单独冒烟；保留旧类名 re-export 过渡 |
| serialCom 拆 mixin 后多继承 MRO 异常 | mixin 之间不得互相继承，全部平级组合；用 `super()` 链时显式声明 |
| 脚本引擎下沉 core 后行为漂移 | Phase 5.5 先补脚本引擎单测再迁 |

**回滚单位**：以"一个 Phase 的一个子任务"为最小回滚单位；每个子任务独立 commit（由人工执行），出问题直接 revert 该子任务。

---

## 10. 验收口径汇总（Definition of Done）

每个 Phase 退出前必须全部满足：
1. `python main.py` 启动无报错，目标页面功能冒烟通过。
2. `lint`（项目配置的 linter）无新增告警。
3. `pytest tests/refactor/` 全绿。
4. 源文件行数达到该 Phase 目标（见各 Phase 验收）。
5. `DIRECTORY_STRUCTURE.txt` 已同步（若有结构变动）。
6. `.ai/memory.md` 更新该 Phase 完成状态。

全工程 DoD（Phase 7 退出）：
- 28 个红区文件降至 ≤ 8 个（仅保留职责单一的同质文件）。
- `ui/` 中无纯算法/解析函数（`test_no_qt_in_core_analysis.py` 扩展覆盖）。
- `ui/widgets/` 成为通用控件单一权威来源。
- `core/controllers/` 承接所有粗粒度仪器操作编排。

---

## 11. 附录：目标目录结构预览（Phase 7 完成后）

```
ui/
  ├─ main_window.py              (< 800 行，导航+装配)
  ├─ utils/win32_frameless.py    (🆕 Win32 胶水)
  ├─ widgets/                    (通用控件单一权威)
  │   ├─ toggle.py / card_frame.py / tab_bar.py / ...
  ├─ modules/serialCom_module/
  │   ├─ serialCom_module_frame.py  (< 500 行，组合壳)
  │   ├─ mixins/    (7 个)
  │   ├─ widgets/   (剩余专属)
  │   ├─ dialogs/   (8 个)
  │   ├─ workers/   (3 个)
  │   └─ styles/    (token 化)
  └─ pages/
      ├─ n6705c_power_analyzer/n6705c_datalog_ui.py  (< 800 行)
      ├─ consumption_test/consumption_test.py        (< 1000 行)
      └─ pmu_test/clk_test_ui.py 等                  (仅视图)

core/
  ├─ pmu_test/        (clk/gpadc/dcdc/isgain/oscp 各 analysis+worker)
  ├─ n6705c_datalog/  (3 worker + analysis)
  ├─ consumption_test/ (controller)
  ├─ serialcom/       (script_engine)
  ├─ controllers/     (oscilloscope_controller)
  └─ instruments/connection_hub.py  (🆕 连接共享中枢)
```

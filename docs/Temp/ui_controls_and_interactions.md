# KK_Lab UI 控件与交互逻辑汇总

> 本文汇总 KK_Lab 整个 UI 的骨架、导航机制、复用控件、以及 **15 个页面（含 Tab 子页）** 的控件构成与交互逻辑。
>
> 代码事实源（入口）：
> - 主入口： [main.py](../../main.py)
> - 主窗口： [ui/main_window.py](../../ui/main_window.py)
> - 导航： [ui/nav_controller.py](../../ui/nav_controller.py)
> - 顶栏： [ui/app_top_bar.py](../../ui/app_top_bar.py)
> - 状态栏： [ui/instrument_status.py](../../ui/instrument_status.py)
> - 各页面： `ui/pages/<page>/`，复用件： `ui/modules/`、`ui/widgets/`

---

## 一、应用骨架

### 1.1 入口链

```
main.py
 ├─ 全局初始化：stdout/stderr 兜底、faulthandler、setup_logging、log_ring（AI）
 ├─ 全局异常钩子 _global_excepthook → logger.critical
 ├─ HoverFixStyle(QProxyStyle)：polish 时给所有 QWidget 开 WA_Hover（保证 hover QSS 生效）
 ├─ qInstallMessageHandler：过滤 QPainter::end 噪音告警
 └─ QApplication(Fusion 基样式) → MainWindow(with_ai=WITH_AI_ASSISTANT)
```

### 1.2 主窗口三层布局

[MainWindow._create_main_content](../../ui/main_window.py)：

```
┌───────────────────────────────────────────────────────────────┐
│ AppTopBar（自绘标题栏，固定高 32px）                            │
├─────────────┬────────────────────────────────┬────────────────┤
│ 左侧导航     │  right_content                  │  AI 面板        │
│ 固定 187px  │  instrument_ui_container        │  AIAssistPanel  │
│ (QFrame     │  （页面容器，懒加载 15 个页面）   │  可显隐/拖宽     │
│  #leftNav)  │                                 │                 │
│             │                                 │                 │
│ 底部：       │                                 │                 │
│ Help 按钮    │                                 │                 │
│ 仪器状态列表 │                                 │                 │
└─────────────┴────────────────────────────────┴────────────────┘
   main_splitter(水平)                  outer_splitter(水平)
```

- **主分割**：`main_splitter = QSplitter(Horizontal)`，左导航 `setCollapsible(False)`，初始 `[187, 1013]`。
- **AI 面板**：`with_ai=True` 时再包一层 `outer_splitter`，宽度经 `ui/ai/panel_state.py` 持久化（`load_panel_state/clamp_width`）；`with_ai=False` 时直接 `main_layout.addWidget(main_splitter)` 并隐藏顶栏 AI 按钮。
- **Windows 原生框**：`showEvent` 时经 ctypes 注入 `WS_CAPTION|WS_THICKFRAME|WS_MINIMIZEBOX|WS_MAXIMIZEBOX|WS_SYSMENU`，并用 DWM API 设圆角与边框色 `#203440`；非 Windows 平台用 `FramelessWindowHint` + 自绘 6px 边缘缩放。
- **全局样式**：`_setup_style()` 设深色 QPalette + `Segoe UI 9` + 大段 QSS（QPushButton/QComboBox/QLineEdit/QTabWidget 等基础控件深色主题）+ `SCROLLBAR_STYLE`。

---

## 二、顶栏 AppTopBar（自绘 CSD）

[ui/app_top_bar.py](../../ui/app_top_bar.py)，`objectName=appTopBar`，高 32px：

| 区域 | 控件 | 交互 |
|---|---|---|
| 左 | 应用图标（`kk_lab.svg` 着色渲染）+ `QLabel#appTitleText` | 空白区按下拖动窗口；双击最大化/还原 |
| 右 | `AIPanelButton`（checkable） | `toggled → MainWindow._on_ai_panel_toggled` 显隐 AI 面板；`ai_settings.enabled=False` 时直接隐藏 |
| 右 | 最小化 / 最大化-还原 / 关闭按钮（`QPushButton#winCtrlBtn` / `#winCloseBtn`，46×32，图标为 QPainter 自绘 1px 线条 min/max/restore/close） | close 悬停变红 `#e81123`；最大化图标随窗口状态切换（`sync_max_icon`，由 MainWindow.changeEvent 驱动） |

控件高度单一权威：窗口按钮用 ID 选择器钉死尺寸（符合项目 §24 规范）。

---

## 三、左侧导航（NavController）

[ui/nav_controller.py](../../ui/nav_controller.py)

### 3.1 导航按钮分组（11 个，QButtonGroup 互斥）

按钮均为 `SidebarNavButton`（SVG 图标 + 标题 + 右侧箭头，checked 态显示箭头）：

| 分组标题 | 按钮 | SVG 图标 | 悬停子菜单项（SidebarSubMenu） |
|---|---|---|---|
| （顶部 Logo） | "LabControl Pro" 文本 | — | — |
| INSTRUMENTS | N6705C（默认 checked） | zap | `analyser` N6705C Analyser / `datalog` N6705C Datalog |
| | Oscilloscope | activity | — |
| | Chamber | thermometer | — |
| AUTOMATION | PMU Test | settings | `dcdc_efficiency` / `output_voltage` / `is_gain` / `oscp` / `gpadc_test` / `clk_test` |
| | Charger Test | battery | `config_traverse` / `status_register` / `iterm` / `regulation_voltage` |
| | Module Test | module_test | `ldo` / `dcdc` |
| | Consumption Test | gauge | `auto_test` / `high_low_temp` |
| | VminHunter | crosshair | — |
| TOOLS | PMU | zap | `1811` / `1860` |
| | Collection | settings | `mcu_io` MCU IO / `kk_serials` KK Serials / `i2c_control` IIC Control |
| ORCHESTRATION | Orchestrator | network | — |

### 3.2 交互逻辑

- **悬停弹子菜单**：按钮和子菜单都 `installEventFilter(host)`；`Enter` 立即 `_show_xxx_submenu()`（定位到按钮右侧 +8px），`Leave` 延迟 220ms（`_SUBMENU_HIDE_DELAY`）后 `_hide_xxx_submenu_if_needed()`（按钮或菜单任一仍悬停则不隐藏）。
- **子菜单点击**：记录 `NavController.current_<group>_key` → `set_current_item` 高亮 → 父按钮 `setChecked(True)` → 调宿主页 `_create_xxx_ui(selected_test=key)` → 隐藏菜单。
- **按钮点击**：`_connect_signals` 把 11 个按钮 `clicked` 全接到 `_on_nav_button_clicked` → `nav.handle_nav_button_clicked(sender)`：隐藏其它 6 个子菜单 → 调对应 `_create_*_ui()`（带当前子项 key）→ `_refresh_nav_arrow_state()`。
- **快捷键**：`Ctrl+1` N6705C、`Ctrl+2` Oscilloscope、`Ctrl+3` Chamber、`Ctrl+4` PMU Test、`Ctrl+5` Charger Test、`Ctrl+6` Consumption Test、`Ctrl+7` VminHunter、`Ctrl+8` Orchestrator、`Ctrl+0` Collection；快捷键提示自动拼进按钮 tooltip。
- **子项 key → Tab 索引映射**：`pmu_test_tab_map`（6 项）、`charger_test_tab_map`（4 项）、`module_test_tab_map`（ldo=0/dcdc=1）、`consumption_test_tab_map`（2 项）。

---

## 四、页面切换机制

### 4.1 懒加载 + 淡入

每个 `_create_*_ui()` 同模式（[ui/main_window.py](../../ui/main_window.py) 1419 行起）：

1. `_hide_all_instrument_uis()`：保存当前窗口几何 `_page_switch_geometry`，15 个页面实例全部 `setGraphicsEffect(None) + hide()`。
2. 实例为 None → 构造（透传 `n6705c_top / mso64b_top / chamber_ui / instrument_manager / ui_action_registry`）并 `addWidget` 进 `instrument_ui_container_layout`；否则 `_sync_from_top()` + `show()`。
3. 置 `current_instrument_ui = "<page_key>"`。
4. Tab 容器页额外：`if selected_test in tab_map: set_current_test(selected_test)`。
5. `_fade_in_widget()`：
   - 同步 AI 上下文：`ai_service.set_page_context(help_key)`、`_update_ai_apply_callbacks()`、`ai_panel.refresh_quick_actions()/on_page_changed()`；
   - 150ms `QGraphicsOpacityEffect` 淡入动画（InOutQuad），完成后清除 effect；
   - `QTimer.singleShot(0, _restore_page_switch_geometry)` 恢复窗口几何（最大化/全屏跳过）。

### 4.2 页面实例与 page_key 对照

| page_key (`current_instrument_ui`) | 页面类 | 构造方法 |
|---|---|---|
| `power_analyser` | N6705CAnalyserUI | `_create_power_analyser_ui` |
| `datalog` | N6705CDatalogUI | `_create_datalog_ui` |
| `oscilloscope` | OscilloscopeBaseUI | `_create_oscilloscope_ui` |
| `thermal_chamber` | ChamberControlUI | `_create_thermal_chamber_ui` |
| `pmu_test` | PMUTestUI（QTabWidget 容器，6 子页） | `_create_pmu_test_ui` |
| `charger_test` | ChargerTestUI（4 子页） | `_create_charger_test_ui` |
| `module_test` | ModuleTestUI（2 子页） | `_create_module_test_ui` |
| `consumption_test` | ConsumptionTestWrapper（2 子页） | `_create_consumption_test_ui` |
| `orchestrator` | OrchestratorUI | `_create_orchestrator_ui` |
| `vmin_hunter` | VminHunterUI | `_create_vmin_hunter_ui` |
| `kk_serials` | _KKSerialsPage（main_window 内嵌，SerialComMixin+QWidget） | `_create_kk_serials_ui` |
| `i2c_control` | _I2cControlPage（I2cMixin+QWidget） | `_create_i2c_control_ui` |
| `collection` | _CollectionPage（McuIoConnectionMixin+QWidget） | `_create_collection_ui` |
| `pmu_1811` | Pmu1811UI | `_create_pmu_ui` |
| `pmu_1860` | Pmu1860UI（占位页） | `_create_pmu_ui` |

`_switch_pa_mode(mode)`：N6705C 按钮在 analyser/datalog 两页间切换。

### 4.3 跨页数据分发

- `TestManager.data_updated → _update_data(data)`：按 `current_instrument_ui` 分发——`power_analyser` 更新 4 通道电压电流值；`pmu_test` 按 `test_type` 调 `update_test_result`；其余页写 `channels[]` 的 voltage/current QLabel。
- `ConnectionHub.connection_changed → _update_instrument_status` → 状态面板刷新。

---

## 五、左下角：Help + 仪器状态

[ui/instrument_status.py](../../ui/instrument_status.py) `InstrumentStatusPanel.create_bottom_widget()`：

- 分隔线（1px `#1a2238`）。
- **Help 按钮**：紫色 `? Help`（42px 高）→ `MainWindow._on_help()`：按 `_get_current_help_key()`（Tab 容器页映射到子页 key，如 `pmu_dcdc_efficiency`）读 `helps/<key>.html` + 版本脚注，弹深色 `QDialog(parent=self)` + QTextBrowser + 关闭按钮。
- **仪器状态列表**：每台仪器一项（彩色圆点 ● + 名称 + `to:\n 地址` 两行文本）；`_DISPLAY_NAME_MAP` 映射型号显示名（N6705C/MSO64B/DSOX4034A/VT6002/MT3065/WT2040/53230A/Serial/USB-I2C）；`default/main_scope` 槽位隐藏；新连接时 `ToastNotification` 弹提示。

---

## 六、通用复用件（ui/modules + ui/widgets）

### 6.1 连接 Mixin 三段式契约

所有仪器连接区 Mixin 统一接口：`init_<x>_connection(...)` → `build_<x>_connection_widgets(layout, title_row=...)` → `bind_<x>_signals()`；内部搜索/连接走 QThread Worker，状态经 Signal 回刷。

| Mixin | 文件 | 主要控件 |
|---|---|---|
| N6705CConnectionMixin | [n6705c_module_frame.py](../../ui/modules/n6705c_module_frame.py) | 搜索按钮 `_N6705CSearchButton`、地址下拉、连接/断开、状态点 |
| OscilloscopeConnectionMixin | [oscilloscope_module_frame.py](../../ui/modules/oscilloscope_module_frame.py) | 同上（`_ScopeSearchButton`） |
| ChamberConnectionMixin | [chamber_module_frame.py](../../ui/modules/chamber_module_frame.py) | 串口搜索 `_ChamberSearchButton`、温箱类型选择（默认 vt6002） |
| Keysight53230AConnectionMixin | [keysight_53230a_module_frame.py](../../ui/modules/keysight_53230a_module_frame.py) | `_CounterSearchButton`、频率计连接 |
| McuIoConnectionMixin | [mcu_io_module_frame.py](../../ui/modules/mcu_io_module_frame.py) | MCU 类型切换（CH9114F / YD-RP2040）、GPIO 行（GpioLevelToggle + Pulse/Toggle 按钮 + Read）、连接 Worker 组 |
| SerialComMixin | [serialCom_module/](../../ui/modules/serialCom_module/serialCom_module_frame.py) | 完整串口控制台（见 §7.12） |
| I2cMixin | [IIC_Module/i2c_mixin.py](../../ui/modules/IIC_Module/i2c_mixin.py) | I2C 面板（见 §7.13） |
| Ch9114GpioMixin | [ch9114f_gpio_module_frame.py](../../ui/modules/ch9114f_gpio_module_frame.py) | CH9114F GPIO 高低切换（Ch9114HiLoToggle） |

### 6.2 ExecutionLogsFrame（执行日志区）

[execution_logs_module_frame.py](../../ui/modules/execution_logs_module_frame.py)：

- 头部：日志图标 + 标题 + `_PillSwitcher`（ALL/INFO/WARN/ERR 等级过滤丸）+ 搜索框 `QLineEdit#searchInput`（filter 图标，关键字过滤）+ "Auto scroll" 标签 + `_AutoScrollToggle`。
- 可选进度区（`show_progress`）：当前步骤文本 + 进度。
- 交互：折叠态记忆 splitter sizes；规范强制经 `ExecutionLogsFrame.wrap_with(main_content, ...)` 装配进 `QSplitter(Qt.Vertical)` 隐式手柄，禁直接 addWidget / setMaximumHeight。
- `append_log(msg)` 供页面与 `[AI]` 日志回填。

### 6.3 ui/widgets 通用控件

`DarkComboBox`（高度自洽 22px）、`SidebarNavButton`、`SidebarSubMenu`、`PlotWidget`（pyqtgraph 封装）、`ProgressButton`、`ToastNotification`、`StartSequence`、`InstrumentStatePoller`、自定义滚动条。

---

## 七、各页面控件与交互

### 7.1 N6705C Analyser（power_analyser）

[N6705CAnalyserUI](../../ui/pages/n6705c_power_analyzer/n6705c_analyser_ui.py)（`QWidget + SettingViewMixin + BatchViewMixin + ConsumptionViewMixin`，三视图分文件 `analyser_view_setting/batch/consumption.py`）：

- **顶部条** `_create_top_bar`：A/B 双机槽连接卡（搜索、地址、连接/断开、状态）；轮询开关（SlideToggle）→ `_on_polling_toggle_clicked` 启停通道同步。
- **通道 Tab**：`ChannelTabBar` + `_build_channel_tab_buttons`，按已连接设备动态重建（`_rebuild_dynamic_sections`）；切换 `_switch_channel(dev_label, ch)` 应用通道主题色 `_apply_channel_theme`。
- **设置视图**：电压/电流输入（`_on_voltage_text_changed` 标 dirty → Set 按钮高亮；回车 `_on_voltage_input_enter` 直接下发）、Set 按钮 `_on_set_clicked`、输出开关 `_on_output_toggle_clicked`、Measure `_on_measure_clicked`、模式按钮组（CV/CC 等，`_on_mode_button_clicked`，与仪器模式双向映射）。
- **批量/功耗视图**：批量通道表格与功耗统计（各 Mixin 内实现）。
- **轮询**：`_start_channel_sync` → `_read_channel_snapshot`（持 session IO 锁）→ `_apply_channel_snapshot` 刷新数值；`showEvent/hideEvent` 自动启停轮询。
- 注册 AI UI 动作（`_register_ai_ui_actions`）：连接/设置/输出等按钮原槽进白名单。

### 7.2 N6705C Datalog（datalog）

[N6705CDatalogUI](../../ui/pages/n6705c_power_analyzer/n6705c_datalog_ui.py)，自有 Worker 组（`_ScanWorker/_ConnectWorker/_DatalogWorker`）：

- 连接卡（扫描/连接，支持 Mock）、`ChannelConfigTabBar`（通道配置 tab）、`VerticalTextButton`（竖排折叠侧栏）。
- 采集流程：`_DatalogWorker` 配采样周期 → 等待捕获 → 下载（CSV fallback 双通道电流）→ pyqtgraph 波形；`_generate_mock_data` Mock 分支。
- 波形区交互：`ScaleOffsetEdit`（滚轮调缩放/偏移）、`ChannelNameLabel`（双击改名）、marker 窗口（`get_marker_window`）、可见范围（`get_visible_x_range`）、`build_waveform_digest`（供 AI 摘要）、`export_combined_csv_to_path`（非交互导出，供 AI `export_datalog_csv`）。
- `ToggleLabel` 可点击标签作轻量开关；`CardFrame`/`ClickableHeader` 卡片容器（头部可点击折叠）。

### 7.3 Oscilloscope（oscilloscope）

[OscilloscopeBaseUI](../../ui/pages/oscilloscope/oscilloscope_base_ui.py)：

- 顶栏：标题、系统状态、连接区（搜索 `_OscSearchThread`、连接/断开 `_on_connect_toggle`）。
- 控制行：RunStopToggle（运行/停止，`_apply_run_stop_style`）、通道卡 CH1-4（`_create_channel_card`：CouplingToggle 耦合切换、垂直档位/偏移）、时基 `TimeScaleEdit`（`timebase_apply_requested`）、触发卡（TriggerModeToggle、触发源、电平）。
- 显示卡 `_create_display_card`：截屏图像显示 + 右键菜单（`_on_capture_context_menu` 导出/反色）。
- 测量卡 `_create_measurements_card`：`_on_add_measurement` 增项 / `_on_delete_single_measurement` / `_on_clear_measurements`，metric card 网格（`_create_metric_card`：标题+值+单位），`update_measure_result` 回刷。
- Quick Function 卡：`_on_all_channel_set_default`、`_on_ripple_set`。
- dirty 跟踪：`_connect_dirty_tracking` → 参数变更 `_mark_settings_dirty` → Apply 按钮脉冲动画（`_start_apply_pulse` 定时变色）→ 应用后 `_clear_settings_dirty`。
- `_set_interactive_enabled(False)` 在操作期整体禁用交互。

### 7.4 Chamber（thermal_chamber）

[ChamberControlUI](../../ui/pages/chamber/chamber_control_ui.py) + 自绘 `TemperatureGauge` 仪表：

- 区块（`_build_*_block`）：头部、连接表单（温箱类型 VT6002/MT3065/WT2040 切换 `_on_chamber_type_changed`、串口搜索/连接）、状态块、监控块（当前温湿度 + 仪表）、电源块、目标温度块、循环块（loop 配置）、摘要块。
- 双布局：`_build_large_layout` / `_build_compact_layout` 按宽度自适应。
- 会话信号：`_on_manager_session_connected/disconnected/connect_failed` 刷新状态；`connection_changed` 上报主窗口。

### 7.5 PMU Test（pmu_test，QTabWidget 容器）

[PMUTestUI](../../ui/pages/pmu_test/pmu_test_ui.py)：`TEST_TAB_MAP` 6 子页，`set_current_test(key)` 切 tab，`update_test_result(test_type, result)` 分发结果。各子页统一结构：连接卡 + 配置表单 + Start/Stop + ExecutionLogsFrame + 结果/图表；均实现 AI 契约六方法并发 `sequence_execution_finished(bool, str)`。

| 子页 | 关键控件 |
|---|---|
| DCDC Efficiency（`pmu_dcdc_efficiency.py`） | `▶ START SEQUENCE` / `■ STOP`；图表工具条：缩放 `+`/`−`、`Auto`、`Marker`；`⇧ Import CSV` / `⇩ Export CSV`；效率曲线图 |
| Output Voltage（`pmu_output_voltage.py`） | `▷ Start Sequence` / `■ Stop` / `⇩ Export CSV`；`Save Config` / `Load Config` |
| Is_gain（`pmu_isGain_ui.py`） | `▷ Start Sequence` / `Abort Test` / `Export`；导出确认对话框（Cancel/Export） |
| OSCP（`pmu_oscp_ui.py`） | `▶ START` / `■ STOP`；CardFrame 卡片 |
| GPADC Test（`gpadc_test_ui.py`） | `▶ START TEST` / `■` / `Export Result` / `Export Parameters` / `Save Config` / `Load Config`（含串口 Mixin） |
| CLK Test（`clk_test_ui.py`） | `Import CSV` / `▷ Start Sequence` / `■ Stop` / `Export Result`（含示波器+温箱+53230A 三路连接 Mixin） |

交互主线：填参 → Start 起 `core/pmu_test/<name>/` Worker（QThread）→ Signal 回刷日志/进度/结果 → Stop 中止 → Export 落 `Results/`（时间戳+芯片型号）。

### 7.6 Charger Test（charger_test，4 子页）

[ChargerTestUI](../../ui/pages/charger_test/charger_test_ui.py)，子页均为 CardFrame 卡片布局 + N6705C/Chamber 连接卡：

| 子页 | 卡片构成 | 关键按钮 |
|---|---|---|
| Config Traverse（`config_traverse_test.py`） | N6705C / Test Config / ⇄ Register Range | `▶ START TRAVERSE` / `■ STOP` / `⇩ Export CSV` |
| Status Register（`status_register_test.py`） | ◉ Test Item / ⚡ N6705C / Chamber / ☷ Test Config / ↔ Register Config | `▶ START POLL` / `■ STOP`；`_StatusPollWorker` 轮询状态寄存器 |
| Iterm（`iterm_test.py`） | ⚡ N6705C / ☰ Test Item / ☷ Test Config / ⇄ Register Range | `▶ START ITERM TEST` / `■ STOP` / `⇩ Export CSV` |
| Regulation Voltage（`regulation_voltage_ui.py`） | ⚡ N6705C / ☷ Test Config / ⇄ Register Range | `▶ START TEST` / `■ STOP` / `⇩ Export CSV` |

### 7.7 Module Test（module_test，2 子页）

[ModuleTestUI](../../ui/pages/module_test/module_test_ui.py)：`LDO` / `DCDC` 两 tab，共用 `_base_subpage.py` 基类：

- DUT 模式管理：`+ 添加模式` / `编辑` / `删除`。
- 操作行：`▶ 开始测试` / `■ 停止` / `保存` / `另存为` / `打开` 配置；`全选测试项` / `清空结果` / `打开报告`。
- 每测试项行内 `设置` 按钮；widgets.py 表格 `+ 行` / `- 行`。
- 中文 UI（本模块为中文文案页面）。

### 7.8 Consumption Test（consumption_test，2 子页）

[ConsumptionTestWrapper](../../ui/pages/consumption_test/consumption_test_wrapper.py)：`Auto Test` / `High-Low Temperature Test`。

- **Auto Test**（`consumption_test.py` + view_config/view_panels/view_results Mixin，详见 [consumption_test_summary.md](./consumption_test_summary.md)）：Header（Import/Export Config）；Config Import 面板（▼ 折叠）；左列 Connection Panel（MCU `Connect`）、Firmware Download（`...` 浏览）、Test Config；右列 Channel Config 横向滚卡、Chip `Check`/`Save`、每通道 `Exec`、结果区 `⤓ Export` / `Save DataLog`；自定义开关控件 DownloadModeToggle/ControlMethodToggle/PolarityToggle/BinaryTextToggle。
- **High-Low Temp**（`high_low_temp_test_ui.py`）：`▷ Start Test` / `Export CSV`；温箱联动的高低温度功耗测试。

### 7.9 VminHunter（vmin_hunter）

[VminHunterUI](../../ui/pages/vmin_hunter/vmin_hunter_ui.py)（N6705C + Chamber + MCU IO 三路连接 Mixin）：

- 区块：Header、连接面板、Test Config（电压扫描 start/end/step + `_update_sweep_hint`、温度开关 `_on_temp_toggled`、VCOREL 开关 `_on_vcorel_toggled`）、Channel Config（电流限值 spin）、IIC 组（`_create_iic_group` 可整体启停）、操作行、结果面板。
- 交互：`_on_start_clicked` → 外部 sleep sweep 或分相位 `_start_sweep_phase(phase_index)` → `_on_phase_finished` 级联下一阶段；`_on_stop_clicked` 中止；UART 数据 `_on_uart_data_received` 解析状态脚电平；日志进 ExecutionLogsFrame。

### 7.10 Orchestrator（orchestrator）

[OrchestratorUI](../../ui/pages/orchestrator/orchestrator_ui.py)（N6705C + Chamber + SerialCom 三 Mixin）：

- 左面板 `_build_left_panel`：`InstrumentConnectionPanel`（各仪器连接页，含 MCU IO / CH9114F `Connect`）；`NodePalette` 节点面板（仪器/IO/逻辑/值节点，`_on_add_node` 拖入画布）。
- 画布工具条（sequence_canvas.py）：`+ Add` / `✕ Remove` / `Copy` / `Paste` / `Duplicate` / `↑` / `↓` / `Templates`（模板库 TemplateGallery）/ `Save` / `Load`（sequence_io JSON）；运行控制 `▶ Run` / `∥ Pause` / `■ Stop`。
- 右/下面板：`PropertyPanel` 节点参数编辑（逻辑节点 `+ Add Else If`）、`ValidationPanel` 预检问题对话框（`issue_activated` 定位节点 `_locate_validation_issue`）、`ResultPanel` 结果表 + 趋势图 + `Export`、`RecordDataPointEditor`（`+ 添加字段` / `↻ 刷新变量`）。
- 运行链：`_on_run` → preflight 校验（`_show_preflight_issues`）→ `_show_run_summary` 确认 → Executor 逐节点执行；`prompt_requested` 人工输入弹窗（带超时 `_PromptRequest`）；`sequence_execution_finished` 上报 AI 回灌。
- AI 接口：`get_ai_sequence_data/test_config/test_steps/result_summary`、`ai_set_test_variable`、`ai_run_single_step`。

### 7.11 Collection - MCU IO（collection）

[_CollectionPage](../../ui/main_window.py)（main_window 内嵌类）：标题行（随 MCU 类型联动 "MCU IO (CH9114F/YD-RP2040)"）+ 连接卡片（380px 限宽）+ GPIO 行（电平切换、Pulse/Toggle、Read）+ `ExecutionLogsFrame(title="MCU IO Logs", show_progress=False)`，`QSplitter(Qt.Vertical)` 上下布局。

### 7.12 Collection - KK Serials（kk_serials）

[_KKSerialsPage](../../ui/main_window.py) = `SerialComMixin`（[serialCom_module_frame.py](../../ui/modules/serialCom_module/serialCom_module_frame.py)，MODE_FULL）：

- 连接区：串口搜索、波特率、`Connect`；多会话管理（`SerialSessionManager` + 会话 tab，`session_data_received` 转发 AI rx_cache）。
- 收发区：RX 显示（过滤/保存）、TX 输入 + `Send`、脚本（ScriptMixin：步骤序列、`Add Step`、套件配置保存）、图表（ChartMixin + SerialChartDialog：字段/规则/序列/统计列编辑器）。
- 设置对话框 tab：Serial / RX / TX / Log / Display / Auto-Detect / About（OK/Cancel 二元化）。
- 工具条 `Clear`、快捷命令等（ToolbarMixin）。

### 7.13 Collection - IIC Control（i2c_control）

[_I2cControlPage](../../ui/main_window.py) = `I2cMixin`（[i2c_mixin.py](../../ui/modules/IIC_Module/i2c_mixin.py) + `_I2C_DARK_STYLE`）：

- 模板区：`Save` / `Open` / `Export`；字段编辑 `+ Field`。
- 读写区：HexLineEdit（十六进制输入）、RegAddrInput（寄存器地址）、DataValueInput、BitsTable/BitsTableContainer（位域表，ToggleSwitch 位开关）、`Read` / `Write`（QThread Worker）。
- 序列区（可折叠 ▼）：`Linked Only` 过滤、`New`/`Dup`/`Del` 序列、`+ Cmd`/`- Cmd` 命令行、`YAML` 模式切换、`Save`/`Stop`/`Run`（`_I2cSequenceWorker`）。
- 底层：DLL `Browse`/`Reset`、`BES Chip Check`（`_I2cChipCheckWorker`）。

### 7.14 PMU 1811（pmu_1811）

[Pmu1811UI](../../ui/pages/pmu/pmu_1811/page.py)（独立三层模块 models/workers/page+widgets）：

- Header + 芯片配置卡（`_build_chip_config`，`_on_chip_config`）。
- 画布 `DiagramCanvas`：`ModuleCard` 模块卡（LDO/BUCK/SW），点击选中 `_on_select` → 右侧 `PropertyPanel`（使能 ToggleSwitch、模式、电压/dsleep 电压编辑）；卡片上直接改电压 `_on_card_voltage`、使能 `_on_card_enable`；右键 `_on_context` 上下文菜单（成对写入等）。
- `◉ Check` 全量读（`LdoReadAllWorker`）；写入走 `LdoWriteWorker` / `PairWriteWorker`（主次联动 `_start_pair_write`）。
- `_BlockedOverlay`：Worker 忙时遮罩锁操作；日志 `_log(level, msg)` 进日志区。

### 7.15 PMU 1860（pmu_1860）

[Pmu1860UI](../../ui/pages/pmu/pmu_1860_ui.py)：占位页，仅标题 + "（占位页面，待实现）" 提示。

---

## 八、AI 助手面板与 AI↔UI 交互

### 8.1 AIAssistPanel

[ui/ai/ai_assist_panel.py](../../ui/ai/ai_assist_panel.py)（右栏 QFrame）：

- 信号：`request_close` / `request_open` / `pick_requested`。
- 组成：ChatView 对话区、快捷动作区（`refresh_quick_actions` 按页刷新）、任务托盘、草案预览（ConfigPreview/ScriptPreview）。
- `confirm_action(spec, arguments, reason)`：高风险动作确认对话框（ActionConfirmDialog）。
- `attach_picked_context(label, content)`：ElementPicker 拾取的控件上下文附加进对话。
- 页切换钩子 `on_page_changed`。

### 8.2 MainWindow 侧 AI 桥（_setup_ai_action_system）

- **动作系统**：`build_action_system(ActionDeps(...))` 注入约 30 个 UI 回调：打开页面 `_ai_open_page`（含 Collection/PMU 子项 key 预置）、面板开关 `_ai_toggle_panel`、串口收发/枚举/清缓存、测试 run/pause/stop/设变量/单步、温箱判稳 `_ai_chamber_wait_stable`（busy 租约 + ThreadPool + QEventLoop 轮询不卡 UI）、Datalog CSV 导出、波形数据/范围/marker provider。
- **UI 动作白名单**：`UIActionRegistry` 按 page_key 登记按钮原槽；`_ai_ui_invoke` 仅允许触发当前页动作，前置 `enabled_when` 检查，执行后 `[AI] 触发 xxx：成功/失败` 回填页面 `append_log`。
- **页面能力契约**（鸭子类型 `_ai_caps`）：`ai_capabilities / ai_get_config / ai_apply_config / ai_start_test / ai_stop_test / ai_get_result_summary`；`resolve_active_ai_page` 对 Tab 容器页下钻 `tab_widget.currentWidget()`，保证 page_key 与子页对齐。
- **调度与回灌**：`schedule_register_callback` 起单次 QTimer → 到点 dispatcher 执行 → `pending_task_registry` 回灌 `resume_with_task_result`；`scan_finished`（仪器扫描）与 `sequence_execution_finished`（测试序列）两类异步完成信号同样回灌续跑。

---

## 九、全局交互约定（速查）

1. **耗时操作一律 QThread Worker + Signal/Slot** 回刷 UI；页面不直接做阻塞 IO。
2. **弹窗**：`QDialog(parent=self)`，OK/Cancel 显式二元化（default/autoDefault）。
3. **数值标签**：`名称 (单位)` 格式。
4. **控件高度**：可复用控件用 `#objectName` ID 选择器自钉高度（标准 22px），父页面 QSS 禁裸 `min-height`。
5. **页面帮助**：每页对应 `helps/<page_key>.html`，Help 按钮按当前页（含 Tab 子页）打开。
6. **AI 可见性**：页面注册 `ui_action_registry` 的动作才可被 AI `ui_invoke` 触发，且严格按当前页隔离。

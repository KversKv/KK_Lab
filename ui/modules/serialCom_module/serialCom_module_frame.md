# serialCom_module_frame.py — 页面结构与架构说明

> 串口调试控制台（KK Serial Console）核心实现文件。
> 既可作为主程序内嵌页面（暗色风格），也可作为独立打包程序运行（Apple 浅色风格）。

---

## 1. 模块定位

| 项 | 说明 |
|---|---|
| 路径 | `ui/modules/serialCom_module/serialCom_module_frame.py` |
| 分层 | `ui/` 层 UI 页面，禁止阻塞 IO，串口读写一律走 `QThread + Signal/Slot` |
| 入口 | `python -m ui.modules.serialCom_module.serialCom_module_frame`（独立运行）|
| 风格切换 | 通过 `_select_serialcom_style_module()` 在暗色 / Apple 浅色样式间运行时切换 |

---

## 2. 同目录协作文件

| 文件 | 职责 |
|---|---|
| `serialCom_module_frame.py` | 主体：`SerialComMixin` 业务逻辑 + 所有对话框 / 控件类 |
| `serialCom_dark_style.py` | 暗色主题样式表（主程序内嵌时使用）|
| `serialCom_apple_gpt5p5_style.py` | Apple 浅色主题样式表（独立运行时使用）|
| `serial_session.py` | `SerialSession`：单条串口会话（端口、读线程、收发计数）|
| `serial_session_manager.py` | `SerialSessionManager`：多会话统一管理（创建 / 移除 / 广播）|

---

## 3. 样式动态加载机制

```
_select_serialcom_style_module()
        │  依据 环境变量 KK_SERIALCOM_STYLE / __main__ / frozen exe 名
        ▼
   选择 dark 或 apple 样式模块名
        │
_importlib.import_module(...)               # 动态导入样式模块
        │
globals().update(_SERIALCOM_STYLE_EXPORTS)  # 把约 130 个样式符号注入本模块全局
```

- 切换优先级：`KK_SERIALCOM_STYLE` 环境变量 > 运行模式（`__main__` 或冻结的 `serialcom_module.exe`）> 默认暗色。
- `_SERIALCOM_STYLE_EXPORTS` 是一个白名单元组，列出两套样式模块都必须导出的符号（颜色常量、样式函数、`SerialDarkComboBox` 等）。

---

## 4. 核心架构总览

```
SerialComMixin（业务逻辑混入类，无 UI 基类）
   │  与 QWidget 组合使用：class XxxWidget(SerialComMixin, QWidget)
   │
   ├── 简易串口连接组件  init/build_serial_connection_widgets（MODE_INLINE / MODE_FULL / MODE_SEARCH_SELECT）
   │
   └── 完整控制台        complete_serialComWidget(parent_layout)   ← 主入口
            │
            ├── _build_sc_toolbar()        顶部工具栏
            ├── body_splitter (Horizontal)
            │      ├── _build_sc_sidebar()  左侧参数侧栏
            │      └── center_widget
            │             └── center_splitter (Vertical)
            │                    ├── top_section
            │                    │     ├── _build_sc_log_area()   日志显示区
            │                    │     │      └── _build_sc_status_bar()  状态栏（嵌在日志框底部，非独立节点）
            │                    │     └── _build_sc_send_area()  发送区
            │                    └── _build_sc_quick_commands()   快捷指令 / 脚本区

会话层：SerialSessionManager ──持有多个── SerialSession ──持有── _SessionReadWorker(QThread)
```

> ⚠️ 注意：`_build_sc_status_bar()`（截图底部 `Port: Unconnected · Baud rate · RX · TX`）
> **不是** `outer` 的独立子节点，而是被 `_build_sc_log_area()` 添加到日志框 `QVBoxLayout` 的最底部。

---

## 5. 完整控制台页面结构（`complete_serialComWidget`，行 931）

布局根 `outer = QVBoxLayout(10,10,10,10)`，自上而下：工具栏 → `body_splitter`。
对照下面截图区块逐一说明（控件名为源码中的 `self._sc_*` 属性）。

```
┌─ 工具栏 _build_sc_toolbar() ──────────────────────────────────────────────┐
│ Connect  Pause  Stop  Refresh │ +(Add) −(Remove) │ Sidebar     ⋯  Settings │
├──────────────┬────────────────────────────────────────────────────────────┤
│ 侧栏          │  Serial Log                         🔍 ⧉ ⤓ 💾 🗑 ↧（图标行）│
│ SERIAL CONFIG │  ┌─ 过滤行(默认隐藏) Regex/Case/Invert/Before/After ──────┐ │
│ RX CONFIG     │  │ 日志文本区 _sc_log_edit (QTextEdit)                    │ │
│ TX CONFIG     │  └────────────────────────────────────────────────────────┘ │
│               │  ● Port: ...  Baud rate: -  RX: 0 B  TX: 0 B  (状态栏)       │
│               ├────────────────────────────────────────────────────────────┤
│               │  [ Inject command... ▾ ]                          [ Send ]   │
│               ├────────────────────────────────────────────────────────────┤
│               │  ⚡Quick Commands │ 📄Scripts        (底部 Tab)              │
│               │  ...                                                          │
└──────────────┴────────────────────────────────────────────────────────────┘
```

### 5.1 工具栏 `_build_sc_toolbar()`（行 1086，`QFrame` 固定高 48）
| 控件属性 | 文本/图标 | 说明 |
|---|---|---|
| `_sc_connect_btn` | Connect | 连接 / 断开切换（绿色高亮）|
| `_sc_pause_btn` | Pause | 可勾选，暂停日志刷新 |
| `_sc_stop_btn` | Stop | 停止 |
| `_sc_refresh_btn` | Refresh | 刷新串口列表 |
| —（分隔符 VLine）| | |
| `_sc_add_log_btn` | + | 新增 LOG 分屏面板（28×28）|
| `_sc_remove_log_btn` | − | 移除当前 LOG 面板（默认禁用）|
| —（分隔符 VLine）| | |
| `_sc_sidebar_toggle_btn` | Sidebar | 可勾选，折叠/展开左侧栏 |
| —（`addStretch` 弹性）| | |
| `_sc_settings_btn` | Settings | 打开完整设置对话框 |

### 5.2 主体水平分割 `body_splitter (QSplitter.Horizontal)`
- 左：`_sc_sidebar_widget = _build_sc_sidebar()`（默认宽 250，最小 237，最大 298，可折叠）
- 右：`center_widget` → `center_splitter (QSplitter.Vertical)`

### 5.3 左侧栏 `_build_sc_sidebar()`（行 1188，`QScrollArea` 内三段卡片）

每段用 `_make_sc_section(title, icon)` 生成带标题的卡片。

**① SERIAL CONFIG `_build_sc_section_port_settings()`（行 1223）** — `QGridLayout`：
| 控件 | 内容 |
|---|---|
| `_sc_port_combo` | Port 端口下拉 |
| `_sc_baud_combo` | Baudrate（921600/1152000/2000000/3000000/Custom，可编辑）|
| `_sc_auto_detect_cb` | Auto-Detect（勾选后波特率框禁用）|
| `_sc_databit_combo` | Data bits（8/7/6/5）|
| `_sc_flow_combo` | Flow Control（None/RTS·CTS/XON·XOFF）|
| `_sc_stopbit_combo` | Stop bits（1/1.5/2）|
| `_sc_parity_combo` | Parity（None/Even/Odd/Mark/Space）|

**② RX CONFIG `_build_sc_section_rx_settings()`（行 1311）**：
| 控件 | 内容 |
|---|---|
| `_sc_rx_toggle` | Format ASCII/HEX 滑动开关（`_MiniSlideToggle`）|
| `_sc_rx_auto_flush_cb` + `_sc_rx_auto_flush_spin` | Auto Flush + 间隔（ms，默认 50）|
| `_sc_rx_show_time_cb` | Show Time (ms) 时间戳（默认勾选）|

**③ TX CONFIG `_build_sc_section_tx_settings()`（行 1354）**：
| 控件 | 内容 |
|---|---|
| `_sc_tx_toggle` | Format ASCII/HEX 滑动开关 |
| `_sc_ending_combo` | Line Ending（`\r\n`/`\n`/`\r`/`\n\r`/None）|
| `_sc_show_send_cb` | Show Sent Data（默认勾选）|
| `_sc_line_by_line_cb` | Line by Line 逐行发送 |

### 5.4 中央垂直分割 `center_splitter (QSplitter.Vertical)`
默认 sizes `[680, 155]`，拖动后经 400ms 防抖定时器持久化；上部不可折叠。

**上部 `top_section`**

**① 日志区 `_build_sc_log_area()`（行 1403，`QFrame#scLogFrame`）** — 容器为 `_sc_log_container`（`QGridLayout`，支持多面板分屏），主面板自上而下：
- 标题行：`Serial Log` 标题 + 弹性 + 图标按钮组
  | 控件 | 图标 | 说明 |
  |---|---|---|
  | `_sc_filter_btn` | 🔍 filter | 可勾选，展开/收起过滤行 |
  | `_sc_copy_btn` | ⧉ copy | 复制全部日志到剪贴板 |
  | `_sc_export_btn` | ⤓ export | 导出为文件 |
  | `_sc_save_btn` | 💾 save | 可勾选，落盘并持续追加 |
  | `_sc_clear_btn` | 🗑 trash | 清空日志 |
  | `_sc_scroll_lock_btn` | ↧ auto-scroll | 可勾选（默认开，绿色），自动滚到底 |
- 过滤行 `_sc_filter_row`（默认隐藏）：`_sc_filter_input`（关键字/正则）、`_sc_filter_match_label`（匹配计数）、`_sc_filter_regex_cb` Regex、`_sc_filter_case_cb` Match Case、`_sc_filter_invert_cb` Invert、`_sc_filter_before_spin` Before N lines、`_sc_filter_after_spin` After N lines。
- 日志文本：`_sc_log_edit`（`QTextEdit` 只读，`maximumBlockCount=5000`）。
- **状态栏 `_build_sc_status_bar()`（行 2047，嵌在此处底部）**：`_sc_status_port_label`（Port）、`_sc_status_baud_label`（Baud rate bps）、`_sc_status_rx_label`（RX 字节）、`_sc_status_tx_label`（TX 字节）、`_sc_status_autobaud_label`（自动波特率，默认隐藏）。

**② 发送区 `_build_sc_send_area()`（行 1614）**：`_sc_history_combo`（`SerialHistoryComboBox`，可编辑、↑↓ 调历史，内部 `_sc_send_input` 为其 lineEdit）+ `_sc_send_btn`（Send）。

**下部 快捷指令/脚本区 `_build_sc_quick_commands()`（行 1652，最小高 150）**
`QTabWidget#scBottomTabs`，两个 Tab：

- **Quick Commands Tab `_build_sc_qc_tab()`（行 1695）**
  - header：⚡图标 + `_sc_qc_project_tabs`（`_ProjectTabBar` 项目标签栏，末尾内置 `+` 加号 tab，支持右键菜单 + 拖拽排序）
  - 工具栏：`Group:` 标签 + `_sc_qc_group_combo`（分组下拉）+ `_sc_qc_new_group_btn`（+ Group）+ `_sc_qc_group_edit_btn`（编辑分组）+ `_sc_qc_group_delete_btn`（删除分组）+ 弹性 + `_sc_qc_add_btn`（+ Add 蓝色主按钮）+ `_sc_qc_import_btn`（Import）+ `_sc_qc_export_btn`（Export）
  - 按钮区：`_sc_qc_btn_scroll`（`QScrollArea`）内 `_sc_qc_btn_container` + `_sc_qc_btn_layout`（`QGridLayout`），放置可拖拽的 `_QuickCmdButton` 快捷指令按钮（截图中的 test1 / test2）

- **Scripts Tab `_build_sc_script_tab()`（行 1854）**
  - 工具栏：`Run File:` + `_sc_script_combo`（脚本下拉）+ `_sc_script_run_btn`（Run）+ `_sc_script_stop_btn`（Stop，默认禁用）+ `_sc_script_loop_cb`（Loop）+ `_sc_script_loop_spin`（循环次数）+ 弹性 + `_sc_script_new_btn`（New）/`_sc_script_edit_btn`（Edit）/`_sc_script_del_btn`（Delete）/`_sc_script_import_btn`（Import）/`_sc_script_export_btn`（Export）
  - 状态行：`_sc_script_status_dot`（状态点）+ `_sc_script_status_label`（Status: Idle）+ 弹性 + `_sc_script_count_label`（步骤数）
  - 步骤表 `_sc_script_table`（`QTableWidget` 6 列：`# / Command / Priority / Wait(ms) / Status Condition / Actions`）+ `_sc_script_add_step_btn`（+ Add Sequence Step Directive），整体包在 `_sc_script_body_scroll` 可滚动区内

---

## 6. SerialComMixin 方法分组（约 200 个方法）

| 分组 | 前缀 | 代表方法 |
|---|---|---|
| 简易连接组件 | `init_serial_connection` / `build_serial_connection_widgets` | 三种 MODE 的精简串口连接 UI |
| 简易连接逻辑 | `_on_serial_*` | 搜索 / 连接 / 断开 / 设置 / 读线程 |
| 完整页面构建 | `_build_sc_*` | toolbar / sidebar / 各 section / log / send / quick / status |
| 连接控制 | `_sc_on_connect_toggle` / `_sc_do_connect` / `_sc_do_disconnect` | 主控制台连接 |
| 自动波特率 | `_sc_*auto_baud*` / `_sc_*auto_detect*` | 调 `core.auto_baud_detector` 扫描与监测 |
| 日志面板 | `_sc_*log_panel*` / `_build_extra_log_panel` / `_sc_extra_panel_*` | 多面板增删、独立窗口、分屏 |
| 过滤 | `_sc_*filter*` | 关键字 / 正则 / 大小写 / 反选 / 上下文行高亮 |
| 保存 / 导出 | `_sc_*save*` / `_sc_export_logs` / `_sc_*temp_log*` / `_sc_*auto_save*` | 手动保存、临时日志、自动落盘 |
| 收发 | `_sc_on_send` / `_sc_on_data_received` / `_sc_append_log` | 含 100ms 批量刷新（`_sc_flush_pending_logs`）|
| 脚本 | `_sc_script_*` | 脚本步骤、循环、超时等待关键字、执行流 |
| 快捷指令 | `_sc_qc_*` / `_sc_send_quick` | 项目 / 分组 / 按钮、拖拽排序、导入导出 |
| NTP 时间 | `_sc_*ntp*` | 时间戳校时（`_NtpSyncWorker` 线程）|
| 持久化 | `_sc_*persisted*` / `_sc_collect/apply_*state` | 用户配置 JSON 读写、窗口几何、迁移旧配置 |
| 多会话 | `send_to_session` / `broadcast_send` / `send_to_active_session` | 委托 `SerialSessionManager` |

---

## 7. 文件内辅助类清单

| 类 | 基类 | 职责 |
|---|---|---|
| `_SerialSearchButton` | `QPushButton` | 带旋转动画的搜索按钮 |
| `_SearchSerialPortWorker` | `QObject` | 后台枚举串口（线程内运行）|
| `_MixinSerialSettingsDialog` | `QDialog` | 简易模式串口参数对话框 |
| `SerialComMixin` | — | 业务逻辑混入主体 |
| `_MiniSlideToggle` | `QWidget` | ASCII/HEX 等小型滑动开关 |
| `_AddLogPanelDialog` / `_PanelSettingsDialog` | `QDialog` | 新增 / 配置日志面板 |
| `_IndependentSerialWindow` | `QWidget` | 独立弹出的串口监视窗 |
| `_QuickCmdPreviewPopup` / `_QuickCmdButton` | `QFrame` / `QPushButton` | 快捷指令预览气泡与可拖拽按钮 |
| `_ProjectTabBar` | `QTabBar` | 支持拖拽重排的项目标签栏 |
| `_QuickCommandPickerPopup` | `QFrame` | 快捷指令选择弹窗（树形）|
| `_SerialScriptStepDialog` / `_SerialScriptEditorDialog` | `QDialog` | 脚本步骤 / 脚本编辑 |
| `_QuickTextInputDialog` / `_QuickCmdDialog` | `QDialog` | 文本输入 / 快捷指令编辑 |
| `_SerialSaveDialog` | `QDialog` | 日志保存配置 |
| `_SerialSettingsDialog` | `QDialog` | 完整设置（Serial/RX/TX/Log/Display/Auto-Detect/About 多标签）|
| `_NtpSyncWorker` | `QObject` | NTP 校时后台线程 |
| `_SerialReadWorker` | `QObject` | 简易模式串口读线程 |

---

## 8. 线程模型（遵守 UI 不阻塞铁律）

| 线程 Worker | 信号 | 用途 |
|---|---|---|
| `_SearchSerialPortWorker` | `finished(list)` / `error(str)` | 枚举串口 |
| `_SerialReadWorker` | 数据 / 错误信号 | 简易模式读串口 |
| `_SessionReadWorker`（`serial_session.py`）| `data_received` / `read_error` | 多会话读串口 |
| `_NtpSyncWorker` | `synced(offset,rtt)` / `failed(reason)` | NTP 校时 |
| `core.auto_baud_detector.AutoBaudScanWorker` | 进度 / 结果信号 | 自动波特率扫描 |

> 所有串口 IO 都在子线程，UI 通过 Signal/Slot 接收；日志渲染用 100ms 批量刷新定时器降低重绘开销。

---

## 9. 会话层（多串口）

```
SerialSessionManager (QObject)
  ├── sessions: dict[str, SerialSession]
  ├── active_session_id
  ├── create_session / remove_session / set_active_session
  ├── send_to_session / send_to_active_session / broadcast_send
  ├── connect_session / disconnect_session / disconnect_all
  └── to_config / load_config           # 持久化

SerialSession (QObject)
  ├── 属性：session_id / display_name / port / baudrate / connected / rx_bytes / tx_bytes
  ├── configure / connect_port / disconnect_port / send / reset_counters
  ├── _start_read / _stop_read → _SessionReadWorker(QThread)
  └── to_config / from_config / cleanup
```

`SerialComMixin.init_serial_connection()` 内创建 `_sc_session_manager`，并把其 `_sessions` 共享给 `_sc_sessions`。

---

## 10. 持久化与配置

- 用户配置目录：`_sc_user_config_dir()`，主路径 `_sc_persisted_path()`，回退 `_sc_fallback_path()`。
- 落盘内容：快捷指令、脚本、窗口几何、分割器尺寸、RX/TX/Log/Display/Auto-Detect 设置。
- `_sc_migrate_legacy_config()` 处理旧版本配置迁移。
- 关闭时 `closeEvent` → `_sc_save_persisted_state()` + `close_serial()` + 关闭独立窗口。

---

## 11. 外部依赖

| 依赖 | 用途 |
|---|---|
| `pyserial`（`serial`, `serial.tools.list_ports`）| 串口收发与枚举 |
| `core.auto_baud_detector` | 自动波特率检测（状态机 / 监测 / 扫描）|
| `log_config.get_logger` | 统一日志（禁 `print`）|
| `debug_config.DEBUG_MOCK` | Mock 调试开关 |
| `ui.utils.icon_utils` | SVG 着色图标 |
| `ui.resource_path.get_resource_base` | 资源根路径（兼容打包）|

资源目录：`resources/modules/SVG_Common`、`SVG_Serial`、`SVG_Logs`。

---

## 12. 独立运行入口（文件底部 `__main__`）

- `_DemoCompleteSerialWidget(SerialComMixin, QWidget)`：演示 / 独立程序容器。
- 安装自定义 Qt 消息处理器过滤无害 `QPainter::end` 警告。
- `QApplication` + Fusion 风格 + `serialcom_module.ico` 图标。
- 还原窗口几何，支持最大化恢复。

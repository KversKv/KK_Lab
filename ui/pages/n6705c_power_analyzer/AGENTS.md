# ui/pages/n6705c_power_analyzer — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../../AGENTS.md) 与 [ui/pages/AGENTS.md](../AGENTS.md) 硬红线。

## 加载指针（AI 按需拉取）

- **N6705C Datalog 使用** → [n6705c_datalog_ui_usage.md](./n6705c_datalog_ui_usage.md)
- **Datalog 解析 / 写盘** → [instruments/power/keysight/n6705c_datalog_process.py](../../../instruments/power/keysight/n6705c_datalog_process.py)
- **巨石重构（本页拆分背景）** → @see ADR [005-monolith-refactor](../../../docs/ai/decisions/005-monolith-refactor.md)

## 本模块职责与边界

- **职责**：N6705C 电源分析仪控制（通道电压/电流、批量、功耗）+ Datalog 长时采集与波形分析。
- **上游**：`ui/main_window.py`；**下游**：`core/n6705c/` Worker（QThread 无 QtWidgets）、`instruments/factory`。
- **铁律**：UI 仅交互；采集 / 同步走 `core/n6705c/*_worker.py`。

## 接口契约（对外不可破坏）

- `N6705CTop`（[n6705c_top.py](./n6705c_top.py)）：**双台仪器 A/B** 连接状态共享中枢，供多页注入。
- 主壳 [n6705c_analyser_ui.py](./n6705c_analyser_ui.py)：状态机 / 连接 / 通道切换 / 装配；视图拆分为 `analyser_view_setting / analyser_view_batch / analyser_view_consumption` Mixin + `widgets.py`。
- `N6705CDatalogUI`：可独立运行（`python n6705c_datalog_ui.py`）或 `N6705CDatalogUI(n6705c_top=...)` 嵌入同步连接。
- **一键截图钩子 `get_capture_pixmap()`**（MainWindow 降级链最高优先级）：`chart_frame` + `measurement_card` 纵向合成（gap 6 与 `chart_and_meas_layout` 一致，底色 #020817）；改布局间距 / 页面底色需同步。
- **导出波形摘要钩子 `get_waveform_summary_pixmap()`**：与 AI 摘要同源（LTTB→PELT 变点 + `classify_segment` 标注，最低电平带归「基线」）把波形压成平直线段示意图（标注 S1..Sn）+ 阶段汇总表（持续时长/平均电流），QPainter 直绘 #020817 底图；入口为 `_StandaloneTitleBar.summary_button`（一键截图右侧 `#waveformSummaryBtn`，图标 `activity.svg`）→ `_on_export_waveform_summary` → 剪贴板；分段/渲染为模块级函数 `_build_summary_stages` / `_render_waveform_summary_image`。
- **Datalog 页布局骨架**：`content_layout`（QHBox）= 左窄边栏 `left_rail`（单图标 rail：`rail_settings_btn` / `rail_instrument_btn`，`#railIconBtn`）+ `left_panel_host`（`settings_panel` 240（DATALOG CONFIG + Measurement Settings 合并）与 `instrument_panel` 360 **互斥单开**，一切切换/收起统一走 `_show_left_panel(which)`，全收起仅剩 rail；未连接时默认展开仪器面板、已连接全收起）+ `main_area`（QVBox：`mid_layout` 居上 = `center_col_layout`（chart+meas 居上、Channel Config 居下，二者强制同宽）+ 右 `label_card` 侧栏（通高）；`bottom_bar` 居下 = Start/Export/Import 靠左（QSS 钉总高 34px，Export/Import 仅图标 34×34 带 ToolTip）+ 设置齿轮靠右（弹 `N6705CSettingsDialog` 五标签设置对话框））；Channel Config 禁再挂回 `main_area`（会拉通全宽）。
- **设置对话框 [n6705c_settings_dialog.py](./n6705c_settings_dialog.py)**：五标签页 Instruments（默认仪器增/改/删 + 每台/全局自动连接，经 `apply_instrument_settings(devices, auto_connect_enabled)` 与设备卡片联动，busy 卡仅更新 auto_connect 不删不改地址；`is_instrument_busy(serial, resource)` 判忙）/ Network Scan（`core.n6705c.search_worker.save_extra_subnets` 写 discovery.json）/ DLog Save（录制正常结束 `_maybe_auto_save_dlog` 自动写 .dlog，`_recording_had_error` 出错路径跳过；命名模板占位符 `{date}/{time}/{datetime}/{seq}`，递增序号落盘 next_seq）/ Waveform Summary（事件算法写 `AISettings.waveform_event_algo/params`；max_stages/lttb_threshold/pelt_max_n 写 datalog_settings.json，`_build_summary_stages` 经 `waveform_summary_params()` 读取）/ About（版本、配置目录、RESET JSON 还原默认）。本页设置存 `user_data/n6705c/datalog_settings.json`（`load/save_datalog_app_settings`）；对话框不 import 主页面模块，仅持引用调公共方法防循环依赖。
- **Custom Labels 显隐契约**：唯一入口 `set_labels_panel_visible(visible)` + 信号 `labels_panel_toggled(bool)` + 查询 `is_labels_panel_visible()`（`isHidden` 反判，suite 切页父链暂隐不丢态）；三处标题栏在一键截图右侧以分割线（`#titleBarSeparator`）+ `#labelsToggleBtn` 接入——独立 `_StandaloneTitleBar`（常显）、套件 `_SuiteTitleBar`（仅 standalone 且 Datalog 页签）、MainWindow `AppTopBar`（仅 datalog 页，`_sync_labels_toggle_button` 随 `_sync_compact_view_button` 同点调用）；页面内不再放切换按钮。
- **独立运行入口是 `_StandaloneDatalogWindow`**（文件尾部，`__main__` 勿直接实例化 `N6705CDatalogUI`）：无边框 + `_StandaloneTitleBar` 自建标题栏（含一键截图按钮），nativeEvent 方案与 [ui/main_window.py](../../main_window.py) 一致（WM_NCCALCSIZE→0 + WM_NCHITTEST 边框缩放 + HTCAPTION 拖动）。
- **套件入口 `N6705CSuiteWindow`**（[n6705c_suite_ui.py](./n6705c_suite_ui.py)）：无边框 + 标题栏内嵌页面切换 tab，`QStackedWidget` 承载多页；页面注册表 `_SUITE_PAGES`（key/标题/类），新增界面只追加注册项；全部子页注入同一 `N6705CTop` + `InstrumentManager`；关闭时逐页 `sendEvent(QCloseEvent)` 复用子页清理（嵌入态 `isWindow()=False`，datalog 几何记忆保存空转不污染）。
  - `standalone=True` 独立运行（`python n6705c_suite_ui.py`）；`standalone=False` 嵌入 MainWindow——N6705C 为**一级菜单**（无二级子菜单），标题栏仅留 tab，子页经 `analyser_page` / `datalog_page` 暴露给 MainWindow 既有引用（compact / AI 回调 / 截图链），tab 切换经 `page_changed` 信号同步 `current_instrument_ui`。
  - 注意：MainWindow 首页装载即构造两子页，datalog 的 auto_connect 启动即触发（原懒加载为首次切换才触发）。
- `set_compact_mode(compact: bool)`（主壳对外方法）：主窗口顶栏「最小视图」按钮调用——True 时隐藏页面 top_bar / 通道区 / 功耗区，仅留 Quick Setup（`batch_tools_panel`，收起态自动展开），并隐藏折叠头、归零区块间距、收窄页边距（配合 main_window `_COMPACT_VIEW_SIZE=(600,200)`）；False 恢复。命名与语义不可改（[main_window.py](../../main_window.py) `_on_compact_view_toggled` 依赖）。

## 局部约定

- **通道标签用 QPushButton 模拟 tab**：active / inactive / disabled 的 `padding / border / margin` **盒模型必须一致**（见 03§25）；视觉连接用同背景色 `border-bottom`，**禁 `border-bottom: none`**（否则切到末位 tab 内容偏移几像素）。参考 `_build_channel_tab_style`。
- **可编辑数值输入框统一用 `widgets.SelectAllLineEdit`**（实现已沉淀为 [ui/widgets/wheel_line_edit.py](../../widgets/wheel_line_edit.py) `WheelLineEdit` 的兼容别名）：双击全选（Qt 默认按"词"选择、小数点算分隔符，`3.8000` 双击只选中 `8000`）+ 滚轮调值（默认步进 0.01，`set_wheel_step(1)` 用于整数秒/微秒字段，置 `None` 禁用；仅聚焦时生效，未聚焦事件传父级不影响页面滚动）。只读显示字段（大字号 value）仍用普通 `QLineEdit`。
- 单位显示：内存值统一 mA/mV/mW；`_format_value(value_mA)` 显示时 SI 选档。
- 通道同步经 `core/n6705c/channel_sync_worker.py` 周期回读。

## 局部坑点

- **Datalog 连接管理三律**：① 连接/断连/刷新收尾统一走 `_after_slot_states_synced`（槽位签名去重，禁止绕过重发 `connection_status_changed` 或直调 `_refresh_channel_config`）；② 并发连接用 `_pending_connects`（slot→resource）守卫，`_find_next_free_slot` 必须跳过 pending 槽；③ manager 的 `connection_failed` **不发** `sessions_changed`，必须单独监听恢复卡片按钮态，否则按钮卡死 "Connecting..."；session 被他页 `remove_session` 移除时靠 `_on_manager_sessions_changed` 对账清理。
- **签名必须含 pending**：manager 连接成功先发 `session_connected`（→ top → `_sync_from_top` 抢跑收尾）后发 `sessions_changed`（→ 对账清 pending）；`_after_slot_states_synced` 签名若不含 `_pending_connects`，pending 清除时被去重跳过，设备卡片永久卡 "Connecting..."（suite 双页同建场景实踩）。
- **§25 Tab 盒模型坑**：见上"局部约定"第一条，是本页踩过的真实坑。
- **窗口几何恢复禁按 margin 压尺寸**：`_clamped_window_geometry` 只允许"超出可用区域才截断"（`min(saved, available)`）；若按 `可用宽-40` 预留 margin，Windows 吸附 1/2 屏（宽=整屏）后重开会被压小，150% DPI 下右侧出现 60 物理 px 空白。`_WINDOW_MARGIN` 仅用于默认窗口尺寸。
- Datalog 导出是二进制+CSV 混合，**不要重复造解析轮子**，用 instruments 层 datalog_process。
- **面板显隐门禁用 `isHidden()` 反判，禁用 `isVisible()`**：本页嵌在 suite/MainWindow 的 `QStackedWidget` 里，启动自动连接完成时本页常非当前页，`isVisible()` 受祖先隐藏影响恒为 False 会跳过折叠/显隐联动；判"面板是否展开"必须用 `not xxx.isHidden()`（仅看自身显式标志）。
- 波形单位事实源在 `n6705c_datalog_process.py`（`parse_channel_label` 等），勿在 UI 另写推断。
- Datalog Viewer 轴/网格约定：横轴经 `_update_x_limits()` 用 `vb.setLimits(xMin/xMax/maxXRange)` 约束在含对齐时差的数据范围（`maxXRange` 必设，否则窗口比数据宽时 clamp 失效仍露出负时间区）；左轴不显示数值（`setWidth(0)` + `setTicks([])`），各通道 band 高度均分（`_compute_band_edges(n)` 为 band 几何唯一入口），band 间无分隔线，纵轴网格线 8 格均分整个图表区域纵向高度（`_rebuild_band_grid_lines` 建线、`_update_grid_line_positions` 挂 `_on_range_changed` 随可见 Y 范围实时重定位，与 band 划分无关），具体数值读数看右侧通道面板 Scale/Offset；每通道纵向 0 刻度线由 `_update_band_zero_lines()` 维护（0 落在当前量程内才显示，z=-9 勿盖过波形），raw 映射变动路径（拖动/滚轮/Scale 编辑）必须调用。
- **十字预览线残留**：`sigMouseMoved` 经 `SignalProxy(rateLimit=30)` 会延迟投递最后一个移动事件（慢速移出光标时在 `QEvent.Leave` 隐藏之后才触发，预览线被重新点亮）；`_on_mouse_moved` 必须以 `QCursor.pos()` 实时判定光标是否在控件内，不能信事件坐标。
- MEASUREMENT 卡无独立标题行：图标+标题写在结果表左上角表头单元格（`_apply_meas_corner_title`，两处 `setHorizontalHeaderLabels` 后必须重调），卡片纵向边距 (14,2,14,6)。
- **纯 QWidget 自建标题栏 QSS 背景不生效**：正常 paint 路径下纯 `QWidget` 不绘制 QSS `background-color`（透出父级底色；`grab()` 离屏渲染却会绘制，易被误导），必须 `setAttribute(Qt.WA_StyledBackground, True)`（`_StandaloneTitleBar` 已处理；`ui/app_top_bar.py` 因背景色与页面相近未暴露，改色时需同样处理）。
- **Channel Config 高度须随内容收缩**：`_instruments_tab` 禁设固定 `setMinimumHeight`（内容变矮时多余高度会回灌各行、撑宽标题行与单元格间距）；Active 页签布局末尾必须保留 `addStretch()` 收口袋（导入页签已有），残余空间沉底而非均分回行。
- **行内混排控件纵向策略须一致**：QLineEdit 默认纵向 Fixed，与 ToggleLabel(min 24) 同行时行高由大者决定、Fixed 控件短一截，相邻行间距视觉差出高度差；`ScaleOffsetEdit`（及导入页签占位 QLineEdit）已设纵向 `Expanding` 随行高拉伸，新增同类行内输入框须同样处理。
- **Channel Config 右缘防"双线"**：整行最末槽的最末通道单元格用 `OUT_FRAME_LAST_STYLE`（去右边框），其余单元格用 `OUT_FRAME_STYLE`；导入页签行尾有 addStretch 单元格不贴右缘，无需处理。左侧 rail 按钮 `#railIconBtn` 总尺寸 20px（content 18 + border 2）；rail 图标用 `_make_svg_icon(..., 16, zoom=1.15)` 放大裁掉 Feather SVG 内建留白（zoom 1.25 会削掉 link-connect 圆弧端点，禁超 1.15）。
- **固定高输入框的控件级样式必须自带完整盒模型**：本页全局 `QLineEdit { padding: 6px 10px; border: 1px }`，24px 固定高输入框内容区仅剩 10px，数字底部截断；`setStyleSheet` 只设颜色不设 padding/font/border 会级联回全局同样截断。参考 `SAMPLE_PERIOD_EDIT_STYLE / SAMPLE_PERIOD_READONLY_STYLE`（padding 2px 4px + font 11px 全套）。

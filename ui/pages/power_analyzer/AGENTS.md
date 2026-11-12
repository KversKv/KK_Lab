# ui/pages/power_analyzer — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../../AGENTS.md) 与 [ui/pages/AGENTS.md](../AGENTS.md) 硬红线。

## 加载指针（AI 按需拉取）

- **N6705C Datalog 使用** → [power_analyzer_datalog_ui_usage.md](./power_analyzer_datalog_ui_usage.md)
- **Datalog 解析 / 写盘** → [instruments/power/keysight/n6705c_datalog_process.py](../../../instruments/power/keysight/n6705c_datalog_process.py)
- **巨石重构（本页拆分背景）** → @see ADR [005-monolith-refactor](../../../docs/ai/decisions/005-monolith-refactor.md)

## 本模块职责与边界

- **职责**：N6705C / IT2705 通用电源控制（通道电压/电流、批量、功耗）+ Datalog 长时采集与波形分析；用户可见名称为 `Power Control`，保留 `n6705c` 内部键与会话 ID。
- **上游**：`ui/main_window.py`；**下游**：`core/n6705c/` Worker（QThread 无 QtWidgets）、`instruments/factory`。
- **铁律**：UI 仅交互；采集 / 同步走 `core/n6705c/*_worker.py`。

## 接口契约（对外不可破坏）

- `N6705CTop`（[power_analyzer_top.py](./power_analyzer_top.py)）：**双台仪器 A/B** 连接状态共享中枢，供多页注入；连接统一经 `instruments/factory.py` 按 `*IDN?` 识别 N6705C / IT2705，页面显示真实型号。
- **通道事实源**：实例 `VALID_CHANNELS`；N6705C 回退 1–4，IT2705 为 1–8。Channel Tabs / Batch / Consumption / Datalog Channel Config 均按实际通道动态重建。
- **模块门禁**：连接后由 factory 刷新 `channel_module_models`，页面统一用 `is_channel_supported(ch)`；N6705C 仅 N6781A/N6784A、IT2705 仅 IT27814/IT27814E 可用，空槽/未知/查询失败的通道在 Channel Tabs / Batch / Consumption / Datalog Active 中直接隐藏，且不得恢复勾选或参与采集；内部列表保留完整物理通道索引。
- **Datalog 双路径**：N6705C 保留原生 DLOG 配置、等待、下载与解析；IT2705 走 **ELOG 外部记录仪**（`it2705.configure_elog/start_elog/fetch_elog_records/stop_elog`，仪器按 PER 真实采样最低 20us，采集循环每 0.2s 流式 `FETC:ELOG?` 回读，V/A 转 mV/mA，时间轴=记录序号×PER），不伪造原始 `.dlog`；混合连接时原生等待与 ELOG 流式回读同循环并行。**数据 key 前缀随连接形态**：A 单机无前缀（`CH1 V`），B 单机 / 双机带槽位前缀（`B CH1 V` / `A CH1 V`）；门禁 / P 计算 / 时间偏移一律按 `_parse_ch_label` 反推（P 计算前缀见 `n6705c_datalog_process._unit_prefix_for_ch`），禁硬编码 `""` / `"B"`。
- 主壳 [power_analyzer_analyser_ui.py](./power_analyzer_analyser_ui.py)：状态机 / 连接 / 通道切换 / 装配；视图拆分为 `analyser_view_setting / analyser_view_batch / analyser_view_consumption` Mixin + `widgets.py`。
- `N6705CDatalogUI`：可独立运行（`python power_analyzer_datalog_ui.py`）或 `N6705CDatalogUI(n6705c_top=...)` 嵌入同步连接。**实现已拆分至 [datalog/](./datalog/) 子包**：主壳 `datalog/datalog_ui.py`（信号/状态/初始化）+ `view_connection / view_layout / view_channel_config / view_plot / view_recording / view_markers / view_labels / view_time_offset / view_import_export` 九个视图 Mixin + `helpers / widgets / workers / standalone`；`power_analyzer_datalog_ui.py` 仅作兼容入口（re-export + `__main__` + 打包入口），改功能请进子包对应模块。
- **一键截图钩子 `get_capture_pixmap()`**（MainWindow 降级链最高优先级）：`chart_frame` + `measurement_card` + `channel_config_outer` 纵向合成（gap 6 与布局行间距一致，底色 #020817，DPR 随 `grab()`）；改布局间距 / 页面底色需同步。
- **导出波形摘要钩子 `get_waveform_summary_pixmap()`**：与 AI 摘要同源（LTTB→PELT 变点 + `classify_segment` 标注，最低电平带归「基线」）把波形压成平直线段示意图（标注 S1..Sn）+ 阶段汇总表（持续时长/平均电流），QPainter 直绘 #020817 底图；入口为 `_StandaloneTitleBar.summary_button`（一键截图右侧 `#waveformSummaryBtn`，图标 `activity.svg`）→ `_on_export_waveform_summary` → 剪贴板；分段/渲染为模块级函数 `_build_summary_stages` / `_render_waveform_summary_image`。
- **Datalog 页布局骨架**：`content_layout`（QHBox）= 左窄边栏 `left_rail`（单图标 rail：`rail_settings_btn` / `rail_instrument_btn`，`#railIconBtn`）+ `left_panel_host`（`settings_panel` 240（DATALOG CONFIG + Measurement Settings 合并）与 `instrument_panel` 360 **互斥单开**，一切切换/收起统一走 `_show_left_panel(which)`，全收起仅剩 rail；未连接时默认展开仪器面板、已连接全收起）+ `main_area`（QVBox：`mid_layout` 居上 = `center_col_layout`（chart+meas 居上、Channel Config 居下，二者强制同宽）+ 右 `label_card` 侧栏（通高）；`bottom_bar` 居下 = Start/Export/Import 靠左（QSS 钉总高 34px，Export/Import 仅图标 34×34 带 ToolTip）+ 设置齿轮与帮助按钮靠右（齿轮弹 `N6705CSettingsDialog` 五标签设置对话框；问号 `bottom_help_btn` 复用 `#bottomSettingsBtn` 样式弹 `DatalogHelpDialog`））；Channel Config 禁再挂回 `main_area`（会拉通全宽）。
- **帮助系统 [power_analyzer_datalog_help.py](./power_analyzer_datalog_help.py)**：手册存 [helps/datalog.html](../../../helps/datalog.html)（`load_datalog_help_html` 读取，n6705c_datalog.spec 已打包 helps/）；`DatalogHelpDialog`（exec 返回 `GUIDE_REQUESTED` 时页面启动引导）；`GuideTourOverlay(host, steps)` 通用引导层（遮罩镂空高亮 + 气泡卡片，步骤 dict 含 target/title/text/on_enter，Esc/跳过/完成均发 `finished`）；入口 `_on_open_help_dialog` / `_start_guide_tour`（11 步，面板经 `_show_left_panel` 联动，结束恢复原面板态）。
- **🔴 功能变更同步义务**：新增 / 改动本页功能，必须主动同步维护 [helps/datalog.html](../../../helps/datalog.html) 帮助手册与 `_start_guide_tour` 引导步骤。
- **设置对话框 [power_analyzer_settings_dialog.py](./power_analyzer_settings_dialog.py)**：五标签页 Instruments（默认仪器增/改/删 + 每台/全局自动连接，经 `apply_instrument_settings(devices, auto_connect_enabled)` 与设备卡片联动，busy 卡仅更新 auto_connect 不删不改地址；`is_instrument_busy(serial, resource)` 判忙；LAN=HiSLIP，IT2705 等无 HiSLIP 服务设备选 Socket+端口，如 `TCPIP0::ip::30000::SOCKET`）/ Network Scan（`core.n6705c.search_worker.save_extra_subnets` 写 discovery.json）/ DLog Save（录制正常结束 `_maybe_auto_save_dlog` 自动写 .dlog，`_recording_had_error` 出错路径跳过；命名模板占位符 `{date}/{time}/{datetime}/{seq}`，递增序号落盘 next_seq）/ Waveform Summary（事件算法写 `AISettings.waveform_event_algo/params`；max_stages/lttb_threshold/pelt_max_n 写 datalog_settings.json，`_build_summary_stages` 经 `waveform_summary_params()` 读取）/ About（版本、配置目录、RESET JSON 还原默认）。本页设置存 `user_data/n6705c/datalog_settings.json`（`load/save_datalog_app_settings`）；对话框不 import 主页面模块，仅持引用调公共方法防循环依赖。
- **Custom Labels 显隐契约**：唯一入口 `set_labels_panel_visible(visible)` + 信号 `labels_panel_toggled(bool)` + 查询 `is_labels_panel_visible()`（`isHidden` 反判，suite 切页父链暂隐不丢态）；三处标题栏在一键截图右侧以分割线（`#titleBarSeparator`）+ `#labelsToggleBtn` 接入——独立 `_StandaloneTitleBar`（常显）、套件 `_SuiteTitleBar`（仅 standalone 且 Datalog 页签）、MainWindow `AppTopBar`（仅 datalog 页，`_sync_labels_toggle_button` 随 `_sync_compact_view_button` 同点调用）；页面内不再放切换按钮。
- **独立运行入口是 `_StandaloneDatalogWindow`（[datalog/standalone.py](./datalog/standalone.py)，`__main__` 勿直接实例化 `N6705CDatalogUI`）**：无边框 + `_StandaloneTitleBar` 自建标题栏（含一键截图按钮），nativeEvent 方案与 [ui/main_window.py](../../main_window.py) 一致（WM_NCCALCSIZE→0 + WM_NCHITTEST 边框缩放 + HTCAPTION 拖动）。
- **套件入口 `N6705CSuiteWindow`**（[power_analyzer_suite_ui.py](./power_analyzer_suite_ui.py)）：无边框 + 标题栏内嵌页面切换 tab，`QStackedWidget` 承载多页；页面注册表 `_SUITE_PAGES`（key/标题/类），新增界面只追加注册项；全部子页注入同一 `N6705CTop` + `InstrumentManager`；关闭时逐页 `sendEvent(QCloseEvent)` 复用子页清理（嵌入态 `isWindow()=False`，datalog 几何记忆保存空转不污染）。
  - `standalone=True` 独立运行（`python power_analyzer_suite_ui.py`）；`standalone=False` 嵌入 MainWindow——Power Control 为**一级菜单**（无二级子菜单），标题栏仅留 tab，子页经 `analyser_page` / `datalog_page` 暴露给 MainWindow 既有引用（compact / AI 回调 / 截图链），tab 切换经 `page_changed` 信号同步 `current_instrument_ui`。
  - 注意：MainWindow 首页装载即构造两子页，datalog 的 auto_connect 启动即触发（原懒加载为首次切换才触发）。
- `set_compact_mode(compact: bool)`（主壳对外方法）：主窗口顶栏「最小视图」按钮调用——True 时隐藏页面 top_bar / 通道区 / 功耗区，仅留 Quick Setup（`batch_tools_panel`，收起态自动展开），并隐藏折叠头、归零区块间距、收窄页边距（配合 main_window `_COMPACT_VIEW_SIZE=(600,200)`）；False 恢复。命名与语义不可改（[main_window.py](../../main_window.py) `_on_compact_view_toggled` 依赖）。

## 局部约定

- **增删查改功能时必须考虑适配所有仪器**：当前包括 N6705C 与 IT2705，禁止仅适配单一型号。
- **通道配色按槽位仪器实例选择**：IT2705 主色事实源为 `widgets.py::IT2705_CHANNEL_ACCENTS`；Analyser / Consumption / Datalog 统一经实例感知接口取色，禁止全局型号开关或 IT2705 B 槽 `+4` 偏移。
- **通道标签用 QPushButton 模拟 tab**：active / inactive / disabled 的 `padding / border / margin` **盒模型必须一致**（见 03§25）；视觉连接用同背景色 `border-bottom`，**禁 `border-bottom: none`**（否则切到末位 tab 内容偏移几像素）。参考 `_build_channel_tab_style`。
- **可编辑数值输入框统一用 `widgets.SelectAllLineEdit`**（实现已沉淀为 [ui/widgets/wheel_line_edit.py](../../widgets/wheel_line_edit.py) `WheelLineEdit` 的兼容别名）：双击全选（Qt 默认按"词"选择、小数点算分隔符，`3.8000` 双击只选中 `8000`）+ 滚轮调值（默认步进 0.01，`set_wheel_step(1)` 用于整数秒/微秒字段，置 `None` 禁用；仅聚焦时生效，未聚焦事件传父级不影响页面滚动）。只读显示字段（大字号 value）仍用普通 `QLineEdit`。
- 单位显示：内存值统一 mA/mV/mW；`_format_value(value_mA)` 显示时 SI 选档。
- 通道同步经 `core/n6705c/channel_sync_worker.py` 周期回读。
- **Quick Setup 通道同步组**：状态存页面级 `_batch_sync_groups`（dev_label → 通道 set 列表，重建矩阵不丢，断连保留、连接时按可用通道剪枝）；主通道 = 组内序号最小者，从通道电压/限流输入禁用并镜像主通道值；组配色按组索引循环取 `widgets.py::SYNC_GROUP_COLORS`，按钮边框与从通道输入框边框同组同色；覆盖态唯一入口 `_apply_batch_sync_ui()`，必须在 `_apply_dynamic_channel_constraints` 收尾处调用（先于它会被 supported 复位）；`_on_batch_set` 经 `_expand_batch_sync_channels` 整组展开、从通道取主通道值。
- 设定输入的 dirty 跟踪必须用 `textEdited`，禁用 `textChanged`：ConfigMemory 等程序化 `setText` 不应被当作用户编辑而阻断仪器快照回写。

## 局部坑点

- **Datalog 连接管理三律**：① 连接/断连/刷新收尾统一走 `_after_slot_states_synced`（槽位签名去重，禁止绕过重发 `connection_status_changed` 或直调 `_refresh_channel_config`）；② 并发连接用 `_pending_connects`（slot→resource）守卫，`_find_next_free_slot` 必须跳过 pending 槽；③ manager 的 `connection_failed` **不发** `sessions_changed`，必须单独监听恢复卡片按钮态，否则按钮卡死 "Connecting..."；session 被他页 `remove_session` 移除时靠 `_on_manager_sessions_changed` 对账清理。
- **§44 Mixin 同名 Qt 虚函数遮蔽**：`N6705CDatalogUI` 是 QWidget 居首多继承，Mixin 里的 `eventFilter`/`event`/`*Event` 会被 QObject 空实现遮蔽静默失效；`eventFilter` 已在类首显式绑定 `PlotViewMixin.eventFilter`，Mixin 内禁 `super().eventFilter`（MRO 尾段只有 object），不拦截 `return False`。
- **IT2705 ELOG 采样三律**（`datalog/workers.py`）：① 同通道 V/I 来自同一条 ELOG 记录，按记录序号共用时间轴，`calc_power_for_ch` 可配对；② 单次 `fetch_elog_records` 失败仅跳过该批（`_log_sample_failure` kind="ELOG"），禁上抛终止录制；③ `instr.timeout` 长超时（≥600s）仅对原生 DLOG 单元（有 `read_mmem_data`）提升，ELOG 单元保留驱动默认 10s。旧 `measure_*` 软件采样路径已弃用（MEAS 单条 ≥20ms，20us 不可能），仅作无 `fetch_elog_records` 仪器的兜底。Mock 调试卡含 `MOCK::IT2705`（`_add_default_debug_device`）。
- **签名必须含 pending**：manager 连接成功先发 `session_connected`（→ top → `_sync_from_top` 抢跑收尾）后发 `sessions_changed`（→ 对账清 pending）；`_after_slot_states_synced` 签名若不含 `_pending_connects`，pending 清除时被去重跳过，设备卡片永久卡 "Connecting..."（suite 双页同建场景实踩）。
- **§25 Tab 盒模型坑**：见上"局部约定"第一条，是本页踩过的真实坑。
- **窗口几何恢复禁按 margin 压尺寸**：`_clamped_window_geometry` 只允许"超出可用区域才截断"（`min(saved, available)`）；若按 `可用宽-40` 预留 margin，Windows 吸附 1/2 屏（宽=整屏）后重开会被压小，150% DPI 下右侧出现 60 物理 px 空白。`_WINDOW_MARGIN` 仅用于默认窗口尺寸。
- Datalog 导出是二进制+CSV 混合，**不要重复造解析轮子**，用 instruments 层 datalog_process。
- **面板显隐门禁用 `isHidden()` 反判，禁用 `isVisible()`**：本页嵌在 suite/MainWindow 的 `QStackedWidget` 里，启动自动连接完成时本页常非当前页，`isVisible()` 受祖先隐藏影响恒为 False 会跳过折叠/显隐联动；判"面板是否展开"必须用 `not xxx.isHidden()`（仅看自身显式标志）。
- 波形单位事实源在 `n6705c_datalog_process.py`（`parse_channel_label` 等），勿在 UI 另写推断。
- Datalog Viewer 轴/网格约定：横轴经 `_update_x_limits()` 用 `vb.setLimits(xMin/xMax/maxXRange)` 约束在含对齐时差的数据范围（`maxXRange` 必设，否则窗口比数据宽时 clamp 失效仍露出负时间区）；左轴不显示数值（`setWidth(0)` + `setTicks([])`），各通道 band 高度均分（`_compute_band_edges(n)` 为 band 几何唯一入口），band 间无分隔线，纵轴网格线 8 格均分整个图表区域纵向高度（`_rebuild_band_grid_lines` 建线、`_update_grid_line_positions` 挂 `_on_range_changed` 随可见 Y 范围实时重定位，与 band 划分无关），具体数值读数看右侧通道面板 Scale/Offset；每通道纵向 0 刻度线由 `_update_band_zero_lines()` 维护（0 落在当前量程内才显示，z=-9 勿盖过波形），raw 映射变动路径（拖动/滚轮/Scale 编辑）必须调用。
- **Datalog 图表右键菜单唯一入口 = `sigMouseClicked` → `_on_chart_clicked`**（release 时触发，annotation 优先于 marker snap 判定，annotation 菜单由 `PairAnnotationItem.mouseClickEvent` 自弹）：pyqtgraph `GraphicsScene` 在 press 时即记录 clickEvent、release 时**无条件** emit `sigMouseClicked`（`sendClickEvent` 末尾），若同时在 Qt 层 press 事件过滤或 InfiniteLine `sigClicked` 里弹菜单，同一次右键会连弹两个菜单（菜单动作删掉 marker 后第二次落进空白分支）。
- **十字预览线残留**：`sigMouseMoved` 经 `SignalProxy(rateLimit=30)` 会延迟投递最后一个移动事件（慢速移出光标时在 `QEvent.Leave` 隐藏之后才触发，预览线被重新点亮）；`_on_mouse_moved` 必须以 `QCursor.pos()` 实时判定光标是否在控件内，不能信事件坐标。
- MEASUREMENT 卡无独立标题行：图标+标题写在结果表左上角表头单元格（`_apply_meas_corner_title`，两处 `setHorizontalHeaderLabels` 后必须重调），卡片纵向边距 (14,2,14,6)。
- **纯 QWidget 自建标题栏 QSS 背景不生效**：正常 paint 路径下纯 `QWidget` 不绘制 QSS `background-color`（透出父级底色；`grab()` 离屏渲染却会绘制，易被误导），必须 `setAttribute(Qt.WA_StyledBackground, True)`（`_StandaloneTitleBar` 已处理；`ui/app_top_bar.py` 因背景色与页面相近未暴露，改色时需同样处理）。
- **Channel Config 高度须随内容收缩**：`_instruments_tab` 禁设固定 `setMinimumHeight`（内容变矮时多余高度会回灌各行、撑宽标题行与单元格间距）；Active 页签布局末尾必须保留 `addStretch()` 收口袋（导入页签已有），残余空间沉底而非均分回行。
- **行内混排控件纵向策略须一致**：QLineEdit 默认纵向 Fixed，与 ToggleLabel(min 24) 同行时行高由大者决定、Fixed 控件短一截，相邻行间距视觉差出高度差；`ScaleOffsetEdit`（及导入页签占位 QLineEdit）已设纵向 `Expanding` 随行高拉伸，新增同类行内输入框须同样处理。
- **Channel Config 右缘防"双线"**：整行最末槽的最末通道单元格用 `OUT_FRAME_LAST_STYLE`（去右边框），其余单元格用 `OUT_FRAME_STYLE`；导入页签行尾有 addStretch 单元格不贴右缘，无需处理。左侧 rail 按钮 `#railIconBtn` 总尺寸 20px（content 18 + border 2）；rail 图标用 `_make_svg_icon(..., 16, zoom=1.15)` 放大裁掉 Feather SVG 内建留白（zoom 1.25 会削掉 link-connect 圆弧端点，禁超 1.15）。
- **固定高输入框的控件级样式必须自带完整盒模型**：本页全局 `QLineEdit { padding: 6px 10px; border: 1px }`，24px 固定高输入框内容区仅剩 10px，数字底部截断；`setStyleSheet` 只设颜色不设 padding/font/border 会级联回全局同样截断。参考 `SAMPLE_PERIOD_EDIT_STYLE / SAMPLE_PERIOD_READONLY_STYLE`（padding 2px 4px + font 11px 全套）。
- **wordWrap QLabel 所在气泡禁 `adjustSize()` 量高**：`GuideTourOverlay._reposition` 曾因 `adjustSize()` 依赖 label sizeHint（按布局旧宽度换行）把高度算小、文本截断；须用 `QFontMetrics.boundingRect(固定文本宽, TextWordWrap)` 显式量正文高 + 固定项求和后 `setFixedHeight`。同理凡"文本刚更新即量高"的场景都不能信 sizeHint。
- **引导层高亮坐标须 `mapToGlobal` 中转**：`GuideTourOverlay._target_rect` 曾用 `target.mapTo(overlay, …)`（mapTo 的 parent 参数必须是调用者祖先，overlay 不是目标祖先）坐标错乱；一律 `overlay.mapFromGlobal(target.mapToGlobal(QPoint(0,0)))`。
- **`widget.grab()` 返回带 devicePixelRatio 的物理像素图**：多图 QPainter 合成时目标 QPixmap 必须 `setDevicePixelRatio(同 DPR)` 且坐标用逻辑值，否则 150% 缩放下内容缩至左上、右侧/中间留空白（`get_capture_pixmap` 实踩）。
- **通道门禁判"支持"禁用 `isEnabled()`**：录制中 `_show_progress_overlay` 禁用 `channel_config_card` 会把子控件 `isEnabled()` 传播为 False（瞬时锁），曾致可见通道集清空 + 快照恢复误擦勾选态（波形空白、MEASUREMENT 仍有数据）；门禁判断一律走 `view_recording.py::_cb_supported`（`WA_ForceDisabled` 显式禁用标志）。
- **仪器编辑对话框 IP 字段禁原样拼包**：`_InstrumentEditDialog._on_save` 必须先归一化（粘贴完整 VISA 地址时提取 host/端口），否则 `TCPIP0::{ip}::...` 拼出双重包裹非法地址（如 `TCPIP0::TCPIP0::ip::30000::SOCKET::hislip0::INSTR`），连接时 `viParseRsrcEx` 直接报 RSRC_NFOUND、auto 探测链在 N6705C 探针即失败，IT2705 永远不被尝试（2026-11 实踩）。

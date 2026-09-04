# ui/pages/pmu_test — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../../AGENTS.md) 与 [ui/pages/AGENTS.md](../AGENTS.md) 硬红线。

## 加载指针（AI 按需拉取）

- **新增 / 修改测试流程** → @see [docs/ai/07_TEST_GUIDE.md](../../../docs/ai/07_TEST_GUIDE.md)
- **算法 / Worker 下沉位置** → @see [core/pmu_test/](../../../core/pmu_test/)（clk/dcdc/gpadc/isgain/oscp 各自 analysis+worker）
- **巨石重构范式** → @see ADR [005-monolith-refactor](../../../docs/ai/decisions/005-monolith-refactor.md)

## 本模块职责与边界

- **职责**：PMU 子测试 Tab 容器（DCDC 效率 / 输出电压 / Is Gain / OSCP / GPADC / CLK）。
- **上游**：`ui/main_window.py`；**下游**：`core/pmu_test/` 各 analysis+worker、`instruments/factory`。
- **铁律**：UI 仅交互；算法 / 解析落 `core/pmu_test/*_analysis.py`（无 Qt）、Worker 落 `*_worker.py`（仅 QtCore）。

## 接口契约（对外不可破坏）

- `PMUTestUI` 构造透传：`n6705c_top / mso64b_top / chamber_ui / instrument_manager / ui_action_registry`。
- `TEST_TAB_MAP`：`dcdc_efficiency=0 / output_voltage=1 / is_gain=2 / oscp=3 / gpadc_test=4 / clk_test=5`。
- 各子页实现 `AIControllablePage` 契约：`ai_capabilities / ai_get_config / ai_apply_config / ai_start_test / ai_stop_test / ai_get_result_summary`。

## 局部约定

- 子页统一模式：`apply_config_to_controls` 单一写入口（线程边界校验 + `_AI_HIGHLIGHT_QSS` 临时高亮）。
- 通道在配置为 int、combo 文本为 "CH n"，apply 经 normalize 归一化匹配。
- **Output Voltage 有效区间判据**（`pmu_output_voltage.py` `_compute_valid_range`，2026-09）：以相邻压差**中位数**为参考步进（抗毛刺/饱和段污染），连续 2 点跌破参考的 85%（`_VALID_STEP_RATIO`/`_VALID_STEP_CONSEC` 常量）判死区/饱和，双向剔除；软饱和缓变与平坦段同覆盖（替代旧 1mV 平坦检测）。MSB 位加权不匹配的单点跳变（如 0x80 处约 2 倍步进）是固有现象，靠"连续 N 点"保留勿当异常剔除。
- **Output Voltage 前置校验失败 / 尾部饱和均改为用户确认弹窗**（2026-09）：不再直接中止，Worker 经统一 `confirm_request(title, message)` 信号 → UI 弹中文 QMessageBox（按钮"继续/中止"，默认+Esc=中止，`_on_confirm_request`）；Worker 用 `threading.Event` 阻塞等应答（`_wait_user_confirm`）且期间可响应 Stop。前置校验：仅问一次（`precheck_asked`），选继续时 `voltages/codes.clear()` 剔除已测异常前缀（性能指标自动排除，图表/日志保留原始数据）并重印表头+复述已测点（弹窗日志不打断 MEAS 表格，保证连续可解析），死区仍由 `_compute_valid_range` 兜底剔除；尾部饱和：选继续置 `_saturation_continue=True` 本次不再触发（保留平坦点，有效区间算法剔除），选中止则截断平台后 break。`_precheck_first_points` 原因文本为中文（嵌入弹窗）。
- **Output Voltage 扫描逻辑与 Module Test 双向同步**（2026-09 起，硬规则）：本页 `pmu_output_voltage.py` 的扫描行为（前置校验/尾部饱和确认弹窗及文案、`_PRECHECK_*` / `_TAIL_STOP_*` 阈值常量、异常前缀剔除语义、寄存器 finally 兜底恢复）与 [core/module_test/_common.py](../../core/module_test/_common.py) 的 `run_vout_scan` 保持一致。任一侧改动上述逻辑，必须在同一次变更内同步另一侧（阈值/文案/判定语义对齐），并同步更新两侧 AGENTS.md（另一侧为 ui/pages/module_test/AGENTS.md）。
- 结果落 `Results/`，文件名带时间戳 + 芯片型号。
- 新增子测试：UI 在 `ui/pages/pmu_test/`、analysis+worker 在 `core/pmu_test/<name>/`，并注册进 `TEST_TAB_MAP`。
- GPADC 最近测试管理（本会话内存记录，`_recent_test_records`，上限 `RECENT_TEST_LIMIT`）：
  - 管理栏位于 Curve 右侧 `recent_curve_splitter`（水平 QSplitter），chart 头部 `toggle_recent_btn` 可折叠/展开（记住宽度）；
  - 每条记录按 `id % 8` 稳定分配专属曲线色（`_record_color`），列表项前景色 / 图例 / 曲线三处一致；显示名经 `_record_display_name`（优先用户 Rename 的 label）贯通列表/对比图图例/单次图图例；
  - 列表 SingleSelection：选中变化（`_on_recent_selection_changed`，用 `selectedItems()` 而非 `currentItem()`——clearSelection 后 currentItem 不清空）同步高亮对比图中对应记录（图例加粗），其余记录曲线/符号/包络带半透明（`_plot_comparison_record` 的 `dimmed`，alpha 90）；
  - 列表右键菜单（`_show_recent_item_menu`）：Rename（QInputDialog 改 label）/ Load Curve / Check·Uncheck / Remove / Clear All；`_refresh_recent_test_list` 重建时按 record id 记忆并恢复勾选+选中状态（勿回退为全 Unchecked，Rename 后 Compare 依赖此行为）；
  - Curve View 选项（Mean / Min-Max / Error，非互斥 checkable）过滤载入图与对比图的曲线；入口两处：面板按钮 + 图表右键菜单（`_show_curve_view_menu`，PlotWidget 经 `_attach_curve_context_menu` 挂 CustomContextMenu 并禁 pyqtgraph 自带菜单，状态双向同步）；切换经 `_on_curve_view_changed` 自动重绘（优先对比图，其次 `_loaded_record`）；
  - 单次曲线图（`_plot_voltage_adc_curve`）的 Min-Max Band **不下沉叠加在主图上**，而是主图下方独立子图：画 Max/Min 相对 Mean 的偏差（`Max/Min - Mean`，电压模式单位 mV/V 按量级自适应，温度模式 °C），X 轴 `setXLink` 与主图联动，主图:子图布局拉伸比 3:1；快照导出（`_chart_image_bytes`）把两图纵向合成一张 QImage（ImageExporter **仅指定 width**，同时指定 height 会按 cover 缩放导致宽度不精确而裁剪）；对比图（`_plot_comparison_curves`）与 temp_consistency 图仍为叠加包络带，未迁移；
  - 曲线类测试（force_voltage / high_low_temp / temp_consistency）完成时 `_set_curve_view_all(True)` 默认全开全部波形，并把 `_loaded_record` 指向最新记录（右键切换据此重绘单次数据）；1000CNT 不重置 Curve View；`_set_curve_view_all` 内 blockSignals 防自动重绘副作用；
  - 每次测试完成在 `_on_test_done` 尾部统一 `_record_recent_test(kind, result)`（result 为 None 不记录）；
  - Compare = 勾选 ≥2 条：曲线类记录画对比图（`_plot_comparison_curves`，遵循 Curve View），1000CNT 记录输出统计对比表到日志；
  - Load/双击 = 单条恢复曲线+指标卡+`_export_data`（可继续 Export），并置 `_loaded_record`；
  - 新测试开始 `_start_test` 调 `_reset_result_display()` 清旧曲线/指标/导出数据/`_loaded_record`；
  - 默认空坐标系构建集中在 `_build_default_chart_placeholder()`，勿在 `_create_layout` 内散写。
- **GPADC 测试自动命名**（Recent 面板 Test Naming 区）：`芯片_通道_CASE_序号`，序号在相同 (chip, channel, case) 组合内经 `_naming_counters` 自动递增（三位零填充）；记录存 `name` / `naming` 字段，显示名优先级 label（用户 Rename）> name（自动）> test_item；列表项悬浮 tooltip（`_record_tooltip`）展示测试时间/测试项/性能参数/算法/命名。
- **GPADC 采样算法**（Test Parameters Algorithm 区）：算法实现在 `core/pmu_test/gpadc/gpadc_analysis.py` 的 `ALGORITHM_REGISTRY`（纯函数注册表，含参数元信息），UI 参数控件经 `_rebuild_algorithm_params` 按注册表动态生成——**新增算法只写纯函数+注册表登记，零 UI 改动**；默认 None = 原始流程；`_start_test` 快照到 `_algorithm_snapshot`，在 `gpadc_uart_read_by_cnts` / `gpadc_reg_read_by_cnts` 的 raw_data 上应用（含 DEBUG_MOCK 路径）；算法配置进 `get_test_config()['algorithm']` 并支持 `apply_config_to_controls` 回填。

## 局部坑点

- 跨线程更新 UI 只走 Signal/Slot；Worker 禁 import QtWidgets。
- 日志区用 `ExecutionLogsFrame.wrap_with`（见 ui/modules/AGENTS.md §6.4）。
- 公共 Mixin / 样式改动需回归全部 6 个子页。
- **GPADC 停止测试禁在 UI 线程 `thread.wait()`**（2026-08 实测卡死）：worker 收尾耗时不可控时主线程被无限期阻塞；且 UART 数据泵（`_on_uart_rx_data` 是主线程槽）随主线程一起断供，`_next_uart_log_line` 内层若不查 `stop_check` 会自旋到 deadline（120s）——两层叠加即"点停止无反应、窗口卡死"。修法：`_stop_test` 只 `request_stop()+quit()`，收尾交 `thread.finished → _on_test_thread_finished`（与 clk_test_ui 同范式）；所有 worker 侧等待循环（含内层 `_next_uart_log_line`、temp_consistency 的 30s 稳温 sleep）必须逐片检查 `stop_check`。
- **worker 线程禁直调 `set_system_status`**（2026-08 实测整进程 SIGABRT / "Fatal Python error: Aborted"，现场仅主线程栈停在 `app.exec()`）：Mixin 原实现直接 `setText/setObjectName/unpolish/polish`，跨线程改 QWidget 破坏线程亲和性；GPADCTestUI 已重写为经 `system_status_requested` 信号队列化回主线程（`_apply_system_status` 槽），页面内直接 `self.set_system_status(...)` 即可，勿绕过重写。

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
- 结果落 `Results/`，文件名带时间戳 + 芯片型号。
- 新增子测试：UI 在 `ui/pages/pmu_test/`、analysis+worker 在 `core/pmu_test/<name>/`，并注册进 `TEST_TAB_MAP`。
- GPADC 最近测试管理（本会话内存记录，`_recent_test_records`，上限 `RECENT_TEST_LIMIT`）：
  - 管理栏位于 Curve 右侧 `recent_curve_splitter`（水平 QSplitter），chart 头部 `toggle_recent_btn` 可折叠/展开（记住宽度）；
  - 每条记录按 `id % 8` 稳定分配专属曲线色（`_record_color`），列表项前景色 / 图例 / 曲线三处一致；显示名经 `_record_display_name`（优先用户 Rename 的 label）贯通列表/对比图图例/单次图图例；
  - 列表 SingleSelection：选中变化（`_on_recent_selection_changed`，用 `selectedItems()` 而非 `currentItem()`——clearSelection 后 currentItem 不清空）同步高亮对比图中对应记录（图例加粗），其余记录曲线/符号/包络带半透明（`_plot_comparison_record` 的 `dimmed`，alpha 90）；
  - 列表右键菜单（`_show_recent_item_menu`）：Rename（QInputDialog 改 label）/ Load Curve / Check·Uncheck / Remove / Clear All；`_refresh_recent_test_list` 重建时按 record id 记忆并恢复勾选+选中状态（勿回退为全 Unchecked，Rename 后 Compare 依赖此行为）；
  - Curve View 选项（Mean / Min-Max / Error，非互斥 checkable）过滤载入图与对比图的曲线；入口两处：面板按钮 + 图表右键菜单（`_show_curve_view_menu`，PlotWidget 经 `_attach_curve_context_menu` 挂 CustomContextMenu 并禁 pyqtgraph 自带菜单，状态双向同步）；切换经 `_on_curve_view_changed` 自动重绘（优先对比图，其次 `_loaded_record`）；
  - 曲线类测试（force_voltage / high_low_temp / temp_consistency）完成时 `_set_curve_view_all(True)` 默认全开全部波形，并把 `_loaded_record` 指向最新记录（右键切换据此重绘单次数据）；1000CNT 不重置 Curve View；`_set_curve_view_all` 内 blockSignals 防自动重绘副作用；
  - 每次测试完成在 `_on_test_done` 尾部统一 `_record_recent_test(kind, result)`（result 为 None 不记录）；
  - Compare = 勾选 ≥2 条：曲线类记录画对比图（`_plot_comparison_curves`，遵循 Curve View），1000CNT 记录输出统计对比表到日志；
  - Load/双击 = 单条恢复曲线+指标卡+`_export_data`（可继续 Export），并置 `_loaded_record`；
  - 新测试开始 `_start_test` 调 `_reset_result_display()` 清旧曲线/指标/导出数据/`_loaded_record`；
  - 默认空坐标系构建集中在 `_build_default_chart_placeholder()`，勿在 `_create_layout` 内散写。

## 局部坑点

- 跨线程更新 UI 只走 Signal/Slot；Worker 禁 import QtWidgets。
- 日志区用 `ExecutionLogsFrame.wrap_with`（见 ui/modules/AGENTS.md §6.4）。
- 公共 Mixin / 样式改动需回归全部 6 个子页。
- **GPADC 停止测试禁在 UI 线程 `thread.wait()`**（2026-08 实测卡死）：worker 收尾耗时不可控时主线程被无限期阻塞；且 UART 数据泵（`_on_uart_rx_data` 是主线程槽）随主线程一起断供，`_next_uart_log_line` 内层若不查 `stop_check` 会自旋到 deadline（120s）——两层叠加即"点停止无反应、窗口卡死"。修法：`_stop_test` 只 `request_stop()+quit()`，收尾交 `thread.finished → _on_test_thread_finished`（与 clk_test_ui 同范式）；所有 worker 侧等待循环（含内层 `_next_uart_log_line`、temp_consistency 的 30s 稳温 sleep）必须逐片检查 `stop_check`。
- **worker 线程禁直调 `set_system_status`**（2026-08 实测整进程 SIGABRT / "Fatal Python error: Aborted"，现场仅主线程栈停在 `app.exec()`）：Mixin 原实现直接 `setText/setObjectName/unpolish/polish`，跨线程改 QWidget 破坏线程亲和性；GPADCTestUI 已重写为经 `system_status_requested` 信号队列化回主线程（`_apply_system_status` 槽），页面内直接 `self.set_system_status(...)` 即可，勿绕过重写。

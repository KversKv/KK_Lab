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

## 局部坑点

- 跨线程更新 UI 只走 Signal/Slot；Worker 禁 import QtWidgets。
- 日志区用 `ExecutionLogsFrame.wrap_with`（见 ui/modules/AGENTS.md §6.4）。
- 公共 Mixin / 样式改动需回归全部 6 个子页。

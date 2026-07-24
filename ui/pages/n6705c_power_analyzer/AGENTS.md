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

## 局部约定

- **通道标签用 QPushButton 模拟 tab**：active / inactive / disabled 的 `padding / border / margin` **盒模型必须一致**（见 03§25）；视觉连接用同背景色 `border-bottom`，**禁 `border-bottom: none`**（否则切到末位 tab 内容偏移几像素）。参考 `_build_channel_tab_style`。
- 单位显示：内存值统一 mA/mV/mW；`_format_value(value_mA)` 显示时 SI 选档。
- 通道同步经 `core/n6705c/channel_sync_worker.py` 周期回读。

## 局部坑点

- **§25 Tab 盒模型坑**：见上"局部约定"第一条，是本页踩过的真实坑。
- Datalog 导出是二进制+CSV 混合，**不要重复造解析轮子**，用 instruments 层 datalog_process。
- 波形单位事实源在 `n6705c_datalog_process.py`（`parse_channel_label` 等），勿在 UI 另写推断。

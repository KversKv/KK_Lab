# ui/pages/vmin_hunter — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../../AGENTS.md) 与 [ui/pages/AGENTS.md](../AGENTS.md) 硬红线。

## 加载指针（AI 按需拉取）

- **探底引擎（core）** → @see [core/vmin_hunter/](../../../core/vmin_hunter/)（`alive_checker` / `sleep_vmin_engine`）
- **结构设计** → `docs/ai/VminHunter/ViminHunterStructure.md`
- **用户手册** → `docs/User Manual/AUTOMATION/VminHunter.md`

## 本模块职责与边界

- **职责**：探测芯片能稳定工作的最低电压边界（Vmin）。
- **上游**：`ui/main_window.py`；**下游**：`core/vmin_hunter/` 引擎（QThread + EngineHooks 注入硬件动作）、`instruments/factory`。
- **铁律**：本页仅 UI 与交互；遍历引擎 / 校准 / 死机判定 / 恢复在 core 层，UI 禁阻塞 IO。

## 接口契约（对外不可破坏）

- `VminHunterContainerUI`（`vmin_hunter_container.py`）：Tab 容器，`TEST_TAB_MAP = {"hunt": 0, "single_test": 1}`，`set_current_test()` + `sync_n6705c_from_top()` 透传子页；`main_window._create_vmin_hunter_ui(selected_test=...)` 经侧边栏悬停子菜单切换。
- 复用 Mixin：`N6705CConnectionMixin` + `ChamberConnectionMixin` + `McuPwrResetConfigMixin` + `SerialComMixin(MODE_FULL)`。
- 引擎 `SleepVminEngine`（core）：QThread 编排，硬件动作经 `EngineHooks` 注入（UI 提供）。
- 判活策略可插拔（`alive_checker`：默认 sleep=0/1 翻转 + 崩溃关键字 + 超时）。

## 局部约定

- 布局：左侧配置列（设备连接 / Test Config / Channel Config）+ 右侧监控区（电压点遍历结果表 + 死机记录）+ 底部 Execution Logs（UART 日志 / 死机检测）。
- 子页 `VminSingleTestUI`（`vmin_single_test_ui.py`）继承 `VminHunterUI`：仅重写 `_create_test_config_panel`（单点 Default + Vmin 替代扫描参数）/`_on_vcorel_toggled`/`_read_params`/`_apply_config`；`voltage_points=[vmin]` 复用父类 `_start_external_sleep_sweep` 单点执行。父类 `_apply_config` 的通道/串口尾部已抽为 `_apply_channel_and_link_config` 供子类复用。
- 结果落 `Results/` 带时间戳。

## 局部坑点

- **§7 长耗时**：电压遍历 + 死机恢复为长流程，必须 QThread 异步。
- 死机判定靠 UART 日志关键字 + 判活翻转，UI 只展示不判定。
- 跨线程更新结果表只走 Signal/Slot。

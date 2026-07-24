# ui/pages/charger_test — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../../AGENTS.md) 与 [ui/pages/AGENTS.md](../AGENTS.md) 硬红线。

## 加载指针（AI 按需拉取）

- **新增 / 修改测试流程** → @see [docs/ai/07_TEST_GUIDE.md](../../../docs/ai/07_TEST_GUIDE.md)
- **巨石重构范式** → @see ADR [005-monolith-refactor](../../../docs/ai/decisions/005-monolith-refactor.md)

## 本模块职责与边界

- **职责**：Charger 子测试 Tab 容器（配置遍历 / 状态寄存器 / Iterm / 调节电压）。
- **上游**：`ui/main_window.py`；**下游**：`core/` 测试编排、`instruments/factory`、温箱联动。
- **铁律**：UI 仅交互；测试逻辑走 QThread Worker + Signal/Slot。

## 接口契约（对外不可破坏）

- `ChargerTestUI` 构造透传：`n6705c_top / chamber_ui / instrument_manager / ui_action_registry`。
- `TEST_TAB_MAP`：`config_traverse=0 / status_register=1 / iterm=2 / regulation_voltage=3`。
- 各子页实现 `AIControllablePage` 契约（同 pmu_test）。

## 局部约定

- 子页统一模式：`apply_config_to_controls` 单写入口 + AI 高亮。
- I2C 地址为 16 进制，回填用 `_to_hex` 统一。
- 结果落 `Results/` 带时间戳；新增子测试注册进 `TEST_TAB_MAP`。

## 局部坑点

- 温箱联动（高低温扫描）走 `chamber_ui` 注入，勿在页内直接连温箱。
- 跨线程只走 Signal/Slot；日志区用 `ExecutionLogsFrame.wrap_with`。

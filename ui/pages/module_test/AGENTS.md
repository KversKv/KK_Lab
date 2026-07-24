# ui/pages/module_test — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../../AGENTS.md) 与 [ui/pages/AGENTS.md](../AGENTS.md) 硬红线。

## 加载指针（AI 按需拉取）

- **新增 / 修改测试流程** → @see [docs/ai/07_TEST_GUIDE.md](../../../docs/ai/07_TEST_GUIDE.md)
- **编排内核** → @see [core/module_test/](../../../core/module_test/)（`_runner_base` / `mode_manager` / `_common` / `result_model`）

## 本模块职责与边界

- **职责**：Module Test（LDO / DCDC）隐藏 Tab 容器。
- **上游**：`ui/main_window.py` / nav_controller；**下游**：`core/module_test/` runner + items。
- **铁律**：UI 仅交互；`core/module_test/` 无 QtWidgets。

## 接口契约（对外不可破坏）

- `ModuleTestUI` 构造透传：`n6705c_top / mso64b_top / chamber_ui / instrument_manager / ui_action_registry`。
- `TEST_TAB_MAP`：`ldo=0 / dcdc=1`；暴露 `set_current_test / get_current_test / _sync_from_top` 供枢纽调用。
- 共享基类 [_base_subpage.py](./_base_subpage.py)：两子页（LDO/DCDC）复用的被测配置区 / DUT 模式管理 / AI 契约。

## 局部约定

- **DUT 工作模式管理**（reg / load / manual）：reg 写 I2C 寄存器、load 设负载电流触发切换、manual 走 `ctx.pause_fn(prompt)` 暂停等确认。
- **手动暂停跨线程**：worker `_pause_fn` 在工作线程 `QWaitCondition.wait(200ms)` 轮询；UI 槽弹框后 `confirm_mode` 唤醒；`request_stop` 也唤醒（confirmed=False）防死锁。
- `measured` 用 `list[dict]`（非 `{"rows":[...]}`）才能被 `_measured_to_rows` 渲染成正表。
- quiescent 项：`parse_dut_modes` 遍历，CSV 扩为 `["Mode","ActualMode","EnterBy","Iq (uA)"]`；`ai_get_config` 勾选且有模式才计入 sweep_dimensions。

## 局部坑点

- `mode_confirm_required` 信号 → QMessageBox → `confirm_mode`，全程主线程。
- 结果落 `Results/`；新增测试项落 `core/module_test/{ldo,dcdc}/items/`。

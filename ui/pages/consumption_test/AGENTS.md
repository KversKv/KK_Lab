# ui/pages/consumption_test — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../../AGENTS.md) 与 [ui/pages/AGENTS.md](../AGENTS.md) 硬红线。

## 加载指针（AI 按需拉取）

- **编排内核** → @see [core/consumption_test/](../../../core/consumption_test/)（controller + workers）
- **新增测试流程** → @see [docs/ai/07_TEST_GUIDE.md](../../../docs/ai/07_TEST_GUIDE.md)
- **巨石重构（本页待续拆）** → @see ADR [005-monolith-refactor](../../../docs/ai/decisions/005-monolith-refactor.md)

## 本模块职责与边界

- **职责**：DUT 固件下载 + 功耗测试（含高低温扫描）。
- **上游**：`ui/main_window.py`；**下游**：`core/consumption_test/`、`instruments/factory`（双 N6705C + 温箱）、`lib/download_tools/`（dldtool）。
- **铁律**：UI 仅交互；下载 / 采集 / 温控等待走 QThread Worker。

## 接口契约（对外不可破坏）

- 复用 Mixin：`N6705CConnectionMixin` + `SerialComMixin(MODE_INLINE)` + `ExecutionLogsFrame`。
- 视图拆分：`view_config / view_panels / view_results / widgets`；controller 在 `core/consumption_test/consumption_controller.py`。
- 固件下载走 `lib/download_tools/`（dldtool.exe），禁在 UI 直接调。

## 局部约定

- **双 N6705C**（供电 + 测量）+ 温箱联动，高低温扫描经 `high_low_temp_test_ui.py`。
- YAML 配置加载（`yaml` 可选导入，缺失降级）。
- 结果落 `Results/` 带时间戳。

## 局部坑点

- **ADR 005 遗留**：`consumption_test.py` UI 本体仍较大，后续按 `view_config / view_results` 继续拆，勿新增上帝类。
- 温箱温度稳定等待为分钟级，必须异步（见 03§7）。
- AI 受控接入评估后**推迟**（`HighLowTempConsumptionTestUI` 双仪器 + 温箱，契约命名非标准 `_on_start_clicked` / `_test_worker`），建议独立迭代。

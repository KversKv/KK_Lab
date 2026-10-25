# core/ — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../AGENTS.md) 硬红线。仅存放本模块局部知识；通用规范回指 docs/ai。

## 加载指针（AI 按需拉取）

- **新增 / 修改测试流程** → @see [docs/ai/07_TEST_GUIDE.md](../docs/ai/07_TEST_GUIDE.md)
- **分层与 UI 内容约束** → @see [docs/ai/04_ARCHITECTURE.md](../docs/ai/04_ARCHITECTURE.md)
- **巨石重构背景** → @see ADR [005-monolith-refactor](../docs/ai/decisions/005-monolith-refactor.md)
- **跨模块坑** → @see [docs/ai/03_GOTCHAS.md](../docs/ai/03_GOTCHAS.md)

## 本模块职责与边界

- **职责**：业务编排、测试流程、数据流、后台 Worker；承上启下连接 UI 与仪器。
- **上游**：`ui/` 通过 Signal/Slot 调用 controller / test 类。
- **下游**：`instruments/`（经 factory）、`lib/`、`chips/` 配置。
- **铁律**：本模块**禁止** import `PySide6.QtWidgets` / `QtGui`；Worker 只能 `from PySide6.QtCore import ...`。

## 接口契约（对外不可破坏）

- 测试类统一信号：`progress(int)` / `point_ready(object)` / `finished(bool, str)`，并提供 `start()` / `stop()`。
- 线程模型：`QObject + moveToThread`，禁止继承 `QThread` 再 override `run`。
- `serial_io/` 为 pyserial 唯一入口：UI 禁直接 `import serial`；端口枚举 / 打开连接 / 参数文本映射走 `serial_backend`（无 Qt）；会话与多会话管理为 `serial_session.py` / `serial_session_manager.py`（仅 QtCore），UI 经 `core.serial_io` 导入。
- `serial_io/read_worker.SerialReadWorker` 的 `run()` 结束（含异常 break）必发 `finished`；连接侧必须据此 `thread.quit` + `worker.deleteLater` 并复位线程引用，否则异常退出后无法重建读线程。
- `instruments/visa_scan.py`：通用 VISA *IDN? 关键词扫描（`discover_visa_by_idn` + `VisaIdnScanWorker`），UI 连接 Mixin 的 Search 统一走它；探测串行执行，禁并发。
- `stop()` 只置 `self._abort = True`，子线程循环检测软停止；`finally` 里必须 `thread.quit(); thread.wait()`。
- 连接状态共享经 [instruments/connection_hub.py](./instruments/connection_hub.py) 的 `ConnectionHub` 单点订阅。

## 局部约定

- **拆分范式（ADR 005）**：新功能按 `View / Controller / Worker / Analysis` 四分：
  - `*_ui.py` → `ui/pages/`；
  - `*_controller.py` → `core/<feature>/`；
  - `*_worker.py` → `core/<feature>/`（仅 QtCore）；
  - `*_analysis.py` → `core/<feature>/`（**无任何 Qt**，pytest 可直测）。
- **禁止在 core 出现 UI 逻辑**：弹窗、样式、控件操作一律回 UI 层。Worker 需用户决策时走"信号请求 + threading.Event 阻塞应答"范式（参考 [pmu_test/gpadc/gpadc_worker.py](./pmu_test/gpadc/gpadc_worker.py) 的 `confirm_request / wait_user_confirm / respond_confirm` 三件套，阻塞期间须可响应 Stop），不得自行 import QtWidgets 弹窗。
- **数据落盘**：结果写 `Results/`，文件名 `<功能>_<型号>_<YYYYMMDD_HHMMSS>.csv`，写前 `os.makedirs(..., exist_ok=True)`。
- **芯片配置**：从 [chips/bes_chip_configs/](../chips/bes_chip_configs/) 读取，不在 core 硬编码寄存器 / 电压表。
- `pmu_test/dcdc/dcdc_analysis.generate_current_points` Linear/Log 模式必含 `end_current_a` 终点（2026-09，步进/网格不足时自动补点，相对 1e-9 近重去重）；Custom 模式取 `custom_points`（A 列表），abs/剔 0/去重/升序，空表回退 `[start_a, end_a]`。
- `module_test/report/` 为包（原 report.py 拆分）：`data.py`（REPORT_DATA 构建）/ `template.py`（HTML 模板）/ `api.py`（生成+落盘）；对外只经 `__init__.py` 再导出，引用侧一律 `from core.module_test.report import ...`，禁直导子模块。

## 局部坑点

> 详细背景见 [docs/ai/03_GOTCHAS.md](../docs/ai/03_GOTCHAS.md)。

- **§7 长耗时 IO 阻塞 UI**：VISA query、下载、温箱等待必须放 QThread / Worker，违反会卡死界面。
- **§8 QThread 生命周期**：用 `QObject + moveToThread`；线程结束 `quit() → wait()`，否则主窗口关闭时崩溃；跨线程只用 Signal/Slot。
- **§26 worker finished 槽链里再起新 QThread**：禁止 `QTimer.singleShot(0, ...)` 直接重入，会与上一轮线程清理竞态导致无声闪退；须 `singleShot(≥50ms)`。
- **VISA 探测禁止并发调用**：`n6705c/search_worker.py` 的 `_probe_one` 必须串行执行——IVI-VISA 多线程并发 viOpen/viRead/viClose（即使每线程独立 RM）会堆损坏崩溃（fatal 0xc0000374 / access violation，2026-10-15 真机实测）；跨网段端口扫描（纯 socket）不受此限可并发。
- **ADR 005 遗留**：`serialCom_module_frame.py` 主壳仍有对话框未拆、`consumption_test.py` UI 本体仍大，重构时按既有阶段继续切，不要大爆炸。
- **Orchestrator 裸变量名校验语义**：节点参数裸变量名（如 case4 模板 `temperature: "i"`）运行期由 `resolve_value` 求值，preflight（`schema.validate_param_schema`，签名为 `(node, known_variables=None)`）仅放行**前序节点已产生**的变量名（如循环变量），未知裸名仍按字面值报类型错；外部注入变量必须用 `${name}` 引用（仅 warning 级）。

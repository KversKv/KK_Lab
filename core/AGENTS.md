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
- `stop()` 只置 `self._abort = True`，子线程循环检测软停止；`finally` 里必须 `thread.quit(); thread.wait()`。
- 连接状态共享经 [instruments/connection_hub.py](./instruments/connection_hub.py) 的 `ConnectionHub` 单点订阅。

## 局部约定

- **拆分范式（ADR 005）**：新功能按 `View / Controller / Worker / Analysis` 四分：
  - `*_ui.py` → `ui/pages/`；
  - `*_controller.py` → `core/<feature>/`；
  - `*_worker.py` → `core/<feature>/`（仅 QtCore）；
  - `*_analysis.py` → `core/<feature>/`（**无任何 Qt**，pytest 可直测）。
- **禁止在 core 出现 UI 逻辑**：弹窗、样式、控件操作一律回 UI 层。
- **数据落盘**：结果写 `Results/`，文件名 `<功能>_<型号>_<YYYYMMDD_HHMMSS>.csv`，写前 `os.makedirs(..., exist_ok=True)`。
- **芯片配置**：从 [chips/bes_chip_configs/](../chips/bes_chip_configs/) 读取，不在 core 硬编码寄存器 / 电压表。

## 局部坑点

> 详细背景见 [docs/ai/03_GOTCHAS.md](../docs/ai/03_GOTCHAS.md)。

- **§7 长耗时 IO 阻塞 UI**：VISA query、下载、温箱等待必须放 QThread / Worker，违反会卡死界面。
- **§8 QThread 生命周期**：用 `QObject + moveToThread`；线程结束 `quit() → wait()`，否则主窗口关闭时崩溃；跨线程只用 Signal/Slot。
- **§26 worker finished 槽链里再起新 QThread**：禁止 `QTimer.singleShot(0, ...)` 直接重入，会与上一轮线程清理竞态导致无声闪退；须 `singleShot(≥50ms)`。
- **ADR 005 遗留**：`serialCom_module_frame.py` 主壳仍有对话框未拆、`consumption_test.py` UI 本体仍大，重构时按既有阶段继续切，不要大爆炸。

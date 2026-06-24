# ADR 005 - 巨石重构（Monolith Refactor）：UI 巨石 → View/Controller/Worker/Analysis 三层

- **状态**：Accepted
- **日期**：2026-06-24
- **范围**：`ui/` 红区巨石文件（serialCom_module_frame / n6705c_analyser_ui / n6705c_datalog_ui / pmu_test/* / oscilloscope / consumption_test / main_window / ai_assist_panel）、新增 `core/pmu_test/`、`core/controllers/`、`core/n6705c/`、`core/serial_script/`、`core/consumption_test/`、`core/instruments/connection_hub.py`、`ui/ai/transcript_exporter.py`、`ui/styles/serial_tokens.py` 等
- **关联**：[CodebaseRefactorAssessment.md](../NewFT/CodebaseRefactorAssessment.md)、[04_ARCHITECTURE.md §2.1](../04_ARCHITECTURE.md)

---

## 背景

盘点全量 Python 源码（~97,800 行 / 313 文件）发现 31 个 >800 行的红区文件几乎全部落在 `ui/`，根因是 PySide6 的 `QWidget` 子类被当成"上帝对象"：单个类同时承担视图构建、业务编排、数据处理、后台 Worker、设备 IO、弹窗与样式字符串。典型如 `serialCom_module_frame.py`（8564 行）单类承载 8+ 职责，`n6705c_analyser_ui.py`（7234 行）Worker 与 UI 同住。

这导致：算法/解析被 Qt 文件绑架、无法脱离 UI 单测；视图构建函数动辄 150~500 行；样式字符串散落重复；`main_window` 把导航 + 连接共享 + Signal 宿主混在一起。

`core/custom_test/`、`core/ai/`、`core/instruments/` 已是干净范本（document/executor/compiler/nodes、providers/algorithms/actions、session/manager/registry 各司其职），可作为目标形态。

## 决策

1. **统一拆分范式（MVC/MVP 三角）**：对每个红区页面切成 View / Controller / Worker / Analysis 四类文件，包内分文件而非一个 god file：
   - `ui/pages/<feature>/<feature>_ui.py`：瘦 View，只做控件树 / 布局 / 样式 / 信号连线。
   - `core/<feature>/<feature>_controller.py`：流程编排（start/stop/pause），发 Signal。
   - `core/<feature>/<feature>_worker.py`：QThread/QObject Worker，**仅** `QtCore`。
   - `core/<feature>/<feature>_analysis.py`：纯算法 / 解析，**无任何 Qt**，pytest 可直测。

2. **强化铁律（并入 [04_ARCHITECTURE §2.1](../04_ARCHITECTURE.md)）**：
   - `ui/` 禁止出现纯解析 / 算法 / 统计函数 → 一律落 `core/**/*_analysis.py`。
   - Worker 只依赖 `QtCore`，不得 import `QtWidgets`/`QtGui`。
   - View 单方法 > ~80 行须抽小工厂；View 不直接发 SCPI / 读串口。

3. **渐进式落地（不大爆炸）**：按"先算法 → 再 Worker → 再 controller → 最后视图"顺序，每步纯搬运不改行为，旧入口 re-export 兼容，每步跑 `tests/test_smoke_import.py` + 相关 pytest。回滚单元 = 单个阶段。

4. **连接状态共享中枢下沉**：新增 `core/instruments/connection_hub.py` 的 `ConnectionHub`（仅 `QtCore`），聚合 `N6705CTop` / `MSO64BTop` / `InstrumentManager` 三处 `connection_changed` / `sessions_changed` 为单一信号；`main_window` 仅订阅 `hub.connection_changed`，不再各自连线三处。tops 由 ui 注入，hub 不反向 import ui，保持 `core` 不依赖 `ui` 的方向。

5. **样式 token 化**：`ui/styles/serial_tokens.py` 提炼 `APPLE_TOKENS` / `DARK_TOKENS`，两套 serialCom 皮肤改为引用 token，去重并保留皮肤选择逻辑。

6. **Mixin 装配**：`serialCom_module_frame` 的 `SerialComMixin` 以多继承装配 7 个职责 Mixin（connection / toolbar / log_panel / filter_save / send / chart / script），MRO 无冲突，原方法名保持不变；脚本执行引擎下沉 `core/serial_script/script_engine.py`（无 Qt）。

## 落地阶段（8 Phase）

| Phase | 内容 | 状态 |
|---|---|---|
| 0 | 基线 + 测试网（`tests/test_smoke_import.py` + `tests/refactor/`） | ✅ |
| 1 | PMU 算法/Worker 下沉 `core/pmu_test/{clk,gpadc,dcdc,isgain,oscp}` | ✅ |
| 2 | 示波器 controller 化 `core/controllers/oscilloscope_controller.py` | ✅ |
| 3 | n6705c_analyser 拆分（Worker→core，widgets/view 分文件） | ✅ |
| 4 | serialCom 巨石拆分（7 Mixin + 脚本引擎下沉） | ✅ |
| 5 | consumption_test 收尾（controller + view 拆分） | ✅ |
| 6 | 样式 token 统一 | ✅ |
| 7 | 收尾：connection_hub / ai_assist_panel 子组件 / n6705c_datalog 复用 / 文档同步 / ADR | ✅ |

## 影响

- 新增子包：`core/pmu_test/`、`core/controllers/`、`core/n6705c/`、`core/serial_script/`、`core/consumption_test/`、`core/instruments/connection_hub.py`、`ui/ai/transcript_exporter.py`、`ui/styles/serial_tokens.py`、`ui/modules/serialCom_module/mixins/`。
- `ui/` 红区文件普遍瘦身（如 clk_test_ui 2588→1710、dcdc 2362→1634、isGain 1775→1334、oscp 1571→1112）；`main_window` 连接连线由 3 处收敛为 1 处 hub 订阅。
- 强化铁律正式并入 [04_ARCHITECTURE §2.1](../04_ARCHITECTURE.md)，后续新页面须遵循 View/Controller/Worker/Analysis 四分。
- `DIRECTORY_STRUCTURE.txt`、`spec/kk_lab.spec`（hiddenimports）、`helps/` 已同步；无新增第三方依赖。
- 回归：`tests/test_smoke_import.py` + `tests/refactor/` 全绿（含 Phase 7 新增 `test_phase7_connection_dlog.py` 6 单测）。

## 遗留 / 后续

- `serialCom_module_frame.py` 主壳仍有 6 个对话框/控件类未搬到 `widgets.py`（见评估文档 §12.2），后续按需继续拆。
- `consumption_test.py` UI 本体仍较大，可在下一轮按 view_config / view_results 继续切。
- 评估文档中部分行数为早期快照（如 `n6705c_datalog_ui.py` 标 2065，实际 7234），以代码现状为准。

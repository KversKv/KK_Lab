# Module Test 页面规划（LDO / DCDC 完整可测测试项 + 报告）

> 类型：新增 UI 页面（AUTOMATION 分组）+ 配套 core 编排 + 报告体系。
> 本文仅做**规划**，不动代码。落地时严格遵循 [06_PAGE_GUIDE](../../06_PAGE_GUIDE.md) / [01_CONVENTIONS §6](../../01_CONVENTIONS.md) / [03_GOTCHAS](../../03_GOTCHAS.md) / [07_TEST_GUIDE](../../07_TEST_GUIDE.md) / [04_ARCHITECTURE](../../04_ARCHITECTURE.md)。
> 参考现有对标页面：[pmu_test_ui.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/pages/pmu_test/pmu_test_ui.py)、[charger_test_ui.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/pages/charger_test/charger_test_ui.py)。

---

## 1. 目标

在侧边栏 **AUTOMATION** 分组下新增顶层入口 **Module Test**，含两个子页面：

- **LDO** —— 面向线性稳压器（LDO）的完整可测测试项。
- **DCDC** —— 面向开关电源（BUCK/DCDC）的完整可测测试项。

每个子页面完成"参数配置 → 编排执行 → 结果落盘 → 生成报告"的闭环，与现有 PMU Test / Charger Test 的交互与分层风格保持一致。

### 非目标（本期不做）
- 不重写现有 PMU/Charger 的单项测试逻辑，可**复用**其 core worker（如 DCDC 效率、Output Voltage）。
- 不引入新的仪器驱动；仅使用现有 N6705C / 示波器 / 温箱及其 Mock。
- 不实现分布式/远程报告服务，报告为本地文件产物。

---

## 2. 需求拆解：LDO / DCDC 可测测试项

> 依据 [PMU 测试用例汇总](file:///d:/CodeProject/TRAE_Projects/KK_Lab/docs/user/pmu_test_reports/00_PMU测试用例与方法汇总.md) 的"电源质量类"矩阵抽取，只保留**当前仪器条件下可自动化测量**的项。带 `(scope)` 需示波器，`(n6705c)` 仅需电源分析仪，`(chamber)` 可选联动温箱扫高低温。

### 2.1 LDO 子页面测试项
| Key | 测试项 | 主要仪器 | 判定/记录 |
|---|---|---|---|
| `ldo_vout_scan` | 各挡位输出电压扫描（遍历寄存器全挡位） | n6705c | 输出电压范围/步进/线性度 |
| `ldo_load_reg` | 负载调整率（1~200mA 扫描） | n6705c | ΔVout/ΔIload |
| `ldo_line_reg` | 线性调整率（Vin 3.2~4.2V 扫描） | n6705c | ΔVout/ΔVin |
| `ldo_quiescent` | 静态电流（Iq） | n6705c | 各模式静态电流 |
| `ldo_ripple` | 输出纹波 | scope | Vpp / RMS |
| `ldo_psrr` | 电源抑制比（可选，注入源存在时） | scope | dB @ 频点 |
| `ldo_load_transient` | 负载瞬态响应（10/100/1000Hz） | scope | 过冲/下冲/恢复时间 |

### 2.2 DCDC 子页面测试项
| Key | 测试项 | 主要仪器 | 判定/记录 |
|---|---|---|---|
| `dcdc_vout_scan` | 各挡位输出电压扫描 | n6705c | 输出电压范围/步进 |
| `dcdc_efficiency` | 效率（1~200mA ramp，复用现有 worker） | n6705c | η @ 各负载点 |
| `dcdc_load_reg` | 负载调整率 | n6705c | ΔVout/ΔIload |
| `dcdc_line_reg` | 线性调整率 | n6705c | ΔVout/ΔVin |
| `dcdc_quiescent` | 静态电流（PWM/BURST/ULP 分模式） | n6705c | 各模式 Iq |
| `dcdc_ripple` | BUCK 纹波 | scope | Vpp / RMS |
| `dcdc_psrr` | DCDC PSRR（可选） | scope | dB @ 频点 |
| `dcdc_load_transient` | 负载瞬态响应 | scope | 过冲/下冲/恢复时间 |
| `dcdc_inductor_current` | 不同负载下电感电流 | scope | 波形特征 |

> 说明：每个子页面内部以"测试项清单（勾选）+ 统一参数区 + 执行/日志区"组织，用户勾选需要跑的项，一次执行产出一份合并报告。可测项以矩阵驱动，未接示波器时自动灰化 `(scope)` 项。

---

## 3. 目录与文件规划（新增）

遵循 `ui/pages/<功能分类>/` 分包与 `core/<功能>/<子项>/worker+analysis` 分层。

```
ui/pages/module_test/
├── __init__.py                 # 含 MODULE_VERSION = "0.0.0"
├── module_test_ui.py           # 顶层容器（隐藏 tab 的 QTabWidget，切换 LDO/DCDC）
├── ldo_test_ui.py              # LDO 子页面
├── dcdc_test_ui.py             # DCDC 子页面
└── widgets.py                  # 测试项清单表、参数网格等复用控件（可选）

core/module_test/
├── __init__.py
├── report.py                   # 报告构建（HTML + Excel/CSV），可复用 orchestrator/reports.py 思路
├── result_model.py             # 统一结果数据结构（ModuleTestResult / ItemResult）
├── ldo/
│   ├── __init__.py
│   ├── ldo_runner.py           # QThread 编排：按勾选项串行调度各 item worker
│   └── items/                  # 单测试项算法/worker（可复用 core/pmu_test 内已有实现）
│       ├── __init__.py
│       ├── vout_scan.py
│       ├── load_line_reg.py
│       ├── quiescent.py
│       ├── ripple_psrr.py      # 依赖示波器
│       └── load_transient.py
└── dcdc/
    ├── __init__.py
    ├── dcdc_runner.py
    └── items/
        ├── __init__.py
        ├── vout_scan.py
        ├── efficiency.py       # 复用 core/pmu_test/dcdc/dcdc_worker.py
        ├── load_line_reg.py
        ├── quiescent.py
        ├── ripple_psrr.py
        ├── load_transient.py
        └── inductor_current.py

helps/
├── module_test_ldo.html        # 复制 helps/pmu_dcdc_efficiency.html 改内容
└── module_test_dcdc.html

resources/icons/
├── module_test.svg             # 侧边栏按钮图标（SVG，禁 .ico）
└── module_test_thumb.svg
```

> 复用策略：DCDC 效率直接调用 [dcdc_worker.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/pmu_test/dcdc/dcdc_worker.py)；Output Voltage 扫描可参考 [pmu_output_voltage.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/pages/pmu_test/pmu_output_voltage.py) 的 core 路径，避免重复造轮子。

### 3.1 AI Assist 相关（❗不新增独立文件，均为内嵌 + 改现有）

> 关键结论：现有 PMU/Charger 等页面的 AI 能力**没有独立 AI 文件**——契约方法（`ai_*`）与 `UIActionSpec` 登记都**内嵌在页面 `.py` 里**，core 侧只需在**既有** `core/ai/*` 文件里补几条数据。因此 `ui/pages/module_test/` 与 `core/module_test/` 下**不新建任何 AI 专属文件**。

**A. 内嵌进新增页面文件（无新文件）**
```
ui/pages/module_test/ldo_test_ui.py
  └─ ai_capabilities / ai_get_config / ai_apply_config /
     ai_start_test / ai_stop_test / ai_get_result_summary   # §8.1 契约方法
  └─ _register_ai_ui_actions()  → self._ui_action_registry.register_many([...])  # §8.2 白名单
ui/pages/module_test/dcdc_test_ui.py
  └─ 同上（page_key=module_test_dcdc）
```

**B. 改动既有 `core/ai/*` 文件（不新建，仅增数据/分支）**
```
core/ai/providers/page_provider.py   # _PAGE_LABELS 增 "module_test": "Module 测试（LDO/DCDC）"
core/ai/profiles.py                  # AI_PROFILES 增 "module_test_ldo" / "module_test_dcdc" 两条 profile
                                     #   （含 label / system 提示 / quick_actions，仿 pmu_dcdc_efficiency 条目）
```
> `core/ai/page_contract.py` 的 `ACTION_CAPABILITY_MAP`、`core/ai/ui_action_registry.py`、各 `handlers/*`、`dispatcher.py` **均无需改动**——通用动作恒保留，页级动作依 `ai_capabilities()` 自动裁剪，白名单动作经统一 `ui_invoke` 派发。

**C. 改动既有 `ui/main_window.py`（§8.3 已列，归此处统一登记）**
```
ui/main_window.py
  └─ _get_current_help_key()      # 增 module_test → module_test_ldo/dcdc 分支
  └─ resolve_active_ai_page()     # module_test 纳入 Tab 下钻集
  └─ _current_active_page()       # 补 "module_test": self.module_test_ui
  └─ _current_module_version()    # 补 "module_test": "ui.pages.module_test"
```

**D. 新增运行期 AI 记忆库目录（`docs/kk_lab_ai_memory/`）**

> 依据 [_shared/README.md](file:///d:/CodeProject/TRAE_Projects/KK_Lab/docs/kk_lab_ai_memory/_shared/README.md) 与 [_shared/conventions.md](file:///d:/CodeProject/TRAE_Projects/KK_Lab/docs/kk_lab_ai_memory/_shared/conventions.md)：记忆库按「左侧导航 4 大组 / 业务簇伞目录 / page_key 子目录」组织，目录名唯一来源是 `MainWindow._get_current_help_key()`。Module Test 属 **AUTOMATION** 组，需建 `module_test` 伞目录 + 两个子页目录（page_key 与 §8.3 一致）。

```
docs/kk_lab_ai_memory/automation/module_test/     # 业务簇伞目录（总记忆）
├── memory.md            # LDO/DCDC 模块测试通用背景、被测项矩阵、参数含义
├── lessons.md           # 跨子页共性踩坑/排障结论
├── test_items.md        # 通用测试项（§2 LDO 7 项 + DCDC 9 项抽象）
├── test_cases.md        # 结构化用例（输入/步骤/期望/判定）
├── quick_actions.md     # 簇级快捷指令
├── module_test_ldo/     # page_key=module_test_ldo
│   ├── memory.md
│   ├── lessons.md
│   ├── test_items.md
│   ├── test_cases.md
│   └── quick_actions.md
└── module_test_dcdc/    # page_key=module_test_dcdc
    ├── memory.md
    ├── lessons.md
    ├── test_items.md
    ├── test_cases.md
    └── quick_actions.md
```

> 说明（对齐现有 `pmu_test/` 簇）：伞目录承载跨子页总记忆，子目录承载各 page_key 私有记忆。5 类文件职责见 README §4；`quick_actions.md` 与 §8.3 补的 `profiles.py` 中 `AI_PROFILES[...].quick_actions` 相互对应（profile 是运行期来源，记忆库是可读文档镜像）。落地时可只放模板骨架 + 首批条目，其余由 AI 运行期受控追加。本机私有沉淀镜像 `user_data/ai/kk_lab_ai_memory/<page_key>/*.local.md` 由运行期自动生成，**不纳入本次规划文件**。

---

## 4. 架构与分层

```
main.py
  └─ ui/main_window.py ── 创建 ModuleTestUI(顶层容器)
        └─ ui/pages/module_test/module_test_ui.py
              ├─ LDOTestUI      (ui/pages/module_test/ldo_test_ui.py)
              └─ DCDCTestUI     (ui/pages/module_test/dcdc_test_ui.py)
                    │  仅负责：参数读写、勾选项、启动/停止、进度与日志展示、报告触发
                    ▼ Signal/Slot（禁 UI 直连仪器）
        core/module_test/ldo/ldo_runner.py  (QThread)
        core/module_test/dcdc/dcdc_runner.py (QThread)
              └─ items/*  →  instruments/factory.py 创建的 N6705C / Scope / Chamber
                    └─ core/module_test/report.py  →  Results/ 落盘 + HTML/Excel
```

分层铁律（复述以自检）：
- UI 层禁止阻塞 IO、禁止 `time.sleep`、禁止直接 `N6705C(resource)`；耗时全部走 `*_runner.py` 的 QThread，跨线程只用 Signal/Slot。
- `core/module_test/` 与 `items/` 禁依赖 Qt Widget（可依赖 `QtCore` 的 QThread/Signal，参照现有 worker）。
- 仪器一律走 `instruments/factory.py`；Mock 模式（`DEBUG_MOCK`）下全流程可空跑。
- 日志统一 `log_config.get_logger(__name__)`，异常 `exc_info=True`，禁裸 `except`、禁 `print`。

---

## 5. UI 设计

### 5.1 顶层容器 `ModuleTestUI`
仿 [PMUTestUI](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/pages/pmu_test/pmu_test_ui.py)：
- 内含 `QTabWidget` 且 `tabBar().hide()`，两页：`LDO` / `DCDC`。
- 构造参数：`n6705c_top`、`mso64b_top`、`chamber_ui`、`instrument_manager`、`ui_action_registry`。
- 暴露 `set_current_test(key)` / `get_current_test()` / `_sync_from_top()`，与 nav_controller 的 tab_map 对齐。

```python
TEST_TAB_MAP = {"ldo": 0, "dcdc": 1}
```

### 5.2 子页面 `LDOTestUI` / `DCDCTestUI`
统一区块结构（自上而下）：
1. **仪器连接区**：复用 `ui/modules/n6705c_module_frame.py` 的 `N6705CConnectionMixin`；需示波器项时加示波器连接 Frame。
2. **通道/被测配置区**：Vin/Vout/Iload 通道映射、被测 LDO/DCDC 选择、寄存器挡位范围。
3. **测试项清单区**：`QTableWidget`/勾选列表，逐项勾选，`(scope)` 项在未接示波器时禁用+提示。
4. **统一参数区**：负载范围、频点、纹波带宽、平均次数、（可选）温箱温度点。
5. **执行/日志区**：`ExecutionLogsFrame` + `QSplitter(Qt.Vertical)`（**铁律**：禁直接 addWidget / setMaximumHeight）；含 `start_test_btn` / `stop_test_btn` / 进度条。
6. **报告区**：执行结束后"打开报告"按钮（`QDesktopServices.openUrl`）。

控件规范（复述铁律）：
- 数值 QLabel 必含单位：`名称 (单位)`，如 `Vout (mV)`、`效率 (%)`。
- QComboBox/QPushButton 高度用自身 ID 选择器 `#objectName` 钉 `min-height:22px` 自洽，页面父级 QSS 禁裸 `QComboBox/QPushButton{min-height}`。
- QDialog 必传 `parent=self`；OK/Cancel 显式 default/autoDefault 二元化。
- 样式复用 `ui/styles/` 常量（`SCROLLBAR_STYLE` / `START_BTN_STYLE`），禁大段内嵌 setStyleSheet。

### 5.3 子页面公共接口（供顶层容器 & AI 动作调用）
对齐现有页面：`get_test_config()` / `update_test_result(result)` / `clear_results()` / `set_system_status(status, is_error)`；
并按 [page_contract](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/ai/page_contract.py) 注册 `CAP_GET_CONFIG / CAP_APPLY_CONFIG / CAP_START_TEST / CAP_STOP_TEST / CAP_GET_RESULT`（与 iterm_test.py 一致）。

---

## 6. core 编排（Runner）

`ldo_runner.py` / `dcdc_runner.py` 为 `QThread` 子类，职责：
- 输入：`config`（勾选项 + 参数 + 通道映射）、仪器句柄（N6705C/Scope/Chamber，Mock 或真机）。
- 逐项调用 `items/<item>.run(...)`，每项返回标准化 `ItemResult`。
- 信号：`progress(int, str)`、`item_finished(str, dict)`、`log(str)`、`finished(ModuleTestResult)`、`failed(str)`。
- 支持 `stop()`（协作式中断，检查标志位，禁强杀线程）。
- 温箱联动（可选）：外层按温度点循环，等待温箱到温后再跑勾选项。

单测试项 `items/*.py` 只做"配置仪器 → 采样 → 计算 → 返回 ItemResult"，纯逻辑部分可拆到 `*_analysis.py`（对齐 `core/pmu_test/<x>/<x>_analysis.py`）。

---

## 7. 结果与报告体系

### 7.1 统一数据模型（`result_model.py`）
```
ItemResult:
  item_key, name, unit, passed(bool|None), measured(dict/list),
  raw_csv_path(str|None), waveform_png(str|None), notes, ts
ModuleTestResult:
  module_type("ldo"|"dcdc"), chip_name, operator, temperature,
  started_at, finished_at, items: list[ItemResult], summary(dict)
```

### 7.2 落盘规范
- 目录：`Results/module_test/<ldo|dcdc>/<chip>_<YYYYmmdd_HHMMSS>/`；写前 `os.makedirs(..., exist_ok=True)`。
- 原始数据：每项一份 CSV（`csv`/`openpyxl`）；波形项保存示波器截图 PNG（调用现有 scope `capture_screen`）。
- 汇总报告：
  - **HTML**（主）：参照 [orchestrator/reports.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/orchestrator/reports.py) 的 `build_html_report` 风格，含标题、芯片/操作员/温度元信息、逐项 PASS/FAIL 表、关键数值、内嵌波形图。
  - **Excel**（可选）：`openpyxl` 一测试项一 Sheet + 汇总 Sheet。
- 报告生成在 `core/module_test/report.py`，UI 只拿路径打开，不做 IO。

### 7.3 判定
- 每项支持可配置阈值（默认给经验值，允许在参数区覆盖）；`passed=None` 表示仅记录不判定。
- 汇总 `summary` 统计 PASS/FAIL/未判定数量，报告顶部显示总体结论。

---

## 8. AI Assist 集成（页面受控 + UI 动作白名单）

> 依据 [page_contract.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/ai/page_contract.py)、[ui_action_registry.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/ai/ui_action_registry.py) 与 `AIAssist_PageScopedControlPlan`。核心原则：**core 不反向依赖 ui**，页面以鸭子类型实现契约方法 + 声明式登记具名 UI 动作，枢纽（MainWindow）据 `page_key` 路由与裁剪，新增页面**零改 core / 零改 handler**。

### 8.1 页面契约（`AIControllablePage`）
`LDOTestUI` / `DCDCTestUI` 各自实现（与 [pmu_dcdc_efficiency.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/pages/pmu_test/pmu_dcdc_efficiency.py#L1711-L1786) 完全同构）：

| 方法 | 能力常量 | 语义 |
|---|---|---|
| `ai_capabilities()` | — | 返回本页真实支持子集 |
| `ai_get_config()` | `CAP_GET_CONFIG` | 只读当前配置快照（含勾选项、通道映射、参数、温度点）；无数据返回 `None` |
| `ai_apply_config(payload)` | `CAP_APPLY_CONFIG` | 落地配置草案到控件；**运行中拒绝改配置**，返回 `(ok, message)` |
| `ai_start_test()` | `CAP_START_TEST` | 启动前校验连接/运行态/示波器依赖项；追加 `[AI]` 日志；返回 `(ok, message)` |
| `ai_stop_test()` | `CAP_STOP_TEST` | 协作式停止；返回 `(ok, message)` |
| `ai_get_result_summary()` | `CAP_GET_RESULT` | 读最近 `ModuleTestResult` 摘要（PASS/FAIL/未判定计数、报告路径）；无结果返回 `None` |

```python
def ai_capabilities(self) -> set[str]:
    return {CAP_GET_CONFIG, CAP_APPLY_CONFIG, CAP_START_TEST, CAP_STOP_TEST, CAP_GET_RESULT}
```

返回值约定（复述铁律）：读类无数据返回 `None`；写/控制类返回 `(ok, message)`，`ok=False` 时 message 给可读原因 + 可执行引导（如"未连接示波器，`ldo_ripple` 等示波器项将跳过"）。契约方法内异常一律 `logger.error(..., exc_info=True)` 后降级，禁裸 `except`。

`ai_get_config()` 设计要点：只暴露**当前勾选项真正会遍历**的维度（对齐 pmu_dcdc_efficiency 的做法），避免把 UI 上常驻但未勾选的字段（如未勾 `line_reg` 时的 Vin 扫描范围）当成会执行的维度，误导 AI 臆造组合数。

### 8.2 具名 UI 动作白名单（`UIActionSpec`）
页面构建控件后一次性 `register_many`，`handler` 直接指向按钮原槽（行为与人点一致），仅白名单内动作可被 AI 触发。构造参数已含 `ui_action_registry`（顶层容器透传给两个子页）。示例：

```python
self._ui_action_registry.register_many([
    UIActionSpec(id="module_test_ldo.open_report", label="打开报告",
                 page_key="module_test_ldo", handler=self._on_open_report,
                 risk="low", confirm=False,
                 enabled_when=lambda: self._last_report_path is not None),
    UIActionSpec(id="module_test_ldo.clear_results", label="清空结果",
                 page_key="module_test_ldo", handler=self._on_clear_results,
                 risk="low"),
    UIActionSpec(id="module_test_ldo.select_all_items", label="全选测试项",
                 page_key="module_test_ldo", handler=self._on_select_all_items,
                 risk="low", confirm=False),
])
```

DCDC 子页同理，`page_key="module_test_dcdc"`。start/stop/apply_config 已由契约方法覆盖，**无需**再登记为 UI 动作，避免重复。页面销毁时枢纽 `unregister_page(page_key)` 清理（沿用现有机制，无需页面额外处理）。

### 8.3 page_key 与子页下钻（枢纽侧改动）
Tab 容器页需支持 AI 下钻到当前子页，改动点：

1. [main_window.py `_get_current_help_key()`](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/main_window.py#L1598-L1625)：新增 `module_test` 分支，映射当前子页 key → page_key：
   ```python
   elif self.current_instrument_ui == "module_test":
       key_map = {"ldo": "module_test_ldo", "dcdc": "module_test_dcdc"}
       return key_map.get(self.nav.current_module_test_key, "module_test_ldo")
   ```
   该返回值同时用作 help HTML 文件名、AI `page_key`、UI 动作归属 key，三者必须一致（因此 help 文件命名为 `module_test_ldo.html` / `module_test_dcdc.html`，与 §3 一致）。
2. [`resolve_active_ai_page()`](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/main_window.py#L1285-L1311)：把 `module_test` 加入需下钻的 Tab 容器集合（与 `pmu_test`/`charger_test` 同支），下钻到 `tab_widget.currentWidget()`，使能力裁剪落到具体子页。
3. [`_current_active_page()`](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/main_window.py#L1313-L1321) 与 [`_current_module_version()`](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/main_window.py#L1626-L1648)：补 `"module_test": self.module_test_ui` / `"module_test": "ui.pages.module_test"`。

> `ACTION_CAPABILITY_MAP` 与 `to_tools(capabilities)` 的按页裁剪逻辑**无需改动**——通用动作恒保留，页级动作依据子页 `ai_capabilities()` 自动裁剪。

4. [page_provider.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/ai/providers/page_provider.py) `_PAGE_LABELS`：增 `"module_test": "Module 测试（LDO/DCDC）"`，让 AI 上下文能把当前页翻译成可读标签。
5. [profiles.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/ai/profiles.py) `AI_PROFILES`：增 `"module_test_ldo"` / `"module_test_dcdc"` 两条 profile（`label` / `system` 提示 / `quick_actions`），仿现有 `pmu_dcdc_efficiency` 条目，使 AI 在本页有贴合的引导与快捷动作。

### 8.4 AI 回填可视化（高亮）
`ai_apply_config` 落地后，对被 AI 修改的控件套用临时高亮（对齐现有 `_AI_HIGHLIGHT_QSS = "border: 1px solid #15d1a3;"` + `_AI_HIGHLIGHT_MS = 1500`），并在 `ExecutionLogsFrame` 追加 `[AI] ...` 日志，与人工操作路径一致（控件状态照常经原信号/轮询刷新）。

### 8.5 权限 / 审计 / 确认
- 写/控制类动作（apply_config / start / stop / ui_invoke）经枢纽统一走 `PermissionChecker` + 二次确认 + `AuditLog`（现有链路，页面侧无需实现，仅需返回规范 `(ok, message)`）。
- `risk` 分级：`open_report`/`clear_results`/勾选类 = `low`；启动测试 = `medium`（含仪器动作）；本页无 `high`。

### 8.6 AI 相关验收
- [ ] 切到 Module Test 后 `page_context` = `module_test_ldo` / `module_test_dcdc`，随子页切换更新。
- [ ] AI `get_current_test_config` 只返回当前勾选项会遍历的维度。
- [ ] AI `generate_config_draft` → `apply_test_config_draft` 走确认闭环，落地后控件高亮 + `[AI]` 日志。
- [ ] AI `start_test`：未连接仪器/示波器依赖缺失时返回可读拒绝原因，不误启动。
- [ ] AI `list_ui_actions` 仅列出本页 `enabled` 的白名单动作；跨页调用被拒。
- [ ] AI `get_test_result_summary` 返回 PASS/FAIL 计数与报告路径。

---

## 9. 侧边栏集成（AUTOMATION）

参照 PMU/Charger 的 nav 接线，改动点：

1. [nav_controller.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/nav_controller.py)：
   - `__init__` 增 `self.current_module_test_key = "ldo"` 与
     ```python
     self.module_test_tab_map = {"ldo": 0, "dcdc": 1}
     ```
   - AUTOMATION 分组下新增 `self.module_test_btn = SidebarNavButton("Module Test", ...)`，`left_nav_layout.addWidget(...)`，加入 `nav_button_group`。
   - 新增 `SidebarSubMenu([("ldo","LDO"),("dcdc","DCDC")])` 及 `_show_module_submenu` / `_hide_module_submenu_if_needed` / `_on_module_submenu_clicked`（复制 pmu 三方法改名）。
   - `installEventFilter` + `eventFilter` 分支 + 快捷键表补一项。
2. [main_window.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/main_window.py)：
   - `import ModuleTestUI`；新增 `self.module_test_ui = None`。
   - 新增 `_create_module_test_ui(self, selected_test=None)`（复制 `_create_pmu_test_ui` 改名，传 `mso64b_top`）。
   - `module_test_btn.clicked.connect(self._on_nav_button_clicked)`；`_hide_all_instrument_uis` 纳入新页面。

> 放置顺序建议：AUTOMATION 组内 PMU Test / Charger Test 之后、Consumption 之前，符合"模块级测试"的语义定位。

---

## 10. Mock / 回归

- `DEBUG_MOCK=True` 下：Runner 用 `MockN6705C` 等，全部勾选项可空跑出假数据并生成报告，验证 UI→core→report 闭环。
- 手动回归清单：
  - [ ] 侧边栏 Module Test 出现，悬停出 LDO/DCDC 子菜单，切换正常。
  - [ ] 未接示波器时 `(scope)` 项灰化并提示。
  - [ ] Start 后进度/日志刷新，Stop 可协作中断。
  - [ ] `Results/module_test/...` 生成 CSV + HTML（+可选 Excel），波形项含 PNG。
  - [ ] "打开报告"能在浏览器打开 HTML。
  - [ ] `?` 帮助按钮打开对应 help HTML。
  - [ ] lint 通过；无 `print`、无裸 `except`、UI 无阻塞 IO。

---

## 11. 同步矩阵（落地后必更）

依据 [08_CHECKLISTS 同步矩阵](../../08_CHECKLISTS.md) 与项目规则 §4：
- [ ] `DIRECTORY_STRUCTURE.txt`：新增 `ui/pages/module_test/`、`core/module_test/`。
- [ ] `spec/kk_lab.spec`：纳入新增图标 SVG、help HTML 资源。
- [ ] `helps/`：新增 `module_test_ldo.html` / `module_test_dcdc.html`。
- [ ] `requirements.txt`：若报告用 `openpyxl` 未在则补（当前已有则免）。
- [ ] `docs/kk_lab_ai_memory/automation/module_test/`：新增记忆库伞目录 + `module_test_ldo/` / `module_test_dcdc/` 两个子页目录，各含 5 类 md（见 §3.1-D）。
- [ ] `docs/ai/memory.md`：沉淀本次协作上下文与复用点（AI coding 侧，与运行期记忆库区分）。
- [ ] `docs/ai/decisions/`：如做了取舍（如仅 HTML 不出 Excel）记录决策。
- [ ] AI 侧（改现有文件，不新建）：`core/ai/providers/page_provider.py` 补 `_PAGE_LABELS`、`core/ai/profiles.py` 补两条 `AI_PROFILES`；`main_window.py` 补 page_key 下钻（§8.3）。
- [ ] 各模块 `__init__.py` 的 `MODULE_VERSION` 初始 `0.0.0`。

---

## 12. 实施顺序建议（后续动代码时）

1. 骨架：`ui/pages/module_test/` 三个 UI（先空跑 UI、隐藏 tab、接 nav）。
2. core：`result_model.py` + `report.py` + 两个 runner（先跑通 Mock 假数据 + HTML 报告）。
3. 逐项填 `items/*`：先复用 DCDC 效率与 Output Voltage，再补纯 n6705c 项，最后补示波器项。
4. Excel/波形增强 + 阈值判定。
5. AI 契约方法 + UIActionSpec 登记 + 枢纽 page_key 下钻（§8.3：含 `page_provider.py` / `profiles.py`）。
6. 建 `docs/kk_lab_ai_memory/automation/module_test/` 记忆库骨架（伞目录 + 两子页 × 5 md，§3.1-D）。
7. help HTML + 图标 + 同步矩阵收尾 + lint 回归。

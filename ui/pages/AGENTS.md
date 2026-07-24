# ui/pages/ — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../AGENTS.md) 硬红线。仅存放功能页面局部知识；通用 UI 规范回指 docs/ai。

## 加载指针（AI 按需拉取）

- **新增 / 修改 UI 页面** → @see [docs/ai/06_PAGE_GUIDE.md](../../docs/ai/06_PAGE_GUIDE.md)
- **Qt / UI 通用规范** → @see [docs/ai/01_CONVENTIONS.md §6](../../docs/ai/01_CONVENTIONS.md)
- **巨石重构与 View/Controller/Worker/Analysis 拆分** → @see ADR [005-monolith-refactor](../../docs/ai/decisions/005-monolith-refactor.md)
- **跨模块坑** → @see [docs/ai/03_GOTCHAS.md](../../docs/ai/03_GOTCHAS.md)

## 本模块职责与边界

- **职责**：功能页面 View（布局、交互、展示）；按仪器 / 功能分包。
- **上游**：用户操作、`ui/main_window.py` 导航。
- **下游**：`core/` controller / test 类（Signal/Slot）、`ui/modules/` 连接 Mixin、`ui/widgets/` 通用控件。
- **铁律**：页面**禁止**直接发 VISA / 串口 / I2C 阻塞调用；禁止在槽函数里 `time.sleep`；跨线程更新 UI 必须走 Signal/Slot。

## 接口契约（对外不可破坏）

- 页面类多继承：`QWidget` + 对应 `ui/modules/` 连接 Mixin + `ExecutionLogsModuleFrame`（如需日志区）。
- 业务执行路径：读取参数 → 构造 `core/<feature>/` 测试 / controller → 订阅 `progress / point_ready / finished` → `start()`。
- 结果刷新只通过 Signal/Slot；不直接操作仪器对象。
- 页面帮助：每个页面在 [helps/](../../helps/) 有对应 HTML，"?"按钮经 `QDesktopServices.openUrl` 打开。

## 局部约定

- **分包归属**：按仪器 / 功能放 `chamber/`、`charger_test/`、`consumption_test/`、`module_test/`、`n6705c_power_analyzer/`、`orchestrator/`、`oscilloscope/`、`pmu/`、`pmu_test/`、`vmin_hunter/`；新大类先建子包加 `__init__.py`。
- **样式**：复用 [ui/styles/](../styles/) 常量与 `get_page_base_qss()`；禁止在页面里散写大段 `setStyleSheet`。
- **弹窗**：所有 `QDialog` / 静态对话框必须显式传 `parent=self`；OK/Cancel 显式二元化 `default/autoDefault`。
- **数值控件 label**：物理量必须 `名称 (单位)`；多单位输入要维护"上次单位"记忆并动态更新 label。
- **耗时操作**：一律走 `core/` + QThread；Worker 不 import QtWidgets。

## 局部坑点

> 详细背景见 [docs/ai/03_GOTCHAS.md](../../docs/ai/03_GOTCHAS.md)。

- **§24 `get_page_base_qss()` 禁止全局 `min-height`**：会级联覆盖子控件 `setFixedHeight()`，挤占布局间距。需要标准高度的控件在 `page_extra` 中按 `#objectName` 单独设置。
- **§24.1 DarkComboBox 高度治理**：可复用控件必须用 ID 选择器 `QComboBox#darkCombo_<id>` 在自身 QSS 钉死 `min-height: 22px` + 上下 `padding: 2px`，不依赖父页面。
- **§25 Tab 状态盒模型一致**：用 `QPushButton` 模拟 tab 时，active/inactive 的 padding、border、margin 必须一致；视觉连接用同背景色 `border-bottom`，不要用 `border-bottom: none`。
- **§23 SVG 图标**：禁止 `QPixmap.setDevicePixelRatio()`，直接用逻辑大小渲染，详见 [ui/utils/icon_utils.py](../utils/icon_utils.py)。
- **§22 模组直接运行**：若页面内嵌 `ui/modules/*_module_frame.py` 的 Demo 块，注意其已注入 `sys.path` 兼容 `python ui\modules\xxx.py` 直接运行。
- **ADR 005 遗留**：`serialCom_module_frame.py` 主壳、`consumption_test.py` 仍有可拆分空间，修改时按既有 View/Controller/Worker/Analysis 范式继续切，不要新增上帝类。

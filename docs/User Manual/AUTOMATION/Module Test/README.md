# Module Test

Module Test 是芯片 **LDO / DCDC 模块**的独立测试套件，与 PMU Test 解耦，使用轻量级纯函数 Runner，不依赖 PMU 的 QThread Worker，便于单独运行。

## 子页面索引

| 子页面 | 测试目标 | 主要仪器 |
|---|---|---|
| [LDO](./LDO.md) | LDO 模块测试项集合（输出电压、负载调整率、PSRR 等） | N6705C + 示波器 + 温箱 |
| [DCDC](./DCDC.md) | DCDC 模块测试项集合（效率、瞬态响应、纹波等） | N6705C + 示波器 + 温箱 |

## 页面入口

- 导航栏 → `AUTOMATION` → `Module Test` → 悬停展开子菜单选择 LDO 或 DCDC。
- 对应源码：`ui/pages/module_test/module_test_ui.py`（容器，隐藏顶部 Tab）。
- 子页面：`ldo_test_ui.py`（`LDOTestUI`）/ `dcdc_test_ui.py`（`DCDCTestUI`），均继承 `ModuleTestSubPageBase`。

## 共用约定

- **测试项注册表**：每个子页面绑定一个 items 注册表（`core/module_test/ldo/items.py::LDO_ITEMS` / `core/module_test/dcdc/items.py::DCDC_ITEMS`），列出该模块所有可用测试项。每个测试项含名称、配置 schema、PASS/FAIL 判据。
- **Runner**：`LDOTestRunner` / `DCDCTestRunner` 是轻量级纯函数实现，不耦合 Qt，可独立运行（也支持被 Orchestrator 调用）。
- **页面 Page Key**：`module_test_ldo` / `module_test_dcdc`，用于 AI 枢纽路由与 page_key 隔离。
- **仪器连接**：通过 Mixin 复用 N6705C / 示波器 / 温箱会话。
- **测试项表**：UI 表格高度按 `header + 30px × 行数` 计算，SizePolicy 垂直 Expanding，避免内容截断。
- **结果文件**：输出到 `Results/module_test_<ldo|dcdc>/<时间戳>/`，含 CSV 与 HTML 报告。
- **AI 契约**：两个子页面均实现 `ai_capabilities()` 提供 5 个能力。

## 教训沉淀

> Reusing PMU's QThread worker for DCDC efficiency caused Qt coupling; reimplemented as lightweight pure functions to keep Module Test independent and runnable.

DCDC 效率测试曾复用 PMU 的 QThread Worker，导致 Qt 耦合；后重写为轻量级纯函数 Runner，保证 Module Test 独立可运行。详见 `docs/kk_lab_ai_memory/`。

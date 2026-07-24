# ui/modules/ — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../AGENTS.md) 硬红线。仅存放可复用 UI 模块 / 连接 Mixin 的局部知识。

## 加载指针（AI 按需拉取）

- **新增 UI 页面如何使用 Mixin** → @see [docs/ai/06_PAGE_GUIDE.md](../../docs/ai/06_PAGE_GUIDE.md)
- **Qt / UI 通用规范** → @see [docs/ai/01_CONVENTIONS.md §6](../../docs/ai/01_CONVENTIONS.md)
- **跨模块坑** → @see [docs/ai/03_GOTCHAS.md](../../docs/ai/03_GOTCHAS.md)

## 本模块职责与边界

- **职责**：可复用 UI 组件与"搜索 + 连接 / 断开 + 状态指示"连接区域 Mixin、执行日志区、串口 / I2C 等通用面板。
- **上游**：`ui/pages/` 各功能页多继承混入。
- **下游**：`instruments/factory.py`（创建仪器）、`ui/styles/`（样式常量）、`resources/`（SVG 图标）。
- **铁律**：Mixin 本身**不直接**做阻塞 IO；搜索 / 连接走 `QThread + QObject` 后台 Worker。

## 接口契约（对外不可破坏）

- 连接 Mixin 统一提供：`_build_<instrument>_frame()` 返回 QWidget；内部维护仪器实例并暴露给页面。
- 仪器实例必须通过 `instruments.factory.create_*` 获取，禁止直接 `new` 驱动类。
- 必须支持 `DEBUG_MOCK` 分支，使用 `instruments.mock.mock_instruments.MockXxx`。
- `ExecutionLogsFrame` 必须经工厂方法 `ExecutionLogsFrame.wrap_with(...)` 装配，禁止手写 `QSplitter` 样板。

## 局部约定

- **文件布局**：通用连接 Mixin 为 `*_module_frame.py`；串口模块在 `serialCom_module/` 子包；I2C 模块在 `IIC_Module/` 子包。
- **样式**：复用 [ui/styles/](../styles/) 常量；通用图标优先用 `resources/modules/SVG_Common/` 下 SVG，不新增位图。
- **日志区**：使用 `ExecutionLogsFrame.wrap_with(main_content, show_progress=..., stretch=(4, 1))`；禁止直接 `layout.addWidget(self.execution_logs)`，禁止 `setMaximumHeight`。
- **控件高度**：可复用控件（如 DarkComboBox）用自身 QSS ID 选择器钉死高度，不依赖父页面。

## 局部坑点

> 详细背景见 [docs/ai/03_GOTCHAS.md](../../docs/ai/03_GOTCHAS.md)。

- **§22 直接运行入口**：凡带 `if __name__ == "__main__":` Demo 块、且顶部 `from ui.* / instruments.*` 导入的文件，必须在**最顶部**注入项目根 `sys.path`，否则 `python ui\modules\xxx.py` 会 `ModuleNotFoundError: No module named 'ui'`。参考 [keysight_53230a_module_frame.py](./keysight_53230a_module_frame.py) 前 13 行。
- **§6.4 ExecutionLogsFrame**：必须与主内容一起放入 `QSplitter(Qt.Vertical)`，手柄用隐式样式；统一走 `wrap_with` 工厂，禁止绕过。
- **§24 高度级联**：嵌入页面时，父页面 QSS 的裸 `QComboBox { min-height }` 会穿透进模块内部；模块自身控件须用 ID 选择器自洽（见 §24.1）。
- **§23 SVG 渲染**：模块内 SVG 图标禁止 `setDevicePixelRatio`，直接用逻辑大小渲染。
- **§5 VISA 地址**：搜索按钮扫描 → 下拉框选择 → 传给 `factory.create_*`，禁止硬编码地址。

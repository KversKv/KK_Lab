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
- **ChamberConnectionMixin 连接态 = 推送 + 拉取双通道**：`init_chamber_connection` 末尾自动从 manager 补拉一次已有 chamber 会话（页面懒创建会错过 `session_connected` 广播），`build_chamber_connection_widgets` 末尾据拉取结果刷连接态 UI；公开 `sync_chamber_from_manager()`（对齐 `sync_n6705c_from_top` 语义，变化才 emit `chamber_connection_changed`），页面构造尾部 / 容器 `_sync_from_top` 应级联调用。
- 仪器实例必须通过 `instruments.factory.create_*` 获取，禁止直接 `new` 驱动类。
- 必须支持 `DEBUG_MOCK` 分支，使用 `instruments.mock.mock_instruments.MockXxx`。
- `ExecutionLogsFrame` 必须经工厂方法 `ExecutionLogsFrame.wrap_with(...)` 装配，禁止手写 `QSplitter` 样板。

## 局部约定

- **文件布局**：通用连接 Mixin 为 `*_module_frame.py`；串口模块在 `serialCom_module/` 子包；I2C 模块在 `IIC_Module/` 子包。
- **串口热插拔**：`serialCom_module/serial_hotplug.py` 提供 `SerialPortHotplugMonitor` **模块级单例**（Windows `WM_DEVICECHANGE` 原生事件 + 600ms 去抖 + 后台 QThread 重扫，端口集合变化才广播 `ports_changed(list)`）。`SerialComMixin` 完整模式在 `complete_serialComWidget()` 尾部经 `_sc_start_port_hotplug()` 接入（`DEBUG_MOCK` 下不启用）；多页面共享同一单例，禁止各页面自建监控线程。串口列表条目格式统一 `"{device} - {description}"`，热插拔回调据此静默重建 `_sc_port_combo` 并保留当前选择。
- **样式**：复用 [ui/styles/](../styles/) 常量；通用图标优先用 `resources/modules/SVG_Common/` 下 SVG，不新增位图。
- **日志区**：使用 `ExecutionLogsFrame.wrap_with(main_content, show_progress=..., stretch=(4, 1))`；禁止直接 `layout.addWidget(self.execution_logs)`，禁止 `setMaximumHeight`。
- **控件高度**：可复用控件（如 DarkComboBox）用自身 QSS ID 选择器钉死高度，不依赖父页面。
- **McuPwrResetConfigMixin 的 Status 行**：仅保留 GPIO 下拉 + “唤醒电平” High/Low 切换（`PolarityToggle(options=_STATUS_WAKE_LEVEL_OPTIONS)`），不再有 Pulse/Level 模式；`status_mode`/`mcu_status_toggle` 已移除。唤醒=`mcu_io.out(pin, active)`，睡眠=`mcu_io.out(pin, 1-active)`（`active = 1 if status_polarity == "rising"(High) else 0`）。`mcu_set_status(active=True/False)` 即按此映射输出电平。`status_polarity` 键仍复用 `rising/falling`（High=rising、Low=falling）以兼容页面读取。Ctrl 行仍保留 Pulse/Level `ModeToggle`。
- **MCU 家族共享会话**：`McuIoConnectionMixin`（含 `McuPwrResetConfigMixin`）与 `Ch9114GpioMixin` 接入 `InstrumentManager` 后，CH9114F 与 YD-RP2040 均走共享会话：CH9114F=`ch9114f:default`、YD-RP2040=`mcu_io:default`（`_mcu_io_target_session_id()` 按当前类型解析，`_is_mcu_io_family_session()` 判断家族联动）。搜索/连接/断开统一走 `manager.scan_async/connect_async/disconnect_async`；manager 为 None 时 Mixin 回退本地 worker 路径。断开时用 `_resolve_mcu_io_session_id()`（类型切换后按已持实例反查），防漏断旧会话。
- **SerialCom 多面板控制跟随**：顶部 Connect/Pause/Stop 按 `_sc_active_log_panel_index` 分发到聚焦面板（Refresh 保持全局端口扫描）；焦点切换 / 面板连接变化统一经 `_sc_sync_top_control_state()` 回同步按钮文本/图标/勾选，新增面板控制入口必须调用它。额外面板 `paused=True` 时在 `_sc_extra_panel_on_data` 入口丢数据（与主面板语义一致）。
- **SerialCom 日志面板统一组件 `serial_log_panel.py:SerialLogPanel`**：主面板 / 额外内嵌面板 / 独立浮窗三处共用同一实现（工具栏/过滤/append/着色/批量刷新/auto-scroll/状态栏），差异仅经构造参数（`filter_mode=full|simple`、`status_bar=primary|basic|rxtx`、`show_save_button` 等）与钩子（`entry_renderer`/`ntp_timestamp_provider`/`raw_appended`/`export_fast_path`/`save_toggled`/`clicked`）注入。主面板经 `_build_sc_log_area`、额外面板经 `_build_extra_log_panel`（dict facade 别名组件属性）装配；**改日志/滚动/过滤逻辑只动组件一处，禁止在 Mixin/浮窗另起平行实现**。
- **SerialCom auto-scroll 冻结坑**：`QTextEdit` 贴底时 append 会被 Qt 自动钉底并触发 `valueChanged(max)`，"回底自动恢复"检测会误杀刚关闭的 auto-scroll（按钮关不掉=失效）。组件内统一防护：append 期间置 `appending` 守卫（滚动检测直接 return），且 auto-scroll 关闭时 append 后 `setValue(prev_value)` 恢复冻结位置。

## 局部坑点

> 详细背景见 [docs/ai/03_GOTCHAS.md](../../docs/ai/03_GOTCHAS.md)。

- **§22 直接运行入口**：凡带 `if __name__ == "__main__":` Demo 块、且顶部 `from ui.* / instruments.*` 导入的文件，必须在**最顶部**注入项目根 `sys.path`，否则 `python ui\modules\xxx.py` 会 `ModuleNotFoundError: No module named 'ui'`。参考 [keysight_53230a_module_frame.py](./keysight_53230a_module_frame.py) 前 13 行。
- **§6.4 ExecutionLogsFrame**：必须与主内容一起放入 `QSplitter(Qt.Vertical)`，手柄用隐式样式；统一走 `wrap_with` 工厂，禁止绕过。
- **§24 高度级联**：嵌入页面时，父页面 QSS 的裸 `QComboBox { min-height }` 会穿透进模块内部；模块自身控件须用 ID 选择器自洽（见 §24.1）。
- **§23 SVG 渲染**：模块内 SVG 图标禁止 `setDevicePixelRatio`，直接用逻辑大小渲染。
- **§5 VISA 地址**：搜索按钮扫描 → 下拉框选择 → 传给 `factory.create_*`，禁止硬编码地址。
- **连接按钮 enable 状态必须成对恢复**：manager 异步路径在 `connect_async` 前 `setEnabled(False)` 后，所有状态同步出口（`sync_*_from_top` / `*_top_changed` / `connection_failed` 处理器）都必须 `setEnabled(True)`；否则按钮停在 disabled，`_xxx_disconnect_style` 里的 `QPushButton:disabled` 规则生效，Disconnect 红底被灰底覆盖（示波器在 module_test 页曾因此不变红，N6705C 因有 `_on_mixin_manager_connected` 恢复而正常）。
- **manager 断开失败也要恢复按钮**：`disconnect_async` 失败时 manager 发 `disconnect_failed(session_id, error)` 而非 `session_disconnected`，会话仍 connected；MCU 家族 Mixin 的 `_on_*_manager_disconnect_failed` 需把按钮恢复为已连接态（search 禁用、connect 可点），否则按钮永久卡 disabled。

# ui/pages/gpio — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../../AGENTS.md) 与 [ui/pages/AGENTS.md](../AGENTS.md) 硬红线。

## 本模块职责与边界

- **职责**：DUT GPIO 控制页（TOOLS 组）——Detect DUT → GPIO 网格 → 单脚 模式/电平/drv 控制。
- **下游**：`core/gpio/`（配置 + Worker）；页面**禁止**直接发 I2C。

## 局部约定

- **寄存器偏移硬约定**（各 bank 一致，见 `core/gpio/gpio_config.py`）：Out Set=+0x00 / Dir Set=+0x04 / Out Clr=+0x0C / Dir Clr=+0x10 / Input Read=+0x50；每 bank 32 GPIO，bit=(group%4)*8+pin。
- **芯片配置**：`chips/gpio_configs/<chip_name>.json` 按 `bes_chip_check()` 的 `chip_name` 匹配；drv_sel 独立地址区（bits_per_gpio=2→16脚/寄存器，4→8脚/寄存器，fast/slow 值按芯片填）；PU/PD 各一个独立寄存器区（1bit/GPIO），地址 null 时 UI 自动禁用上下拉按钮。
- **设备地址/位宽**：固定 BIT_32，dev 取 `chip_info["main_die_i2c_addr"]`（0x11/0x31 自适应）。
- **GPIO 命名**：`GPIO{group}{pin}`（Group0→GPIO00~07，Group1→GPIO10~17）；矩阵卡片另按 bank 内位号显示 `P{bit:02d}`。
- **线程链**：Worker finished 槽链里再起读线程统一走 `_defer_read`（页内单发 QTimer ≥50ms，重复延迟合并；03§26）；QThread 不挂父对象，`finished` 经 `_on_worker_done` 绑定分发，关窗清理走 `cleanup_threads()`（已注册 CleanupMixin；03§39）。
- 方向寄存器只有 set/clear 无回读地址，模式状态仅本页会话内记忆。
- **影子寄存器模型**：页面以 `_dir_shadow` / `_out_shadow`（按 bank）与 `_reg_shadow`（按地址，PU/PD/drv/任意写）维护会话影子；引脚模式、上下拉、drv、统计计数全部由影子推导，所有写操作（含批处理/掩码/位翻转）统一走 `_apply_actions()` 管道（嗅探→影子→仿真直写或 Worker）。
- **Simulated DUT**：页内仿真器（Bridge 按钮切换，不触碰硬件），影子即仿真寄存器；读 0x50 由方向/输出/上下拉/外部激励（`_pin_meta stim`）综合判定；切桥接清空全部会话状态。
- **7 视图 Tab**（QButtonGroup + QStackedWidget）：Matrix/Table/RegMap/Sniffer/JSON/CodeExport/ConfirmNote；页面级 QSS 常量 `_GPIO_PAGE_QSS` 一次性 `setStyleSheet`，控件高度一律 QSS `min-height==max-height` 钉死。

## 局部坑点

- **set/clear 寄存器整写**即可（写 1 生效位）；**PU/PD/drv 是普通 RW 寄存器**，必须 OP_BITS 位域写（DLL RMW），禁整写覆盖其他脚。
- **stack 页 / QScrollArea viewport 背景发白**：默认浅 palette（standalone/离屏）下二者不继承页面 QSS 底色，必须给视图页与滚动容器显式 `setObjectName("gpioViewPage")` / `QScrollArea` 命名 `gpioScroll` 并在页 QSS 钉背景色，否则嵌入/独立运行中间区域发白。

# ui/pages/gpio — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../../AGENTS.md) 与 [ui/pages/AGENTS.md](../AGENTS.md) 硬红线。

## 本模块职责与边界

- **职责**：DUT GPIO 控制页（TOOLS 组）——Detect DUT → GPIO 网格 → 单脚 模式/电平/drv 控制。
- **下游**：`core/gpio/`（配置 + Worker）；页面**禁止**直接发 I2C。

## 局部约定

- **寄存器偏移硬约定**（各 bank 一致，见 `core/gpio/gpio_config.py`）：Out Set=+0x00 / Dir Set=+0x04 / Out Clr=+0x0C / Dir Clr=+0x10 / Input Read=+0x50；每 bank 32 GPIO，bit=(group%4)*8+pin。
- **芯片配置**：`chips/gpio_configs/<chip_name>.json` 按 `bes_chip_check()` 的 `chip_name` 匹配；drv_sel 独立地址区（bits_per_gpio=2→16脚/寄存器，4→8脚/寄存器，fast/slow 值按芯片填）；PU/PD 各一个独立寄存器区（1bit/GPIO），地址 null 时 UI 自动禁用上下拉按钮。
- **设备地址/位宽**：固定 BIT_32，dev 取 `chip_info["main_die_i2c_addr"]`（0x11/0x31 自适应）。
- **GPIO 命名**：`GPIO{group}{pin}`（Group0→GPIO00~07，Group1→GPIO10~17）。
- **线程链**：Worker finished 槽内再起读线程须 `QTimer.singleShot(≥50ms)`（03§26）。
- 方向寄存器只有 set/clear 无回读地址，模式状态仅本页会话内记忆。

## 局部坑点

- **set/clear 寄存器整写**即可（写 1 生效位）；**PU/PD/drv 是普通 RW 寄存器**，必须 OP_BITS 位域写（DLL RMW），禁整写覆盖其他脚。

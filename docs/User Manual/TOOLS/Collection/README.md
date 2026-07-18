# Collection

Collection 是**辅助采集工具**集合，提供 MCU IO 控制、串口终端、I2C 寄存器读写三个独立工具页，常用于调试 DUT 的底层通讯。

## 子页面索引

| 子页面 | 用途 | 通信方式 |
|---|---|---|
| [MCU IO](./MCU%20IO.md) | MCU IO（YD-RP2040 / CH9114F）GPIO 控制 | USB 串口 |
| [KK Serials](./KK%20Serials.md) | 通用串口收发终端 | USB 串口 |
| [IIC Control](./IIC%20Control.md) | USB-I2C 寄存器读写、模板持久化、序列脚本 | USB-I2C |

## 页面入口

- 导航栏 → `TOOLS` → `Collection` → 悬停展开子菜单选择具体工具。
- 对应源码：`ui/modules/` 下的 `mcu_io_module_frame.py` / `serialCom_module/serialCom_module_frame.py` / `IIC_Module/i2c_mixin.py`，由 `main_window.py` 中的 `_CollectionPage` / `_KKSerialsPage` / `_I2cControlPage` 组装。

## 共用约定

- **三个工具完全独立**：可同时使用（如 MCU IO 控制 DUT 复位、KK Serials 监听 UART、IIC Control 读写 PMU 寄存器）。
- **暗色主题**：三个工具均采用 `#020817` / `#060f24` 深色背景 + `#dbe7ff` 文字，与主窗口风格一致。
- **状态指示**：`statusOk` 绿色 / `statusWarn` 橙色 / `statusErr` 红色，统一字号字重。
- **日志区**：MCU IO 自带 `ExecutionLogsFrame`；KK Serials / IIC Control 各有独立日志区。

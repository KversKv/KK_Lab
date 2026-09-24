# lib/i2c/ — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../AGENTS.md) 硬红线。仅存放本模块局部知识；通用规范回指 docs/ai。

## 加载指针（AI 按需拉取）

- **I2C DLL 加载 / 打包** → @see [docs/ai/03_GOTCHAS.md](../../docs/ai/03_GOTCHAS.md) §11
- **分层依赖规则** → @see [docs/ai/04_ARCHITECTURE.md](../../docs/ai/04_ARCHITECTURE.md)

## 本模块职责与边界

- **职责**：BES 芯片 USB-I2C 通信（CH341 桥接）底层封装 + 各芯片 eFuse 读写脚本；对上（core/ai、IIC_Module）暴露寄存器读写与 eFuse 读写能力。
- **铁律**：禁 Qt 依赖；DLL 仅 64 位（03_GOTCHAS §11）；模块自身代码禁 `print` 用 logger，但 eFuse 脚本内 `print` 是厂商示例约定（输出被上位机 I2C Tool 捕获），新增脚本可沿用。

## I2C 接口使用方法

- **底层**：[Bes_I2CIO_Interface.py](./Bes_I2CIO_Interface.py) `BESI2CIO(dll_path=None, verbose=False)`，ctypes 直调 `config/BES_USBIO_I2C_X64.dll`，类级 RLock 线程安全。
  - `read(speed_mode, dev_addr, reg_addr, width_flag) -> int`
  - `write(speed_mode, dev_addr, reg_addr, data, width_flag, high_bit=-1, low_bit=-1)`：`high/low_bit` 非 -1 时按位写（DLL 内部 read-modify-write）。
- **枚举**：`I2CSpeedMode`（SPEED_20K/100K/400K/750K）；`I2CWidthFlag`（BIT_8=8位地址+16位数据 / BIT_10=10位地址+16位数据 / BIT_32=32位地址+32位数据）；异常 `I2CError` 及子类（Device/Operation/Parameter）。
- **高层**：[i2c_interface_x64.py](./i2c_interface_x64.py) `I2CInterface`：`read/write(device_addr, reg_addr, width_flag, ...)`；`WIDTH_8X8=88` 表示 8位地址+8位数据；`bes_chip_check()` 芯片检测（0x11=main die 32bit（0xFFFFFFFF 时回退 0x31）/ 0x27=main-die PMU / 0x17=独立 PMU，10bit 优先 8bit 兜底）；`raw` 属性取底层 `BESI2CIO`。
- **设备地址约定**：main die=0x11（0x31 备选）、main-die PMU=0x27、独立 PMU=0x17；eFuse 控制寄存器（0xb7/0xbd/0xbe/0x147/0x158）位于 PMU 的 10bit 地址空间，eFuse 调用 device_addr 传 PMU 地址。

## eFuse 读取流程

- **脚本契约**：[config/EFUSE_SCRIPTS/](./config/EFUSE_SCRIPTS/) 每芯片一份 `efuse_<chip>.py`，必须提供 `read_efuse(reg_offset) -> int` / `write_efuse(reg_offset, data) -> bool`；脚本顶部用 `globals().get()` 取注入变量，禁 import 主程序模块。
- **调用入口**：[efuse_script_caller.py](./efuse_script_caller.py) `EFuseScriptCaller(BESI2CIO实例)`：importlib 动态加载脚本并注入 `i2c_interface / I2CSpeedMode / I2CWidthFlag / I2CError / ui_dev_addr / ui_reg_addr / ui_data_hex / ui_data_width / ui_module_name_unique / ui_chip_name`；对外 `read_efuse(device_addr, reg_addr, data_width, speed_mode, script_filename, chip_name)` / `write_efuse(...)`。
- **1307ph 读取时序（2026-09-24 实机验证）**：① 读 0x158，低 4 位须==0（idle）；② 0x147 bit[14]=1，efuse 时钟切 osc；③ 0xb7=0x0008 开 clk en+read mode；④ 0xb7=0x0018 function on；⑤ 0xb7=`0x0018|(addr<<6)` 装入 efuse 地址；⑥ 0xb7=`0x0038|(addr<<6)` 单次读触发；⑦ 0xb7=`0x0018|(addr<<6)` 触发关闭；⑧ 读 0xbd（高16bit）/ 0xbe（低16bit），`value1|value2` 合并为结果；⑨ 收尾 0xb7=0x0008 → 0xb7=0x0000 关 efuse/时钟，0x147 bit[14]=0 切回 32k。
- **验证基准**：[tests/verify_efuse_1307ph.py](../../tests/verify_efuse_1307ph.py)（device=0x27，BIT_10，100K）：1307ph eFuse[0x0001]=0x0003 通过；改动脚本或调用器后必须重跑回归。

## 局部坑点

- **eFuse 写入不可逆**：`write_efuse` 逐 bit 烧录（1307ph 模板把 16bit 业务值复制成"正常+备份"32bit 扫描写入）；写流程需先 24M 时钟使能 `write(speed, 0x11, 0x40080004, 1, BIT_32, 28, 28)`（读流程不需要）。
- **WIDTH_8X8 整寄存器写**：底层 8位地址/16位数据一次写会连带覆盖相邻 reg+1，`I2CInterface.write` 已先读 reg+1 拼低字节回写保护，勿绕过该封装直接整写。
- **DLL stdout**：DLL 内部调试信息写 C 层 stdout，`BESI2CIO` 默认 `_suppress_stdout`（fd 级）静默，`verbose=True` 才放行；fd 级重定向在 `sys.stdout is None` 的窗口模式下同样有效。

# 00 - 项目概述

## 1. 项目定位

**KK_Lab** 是一个基于 **PySide6 (Qt6)** 的 Windows 桌面应用，面向 BES 芯片研发测试场景，目标用户为芯片 / 系统 / 测试工程师。

核心功能：
- 通过 VISA 控制 **Keysight N6705C 直流电源分析仪**：电压/电流设置、通道控制、Datalog 长时采集。
- 通过 VISA 控制 **Keysight DSOX4034A / Tektronix MSO64B 示波器**：自动识别型号、测量、触发、截图。
- 通过 Modbus 串口控制 **VT6002 高低温箱**：温度设置、读取、程序段运行。
- 通过 **USB-I2C（CH341 / BES USB-IO）** 与芯片 PMU / Charger 模块交互。
- 通过 UART `dldtool.exe` 完成 BES 芯片 bin 下载、ramrun、eFuse 读写。
- 组合以上能力，完成 PMU 输出电压 / DCDC 效率 / OSCP / GPADC / Clock / Is Gain、Charger 配置遍历 / Iterm / 状态寄存器 / 调节电压、功耗、温度扫描等自动化测试。

## 2. 技术栈

| 层 | 技术 |
|---|---|
| 语言 | Python ≥ 3.10 |
| UI | PySide6 6.6.0（Fusion 风格 + 自定义 QSS + `HoverFixStyle` QProxyStyle） |
| 绘图 | pyqtgraph 0.13.3 |
| 仪器通讯 | pyvisa 1.13 + pyvisa-py 0.7，pyserial 3.5 |
| USB | pyusb + libusb-package |
| 数据 | numpy, openpyxl |
| 打包 | PyInstaller（`spec/` 目录下自定义 spec，`hooks/hook-pyqtgraph.py`） |

## 3. 分层架构

```
┌───────────────────────────────────────────────────────┐
│                     main.py (入口)                     │
│           setup_logging → QApplication → MainWindow   │
└───────────────────────────┬───────────────────────────┘
                            │
                ┌───────────▼────────────┐
                │        ui/             │  ← 事件、展示、交互
                │  main_window, pages/,  │
                │  widgets/, styles/     │
                └───────────┬────────────┘
                            │  Signal/Slot
                ┌───────────▼────────────┐
                │       core/            │  ← 业务编排
                │  test_manager.py       │
                │  data_collector.py     │
                │  controllers/          │
                └───────────┬────────────┘
                            │
                ┌───────────▼────────────┐
                │     instruments/       │  ← 驱动 & 协议
                │  base/, scopes/,       │
                │  power/, chambers/,    │
                │  mock/, factory.py     │
                └───────────┬────────────┘
                            │
                ┌───────────▼────────────┐
                │         lib/           │  ← 底层（I2C、下载器）
                │  i2c/, download_tools/ │
                └────────────────────────┘

    日志 log_config.py  |  调试开关 debug_config.DEBUG_MOCK
```

## 4. 目录速览

| 目录 | 职责 |
|---|---|
| `main.py` | 应用入口 |
| `log_config.py` | 日志统一入口（`setup_logging`、`get_logger`） |
| `debug_config.py` | `DEBUG_MOCK` 开关 |
| `core/` | 业务流程（`test_manager`、`data_collector`、`controllers/`） |
| `instruments/` | 仪器驱动（分 `base/`、`scopes/`、`power/`、`chambers/`、`mock/`） |
| `ui/` | 界面（`main_window`、`pages/`、`widgets/`、`styles/`、`dialogs/`） |
| `lib/` | 底层封装（`i2c/`、`download_tools/`） |
| `helps/` | HTML 帮助文档（每个功能页配一份） |
| `chips/` | 芯片配置 YAML + Python 配置类（`bes_chip_configs/`） |
| `resources/icons/` | SVG / ICO 图标 |
| `spec/` | PyInstaller spec |
| `hooks/` | PyInstaller hook |
| `Results/` | 运行时测试产物（Git 忽略内容） |

## 5. 运行时关键开关

- `debug_config.DEBUG_MOCK = True` → 走 `instruments/mock/mock_instruments.py` 模拟仪器，无硬件也能跑。
- `log_config.setup_logging(level=...)` → 日志级别（main.py 默认 `INFO`）。
- 打包 vs 源码：用 `sys._MEIPASS` 定位图标资源（见 [main.py:L84-L89](file:///d:/CodeProject/TRAE_Projects/KK_Lab/main.py#L84-L89)）。

## 6. 延伸阅读

- [01_CONVENTIONS.md](./01_CONVENTIONS.md) —— 代码规范
- [04_ARCHITECTURE.md](./04_ARCHITECTURE.md) —— 更细的架构细节
- [05_INSTRUMENT_GUIDE.md](./05_INSTRUMENT_GUIDE.md) —— 新增仪器
- [06_PAGE_GUIDE.md](./06_PAGE_GUIDE.md) —— 新增 UI 页面
- [07_TEST_GUIDE.md](./07_TEST_GUIDE.md) —— 新增测试功能
- [09_WORKFLOW.md](./09_WORKFLOW.md) —— 任务 SOP（调用 / 执行 / 回归）

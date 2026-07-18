# KK_Lab 用户手册

本目录是 KK_Lab（LabControl Pro）各功能页面的最终用户使用手册，按主窗口左侧导航栏的页面结构组织。每个页面单独成文，介绍该页面的用途、入口、界面布局、典型操作流程与注意事项。

> 本手册面向**使用者**（实验室测试工程师），不涉及代码实现。如需开发/扩展指引，请参阅 `docs/ai/` 目录下的开发文档。

## 启动主程序

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

启动后主窗口左侧为导航栏，按 **INSTRUMENTS / AUTOMATION / TOOLS / ORCHESTRATION** 四个分组组织页面；右侧为当前页面内容区；底部状态栏显示仪器连接状态；右上角为 AI 助手入口（可通过环境变量 `KK_LAB_WITH_AI=0` 关闭）。

## 导航分组与页面索引

### INSTRUMENTS（仪器控制）
直接驱动单台仪器的页面。

| 页面 | 子页面 | 说明 |
|---|---|---|
| [N6705C Power Analyzer](./INSTRUMENTS/N6705C%20Power%20Analyzer/README.md) | [N6705C Analyser](./INSTRUMENTS/N6705C%20Power%20Analyzer/N6705C%20Analyser.md) | Keysight N6705C 直流电源分析仪实时控制台 |
| | [N6705C Datalog](./INSTRUMENTS/N6705C%20Power%20Analyzer/N6705C%20Datalog.md) | N6705C 长时间数据采集与波形分析 |
| [Oscilloscope](./INSTRUMENTS/Oscilloscope.md) | — | 示波器（MSO64B / DSOX4034A）控制与测量 |
| [Chamber](./INSTRUMENTS/Chamber.md) | — | 温箱（VT6002 等）控制与温度循环 |

### AUTOMATION（自动化测试）
针对 BES 芯片 PMU / Charger / 功耗等模块的自动化测试套件。

| 页面 | 子页面 | 说明 |
|---|---|---|
| [PMU Test](./AUTOMATION/PMU%20Test/README.md) | [DCDC Efficiency](./AUTOMATION/PMU%20Test/DCDC%20Efficiency.md) | DCDC 转换效率扫描 |
| | [Output Voltage](./AUTOMATION/PMU%20Test/Output%20Voltage.md) | LDO/BUCK 输出电压精度 |
| | [Is_gain](./AUTOMATION/PMU%20Test/Is_gain.md) | 电流源增益测试 |
| | [OSCP](./AUTOMATION/PMU%20Test/OSCP.md) | OSCP 过冲保护监测 |
| | [GPADC Test](./AUTOMATION/PMU%20Test/GPADC%20Test.md) | GPADC 采样精度测试 |
| | [CLK Test](./AUTOMATION/PMU%20Test/CLK%20Test.md) | 时钟频率与性能测试 |
| [Charger Test](./AUTOMATION/Charger%20Test/README.md) | [Config Traverse Test](./AUTOMATION/Charger%20Test/Config%20Traverse%20Test.md) | 充电器配置寄存器遍历 |
| | [Status Register Test](./AUTOMATION/Charger%20Test/Status%20Register%20Test.md) | 状态寄存器读取测试 |
| | [Iterm Test](./AUTOMATION/Charger%20Test/Iterm%20Test.md) | 终止电流测试 |
| | [Regulation Voltage Test](./AUTOMATION/Charger%20Test/Regulation%20Voltage%20Test.md) | 调压精度测试 |
| [Module Test](./AUTOMATION/Module%20Test/README.md) | [LDO](./AUTOMATION/Module%20Test/LDO.md) | LDO 模块测试 |
| | [DCDC](./AUTOMATION/Module%20Test/DCDC.md) | DCDC 模块测试 |
| [Consumption Test](./AUTOMATION/Consumption%20Test/README.md) | [Auto Test](./AUTOMATION/Consumption%20Test/Auto%20Test.md) | 自动功耗测试（含固件下载） |
| | [High-Low Temperature Test](./AUTOMATION/Consumption%20Test/High-Low%20Temperature%20Test.md) | 高低温功耗测试 |
| [VminHunter](./AUTOMATION/VminHunter.md) | — | 最低稳定电压探底测试 |

### TOOLS（工具）
辅助工具页面。

| 页面 | 子页面 | 说明 |
|---|---|---|
| [PMU](./TOOLS/PMU/README.md) | [1811](./TOOLS/PMU/1811.md) | BES1811 PMU 图形化配置工具 |
| | [1860](./TOOLS/PMU/1860.md) | BES1860 PMU 配置工具（占位） |
| [Collection](./TOOLS/Collection/README.md) | [MCU IO](./TOOLS/Collection/MCU%20IO.md) | MCU IO（YD-RP2040 / CH9114F）GPIO 控制 |
| | [KK Serials](./TOOLS/Collection/KK%20Serials.md) | 串口收发终端 |
| | [IIC Control](./TOOLS/Collection/IIC%20Control.md) | USB-I2C 寄存器读写工具 |

### ORCHESTRATION（编排）
| 页面 | 说明 |
|---|---|
| [Orchestrator](./ORCHESTRATION/Orchestrator.md) | 节点式可视化测试序列编辑器与执行器 |

## 通用约定

- **仪器连接**：所有页面共用统一的 `InstrumentManager`，在导航栏底部状态面板可查看当前连接的所有仪器。新页面通过 Mixin（如 `N6705CConnectionMixin` / `ChamberConnectionMixin` / `OscilloscopeConnectionMixin`）复用连接逻辑。
- **日志**：每个测试页底部均带 `ExecutionLogsFrame` 日志区，可通过 `QSplitter` 隐式手柄调节高度。
- **结果文件**：测试结果统一输出到项目根目录的 `Results/` 文件夹，文件名带时间戳。
- **Mock 模式**：在 `debug_config.py` 中开启 `DEBUG_MOCK=True` 时，所有仪器自动连接模拟实现，可在无硬件环境下走通流程。
- **快捷键**：`Ctrl+1` ~ `Ctrl+0` 已绑定到 10 个一级页面，不可重映射。
- **AI 助手**：右上角面板，可对话式查询当前页面状态、触发已注册的 UI 动作（仅限当前页 page_key，禁跨页派发）。

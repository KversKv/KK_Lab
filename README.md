# KK_Lab

基于 **PySide6 (Qt6)** 的 Windows 实验室仪器自动化测试平台，面向 BES 芯片研发测试场景。通过 VISA / 串口 / USB-I2C 统一控制电源分析仪、示波器、温箱等仪器，完成 PMU / Charger / 功耗 / 波形类自动化测试。

## 功能特性

- **PMU 测试**：输出电压、DCDC 效率、OSCP、GPADC（含多温度）、Clock、Is Gain
- **Charger 测试**：配置遍历、Iterm、状态寄存器、调节电压
- **功耗测试**：芯片功耗自动采集与分析
- **Datalog**：N6705C 长时数据采集
- **Module Test**：DCDC / LDO 模块测试，支持 XLSX / PDF 报告导出
- **Vmin Hunter**：Sleep Vmin 自动搜索
- **Orchestrator**：可视化测试流程编排（节点 / 宏 / 断点 / 扫参）
- **波形工具**：示波器测量、触发、截图、波形分析
- **温箱控制**：温度设置、读取、程序段运行
- **GPIO / I2C / 串口**：GPIO 控制、USB-I2C 芯片交互、eFuse 读写、bin 下载、串口脚本引擎
- **AI Assistant**：内置 AI 助手（日志 / 页面 / 波形上下文、受控动作、任务调度）

## 支持的仪器

| 仪器 | 接口 |
|---|---|
| Keysight N6705C 直流电源分析仪 | VISA / LXI（支持 mDNS 跨子网发现） |
| Keysight DSOX4034A / Tektronix MSO64B 示波器 | VISA（自动识别型号） |
| VT6002 / MT3065 / WT2040 高低温箱 | Modbus 串口 |
| CH341 / BES USB-IO | USB-I2C |
| CH9114F / YD RP2040 | GPIO / MCU IO |
| dldtool.exe | UART（BES 芯片 bin 下载 / ramrun / eFuse） |

无硬件环境可开启 `debug_config.DEBUG_MOCK = True`，全部仪器走 Mock 实现。

## 环境要求

- Windows，Python ≥ 3.10（推荐 3.12）
- 依赖见 [requirements.txt](./requirements.txt)：PySide6、pyqtgraph、pyvisa、pyserial、openpyxl、numpy、httpx 等

## 快速开始

```powershell
git clone <repo-url>
cd KK_Lab
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## 打包

```powershell
# 主程序
python -m PyInstaller spec/kk_lab.spec --clean --noconfirm

# 各功能模块独立包（spec/ 下有对应 spec 文件）
python -m PyInstaller spec/n6705c_datalog.spec --clean --noconfirm
```

## 项目结构

```
main.py → ui/ ←→ core/ → instruments/ → lib/
               ↑
         log_config / debug_config
```

| 目录 | 职责 |
|---|---|
| `main.py` / `version.py` | 应用入口 / 版本号唯一事实源 |
| `ui/` | 界面层（pages / widgets / modules / styles / ai） |
| `core/` | 业务逻辑与测试流程编排（含 `core/ai/` AI 子系统） |
| `instruments/` | 仪器驱动（base / scopes / power / chambers / mock，统一走 `factory.py`） |
| `lib/` | 底层封装（I2C、下载工具） |
| `chips/` | BES 芯片配置 |
| `resources/` | SVG 图标等静态资源 |
| `helps/` | 各功能页 HTML 帮助文档 |
| `spec/` / `hooks/` | PyInstaller 打包配置与 hook |
| `tests/` | 回归测试与调试脚本 |
| `Results/` | 测试产物输出（Git 忽略） |

完整结构见 [DIRECTORY_STRUCTURE.txt](./DIRECTORY_STRUCTURE.txt)。

## 文档

- [AGENTS.md](./AGENTS.md) — AI 协作指引（含加载决策 SOP 与硬红线）
- [docs/ai/](./docs/ai/) — 深度专题文档（00 概述 ~ 10 版本管理）
- [helps/](./helps/) — 功能页操作说明

## 版本管理

版本号唯一事实源为 [version.py](./version.py)，研发初期手动低频维护、与 git 解耦，详见 [docs/ai/10_VERSIONING.md](./docs/ai/10_VERSIONING.md)。

# KK_Lab - AI 协作指引

> 🔴 **重要**：这是 AI（Claude/TRAE）介入本项目时必读的主入口文档。
> 所有修改、新增、重构任务都应先阅读本文件及引用的子文档。

---

## 1. 项目简介

**KK_Lab** 是一个基于 **PySide6 (Qt)** 的芯片功耗测试与调试桌面工具。

- **核心能力**：通过 VISA / 串口 / USB-I2C 控制电源分析仪、示波器、温箱等仪器，完成自动化数据采集、PMU 测试、Charger 测试、功耗分析、波形展示。
- **运行平台**：Windows 64 位（依赖 CH341/BES USB-IO DLL）
- **Python 版本**：建议 3.10+（PySide6 6.6.0 兼容范围）
- **打包方式**：PyInstaller + 自定义 spec

详细架构见 [docs/ai/00_OVERVIEW.md](./docs/ai/00_OVERVIEW.md)

---

## 2. 🔴 CRITICAL 规则（必须遵守）

### 禁止项（NEVER）
1. **禁止**在 `instruments/` 层直接调用 UI 代码或 Qt 信号；仪器驱动必须纯粹。
2. **禁止**在 UI 层（`ui/`）直接执行 VISA/串口阻塞 IO；必须通过 `core/` 或 QThread 异步调用。
3. **禁止**硬编码仪器资源地址；统一通过仪器工厂 `instruments/factory.py` 创建。
4. **禁止**使用 `print()` 输出日志；必须使用 `log_config.get_logger(__name__)`。
5. **禁止**在业务代码中直接实例化具体仪器类（如 `N6705C()`）；走工厂。
6. **禁止**在 `main` 线程执行耗时 > 100ms 的同步操作（会卡 UI）。
7. **禁止**忽略 `debug_config.DEBUG_MOCK` 开关；新仪器必须同时提供 Mock 实现。

### 必做项（ALWAYS）
1. **所有**新仪器驱动必须继承 `instruments/base/instrument_base.py` 的抽象基类。
2. **所有**新增 UI 页面必须复用 `ui/modules/` 下的 Mixin（如 `n6705c_module_frame`、`oscilloscope_module_frame`）。
3. **所有**新增 UI 页面必须复用 `ui/styles/` 下的样式, 保持风格统一.
4. **所有**新功能页面必须配套 HTML 帮助文档放到 `helps/`。
5. **所有**测试结果文件必须输出到 `Results/` 目录，文件名带时间戳。
6. **所有**跨线程通信必须用 Qt Signal/Slot，不允许直接操作另一个线程的 Widget。
7. **所有**异常必须捕获并通过 logger 记录，UI 层需给出用户可读提示。
8. **所有**新增图标统一使用 **SVG** 格式（`.ico` 仅限窗口/打包图标），并按归属放入 `resources/` 对应子文件夹：通用 → `resources/icons/`；通用模块 → `resources/modules/SVG_<模块名>/`；页面专属 → `resources/pages/<页面>_SVGs/`。

---

## 3. 项目分层（严格遵守）

```
main.py → ui/ ←→ core/ → instruments/ → lib/
                  ↑
          log_config / debug_config
```

| 层 | 职责 | 禁止 |
|---|------|------|
| `ui/` | 界面、事件、展示 | 禁止直接 IO 阻塞 |
| `core/` | 业务流程、数据采集编排 | 禁止引入 Qt Widget |
| `instruments/` | 仪器通信与协议封装 | 禁止依赖 UI |
| `lib/` | 第三方/底层封装（I2C、下载器） | 尽量无业务 |

详见 [docs/ai/04_ARCHITECTURE.md](./docs/ai/04_ARCHITECTURE.md)

---

## 4. 关键约定速查

### 日志

```python
from log_config import get_logger
logger = get_logger(__name__)
logger.info("xxx")
logger.error("xxx", exc_info=True)
```

### Mock 调试

```python
from debug_config import DEBUG_MOCK
if DEBUG_MOCK:
    # 使用 mock_instruments.py 中的模拟类
    ...
```

### 仪器创建（统一入口）

```python
from instruments.factory import create_instrument
inst = create_instrument("n6705c", resource="USB0::...")
```

## 5. 常用命令

```powershell
python main.py                                                      # 运行
python -m PyInstaller spec/kk_lab.spec --clean --noconfirm          # 打包主程序
python -m PyInstaller spec/n6705c_datalog.spec --clean --noconfirm  # 打包子工具
```

完整命令见 [docs/ai/02_COMMANDS.md](./docs/ai/02_COMMANDS.md)。

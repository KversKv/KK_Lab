# 03 - 坑点与重要注意事项 ⭐

> 本文档汇总了开发 / 维护过程中踩过的"坑"。AI 在修改代码前**必读**，以免重复掉坑。

---

## 1. PyVisa 清理时崩溃（已处理）

PyVisa `ResourceManager.__del__` 在解释器退出时偶尔抛异常，导致退出崩溃。
主入口已做了防御性 patch，不要删除：

参考 [main.py:L52-L59](file:///d:/CodeProject/TRAE_Projects/KK_Lab/main.py#L52-L59)

```python
_original_rm_del = pyvisa.ResourceManager.__del__
def _safe_rm_del(self):
    try:
        _original_rm_del(self)
    except Exception:
        pass
pyvisa.ResourceManager.__del__ = _safe_rm_del
```

## 2. 打包后 `sys.stdout` 为 `None`

PyInstaller `--windowed` 模式下 `sys.stdout / sys.stderr` 为 `None`，直接 `print` 或 `logging` 写入会炸。
入口已处理（[main.py:L13-L16](file:///d:/CodeProject/TRAE_Projects/KK_Lab/main.py#L13-L16)）：

```python
if sys.stdout is None: sys.stdout = open(os.devnull, "w")
if sys.stderr is None: sys.stderr = open(os.devnull, "w")
```

新增日志 / 打印代码不要重新引入 `print`。

## 3. Qt `QPainter::end` 警告刷屏

Fusion + 自绘图表组合，偶尔刷 `QPainter::end` 警告。已通过 `custom_message_handler` 过滤（[main.py:L72-L75](file:///d:/CodeProject/TRAE_Projects/KK_Lab/main.py#L72-L75)），请保留。

## 4. `HoverFixStyle`

`QProxyStyle` 子类统一给 `QWidget` 打开 `Qt.WA_Hover`，解决 Fusion 风格下 `:hover` 伪类在部分控件失效的问题。替换 QStyle 时注意保留。

## 5. VISA 资源路径硬编码

**绝不允许**在业务代码写死 VISA 地址（如 `USB0::0x...::INSTR`）。必须：
1. 通过 `ui/styles/*_module_frame.py` 的搜索按钮扫描；
2. 用户在下拉框中选择；
3. 传给 `instruments.factory.create_xxx`。

## 6. 仪器断线重连

仪器长时间空闲或 USB 被抢占会掉线。仪器类 `is_connected()` 不要假设恒真；
调用 `read/write` 前要有超时保护；异常要落盘日志并通知 UI。

## 7. 长耗时 IO 阻塞 UI（高频坑）

- VISA `query` 动辄几十 ms 到数秒。
- `dldtool.exe` 下载过程秒级。
- 温箱温度稳定等待分钟级。

**一律放到 QThread 或 `QTimer.singleShot(0, ...)` 异步回调**。违反会卡死界面。

## 8. QThread 生命周期

- 使用 `QObject + moveToThread`，不要继承 `QThread` 再 override `run`（项目约定风格）。
- 线程结束必须 `quit() → wait()`，否则主窗口关闭时会崩溃。
- 跨线程只用 Signal/Slot，禁止在子线程直接操作主线程 Widget。

## 9. DEBUG_MOCK 切换

- `debug_config.DEBUG_MOCK` 是**模块级常量**，代码里多处 `from debug_config import DEBUG_MOCK` 按值 import。
- 改值后**必须重启**应用；运行时热切换不生效。
- 新增仪器务必同步加 Mock 类，否则 Mock 模式下会崩。

## 10. HTML 帮助路径

`helps/*.html` 在打包后位于 `sys._MEIPASS` 下：

```python
base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
html_path = os.path.join(base, "helps", "xxx.html")
```

直接写相对路径在开发态没问题，打包后必挂。

## 11. I2C DLL 加载

`lib/i2c/config/*.dll` 是 64 位 DLL，必须：
- 32 位 Python **不兼容**；
- 打包时需在 spec 中显式 `datas/binaries` 收集；
- 运行时以绝对路径 `LoadLibrary`。

## 12. PyInstaller + pyqtgraph

pyqtgraph 动态导入资源，必须启用 `hooks/hook-pyqtgraph.py` 并在 spec 的 `hookspath` 中注册。否则打包后图表空白。

## 13. 温箱 Modbus CRC

VT6002 使用 Modbus RTU（CRC16）。串口波特率、奇偶校验、起止位需严格匹配；超时默认 1s 不够，建议 2-3s。

## 14. N6705C Datalog 格式

Datalog 导出是二进制 + CSV 混合格式，解析走 [n6705c_datalog_process.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/instruments/power/keysight/n6705c_datalog_process.py)，不要重复造轮子。

## 15. 示波器截图

DSOX4034A / MSO64B 的截图 SCPI 指令不同：
- DSOX：`:DISP:DATA? PNG, COLor`；
- MSO64B：`HARDCopy` 系列；
建议在基类保留 `capture_screen(path)` 接口，子类各自实现。

## 16. Results 目录

- Git **不跟踪**内容（`.gitkeep` 占位）。
- 文件名必须带时间戳，避免覆盖历史结果。
- 写文件前必须 `os.makedirs(..., exist_ok=True)`。

## 17. 日志级别切错

生产运行建议 `INFO`，长测试切 `WARNING`，排查问题切 `DEBUG`。
**不要提交** `DEBUG` 级别进默认配置，刷屏会打爆日志。

## 18. 不要删除 `faulthandler.enable()`

[main.py:L18](file:///d:/CodeProject/TRAE_Projects/KK_Lab/main.py#L18) 用于抓 C 扩展段错误（pyvisa / Qt plugin），崩溃时可见原生堆栈。

## 19. `QApplication` 只能创建一次

若在子脚本 / 工具里复用模块，注意不要重复 `QApplication(sys.argv)`。使用 `QApplication.instance()` 判断。

## 20. `pyvisa_py.tcpip` 警告

`pyvisa-py` 的 TCPIP 模块在 Windows 下会 emit 警告，已过滤（[main.py:L50](file:///d:/CodeProject/TRAE_Projects/KK_Lab/main.py#L50)）。不要删这行 `filterwarnings`。

## 21. VISA 后端选择（禁止硬编码 `'@py'`）

**现象**：USBTMC 仪器（如 Keysight 53230A / N6705C、Tektronix MSO64B）在 NI MAX 能正常通信，但 Python 运行时抛：

```
File ".../pyvisa_py/protocols/usbtmc.py", line 199, in __init__
    raise ValueError("No device found.")
```

**根因**：驱动层写死 `pyvisa.ResourceManager('@py')`，强制使用 `pyvisa-py`。而 Windows 上仪器的 USBTMC 驱动由 NI-VISA / Keysight IO Libraries 接管，走 `pyvisa-py`（依赖 libusb / WinUSB）时无法枚举到设备。

**规则**：

- 驱动层禁止写死 `'@py'`；默认调用 `pyvisa.ResourceManager()`，由系统自动选择 NI-VISA 等后端。
- 构造函数需提供 `visa_library` 可选参数，允许外部显式指定（`'@ni'` / `'@py'` / `r'C:\Windows\System32\visa64.dll'`）。
- 打开失败（`OSError` / `ValueError`）时回退到 `'@py'`，并 `logger.warning` 记录。
- 连接成功后 `logger.debug("<Class> visalib=%s", self.rm.visalib)`，便于日志快速判定后端。

**参考实现**：
- [keysight_53230A.py:20-38](file:///d:/CodeProject/TRAE_Projects/KK_Lab/instruments/frequencyCounter/keysight_53230A.py#L20-L38)
- [n6705c.py:41-55](file:///d:/CodeProject/TRAE_Projects/KK_Lab/instruments/power/keysight/n6705c.py#L41-L55)
- [mso64b.py:8-23](file:///d:/CodeProject/TRAE_Projects/KK_Lab/instruments/scopes/tektronix/mso64b.py#L8-L23)
- 示波器基类风格见 [dsox4034a.py:70-79](file:///d:/CodeProject/TRAE_Projects/KK_Lab/instruments/scopes/keysight/dsox4034a.py#L70-L79)。

**新增仪器驱动自检**：搜 `ResourceManager\('@py'\)`，凡驱动层命中一律替换为默认 + 回退模式。

## 22. UI 模组文件的"直接运行"入口（`ModuleNotFoundError: No module named 'ui'`）

**现象**：`ui/modules/*_module_frame.py` 顶部 `#python -m ui.modules.xxx` 只说明了"按模块运行"方式。当用户直接：

```powershell
python ui\modules\keysight_53230a_module_frame.py
```

启动，Python 把 `sys.path[0]` 设为脚本所在目录 `ui/modules/`，导致顶层包 `ui.resource_path` / `instruments.*` / `debug_config` 全部无法解析：

```
ModuleNotFoundError: No module named 'ui'
```

**根因**：`python -m <pkg>` 会把 **CWD** 注入 `sys.path[0]`；而 `python <path>.py` 只会注入 **脚本所在目录**，不是项目根。

**规则**：凡 `ui/modules/*_module_frame.py` 带 `if __name__ == "__main__":` Demo 块、且顶部直接 `from ui.xxx import ...` 的文件，必须在 **最顶部、任何 `from ui.*` / `from instruments.*` 之前** 注入项目根：

```python
#python -m ui.modules.xxx_module_frame
import os
import sys

if __name__ == "__main__" and __package__ in (None, ""):
    _PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from ui.resource_path import get_resource_base
# ... 其余顶层 import 照常
```

**要点**：
- 用 `__name__ == "__main__" and __package__ in (None, "")` 双守卫，仅"脚本模式"触发，不污染正常 `import` 路径。
- 用 `sys.path.insert(0, ...)` 抢占优先级，避免同名 `ui` 包冲突。
- 用 `_PROJECT_ROOT not in sys.path` 保证幂等，防止反复运行时堆积路径条目。

**参考实现**：[keysight_53230a_module_frame.py:1-13](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/modules/keysight_53230a_module_frame.py#L1-L13)

**新增 UI 模组自检**：同时支持两种启动方式——`python -m ui.modules.xxx` 与 `python ui\modules\xxx.py`，均应能弹出 Demo 窗口。

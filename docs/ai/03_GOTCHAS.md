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

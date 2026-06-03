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

## 23. SVG 图标禁止使用 `QPixmap.setDevicePixelRatio()`

**现象**：在 DPR > 1 的高 DPI 屏幕上，通过 `QPixmap(px_size, px_size)` + `setDevicePixelRatio(dpr)` 渲染的 SVG 图标在 `QLabel.setPixmap()` 或 `QIcon` 中只显示左上角一部分（被放大裁剪）。

**根因**：当前 PySide6 版本中，`QLabel` 和 `QIcon` 在渲染带 DPR 标记的 pixmap 时，不能正确识别 `devicePixelRatio` 标记——会把物理像素大小（如 24×24）直接当作逻辑像素大小来显示，在逻辑大小为 16×16 的 label 中只能看到左上 16×16 部分。

**规则**：

- 渲染 SVG 到 `QPixmap` 时，**直接用逻辑大小** `QPixmap(size, size)` 创建，**不要** `setDevicePixelRatio`。
- Qt 的 High DPI 缩放系统会在底层自动处理设备像素映射。
- `QSvgRenderer.render(painter)` 无参数版本即可填满整个 pixmap。
- `CompositionMode_SourceIn` + `fillRect(pixmap.rect(), color)` 实现着色。

**正确模式**：

```python
pixmap = QPixmap(size, size)
pixmap.fill(Qt.transparent)
painter = QPainter(pixmap)
painter.setRenderHint(QPainter.Antialiasing)
painter.setRenderHint(QPainter.SmoothPixmapTransform)
renderer.render(painter)
painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
painter.fillRect(pixmap.rect(), QColor(color))
painter.end()
```

**错误模式（禁止）**：

```python
px_size = int(size * dpr)
pixmap = QPixmap(px_size, px_size)
pixmap.setDevicePixelRatio(dpr)  # ← 禁止
```

**参考实现**：[icon_utils.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/utils/icon_utils.py)

## 24. `get_page_base_qss()` 禁止全局 `min-height`

**现象**：使用 `get_page_base_qss()` 的页面中，嵌入的模块面板（如 N6705C 连接面板）内的 QComboBox / QPushButton 被强制拉高，挤占了 `setSpacing()` 定义的布局间距，视觉上"完全没有间距"。而同一模块面板单独运行时间距正常。

**根因**：`get_page_base_qss()` 曾定义全局 `QPushButton { min-height: 32px; }` / `QComboBox { min-height: 28px; }`。Qt QSS 中，父 widget 的 stylesheet 的 `min-height` 属性会级联覆盖子 widget 的 `setFixedHeight()` / `setMinimumHeight()` 代码设置。

**规则**：

- `get_page_base_qss()` 中**不允许**定义全局 `min-height`（QLineEdit / QPushButton / QComboBox / QSpinBox）。
- 需要标准高度的控件，应在各页面的 `page_extra` 中为**特定 objectName** 设置 `min-height`（如 `QPushButton#smallActionBtn { min-height: 28px; }`）。
- 通用控件的高度由代码中 `setFixedHeight()` / `setMinimumHeight()` 精确控制。

**参考实现**：[page_styles.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/styles/page_styles.py)

### 24.1 可复用控件嵌入页面时的高度治理（DarkComboBox 实战）

**现象**：`DarkComboBox` 在不同页面/位置表现不一致——同一控件在 `vmin_hunter_ui.py` 的 MCU PWR / N6705C 区域被压扁成几像素的细条，而 UART 区域与其它页面（如 `pmu_dcdc_efficiency.py`）正常。规律是：**设了 `setFixedHeight()` 的 combo 正常；没设的被压扁或被撑高。**

**根因（三处高度来源互相打架）**：

1. 页面父级 QSS 的裸类型选择器 `QComboBox { min-height; padding }` 会**级联穿透**到嵌套模块内部的每个 combo。
2. 可复用控件 `DarkComboBox` 自身 QSS 若用**相同特异度**的 `QComboBox` 选择器，Qt 中**祖先 stylesheet 优先**，子控件写的值反而不生效（见 #24 现象）。
3. `min-height` 与上下 `padding` 会**叠加进最终高度**：`min-height:24 + padding:4+4 ≈ 32px`，造成"过高"；把自身 `min-height` 删成 0 又失去兜底，没设 `setFixedHeight` 的 combo 被压扁。

**业内正确做法（控件高度治理三原则）**：

- **单一权威来源**：一个控件的高度不要同时由"父级 QSS min-height + 自身 QSS padding + 代码 setFixedHeight"三方决定，必混乱。
- **可复用控件必须自洽**：通用控件（如 `DarkComboBox`）应在**自身 QSS** 中用**足够高特异度的选择器**（ID 选择器 `QComboBox#objectName`，特异度 `(0,1,0,0)` > 类型选择器 `(0,0,0,1)`）钉死 `min-height` / `padding` / `border`，**绝不依赖父页面恰好给了 min-height 才长得对**。
- **特异度只决定"谁的值生效"，不决定"值设多少"**：用 ID 选择器反超父级后，还要把 `min-height` 设为标准值（本项目 = **22px**），并把上下 `padding` 收到 **2px**，避免叠加过高。需要特殊高度的场景（如要与按钮/开关精确对齐）再由调用处 `setFixedHeight()` 指定。

**本项目落地（基准值）**：

- `DarkComboBox` 全局标准高度 = `min-height: 22px` + 上下 `padding: 2px`，且选择器用 `QComboBox#darkCombo_<id>`（实例唯一 objectName）。见 [dark_combobox.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/widgets/dark_combobox.py)。
- MCU IO 模块的 combo / 按钮 / 开关统一走常量 `MCU_IO_BTN_HEIGHT = 22`，一处改动全局对齐。见 [mcu_io_module_frame.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/modules/mcu_io_module_frame.py)。
- 页面父级 QSS 仍**禁止**用裸 `QComboBox { min-height }`（见 #24 规则）；可复用控件靠自身 ID 选择器自洽，二者配合才稳。

## 25. Tab 状态样式的盒模型必须一致

**现象**：`n6705c_analyser_ui.py` 中，连接 N6705C 后切换通道标签到 CH4，页面内容会向上偏移几个像素，底部控件看起来被牵动；CH1~CH3 切换不明显。

**根因**：通道标签使用 `QPushButton` 模拟 tab，`checked` 与未选中状态的 QSS 盒模型不一致：

- active 状态使用更小的垂直 `padding`；
- active 状态使用 `border-bottom: none`，比未选中状态少 1px border；
- Qt 会按当前样式重新计算 `sizeHint()`，最后一个 tab（CH4）激活时更容易暴露为整体上移。

**规则**：

- 用 `QPushButton` / 自绘控件模拟 tab 时，active / inactive / disabled 状态必须保持一致的 `padding`、`border` 宽度与 `margin`。
- 需要做"选中 tab 与内容区连成一体"的视觉效果时，不要用 `border-bottom: none`；改用 `border-bottom: 1px solid <内容区背景色>`。
- 不要为了修这种几像素跳动而全局固定父区域或底部控件高度，否则容易造成页面底部控件截断。

**参考实现**：[n6705c_analyser_ui.py:_build_channel_tab_style](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/pages/n6705c_power_analyzer/n6705c_analyser_ui.py)

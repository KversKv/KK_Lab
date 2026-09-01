# 03 - 坑点与重要注意事项 ⭐

> 📌 何时读我：跨模块坑点总库（唯一事实源，全文保留）。改代码前排查同类坑；子模块 AGENTS.md「局部坑点」均以 §N 回指本文件对应章节。

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

## 26. AI Agent「上下文自我污染」与「强制重试启新 worker 的时序闪退」

**现象 A（多次设置不生效）**：新对话第一次让 AI"打开通道 1"能真控制仪器，第二次起 AI 只回"✅ CH1 输出已开启，系统已弹出确认框…"之类文字，但**不再发 tool_call**，仪器不动。

**根因 A —— 上下文自我污染**：AI 第一次真调工具成功后，它编造的"系统已弹出确认框/确认后即执行"叙述被写入 `history` 并由 `PromptManager.build_messages` 原样回灌；第二次起模型照抄这段文本、不再发 `tool_call` → `ActionDispatcher` 无动作可执行。

**修复 A —— 动作轮强制要求 tool_call**（[ai_service.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/ai/ai_service.py)）：
- `_looks_like_fake_execution(content)` 识别"嘴上执行"关键词；
- 仅当 `_agent_rounds == 0 and not _agent_forced_retry`（真·首轮、一次工具都没调过）才触发，避免误判多轮真执行后的合法总结；
- 回灌 `_FORCE_TOOL_NUDGE` 强约束提示，`_agent_forced_retry=True`，重跑一轮逼模型改用工具。

**现象 B（强制重试后窗口闪退）**：实施修复 A 后，触发强制重试时进程**无声退出**（非 segfault，`faulthandler` 抓不到栈、写文件为空 → 这是关键判据：空 faulthandler ≈ Qt 内部状态损坏 abort，而非野指针）。

**根因 B —— QThread 清理时序竞争**：强制重试在首轮 worker 的 `finished` 回调链里用 `QTimer.singleShot(0, ...)` 再起新 worker，回调被排到**首轮 QThread 的 `finished → _cleanup_thread`（deleteLater）之前**，二者交织破坏 Qt 线程对象状态。

**修复 B**：把重试延后量从 `0ms` 改为 `QTimer.singleShot(50, self._run_forced_retry)`，让首轮线程的 `finished`/`deleteLater` 先排空，竞争消失。`_run_forced_retry` 为独立延后入口（先 `_teardown_thread` 再 `_run_next_agent_round`）。

**规则**：
- AI 历史回灌是污染传播路径；凡"声称已执行控制类动作"的轮次必须强制走真 tool_call，禁止用文字假装完成。
- 在 worker `finished` 信号槽链里**再起新 QThread worker**，必须用**带正延迟**的 `singleShot`（≥50ms）或等首轮线程 `finished` 完全处理后再启动，禁止 `singleShot(0)` 直接重入，否则与上一轮线程清理竞态导致闪退。
- 排查"无声闪退"时：`faulthandler` 输出为空往往指向 Qt 线程/对象生命周期问题，而非 C 段错误；用分步 `logger.warning` 埋点夹逼定位（注意 `StreamHandler` 默认每条 flush，最后一条日志可信）。

## 27. AI 经验沉淀写盘：`resources/` 打包后只读，必须写本机 `.local` 覆盖文件

**现象**：开发态把 AI「一键沉淀」的纠偏片段、快捷指令、项目规则直接写回随包的 `resources/ai/nudges.json` 看似可行；PyInstaller 打包（frozen）后，`resources/` 落在只读安装目录（甚至 `_MEI` 临时解包目录），运行时写入会 `PermissionError` 或写到临时目录被下次启动丢弃。

**根因**：随包资源是只读发布物；用户态可写数据必须落在 `get_user_data_dir()`（`user_data/`），二者不能混。

**修复（本机 `.local` 覆盖方案）**：
- 随包只读：`resources/ai/nudges.json`（出厂片段库）。
- 本机可写：`user_data/ai/nudges.local.json` / `quick_actions.local.json` / `project_rules.local.md` / `user_prompt.md` 与 `tests/ai_eval/cases/local_*.json`。
- 加载侧合并：[nudges.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/ai/nudges.py) 按 `id` 合并（本机优先覆盖随包）；[profiles.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/ai/profiles.py) 按 `page_key` 合并快捷指令；[prompt_manager.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/ai/prompt_manager.py) 把本机项目规则插在「项目层之后、Profile 之前」。
- 写入侧统一走 [curator.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/ai/curator.py)，只写 `.local`；`reset_local()` 只删本机沉淀，不动随包出厂项。

**规则**：
- 凡运行时需写入的 AI 配置/经验，一律写 `get_user_data_dir()` 下的 `.local` 文件，禁止写 `resources/`。
- 「随包出厂 + 本机覆盖」按稳定主键（`id` / `page_key`）合并，本机优先；删除/重置只作用于本机层。

## 28. 示波器断开失灵 → 重连报 "Session already connected"（session_id 解析依赖 model 文案 + 异步断开时序）

**现象**：示波器点 Disconnect 后立刻 Connect，报 `Session dsox4034a:main_scope already connected, disconnect first`；且 Connect 按钮在断开期间永久卡禁用，界面没有 `"Disconnecting"` 之后的任何 manager 断开日志。

**根因（双坑叠加）**：

1. **`MSO64BTop._resolve_scope_session_id` 用 `self.scope_type` 猜 instrument_type**。但 `scope_type` 在 manager 连接路径下被赋为 `session.model`（如 `"DSO-X 4034A"`），`.lower()` 后是 `"dso-x 4034a"`，不在已知类型表 `("mso64b","dsox4034a")`，被**静默回退成 `mso64b`** → 解析出 `mso64b:main_scope`，而真实 session 是 `dsox4034a:main_scope`。`get_session` 返回 None → 跳过 `manager.disconnect_async()`，只走 `self.mso64b.disconnect()` 关了 VISA，**manager 里 session 永远 `connected=True`**。重连必撞 already connected。
2. **UI 在异步断开未完成时就同步复位按钮**（早期实现），或反过来等待永不到来的 `session_disconnected`（修复不当）导致按钮卡死。

**修复**：

- [mso64b_top.py `_resolve_scope_session_id`](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/pages/oscilloscope/mso64b_top.py#L27)：改为**优先按 slot 遍历 `("dsox4034a","mso64b")` 找 manager 里真实 `connected=True` 的 session**，文案解析仅作兜底，且兼容 `"dso-x"`/`"dsox"` 前缀。
- [oscilloscope_module_frame.py `_on_disconnect_scope`](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/modules/oscilloscope_module_frame.py#L571) 与 [oscilloscope_base_ui.py `_disconnect_instrument`](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/pages/oscilloscope/oscilloscope_base_ui.py#L1840)：manager 异步路径调 `disconnect_async` 后**保持按钮禁用直接 return**，由 `session_disconnected` / `connection_changed` 信号在后台 VISA 真正关闭后复位；另订阅 `disconnect_failed` 兜底恢复按钮防卡死。

**规则**：

- **凡要把"仪器型号/类型"映射到 manager session_id，禁止用 `session.model` / 用户可读文案做匹配**——model 是自由文本（`"DSO-X 4034A"`），必须用稳定的 `instrument_type` 枚举或直接按 slot 遍历真实 session。
- **`connect_async` 前 `setEnabled(False)` 后，所有状态同步出口（`sync_*_from_top` / `*_top_changed` / `session_disconnected` / `connect/disconnect_failed`）都必须成对 `setEnabled(True)`**；断开完成（`session_disconnected`）才是真正放行 Connect 的时机，不能 fire-and-forget 后立刻复位。
- 排查"Disconnect 没反应"先确认 `disconnect_async` 是否真被调到：调了 manager 入口就有日志，没日志=断在更上层的 id 解析/分支判断。

## 29. Card `cardContent` 的 `border-top` 被 `border-radius` clip path 裁成圆角（高频视觉坑）

**现象**：`Card`（`QFrame#Card`）设了 `border-radius: $radius_lg`，其内容区 `QFrame#cardContent` 用 `border-top: 1px solid $border_subtle` 画 header 下方分割线。预期分割线两端直角，实际两端呈渐变抗锯齿圆角（像素分析：左端 x=299~301、右端 x=1106~1108 颜色从 `card_bg` 渐变到 `border_subtle`），视觉上像"分割线两端被磨圆"。

**根因**：Qt QStyleSheet 实现 `border-radius` 时，会把控件（含其子控件绘制区域）clip 成圆角矩形。`cardContent` 的 `border-top` 是 `cardContent` 自身边框，贯穿 `cardContent` 全宽（紧贴 `Card` 内宽），其两端落在 `Card` 圆角弧线的 clip path 边界上，被 clip path 裁剪 + 抗锯齿，产生渐变圆角效果。即便 `cardContent` 的 y 已在 `Card` 直边段（y > radius），`border-top` 作为 `cardContent` 自身边框仍会被父级 clip path 影响。

**修复**：去掉 `cardContent` 的 `border-top`，改用独立的 separator widget 画分割线：

- [card.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/widgets/card.py#L63-L82)：在 `content_layout` 顶部加 `QFrame#cardSeparator`（`setFixedHeight(1)`），`content_layout` margins `(10, 0, 10, 10)`，separator 后 `addSpacing(7)` 保持原视觉间距。
- [controls.qss](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/theme/qss/controls.qss#L318-L329)：`QFrame#cardContent { border: none; }`；新增 `QFrame#cardSeparator { background-color: $border_subtle; border: none; margin: 0; }`。

separator 是 `content_layout` 内的独立 widget，受其 margins 缩进（左右各 10px），两端悬空在 `Card` 圆角外框内侧的"直边段"区域，是纯净的 1px 直角横线（像素验证：左端 x=30→x=31 从 `card_bg` 直接切换到 `border_subtle`，无渐变）。

**规则**：

- **凡是在带 `border-radius` 的容器（`Card` / 圆角 `QFrame`）内部画贯穿宽度的横线/分割线，禁止用子控件的 `border-top` / `border-bottom`**——会被父级 clip path 裁成圆角。必须用独立的 separator widget（`QFrame` + `setFixedHeight(1)` + `background-color`），并让 separator 受容器内 layout 的 margins 缩进，两端不与圆角弧线相接。
- **若需分割线横贯容器全宽（两端贴边框）**：separator 不能放在带 margins 的内层 layout 里，需用 `paintEvent` 自绘（`QPainter.drawLine` 从 `x=radius` 到 `x=width-radius`，跳过圆角弧线区域），或把 separator 直接挂在容器根 layout（margins=0）且 y 落在直边段（y > radius 且 y < height-radius）。单纯 `border-top` 方案不可行。
- 排查"分割线两端圆角"先用 PIL 读渲染图像素，确认两端是否有颜色渐变（抗锯齿）——有渐变即是被 clip path 裁剪。

## 30. 祖先裸选择器 QSS 级联"补全"控件 padding，撑高单元格内控件（表格行内控件变形）

**现象**：模块/页面**独立运行**（自带 Demo 入口）时表格行内控件正常，**嵌入 MainWindow** 后同行控件被纵向拉伸、超出表格行高（如 IIC 模块 `BitsTable` 的 Val 列 bit 按钮圆角框上下顶破行边界，行高仍 30px 但按钮被撑成 36px 被裁切）。

**根因**：Qt 样式表对**同优先级**选择器是**属性级合并（cascade）**，而非"谁近谁全赢"。当控件自身 QSS（如 `QPushButton { min-height:22px; max-height:22px }`，作用域=该按钮自身）只声明了 `min/max-height` 却没声明 `padding`，而祖先链上存在**同优先级**的裸选择器规则（如 MainWindow 的 `QPushButton { padding: 6px 12px }`，[main_window.py `_setup_style`](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/main_window.py#L445)），未声明的 `padding` 会被祖先规则**补全合并**进最终渲染属性。结果控件总高 = 自身 `max-height`(24) + 祖先 `padding`(上下 12) = 36px，撑破表格行。独立运行时无祖先 QSS，故正常。

**实测**（`BitsTable` 8bit 行，Fusion）：
- 独立：按钮 24px、行高 30px；
- 嵌入 MainWindow：按钮 36px（24+6+6）、行高仍 30px → 裁切；
- 控件自身 QSS 补 `padding:0` 后恢复 24px。

**修复**：可复用控件的**自身 QSS 必须盒模型自洽**——凡钉了 `min/max-height` 的控件，同一条规则里**显式声明 `padding`**（紧凑控件用 `padding:0`），不要假设祖先不会注入 padding。参见 [i2c_styles.py `_bit_val_style`](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/modules/IIC_Module/i2c_styles.py#L76)（已补 `padding:0px`）。

**规则**：

- 这是 §24.1「控件高度自洽」的**具体机制**：问题不只是 `min-height` 被覆盖，更是 `padding` 等未声明属性被祖先**合并补全**。控件 QSS 里 `min/max-height` 与 `padding` 必须**成对写全**。
- 排查"嵌入后表格行内控件变形/撑高"：先量控件 `sizeHint().height()`，若大于 `max-height` 即被祖先 padding 补全；在控件自身 QSS 补 `padding:0`（或目标值）即可。
- **禁止**反过来在页面/MainWindow 侧加全局豁免或改共享常量——会影响其它页面；只在**出问题的控件自身 QSS** 内补全盒模型属性。
- 易中招的控件：`QTableWidget.setCellWidget` 放进单元格的 `QPushButton` / `QComboBox` / `QSpinBox`（这类控件常以自身 `setStyleSheet` 钉高，且行高由 `verticalHeader` 钉死，padding 一多就破行）。

## 31. 共享控件 `setVisible` 在 `addWidget` 前调用 → 构造期独立小窗闪现（standalone 运行高频坑）

**现象**：页面 standalone 运行（`python ui\pages\xxx.py`）时，主窗弹出前会先闪过几个几乎全白的小窗口（尺寸常为 12×12 / 24×12 / 256×192），一闪即逝。嵌入 `MainWindow` 内运行时无此现象。

**根因**：Qt 机制——**无 parent 的控件调 `setVisible(True)` 会立即成为独立顶层窗口（`isWindow()==True`）并 `Show`**。共享控件在构造期把 `setVisible(...)` 用在尚未挂到任何 layout（或 layout 本身无 parent widget）的子控件上，子控件 parent=None → 短暂成为独立顶层窗闪现，直到后续 `addWidget` 把它 reparent 进父 widget 才隐藏。

典型错误顺序（[form.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/widgets/form.py) `FormRow.__init__` 修复前）：

```python
line = QHBoxLayout()              # ← layout 无 parent widget
self._unit = QLabel(unit)
self._unit.setVisible(bool(unit)) # ← QLabel parent=None → 独立顶层窗 Show！
line.addWidget(self._unit)        # ← 此时才 reparent，但已闪过一次
root.addLayout(line)              # ← line 才挂到 root（self）
```

**修复**：调换顺序——**先让子布局挂到父 widget（`root.addLayout(line)`），再 `addWidget`（设子控件 parent），最后 `setVisible`**：

```python
line = QHBoxLayout()
root.addLayout(line)              # ← 先让 line 有 parent widget=self
self._unit = QLabel(unit)
line.addWidget(self._unit)        # ← addWidget 时 QLabel parent=self
self._unit.setVisible(bool(unit)) # ← 此时已有 parent，不再独立成窗
```

**要点**：

- `QHBoxLayout`/`QVBoxLayout` 本身**不是 widget**，`layout.addWidget(child)` 是否设 `child` 的 parent，取决于 layout 有没有 parent widget——没有时 `child.parent()==None`。故**先 `parent_layout.addLayout(child_layout)` 把子布局挂到有 parent widget 的祖先 layout，再在子布局上 `addWidget`**。
- 同理 `QStackedLayout`：必须先 `root.addLayout(self._stack, 1)` 挂到父，再 `addWidget(view)`，否则 `setCurrentWidget` 触发的 `Show` 会让无 parent 的子控件独立成窗（[result_table.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/widgets/result_table.py)）。
- `EmptyState` 的 `self._hint.setVisible(bool(hint))` 同坑（[empty_state.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/widgets/empty_state.py)）——`lay.addWidget(self._hint)` 须在 `setVisible` 之前。
- 嵌入 `MainWindow` 运行时不闪，是因为主窗已 `show`，子控件 reparent 时 Qt 不会把它们当独立顶层窗单独 `Show`；standalone 下页面构造发生在 `app.exec()` 之前，无主窗兜底，每个无 parent 的 `setVisible(True)` 都会真正弹独立窗。

**DEBUG 方式**（捕获短命窗口的标准手段，比 `topLevelWidgets()` 快照更准）：

```python
class _WinFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Show and obj.isWindow():
            traceback.print_stack()  # 打印调用栈定位 setVisible 来源
        return False
app.installEventFilter(_WinFilter())
```

事件过滤器能捕获每个 `Show` 事件瞬间（含短命窗口），不会漏；`topLevelWidgets()` 快照受采样间隔限制，短命窗口易漏。

### 31.1 standalone `__main__` 块须复刻 `MainWindow._setup_style()` 的深色 palette（页面发白）

**现象**：页面 standalone 运行后样式异常——未设 QSS 的控件（含顶层 `QWidget` 背景）回落默认浅色，页面整体发白；而嵌入 `MainWindow` 内样式正常。

**根因**：`MainWindow._setup_style()` 在构造时设了深色 `QPalette`（Window `#020618` / Text `#c8c8c8` / Button `#32353a` 等）+ `QFont("Segoe UI", 9)`，app 级兜底；页面/控件级 QSS 只覆盖部分属性，未覆盖的回落 app palette。standalone `__main__` 块若只 `app.setStyle("Fusion")` 而不设 palette，未覆盖 QSS 的控件就回落系统默认浅色 → 发白。

**修复**：standalone `__main__` 块复刻 `main.py` + `MainWindow._setup_style()` 的 app 级初始化（[module_test_ui.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/pages/module_test/module_test_ui.py#L184-L231)）：

1. `configure_high_dpi()`（须在 `QApplication` 之前）
2. `app.setStyle("Fusion")`
3. `app.setPalette(深色 QPalette)`——色值逐字复刻 `MainWindow._setup_style`
4. `app.setFont(QFont("Segoe UI", 9))`
5. `app.setStyleSheet(QToolTip 深底 QSS)`——复刻 `main.py:101`（QToolTip 是顶级窗口，不继承 palette）

**规则**：凡带 `__main__` 块的页面/模组 standalone 运行后样式异常（发白/控件变形），先检查是否复刻了 `MainWindow._setup_style` 的 app 级 palette + font；与 §30（祖先 QSS 补全）是两类不同机制——§30 是 QSS 级联问题，本节是 palette 缺失问题。

## 32. 开发环境 DLP 加密 CSV/XLSX/PDT/PDF → 禁止入 git 追踪路径

**现象**：本机开发环境（DLP 终端管控）对 `*.csv` / `*.xlsx` / `*.pdt` / `*.pdf` 四类格式**落盘即透明加密**；git 提交的是密文，无 DLP 环境的机器克隆后无法打开（Excel 报格式损坏等）。

**处理（2026-08 已执行）**：

- `.gitignore` 全局忽略 `*.csv / *.xlsx / *.pdt / *.pdf` 与 `Temp_Docs/`，从机制上拦截误提交（gitignore 不影响已追踪文件）。
- git 追踪路径内的 14 个此类文件已迁至 `Temp_Docs/`（gitignored，按原相对路径结构存放：`docs/user/**`、`ui/pages/pmu/pmu_1811/data/**`、`tests/_report_smoke/**`）。
- 根 [AGENTS.md](../../AGENTS.md) 硬红线 14：这四类格式禁止出现在任何 git 追踪路径；文档/参考资料放 `Temp_Docs/`，运行期产物写 `Results/` 等已忽略目录。

**遗留与注意**：

- `.trae/skills/` 与 `.agents/skills/` 下 60 个技能数据 CSV 仍被 git 追踪（**经确认保留现状**，避免破坏 ui-ux-pro-max 技能）；若未来被 DLP 重写加密，需评估 `git rm --cached` 停止追踪。
- `tests/_report_smoke/` 每次跑 `tests/_smoke_report.py` 会重新生成 CSV——已被全局 `*.csv` 忽略兜底，不会再入库。
- 需要给他人共享此类文件时走仓库外通道（网盘/IM），不要 `git add -f` 强推。

## 33. 独立模块 spec 打包缺 `ui/theme/qss` → 启动即 `FileNotFoundError`

**现象**：用 `spec/serialcom_module.spec` 打包独立串口窗口，EXE 启动即报 `FileNotFoundError: ...\_internal\ui\theme\qss\log_splitter.qss`，窗口打不开。

**根因**：入口 `serialCom_module_frame.py` import `ui.modules.*` 时必先执行 [ui/modules/__init__.py](../../../ui/modules/__init__.py)，其顶部 `from ui.modules.execution_logs_module_frame import ExecutionLogsFrame`（try/except 只吞 `ImportError`）；该模块在**模块级**调 `load_qss("log_splitter") / load_qss("log_frame")` 读 `ui/theme/qss/`。qss 是数据文件，PyInstaller 不会自动收集；spec 的 `datas` 只打了 `resources/` 两目录，缺 `ui/theme/qss` 即崩。

**规则**：

- 任何独立 spec（入口落在 `ui/modules/**` 或 `ui/pages/**` 下，如 `serialcom_module.spec` / `n6705c_datalog.spec`）必须在 `datas` 打包整目录 `(ui/theme/qss → ui/theme/qss)`（覆盖 `log_splitter / log_frame / start_button` 等全部模块级 `load_qss`），与 [kk_lab.spec](../../../spec/kk_lab.spec) 保持一致。`ui/pages/**` 入口经 `ui.styles` → `ui.widgets.start_sequence` 同样触发模块级 `load_qss("start_button")`（2026-09 n6705c_datalog 复发）。
- `try/except ImportError` 防不住**模块级文件读取**的 `FileNotFoundError`——新增带模块级资源加载的模块时，独立 spec 同步核对 `datas`。
- 参考修复：[serialcom_module.spec](../../../spec/serialcom_module.spec) `datas` 注释处（2026-08）；[n6705c_datalog.spec](../../../spec/n6705c_datalog.spec)（2026-09）。

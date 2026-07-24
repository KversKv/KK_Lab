# 01 - 代码规范与风格

> 📌 何时读我：任何编码任务涉及命名 / 日志 / 异常 / Qt 弹窗 / 单位 label / 图标 / 依赖规范时；或子模块 AGENTS.md 出现 @see 本文件时。

本文件描述 KK_Lab 项目的编码约定，AI 修改代码必须严格遵守。

---

## 1. Python 版本与格式

- 目标版本：**Python 3.10+**，允许使用 PEP 604 `X | None` 写法、`match/case`。
- 缩进：4 空格；编码：UTF-8；所有 `.py` 文件开头保持现有文件风格，不强制加 shebang。
- 行长：建议 ≤ 120 字符，不强制。
- 未配置 black / ruff 等格式化工具，**保持文件局部风格**。

## 2. 命名

| 实体 | 规范 | 示例 |
|---|---|---|
| 模块 / 包 | 小写 + 下划线 | `pmu_test_ui.py`、`data_collector.py` |
| 类 | PascalCase，仪器类用型号全大写 | `MainWindow`、`N6705C`、`DSOX4034A`、`MSO64B`、`VT6002` |
| 函数 / 方法 | 小写 + 下划线 | `create_oscilloscope`、`setup_logging` |
| 常量 | 全大写 | `DEBUG_MOCK`、`SCROLLBAR_STYLE`、`START_BTN_STYLE` |
| Qt 信号 | 小写 + 下划线 + `_signal` 或直接名词 | `data_updated`、`connected` |
| 私有成员 | 前缀 `_` | `_icon_path`、`_safe_rm_del` |

## 3. 日志（CRITICAL）

- **禁止** `print()`。
- 模块顶部：
  ```python
  from log_config import get_logger
  logger = get_logger(__name__)
  ```
- 级别约定：
  - `logger.debug(...)` —— 详细诊断，默认关闭。
  - `logger.info(...)` —— 关键步骤、状态变化。
  - `logger.warning(...)` —— 可恢复异常、降级路径。
  - `logger.error("xxx", exc_info=True)` —— 异常必须带 `exc_info=True`。

## 4. 异常

- 仪器层抛 `instruments/base/exceptions.py` 中定义的业务异常（如 `InstrumentConnectionError`）。
- UI 层必须捕获并转成用户可读提示（`QMessageBox` 或状态栏）。
- **严禁**裸 `except:`，至少写 `except Exception as e:`。

## 5. 日志 / 异常样例

```python
try:
    inst = create_instrument("n6705c", resource=res)
    inst.connect()
except Exception as e:
    logger.error("N6705C connect failed: %s", e, exc_info=True)
    QMessageBox.critical(self, "连接失败", str(e))
    return
```

## 6. Qt / UI 规范

- 所有耗时操作 **禁止**在主线程执行；使用 `QThread` 或 `QTimer` + 异步回调。
- 跨线程更新 UI **必须**走 `Signal/Slot`。
- 控件样式统一走 `ui/styles/`；禁止在页面里散写 `setStyleSheet`。
- 共用布局用 `ui/modules/*_module_frame.py` 提供的 Mixin。
- Widgets 构造中不做 IO；IO 放到槽函数 / 控制器。

### 6.1 弹窗 / 对话框 parent（CRITICAL）

- 所有 `QDialog` 子类实例化必须显式传 `self` 作为 parent，**严禁** `parent=None` 或省略。
- 静态对话框 `QFileDialog.getOpenFileName / getSaveFileName / getExistingDirectory`、`QMessageBox.warning / information / critical / question / about`、`QInputDialog.getText / getInt / getDouble / getItem` 的第一个参数（parent）**必须**传 `self` 或对应顶层 widget；**严禁**传 `None`。
- 依据：Qt 以 parent 的 top-level window 为锚点自动居中；`parent=None` 退化为主屏中心，多屏 / 窗口移动场景会割裂体验，并产生多余任务栏项、无法随父最小化、生命周期失管等副作用。
- 参考正例：[_sc_open_settings_dialog](../../ui/modules/serialCom_module/serialCom_module_frame.py) 的 `dlg = _SerialSettingsDialog(self)`。

### 6.2 QDialog 回车绑定（CRITICAL）

- **OK / 主操作按钮**：`setDefault(True)` + `setAutoDefault(True)`，使回车键直接提交表单。
- **Cancel / Browse / 其它副作用按钮**：`setAutoDefault(False)` + `setDefault(False)`，否则 QDialog 会隐式把所有 QPushButton 的 autoDefault 置 True，Tab 过去按回车就误触发。
- 不要依赖 Qt 的"自动默认按钮推断"；每个按钮的 default / autoDefault 必须**显式二元化**。
- 参考正例：[_QuickCmdDialog](../../ui/modules/serialCom_module/serialCom_module_frame.py) 的 OK / Cancel 按钮配置。

### 6.3 数值控件 QLabel 必须标注单位（CRITICAL）

- 凡 `QLineEdit / QSpinBox / QDoubleSpinBox / QSlider` 等承载**物理量 / 工程量**的控件，其配套 QLabel 必须以 `名称 (单位)` 格式呈现，例如 `Voltage (V)`、`Current (mA)`、`Frequency (Hz)`、`Time Offset (us)`、`TimeScale (s/div)`、`Scale (V/div)`、`Offset (V)`、`Level (V)`、`Trigger Position (%)`。
- **不带单位**的纯枚举 / 名称类 label（`Source / Coupling / Slope / Trigger Mode / Type` 等）保持原样。
- 多单位后缀输入（如 `100us / 0.5ms / 1s`）：
  - 必须维护"上次单位"记忆字段（参考 [TimeScaleEdit](../../ui/pages/oscilloscope/oscilloscope_base_ui.py) 的 `_last_unit_mult`）。
  - 输入无单位的纯数字时，**复用上次单位倍率**，不得默认按基本单位（秒 / 伏）解释。
  - 解析成功后必须把 label 文本动态更新为当前生效的单位（`Time Offset (us) → Time Offset (ms)`）。
- 仪器型号差异导致**单位语义不同**的字段（如 Keysight 用秒、Tektronix 用百分比），label 与占位符必须随连接仪器**动态切换**，参考 [_update_time_offset_mode](../../ui/pages/oscilloscope/oscilloscope_base_ui.py)。
- 测量结果展示卡（`value_label` + `unit_label`）必须按数值大小自动选档（V/mV/µV、Hz/kHz/MHz/GHz 等），参考 [_format_measurement_value_split](../../ui/pages/oscilloscope/oscilloscope_base_ui.py)。
- 新增 / 修改任何此类控件时，**必须同步更新 label 文本与日志输出格式**，避免 UI 显示与 `[SETTING]` 日志单位不一致。

### 6.4 ExecutionLogsFrame 必须配合 QSplitter 实现高度可调（CRITICAL）

- 凡页面使用 `ExecutionLogsFrame`（日志模块），**必须**将其与上方主内容区域（图表 / 结果面板）一起放入 `QSplitter(Qt.Vertical)` 中，使用户可拖拽调整 LOG 区域高度。
- 分割线手柄**必须使用隐式样式**：默认透明、悬停时淡色提示、按下时高亮。
- **必须使用工厂方法** `ExecutionLogsFrame.wrap_with(...)` 完成装配，**禁止**在页面里手写 `QSplitter` 拼装样板。该工厂已把上述 CRITICAL 约束（隐式手柄、`setCollapsible(False)`、stretch 比例）固化进单一可信源。
- 标准模板：
  ```python
  from ui.modules import ExecutionLogsFrame

  # 返回 (splitter, logs)；title/show_progress/stretch/sizes/min_log_height 按需传
  right_splitter, self.execution_logs = ExecutionLogsFrame.wrap_with(
      main_content_widget,            # 图表 / 结果面板
      show_progress=True,
      stretch=(4, 1),                 # 主内容占比大、LOG 占比小
  )
  # 变量名按页保留别名透传（部分页用 log_text / log_edit）
  self.log_edit = self.execution_logs.log_edit
  right_layout.addWidget(right_splitter, 1)
  ```
- 工厂参数说明：
  - `title` —— LOG 卡片标题，默认 `"Execution Logs"`（如 gpadc / clk 用 `"TEST LOG"`）。
  - `show_progress` —— 是否显示进度条。
  - `stretch` —— `(主内容, LOG)` 的 stretch factor，默认 `(4, 1)`。
  - `sizes` —— 初始像素高度 `[主内容, LOG]`，可选。
  - `min_log_height` —— LOG 区最小高度，可选。
- **禁止**直接 `layout.addWidget(self.execution_logs)` 而不经过 `QSplitter` / 工厂。
- **禁止**对 `execution_logs` 设置 `setMaximumHeight` / `setFixedHeight` 来限制高度，改用工厂的 `stretch` / `sizes` 控制默认比例。
- 工厂实现见 [ExecutionLogsFrame.wrap_with](../../ui/modules/execution_logs_module_frame.py)；参考正例：[gpadc_test_ui.py](../../ui/pages/pmu_test/gpadc_test_ui.py)。

## 7. 仪器层规范

- 所有仪器继承 `instruments/base/instrument_base.py` 的抽象基类，统一暴露：
  - `connect()` / `disconnect()` / `is_connected()` / `identify()`。
- VISA 仪器优先继承 `instruments/base/visa_instrument.py`。
- 具体型号类放到 `instruments/<类型>/<厂商>/<型号>.py`。
- 不允许在仪器类内部依赖 Qt / UI / `QWidget`。
- **新仪器必须同时**在 `instruments/mock/mock_instruments.py` 添加 `MockXXX` 模拟类。

## 8. 仪器工厂

- 统一入口：`instruments/factory.py`。
- 禁止业务代码直接 `N6705C(...)`；必须 `create_oscilloscope / create_power_analyzer / create_chamber`。
- 工厂内部根据 `debug_config.DEBUG_MOCK` 返回真实 / Mock 实例（扩展时保持此约定）。

## 9. 注释与文档

- **不主动添加注释**；若用户没要求，保留原有注释密度。
- 类 / 模块若原本没有 docstring，不要强行补。
- 对外公开函数可以写 1 行用途说明。

## 10. 资源与路径

- 图标 / HTML / DLL 路径必须兼容 PyInstaller，使用：
  ```python
  _base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
  path = os.path.join(_base, "resources", "icons", "kk_lab.ico")
  ```
  或项目已有的 `get_resource_base()` 工具函数。
- `Results/` 输出文件命名：`<功能>_<型号>_<YYYYMMDD_HHMMSS>.csv`。

### 10.1 图标规范（CRITICAL）

- **格式**：新增图标统一使用 **SVG**，禁止引入 PNG / JPG / GIF 等位图作为 UI 图标。
  - `.ico` 仅用于窗口图标 / PyInstaller 打包图标（如 `kk_lab.ico`、`n6705c.ico`），不用于控件内 icon。
  - 需要多色彩/主题适配的图标，优先通过 SVG 内 `currentColor` 或生成多份 `<name>_<accent>.svg`（参考 `checked_*.svg` / `unchecked_*.svg`）。
- **存放位置**：图标必须放在 `resources/` 下，按归属分类：
  | 归属 | 目录 | 示例 |
  |---|---|---|
  | 通用 / 跨页面复用 | `resources/icons/` | `link.svg`、`settings.svg` |
  | 通用模块（serial / logs / common 等） | `resources/modules/SVG_<模块名>/` | `resources/modules/SVG_Serial/connect.svg` |
  | 页面专属 | `resources/pages/<页面>_SVGs/` | `resources/pages/pmu_test_SVGs/database.svg` |
- **加载方式**：禁止硬编码绝对路径；必须使用：
  ```python
  from resources_utils import get_resource_base  # 或对应工具
  icon_path = os.path.join(get_resource_base(), "resources", "icons", "xxx.svg")
  ```
- **打包同步**：若新增 `resources/` 下的**新子目录**，必须同步更新 [spec/kk_lab.spec](../../spec/kk_lab.spec) 的 `datas=[...]`，否则打包后图标丢失。
- **PySide6 SVG 依赖**：使用 SVG 必须保证 `PySide6.QtSvg` 在 `hiddenimports` 中（现有 spec 已包含）。

## 11. 依赖管理

- 新依赖需同时更新 `pyproject.toml` 和 `requirements.txt`，锁定版本。
- 禁止引入非 Windows 专用包或破坏打包的库（大型原生依赖需评估打包兼容性）。

## 12. 语言（回复 & 注释）

- 用户使用中文 → AI 用简体中文回复。
- 代码注释在项目内以简体中文 / 英文混用，尊重所在文件的既有风格。

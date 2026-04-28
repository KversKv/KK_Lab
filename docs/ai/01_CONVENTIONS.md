# 01 - 代码规范与风格

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
- 共用布局用 `ui/modules/` / `ui/styles/*_module_frame.py` 提供的 Mixin。
- Widgets 构造中不做 IO；IO 放到槽函数 / 控制器。

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

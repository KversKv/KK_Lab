# 06 - 新增 UI 页面指南

本文档描述如何在 `ui/pages/` 下新增一个功能页面，并正确集成到主窗口和侧边栏。

---

## 1. 页面放置位置

按 "仪器 / 功能归类" 分包：

```
ui/pages/
├── n6705c_power_analyzer/   # 以 N6705C 为主的页面
├── oscilloscope/            # 示波器相关
├── pmu_test/                # PMU 子测试
├── charger_test/            # Charger 子测试
├── chamber/                 # 温箱
└── consumption_test/        # 独立功能
```

新页面先判断：
- 有对应分类 → 放进去；
- 全新大类 → 新建子包，加 `__init__.py`。

## 2. 步骤

### 步骤 1：创建页面文件

示例：新增 "频率响应测试" 放到 `pmu_test/`：

```
ui/pages/pmu_test/freq_response_ui.py
```

### 步骤 2：复用 Mixin 与样式

页面必须**多继承** `ui/styles/` 下对应的连接 Mixin：

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout
from log_config import get_logger
from ui.styles.n6705c_module_frame import N6705CModuleFrame
from ui.styles.oscilloscope_module_frame import OscilloscopeModuleFrame
from ui.styles.execution_logs_module_frame import ExecutionLogsModuleFrame
from ui.styles.button import START_BTN_STYLE
from ui.styles.scrollbar import SCROLLBAR_STYLE

logger = get_logger(__name__)


class FreqResponsePage(QWidget, N6705CModuleFrame, OscilloscopeModuleFrame, ExecutionLogsModuleFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._init_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(self._build_n6705c_frame())       # 来自 Mixin
        layout.addWidget(self._build_oscilloscope_frame()) # 来自 Mixin
        layout.addWidget(self._build_parameters_frame())   # 业务参数
        layout.addWidget(self._build_execution_logs())     # 来自 Mixin

    def _build_parameters_frame(self):
        ...

    def _init_signals(self):
        ...
```

### 步骤 3：添加侧边栏入口

在 [ui/main_window.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/main_window.py) 中：
1. `import` 新页面类；
2. 在 `QStackedWidget` 插入页面实例；
3. 在侧边栏添加对应 `SidebarNavButton`；
4. 按钮 `clicked` 信号连接 `self.stack.setCurrentIndex(...)`。

### 步骤 4：配套 HTML 帮助

在 `helps/` 添加 `freq_response.html`，样式参考 `helps/pmu_dcdc_efficiency.html`（复制一份改内容即可）。
在页面的"?"按钮里 `QDesktopServices.openUrl(QUrl.fromLocalFile(...))` 打开。

### 步骤 5：业务执行路径

**UI 不得直接调用仪器**，统一流程：

```python
def on_start_clicked(self):
    # 1. 读取参数
    params = self._read_params()

    # 2. 交给 core 编排
    from core.test_manager import FreqResponseTest
    self._test = FreqResponseTest(params, self.n6705c, self.oscilloscope)

    # 3. 监听结果
    self._test.progress.connect(self._on_progress)
    self._test.finished.connect(self._on_finished)
    self._test.start()   # core 内部起 QThread
```

### 步骤 6：结果落盘

- 结果保存到 `Results/`，文件名带时间戳 + 芯片型号；
- 写入前 `os.makedirs('Results', exist_ok=True)`；
- CSV 使用 `csv` / `openpyxl`；波形截图调用示波器 `capture_screen`。

### 步骤 7：图标

- 给页面准备 SVG 图标放 `resources/icons/`；
- 命名 `freq_response.svg` / `freq_response_thumb.svg`；
- 侧边栏按钮引用 `resources/icons/checked_*.svg` + 自定义 thumb。

## 3. Checklist

- [ ] 页面继承 `QWidget` + 对应 Mixin
- [ ] 复用了 `ui/styles/` 中的样式常量
- [ ] 未在页面里直接写 `setStyleSheet("...大段...")`
- [ ] 不在槽函数里做阻塞 IO
- [ ] 耗时操作走 `core/` + QThread
- [ ] 跨线程只用 Signal/Slot
- [ ] 异常用 `logger.error` + UI 提示
- [ ] 结果文件输出到 `Results/`
- [ ] 新增 HTML 帮助到 `helps/`
- [ ] 在 `main_window.py` 注册侧边栏入口
- [ ] Mock 模式下能走通流程

## 4. 常用参考页面

| 需求 | 参考 |
|---|---|
| N6705C 单台连接 | [n6705c_analyser_ui.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/pages/n6705c_power_analyzer/n6705c_analyser_ui.py) |
| 示波器自动识别 | [oscilloscope_base_ui.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/pages/oscilloscope/oscilloscope_base_ui.py) |
| Tab 多子测试整合 | [pmu_test_ui.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/pages/pmu_test/pmu_test_ui.py)、[charger_test_ui.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/pages/charger_test/charger_test_ui.py) |
| 温箱 + 电源联动 | [consumption_test.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/pages/consumption_test/consumption_test.py) |

## 5. 反模式

- ❌ 直接在页面里 `N6705C(resource)`。
- ❌ 在槽函数里 `time.sleep(5)`。
- ❌ 用子线程直接 `self.label.setText(...)`。
- ❌ 把样式写成内嵌长字符串。
- ❌ 忘记写 help HTML。

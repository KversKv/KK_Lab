# KK_Lab — TRAE 规则

## 0. 前置义务
**开工前必读** [AGENTS.md](../../AGENTS.md)；按 docs/ai 分发表取细则。

## 1. 栈
Win/PySide6·Py3.12+·pyvisa·pyqtgraph·Modbus·PyInstaller。分层 `main→ui↔core→instruments→lib`。

## 2. 硬红线
- 禁`print`，用`log_config.get_logger(__name__)`；异常`exc_info=True`，禁裸`except`。
- `instruments/`禁Qt；UI禁阻塞IO，走QThread+Signal/Slot。
- 仪器走`factory.py`；新驱动继承`InstrumentBase`配`MockXxx`；VISA禁`'@py'`；地址禁硬编码。
- 图标仅SVG入`resources/`；`.ico`仅打包。
- QDialog必传`parent=self`；OK/Cancel显式二元化default/autoDefault。
- 数值QLabel必含单位`名称 (单位)`。
- `ExecutionLogsFrame`必配`QSplitter(Qt.Vertical)`隐式手柄，禁直接addWidget或setMaximumHeight。
- 控件高度单一权威：页面父级QSS禁裸`QComboBox/QPushButton{min-height}`；可复用控件自身用ID选择器`#objectName`钉死`min-height`+小`padding`自洽，标准高22px，特殊对齐才`setFixedHeight()`（详见03§24.1）。
- 中文→简体；不增删注释；不主动`git commit`；

## 3. 触发式必读
仪器→05；页面→06+01§6；测试→07；打包→03+08；报错→03；开工→09。

## 4. 同步
目录→`DIRECTORY_STRUCTURE.txt`；资源→`spec/kk_lab.spec`；页面→`helps/`；依赖→`requirements.txt`；决策→`decisions/`；上下文→`docs/ai/memory.md`；新坑→03。

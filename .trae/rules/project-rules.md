# KK_Lab — TRAE 规则（调度器）

## 0. 前置义务（CRITICAL）
**开工前必先读完** [CLAUDE.md](../../CLAUDE.md) + [AGENTS.md](../../AGENTS.md)；两入口含任务→docs/ai 分发表，按表取细则。

## 1. 栈
Windows/PySide6·Py3.10+·pyvisa·pyqtgraph·Modbus·PyInstaller。分层 `main→ui↔core→instruments→lib`。VISA/串口/I2C 控仪做 BES 芯片测试。

## 2. 硬红线
- 禁 `print`，用 `log_config.get_logger(__name__)`；异常 `exc_info=True`，禁裸 `except`。
- `instruments/` 禁 `PySide6.*`；UI 禁阻塞 IO，走 QThread+Signal/Slot。
- 仪器走 `factory.py`；新驱动继承 `InstrumentBase` 配 `MockXxx`；VISA 禁 `'@py'`；地址禁硬编码。
- 图标仅 SVG 入 `resources/`；`.ico` 仅打包。
- QDialog 必传 `parent=self`；OK/Cancel 显式二元化 default/autoDefault。
- 数值 QLabel 必含单位 `名称 (单位)`。
- 中文→简体；不增删注释；不新建 `*.md`；禁 `git commit`；改完跑 lint。

## 3. 触发式必读
仪器→05_INSTRUMENT_GUIDE；页面→06_PAGE_GUIDE+01_CONVENTIONS§6；测试→07_TEST_GUIDE；打包→03_GOTCHAS+08_CHECKLISTS；报错→03_GOTCHAS；开工→09_WORKFLOW。

## 4. 同步 / Memory
目录→`DIRECTORY_STRUCTURE.txt`；资源→`spec/kk_lab.spec`；页面→`helps/`；依赖→`requirements.txt`；纯文档仅同步目录表。决策→`decisions/`；上下文→`.ai/memory.md`；新坑→03_GOTCHAS。

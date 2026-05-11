# KK_Lab — TRAE 规则

细则：[CLAUDE.md](../../CLAUDE.md) · [docs/ai/](../../docs/ai/)（09_WORKFLOW · 03_GOTCHAS · 08_CHECKLISTS）。

## 目标 / 栈
Windows/PySide6，VISA/串口/I2C 控仪做 BES 芯片自动化测试。
Py3.10+ · PySide6 · pyvisa · pyqtgraph · Modbus · PyInstaller。
分层 `main → ui ↔ core → instruments → lib`。

## 风格
- 中文→简体中文；不增删注释。
- 禁 `print`，用 `log_config.get_logger(__name__)`；异常 `exc_info=True`，禁裸 `except`。
- `instruments/` 禁 `PySide6.*`；UI 禁阻塞 IO，走 QThread+Signal/Slot。
- 仪器走 `factory.py`；新驱动继承 `InstrumentBase` 并配 `MockXxx`；VISA 禁 `'@py'`；地址禁硬编码。
- 图标仅 SVG 入 `resources/`；`.ico` 仅打包。
- QDialog 必传 `parent=self`；OK/Cancel 显式二元化 default/autoDefault。
- 数值 QLabel 必含单位 `名称 (单位)`（见 01_CONVENTIONS §6）。

## 边界
优先改现有；不新建 `*.md`；改完跑 lint；重大设计先问用户。

## 同步 / Memory（矩阵见 08_CHECKLISTS）
目录→`DIRECTORY_STRUCTURE.txt`；资源→`spec/kk_lab.spec`；页面→`helps/`；依赖→`requirements.txt`；纯文档仅同步 `DIRECTORY_STRUCTURE.txt`。
决策→[decisions/](../../docs/ai/decisions/)；上下文→[.ai/memory.md](../../.ai/memory.md)；新坑→03_GOTCHAS。

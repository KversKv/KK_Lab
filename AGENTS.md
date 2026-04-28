# KK_Lab - AI Agents 协作指引（通用入口）

> 📎 本文件是 [CLAUDE.md](./CLAUDE.md) 的镜像入口，用于兼容非 Claude 系 AI 工具（例如 OpenAI Codex、Cursor、Continue、Cline、Aider 等）。
>
> **所有内容以 [CLAUDE.md](./CLAUDE.md) 为准**。如果该文件与 CLAUDE.md 出现冲突，请优先阅读 CLAUDE.md。

---

## 快速阅读清单（Agent 必读）

1. 🔴 [CLAUDE.md](./CLAUDE.md) —— 主入口与 CRITICAL 规则
2. 🔴 [docs/ai/03_GOTCHAS.md](./docs/ai/03_GOTCHAS.md) —— 必看坑点
3. 🔴 [docs/ai/08_CHECKLISTS.md](./docs/ai/08_CHECKLISTS.md) —— 开发 Checklist
4. [docs/ai/00_OVERVIEW.md](./docs/ai/00_OVERVIEW.md) —— 项目概述
5. [docs/ai/04_ARCHITECTURE.md](./docs/ai/04_ARCHITECTURE.md) —— 架构分层
6. [.trae/rules/project-rules.md](./.trae/rules/project-rules.md) —— TRAE IDE 规则
7. [.ai/memory.md](./.ai/memory.md) —— 会话沉淀的长期记忆

---

## 项目一句话概述

**KK_Lab** 是一个基于 **PySide6** 的 Windows 桌面工具，用于通过 VISA / 串口 / USB-I2C 控制实验室仪器（电源分析仪 N6705C、示波器 DSOX4034A / MSO64B、VT6002 温箱等），完成 BES 芯片的 PMU / Charger / 功耗 / 波形类自动化测试。

## 分层（铁律）

```
main.py → ui/ ←→ core/ → instruments/ → lib/
               ↑
         log_config / debug_config
```

- `ui/` 禁止阻塞 IO；必须通过 `core/` 或 QThread。
- `instruments/` 禁止依赖 Qt Widget / UI。
- 日志统一用 `log_config.get_logger(__name__)`，禁止 `print()`。
- 仪器统一走 `instruments/factory.py` 创建。
- 新仪器必须同时提供 Mock 实现（`instruments/mock/mock_instruments.py`）。

## 运行 / 打包

```powershell
python main.py
python -m PyInstaller spec/kk_lab.spec --clean --noconfirm
python -m PyInstaller spec/n6705c_datalog.spec --clean --noconfirm
```

更多命令见 [docs/ai/02_COMMANDS.md](./docs/ai/02_COMMANDS.md)。

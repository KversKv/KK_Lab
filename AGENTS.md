# KK_Lab - AI Agents 协作指引（通用入口）

> 📎 本文件是 [CLAUDE.md](./CLAUDE.md) 的镜像入口，用于兼容非 Claude 系 AI 工具（例如 OpenAI Codex、Cursor、Continue、Cline、Aider 等）。
>
> **所有内容以 [CLAUDE.md](./CLAUDE.md) 为准**。如果该文件与 CLAUDE.md 出现冲突，请优先阅读 CLAUDE.md。

---

## 快速阅读清单（Agent 必读）

1. 🔴 [CLAUDE.md](./CLAUDE.md) —— 主入口与 CRITICAL 规则
2. 🔴 [docs/ai/09_WORKFLOW.md](./docs/ai/09_WORKFLOW.md) —— 任务 SOP（调用 / 执行 / 回归）
3. 🔴 [docs/ai/03_GOTCHAS.md](./docs/ai/03_GOTCHAS.md) —— 必看坑点
4. 🔴 [docs/ai/08_CHECKLISTS.md](./docs/ai/08_CHECKLISTS.md) —— 开发 Checklist
5. [docs/ai/00_OVERVIEW.md](./docs/ai/00_OVERVIEW.md) —— 项目概述
6. [docs/ai/04_ARCHITECTURE.md](./docs/ai/04_ARCHITECTURE.md) —— 架构分层
7. [.trae/rules/project-rules.md](./.trae/rules/project-rules.md) —— TRAE IDE 规则
8. [.ai/memory.md](./.ai/memory.md) —— 会话沉淀的长期记忆

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

---

## 分发索引

> 🔴 **强制要求**：开始任务前，先在下表定位任务类型，**必须通读对应"必读"文档**再动手；"可选"文档按需拉取。
> 以 [CLAUDE.md §7](./CLAUDE.md#7-任务--docsai-分发索引critical--ai-必读) 为唯一事实源，本表同步其内容。

| 任务类型（触发词） | 必读（Must-Read） | 可选（On-Demand） |
|---|---|---|
| **新增 / 修改仪器驱动** | [05_INSTRUMENT_GUIDE](./docs/ai/05_INSTRUMENT_GUIDE.md) · [04_ARCHITECTURE](./docs/ai/04_ARCHITECTURE.md) · [03_GOTCHAS](./docs/ai/03_GOTCHAS.md) | [01_CONVENTIONS](./docs/ai/01_CONVENTIONS.md) |
| **新增 / 修改 UI 页面 / 对话框 / 控件** | [06_PAGE_GUIDE](./docs/ai/06_PAGE_GUIDE.md) · [01_CONVENTIONS §6](./docs/ai/01_CONVENTIONS.md) · [03_GOTCHAS](./docs/ai/03_GOTCHAS.md) | [04_ARCHITECTURE](./docs/ai/04_ARCHITECTURE.md) |
| **新增 / 修改测试流程（PMU/Charger/...）** | [07_TEST_GUIDE](./docs/ai/07_TEST_GUIDE.md) · [04_ARCHITECTURE](./docs/ai/04_ARCHITECTURE.md) · [08_CHECKLISTS](./docs/ai/08_CHECKLISTS.md) | [01_CONVENTIONS](./docs/ai/01_CONVENTIONS.md) |
| **PyInstaller 打包 / spec 修改** | [03_GOTCHAS](./docs/ai/03_GOTCHAS.md) · [08_CHECKLISTS](./docs/ai/08_CHECKLISTS.md) · [02_COMMANDS](./docs/ai/02_COMMANDS.md) | — |
| **排查 Bug / 回归报错** | [03_GOTCHAS](./docs/ai/03_GOTCHAS.md) · [09_WORKFLOW](./docs/ai/09_WORKFLOW.md) · [.ai/memory.md](./.ai/memory.md) | [decisions/](./docs/ai/decisions/) |
| **重构 / 架构调整 / 分层变动** | [04_ARCHITECTURE](./docs/ai/04_ARCHITECTURE.md) · [00_OVERVIEW](./docs/ai/00_OVERVIEW.md) · [decisions/](./docs/ai/decisions/) | [01_CONVENTIONS](./docs/ai/01_CONVENTIONS.md) |
| **新增依赖 / 环境配置** | [02_COMMANDS](./docs/ai/02_COMMANDS.md) · [08_CHECKLISTS](./docs/ai/08_CHECKLISTS.md) | — |
| **按 SOP 走 / 大任务开工** | [09_WORKFLOW](./docs/ai/09_WORKFLOW.md) · [08_CHECKLISTS](./docs/ai/08_CHECKLISTS.md) | 上述所有 |
| **纯文档 / 规则维护** | [08_CHECKLISTS §同步矩阵](./docs/ai/08_CHECKLISTS.md) · [.trae/rules/project-rules.md](./.trae/rules/project-rules.md) | — |

### 阅读规则
1. 命中多行任务类型 → **并集必读**。
2. 找不到匹配 → 默认读 [09_WORKFLOW](./docs/ai/09_WORKFLOW.md) + [03_GOTCHAS](./docs/ai/03_GOTCHAS.md)。
3. 跨层改动（ui ↔ core ↔ instruments）必加读 [04_ARCHITECTURE](./docs/ai/04_ARCHITECTURE.md)。
4. 改动完成前必须核对 [08_CHECKLISTS](./docs/ai/08_CHECKLISTS.md) 的同步矩阵。

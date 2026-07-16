# KK\_Lab - AI Agents 协作指引（通用入口）

> 📎 本文件是 [CLAUDE.md](./CLAUDE.md) 的镜像入口，用于兼容非 Claude 系 AI 工具（例如 OpenAI Codex、Cursor、Continue、Cline、Aider 等）。
>
> **所有内容以** **[CLAUDE.md](./CLAUDE.md)** **为准**。如果该文件与 CLAUDE.md 出现冲突，请优先阅读 CLAUDE.md。

***

## 快速阅读清单（Agent 必读）

1. 🔴 [CLAUDE.md](./CLAUDE.md) —— 主入口与 CRITICAL 规则
2. 🔴 [docs/ai/09\_WORKFLOW.md](./docs/ai/09_WORKFLOW.md) —— 任务 SOP（调用 / 执行 / 回归）
3. 🔴 [docs/ai/03\_GOTCHAS.md](./docs/ai/03_GOTCHAS.md) —— 必看坑点
4. 🔴 [docs/ai/08\_CHECKLISTS.md](./docs/ai/08_CHECKLISTS.md) —— 开发 Checklist
5. [docs/ai/00\_OVERVIEW.md](./docs/ai/00_OVERVIEW.md) —— 项目概述
6. [docs/ai/04\_ARCHITECTURE.md](./docs/ai/04_ARCHITECTURE.md) —— 架构分层
7. [.trae/rules/project-rules.md](./.trae/rules/project-rules.md) —— TRAE IDE 规则
8. [.ai/memory.md](./.ai/memory.md) —— 会话沉淀的长期记忆
9. [docs/ai/10\_VERSIONING.md](./docs/ai/10_VERSIONING.md) —— 版本号管理规范

***

## 项目一句话概述

**KK\_Lab** 是一个基于 **PySide6** 的 Windows 桌面工具，用于通过 VISA / 串口 / USB-I2C 控制实验室仪器（电源分析仪 N6705C、示波器 DSOX4034A / MSO64B、VT6002 温箱等），完成 BES 芯片的 PMU / Charger / 功耗 / 波形类自动化测试。

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

## 版本号管理（研发初期·与 git 解耦）

- 版本号唯一事实源：[version.py](./version.py)（`__version__` / `__build__` / `APP_NAME`），其它地方一律引用，**禁止写死版本号字符串**。
- 与 git **完全解耦**：日常 `commit` 不动版本号、不打 tag、不从 git 反推；仅在"标记里程碑 / 对外发包"时手动改 `version.py`。
- 格式 SemVer，研发期停在 `0.x`；攒功能发包 MINOR +1，急修发包 PATCH +1，日常提交什么都不动。
- 模块级子版本：`ui/pages/*` 与 `ui/modules/` 各模块 `__init__.py` 内 `MODULE_VERSION`（当前均 `0.0.0`），模块单独迭代时自行 +1，不牵动主版本。
- 细则见 [docs/ai/10\_VERSIONING.md](./docs/ai/10_VERSIONING.md)。

## 运行 / 打包

> 📌 项目自带虚拟环境 **`.venv/`**（仓库根目录），命令前先激活：`.\.venv\Scripts\Activate.ps1`。

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
python -m PyInstaller spec/kk_lab.spec --clean --noconfirm
python -m PyInstaller spec/n6705c_datalog.spec --clean --noconfirm
```

更多命令见 [docs/ai/02\_COMMANDS.md](./docs/ai/02_COMMANDS.md)。

***

## 分发索引

> 🔴 **强制要求**：开始任务前，先在下表定位任务类型，**必须通读对应"必读"文档**再动手；"可选"文档按需拉取。
> 以 [CLAUDE.md §7](./CLAUDE.md#7-任务--docsai-分发索引critical--ai-必读) 为唯一事实源，本表同步其内容。

| 任务类型（触发词）                        | 必读（Must-Read）                                                                                                                                         | 可选（On-Demand）                                    |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| **新增 / 修改仪器驱动**                  | [05\_INSTRUMENT\_GUIDE](./docs/ai/05_INSTRUMENT_GUIDE.md) · [04\_ARCHITECTURE](./docs/ai/04_ARCHITECTURE.md) · [03\_GOTCHAS](./docs/ai/03_GOTCHAS.md) | [01\_CONVENTIONS](./docs/ai/01_CONVENTIONS.md)   |
| **新增 / 修改 UI 页面 / 对话框 / 控件**     | [06\_PAGE\_GUIDE](./docs/ai/06_PAGE_GUIDE.md) · [01\_CONVENTIONS §6](./docs/ai/01_CONVENTIONS.md) · [03\_GOTCHAS](./docs/ai/03_GOTCHAS.md)            | [04\_ARCHITECTURE](./docs/ai/04_ARCHITECTURE.md) |
| **新增 / 修改测试流程（PMU/Charger/...）** | [07\_TEST\_GUIDE](./docs/ai/07_TEST_GUIDE.md) · [04\_ARCHITECTURE](./docs/ai/04_ARCHITECTURE.md) · [08\_CHECKLISTS](./docs/ai/08_CHECKLISTS.md)       | [01\_CONVENTIONS](./docs/ai/01_CONVENTIONS.md)   |
| **PyInstaller 打包 / spec 修改**     | [03\_GOTCHAS](./docs/ai/03_GOTCHAS.md) · [08\_CHECKLISTS](./docs/ai/08_CHECKLISTS.md) · [02\_COMMANDS](./docs/ai/02_COMMANDS.md)                      | —                                                |
| **排查 Bug / 回归报错**                | [03\_GOTCHAS](./docs/ai/03_GOTCHAS.md) · [09\_WORKFLOW](./docs/ai/09_WORKFLOW.md) · [.ai/memory.md](./.ai/memory.md)                                  | [decisions/](./docs/ai/decisions/)               |
| **重构 / 架构调整 / 分层变动**             | [04\_ARCHITECTURE](./docs/ai/04_ARCHITECTURE.md) · [00\_OVERVIEW](./docs/ai/00_OVERVIEW.md) · [decisions/](./docs/ai/decisions/)                      | [01\_CONVENTIONS](./docs/ai/01_CONVENTIONS.md)   |
| **新增依赖 / 环境配置**                  | [02\_COMMANDS](./docs/ai/02_COMMANDS.md) · [08\_CHECKLISTS](./docs/ai/08_CHECKLISTS.md)                                                               | —                                                |
| **版本号 / 发版 / 改版本**               | [10\_VERSIONING](./docs/ai/10_VERSIONING.md)                                                                                                          | [08\_CHECKLISTS](./docs/ai/08_CHECKLISTS.md)     |
| **按 SOP 走 / 大任务开工**              | [09\_WORKFLOW](./docs/ai/09_WORKFLOW.md) · [08\_CHECKLISTS](./docs/ai/08_CHECKLISTS.md)                                                               | 上述所有                                             |
| **纯文档 / 规则维护**                   | [08\_CHECKLISTS §同步矩阵](./docs/ai/08_CHECKLISTS.md) · [.trae/rules/project-rules.md](./.trae/rules/project-rules.md)                                   | —                                                |

### 阅读规则

1. 命中多行任务类型 → **并集必读**。
2. 找不到匹配 → 默认读 [09\_WORKFLOW](./docs/ai/09_WORKFLOW.md) + [03\_GOTCHAS](./docs/ai/03_GOTCHAS.md)。
3. 跨层改动（ui ↔ core ↔ instruments）必加读 [04\_ARCHITECTURE](./docs/ai/04_ARCHITECTURE.md)。
4. 改动完成前必须核对 [08\_CHECKLISTS](./docs/ai/08_CHECKLISTS.md) 的同步矩阵。

***

## 🔴 编辑铁律：向文件追加 / 定位 EOF（高频坑，必读）

> **背景**：`SearchReplace` 只替换**首个**匹配。当 `old_str` 选用了在文件中**多处重复**的模板片段（典型：各 Mock 类共有的 `format_current` / `def close(self): pass` / `return f"{...:.3e} A"`），就会误命中**靠前**的那处，把新类**插进别的类中间**，劈裂已有类，导致反复回退重写。**严禁再犯。**

### 必须遵守

1. **追加到文件末尾 ≠ 凭印象找 EOF**。动手前先用 `Grep -n "^class "` 或 `Read`（带 offset）**确认真实最后一行**，记下真正末尾类。
2. **`old_str`** **必须全局唯一**。先 `Grep` 统计候选锚点出现次数：
   - 出现 1 次 → 可直接用；
   - 出现 ≥ 2 次 → **禁止**直接用该片段，须向上扩展锚点（叠加上文若干**唯一**行，如该类特有的 `def identify_instrument` + 紧邻几行）直到整段唯一。
3. **不要用各类通用的尾部模板**（`format_current` / `format_voltage` / `def close` / `def disconnect` 等）单独做锚点——它们几乎必然重复。
4. 每次编辑后**立即复核结构**：`Grep -n "^class |def <已有类的特征方法>"`，确认①目标类落在 EOF、②被参考的相邻类未被劈裂（特征方法行号连续、仍在本类内）。
5. 误插入后**先精确删除误插块、恢复原类**，再以唯一锚点重新追加；不要在错误结构上叠加二次编辑。
6. 每个子文件夹通常会拥有readme.md, 会话开始时必须阅读并告诉我阅读了具体哪个文件; 任务结尾主动去维护每一级的readme.md;

### 反例（本仓库真实事故）

- 用 `MockN6705C` 末尾的 `format_current` 片段当锚点追加 `MockKeysight34461A`，因该片段在 `MockN6705C` / `MockKeysight53230A` 等多处重复，首个匹配落在 `MockN6705C` 内，新类被插进 N6705C 中间，`arb_on` 等方法被孤立 → 反复重写。


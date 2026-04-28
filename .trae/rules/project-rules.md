# KK_Lab - TRAE IDE 项目规则

> 本文件是 TRAE IDE 读取的项目级规则，作用于本项目内所有 AI 交互。
> 主入口仍然是根目录的 [CLAUDE.md](../../CLAUDE.md)。

---

## 1. 响应语言

- 用户使用中文时，AI 必须全程用 **简体中文** 回复。
- 代码注释若无明确要求，保持项目现有风格（多数文件无注释或极少中文注释）。
- 按 CLAUDE.md 要求，**不要主动增删注释**（除非用户明确要求）。

## 2. 必读文档（每次任务开始前）

1. [CLAUDE.md](../../CLAUDE.md)
2. [docs/ai/09_WORKFLOW.md](../../docs/ai/09_WORKFLOW.md) —— 任务 SOP（调用 / 执行 / 回归）
3. [docs/ai/03_GOTCHAS.md](../../docs/ai/03_GOTCHAS.md)
4. [docs/ai/08_CHECKLISTS.md](../../docs/ai/08_CHECKLISTS.md)
5. 与本次任务直接相关的页面 / 仪器文档

## 3. 代码修改规则

### 禁止项（NEVER）
- 禁止使用 `print()`；统一走 `log_config.get_logger(__name__)`。
- 禁止在 `instruments/` 层 import `PySide6.QtWidgets` 等 UI 模块。
- 禁止在 UI 槽函数中直接执行 VISA / 串口 / I2C 阻塞调用。
- 禁止硬编码仪器资源地址（VISA 字符串、串口号）。
- 禁止绕过 `instruments/factory.py` 直接 `new` 具体仪器。
- 禁止忽略 `debug_config.DEBUG_MOCK`；新仪器必须配套 Mock。
- 禁止提交任何 `Results/` 下的测试产物。
- 禁止主动创建 README / *.md 文档，除非用户明确要求。
- 禁止新增 PNG / JPG / ICO 等位图作为 UI 图标（`.ico` 仅限窗口/打包图标）；统一使用 SVG。
- 禁止把图标散落在 `ui/` 或页面代码同级目录；必须放进 `resources/` 下对应子文件夹。

### 必做项（ALWAYS）
- 新仪器驱动继承 `instruments/base/instrument_base.py` 抽象基类。
- 新 UI 页面复用 `ui/modules/` 的 Mixin 和 `ui/styles/` 的样式。
- 新功能页面配套 HTML 帮助文件放入 `helps/`。
- 测试结果文件输出到 `Results/`，文件名带时间戳。
- 跨线程通信用 Qt Signal / Slot。
- 异常必须 `logger.error(..., exc_info=True)` 记录，UI 层给用户可读提示。
- 新增图标统一使用 **SVG**，按归属放入 `resources/` 对应子文件夹：
  - 通用图标 → `resources/icons/`
  - 通用模块（串口 / 日志 / Common 等）→ `resources/modules/SVG_<模块名>/`
  - 页面专属图标 → `resources/pages/<页面>_SVGs/`
  - 代码中通过 `get_resource_base()` + `os.path.join("resources", ...)` 加载，兼容 PyInstaller；新增子目录必须同步到 `spec/kk_lab.spec` 的 `datas`。

## 4. 工具使用偏好

- 优先 `SearchCodebase` / `Grep` 而非反复 `Read`。
- 独立任务并行调用工具。
- 终端命令一律使用 **PowerShell** 语法（非 cmd）。
- 长期运行命令（`python main.py` 等）使用 `blocking=false`。

## 5. 提交与确认

- 除非用户明确说"提交 / commit"，**绝对不要 `git commit`**。
- 修改完成后主动跑一遍 lint / 类型检查（若存在对应命令）。
- 对不确定的重大设计，使用 AskUserQuestion 先确认再动手。

## 6. 文件生成原则

- 优先编辑已有文件；除非必需，不新建文件。
- 不主动创建 `*.md`、`README`；文档类文件仅在用户明确请求时创建。

## 7. 任务完成后沉淀

- 重要决策写入 [docs/ai/decisions/](../../docs/ai/decisions/)（ADR）。
- 会话关键上下文写入 [.ai/memory.md](../../.ai/memory.md)。

## 8. 工程清单同步矩阵（强制）

凡是改动落到磁盘，必须按下表**同步**对应清单文件；无对应触发条件则无需改。

| 触发条件 | 必须同步 |
|---|---|
| 新增 / 删除 / 重命名**目录或顶层重要文件**（含 `.py` / `.md` / 资源子目录） | [DIRECTORY_STRUCTURE.txt](../../DIRECTORY_STRUCTURE.txt) 对应段落 |
| 新增 `resources/` 子目录 / `lib/` 下新 DLL / `chips/` 子目录 / 任何**运行时**需要进入安装包的资源 | [spec/kk_lab.spec](../../spec/kk_lab.spec) 的 `datas`（必要时补 `hiddenimports`） |
| 新增 / 重命名**功能页面**或顶层功能入口 | [helps/](../../helps/) 对应 HTML 帮助文件 |
| 源码 `import` 了**新第三方包**或锁定版本变动 | [requirements.txt](../../requirements.txt) |
| 仅新增 / 修改 `docs/ai/*.md` / `.ai/memory.md` / `AGENTS.md` / `CLAUDE.md` / `.trae/rules/*` 等**纯文档** | 只需同步 [DIRECTORY_STRUCTURE.txt](../../DIRECTORY_STRUCTURE.txt)；spec / helps / requirements **不改** |

> ⚠️ 盲区提醒：`DIRECTORY_STRUCTURE.txt` 与 `requirements.txt` 历来最易被 AI 遗漏，务必在回归期逐项复查。

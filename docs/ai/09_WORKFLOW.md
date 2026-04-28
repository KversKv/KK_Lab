# 09 - 任务工作流 SOP（调用 / 执行 / 回归）⭐

> 本文件定义 AI 接入 KK_Lab 的**标准作业流程（SOP）**：
> - **调用期**：任务开始前读什么、怎么读。
> - **执行期**：动手时的纪律。
> - **回归期**：任务收尾的自检、验证、沉淀。
>
> 与 [08_CHECKLISTS.md](./08_CHECKLISTS.md) 的关系：
> - `08` 是**点**（单项勾选条目）；
> - `09` 是**线**（从接任务到交付的顺序流程）。
> 两者配合使用，不重复。

---

## 0. 触发口令（用户侧）

用户只要说 **"按 SOP 做"** / **"走 09_WORKFLOW"** / **"开始任务前先读文档"**，
AI 就必须完整执行下列三阶段。

---

## 一、调用期（Task Intake）

### 1.1 铁律加载（强制，零例外）

| AI 环境 | 入口文件 | 说明 |
|---|---|---|
| TRAE IDE | [.trae/rules/project-rules.md](../../.trae/rules/project-rules.md) | 会话启动自动注入 |
| Claude 系 | [CLAUDE.md](../../CLAUDE.md) | 主入口 |
| 其他（Codex / Cursor / Continue / Cline / Aider …） | [AGENTS.md](../../AGENTS.md) | CLAUDE.md 镜像 |

三者铁律对齐，任选其一即可覆盖 NEVER / ALWAYS。

### 1.2 长期记忆恢复

阅读 [.ai/memory.md](../../.ai/memory.md)，快速恢复：
- 项目核心一句话；
- 过往会话沉淀的偏好 / 约定 / 已解决的坑；
- 变更履历中最近的改动点。

### 1.3 必读三件套（每次都读）

1. 🔴 [00_OVERVIEW.md](./00_OVERVIEW.md) —— 知道"这是什么项目"。
2. 🔴 [03_GOTCHAS.md](./03_GOTCHAS.md) —— 知道"哪里有坑，别踩"。
3. 🔴 [08_CHECKLISTS.md](./08_CHECKLISTS.md) —— 知道"交付时要勾哪些"。

### 1.4 按任务类型按需读

| 任务类型 | 必读专题文档 |
|---|---|
| 新增仪器驱动 | [05_INSTRUMENT_GUIDE.md](./05_INSTRUMENT_GUIDE.md) |
| 新增 / 修改 UI 页面 | [06_PAGE_GUIDE.md](./06_PAGE_GUIDE.md) |
| 新增测试流程 | [07_TEST_GUIDE.md](./07_TEST_GUIDE.md) |
| 调整代码规范 / 日志 / 异常 | [01_CONVENTIONS.md](./01_CONVENTIONS.md) |
| 打包 / 命令相关 | [02_COMMANDS.md](./02_COMMANDS.md) |
| 架构层级调整 | [04_ARCHITECTURE.md](./04_ARCHITECTURE.md) |
| 延续历史架构决策 | [decisions/](./decisions/) 下相关 ADR |

### 1.5 代码上下文探查

- 优先 `SearchCodebase`（语义检索）/ `Grep`（精确匹配）；
- 避免反复 `Read` 大文件，先定位再精读；
- 改动前至少确认：相关文件、导入、现有风格、上下游调用方。

### 1.6 不确定则提问

- 多方案分歧、影响面大、可能违反铁律 → **先 `AskUserQuestion`**，不要硬猜。
- 记住：提问 < 猜错 < 重做。

---

## 二、执行期（Task Doing）

### 2.1 分层纪律（违反即返工）

```
main.py → ui/ ←→ core/ → instruments/ → lib/
              ↑
        log_config / debug_config
```

- `ui/` 不直调 VISA / 串口 / I2C，耗时 IO 一律走 `core/` + QThread。
- `instruments/` 不 import 任何 `PySide6.QtWidgets`。
- 仪器创建统一走 [instruments/factory.py](../../instruments/factory.py)。
- 日志统一 `log_config.get_logger(__name__)`，禁止 `print()`。
- `DEBUG_MOCK` 相关改动必须同步 `instruments/mock/mock_instruments.py`。

### 2.2 编辑偏好

- **优先编辑已有文件**，非必要不新建。
- **不主动新增** `*.md` / `README` / 冗余注释。
- 新增图标必须是 **SVG**，按归属放入 `resources/` 对应子文件夹；新目录同步到 [spec/kk_lab.spec](../../spec/kk_lab.spec) 的 `datas`。
- 跨线程通信只用 Qt Signal / Slot。
- 异常带 `exc_info=True`；UI 层给 `QMessageBox` / 状态栏可读提示。

### 2.3 工具使用

- 独立的搜索 / 读取 / 诊断操作尽量**并行**调用。
- 长耗时命令（`python main.py` 等）用 `blocking=false`。
- 终端命令一律 **PowerShell** 语法。

### 2.4 只改相关文件

- 与任务无关的文件 **不碰**。
- 动到公共 Mixin / 样式 / 工厂时，显式列出受影响页面并在回归期逐一 smoke test。

---

## 三、回归期（Task Closeout）

### 3.1 通用自检（每次必过）

对照 [08_CHECKLISTS.md](./08_CHECKLISTS.md) 的"✅ 通用"部分：

- [ ] 无 `print()`，全部 `get_logger`。
- [ ] 异常 `exc_info=True`，无裸 `except`。
- [ ] 无硬编码 VISA / 串口地址。
- [ ] `instruments/` 未 import Qt Widget。
- [ ] 耗时 IO 未在主线程。
- [ ] 跨线程仅用 Signal/Slot。
- [ ] 未主动新增 `*.md` / README。
- [ ] 未执行 `git commit`。

### 3.2 专项 Checklist

按任务类型勾 [08_CHECKLISTS.md](./08_CHECKLISTS.md) 对应段落：
**仪器 / UI 页面 / 测试流程 / 重构 / 打包**。

### 3.3 功能验证

1. **Mock 模式 smoke test**：`debug_config.DEBUG_MOCK = True` 启动，走一遍主链路。
2. **真机验证**（有硬件时）：核心操作一次跑通。
3. **公共组件改动** → 列出受影响页面，**逐一**回归。
4. **打包验证**（若动了资源 / DLL / spec）：
   ```powershell
   python -m PyInstaller spec/kk_lab.spec --clean --noconfirm
   ```

### 3.4 静态检查

- 项目当前未配置 `ruff` / `mypy`。
- 若引入新 lint / typecheck / test 命令：
  1. 同步更新 [02_COMMANDS.md](./02_COMMANDS.md)；
  2. 在 [CLAUDE.md](../../CLAUDE.md) 第 5 节追加；
  3. 在 [.trae/rules/project-rules.md](../../.trae/rules/project-rules.md) "5. 提交与确认" 提示本次要运行。

### 3.5 文档沉淀（按需，不强制）

| 触发条件 | 沉淀位置 |
|---|---|
| 架构级 / 方向性决策 | 新增 [docs/ai/decisions/NNN-xxx.md](./decisions/)（ADR 编号顺延） |
| 新踩的坑 / 规避技巧 | 追加到 [03_GOTCHAS.md](./03_GOTCHAS.md) |
| 长期有效的偏好 / 约定 | 写入 [.ai/memory.md](../../.ai/memory.md)，并在"变更履历"追加一行 |
| 新增命令 / 工具 | 更新 [02_COMMANDS.md](./02_COMMANDS.md) |
| 新功能分组 / 页面 | 按需更新 [00_OVERVIEW.md](./00_OVERVIEW.md) 目录速览 |

> ⚠️ 文档沉淀仅写**长期有效**的内容；一次性调试步骤、临时脚本**不要**写进来。

### 3.5.1 工程清单同步矩阵（强制）

与 [.trae/rules/project-rules.md §8](../../.trae/rules/project-rules.md) 对齐，回归期必须逐项核对：

| 触发条件 | 必须同步 |
|---|---|
| 新增 / 删除 / 重命名**目录或顶层重要文件**（含 `.py` / `.md` / 资源子目录） | [DIRECTORY_STRUCTURE.txt](../../DIRECTORY_STRUCTURE.txt) 对应段落 |
| 新增 `resources/` 子目录 / `lib/` 下新 DLL / `chips/` 子目录 / 任何**运行时**进入安装包的资源 | [spec/kk_lab.spec](../../spec/kk_lab.spec) 的 `datas`（必要时 `hiddenimports`） |
| 新增 / 重命名**功能页面**或顶层功能入口 | [helps/](../../helps/) 对应 HTML |
| 源码 `import` 了**新第三方包**或锁定版本变动 | [requirements.txt](../../requirements.txt) |
| 仅新增 / 修改 `docs/ai/*.md` / `.ai/memory.md` / `AGENTS.md` / `CLAUDE.md` / `.trae/rules/*` 等**纯文档** | 只同步 [DIRECTORY_STRUCTURE.txt](../../DIRECTORY_STRUCTURE.txt)；spec / helps / requirements **不改** |

> ⚠️ `DIRECTORY_STRUCTURE.txt` 与 `requirements.txt` 是历史盲区，必须由 AI 在回归期主动核对，不要默认"自己没碰过就不用改"。

### 3.6 汇报与确认

交付时给用户一段结构化摘要：

```
【变更摘要】
- 改动文件：xxx、yyy
- 核心逻辑：...
- 验证方式：Mock smoke / 真机 / 打包
- 风险 / 待办：...
- 是否需要 git commit？（默认否，等用户指令）
```

**除非用户明确说"提交"，否则不 `git commit`。**

---

## 四、流程图（速记）

```
┌────────────┐     ┌────────────┐     ┌────────────┐
│  调用期     │ ──▶ │  执行期     │ ──▶ │  回归期     │
│ Intake     │     │ Doing      │     │ Closeout   │
├────────────┤     ├────────────┤     ├────────────┤
│ 铁律加载    │     │ 分层纪律    │     │ 通用自检    │
│ 长期记忆    │     │ 编辑偏好    │     │ 专项 CL     │
│ 必读三件套   │     │ 工具并行    │     │ 功能验证    │
│ 专题按需读   │     │ 只改相关    │     │ 静态检查    │
│ 代码探查    │     │             │     │ 文档沉淀    │
│ 不确定提问   │     │             │     │ 汇报确认    │
└────────────┘     └────────────┘     └────────────┘
```

---

## 五、常见反例（不要做）

| ❌ 反例 | ✅ 正例 |
|---|---|
| 上来直接改代码，不读 03_GOTCHAS | 先必读三件套，再动手 |
| UI 页面里直接 `visa.open_resource(...)` | 通过 `core/` + QThread + `factory.create_xxx` |
| 改完不测就说"完成" | Mock smoke / 真机 / 公共组件全回归 |
| 任务完成主动 `git commit` | 等用户明确指令 |
| 主动新建 `README.md` 解释改动 | 写进汇报摘要 + `.ai/memory.md` |
| 改了 spec 不验证打包 | `PyInstaller --clean --noconfirm` 走一遍 |

---

## 六、与其他文档的引用关系

- 上游入口：[CLAUDE.md](../../CLAUDE.md)、[AGENTS.md](../../AGENTS.md)、[.trae/rules/project-rules.md](../../.trae/rules/project-rules.md)
- 上游记忆：[.ai/memory.md](../../.ai/memory.md)
- 平级专题：[00_OVERVIEW.md](./00_OVERVIEW.md) ~ [08_CHECKLISTS.md](./08_CHECKLISTS.md)
- 下游沉淀：[decisions/](./decisions/)

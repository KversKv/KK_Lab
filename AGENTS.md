# KK_Lab - AI Agents 协作指引（通用入口 · 路由器）

> 本文件是 KK_Lab 全项目 **AI 协作通用指引（硬红线为通用铁律）**，同时承担路由职责：加载决策 SOP + 硬红线 + 子模块地图 + 分发索引。
> 深度知识按需从 docs/ai/ 与子模块 AGENTS.md 拉取，**禁止预防性通读全量文档**。

---

## 🔴 加载决策 SOP（每次任务第一步，禁止跳过）

1. **判定任务涉及的【子模块路径】**（如 `ui/pages/pmu`、`instruments/`、`core/`）。
2. **读取命中路径的 `AGENTS.md`**（若存在），并**向我报告**：`已读 <路径>/AGENTS.md`。
   - 子模块 AGENTS.md 加载规则：**就近继承**——沿路径从上到下叠加（如改 `ui/pages/pmu` → 依次读 `ui/AGENTS.md`（若有）→ `ui/pages/pmu/AGENTS.md`），下层覆盖上层同名约定。
3. **查下方【分发索引表】**，加载命中行的"必读"深度文档（docs/ai/）。
4. 子模块 AGENTS.md 中出现 `@see docs/ai/xx` 时，**按需追加**加载该专题。
5. 仍无匹配 → 默认 `09_WORKFLOW` + `03_GOTCHAS`。
6. **全程只加载"命中"文档**，禁止一次性通读 docs/ai/ 或所有子模块 AGENTS.md。

### 收尾维护规则（任务结尾）

- **只维护本次真正改动所在的那一级 `AGENTS.md`**（不逐级、不全量）。
- 维护内容仅限：本模块新增的局部约定 / 新踩的坑 / 接口契约变更；跨模块坑写入 `docs/ai/03_GOTCHAS.md`。
- 同步核对 `docs/ai/08_CHECKLISTS.md` 的【同步矩阵】。

---

## 🔴 硬红线（贯穿全项目，任何任务都适用）

1. 禁 `print()`，统一 `log_config.get_logger(__name__)`。
2. 分层：`main.py → ui/ ←→ core/ → instruments/ → lib/`
   - `ui/` 禁阻塞 IO，走 `core/` 或 QThread + Signal/Slot；
   - `instruments/` 禁依赖 Qt Widget / UI。
3. 仪器统一走 `instruments/factory.py` 创建；新驱动必配 `MockXxx`（`instruments/mock/`）；VISA 禁 `'@py'`；地址禁硬编码。
4. 图标仅 SVG 入 `resources/`；`.ico` 仅打包用。
5. `QDialog` 必传 `parent=self`；OK/Cancel 显式二元化。
6. 数值 QLabel 必含单位：`名称 (单位)`。
7. `ExecutionLogsFrame` 必配 `QSplitter(Qt.Vertical)`。
8. 控件高度单一权威：页面父 QSS 禁裸 `min-height`，控件用 `#objectName` 钉死。
9. 中文→简体；不增删无关注释；**不主动 `git commit`**。
10. 版本号唯一事实源 = [version.py](./version.py)，禁止写死版本号字符串，与 git 解耦。

---

## 项目一句话概述

**KK_Lab** 是基于 **PySide6** 的 Windows 桌面工具，通过 VISA / 串口 / USB-I2C 控制实验室仪器（电源分析仪 N6705C、示波器 DSOX4034A / MSO64B、VT6002 温箱等），完成 BES 芯片的 PMU / Charger / 功耗 / 波形类自动化测试。

## 分层（铁律）

```

main.py → ui/ ←→ core/ → instruments/ → lib/
               ↑
         log_config / debug_config

```

---

## 🗺️ 子模块地图（路由用 · 定位任务落在哪）

> 判定任务子模块路径后，优先读对应目录的 `AGENTS.md`（若存在）。带 ✅ 者应优先建/维护局部 AGENTS.md。

| 子模块路径 | 职责 | 局部 AGENTS.md | 深度专题 @see |
|---|---|---|---|
| `ui/pages/` ✅ | 各功能页（PMU/Charger/功耗/波形…） | **有**（第一批）；页级下沉待第二批 | 06_PAGE_GUIDE · 01_CONVENTIONS§6 |
| `ui/modules/` ✅ | 可复用 UI 控件/连接 Mixin | **有**（第一批） | 06_PAGE_GUIDE · 01_CONVENTIONS§6 |
| `ui/widgets/` | 通用控件（combobox/sidebar/plot…） | 无 · 第二批 | 01_CONVENTIONS§6 · 03_GOTCHAS |
| `core/` ✅ | 业务逻辑 / 测试流程编排 | **有**（第一批） | 07_TEST_GUIDE · 04_ARCHITECTURE |
| `core/ai/` ✅ | AI 助手子系统 | **有**（第一批） | decisions/003 · 004 · 03_GOTCHAS§26 |
| `instruments/` ✅ | 仪器驱动 | **有**（第一批） | 05_INSTRUMENT_GUIDE · 04_ARCHITECTURE |
| `instruments/mock/` | Mock 实现 | 随 instruments | 05_INSTRUMENT_GUIDE |
| `lib/` | 底层通信/工具 | 无 · 第二批 | 04_ARCHITECTURE |
| `spec/` | PyInstaller 打包 | 无 · 第二批 | 08_CHECKLISTS · 02_COMMANDS |
| 根目录/全局 | 版本、环境、跨模块 | 本文件 | 见分发表 |

---

## 运行 / 打包

> 📌 项目自带虚拟环境 `.venv/`（根目录），命令前先激活。

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
python -m PyInstaller spec/kk_lab.spec --clean --noconfirm
python -m PyInstaller spec/n6705c_datalog.spec --clean --noconfirm
```

更多命令见 [docs/ai/02_COMMANDS.md](./docs/ai/02_COMMANDS.md)。

---

## 分发索引表（深度专题按需加载）

> 定位任务类型 → 加载"必读"；"可选"按需拉取。命中多行取**并集**。

| 任务类型（触发词） | 必读（Must-Read） | 可选（On-Demand） |
| -------------------- | ------------------- | ------------------- |
| **新增 / 修改仪器驱动**                   | [05_INSTRUMENT_GUIDE](./docs/ai/05_INSTRUMENT_GUIDE.md) · [04_ARCHITECTURE](./docs/ai/04_ARCHITECTURE.md) · [03_GOTCHAS](./docs/ai/03_GOTCHAS.md)          | [01_CONVENTIONS](./docs/ai/01_CONVENTIONS.md)                  |
| **新增 / 修改 UI 页面 / 对话框 / 控件**                   | [06_PAGE_GUIDE](./docs/ai/06_PAGE_GUIDE.md) · [01_CONVENTIONS §6](./docs/ai/01_CONVENTIONS.md) · [03_GOTCHAS](./docs/ai/03_GOTCHAS.md)          | [04_ARCHITECTURE](./docs/ai/04_ARCHITECTURE.md)                  |
| **新增 / 修改测试流程（PMU/Charger/…）**                   | [07_TEST_GUIDE](./docs/ai/07_TEST_GUIDE.md) · [04_ARCHITECTURE](./docs/ai/04_ARCHITECTURE.md) · [08_CHECKLISTS](./docs/ai/08_CHECKLISTS.md)          | [01_CONVENTIONS](./docs/ai/01_CONVENTIONS.md)                  |
| **PyInstaller 打包 / spec 修改**                   | [03_GOTCHAS](./docs/ai/03_GOTCHAS.md) · [08_CHECKLISTS](./docs/ai/08_CHECKLISTS.md) · [02_COMMANDS](./docs/ai/02_COMMANDS.md)          | —                |
| **排查 Bug / 回归报错**                   | [03_GOTCHAS](./docs/ai/03_GOTCHAS.md) · [09_WORKFLOW](./docs/ai/09_WORKFLOW.md) · [memory.md](./docs/ai/memory.md)          | [decisions/](./docs/ai/decisions/)                  |
| **重构 / 架构调整 / 分层变动**                   | [04_ARCHITECTURE](./docs/ai/04_ARCHITECTURE.md) · [00_OVERVIEW](./docs/ai/00_OVERVIEW.md) · [decisions/](./docs/ai/decisions/)          | [01_CONVENTIONS](./docs/ai/01_CONVENTIONS.md)                  |
| **新增依赖 / 环境配置**                   | [02_COMMANDS](./docs/ai/02_COMMANDS.md) · [08_CHECKLISTS](./docs/ai/08_CHECKLISTS.md)              | —                |
| **版本号 / 发版 / 改版本**                   | [10_VERSIONING](./docs/ai/10_VERSIONING.md)                  | [08_CHECKLISTS](./docs/ai/08_CHECKLISTS.md)                  |
| **按 SOP 走 / 大任务开工**                   | [09_WORKFLOW](./docs/ai/09_WORKFLOW.md) · [08_CHECKLISTS](./docs/ai/08_CHECKLISTS.md)              | 上述所有          |
| **纯文档 / 规则维护**                   | [08_CHECKLISTS §同步矩阵](./docs/ai/08_CHECKLISTS.md) · [.trae/rules/project-rules.md](./.trae/rules/project-rules.md)              | —                |

### 阅读规则

1. 命中多行任务类型 → **并集必读**。
2. 找不到匹配 → 默认 [09_WORKFLOW](./docs/ai/09_WORKFLOW.md) + [03_GOTCHAS](./docs/ai/03_GOTCHAS.md)。
3. 跨层改动（ui ↔ core ↔ instruments）必加读 [04_ARCHITECTURE](./docs/ai/04_ARCHITECTURE.md)。
4. 改动完成前必须核对 [08_CHECKLISTS](./docs/ai/08_CHECKLISTS.md) 的同步矩阵。

---

## 🔴 编辑铁律：向文件追加 / 定位 EOF（高频坑，必读）

> **背景**：`SearchReplace` 只替换**首个**匹配。当 `old_str` 选用了文件中**多处重复**的模板片段（典型：各 Mock 类共有的 `format_current` / `def close(self): pass` / `return f"{...:.3e} A"`），会误命中**靠前**那处，把新类**插进别的类中间**，劈裂已有类。**严禁再犯。**

### 必须遵守

1. **追加到文件末尾 ≠ 凭印象找 EOF**。动手前先用 `Grep -n "^class "` 或 `Read`（带 offset）确认真实最后一行。
2. **`old_str`** **必须全局唯一**。先 `Grep` 统计候选锚点出现次数：

   - 1 次 → 可直接用；≥ 2 次 → **禁止**，须叠加上文唯一行扩展锚点直到整段唯一。
3. **不要用各类通用尾部模板**（`format_current` / `format_voltage` / `def close` / `def disconnect`）单独做锚点。
4. 每次编辑后**立即复核结构**：`Grep -n "^class |def <特征方法>"`，确认目标类落在 EOF 且相邻类未被劈裂。
5. 误插入后先精确删除误插块、恢复原类，再以唯一锚点重新追加。

### 反例（真实事故）

- 用 `MockN6705C` 末尾的 `format_current` 当锚点追加 `MockKeysight34461A`，因该片段多处重复，首个匹配落在 `MockN6705C` 内，新类被插入其中间，`arb_on` 等方法被孤立 → 反复重写。
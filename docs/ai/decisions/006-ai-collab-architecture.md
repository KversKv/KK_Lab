# ADR 006 - AI 协作体系重构：路由器 + 分层就近加载三层架构

- **状态**：Accepted
- **日期**：2026-07-24
- **范围**：根 `AGENTS.md`、`.trae/rules/project-rules.md`、`docs/ai/`（00–10 + memory + decisions）、新增 5 个子模块 `AGENTS.md`、`DIRECTORY_STRUCTURE.txt`
- **关联**：[09_WORKFLOW.md](../09_WORKFLOW.md)（SOP 关系）、[08_CHECKLISTS.md](../08_CHECKLISTS.md)（同步矩阵）

---

## 背景

原 AI 协作知识集中在 `docs/ai/`（00–10 编号制）。每次任务按 SOP 需通读「必读三件套」（00/03/08）+ 按类型加读专题，token 开销大、信噪比低；且坑点（03_GOTCHAS）与模块强相关却全局混放，AI 难以只取所需。

同时盘点发现 `docs/ai/` 存在文档漂移：06/08 引用已被 ADR 005 迁移到 `ui/modules/` 的连接 Mixin 旧路径/旧类名（`ui/styles/*_module_frame.py`、`N6705CModuleFrame` 等）；10_VERSIONING 的 MODULE_VERSION 表含已不存在的 `custom_test` 且缺多个实际模块；04_ARCHITECTURE 目录树缺 ADR 005 之后新增的 core 子包。

## 决策

采用 **三层架构**：`总 AGENTS.md（路由器）+ 子模块 AGENTS.md（局部知识就近）+ docs/ai/（跨模块深度专题）`。

1. **根 AGENTS.md = 路由器**：只保留加载决策 SOP、硬红线、子模块地图、分发索引、编辑铁律；深度知识一律下放，禁止在根堆知识。（该文件此前已是路由器形态，本轮仅校对子模块地图。）

2. **子模块 AGENTS.md = 局部知识就近**：按归属把"只与某模块相关"的坑/约定/契约下沉到该模块目录，统一模板（加载指针 / 职责边界 / 接口契约 / 局部约定 / 局部坑点）。第一批 5 个高频模块：`instruments/`、`core/`、`core/ai/`、`ui/pages/`、`ui/modules/`。

3. **docs/ai/ = 跨模块深度专题库**：00–10 编号与 memory/decisions 结构不变；每篇顶部加「📌 何时读我」标注触发场景与来源子模块，形成双向索引。

4. **03_GOTCHAS 全文保留**：作为坑点唯一事实源（memory 多处引用其章节号），子模块「局部坑点」只放精炼版并以 §N 回指 03，**不删除 03 原文**、不做内容迁移。

5. **加载路径**：根 AGENTS SOP 判定子模块路径 → 读命中子模块 `AGENTS.md`（就近继承，下层覆盖上层）→ 按子模块内 `@see docs/ai/xx` 深挖专题 → 禁止预防性通读全量文档。

6. **文档漂移顺手修正**：6 处（见"影响"），使文档与代码现状一致。

## 归属原则

| 判定 | 标准 | 去向 |
|---|---|---|
| 局部 | 只与某一子模块相关（如"VISA 后端选择"→instruments） | 下沉到该子模块 AGENTS.md |
| 全局/跨模块 | 涉及多层或全项目（如分层铁律、SOP、版本规范、同步矩阵） | 保留在 docs/ai/ 或根 AGENTS.md |

## 影响

- **新增**：`instruments/AGENTS.md`、`core/AGENTS.md`、`core/ai/AGENTS.md`、`ui/pages/AGENTS.md`、`ui/modules/AGENTS.md`；`DIRECTORY_STRUCTURE.txt` 已同步 5 处。
- **docs/ai**：12 篇加「何时读我」头；06/08 Mixin 路径与类名→`ui/modules/` 真实名（`N6705CConnectionMixin` 等）+ 日志区示例改 `ExecutionLogsFrame.wrap_with`；04 目录树补 core 子包（instruments/、pmu_test/、ai/、orchestrator/ 等）与页面分包；10 MODULE_VERSION 表删 `custom_test`、补 module_test/orchestrator/pmu/IIC_Module/ui/ai/core 子包；01§6 Mixin 路径修正；memory.md 追加变更履历。
- **根 AGENTS.md**：子模块地图校对（补 `core/ai/`、`ui/widgets/` 行，标注第一批/第二批）。
- **project-rules.md**：「前置义务」补子模块就近加载约定，与根 AGENTS 同源。
- **docs/ai 编号不变**；`decisions/` 顺延至 006。

## 遗留 / 后续（第二批）

- `ui/widgets/`、`lib/i2c/`、`ui/ai/`、`spec/` 子模块 AGENTS.md 尚未建，根地图已标"无 · 第二批"。
- 页级下沉（如 `ui/pages/n6705c_power_analyzer/` 的 Tab 盒模型 §25、`ui/pages/pmu/` 等主力页）列入第二批。
- 既有就近文档保持原样、仅被引用不合并：`ui/pages/pmu/pmu_1811/README.md + RULES.md`、`ui/modules/serialCom_module/*.md`、`core/ai/DEBUG_WORKBENCH.md` 等。

## 相关

- [09_WORKFLOW.md](../09_WORKFLOW.md)、[08_CHECKLISTS.md](../08_CHECKLISTS.md)、[03_GOTCHAS.md](../03_GOTCHAS.md)
- 上游入口：[AGENTS.md](../../AGENTS.md)、[.trae/rules/project-rules.md](../../.trae/rules/project-rules.md)

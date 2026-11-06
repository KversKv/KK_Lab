# 文档导航与归档规则

本目录同时包含研发规范、长期参考资料、产品手册和运行期 AI 资料。提交前先判断资料的生命周期，再选择存放位置；临时产物不得散落在仓库根目录或 `docs/` 根目录。

## 文档分类

| 路径 | 用途 | 维护规则 |
|---|---|---|
| [`ai/`](./ai/) | AI 协作规范、架构专题、常见问题和历史功能提案 | 按 `AGENTS.md` 的文档同步矩阵维护 |
| [`plans/`](./plans/) | 有明确范围、验收条件或进度表的工程计划与设计稿 | 使用主题名称；实施后根据验收证据更新状态，过期计划保留并标注结论 |
| [`User Manual/`](./User%20Manual/) | 面向使用者的操作手册 | 按产品功能组织，不放研发临时记录 |
| [`user/`](./user/) | 长期技术参考、测试方法和历史分析 | 只保留有复用价值的资料；数据文件按 DLP 规则放入 `Temp_Docs/` |
| [`kk_lab_ai_memory/`](./kk_lab_ai_memory/) | 程序运行期加载的 AI 知识库 | 该路径与 `core/ai/`、打包配置存在契约；未经代码引用和打包检查，不得移动或清理 |

## 临时资料区

项目内唯一的临时资料区是仓库根目录的 `Temp_Docs/`，整个目录由 Git 忽略。CSV、XLSX、PDT、PDF 等受 DLP 影响的文件不得保存在 Git 跟踪路径中。

| 路径 | 内容 |
|---|---|
| `Temp_Docs/docs/`、`Temp_Docs/tests/`、`Temp_Docs/ui/` | 从对应项目路径迁出的 DLP 文件；保留原相对路径，避免破坏人工查找习惯 |
| `Temp_Docs/quality/` | 质量门禁结果 |
| `Temp_Docs/smoke_runs/` | 打包或启动冒烟验证产物 |
| `Temp_Docs/archive/` | 已结束的临时资料，按 `diffs/`、`issue_artifacts/`、`reference_materials/`、`notes/`、`logs/`、`scripts/`、`test_outputs/`、`config_snapshots/`、`working_tree_snapshots/` 分类 |
| `Temp_Docs/kk_lab_release_venv/` | 本机发布验证虚拟环境，保留为本地工具，不入库 |

不要新建根目录 `Temp/` 或把临时报告放到源码目录。历史 `Temp/` 内容已整理至 `Temp_Docs/archive/`；新生成文件按类型放入上述分类。确认可重建的缓存或一次性测试输出后再删除；芯片资料、人工记录和有效验证结果应先归档。

## 目录维护

- 根目录只放项目入口、全局配置和职责清楚的一级模块；新增一级目录时同步更新 [`DIRECTORY_STRUCTURE.txt`](../DIRECTORY_STRUCTURE.txt)。
- `core/`、`ui/`、`instruments/` 等源码目录按架构边界保留，不为减少目录数量而混合不同职责。
- 新计划先放入 `plans/`，在计划中写清范围、验收条件和进度维护方式；不要使用含义不清的临时文件名或新建“NewPlan”目录。
- 清理前检查 Git 跟踪状态、代码/文档引用和运行期路径；不确定用途的文件先归档，不直接删除。

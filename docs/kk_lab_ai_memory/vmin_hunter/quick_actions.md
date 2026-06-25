# VminHunter - 快捷指令

> 页面：vmin_hunter
> 模板格式见 [../_shared/conventions.md §5.5](../_shared/conventions.md#55-quick_actionsmd)
> 以下条目从 `core/ai/profiles.py` 中 `AI_PROFILES["vmin_hunter"].quick_actions` 迁移而来。

## QA-20260625-001 - 解读最近一次 Vmin 搜索结果

- 页面：vmin_hunter
- 来源：profile_migration
- 状态：active
- 模板：解读最近一次 Vmin 搜索结果
- 占位符：无
- 适用条件：
  - 当前有 Vmin 搜索结果数据
- 执行预期：
  - AI 依据真实搜索结果解读最低工作电压，禁止臆造读数

## QA-20260625-002 - 建议合适的搜索步进与范围

- 页面：vmin_hunter
- 来源：profile_migration
- 状态：active
- 模板：建议合适的搜索步进与范围
- 占位符：无
- 适用条件：
  - 用户准备配置 Vmin 搜索
- 执行预期：
  - AI 结合芯片特性给出搜索步进与电压范围建议

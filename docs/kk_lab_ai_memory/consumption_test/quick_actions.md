# 功耗测试 - 快捷指令

> 页面：consumption_test
> 模板格式见 [../_shared/conventions.md §5.5](../_shared/conventions.md#55-quick_actionsmd)
> 以下条目从 `core/ai/profiles.py` 中 `AI_PROFILES["consumption_test"].quick_actions` 迁移而来。

## QA-20260625-001 - 生成一份功耗测试配置草案

- 页面：consumption_test
- 来源：profile_migration
- 状态：active
- 模板：生成一份功耗测试配置草案
- 占位符：无
- 适用条件：
  - 当前在功耗测试页面
- 执行预期：
  - AI 生成功耗测试配置草案，经预览与校验后才能应用

## QA-20260625-002 - 解读最近一次功耗电流数据

- 页面：consumption_test
- 来源：profile_migration
- 状态：active
- 模板：解读最近一次功耗电流数据
- 占位符：无
- 适用条件：
  - 当前有功耗电流数据
- 执行预期：
  - AI 依据真实数据解读电流功耗，禁止臆造读数

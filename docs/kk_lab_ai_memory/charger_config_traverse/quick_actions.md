# Charger 配置遍历 - 快捷指令

> 页面：charger_config_traverse
> 模板格式见 [../_shared/conventions.md §5.5](../_shared/conventions.md#55-quick_actionsmd)
> 以下条目从 `core/ai/profiles.py` 中 `AI_PROFILES["charger_test"].quick_actions` 按子页面相关性迁移而来。

## QA-20260625-001 - 生成一份充电测试配置草案

- 页面：charger_config_traverse
- 来源：profile_migration
- 状态：active
- 模板：生成一份充电测试配置草案
- 占位符：无
- 适用条件：
  - 当前在 Charger 配置遍历子页面
- 执行预期：
  - AI 生成充电配置遍历测试草案，经预览与校验后才能应用

## QA-20260625-002 - 分析最近一次充电测试结果

- 页面：charger_config_traverse
- 来源：profile_migration
- 状态：active
- 模板：分析最近一次充电测试结果
- 占位符：无
- 适用条件：
  - 当前有充电测试结果数据
- 执行预期：
  - AI 依据真实结果数据解读，禁止臆造读数

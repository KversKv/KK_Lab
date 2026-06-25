# N6705C Datalog - 快捷指令

> 页面：datalog
> 模板格式见 [../_shared/conventions.md §5.5](../_shared/conventions.md#55-quick_actionsmd)
> 以下条目从 `core/ai/profiles.py` 中 `AI_PROFILES["datalog"].quick_actions` 迁移而来。

## QA-20260625-001 - 解读最近一次 Datalog 数据趋势

- 页面：datalog
- 来源：profile_migration
- 状态：active
- 模板：解读最近一次 Datalog 数据趋势
- 占位符：无
- 适用条件：
  - 当前有 Datalog 波形数据摘要
- 执行预期：
  - AI 依据波形数据摘要解读趋势，禁止臆造读数

## QA-20260625-002 - 统计电流尖峰事件的位置与峰值

- 页面：datalog
- 来源：profile_migration
- 状态：active
- 模板：统计电流尖峰事件的位置与峰值
- 占位符：无
- 适用条件：
  - 当前有 Datalog 波形数据摘要且含尖峰事件
- 执行预期：
  - AI 以「尖峰事件（按时间聚簇）」处数为准，不把超阈采样点数当脉冲个数

## QA-20260625-003 - 建议合适的采样率与时长

- 页面：datalog
- 来源：profile_migration
- 状态：active
- 模板：建议合适的采样率与时长
- 占位符：无
- 适用条件：
  - 用户准备配置 Datalog 采集
- 执行预期：
  - AI 结合待测信号特征给出采样率与时长建议

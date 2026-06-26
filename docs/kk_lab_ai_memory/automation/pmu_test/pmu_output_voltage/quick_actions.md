# PMU 输出电压 - 快捷指令

> 页面：pmu_output_voltage
> 模板格式见 [../_shared/conventions.md §5.5](../_shared/conventions.md#55-quick_actionsmd)
> 以下条目从 `core/ai/profiles.py` 中 `AI_PROFILES["pmu_test"].quick_actions` 按子页面相关性迁移而来。

## QA-20260625-001 - 分析最近一次 PMU 测试结果

- 页面：pmu_output_voltage
- 来源：profile_migration
- 状态：active
- 模板：分析最近一次 PMU 测试结果
- 占位符：无
- 适用条件：
  - 当前有 PMU 输出电压测试结果数据
- 执行预期：
  - AI 依据真实结果数据解读输出电压表现，禁止臆造读数

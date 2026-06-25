# PMU DCDC 效率 - 快捷指令

> 页面：pmu_dcdc_efficiency
> 模板格式见 [../_shared/conventions.md §5.5](../_shared/conventions.md#55-quick_actionsmd)
> 以下条目从 `core/ai/profiles.py` 中 `AI_PROFILES["pmu_test"].quick_actions` 按子页面相关性迁移而来。

## QA-20260625-001 - 生成一份 DCDC 效率测试配置草案

- 页面：pmu_dcdc_efficiency
- 来源：profile_migration
- 状态：active
- 模板：生成一份 DCDC 效率测试配置草案
- 占位符：无
- 适用条件：
  - 当前在 PMU DCDC 效率子页面
- 执行预期：
  - AI 生成 DCDC 效率测试配置草案，经预览与校验后才能应用

## QA-20260625-002 - 分析最近一次 PMU 测试结果

- 页面：pmu_dcdc_efficiency
- 来源：profile_migration
- 状态：active
- 模板：分析最近一次 PMU 测试结果
- 占位符：无
- 适用条件：
  - 当前有 PMU 测试结果数据
- 执行预期：
  - AI 依据真实结果数据解读，禁止臆造读数

## QA-20260625-003 - 测 1~200mA 效率

- 页面：pmu_dcdc_efficiency
- 来源：phase4_capability_boundary
- 状态：active
- 模板：测 1~200mA 效率
- 占位符：无
- 适用条件：
  - 当前在 PMU DCDC 效率子页面
  - 已连接 N6705C 仪器
- 执行预期：
  - AI 经 get_current_test_config 读取当前配置 → 应用 1~200mA 扫描范围 → 弹确认 → 启动本页测试

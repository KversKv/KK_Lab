# pmu_dcdc_efficiency 页面测试项（test_items）

> 总记忆见伞目录 [../automation/pmu_test/test_items.md](../automation/pmu_test/test_items.md)
> 条目格式见 [../_shared/conventions.md §5.3](../_shared/conventions.md#53-test_itemsmd)

## T-20260626-151101 - 各路 BUCK 转换效率测试

- 页面：pmu_dcdc_efficiency
- 目标：测各路 BUCK 在负载范围内的效率曲线
- 前置条件：
  - 调试初期用 LDO→DCDC 配置初测；可休眠后用休眠 bin、BUCK 切 normal mode 复测
- 参数：
  - rail: 被测 BUCK 路
  - load: 1~200mA ramp（被测路），另一路保持 5mA
- 步骤：
  1. 被测 BUCK 加 1~200mA ramp 负载
  2. 记录输入/输出功率算效率
- 期望结果：
  - 效率曲线符合 datasheet
- 数据记录：
  - 负载-效率表
- 适用范围：
  - 所有含 DCDC 的 PMU
- 关联项：
  - 伞目录 test_items: T-20260626-150103

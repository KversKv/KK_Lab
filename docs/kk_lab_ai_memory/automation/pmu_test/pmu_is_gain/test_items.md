# pmu_is_gain 页面测试项（test_items）

> 总记忆见伞目录 [../test_items.md](../test_items.md)
> 条目格式见 [../../../_shared/conventions.md §5.3](../../../_shared/conventions.md#53-test_itemsmd)

## T-20260626-151501 - BUCK 各挡位 IS_GAIN / 电流采样阈值

- 页面：pmu_is_gain
- 目标：验证各 BUCK 挡位 IS_GAIN（电流采样增益）及阈值，确认是否需校准
- 前置条件：
  - 各 BUCK 可独立配置挡位
- 参数：
  - is_gain: 各挡位 IS_GAIN 寄存器
- 步骤：
  1. 遍历挡位测 IS_GAIN
  2. 比对设计阈值
- 期望结果：
  - IS_GAIN 符合设计；偏差需校准（1503P IS_GAIN 需校准）
- 数据记录：
  - 挡位-IS_GAIN-阈值表
- 适用范围：
  - 含电流采样的 BUCK
- 关联项：
  - 伞目录 memory: M-20260626-150002（死区/频率/edge 基线）

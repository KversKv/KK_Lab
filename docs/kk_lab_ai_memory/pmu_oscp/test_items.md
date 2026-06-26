# pmu_oscp 页面测试项（test_items）

> 总记忆见伞目录 [../automation/pmu_test/test_items.md](../automation/pmu_test/test_items.md)
> 条目格式见 [../_shared/conventions.md §5.3](../_shared/conventions.md#53-test_itemsmd)

## T-20260626-151301 - 保护电路（OVP/OCP/SCP/UVLO）

- 页面：pmu_oscp
- 目标：验证过压/过流/短路/欠压保护阈值与上报
- 前置条件：
  - 可注入过压/过流/短路条件；abort_source 上报配置
- 参数：
  - thr: 各保护阈值寄存器
- 步骤：
  1. 逐项触发保护
  2. 确认动作与上报（abort_source）
- 期望结果：
  - 阈值正确、上报正确
- 数据记录：
  - 各保护阈值实测
- 适用范围：
  - 含保护功能的 PMU
- 关联项：
  - 伞目录 test_items: T-20260626-150107

## T-20260626-151302 - SPK 短路保护（ocp_sel）

- 页面：pmu_oscp
- 目标：验证 SPK 输出短路限流保护
- 前置条件：
  - SPK 含 DAC（1806P 无 DAC，不适用）
- 参数：
  - ocp_sel: 限流挡位
- 步骤：
  1. 短路 SPK 输出
  2. 观察限流持续时间（约 1ms）
- 期望结果：
  - 正常限流，最低档注意误触风险
- 数据记录：
  - 限流值与持续时间
- 适用范围：
  - 含 SPK DAC 的 PMU

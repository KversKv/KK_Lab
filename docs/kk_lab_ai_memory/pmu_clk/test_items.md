# pmu_clk 页面测试项（test_items）

> 总记忆见伞目录 [../automation/pmu_test/test_items.md](../automation/pmu_test/test_items.md)
> 条目格式见 [../_shared/conventions.md §5.3](../_shared/conventions.md#53-test_itemsmd)

## T-20260626-151401 - LPO 频率范围/JITTER/频偏/高低温

- 页面：pmu_clk
- 目标：验证 LPO 默认频率、范围、JITTER、软件频偏与高低温一致性
- 前置条件：
  - 频率计/示波器
- 参数：
  - repeat: 100 次软件频偏
- 步骤：
  1. 测默认频率/频率范围/JITTER
  2. 100 次软件频偏
  3. 高低温与休眠唤醒频偏
- 期望结果：
  - 频率范围与频偏满足规格（1806P 35.2k~96.6kHz；1811 20.82k~75.67kHz）
- 数据记录：
  - 频率范围、JITTER、频偏
- 适用范围：
  - 含 LPO 的 PMU
- 关联项：
  - 伞目录 test_items: T-20260626-150108

## T-20260626-151402 - 外部 32K 晶体（Capbit/静态功耗/重载）

- 页面：pmu_clk
- 目标：验证外部 32K Capbit、静态功耗与 PMU 重载对频率影响
- 前置条件：
  - 外接 32K 晶体
- 参数：
  - capbit: 默认 9'b1_0010_0000（约 32.7646kHz）
- 步骤：
  1. 测 Capbit 对应频率
  2. 测静态功耗、高低温
  3. PMU 重载观察频率变化
- 期望结果：
  - 频率与功耗满足规格
- 数据记录：
  - Capbit-频率表、静态功耗
- 适用范围：
  - 含外部 32K 的 PMU

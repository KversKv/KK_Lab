# pmu_gpadc 页面测试项（test_items）

> 总记忆见伞目录 [../test_items.md](../test_items.md)
> 条目格式见 [../../../_shared/conventions.md §5.3](../../../_shared/conventions.md#53-test_itemsmd)

## T-20260626-151201 - GPADC 精度/稳定性/高低温

- 页面：pmu_gpadc
- 目标：验证各通道精度、稳定性与温度一致性
- 前置条件：
  - FT 校准完成；burst mode 配置；timer=2000 counts；Vref=1.5V
- 参数：
  - channel: 待测通道（例 1307 CH0 温度 / CH1 VSYS DIV4 / CH3 EXT1；1811 共 12 通道）
  - repeat: 2000~10000 次
- 步骤：
  1. 各通道输入已知电压（输入 0 时读 offset）
  2. 多次读数统计误差
  3. 高低温复测
- 期望结果：
  - 误差 ≤ ±10mV 为 pass
- 数据记录：
  - 各通道误差、稳定性曲线
- 适用范围：
  - 所有 PMU
- 关联项：
  - 伞目录 test_items: T-20260626-150106

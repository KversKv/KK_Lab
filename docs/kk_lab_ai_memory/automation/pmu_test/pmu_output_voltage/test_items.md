# pmu_output_voltage 页面测试项（test_items）

> 总记忆见伞目录 [../test_items.md](../test_items.md)
> 条目格式见 [../../../_shared/conventions.md §5.3](../../../_shared/conventions.md#53-test_itemsmd)

## T-20260626-151001 - 各路输出电压全挡位扫描与线性度

- 页面：pmu_output_voltage
- 目标：遍历各 LDO/DCDC 电压调节寄存器，验证输出范围、步进、线性度，并记录默认挡位
- 前置条件：
  - 已知各路电压寄存器地址与位段；测量通道就绪
- 参数：
  - reg: 电压调节寄存器（例 1307 BUCK_VCORE 0x132[7:0]，默认 0x9D=0.8953V）
  - channel: 测量通道（例 N6705C CH2）
- 步骤：
  1. 从最小到最大遍历寄存器
  2. 每挡读回输出电压
  3. 计算步进与线性度
- 期望结果：
  - 单调无跳变，范围/步进符合规格（1307 BUCK_VCORE 0.3106~1.2602V，步进 3.75mV，线性度 0.22%）
- 数据记录：
  - 挡位→电压→步进→线性度表
- 适用范围：
  - 所有 PMU
- 关联项：
  - 伞目录 test_items: T-20260626-150104
  - lessons: 调压过冲/掉坑见 automation/pmu_test/lessons L-20260626-150202, L-20260626-150204

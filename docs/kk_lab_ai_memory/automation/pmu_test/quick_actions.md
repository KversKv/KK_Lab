# PMU 整套常规测试 - 快捷指令（quick_actions）

> 伞目录：automation/pmu_test
> 条目格式见 [../../_shared/conventions.md §5.5](../../_shared/conventions.md#55-quick_actionsmd)

## QA-20260626-150401 - 输出电压全挡位扫描

- 页面：automation/pmu_test
- 来源：ai_assistant
- 状态：active
- 模板：对 {rail} 路从寄存器 {reg} 最小值扫到最大值，每挡用 {channel} 读回输出电压并记录线性度
- 占位符：
  - rail: 目标电源路，例如 BUCK_VCORE / LDO_VANA
  - reg: 电压调节寄存器，例如 0x132[7:0]
  - channel: 测量通道，例如 N6705C CH2
- 适用条件：
  - 已知目标路寄存器与测量通道
- 执行预期：
  - 触发 pmu_output_voltage 页面挡位扫描动作并汇总线性度

## QA-20260626-150402 - DCDC 效率测试

- 页面：automation/pmu_test
- 来源：ai_assistant
- 状态：active
- 模板：对 {rail} 加 {load_min}~{load_max} ramp 负载，另一路带 {keep}，记录负载-效率曲线
- 占位符：
  - rail: 被测 BUCK 路
  - load_min: 起始负载，默认 1mA
  - load_max: 终止负载，默认 200mA
  - keep: 另一路保持负载，默认 5mA
- 适用条件：
  - 已切到可测效率的 bin（休眠 bin + normal mode）
- 执行预期：
  - 触发 pmu_dcdc_efficiency 页面效率测试动作

## QA-20260626-150403 - GPADC 稳定性读数

- 页面：automation/pmu_test
- 来源：ai_assistant
- 状态：active
- 模板：对 {channel} 通道连续读 {count} 次，统计与 {expect}V 的最大偏差并判定 ±10mV
- 占位符：
  - channel: GPADC 通道
  - count: 读数次数，默认 2000
  - expect: 期望输入电压
- 适用条件：
  - FT 校准完成、burst mode 已配置
- 执行预期：
  - 触发 pmu_gpadc 页面稳定性测试动作

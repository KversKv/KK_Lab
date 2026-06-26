# PMU 整套常规测试 - 结构化测试用例（test_cases）

> 伞目录：automation/pmu_test
> 条目格式见 [../../_shared/conventions.md §5.4](../../_shared/conventions.md#54-test_casesmd)

## TC-20260626-150301 - DCDC 输出电压全挡位线性度扫描

- 页面：automation/pmu_test
- 用例类型：regression / instrument_required
- 输入：
  - chip: 任一 PMU
  - reg: 目标 BUCK 电压寄存器（如 1307 BUCK_VCORE 0x132[7:0]）
  - instrument: N6705C 对应通道测电压
- 执行步骤：
  1. 从最小到最大遍历寄存器值
  2. 每挡读回输出电压
  3. 计算步进与线性度
- 期望行为：
  - 输出随寄存器单调变化，无跳变
- 通过标准：
  - 范围/步进符合规格，线性度优（参考 1307 BUCK_VCORE 0.22%）
- 失败排查：
  - 检查默认值挡位、负载、BG 模式
- 可自动化程度：full

## TC-20260626-150302 - GPADC 稳定性 2000 次读数

- 页面：automation/pmu_test
- 用例类型：regression / instrument_required
- 输入：
  - vref: 1.5V，timer=2000 counts
  - channel: 待测 GPADC 通道，输入已知电压
- 执行步骤：
  1. 配置 burst mode
  2. 连续读 2000 次
  3. 统计最大偏差
- 期望行为：
  - 读数稳定
- 通过标准：
  - 误差 ≤ ±10mV
- 失败排查：
  - 确认 FT 校准、Vref 上电时间/纹波/带载
- 可自动化程度：full

## TC-20260626-150303 - 关机波形（soft / 快速关机）

- 页面：automation/pmu_test
- 用例类型：manual / instrument_required
- 输入：
  - 触发方式：soft poweroff、快速关机+soft poweroff
- 执行步骤：
  1. 分别触发两种关机
  2. 抓 VBAT/各路掉电波形与时间
- 期望行为：
  - 快速关机掉电时间显著缩短
- 通过标准：
  - 时序符合预期（参考 1307PH 7s → 8ms）
- 失败排查：
  - 确认快速关机逻辑/pulldown 配置
- 可自动化程度：partial

# PMU 整套常规测试 - 总经验（lessons）

> 伞目录：automation/pmu_test
> 承载 PMU 常规测试跨芯片、跨页面的踩坑与经验结论。
> 条目格式见 [../../_shared/conventions.md §5.2](../../_shared/conventions.md#52-lessonsmd)

## L-20260626-150201 - SIMO 单电感双输出纹波偏大

- 页面：automation/pmu_test
- 类型：参数经验
- 现象：
  - 1307PH BUCK_VCORE / BUCK_VHPPA 为单电感双输出，输出存在切换，纹波偏大
  - VMIC 依赖 VCM_CAP，VCM_CAP 依赖 BUCK_VHPPA，VHPPA 纹波大导致 VMIC 纹波大
- 原因：
  - 单电感在两路输出间切换产生过冲
- 处理办法：
  - 不考虑切换过冲时平均纹波可降低约一半（如 BUCK_VCORE=10mA、BUCK_VHPPA=50mA）
  - 评估交叉调制对纹波的实际影响，按场景判断可用性
- 验证方式：
  - 抓纹波波形分别记录含过冲与去过冲后的均值
- 风险等级：medium

## L-20260626-150202 - LDO_VCORE_L 过冲与掉坑（1503P A 版）

- 页面：automation/pmu_test
- 类型：坑点
- 现象：
  - 1503P A 版调整电压过程中 LDO_VCORE_L 存在过冲和掉坑
- 原因：
  - A 版供电/调压路径设计
- 处理办法：
  - 采用 B 版 0.6V 方案：BUCK_VHPPA 直接给 Vcore0P6，无过冲/掉坑，可分电使用
  - 1.8V 版兼容旧设计但不推荐分电使用
- 验证方式：
  - 抓调压过程 LDO_VCORE_L 波形
- 风险等级：high

## L-20260626-150203 - 大小 BG 切换影响输出电压

- 页面：automation/pmu_test
- 类型：参数经验
- 现象：
  - 2720/2008H normal 与 sleep 同一 Vbit 输出不一致，受大小 BG 切换影响
  - 空芯片 normal 下测静态电流需调低 lp_bias
- 原因：
  - normal/sleep 使用不同 BG，偏置不同
- 处理办法：
  - LP mode 调低 lp_bias 电流；dsleep 下 reg_lp_bias_sel_ldo_dsleep[6:1]=0x1，normal 默认 0x1F
- 验证方式：
  - 对比 normal/sleep 输出与静态电流
- 风险等级：medium

## L-20260626-150204 - BUCK 电压 ramp 切换过冲/掉坑

- 页面：automation/pmu_test
- 类型：坑点
- 现象：
  - 1806P BUCK_VCORE/VEXT 在 ramp_en=1、ramp_step=1 调压时，过冲稳定复现、掉坑概率复现
- 原因：
  - ramp 切换瞬态
- 处理办法：
  - 记录过冲/掉坑幅度，必要时调整 ramp_step；掉坑为概率性，需多次复现确认
- 验证方式：
  - 0.4V↔0.95V / 0.45V↔0.9V 双向 ramp 抓波形
- 风险等级：medium

## L-20260626-150205 - 快速关机显著降低掉电时间

- 页面：automation/pmu_test
- 类型：仪器行为
- 现象：
  - 快速关机 + soft poweroff 相比纯 soft poweroff 掉电时间大幅降低（1307PH 7s → 8ms）
- 原因：
  - 快速关机逻辑主动放电
- 处理办法：
  - 关机波形测试需分别记录 soft poweroff 与 快速关机+soft poweroff 两种
- 验证方式：
  - 抓 VBAT/各路掉电波形
- 风险等级：low

## L-20260626-150206 - 开关机撞沿导致无法关机

- 页面：automation/pmu_test
- 类型：坑点
- 现象：
  - AC_ON 给 50Hz(0~5V) 方波同时反复写 soft_power_off，出现无法关机（同 3601P 已知问题）
- 原因：
  - 撞沿竞争
- 处理办法：
  - 依赖软件 WDT 重启；测试需覆盖撞沿场景
- 验证方式：
  - 方波 + 反复 soft_power_off 压测
- 风险等级：high

## L-20260626-150207 - 部分形态未出测试口

- 页面：automation/pmu_test
- 类型：坑点
- 现象：
  - 合封/手表封装常未引出单线通信口（1503P/1806P/1811）；08/08H 不支持 PATTERN 复位
- 原因：
  - 封装/形态裁剪
- 处理办法：
  - 测试前先确认该形态是否引出对应 PIN/能力，避免误判 fail
- 验证方式：
  - 对照 datasheet / PIN 表
- 风险等级：low

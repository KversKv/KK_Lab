# PMU 整套常规测试 - 总记忆（memory）

> 伞目录：automation/pmu_test（见 [../../_shared/conventions.md §2.1](../../_shared/conventions.md#21-伞目录键umbrella)）
> 承载 PMU 常规测试跨页面、跨芯片的长期背景与稳定约定。
> 数据来源：docs/user/pmu_test_reports/ 下 7 份历史报告。
> 条目格式见 [../../_shared/conventions.md §5.1](../../_shared/conventions.md#51-memorymd)

## M-20260626-150001 - PMU 常规测试覆盖芯片与形态

- 页面：automation/pmu_test
- 来源：ai_assistant
- 稳定性：stable
- 摘要：记录历史 PMU 常规测试覆盖的芯片清单与各自形态约束
- 内容：
  - BES1307PH：SOC PMU 模块，SIMO（BUCK_VCORE/BUCK_VHPPA 单电感双输出），仅一个 VMIC，DCDC 无 ULP mode
  - BES1503P verB：单独 PMU，提供 0.6V 与 1.8V 两版，A 版 LDO_VCORE_L 有过冲/掉坑
  - BES1806P B版：单独 PMU，功能较完整，含 LPO/外部32K/Load Switch/掉坑测试
  - BES2720YP(1607+1813)：合封，受大小 BG 切换影响明显，1607 新增 Vcore_l
  - BES1811：功能最完善，含 Charger/Fuel Gauge/DVFS/PMU Interface/EFUSE
  - BES2008H：VBAT/Vsys 严禁超 3.3V，08/08H 不支持 PATTERN 复位，唤醒固定 PWM
  - BES2800YP-YA(1810)：xlsx 形态，测试项分组 T1~T32 + 高低温 + 问题点
- 适用条件：
  - 新芯片 PMU 常规测试套用通用测试项前，先核对其形态特殊约束
- 关联项：
  - test_items: T-20260626-150101 起的通用测试项
  - lessons: L-20260626-150201 起的跨芯片经验

## M-20260626-150002 - PMU 通用测试关键参数基线

- 页面：automation/pmu_test
- 来源：ai_assistant
- 稳定性：stable
- 摘要：跨芯片关键参数实测基线，供异常对照
- 内容：
  - PWRON/RST 耐压：1307PH 2.5V / 1503P 2.75V / 1811 5V
  - VBAT 耐压：1307PH 5V / 1503P 5.5V / 1811 5V；VCHG_R 5V；CHG_IN 16V(1811)
  - reset_chip 阻抗：1806P/1811 约 500k~1M，与 bd_option 无关
  - power_on 下拉：1307PH 5M / 1806P 5M(bd_option=0) / 1811 7.5M(bd_option=0)
  - BUCK 死区时间：1307PH dt0=8.913ns/dt1=9.256ns；1503P dt0=7.3ns/dt1=8.7ns
  - BUCK 频率：1503P 固定 1.715M = 24M/2/(5+2)
  - LPO 频率范围：1806P 35.2k~96.6kHz；1811 20.82k~75.67kHz
  - GPADC 判定：误差 ≤ ±10mV 为 pass（timer=2000 counts）
  - RST 时序：1307PH 高 9.911ms/恢复 14.345ms；2720 生效后 8.86ms 复位
- 适用条件：
  - 实测值偏离基线较大时优先怀疑器件/配置差异
- 关联项：
  - test_items: T-20260626-150101

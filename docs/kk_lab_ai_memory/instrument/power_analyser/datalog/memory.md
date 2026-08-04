# N6705C Datalog - 页面长期记忆

> 页面：datalog
> 记录页面长期背景、稳定约定、参数含义、常见上下文。
> 条目格式见 [../../../_shared/conventions.md §5.1](../../../_shared/conventions.md#51-memorymd)
> 默认为空，由人工确认后追加或整理。新条目按模板追加在下方。

<!-- 模板：

## M-YYYYMMDD-HHMMSS - 标题

- 页面：datalog
- 来源：ai_assistant / manual
- 稳定性：stable / tentative
- 摘要：一句话说明这条记忆解决什么问题
- 内容：
  - ...
- 适用条件：
  - ...
- 关联项：
  - lessons: L-...
  - test_items: T-...
-->

## M-20260804-100000 - BES RF SOC 电压域划分与供电对象

- 页面：datalog
- 来源：manual
- 稳定性：stable
- 摘要：给出本项目默认被测对象（BES RF SOC）的电压域划分与各域供电对象，供波形通道归因时定性参考
- 内容：
  - 本项目波形分析优先按 BES 芯片场景理解，通常为 RF SOC（BT / BLE / WIFI）
  - SOC 按电压域分开供电，主要包括 Vcore、Vana、Vhppa 三域
  - Vcore：数字电路供电，如 MCU、Interface 等数字逻辑
  - Vana：RF RX / RF TX 前端电路供电，同时供时钟体系（XTAL、PLL、VCO）
  - Vhppa：Codec、Memory、RF PA 供电
- 适用条件：
  - Datalog 通道名含 VCORE / VANA / VHPPA（含 BUCK_VCORE、BUCK_VHPPA 等派生名）时，按上述归属推断电流变化的功能来源, 要根据实际的电流波形或者用户指定来确认, 而不是随意推断;
  - 仅作定性归因参考；所有电流 / 电压 / 时间读数仍必须取自本轮 [波形数据摘要]，禁止据此臆造或估算数值

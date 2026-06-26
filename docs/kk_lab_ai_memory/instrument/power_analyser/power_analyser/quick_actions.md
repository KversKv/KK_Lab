# N6705C 电源分析仪 - 快捷指令

> 页面：power_analyser
> 模板格式见 [../../../_shared/conventions.md §5.5](../../../_shared/conventions.md#55-quick_actionsmd)
> 以下条目从 `core/ai/profiles.py` 中 `AI_PROFILES["power_analyser"].quick_actions` 迁移而来。

## QA-20260625-001 - 查询当前各通道电压电流

- 页面：power_analyser
- 来源：profile_migration
- 状态：active
- 模板：查询当前各通道电压电流
- 占位符：无
- 适用条件：
  - 当前页面已连接 N6705C
- 执行预期：
  - AI 通过 query_instrument 发送 MEAS:CURR? (@n) / MEAS:VOLT? (@n) 只读查询并汇总

## QA-20260625-002 - 把通道输出电压设到指定值

- 页面：power_analyser
- 来源：profile_migration
- 状态：active
- 模板：把通道 {ch} 输出电压设到 {v}V
- 占位符：
  - ch: 通道号，例如 1 / 2 / 3 / 4
  - v: 电压值，单位 V
- 适用条件：
  - 当前页面已连接 N6705C
- 执行预期：
  - AI 填充参数后调用 set_instrument_voltage(session_id, channel, voltage)，执行前弹确认框

## QA-20260625-003 - 打开通道输出

- 页面：power_analyser
- 来源：profile_migration
- 状态：active
- 模板：打开通道 {ch} 的输出
- 占位符：
  - ch: 通道号，例如 1 / 2 / 3 / 4
- 适用条件：
  - 当前页面已连接 N6705C
- 执行预期：
  - AI 调用 set_instrument_output(session_id, channel, True)，执行前弹确认框

## QA-20260625-004 - 关闭通道输出

- 页面：power_analyser
- 来源：profile_migration
- 状态：active
- 模板：关闭通道 {ch} 的输出
- 占位符：
  - ch: 通道号，例如 1 / 2 / 3 / 4
- 适用条件：
  - 当前页面已连接 N6705C
- 执行预期：
  - AI 调用 set_instrument_output(session_id, channel, False)，执行前弹确认框

## QA-20260625-005 - 解读最近的功率测量曲线

- 页面：power_analyser
- 来源：profile_migration
- 状态：active
- 模板：解读最近的功率测量曲线
- 占位符：无
- 适用条件：
  - 当前有功率测量数据或波形摘要
- 执行预期：
  - AI 依据真实数据解读，禁止臆造读数

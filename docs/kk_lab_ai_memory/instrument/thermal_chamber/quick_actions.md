# 温箱 - 快捷指令

> 页面：thermal_chamber
> 模板格式见 [../_shared/conventions.md §5.5](../../_shared/conventions.md#55-quick_actionsmd)
> 以下条目从 `core/ai/profiles.py` 中 `AI_PROFILES["thermal_chamber"].quick_actions` 迁移而来。

## QA-20260625-001 - 判断当前温度是否已稳定

- 页面：thermal_chamber
- 来源：profile_migration
- 状态：active
- 模板：判断当前温度是否已稳定
- 占位符：无
- 适用条件：
  - 当前已连接 VT6002 温箱并有温度读数
- 执行预期：
  - AI 依据真实温度读数判断稳定性，禁止臆造数值

## QA-20260625-002 - 建议合适的温度梯度与保温时间

- 页面：thermal_chamber
- 来源：profile_migration
- 状态：active
- 模板：建议合适的温度梯度与保温时间
- 占位符：无
- 适用条件：
  - 用户准备配置温控流程
- 执行预期：
  - AI 结合待测器件特性给出温度梯度与保温时间建议

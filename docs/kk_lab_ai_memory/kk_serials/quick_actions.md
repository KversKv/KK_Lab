# 串口工具 - 快捷指令

> 页面：kk_serials
> 模板格式见 [../_shared/conventions.md §5.5](../_shared/conventions.md#55-quick_actionsmd)
> 以下条目从 `core/ai/profiles.py` 中 `AI_PROFILES["kk_serials"].quick_actions` 迁移而来。

## QA-20260625-001 - 分析最近串口接收的异常

- 页面：kk_serials
- 来源：profile_migration
- 状态：active
- 模板：分析最近串口接收的异常
- 占位符：无
- 适用条件：
  - 当前活动串口会话有接收数据
- 执行预期：
  - AI 读取最近串口接收日志，定位异常/超时/复位/协议错误并引用具体日志行

## QA-20260625-002 - 解释这段串口日志的协议含义

- 页面：kk_serials
- 来源：profile_migration
- 状态：active
- 模板：解释这段串口日志的协议含义
- 占位符：无
- 适用条件：
  - 上下文中有选中的串口日志或最近接收日志
- 执行预期：
  - AI 结合协议规则解释日志字段与交互流程

## QA-20260625-003 - 排查串口超时/无响应的可能原因

- 页面：kk_serials
- 来源：profile_migration
- 状态：active
- 模板：排查串口超时/无响应的可能原因
- 占位符：无
- 适用条件：
  - 串口出现超时或无响应
- 执行预期：
  - AI 给出波特率/接线/电源/对端固件等排查方向

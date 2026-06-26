# Orchestrator - 快捷指令

> 页面：orchestrator
> 模板格式见 [../_shared/conventions.md §5.5](../../_shared/conventions.md#55-quick_actionsmd)
> 以下条目从 `core/ai/profiles.py` 中 `AI_PROFILES["orchestrator"].quick_actions` 迁移而来。

## QA-20260625-001 - 生成一个简单的测试序列草案

- 页面：orchestrator
- 来源：profile_migration
- 状态：active
- 模板：生成一个简单的测试序列草案
- 占位符：无
- 适用条件：
  - 当前在 Orchestrator 页面
- 执行预期：
  - AI 生成符合 core/orchestrator 节点 schema 的序列草案，经预览与本地校验后才能应用

## QA-20260625-002 - 解释可用的节点类型

- 页面：orchestrator
- 来源：profile_migration
- 状态：active
- 模板：解释可用的节点类型
- 占位符：无
- 适用条件：
  - 用户想了解 Orchestrator 支持的节点
- 执行预期：
  - AI 列出可用节点类型及其字段含义

## QA-20260625-003 - 检查当前序列的潜在问题

- 页面：orchestrator
- 来源：profile_migration
- 状态：active
- 模板：检查当前序列的潜在问题
- 占位符：无
- 适用条件：
  - 当前画布上已有测试序列
- 执行预期：
  - AI 只读检查序列配置，指出潜在问题与改进建议

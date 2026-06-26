# 示波器 - 快捷指令

> 页面：oscilloscope
> 模板格式见 [../_shared/conventions.md §5.5](../../_shared/conventions.md#55-quick_actionsmd)
> 以下条目从 `core/ai/profiles.py` 中 `AI_PROFILES["oscilloscope"].quick_actions` 迁移而来。

## QA-20260625-001 - 解读当前波形测量结果

- 页面：oscilloscope
- 来源：profile_migration
- 状态：active
- 模板：解读当前波形测量结果
- 占位符：无
- 适用条件：
  - 当前有示波器波形测量数据
- 执行预期：
  - AI 依据真实测量结果解读，禁止臆造读数

## QA-20260625-002 - 建议合适的触发与时基设置

- 页面：oscilloscope
- 来源：profile_migration
- 状态：active
- 模板：建议合适的触发与时基设置
- 占位符：无
- 适用条件：
  - 用户准备配置示波器采集
- 执行预期：
  - AI 结合待测信号特征给出触发与时基建议

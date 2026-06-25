# ADR 004 - AI Assist 受控动作系统（Action Registry / 权限 / 确认 / 审计）

- **状态**：Accepted
- **日期**：2026-06-17
- **范围**：`core/ai/actions/`（新增整层）、`core/ai/ai_service.py`、`core/ai/newapi_client.py`、`ui/ai/action_confirm_dialog.py`（新增）、`ui/ai/ai_assist_panel.py`、`ui/main_window.py`
- **关联**：[AIAssist_Architecture.md §17](../feature_requests/AIAssist/AIAssist_Architecture.md)、[AIAssist_ImplementationPlan.md 阶段 4](../feature_requests/AIAssist/AIAssist_ImplementationPlan.md)

---

## 背景

阶段 4 要让 AI 从「只读问答 + 草案预览」升级为「可执行受控动作」，覆盖查询 / UI 跳转 / 串口 / 仪器 / 测试。核心约束：AI 不得执行任意代码，只能调已注册动作；高风险动作必须人工确认；仪器一律经 `InstrumentManager`，AI 无法绕过 `instruments/`；所有动作（含拒绝 / 取消）写审计。

## 决策

1. **动作层分层**：新增 `core/ai/actions/`，链路为 `Registry → JSON Schema 校验 → PermissionChecker → 必要时 ActionConfirmDialog → Dispatcher 路由 handler → AuditLog`。该层不依赖 QtWidgets；handler 通过 `ActionDeps` 注入的 getter/callback 间接操作 UI / 仪器，保持分层铁律（`core` 不反向依赖 `ui`）。

2. **风险四级**：`low`（直接执行 + 审计）/ `medium`（执行 + 审计）/ `high`（必须弹确认）/ `critical`（默认禁 AI 直接执行）。`PermissionChecker(require_confirm_high=True, allow_critical=False)`。

3. **critical 双保险**：`set_instrument_output` 标记 critical，既被 `PermissionChecker` 拦截（`allow_critical=False`），instrument handler 内部再兜底返回禁止，防止策略被误改后泄漏。

4. **参数校验复用**：复用 `response_parser.validate_against_schema` 做 JSON Schema 子集校验，不引入 `jsonschema` 依赖（遵守打包体积铁律）。

5. **多轮 tool-calling**：`AIService` 注入 registry/dispatcher 后进入 agent 模式，最多 `_MAX_TOOL_ROUNDS=5` 轮；执行结果以 `role=tool` 消息回灌续跑。用 `QTimer.singleShot(0, ...)` 调度下一轮，避免与正在 quit 的旧 QThread 竞态。

6. **确认对话框线程安全**：worker.finished 为 queued connection 到主线程 AIService，`_on_finished → dispatch → confirm_callback`（模态对话框）全程在主线程；对话框 `parent=AI 面板`，取消设为默认按钮（autoDefault/default）以防误触高风险动作。

7. **传输层**：`newapi_client.chat()` 增加原生 `tools`/`tool_choice`，第一版走网关原生 function calling（返回 `tool_calls`）。

## 已注册动作（16）

| 类别 | 动作 | 风险 |
|---|---|---|
| 查询 | get_current_page / get_serial_status / get_recent_serial_logs / get_recent_app_logs / get_instrument_status / get_test_sequence_status | low |
| UI | open_page / toggle_ai_panel | low |
| 串口 | clear_serial_log | low |
| 串口 | send_serial_text | high（确认） |
| 仪器 | query_instrument | low |
| 仪器 | disconnect_instrument | medium |
| 仪器 | set_instrument_output | critical（默认禁） |
| 测试 | start_test_sequence / pause_test_sequence | high（确认） |
| 测试 | stop_test_sequence | high |

## 影响

- `user_data/ai/audit.log` 新增（JSONL，UTF-8，含拒绝 / 取消）。
- `core/ai`、`ui/ai` MODULE_VERSION 升至 `0.3.0`，新增 `core/ai/actions` MODULE_VERSION `0.1.0`。
- spec / DIRECTORY_STRUCTURE 已同步新增模块；无新增第三方依赖。

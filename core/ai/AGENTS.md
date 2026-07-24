# core/ai/ — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../AGENTS.md) 与 [core/AGENTS.md](../AGENTS.md)。仅存放 AI 子系统局部知识。

## 加载指针（AI 按需拉取）

- **Action Registry / 权限 / 审计设计** → @see ADR [004-ai-action-registry](../../docs/ai/decisions/004-ai-action-registry.md)
- **AI Assist 顶栏方案** → @see ADR [003-ai-assist-titlebar](../../docs/ai/decisions/003-ai-assist-titlebar.md)
- **跨模块坑** → @see [docs/ai/03_GOTCHAS.md](../../docs/ai/03_GOTCHAS.md)
- **功能需求原始文档** → @see [docs/ai/feature_requests/AIAssist/](../../docs/ai/feature_requests/AIAssist/)

## 本模块职责与边界

- **职责**：AI 对话、日志 / 波形分析、草案生成、受控动作执行、经验沉淀。
- **上游**：`ui/ai/`（面板、确认框、预览对话框）。
- **下游**：`core/instruments/`（InstrumentManager）、`instruments/factory.py`、`chips/`、`user_data/ai/`。
- **铁律**：`core/ai/` **禁止** import `PySide6.QtWidgets`；动作 handler 通过 `ActionDeps` 注入回调间接操作 UI / 仪器，保持 `core` 不反向依赖 `ui`。

## 接口契约（对外不可破坏）

- `AIService` 信号：`response_started / response_delta / response_finished / analysis_ready / draft_ready / action_requested / action_result`。
- 动作链路固定：`Registry → JSON Schema 校验 → PermissionChecker → 必要时 ActionConfirmDialog → Dispatcher → AuditLog`。
- 风险四级：`low` / `medium` / `high`（确认） / `critical`（默认禁）。
- 本机可写 AI 配置一律走 `get_user_data_dir()` 下的 `.local` 文件，禁止写 `resources/`。

## 局部约定

- **传输层**：`newapi_client.py` 走内网 New API 网关；`httpx` 必须 `trust_env=False` 绕系统代理；`max_tokens` ≥ 1024（GLM 为推理模型）。
- **草案仅草案**：生成 → 预览 → 本地校验 → 确认 → apply；`script` 草案 error 禁 apply、warning 二次确认。
- **流式仅 chat 模式**：`agent / analysis / draft` 仍走非流式。
- **模型选择优先级**：`set_model_override` > Profile > 默认。
- **SerialSessionManager 是每页面实例**，非全局单例；解析当前活动页的 `_sc_session_manager`。
- **历史污染防控**：凡"声称已执行控制类动作"的轮次必须强制真 `tool_call`，禁止文字假装完成（见 §26）。

## 局部坑点

> 详细背景见 [docs/ai/03_GOTCHAS.md](../../docs/ai/03_GOTCHAS.md)。

- **§26 上下文自我污染**：AI 首轮真调工具后编造"已弹确认框"叙述入 history 回灌，后续轮照抄不发 `tool_call`。修复靠 `_looks_like_fake_execution` + `_FORCE_TOOL_NUDGE` + `_agent_forced_retry`，且仅 `_agent_rounds == 0` 触发。
- **§26 强制重试闪退**：worker `finished` 槽链里用 `singleShot(0)` 再起新 worker，会与首轮 QThread `finished→deleteLater` 清理竞态 → 无声闪退（faulthandler 为空）。必须用 `singleShot(≥50ms)`。
- **§27 AI 经验写盘**：`resources/` 打包后只读；纠偏片段 / 快捷指令 / 项目规则写 `user_data/ai/*.local.json` / `.local.md`，加载侧按 `id` / `page_key` 合并，本机优先。
- **波形摘要时效**：`prompt_manager.build_messages` 的 `waveform_context` 放在**本轮 user 消息开头**并附时效声明，防止模型锚定历史 Marker 旧值。

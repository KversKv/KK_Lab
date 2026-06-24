"""AIService：UI 与 New API 之间的桥（QObject + QThread worker）。

职责：
  - 持有 AISettings / NewAPIClient / PromptManager / 对话历史；
  - 把一次 send() 放到后台线程执行，不阻塞 UI；
  - 通过信号回报结果 / 错误 / 状态；支持取消；
  - 暴露 set_page_context() 供页面切换时切换 Profile；
  - 暴露 test_connection() 与 analyze_recent_logs()。

线程模型：每次请求新建一个 _ChatWorker(QObject) + QThread，请求完成后线程退出回收。
"""
from __future__ import annotations

import json

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from core.ai import context_budget
from core.ai.config import AISettings
from core.ai.context_builder import ContextBuilder, ContextOptions
from core.ai.conversation_store import (
    clear_history as _clear_persisted_history,
    load_history as _load_persisted_history,
    load_summary as _load_persisted_summary,
    save_history as _save_persisted_history,
    save_summary as _save_persisted_summary,
)
from core.ai.draft_registry import DraftRegistry
from core.ai.log_ring import get_log_ring
from core.ai.newapi_client import AIClientError, ChatResult, NewAPIClient
from core.ai.nudges import force_tool_nudge
from core.ai.profiles import get_profile
from core.ai.prompt_manager import BudgetConfig, PromptManager, mask_sensitive
from core.ai.providers.log_provider import LogContextProvider
from core.ai.providers.page_provider import PageContextProvider
from core.ai.providers.sequence_provider import SequenceContextProvider
from core.ai.providers.serial_provider import SerialContextProvider
from core.ai.response_parser import (
    KIND_LOG_ANALYSIS,
    parse,
    parse_expected,
)
from core.ai.schemas import (
    CONFIG_DRAFT,
    SCRIPT_DRAFT,
    SessionStats,
    TurnUsage,
)
from core.ai.serial_rx_cache import SerialRxCache
from log_config import get_logger

logger = get_logger(__name__)


class _ChatWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self, client: NewAPIClient, model: str, messages, temperature, max_tokens,
        tools=None,
    ):
        super().__init__()
        self._client = client
        self._model = model
        self._messages = messages
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._tools = tools
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            result = self._client.chat(
                model=self._model,
                messages=self._messages,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                tools=self._tools,
                cancel_check=lambda: self._cancelled,
            )
        except AIClientError as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - 兜底转用户可读错误
            logger.error("AI worker 未预期异常", exc_info=True)
            self.failed.emit(f"未预期错误：{exc}")
            return
        self.finished.emit(result)


class _StreamWorker(QObject):
    """流式 chat worker：逐块经 delta 信号回报增量正文，结束发 finished。"""

    delta = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self, client: NewAPIClient, model, messages, temperature, max_tokens, tools=None
    ):
        super().__init__()
        self._client = client
        self._model = model
        self._messages = messages
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._tools = tools
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            result = self._client.chat_stream(
                model=self._model,
                messages=self._messages,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                tools=self._tools,
                on_delta=lambda chunk: self.delta.emit(chunk),
                cancel_check=lambda: self._cancelled,
            )
        except AIClientError as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - 兜底转用户可读错误
            logger.error("AI 流式 worker 未预期异常", exc_info=True)
            self.failed.emit(f"未预期错误：{exc}")
            return
        self.finished.emit(result)


class _SummaryWorker(QObject):
    """前情提要压缩 worker（Phase 6）：把旧历史压成短摘要，失败发 failed 由调用方回退。"""

    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, client: NewAPIClient, model: str, messages, max_tokens: int):
        super().__init__()
        self._client = client
        self._model = model
        self._messages = messages
        self._max_tokens = max_tokens
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            result = self._client.chat(
                model=self._model,
                messages=self._messages,
                temperature=0.2,
                max_tokens=self._max_tokens,
                cancel_check=lambda: self._cancelled,
            )
        except AIClientError as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - 兜底转可读错误
            logger.error("AI 摘要 worker 未预期异常", exc_info=True)
            self.failed.emit(f"未预期错误：{exc}")
            return
        self.finished.emit((result.content or "").strip())


_SUMMARY_INSTRUCTION = (
    "你是对话压缩助手。请把下面这段实验室仪器控制对话压缩成简洁的「前情提要」，"
    "保留：用户目标、已确认的关键参数（通道/电压/电流/序列名等）、已执行过的操作与结论、"
    "尚未完成的事项。要求：用简体中文、要点式、不超过 200 字，不要复述客套话，不要编造。"
)

_DEFAULT_SESSION = "_default"

_MODE_CHAT = "chat"
_MODE_ANALYSIS = "analysis"
_MODE_CONFIG_DRAFT = "config_draft"
_MODE_SCRIPT_DRAFT = "script_draft"
_MODE_AGENT = "agent"

_MAX_TOOL_ROUNDS = 5

_FORCE_RETRY_DELAY_MS = 50

_FORCE_TOOL_NUDGE_FALLBACK = (
    "[系统强制提示] 上一条回复没有调用任何工具，却用文字声称已执行或"
    "“系统已弹出确认框/确认后即执行”等。这是被禁止的：你不能假装已执行，"
    "也不能只给出命令文本。若用户的请求需要改变仪器/串口/测试运行状态"
    "（如开关输出、设置电压电流、运行/停止序列等），你必须立即调用对应的"
    "受控动作（工具）来执行；高风险动作系统会自动弹确认框，确认后由程序安全下发。"
    "请现在直接发起正确的工具调用；若确实缺少必要参数（如 session_id、通道号），"
    "先调用查询类动作补全，或简短询问用户，但不要再用文字假装已完成。"
)


def _force_tool_nudge_text() -> str:
    """取 force_tool 纠偏片段；片段库缺失时回退内置常量。"""
    return force_tool_nudge() or _FORCE_TOOL_NUDGE_FALLBACK


class AIService(QObject):
    response_ready = Signal(str)
    response_started = Signal()
    response_delta = Signal(str)
    response_finished = Signal(str)
    analysis_ready = Signal(object)
    draft_ready = Signal(object)
    error_occurred = Signal(str)
    busy_changed = Signal(bool)
    connection_tested = Signal(bool, str)
    action_requested = Signal(object)
    action_result = Signal(object)
    usage_updated = Signal(object, object)
    trace_recorded = Signal(str)

    def __init__(self, settings: AISettings, page_key_getter=None, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._page_key: str | None = None
        self._session_key: str = _DEFAULT_SESSION
        self._history: list[dict[str, str]] = _load_persisted_history(self._session_key)
        self._summary: str = _load_persisted_summary(self._session_key)
        self._summary_thread: QThread | None = None
        self._summary_worker: _SummaryWorker | None = None
        self._telemetry_uploader = None
        self._busy = False
        self._pending_mode = _MODE_CHAT
        self._model_override: str | None = None
        self._stream_buffer = ""
        self._stream_started = False
        self._answer_was_streamed = False
        self._session_stats = SessionStats()
        self._pending_trace: dict | None = None

        self._prompt_manager = PromptManager(
            enable_log_masking=settings.enable_log_masking
        )
        if page_key_getter is not None:
            self._prompt_manager.add_provider(PageContextProvider(page_key_getter))
        self._sequence_provider = SequenceContextProvider()
        self._prompt_manager.add_provider(self._sequence_provider)

        self._rx_cache = SerialRxCache()
        self._log_provider = LogContextProvider(
            max_app_lines=settings.max_recent_log_lines,
        )
        self._serial_provider = SerialContextProvider(self._rx_cache)
        self._context_builder = ContextBuilder(
            log_provider=self._log_provider,
            serial_provider=self._serial_provider,
        )

        self._thread: QThread | None = None
        self._worker: _ChatWorker | None = None
        self._orphans: list[tuple[QThread, QObject]] = []

        self._registry = None
        self._dispatcher = None
        self._draft_registry = DraftRegistry()
        self._agent_messages: list[dict] = []
        self._agent_rounds = 0
        self._agent_model = ""
        self._agent_temperature = 0.2
        self._agent_max_tokens = 2048
        self._agent_forced_retry = False

    def set_action_system(self, registry, dispatcher) -> None:
        """UI 注入受控动作系统（ActionRegistry + ActionDispatcher）。

        注入后 send() 默认带 tools，进入 agent 模式（多轮 tool-calling）。
        """
        self._registry = registry
        self._dispatcher = dispatcher

    @property
    def dispatcher(self):
        """已注入的 ActionDispatcher（未注入时为 None）。"""
        return self._dispatcher

    @property
    def draft_registry(self) -> DraftRegistry:
        """草案注册表：generate_draft 产出的草案按 draft_id 登记，供 apply 动作落地。"""
        return self._draft_registry

    @property
    def rx_cache(self) -> SerialRxCache:
        return self._rx_cache

    def set_execution_logs_getter(self, getter) -> None:
        """UI 注入：返回当前页执行日志 list[str] 的回调。"""
        self._log_provider = LogContextProvider(
            max_app_lines=self._settings.max_recent_log_lines,
            execution_logs_getter=getter,
        )
        self._context_builder = ContextBuilder(
            log_provider=self._log_provider,
            serial_provider=self._serial_provider,
        )

    def set_sequence_data_getter(self, getter) -> None:
        """UI 注入：返回当前 Custom Test 画布序列 v2 dict 的回调（F5.1）。

        传入 None 表示当前无序列源（非 Custom Test 页面）。
        """
        self._sequence_provider.set_getter(getter)

    def set_serial_status_getter(self, getter) -> None:
        """UI 注入：返回当前活动串口状态 dict 的回调。"""
        self._serial_provider = SerialContextProvider(self._rx_cache, getter)
        self._context_builder = ContextBuilder(
            log_provider=self._log_provider,
            serial_provider=self._serial_provider,
        )

    def feed_serial_rx(self, session_id: str, data: bytes) -> None:
        """UI 把 SerialSessionManager.session_data_received 喂进 RX 缓存。"""
        self._rx_cache.feed(session_id, data)

    @property
    def settings(self) -> AISettings:
        return self._settings

    @property
    def is_busy(self) -> bool:
        return self._busy

    def set_page_context(self, page_key: str | None) -> None:
        if page_key == self._page_key:
            return
        if self._history:
            _save_persisted_history(self._history, self._session_key)
        self._page_key = page_key
        self._session_key = page_key or _DEFAULT_SESSION
        self._history = _load_persisted_history(self._session_key)
        self._summary = _load_persisted_summary(self._session_key)
        logger.debug("AI 上下文切换页面: %s（会话 %s）", page_key, self._session_key)

    def current_page_key(self) -> str | None:
        return self._page_key

    def current_session_key(self) -> str:
        return self._session_key

    def clear_history(self) -> None:
        self._history.clear()
        self._summary = ""
        _clear_persisted_history(self._session_key)
        self._session_stats.reset()
        self.usage_updated.emit(None, self._session_stats)

    @property
    def session_stats(self) -> SessionStats:
        return self._session_stats

    def _record_usage(self, result: ChatResult | None) -> None:
        if result is None:
            return
        turn = TurnUsage.from_result(result.usage, result.elapsed_ms)
        if turn.total_tokens == 0 and turn.completion_tokens == 0:
            return
        self._session_stats.add(turn)
        self.usage_updated.emit(turn, self._session_stats)

    def persisted_history(self) -> list[dict[str, str]]:
        """返回当前会话历史（user/assistant 正文），供 UI 启动时回放。"""
        return list(self._history)

    def available_models(self) -> list[str]:
        """可选模型清单（含默认模型，去重保序）。"""
        models = list(self._settings.available_models or [])
        default = self._settings.effective_model
        if default and default not in models:
            models.insert(0, default)
        seen = set()
        ordered = []
        for m in models:
            if m and m not in seen:
                seen.add(m)
                ordered.append(m)
        return ordered

    def current_model(self) -> str:
        """当前生效模型：手动覆盖 > 固定默认模型 > Profile > 设置默认。

        model_mode='fixed' 时固定使用设置里的默认模型（覆盖各页面 Profile）；
        'auto' 时按页面 Profile 选择，Profile 未指定才回退设置默认。
        """
        profile = get_profile(self._page_key)
        return self._resolve_model(
            profile.get("model", self._settings.effective_model)
        )

    def set_model_override(self, model: str | None) -> None:
        """手动切换模型（5.3）。传 None / 空串恢复按 Profile 自动选择。"""
        value = (model or "").strip()
        self._model_override = value or None
        logger.debug("AI 模型手动覆盖: %s", self._model_override)

    def _resolve_model(self, profile_model: str) -> str:
        """统一模型解析：手动覆盖 > 固定默认模型 > Profile 模型。"""
        if self._model_override:
            return self._model_override
        if self._settings.model_mode == "fixed" and self._settings.effective_model:
            return self._settings.effective_model
        return profile_model

    def _budget_for(self, model: str) -> BudgetConfig:
        """按当前实际模型构建 token 预算配置（窗口随模型而非全局固定）。"""
        window = self._settings.context_window_for(model)
        block_cap = self._settings.max_context_block_tokens
        usable = max(1, int(window) - int(self._settings.reserve_output_tokens))
        waveform_cap = max(block_cap, int(usable * 0.6))
        return BudgetConfig(
            window=window,
            reserve_output=self._settings.reserve_output_tokens,
            soft_budget_ratio=self._settings.soft_budget_ratio,
            max_context_block_tokens=block_cap,
            waveform_block_tokens=waveform_cap,
        )

    def _trim_agent_messages(self, model: str) -> None:
        """进入下一轮 agent 请求前，对 messages 跑一次预算检查并裁剪最旧历史。"""
        budget = self._budget_for(model)
        self._agent_messages = context_budget.fit_messages(
            self._agent_messages,
            window=budget.window,
            reserve_output=budget.reserve_output,
            soft_budget_ratio=budget.soft_budget_ratio,
        )

    def _make_client(self) -> NewAPIClient:
        return NewAPIClient(
            base_url=self._settings.effective_base_url,
            api_key=self._settings.effective_api_key,
            timeout_seconds=self._settings.timeout_seconds,
        )

    def _record_telemetry(self, event_type: str, payload: dict | None = None) -> None:
        """采集一条遥测事件（隐私开关关闭时由 telemetry.record 静默）。"""
        if not self._settings.telemetry_enabled:
            return
        try:
            from core.ai.telemetry import TelemetryEvent, record

            record(
                TelemetryEvent(
                    event_type=event_type,
                    page_key=self._page_key or "",
                    payload=payload or {},
                ),
                self._settings,
            )
        except Exception:  # noqa: BLE001 - 采集失败绝不影响主流程
            logger.error("采集遥测事件失败: %s", event_type, exc_info=True)

    def _record_trace(
        self,
        result: ChatResult | None,
        mode,
        *,
        error: str | None = None,
    ) -> None:
        """落一条完整对话 trace（隐私开关关闭时由 trace_store.record 静默）。

        trace 含本轮喂给模型的完整 messages 与原始输出，供 replay 重放对比；
        成功落盘后 emit trace_recorded(trace_id) 供 UI 绑定 👍/👎 回填 rating。
        """
        snapshot = self._pending_trace
        if not snapshot:
            return
        self._pending_trace = None
        try:
            from core.ai.trace_store import build_trace, record

            trace = build_trace(
                page_key=snapshot.get("page_key"),
                mode=str(mode or ""),
                model=str(snapshot.get("model") or ""),
                temperature=float(snapshot.get("temperature") or 0.0),
                max_tokens=int(snapshot.get("max_tokens") or 0),
                messages_in=snapshot.get("messages_in") or [],
                raw_output=(result.content if result else ""),
                reasoning=(result.reasoning if result else ""),
                tool_calls=(result.tool_calls if result else []),
                usage=(result.usage if result else None),
                latency_ms=(result.elapsed_ms if result else 0),
                error=error,
            )
            trace_id = record(trace, self._settings)
            if trace_id:
                self.trace_recorded.emit(trace_id)
        except Exception:  # noqa: BLE001 - trace 采集失败绝不影响主流程
            logger.error("落对话 trace 失败", exc_info=True)

    def rate_trace(self, trace_id: str, rating: str) -> None:
        """把 UI 反馈的 👍/👎 回填到对应 trace（便于后续筛差评转 eval）。"""
        if not trace_id:
            return
        try:
            from core.ai.trace_store import set_rating

            set_rating(trace_id, rating)
        except Exception:  # noqa: BLE001
            logger.error("回填 trace rating 失败", exc_info=True)

    def record_feedback(self, msg_id: str, rating: str, comment: str = "") -> None:
        """UI 👍/👎 反馈入口（§3.2 回答反馈事件）。"""
        self._record_telemetry(
            "feedback",
            {"msg_id": msg_id, "rating": rating, "comment": comment},
        )

    def start_telemetry(self) -> None:
        """按当前隐私开关启动后台遥测上报器（关闭则停止/不启动）。"""
        if not self._settings.telemetry_enabled:
            if self._telemetry_uploader is not None:
                self._telemetry_uploader.stop()
            return
        try:
            if self._telemetry_uploader is None:
                from core.ai.telemetry import TelemetryUploader

                self._telemetry_uploader = TelemetryUploader(self._settings, parent=self)
            self._telemetry_uploader.start()
        except Exception:  # noqa: BLE001 - 上报器启动失败不影响主流程
            logger.error("启动遥测上报器失败", exc_info=True)

    def _maybe_summarize(self) -> None:
        """一轮结束后检查历史是否逼近窗口，必要时后台压缩前情提要（Phase 6）。

        失败/未配置时不影响主流程：context_budget.fit_messages 仍按滑动窗口兜底。
        """
        if not self._settings.enable_history_summary:
            return
        if self._summary_thread is not None:
            return
        if len(self._history) < 4:
            return
        model = self._resolve_model(
            get_profile(self._page_key).get("model", self._settings.effective_model)
        )
        window = self._settings.context_window_for(model)
        if not context_budget.should_summarize(
            self._history,
            window=window,
            reserve_output=self._settings.reserve_output_tokens,
            trigger_ratio=self._settings.summary_trigger_ratio,
        ):
            return
        if not self._settings.is_configured():
            return

        keep_recent = 4
        old = self._history[:-keep_recent]
        if not old:
            return
        transcript_lines = []
        if self._summary:
            transcript_lines.append(f"[已有前情提要]\n{self._summary}")
        for item in old:
            role = "用户" if item.get("role") == "user" else "助手"
            transcript_lines.append(f"{role}：{item.get('content', '')}")
        transcript = "\n".join(transcript_lines)
        if self._prompt_manager._enable_masking:
            transcript = mask_sensitive(transcript)

        summary_model = self._settings.summary_model or model
        messages = [
            {"role": "system", "content": _SUMMARY_INSTRUCTION},
            {"role": "user", "content": transcript},
        ]
        try:
            client = self._make_client()
        except Exception:
            logger.error("创建摘要 client 失败", exc_info=True)
            return

        self._summary_old_count = len(old)
        self._summary_thread = QThread()
        self._summary_worker = _SummaryWorker(
            client, summary_model, messages, max_tokens=512
        )
        self._summary_worker.moveToThread(self._summary_thread)
        self._summary_thread.started.connect(self._summary_worker.run)
        self._summary_worker.finished.connect(self._on_summary_finished)
        self._summary_worker.failed.connect(self._on_summary_failed)
        self._summary_worker.finished.connect(self._summary_thread.quit)
        self._summary_worker.failed.connect(self._summary_thread.quit)
        self._summary_thread.finished.connect(self._cleanup_summary_thread)
        self._summary_thread.start()

    def _on_summary_finished(self, summary: str) -> None:
        summary = (summary or "").strip()
        if not summary:
            return
        old_count = getattr(self, "_summary_old_count", 0)
        if old_count <= 0 or old_count > len(self._history):
            return
        self._summary = summary
        self._history = self._history[old_count:]
        _save_persisted_summary(self._summary, self._session_key)
        _save_persisted_history(self._history, self._session_key)
        logger.info(
            "已压缩前情提要（会话 %s）：折叠 %d 条旧历史", self._session_key, old_count
        )
        self._record_telemetry(
            "summary",
            {
                "trigger_ratio": self._settings.summary_trigger_ratio,
                "summarized_turns": old_count,
            },
        )

    def _on_summary_failed(self, message: str) -> None:
        logger.warning("前情提要压缩失败，回退滑动窗口：%s", message)

    def _cleanup_summary_thread(self) -> None:
        if self._summary_worker is not None:
            self._summary_worker.deleteLater()
            self._summary_worker = None
        if self._summary_thread is not None:
            self._summary_thread.deleteLater()
            self._summary_thread = None

    def send(
        self,
        user_text: str,
        include_recent_logs: bool = False,
        extra_context: str = "",
        waveform_context: str = "",
    ) -> None:
        text = (user_text or "").strip()
        if not text:
            return
        if self._busy:
            self.error_occurred.emit("正在处理上一条请求，请稍候。")
            return
        if not self._settings.is_configured():
            self.error_occurred.emit("AI 未配置（缺少 base_url 或 API Key）。")
            return

        log_context = ""
        if include_recent_logs:
            log_context = self._recent_logs_text()

        profile = get_profile(self._page_key)
        model = self._resolve_model(profile.get("model", self._settings.effective_model))
        temperature = profile.get("temperature", 0.2)
        max_tokens = profile.get("max_tokens", 2048)

        messages = self._prompt_manager.build_messages(
            page_key=self._page_key,
            history=self._history,
            user_text=text,
            log_context=log_context,
            extra_context=extra_context,
            budget=self._budget_for(model),
            summary=self._summary,
            waveform_context=waveform_context,
        )
        self._pending_trace = {
            "page_key": self._page_key,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages_in": list(messages),
        }
        self._history.append({"role": "user", "content": text})

        tools = None
        if self._dispatcher is not None and self._registry is not None:
            tools = self._registry.to_tools()

        if tools:
            self._pending_mode = _MODE_AGENT
            self._agent_messages = list(messages)
            self._agent_rounds = 0
            self._agent_forced_retry = False
            self._agent_model = model
            self._agent_temperature = temperature
            self._agent_max_tokens = max_tokens
            self._start_agent_round(tools)
        elif self._settings.stream:
            self._pending_mode = _MODE_CHAT
            self._start_stream_worker(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            self._pending_mode = _MODE_CHAT
            self._start_worker(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

    def send_with_waveform(
        self, user_text: str, digest, extra_context: str = ""
    ) -> None:
        """带波形摘要发送（F1.5/F1.6）：把 WaveformDigest 文本化注入上下文。"""
        from core.ai.prompt_manager import format_waveform_digest

        context = format_waveform_digest(digest)
        self.send(user_text, extra_context=extra_context, waveform_context=context)

    def cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()

    def _start_worker(self, messages, model, temperature, max_tokens, tools=None) -> None:
        self._teardown_thread()
        self._set_busy(True)
        client = self._make_client()
        self._thread = QThread()
        self._worker = _ChatWorker(
            client, model, messages, temperature, max_tokens, tools=tools
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _start_stream_worker(
        self, messages, model, temperature, max_tokens, tools=None
    ) -> None:
        self._teardown_thread()
        self._set_busy(True)
        self._stream_buffer = ""
        self._stream_started = False
        client = self._make_client()
        self._thread = QThread()
        self._worker = _StreamWorker(
            client, model, messages, temperature, max_tokens, tools=tools
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.delta.connect(self._on_stream_delta)
        self._worker.finished.connect(self._on_stream_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _on_stream_delta(self, chunk: str) -> None:
        if not chunk:
            return
        if not self._stream_started:
            self._stream_started = True
            self.response_started.emit()
        self._stream_buffer += chunk
        self.response_delta.emit(chunk)

    def _on_stream_finished(self, result: ChatResult) -> None:
        content = (result.content if result else "") or self._stream_buffer
        tool_calls = result.tool_calls if result else []
        self._record_usage(result)

        if self._pending_mode == _MODE_AGENT:
            self._stream_buffer = ""
            self._on_agent_stream_finished(content, tool_calls, result)
            return

        self._pending_mode = _MODE_CHAT
        if not self._stream_started:
            self.response_ready.emit(content)
        else:
            self.response_finished.emit(content)
        self._history.append({"role": "assistant", "content": content})
        _save_persisted_history(self._history, self._session_key)
        self._stream_buffer = ""
        self._stream_started = False
        self._set_busy(False)
        self._record_telemetry("answer", {"mode": "chat_stream"})
        self._record_trace(result, "chat_stream")
        self._maybe_summarize()

    def _on_agent_stream_finished(self, content, tool_calls, result) -> None:
        """Agent 流式轮收尾：有 tool_calls 则结束流式气泡转工具执行；否则正文即最终答复。

        本轮是否已把正文流式渲染到气泡，记到 _answer_was_streamed，供
        _handle_agent_round 决定最终用 response_finished（收尾流式气泡）
        还是 response_ready（新建气泡）。若本轮有 tool_calls，正文气泡此处先收尾，
        后续工具轮/末轮再各自渲染。
        """
        streamed = self._stream_started
        if streamed and tool_calls:
            self.response_finished.emit(content)
            self._answer_was_streamed = False
        else:
            self._answer_was_streamed = streamed
        self._stream_started = False
        try:
            self._handle_agent_round(content, tool_calls)
        except Exception:
            logger.error("处理 agent 流式轮次失败", exc_info=True)
            self._abort_agent(content, "处理结果失败，已停止本次操作。")

    def _on_finished(self, result: ChatResult) -> None:
        content = result.content if result else ""
        tool_calls = result.tool_calls if result else []
        mode = self._pending_mode
        self._record_usage(result)

        if mode == _MODE_AGENT:
            try:
                self._handle_agent_round(content, tool_calls)
            except Exception:
                logger.error("处理 agent 轮次失败", exc_info=True)
                self._abort_agent(content, "处理结果失败，已停止本次操作。")
            return

        self._pending_mode = _MODE_CHAT
        self._history.append({"role": "assistant", "content": content})
        _save_persisted_history(self._history, self._session_key)

        if mode == _MODE_ANALYSIS:
            parsed = parse(content, tool_calls)
            if parsed.kind == KIND_LOG_ANALYSIS and parsed.payload is not None:
                self.analysis_ready.emit(parsed.payload)
            else:
                self.response_ready.emit(content or "（无分析结果）")
        elif mode == _MODE_CONFIG_DRAFT:
            parsed = parse_expected(content, CONFIG_DRAFT)
            self._register_draft(parsed)
            self.draft_ready.emit(parsed)
        elif mode == _MODE_SCRIPT_DRAFT:
            parsed = parse_expected(content, SCRIPT_DRAFT)
            self._register_draft(parsed)
            self.draft_ready.emit(parsed)
        else:
            self.response_ready.emit(content)
        self._set_busy(False)
        self._record_telemetry("answer", {"mode": mode})
        self._record_trace(result, mode)
        self._maybe_summarize()

    def _on_failed(self, message: str) -> None:
        self._pending_mode = _MODE_CHAT
        self._stream_buffer = ""
        self._stream_started = False
        self._answer_was_streamed = False
        if self._history and self._history[-1].get("role") == "user":
            self._history.pop()
        self.error_occurred.emit(message)
        self._set_busy(False)
        self._record_telemetry(
            "error",
            {"error_type": "chat_failed", "masked_message": (message or "")[:200]},
        )
        self._record_trace(None, _MODE_CHAT, error=(message or "")[:500])

    @staticmethod
    def _looks_like_fake_execution(content: str) -> bool:
        """判断模型是否“嘴上执行”：没调工具却声称已执行/已弹确认框。

        命中任一关键短语即认为是假执行叙述，触发一次强制工具重试。
        宁可漏判（保守）也不误伤普通问答。
        """
        if not content:
            return False
        markers = (
            "系统已弹出确认框",
            "确认后即执行",
            "确认后将执行",
            "确认后由程序",
            "请确认后执行",
            "已弹出确认",
            "已开启",
            "已关闭",
            "已设置",
            "已下发",
            "已执行",
            "已完成设置",
            "输出已",
        )
        return any(m in content for m in markers)

    def _handle_agent_round(self, content: str, tool_calls: list) -> None:
        """处理一轮 agent 结果：无 tool_calls 则结束；有则执行并回灌再起一轮。

        关键：执行 tool_calls 可能弹模态确认框（嵌套事件循环），必须延后到
        本槽函数返回、worker/QThread 完成清理之后再执行，否则嵌套事件循环会
        在 finished 信号仍在栈上时触发 _cleanup_thread.deleteLater() 销毁 worker，
        导致 C++ 对象在信号发射期间被删除而崩溃（窗口闪退）。
        """
        if not tool_calls:
            if (
                self._agent_rounds == 0
                and not self._agent_forced_retry
                and self._looks_like_fake_execution(content)
            ):
                logger.warning(
                    "Agent 未调用工具却声称已执行，强制回灌提示重试一轮: %s",
                    (content or "")[:80],
                )
                if self._answer_was_streamed:
                    self.response_finished.emit(content)
                    self._answer_was_streamed = False
                self._agent_forced_retry = True
                self._agent_messages.append(
                    {"role": "assistant", "content": content or ""}
                )
                self._agent_messages.append(
                    {"role": "user", "content": _force_tool_nudge_text()}
                )
                self._record_telemetry(
                    "nudge_hit",
                    {"nudge_id": "force_tool", "before": (content or "")[:120]},
                )
                QTimer.singleShot(_FORCE_RETRY_DELAY_MS, self._run_forced_retry)
                return
            self._pending_mode = _MODE_CHAT
            self._history.append({"role": "assistant", "content": content})
            _save_persisted_history(self._history, self._session_key)
            if self._answer_was_streamed:
                self.response_finished.emit(content)
                self._answer_was_streamed = False
            else:
                self.response_ready.emit(content)
            self._set_busy(False)
            self._record_trace(ChatResult(content=content or ""), _MODE_AGENT)
            self._maybe_summarize()
            return

        self._agent_messages.append(
            {"role": "assistant", "content": content or "", "tool_calls": tool_calls}
        )
        QTimer.singleShot(0, lambda: self._run_tool_calls(content, list(tool_calls)))

    def _abort_agent(self, content: str, reason: str) -> None:
        """Agent 循环异常/中断时的兜底收尾：落盘已产生历史、复位 busy、报错。

        无论 tool 执行、确认回调（嵌套事件循环）还是回灌请求出现任何异常，
        都必须经此路径恢复，杜绝"转圈卡死且重启无历史"。
        """
        self._pending_mode = _MODE_CHAT
        try:
            self._teardown_thread()
        except Exception:
            logger.error("Agent 中断收尾时清理线程失败", exc_info=True)
        fallback = (content or "").strip() or "处理过程中出现异常，已停止本次操作。"
        if not self._history or self._history[-1].get("content") != fallback:
            self._history.append({"role": "assistant", "content": fallback})
        _save_persisted_history(self._history, self._session_key)
        self.error_occurred.emit(reason)
        self.response_ready.emit(fallback)
        self._set_busy(False)

    def _run_tool_calls(self, content: str, tool_calls: list) -> None:
        """延后执行的 tool_calls 处理（已脱离 worker.finished 槽栈）。"""
        if self._pending_mode != _MODE_AGENT:
            self._set_busy(False)
            return

        try:
            self._teardown_thread()

            for call in tool_calls:
                self._execute_tool_call(call)
        except Exception:
            logger.error("执行 agent 工具调用失败", exc_info=True)
            self._abort_agent(content, "执行工具调用失败，已停止本次操作。")
            return

        self._agent_rounds += 1
        if self._agent_rounds >= _MAX_TOOL_ROUNDS:
            self._pending_mode = _MODE_CHAT
            self._history.append(
                {
                    "role": "assistant",
                    "content": content
                    or "已达到工具调用上限，已停止继续执行动作。",
                }
            )
            _save_persisted_history(self._history, self._session_key)
            self.response_ready.emit(
                content or "已达到工具调用上限，已停止继续执行动作。"
            )
            self._set_busy(False)
            return

        QTimer.singleShot(0, self._run_next_agent_round)

    def _execute_tool_call(self, call: dict) -> None:
        function = (call or {}).get("function") or {}
        name = function.get("name", "")
        call_id = call.get("id", "") or name
        raw_args = function.get("arguments") or "{}"
        try:
            arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            if not isinstance(arguments, dict):
                arguments = {}
        except (ValueError, TypeError):
            arguments = {}

        self.action_requested.emit({"name": name, "arguments": arguments})

        outcome = self._dispatcher.dispatch(name, arguments)
        self.action_result.emit(outcome)

        try:
            payload = json.dumps(
                outcome.to_tool_payload(), ensure_ascii=False, default=str
            )
        except (TypeError, ValueError):
            payload = json.dumps({"status": outcome.status, "message": outcome.message})

        payload = context_budget.clip_context_block(
            payload, self._settings.max_context_block_tokens
        )

        self._agent_messages.append(
            {
                "role": "tool",
                "tool_call_id": call_id,
                "name": name,
                "content": payload,
            }
        )

    def _run_forced_retry(self) -> None:
        if self._pending_mode != _MODE_AGENT:
            self._set_busy(False)
            return
        try:
            self._teardown_thread()
            self._run_next_agent_round()
        except Exception:
            logger.error("Agent 强制重试失败", exc_info=True)
            self._abort_agent("", "重试失败，已停止本次操作。")

    def _run_next_agent_round(self) -> None:
        if self._pending_mode != _MODE_AGENT:
            self._set_busy(False)
            return
        try:
            tools = self._registry.to_tools() if self._registry else None
            self._start_agent_round(tools)
        except Exception:
            logger.error("启动下一轮 agent 失败", exc_info=True)
            self._abort_agent("", "无法继续执行，已停止本次操作。")

    def _start_agent_round(self, tools) -> None:
        """启动一个 agent 轮：流式开启则走 _StreamWorker（tool-call 感知），否则非流式。

        流式 worker 在 finished 时返回聚合的 content + tool_calls，
        由 _on_stream_finished -> _on_agent_stream_finished 统一进入
        _handle_agent_round，与非流式路径行为一致。
        """
        self._trim_agent_messages(self._agent_model)
        self._answer_was_streamed = False
        if self._settings.stream:
            self._start_stream_worker(
                messages=self._agent_messages,
                model=self._agent_model,
                temperature=self._agent_temperature,
                max_tokens=self._agent_max_tokens,
                tools=tools,
            )
        else:
            self._start_worker(
                messages=self._agent_messages,
                model=self._agent_model,
                temperature=self._agent_temperature,
                max_tokens=self._agent_max_tokens,
                tools=tools,
            )

    def _teardown_thread(self) -> None:
        """启动新 worker 前，非阻塞地放手上一个 QThread。

        关键（修复主窗口卡死）：本方法运行在 UI 线程，禁止 thread.wait() 长阻塞。
        本地大模型高峰期单次请求可能数十秒，worker 卡在 httpx 读取上无法立刻退出，
        若在此 wait() 会冻结主窗口。改为：断开旧信号、置取消标志、调用 quit() 让其
        在自身事件循环空闲时退出，并把 (thread, worker) 转入孤儿表自管理回收，
        UI 线程立即返回。线程真正结束后 finished -> _reap_orphan 异步清理引用，
        既不丢引用（避免 C++ 对象提前析构崩溃）又不阻塞 UI。
        """
        thread = self._thread
        worker = self._worker
        self._thread = None
        self._worker = None
        if thread is None:
            return
        try:
            thread.finished.disconnect(self._cleanup_thread)
        except (RuntimeError, TypeError):
            pass
        if worker is not None:
            try:
                worker.cancel()
            except (RuntimeError, AttributeError):
                pass
            try:
                worker.finished.disconnect()
                worker.failed.disconnect()
            except (RuntimeError, TypeError):
                pass
        if thread.isRunning():
            self._orphans.append((thread, worker))
            thread.finished.connect(lambda t=thread: self._reap_orphan(t))
            thread.quit()
            return
        if worker is not None:
            worker.deleteLater()
        thread.deleteLater()

    def _reap_orphan(self, thread: QThread) -> None:
        """孤儿线程真正退出后异步回收（运行在 UI 线程的事件循环里）。"""
        for idx, (t, worker) in enumerate(list(self._orphans)):
            if t is thread:
                try:
                    self._orphans.pop(idx)
                except IndexError:
                    pass
                if worker is not None:
                    worker.deleteLater()
                t.deleteLater()
                break

    def _cleanup_thread(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None

    def _set_busy(self, value: bool) -> None:
        if value != self._busy:
            self._busy = value
            self.busy_changed.emit(value)

    def _recent_logs_text(self) -> str:
        ring = get_log_ring()
        if ring is None:
            return ""
        lines = ring.recent(self._settings.max_recent_log_lines)
        return "\n".join(lines)

    def analyze_recent_logs(self) -> None:
        """基础日志分析入口（兼容旧调用）：走结构化分析。"""
        self.analyze_logs()

    def analyze_logs(self, options: ContextOptions | None = None) -> None:
        """结构化日志分析：聚合软件/串口/执行日志上下文，请模型输出结构化结果。

        上下文经 ContextBuilder 脱敏 / 等级过滤 / 超限摘要截断；
        模型按 LOG_ANALYSIS_SCHEMA 输出 JSON，回报 analysis_ready(LogAnalysisResult)。
        """
        if self._busy:
            self.error_occurred.emit("正在处理上一条请求，请稍候。")
            return
        if not self._settings.is_configured():
            self.error_occurred.emit("AI 未配置（缺少 base_url 或 API Key）。")
            return

        opts = options or ContextOptions(
            max_app_lines=self._settings.max_recent_log_lines,
            enable_masking=self._settings.enable_log_masking,
        )
        context_text = self._context_builder.build(opts)
        if not context_text.strip():
            self.error_occurred.emit("没有可分析的日志（软件 / 串口 / 执行日志均为空）。")
            return

        instruction = (
            "你是测试设备日志分析助手。请分析以下软件运行日志、串口接收日志与执行日志，"
            "判断是否存在异常、告警或错误，定位关键证据并给出可能原因与排查建议。\n"
            "只输出一个 JSON 对象（不要任何额外文字、不要 Markdown 代码块），字段如下：\n"
            '{"summary": "一句话结论", "severity": "info|low|medium|high|critical", '
            '"evidence": ["关键日志行"], "possible_causes": ["可能原因"], '
            '"suggested_actions": ["排查/修复建议"], "confidence": 0.0~1.0}'
        )
        user_text = instruction + "\n\n[待分析日志]\n" + context_text

        profile = get_profile(self._page_key)
        analysis_model = self._resolve_model(
            profile.get("model", self._settings.effective_model)
        )
        messages = self._prompt_manager.build_messages(
            page_key=self._page_key,
            history=[],
            user_text=user_text,
            budget=self._budget_for(analysis_model),
        )
        self._history.append({"role": "user", "content": "（请求结构化日志分析）"})

        self._pending_mode = _MODE_ANALYSIS
        self._start_worker(
            messages=messages,
            model=analysis_model,
            temperature=profile.get("temperature", 0.1),
            max_tokens=profile.get("max_tokens", 2048),
        )

    def generate_draft(self, kind: str, user_text: str) -> None:
        """生成测试配置 / 测试脚本草案（AI_Assist.md §9 / §12）。

        kind: CONFIG_DRAFT 或 SCRIPT_DRAFT；
        模型按对应 schema 输出 JSON 草案，回报 draft_ready(ParsedResponse)。
        草案仅为草案——须经 UI 预览 + 本地校验 + 用户确认后才能 apply。
        """
        text = (user_text or "").strip()
        if not text:
            return
        if self._busy:
            self.error_occurred.emit("正在处理上一条请求，请稍候。")
            return
        if not self._settings.is_configured():
            self.error_occurred.emit("AI 未配置（缺少 base_url 或 API Key）。")
            return
        if kind not in (CONFIG_DRAFT, SCRIPT_DRAFT):
            self.error_occurred.emit(f"未知草案类型：{kind}")
            return

        instruction = self._draft_instruction(kind)
        full_text = instruction + "\n\n[用户需求]\n" + text

        profile = get_profile(self._page_key)
        draft_model = self._resolve_model(
            profile.get("model", self._settings.effective_model)
        )
        messages = self._prompt_manager.build_messages(
            page_key=self._page_key,
            history=[],
            user_text=full_text,
            budget=self._budget_for(draft_model),
        )
        self._history.append({"role": "user", "content": text})

        self._pending_mode = (
            _MODE_CONFIG_DRAFT if kind == CONFIG_DRAFT else _MODE_SCRIPT_DRAFT
        )
        self._start_worker(
            messages=messages,
            model=draft_model,
            temperature=profile.get("temperature", 0.0),
            max_tokens=max(profile.get("max_tokens", 2048), 4096),
        )

    def _draft_instruction(self, kind: str) -> str:
        page = self._page_key or "_default"
        if kind == SCRIPT_DRAFT:
            return (
                "你是 Custom Test 序列助手。请根据用户需求生成一个测试序列草案。\n"
                "只输出一个 JSON 对象（不要任何额外文字、不要 Markdown 代码块），结构如下：\n"
                '{"kind": "script_draft", "title": "标题", "notes": "说明", '
                '"sequence": [{"node_type": "<已注册节点类型>", "params": {...}, '
                '"children": [...]}], "instruments": {}, "metadata": {}}\n'
                "sequence 为节点树，node_type 必须是系统已注册的节点类型；"
                "容器节点（循环/分支）用 children 表达子节点。\n"
                "若上下文已提供[当前 Custom Test 画布序列]，请在其基础上按用户需求优化，"
                "并输出优化后的完整序列。这是草案，会经本地 preflight 校验后由用户确认才应用。"
            )
        return (
            "你是测试配置助手。请根据用户需求生成一个测试配置草案。\n"
            "只输出一个 JSON 对象（不要任何额外文字、不要 Markdown 代码块），结构如下：\n"
            '{"kind": "config_draft", "target_page": "' + page + '", '
            '"title": "标题", "notes": "说明", "payload": {<配置字段>}}\n'
            "payload 为页面配置字典。这是草案，会由用户预览校验确认后才应用。"
        )

    def _register_draft(self, parsed) -> None:
        """把 generate_draft 产出的草案登记到 DraftRegistry，并向模型回灌 draft_id。

        草案经 draft_ready 给 UI 预览的同时，登记一个稳定 draft_id 并以 system 消息
        写入对话历史，使后续 agent 轮次中模型可调 apply_test_config_draft(draft_id)
        经确认闭环落地。草案解析失败时不登记、不回灌句柄。
        """
        if parsed is None or not getattr(parsed, "ok", False) or parsed.payload is None:
            return
        try:
            draft_id = self._draft_registry.register(parsed)
        except Exception:  # noqa: BLE001 - 登记失败不影响 draft_ready 主流程
            logger.error("登记草案失败", exc_info=True)
            return
        if not draft_id:
            return
        kind = getattr(parsed, "kind", "")
        title = getattr(parsed.payload, "title", "") or ""
        kind_label = "脚本" if kind == SCRIPT_DRAFT else "配置"
        note = (
            f"[系统] 已生成{kind_label}草案 {draft_id}（标题：{title}）。"
            f"如需应用，调用 apply_test_config_draft(draft_id=\"{draft_id}\")，"
            f"经用户确认后落地；草案绝不自动应用。"
        )
        self._history.append({"role": "system", "content": note})
        _save_persisted_history(self._history, self._session_key)

    def test_connection(self) -> None:
        """连通性测试（同步、轻量），结果经 connection_tested 信号回报。"""
        if not self._settings.is_configured():
            self.connection_tested.emit(False, "未配置 base_url 或 API Key")
            return
        try:
            client = self._make_client()
            client.ping(self.current_model())
        except AIClientError as exc:
            self.connection_tested.emit(False, str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            logger.error("测试连接未预期异常", exc_info=True)
            self.connection_tested.emit(False, f"未预期错误：{exc}")
            return
        self.connection_tested.emit(True, "连接成功")

    def shutdown(self) -> None:
        self._pending_mode = _MODE_CHAT
        self.cancel()
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)
        self._cleanup_thread()
        for thread, worker in list(self._orphans):
            try:
                if worker is not None:
                    worker.cancel()
                if thread.isRunning():
                    thread.quit()
                    thread.wait(2000)
            except RuntimeError:
                pass
        self._orphans.clear()

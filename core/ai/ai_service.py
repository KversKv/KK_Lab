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

from core.ai.config import AISettings
from core.ai.context_builder import ContextBuilder, ContextOptions
from core.ai.conversation_store import (
    clear_history as _clear_persisted_history,
    load_history as _load_persisted_history,
    save_history as _save_persisted_history,
)
from core.ai.log_ring import get_log_ring
from core.ai.newapi_client import AIClientError, ChatResult, NewAPIClient
from core.ai.profiles import get_profile
from core.ai.prompt_manager import PromptManager
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

    def __init__(self, client: NewAPIClient, model, messages, temperature, max_tokens):
        super().__init__()
        self._client = client
        self._model = model
        self._messages = messages
        self._temperature = temperature
        self._max_tokens = max_tokens
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


_MODE_CHAT = "chat"
_MODE_ANALYSIS = "analysis"
_MODE_CONFIG_DRAFT = "config_draft"
_MODE_SCRIPT_DRAFT = "script_draft"
_MODE_AGENT = "agent"

_MAX_TOOL_ROUNDS = 5


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

    def __init__(self, settings: AISettings, page_key_getter=None, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._page_key: str | None = None
        self._history: list[dict[str, str]] = _load_persisted_history()
        self._busy = False
        self._pending_mode = _MODE_CHAT
        self._model_override: str | None = None
        self._stream_buffer = ""
        self._session_stats = SessionStats()

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

        self._registry = None
        self._dispatcher = None
        self._agent_messages: list[dict] = []
        self._agent_rounds = 0
        self._agent_model = ""
        self._agent_temperature = 0.2
        self._agent_max_tokens = 2048

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
        if page_key != self._page_key:
            self._page_key = page_key
            logger.debug("AI 上下文切换页面: %s", page_key)

    def current_page_key(self) -> str | None:
        return self._page_key

    def clear_history(self) -> None:
        self._history.clear()
        _clear_persisted_history()
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

    def _make_client(self) -> NewAPIClient:
        return NewAPIClient(
            base_url=self._settings.effective_base_url,
            api_key=self._settings.effective_api_key,
            timeout_seconds=self._settings.timeout_seconds,
        )

    def send(
        self,
        user_text: str,
        include_recent_logs: bool = False,
        extra_context: str = "",
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

        messages = self._prompt_manager.build_messages(
            page_key=self._page_key,
            history=self._history,
            user_text=text,
            log_context=log_context,
            extra_context=extra_context,
        )
        self._history.append({"role": "user", "content": text})

        profile = get_profile(self._page_key)
        model = self._resolve_model(profile.get("model", self._settings.effective_model))
        temperature = profile.get("temperature", 0.2)
        max_tokens = profile.get("max_tokens", 2048)

        tools = None
        if self._dispatcher is not None and self._registry is not None:
            tools = self._registry.to_tools()

        if tools:
            self._pending_mode = _MODE_AGENT
            self._agent_messages = list(messages)
            self._agent_rounds = 0
            self._agent_model = model
            self._agent_temperature = temperature
            self._agent_max_tokens = max_tokens
            self._start_worker(
                messages=self._agent_messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
            )
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

    def send_with_waveform(self, user_text: str, digest) -> None:
        """带波形摘要发送（F1.5/F1.6）：把 WaveformDigest 文本化注入上下文。"""
        from core.ai.prompt_manager import format_waveform_digest

        context = format_waveform_digest(digest)
        self.send(user_text, extra_context=context)

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

    def _start_stream_worker(self, messages, model, temperature, max_tokens) -> None:
        self._teardown_thread()
        self._set_busy(True)
        self._stream_buffer = ""
        client = self._make_client()
        self._thread = QThread()
        self._worker = _StreamWorker(client, model, messages, temperature, max_tokens)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.delta.connect(self._on_stream_delta)
        self._worker.finished.connect(self._on_stream_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()
        self.response_started.emit()

    def _on_stream_delta(self, chunk: str) -> None:
        if not chunk:
            return
        self._stream_buffer += chunk
        self.response_delta.emit(chunk)

    def _on_stream_finished(self, result: ChatResult) -> None:
        content = (result.content if result else "") or self._stream_buffer
        self._record_usage(result)
        self._pending_mode = _MODE_CHAT
        self._history.append({"role": "assistant", "content": content})
        _save_persisted_history(self._history)
        self.response_finished.emit(content)
        self._stream_buffer = ""
        self._set_busy(False)

    def _on_finished(self, result: ChatResult) -> None:
        content = result.content if result else ""
        tool_calls = result.tool_calls if result else []
        mode = self._pending_mode
        self._record_usage(result)

        if mode == _MODE_AGENT:
            self._handle_agent_round(content, tool_calls)
            return

        self._pending_mode = _MODE_CHAT
        self._history.append({"role": "assistant", "content": content})
        _save_persisted_history(self._history)

        if mode == _MODE_ANALYSIS:
            parsed = parse(content, tool_calls)
            if parsed.kind == KIND_LOG_ANALYSIS and parsed.payload is not None:
                self.analysis_ready.emit(parsed.payload)
            else:
                self.response_ready.emit(content or "（无分析结果）")
        elif mode == _MODE_CONFIG_DRAFT:
            parsed = parse_expected(content, CONFIG_DRAFT)
            self.draft_ready.emit(parsed)
        elif mode == _MODE_SCRIPT_DRAFT:
            parsed = parse_expected(content, SCRIPT_DRAFT)
            self.draft_ready.emit(parsed)
        else:
            self.response_ready.emit(content)
        self._set_busy(False)

    def _on_failed(self, message: str) -> None:
        self._pending_mode = _MODE_CHAT
        self._stream_buffer = ""
        if self._history and self._history[-1].get("role") == "user":
            self._history.pop()
        self.error_occurred.emit(message)
        self._set_busy(False)

    def _handle_agent_round(self, content: str, tool_calls: list) -> None:
        """处理一轮 agent 结果：无 tool_calls 则结束；有则执行并回灌再起一轮。

        关键：执行 tool_calls 可能弹模态确认框（嵌套事件循环），必须延后到
        本槽函数返回、worker/QThread 完成清理之后再执行，否则嵌套事件循环会
        在 finished 信号仍在栈上时触发 _cleanup_thread.deleteLater() 销毁 worker，
        导致 C++ 对象在信号发射期间被删除而崩溃（窗口闪退）。
        """
        if not tool_calls:
            self._pending_mode = _MODE_CHAT
            self._history.append({"role": "assistant", "content": content})
            _save_persisted_history(self._history)
            self.response_ready.emit(content)
            self._set_busy(False)
            return

        self._agent_messages.append(
            {"role": "assistant", "content": content or "", "tool_calls": tool_calls}
        )
        QTimer.singleShot(0, lambda: self._run_tool_calls(content, list(tool_calls)))

    def _run_tool_calls(self, content: str, tool_calls: list) -> None:
        """延后执行的 tool_calls 处理（已脱离 worker.finished 槽栈）。"""
        if self._pending_mode != _MODE_AGENT:
            return

        for call in tool_calls:
            self._execute_tool_call(call)

        self._agent_rounds += 1
        if self._agent_rounds >= _MAX_TOOL_ROUNDS:
            self._pending_mode = _MODE_CHAT
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

        self._agent_messages.append(
            {
                "role": "tool",
                "tool_call_id": call_id,
                "name": name,
                "content": payload,
            }
        )

    def _run_next_agent_round(self) -> None:
        if self._pending_mode != _MODE_AGENT:
            return
        tools = self._registry.to_tools() if self._registry else None
        self._start_worker(
            messages=self._agent_messages,
            model=self._agent_model,
            temperature=self._agent_temperature,
            max_tokens=self._agent_max_tokens,
            tools=tools,
        )

    def _teardown_thread(self) -> None:
        """启动新 worker 前，确保上一个 QThread 已彻底退出并断连。

        多轮 tool-calling 下，前一轮的 thread.finished -> _cleanup_thread 可能尚未
        被事件循环处理，此时直接覆写 self._thread/_worker 会丢失对正在退出线程的
        引用，造成 C++ 对象提前析构而崩溃。这里同步收尾旧线程后再继续。
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
            thread.quit()
            thread.wait(3000)
        if worker is not None:
            worker.deleteLater()
        thread.deleteLater()

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

        messages = self._prompt_manager.build_messages(
            page_key=self._page_key,
            history=[],
            user_text=user_text,
        )
        self._history.append({"role": "user", "content": "（请求结构化日志分析）"})

        profile = get_profile(self._page_key)
        self._pending_mode = _MODE_ANALYSIS
        self._start_worker(
            messages=messages,
            model=self._resolve_model(profile.get("model", self._settings.effective_model)),
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

        messages = self._prompt_manager.build_messages(
            page_key=self._page_key,
            history=[],
            user_text=full_text,
        )
        self._history.append({"role": "user", "content": text})

        profile = get_profile(self._page_key)
        self._pending_mode = (
            _MODE_CONFIG_DRAFT if kind == CONFIG_DRAFT else _MODE_SCRIPT_DRAFT
        )
        self._start_worker(
            messages=messages,
            model=self._resolve_model(profile.get("model", self._settings.effective_model)),
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

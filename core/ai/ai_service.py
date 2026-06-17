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

from PySide6.QtCore import QObject, QThread, Signal

from core.ai.config import AISettings
from core.ai.log_ring import get_log_ring
from core.ai.newapi_client import AIClientError, ChatResult, NewAPIClient
from core.ai.profiles import get_profile
from core.ai.prompt_manager import PromptManager
from core.ai.providers.page_provider import PageContextProvider
from log_config import get_logger

logger = get_logger(__name__)


class _ChatWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, client: NewAPIClient, model: str, messages, temperature, max_tokens):
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
            result = self._client.chat(
                model=self._model,
                messages=self._messages,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
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


class AIService(QObject):
    response_ready = Signal(str)
    error_occurred = Signal(str)
    busy_changed = Signal(bool)
    connection_tested = Signal(bool, str)

    def __init__(self, settings: AISettings, page_key_getter=None, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._page_key: str | None = None
        self._history: list[dict[str, str]] = []
        self._busy = False

        self._prompt_manager = PromptManager(
            enable_log_masking=settings.enable_log_masking
        )
        if page_key_getter is not None:
            self._prompt_manager.add_provider(PageContextProvider(page_key_getter))

        self._thread: QThread | None = None
        self._worker: _ChatWorker | None = None

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

    def clear_history(self) -> None:
        self._history.clear()

    def _make_client(self) -> NewAPIClient:
        return NewAPIClient(
            base_url=self._settings.effective_base_url,
            api_key=self._settings.effective_api_key,
            timeout_seconds=self._settings.timeout_seconds,
        )

    def send(self, user_text: str, include_recent_logs: bool = False) -> None:
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
        )
        self._history.append({"role": "user", "content": text})

        profile = get_profile(self._page_key)
        self._start_worker(
            messages=messages,
            model=profile.get("model", self._settings.effective_model),
            temperature=profile.get("temperature", 0.2),
            max_tokens=profile.get("max_tokens", 2048),
        )

    def cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()

    def _start_worker(self, messages, model, temperature, max_tokens) -> None:
        self._set_busy(True)
        client = self._make_client()
        self._thread = QThread()
        self._worker = _ChatWorker(client, model, messages, temperature, max_tokens)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _on_finished(self, result: ChatResult) -> None:
        content = result.content if result else ""
        self._history.append({"role": "assistant", "content": content})
        self.response_ready.emit(content)
        self._set_busy(False)

    def _on_failed(self, message: str) -> None:
        if self._history and self._history[-1].get("role") == "user":
            self._history.pop()
        self.error_occurred.emit(message)
        self._set_busy(False)

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
        """基础日志分析：取最近 N 行日志请模型给出排查建议。"""
        self.send(
            "请基于最近的运行日志，分析是否存在异常/告警/错误，并给出可能原因与排查建议。",
            include_recent_logs=True,
        )

    def test_connection(self) -> None:
        """连通性测试（同步、轻量），结果经 connection_tested 信号回报。"""
        if not self._settings.is_configured():
            self.connection_tested.emit(False, "未配置 base_url 或 API Key")
            return
        try:
            client = self._make_client()
            client.ping(self._settings.effective_model)
        except AIClientError as exc:
            self.connection_tested.emit(False, str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            logger.error("测试连接未预期异常", exc_info=True)
            self.connection_tested.emit(False, f"未预期错误：{exc}")
            return
        self.connection_tested.emit(True, "连接成功")

    def shutdown(self) -> None:
        self.cancel()
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)
        self._cleanup_thread()

"""New API（OpenAI 兼容网关）客户端：非流式 /chat/completions。

约束（AI_Assist.md §5 + 阶段 0 smoke test 验证）：
  - localhost / 内网 IP 走直连，httpx.Client(trust_env=False) 绕过系统代理；
  - 鉴权 Authorization: Bearer <key>；
  - 推理模型 glm-5.1-fp8：正文取 choices[0].message.content，
    推理过程在 message.reasoning（独立字段，不当正文）；max_tokens 必须 ≥ 1024。
  - 本类不含 Qt 依赖，可在 QThread worker 中安全使用。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from log_config import get_logger

logger = get_logger(__name__)

_MIN_MAX_TOKENS = 1024


class AIClientError(Exception):
    """统一对外异常类型（含网络/HTTP/解析失败）。"""


@dataclass
class ChatResult:
    content: str
    reasoning: str = ""
    model: str = ""
    finish_reason: str = ""
    usage: dict[str, Any] | None = None


class NewAPIClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float = 60.0):
        self._base_url = (base_url or "").rstrip("/")
        self._api_key = api_key or ""
        self._timeout = float(timeout_seconds)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        cancel_check=None,
    ) -> ChatResult:
        """同步调用 chat/completions（非流式）。

        cancel_check: 可选无参可调用对象，返回 True 表示用户已取消。
        """
        if not self._base_url:
            raise AIClientError("未配置 base_url")
        if not self._api_key:
            raise AIClientError("未配置 API Key")

        effective_max_tokens = max(int(max_tokens), _MIN_MAX_TOKENS)
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": effective_max_tokens,
            "stream": False,
        }
        url = f"{self._base_url}/chat/completions"

        if cancel_check and cancel_check():
            raise AIClientError("已取消")

        try:
            with httpx.Client(trust_env=False, timeout=self._timeout) as client:
                resp = client.post(url, headers=self._headers(), json=payload)
        except httpx.TimeoutException as exc:
            logger.error("New API 请求超时: %s", url, exc_info=True)
            raise AIClientError(f"请求超时（{self._timeout:.0f}s）") from exc
        except httpx.HTTPError as exc:
            logger.error("New API 网络错误: %s", url, exc_info=True)
            raise AIClientError(f"网络错误：{exc}") from exc

        if cancel_check and cancel_check():
            raise AIClientError("已取消")

        if resp.status_code != 200:
            snippet = resp.text[:300] if resp.text else ""
            logger.error("New API HTTP %s: %s", resp.status_code, snippet)
            raise AIClientError(f"HTTP {resp.status_code}: {snippet}")

        try:
            body = resp.json()
        except ValueError as exc:
            logger.error("New API 响应非 JSON", exc_info=True)
            raise AIClientError("响应解析失败（非 JSON）") from exc

        return self._parse(body)

    @staticmethod
    def _parse(body: dict[str, Any]) -> ChatResult:
        choices = body.get("choices") or []
        if not choices:
            raise AIClientError("响应缺少 choices")
        first = choices[0] or {}
        message = first.get("message") or {}
        content = message.get("content")
        reasoning = message.get("reasoning") or ""
        if content is None:
            raise AIClientError("响应 content 为空（可能 max_tokens 过小被推理耗尽）")
        return ChatResult(
            content=str(content),
            reasoning=str(reasoning),
            model=str(body.get("model", "")),
            finish_reason=str(first.get("finish_reason", "")),
            usage=body.get("usage"),
        )

    def ping(self, model: str) -> ChatResult:
        """连通性测试：发一条极简消息验证鉴权与网关可达。"""
        return self.chat(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            temperature=0.0,
            max_tokens=_MIN_MAX_TOKENS,
        )

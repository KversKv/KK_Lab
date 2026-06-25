"""New API（OpenAI 兼容网关）客户端：非流式 /chat/completions。

约束（AIAssist_Architecture.md §5 + 阶段 0 smoke test 验证）：
  - localhost / 内网 IP 走直连，httpx.Client(trust_env=False) 绕过系统代理；
  - 鉴权 Authorization: Bearer <key>；
  - 推理模型 glm-5.1-fp8：正文取 choices[0].message.content，
    推理过程在 message.reasoning（独立字段，不当正文）；max_tokens 必须 ≥ 1024。
  - 本类不含 Qt 依赖，可在 QThread worker 中安全使用。
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

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
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    elapsed_ms: int = 0


class NewAPIClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float = 60.0):
        self._base_url = (base_url or "").rstrip("/")
        self._api_key = api_key or ""
        self._timeout = float(timeout_seconds)

    def _timeout_config(self, *, stream: bool) -> httpx.Timeout:
        """分项超时：connect 短、read 宽松。

        本地大模型高峰期首字节/分块可能很慢，用单一总超时容易误杀长回答；
        改为：connect 固定短超时快速暴露网络不可达；read 用配置的 timeout_seconds
        作为"两次数据之间"的间隔上限（流式即分块间隔，非流式即整体响应等待）。
        write/pool 复用 connect 值。
        """
        connect = min(10.0, self._timeout) if self._timeout > 0 else 10.0
        read = self._timeout if self._timeout > 0 else None
        return httpx.Timeout(read, connect=connect, write=connect, pool=connect)

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
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any | None = None,
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
        if tools:
            payload["tools"] = tools
            if tool_choice is not None:
                payload["tool_choice"] = tool_choice
        url = f"{self._base_url}/chat/completions"

        if cancel_check and cancel_check():
            raise AIClientError("已取消")

        start = time.monotonic()
        try:
            with httpx.Client(
                trust_env=False, timeout=self._timeout_config(stream=False)
            ) as client:
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

        elapsed_ms = int((time.monotonic() - start) * 1000)
        result = self._parse(body)
        result.elapsed_ms = elapsed_ms
        return result

    def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any | None = None,
        on_delta: Callable[[str], None] | None = None,
        cancel_check=None,
    ) -> ChatResult:
        """流式调用 chat/completions（SSE）。

        逐块解析 choices[0].delta.content，经 on_delta 增量回调；
        推理字段 delta.reasoning 单独累计不并入正文；
        返回聚合后的完整 ChatResult（用于写入历史）。
        支持 tools：流式分块里 delta.tool_calls 按 index 增量聚合，
        结束后填入 ChatResult.tool_calls（供 agent 末轮流式：有工具调用则
        丢弃本次流式正文转入工具执行，无工具调用则流式正文即最终回答）。
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
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
            if tool_choice is not None:
                payload["tool_choice"] = tool_choice
        url = f"{self._base_url}/chat/completions"

        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        tool_calls_acc: dict[int, dict[str, Any]] = {}
        finish_reason = ""
        resp_model = model
        usage: dict[str, Any] | None = None

        start = time.monotonic()
        try:
            with httpx.Client(
                trust_env=False, timeout=self._timeout_config(stream=True)
            ) as client:
                with client.stream(
                    "POST", url, headers=self._headers(), json=payload
                ) as resp:
                    if resp.status_code != 200:
                        resp.read()
                        snippet = resp.text[:300] if resp.text else ""
                        logger.error("New API 流式 HTTP %s: %s", resp.status_code, snippet)
                        raise AIClientError(f"HTTP {resp.status_code}: {snippet}")
                    for line in resp.iter_lines():
                        if cancel_check and cancel_check():
                            raise AIClientError("已取消")
                        if not line:
                            continue
                        if not line.startswith("data:"):
                            continue
                        data = line[len("data:"):].strip()
                        if not data or data == "[DONE]":
                            if data == "[DONE]":
                                break
                            continue
                        try:
                            chunk = json.loads(data)
                        except ValueError:
                            continue
                        chunk_usage = chunk.get("usage")
                        if isinstance(chunk_usage, dict):
                            usage = chunk_usage
                        delta_content, delta_reason, fr, mdl = self._parse_chunk(chunk)
                        self._accumulate_tool_calls(chunk, tool_calls_acc)
                        if mdl:
                            resp_model = mdl
                        if fr:
                            finish_reason = fr
                        if delta_reason:
                            reasoning_parts.append(delta_reason)
                        if delta_content:
                            content_parts.append(delta_content)
                            if on_delta is not None:
                                on_delta(delta_content)
        except httpx.TimeoutException as exc:
            logger.error("New API 流式请求超时: %s", url, exc_info=True)
            raise AIClientError(f"请求超时（{self._timeout:.0f}s）") from exc
        except httpx.HTTPError as exc:
            logger.error("New API 流式网络错误: %s", url, exc_info=True)
            raise AIClientError(f"网络错误：{exc}") from exc

        content = "".join(content_parts)
        tool_calls = [tool_calls_acc[i] for i in sorted(tool_calls_acc)]
        if not content and not reasoning_parts and not tool_calls:
            raise AIClientError("流式响应为空（可能 max_tokens 过小被推理耗尽）")
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return ChatResult(
            content=content,
            reasoning="".join(reasoning_parts),
            model=str(resp_model),
            finish_reason=finish_reason,
            usage=usage,
            tool_calls=tool_calls,
            elapsed_ms=elapsed_ms,
        )

    @staticmethod
    def _accumulate_tool_calls(
        chunk: dict[str, Any], acc: dict[int, dict[str, Any]]
    ) -> None:
        """把 SSE delta.tool_calls 增量片段按 index 聚合成完整 tool_calls。

        OpenAI 协议下 tool_calls 分块到达：首块给 id/name，后续块仅补
        function.arguments 片段，统一按 index 累计拼接。
        """
        choices = chunk.get("choices") or []
        if not choices:
            return
        delta = (choices[0] or {}).get("delta") or {}
        deltas = delta.get("tool_calls") or []
        if not isinstance(deltas, list):
            return
        for item in deltas:
            if not isinstance(item, dict):
                continue
            idx = item.get("index", 0) or 0
            slot = acc.setdefault(
                idx,
                {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
            )
            if item.get("id"):
                slot["id"] = item["id"]
            if item.get("type"):
                slot["type"] = item["type"]
            fn = item.get("function") or {}
            if fn.get("name"):
                slot["function"]["name"] = fn["name"]
            if fn.get("arguments"):
                slot["function"]["arguments"] += fn["arguments"]

    @staticmethod
    def _parse_chunk(chunk: dict[str, Any]) -> tuple[str, str, str, str]:
        """解析单个 SSE 块，返回 (content_delta, reasoning_delta, finish_reason, model)。"""
        choices = chunk.get("choices") or []
        if not choices:
            return "", "", "", str(chunk.get("model", ""))
        first = choices[0] or {}
        delta = first.get("delta") or {}
        content = delta.get("content") or ""
        reasoning = delta.get("reasoning") or ""
        finish_reason = first.get("finish_reason") or ""
        return str(content), str(reasoning), str(finish_reason), str(chunk.get("model", ""))

    @staticmethod
    def _parse(body: dict[str, Any]) -> ChatResult:
        choices = body.get("choices") or []
        if not choices:
            raise AIClientError("响应缺少 choices")
        first = choices[0] or {}
        message = first.get("message") or {}
        content = message.get("content")
        reasoning = message.get("reasoning") or ""
        tool_calls = message.get("tool_calls") or []
        if not isinstance(tool_calls, list):
            tool_calls = []
        if content is None and not tool_calls:
            raise AIClientError("响应 content 为空（可能 max_tokens 过小被推理耗尽）")
        return ChatResult(
            content=str(content) if content is not None else "",
            reasoning=str(reasoning),
            model=str(body.get("model", "")),
            finish_reason=str(first.get("finish_reason", "")),
            usage=body.get("usage"),
            tool_calls=tool_calls,
        )

    def ping(self, model: str) -> ChatResult:
        """连通性测试：发一条极简消息验证鉴权与网关可达。"""
        return self.chat(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            temperature=0.0,
            max_tokens=_MIN_MAX_TOKENS,
        )

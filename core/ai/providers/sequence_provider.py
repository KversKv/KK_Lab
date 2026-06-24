"""序列上下文 Provider（F5.1）：把当前画布序列读为 v2 dict 并文本化喂给 AI。

设计（AI_Assist_NewFeature_V1 §5）：
  - data 级入口：复用 core/orchestrator/serialization（dict ↔ 节点树），不落盘；
  - core 不反向依赖 ui：通过 UI 注入的 sequence_data_getter 回调读取画布 v2 dict；
  - 仅在 Orchestrator 页面（page_key == "orchestrator"）注入上下文，避免无谓污染。

本模块纯逻辑，禁 import Qt。
"""
from __future__ import annotations

from typing import Any, Callable

from core.ai.providers.base import ContextProvider
from log_config import get_logger

logger = get_logger(__name__)

SequenceDataGetter = Callable[[], "dict[str, Any] | None"]

_MAX_NODES_IN_CONTEXT = 200


class SequenceContextProvider(ContextProvider):
    """把当前 Orchestrator 画布序列（v2 dict）摘要为上下文文本。"""

    def __init__(self, sequence_data_getter: SequenceDataGetter | None = None):
        self._getter = sequence_data_getter

    def name(self) -> str:
        return "sequence"

    def set_getter(self, getter: SequenceDataGetter | None) -> None:
        self._getter = getter

    def build_context(self, page_key: str | None) -> str:
        if page_key not in (None, "orchestrator"):
            return ""
        if self._getter is None:
            return ""
        try:
            data = self._getter()
        except Exception:
            logger.error("读取画布序列上下文失败", exc_info=True)
            return ""
        if not data:
            return ""
        return format_sequence_data(data)


def _count_nodes(nodes: list[Any]) -> int:
    total = 0
    for node in nodes:
        if not isinstance(node, dict):
            continue
        total += 1
        children = node.get("children") or []
        if isinstance(children, list):
            total += _count_nodes(children)
    return total


def _summarize_nodes(nodes: list[Any], lines: list[str], depth: int, budget: list[int]) -> None:
    indent = "  " * depth
    for index, node in enumerate(nodes):
        if budget[0] <= 0:
            return
        if not isinstance(node, dict):
            continue
        budget[0] -= 1
        node_type = str(node.get("node_type", "?"))
        params = node.get("params") or {}
        param_text = ""
        if isinstance(params, dict) and params:
            pairs = ", ".join(f"{k}={v}" for k, v in list(params.items())[:6])
            param_text = f" ({pairs})"
        lines.append(f"{indent}- [{index}] {node_type}{param_text}")
        children = node.get("children") or []
        if isinstance(children, list) and children:
            _summarize_nodes(children, lines, depth + 1, budget)


def format_sequence_data(data: dict[str, Any]) -> str:
    """把 v2 序列 dict 文本化为简洁上下文（供 prompt 注入）。"""
    sequence = data.get("sequence")
    if not isinstance(sequence, list):
        return ""
    total = _count_nodes(sequence)
    if total == 0:
        return (
            "[当前 Orchestrator 画布序列（最新，以此为准）]\n"
            "以下为用户画布的当前实时序列；若与此前对话中的序列内容或结论冲突，"
            "一律以本段为准，忽略历史中的旧序列。\n"
            "（空序列，尚未添加节点）"
        )

    lines: list[str] = [
        "[当前 Orchestrator 画布序列（最新，以此为准）]",
        "以下为用户画布的当前实时序列；若与此前对话中的序列内容或结论冲突，"
        "一律以本段为准，忽略历史中的旧序列。",
        f"版本：v{data.get('version', 2)}　顶层节点：{len(sequence)}　总节点：{total}",
    ]
    metadata = data.get("metadata") or {}
    caps = metadata.get("required_capabilities") if isinstance(metadata, dict) else None
    if caps:
        lines.append("所需能力：" + ", ".join(str(c) for c in caps))

    lines.append("节点树：")
    budget = [_MAX_NODES_IN_CONTEXT]
    _summarize_nodes(sequence, lines, 1, budget)
    if total > _MAX_NODES_IN_CONTEXT:
        lines.append(f"  …（已截断，仅展示前 {_MAX_NODES_IN_CONTEXT} 个节点）")
    return "\n".join(lines)

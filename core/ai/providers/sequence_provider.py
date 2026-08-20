"""序列上下文 Provider（F5.1）：把当前画布序列读为 v2 dict 并文本化喂给 AI。

设计（AI_Assist_NewFeature_V1 §5）：
  - data 级入口：复用 core/orchestrator/serialization（dict ↔ 节点树），不落盘；
  - core 不反向依赖 ui：通过 UI 注入的 sequence_data_getter 回调读取画布 v2 dict；
  - 仅在 Orchestrator 页面（page_key == "orchestrator"）注入上下文，避免无谓污染；
  - 附带[可用节点类型目录]（自 NODE_REGISTRY 生成），供模型生成序列草案时对齐
    node_type / params schema（agent 模式 generate_sequence_draft 与 draft 模式共用）。

本模块纯逻辑，禁 import Qt。
"""
from __future__ import annotations

from typing import Any, Callable

from core.ai.providers.base import ContextProvider
from log_config import get_logger

logger = get_logger(__name__)

SequenceDataGetter = Callable[[], "dict[str, Any] | None"]

_MAX_NODES_IN_CONTEXT = 200

# 旧版兼容节点：仅加载历史模板时出现，palette 已隐藏（对齐
# ui/pages/orchestrator/node_metadata.py 的 _LEGACY_NODE_TYPES），生成草案时不进目录。
_LEGACY_NODE_TYPES = frozenset({"IfElse", "IfThenElse"})


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
        parts: list[str] = []
        if self._getter is not None:
            try:
                data = self._getter()
            except Exception:
                logger.error("读取画布序列上下文失败", exc_info=True)
                data = None
            if data:
                canvas_text = format_sequence_data(data)
                if canvas_text:
                    parts.append(canvas_text)
        # 节点目录仅注入 orchestrator 页（getter 仅在该页被注入，此处再按 page_key
        # 收严，避免无页面/通用页上下文被编排节点 schema 污染）。
        if page_key == "orchestrator":
            catalog = format_node_catalog()
            if catalog:
                parts.append(catalog)
        return "\n\n".join(parts)


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


def _accepts_children(cls) -> bool:
    """节点类是否为容器（accepts_children 是实例 property，需实例化后读取）。"""
    try:
        return bool(cls().accepts_children)
    except Exception:  # noqa: BLE001 - 实例化异常按非容器处理
        logger.warning("探测节点容器属性失败：%s", getattr(cls, "node_type", "?"), exc_info=True)
        return False


def _format_param(schema: dict) -> str:
    key = str(schema.get("key", ""))
    if not key:
        return ""
    text = f"{key}:{schema.get('type', '')}"
    default = schema.get("default")
    if default is not None:
        text += f"={default}"
    options = schema.get("options")
    if isinstance(options, (list, tuple)) and options:
        text += "(" + "|".join(str(o) for o in options) + ")"
    return text


def format_node_catalog() -> str:
    """把 NODE_REGISTRY 文本化为可用节点类型目录（供模型生成序列草案对齐 schema）。

    过滤规则（与 ui/pages/orchestrator/node_metadata.py 的分类对齐，改节点状态时同步）：
      - 旧版节点（IfElse/IfThenElse）不进目录；
      - 类属性 unsupported_reason 非空的节点不进目录（preflight 会报 error）；
      - 结构分支（IfBranch/ElseIfBranch/ElseBranch）保留——构建 IfBlock 时必需。
    """
    from core.orchestrator.nodes import NODE_REGISTRY

    if not NODE_REGISTRY:
        return ""
    lines: list[str] = [
        "[可用节点类型目录（生成序列草案时 node_type 只能取自此清单，params 键名与下述一致）]",
        "格式：node_type: 参数名:类型=默认值（括号内为枚举可选值）；带 [容器] 的节点用 children 挂子节点。",
        "变量引用统一用 ${var} 占位符；条件/表达式同类（如 ${value} > 0.5）。",
        "条件分支结构：IfBlock 的 children 必须是 IfBranch/ElseIfBranch/ElseBranch，各分支再挂实际步骤。",
    ]
    by_category: dict[str, list] = {}
    for node_type in sorted(NODE_REGISTRY):
        if node_type in _LEGACY_NODE_TYPES:
            continue
        cls = NODE_REGISTRY[node_type]
        if getattr(cls, "unsupported_reason", ""):
            continue
        by_category.setdefault(getattr(cls, "category", "") or "other", []).append(cls)
    for category in sorted(by_category):
        lines.append(f"== {category} ==")
        for cls in by_category[category]:
            params = [
                text
                for schema in getattr(cls, "PARAM_SCHEMA", None) or []
                if (text := _format_param(schema))
            ]
            marker = " [容器]" if _accepts_children(cls) else ""
            lines.append(
                f"- {cls.node_type}{marker}: " + (", ".join(params) if params else "（无参数）")
            )
    return "\n".join(lines)

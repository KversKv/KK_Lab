# -*- coding: utf-8 -*-
"""generate_sequence_draft 动作单测：生成→本地校验→登记 + 按页裁剪可见性 + 节点目录。

可独立运行（无 pytest 也能跑）：
    python tests/core/ai/test_generate_sequence_draft.py
也可被 pytest 收集：
    pytest tests/core/ai/test_generate_sequence_draft.py
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.ai.actions.builder import build_registry  # noqa: E402
from core.ai.actions.handlers.deps import ActionDeps  # noqa: E402
from core.ai.actions.handlers.test import build_handlers  # noqa: E402
from core.ai.draft_registry import DraftRegistry  # noqa: E402
from core.ai.page_contract import (  # noqa: E402
    ACTION_CAPABILITY_MAP,
    CAP_APPLY_CONFIG,
    CAP_APPLY_SCRIPT,
)
from core.ai.providers.sequence_provider import (  # noqa: E402
    SequenceContextProvider,
    format_node_catalog,
)
from core.ai.schemas import SCRIPT_DRAFT  # noqa: E402

VALID_SEQUENCE = [
    {
        "node_type": "LoopRange",
        "params": {"var_name": "temp", "start": -30, "stop": 80, "step": 10},
        "children": [
            {"node_type": "Delay", "params": {"seconds": 2}},
        ],
    },
    {"node_type": "Delay", "params": {"seconds": 1}},
]


def _make_deps(script_callback=None):
    return ActionDeps(
        draft_registry=DraftRegistry(),
        script_apply_callback=script_callback or (lambda nodes: (True, "")),
    )


def test_generate_sequence_draft_registers_valid_draft():
    deps = _make_deps()
    handler = build_handlers(deps)["generate_sequence_draft"]
    result = handler({"sequence": VALID_SEQUENCE, "title": "温度遍历", "notes": "-30→80"})
    assert result["ok"] is True
    assert result["kind"] == SCRIPT_DRAFT
    draft_id = result["draft_id"]
    entry = deps.draft_registry.get(draft_id)
    assert entry is not None
    assert entry["kind"] == SCRIPT_DRAFT
    assert entry["title"] == "温度遍历"
    assert isinstance(entry["payload"].sequence, list)
    assert "apply_test_config_draft" in result["_message"]


def test_generate_sequence_draft_rejects_unknown_node_type():
    deps = _make_deps()
    handler = build_handlers(deps)["generate_sequence_draft"]
    result = handler({"sequence": [{"node_type": "NotARealNode"}]})
    assert result["ok"] is False
    assert result["errors"]
    assert any("未知节点类型" in e for e in result["errors"])
    assert deps.draft_registry.list() == []


def test_generate_sequence_draft_rejects_invalid_param_type():
    deps = _make_deps()
    handler = build_handlers(deps)["generate_sequence_draft"]
    result = handler({"sequence": [{"node_type": "Delay", "params": {"seconds": "abc"}}]})
    assert result["ok"] is False
    assert result["errors"]
    assert deps.draft_registry.list() == []


def test_generate_sequence_draft_rejects_empty_sequence():
    handler = build_handlers(_make_deps())["generate_sequence_draft"]
    assert handler({"sequence": []})["ok"] is False
    assert handler({})["ok"] is False


def test_generate_sequence_draft_requires_apply_callback():
    deps = ActionDeps(draft_registry=DraftRegistry(), script_apply_callback=None)
    handler = build_handlers(deps)["generate_sequence_draft"]
    result = handler({"sequence": VALID_SEQUENCE})
    assert result["ok"] is False


def test_generate_then_apply_two_step_flow():
    """两步闭环：generate 登记 draft_id → apply 经回调把节点树落地（画布语义）。"""
    applied: list = []

    def _apply(nodes):
        applied.append(nodes)
        return True, "脚本草案已应用到画布。"

    deps = _make_deps(script_callback=_apply)
    handlers = build_handlers(deps)
    gen = handlers["generate_sequence_draft"]({"sequence": VALID_SEQUENCE})
    assert gen["ok"] is True
    draft_id = gen["draft_id"]
    # apply 会做同校验并整体回灌节点树（整体替换画布语义）
    apply_result = handlers["apply_test_config_draft"]({"draft_id": draft_id})
    assert apply_result["ok"] is True
    assert apply_result["kind"] == SCRIPT_DRAFT
    assert apply_result["_message"]
    assert len(applied) == 1
    nodes = applied[0]
    assert len(nodes) == 2
    assert nodes[0].node_type == "LoopRange"
    assert nodes[0].params["var_name"] == "temp"
    assert len(nodes[0].children) == 1
    assert nodes[0].children[0].node_type == "Delay"


def test_capability_map_gates_generate_sequence_draft():
    assert ACTION_CAPABILITY_MAP["generate_sequence_draft"] == (CAP_APPLY_SCRIPT,)
    registry = build_registry()
    tools_script = {t["function"]["name"] for t in registry.to_tools({CAP_APPLY_SCRIPT})}
    assert "generate_sequence_draft" in tools_script
    assert "apply_test_config_draft" in tools_script
    tools_config = {t["function"]["name"] for t in registry.to_tools({CAP_APPLY_CONFIG})}
    assert "generate_sequence_draft" not in tools_config
    assert "generate_config_draft" in tools_config
    tools_none = {t["function"]["name"] for t in registry.to_tools(set())}
    assert "generate_sequence_draft" not in tools_none


def test_node_catalog_lists_registered_types():
    catalog = format_node_catalog()
    assert catalog
    assert "Delay" in catalog
    assert "LoopRange" in catalog
    assert "IfBlock" in catalog
    # 旧版节点与未支持节点不进目录
    assert "- IfElse:" not in catalog
    assert "- IfThenElse:" not in catalog
    assert "RFAnalyzerMeasure" not in catalog
    # 容器标记 + 参数类型/默认值格式
    assert "[容器]" in catalog
    assert "seconds:float=1.0" in catalog


def test_sequence_provider_includes_catalog_on_orchestrator():
    data = {
        "version": 2,
        "sequence": [{"node_type": "Delay", "params": {"seconds": 1}}],
    }
    provider = SequenceContextProvider(lambda: data)
    ctx = provider.build_context("orchestrator")
    assert "当前 Orchestrator 画布序列" in ctx
    assert "可用节点类型目录" in ctx
    assert provider.build_context("pmu_test") == ""


def test_sequence_provider_catalog_without_getter():
    provider = SequenceContextProvider(None)
    ctx = provider.build_context("orchestrator")
    assert "可用节点类型目录" in ctx


if __name__ == "__main__":
    failures = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"PASS {name}")
            except AssertionError:
                failures += 1
                import traceback

                traceback.print_exc()
                print(f"FAIL {name}")
    raise SystemExit(1 if failures else 0)

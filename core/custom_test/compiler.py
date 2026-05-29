"""Sequence compiler and dry-run summaries."""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from core.custom_test.execution_plan import ExecutionPlan, ExecutionStep
from core.custom_test.nodes.base import BaseNode
from core.custom_test.resolver import collect_required_capabilities


def compile_sequence(nodes: Sequence[BaseNode]) -> ExecutionPlan:
    steps: List[ExecutionStep] = []

    def walk(items: Sequence[BaseNode], prefix: Tuple[int, ...]) -> None:
        for index, node in enumerate(items, start=1):
            path = prefix + (index,)
            steps.append(ExecutionStep(
                uid=node.uid,
                node_type=node.node_type,
                display_name=node.display_name,
                path=path,
                depth=len(path) - 1,
                required_capabilities=tuple(node.required_instruments()),
            ))
            if node.children:
                walk(node.children, path)

    walk(nodes, ())
    return ExecutionPlan(steps=steps)


def build_dry_run_summary(nodes: Sequence[BaseNode]) -> Dict[str, object]:
    plan = compile_sequence(nodes)
    return {
        "total_steps": plan.total_steps,
        "required_capabilities": sorted(collect_required_capabilities(nodes)),
        "plan": plan.to_dict(),
    }

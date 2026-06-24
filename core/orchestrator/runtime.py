"""Orchestrator 节点运行时辅助。"""

from __future__ import annotations

from typing import List

from core.orchestrator.context import BreakLoop, ContinueLoop, ExecutionContext
from core.orchestrator.nodes.base import BaseNode


def execute_children(children: List[BaseNode], context: ExecutionContext) -> None:
    """深度优先执行子节点列表。"""
    for child in children:
        context.check_stop()
        while context.should_pause and not context.should_stop:
            context.sleep(0.1, poll=0.1)
        context.check_stop()
        try:
            execute_node(child, context)
        except ContinueLoop:
            return
        except BreakLoop:
            raise


def execute_node(node: BaseNode, context: ExecutionContext) -> None:
    """执行单个节点，触发上下文回调。"""
    context.check_stop()
    if context.on_step_started:
        context.on_step_started(node.uid, node.display_name)
    previous_uid = context.set_current_node(node.uid)
    try:
        node.execute(context)
    finally:
        context.set_current_node(previous_uid)
    context.check_stop()
    if context.on_step_finished:
        context.on_step_finished(node.uid, node.display_name)

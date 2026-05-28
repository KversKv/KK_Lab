"""Custom Test 节点运行时辅助。"""

from __future__ import annotations

import time
from typing import List

from core.custom_test.context import BreakLoop, ContinueLoop, ExecutionContext
from core.custom_test.nodes.base import BaseNode


def execute_children(children: List[BaseNode], context: ExecutionContext) -> None:
    """深度优先执行子节点列表。"""
    for child in children:
        if context.should_stop:
            return
        while context.should_pause and not context.should_stop:
            time.sleep(0.1)
        try:
            execute_node(child, context)
        except ContinueLoop:
            return
        except BreakLoop:
            raise


def execute_node(node: BaseNode, context: ExecutionContext) -> None:
    """执行单个节点，触发上下文回调。"""
    if context.on_step_started:
        context.on_step_started(node.uid, node.display_name)
    previous_uid = context.set_current_node(node.uid)
    try:
        node.execute(context)
    finally:
        context.set_current_node(previous_uid)
    if context.on_step_finished:
        context.on_step_finished(node.uid, node.display_name)

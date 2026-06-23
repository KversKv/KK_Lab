# -*- coding: utf-8 -*-
"""串口脚本执行引擎纯逻辑（无 Qt / 无 IO 依赖）。

从 SerialComMixin 脚本职责下沉：步骤排序 / 等待关键字匹配 / 循环与下一步判定。
供 ui.modules.serialCom_module.mixins.script_mixin 调用，便于脱离 GUI 单元测试。
"""
from __future__ import annotations

from typing import Any


def ordered_steps(script: Any) -> list:
    """按 priority 升序返回启用（priority>0）的步骤。

    与原 SerialComMixin._sc_script_ordered_steps 行为一致。
    """
    if not script:
        return []
    steps = [s for s in script.get("steps", []) if int(s.get("priority", 0)) > 0]
    return sorted(steps, key=lambda s: int(s.get("priority", 0)))


def match_wait_keyword(buffer: str, keyword: str) -> tuple:
    """在累积接收缓冲区中匹配等待关键字。

    返回 (matched, new_buffer)：
      - 先将 buffer 截断到最近 4096 字节以防爆内存；
      - keyword 为空时永不匹配；
      - matched 为 True 时 new_buffer 仍返回截断后的 buffer，由调用方决定是否清空。
    """
    if not keyword:
        return (False, buffer[-4096:] if len(buffer) > 4096 else buffer)
    if len(buffer) > 4096:
        buffer = buffer[-4096:]
    return (keyword in buffer, buffer)


def decide_loop_next(step_index: int, num_steps: int,
                     loop_remaining: int, loop_infinite: bool) -> tuple:
    """决定脚本下一步动作。

    返回 (action, new_step_index, new_loop_remaining)：
      - "exec"        : step_index < num_steps，执行当前步（状态不变）；
      - "loop_restart": 到达末尾且仍有循环，回到 step 0（finite 时 loop_remaining 已递减）；
      - "done"        : 到达末尾且循环耗尽，结束。

    与原 _sc_script_on_loop_end 的循环计数语义一致：
      loop_infinite 永不耗尽；finite 时 loop_remaining 每轮递减，<=0 即结束。
    """
    if step_index < num_steps:
        return ("exec", step_index, loop_remaining)
    if loop_infinite:
        return ("loop_restart", 0, loop_remaining)
    new_remaining = loop_remaining - 1
    if new_remaining > 0:
        return ("loop_restart", 0, new_remaining)
    return ("done", 0, new_remaining)

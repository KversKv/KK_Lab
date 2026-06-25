"""AI 受控动作 handlers（AIAssist_Architecture.md §8）。

各 handler 模块导出：
  - SPECS: list[ActionSpec]（动作元数据）
  - build_handlers(deps) -> dict[name, handler]（按注入依赖构建可调用）

deps 为 ActionDeps（core/ai/actions/handlers/deps.py），UI 注入只读访问器与受控操作回调，
保证 core 不反向依赖 ui、仪器一律经 InstrumentManager。
"""
from __future__ import annotations

from core.ai.actions.handlers.deps import ActionDeps

__all__ = ["ActionDeps"]

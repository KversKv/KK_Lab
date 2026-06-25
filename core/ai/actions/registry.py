"""ActionSpec + ActionRegistry（AIAssist_Architecture.md §8）。

ActionSpec 描述一个受控动作的元数据（名称 / 描述 / 参数 Schema / 风险等级 /
是否需确认 / 结果 Schema / 类别）。executor 不在 spec 上，由 dispatcher 按 name
路由到 handlers/*。

ActionRegistry 负责注册 / 查找 / 渲染 OpenAI tools 列表（供原生 function calling）。

本模块纯逻辑，禁 import Qt。不引入额外依赖（打包体积铁律）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from log_config import get_logger

logger = get_logger(__name__)

CATEGORY_QUERY = "query"
CATEGORY_UI = "ui"
CATEGORY_TEST_CONFIG = "test_config"
CATEGORY_TEST_SEQUENCE = "test_sequence"
CATEGORY_SERIAL = "serial"
CATEGORY_INSTRUMENT = "instrument"
CATEGORY_SCOPE = "scope"
CATEGORY_CHAMBER = "chamber"
CATEGORY_SCRIPT = "script"
CATEGORY_EXPORT = "export"
CATEGORY_SCHEDULE = "schedule"


@dataclass(frozen=True)
class ActionSpec:
    """受控动作元数据（AIAssist_Architecture.md §8）。"""

    name: str
    description: str
    parameters_schema: dict = field(default_factory=dict)
    risk_level: str = "low"
    require_confirmation: bool = False
    result_schema: dict = field(default_factory=dict)
    category: str = CATEGORY_QUERY

    def to_tool(self) -> dict[str, Any]:
        """渲染为 OpenAI tools 中的一个 function 描述。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema
                or {"type": "object", "properties": {}},
            },
        }


class ActionRegistry:
    """动作注册表：注册 / 查找 / 渲染 tools。"""

    def __init__(self) -> None:
        self._specs: dict[str, ActionSpec] = {}

    def register(self, spec: ActionSpec) -> None:
        if spec.name in self._specs:
            logger.warning("Action 已存在，覆盖注册: %s", spec.name)
        self._specs[spec.name] = spec

    def register_many(self, specs) -> None:
        for spec in specs:
            self.register(spec)

    def get(self, name: str) -> ActionSpec | None:
        return self._specs.get(name)

    def has(self, name: str) -> bool:
        return name in self._specs

    def all_specs(self) -> list[ActionSpec]:
        return list(self._specs.values())

    def names(self) -> list[str]:
        return list(self._specs.keys())

    def to_tools(self) -> list[dict[str, Any]]:
        """渲染为 OpenAI tools 列表（原生 function calling）。"""
        return [spec.to_tool() for spec in self._specs.values()]

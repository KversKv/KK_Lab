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

from core.ai.page_contract import ACTION_CAPABILITY_MAP
from log_config import get_logger

logger = get_logger(__name__)

CATEGORY_QUERY = "query"
CATEGORY_UI = "ui"
CATEGORY_TEST_CONFIG = "test_config"
CATEGORY_TEST_SEQUENCE = "test_sequence"
CATEGORY_SERIAL = "serial"
CATEGORY_INSTRUMENT = "instrument"
CATEGORY_I2C = "i2c"
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

    def to_tools(
        self, capabilities: set[str] | None = None
    ) -> list[dict[str, Any]]:
        """渲染为 OpenAI tools 列表（原生 function calling）。

        Args:
            capabilities: 当前页面 AI 能力集（CAP_* 常量）。
                - None：不裁剪，返回全量（向后兼容，未注入 getter 的调用方仍可用）；
                - 非 None：按 ACTION_CAPABILITY_MAP 过滤页级动作（test_config/test_sequence
                  类），未列入 map 的通用动作（查询/测量/串口/仪器/导出/调度等）始终保留。
                命中 map 中任一所列能力即保留该动作。
        """
        if capabilities is None:
            return [spec.to_tool() for spec in self._specs.values()]

        caps = set(capabilities)
        tools: list[dict[str, Any]] = []
        for spec in self._specs.values():
            required = ACTION_CAPABILITY_MAP.get(spec.name)
            if required is None:
                # 通用动作，始终保留（只读查询/测量/串口/仪器/导出/调度等）。
                tools.append(spec.to_tool())
                continue
            if any(cap in caps for cap in required):
                tools.append(spec.to_tool())
        return tools

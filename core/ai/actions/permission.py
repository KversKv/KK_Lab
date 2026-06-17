"""PermissionChecker / RiskPolicy（AI_Assist.md §10）。

风险分级与策略：
  - low      : 可直接执行（仍写审计）
  - medium   : 执行前预览/提示，可一键确认
  - high     : 必须弹 ActionConfirmDialog 确认
  - critical : 二次确认；默认禁止 AI 直接执行（仅生成建议由人手动操作）

PermissionChecker 输出一个 RiskDecision（是否允许 / 是否需确认 / 是否禁止），
由上层（AIService / 面板）据此决定弹窗与执行。

本模块纯逻辑，禁 import Qt。
"""
from __future__ import annotations

from dataclasses import dataclass

from core.ai.actions.registry import ActionSpec
from log_config import get_logger

logger = get_logger(__name__)

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
RISK_CRITICAL = "critical"

_RISK_ORDER = {RISK_LOW: 0, RISK_MEDIUM: 1, RISK_HIGH: 2, RISK_CRITICAL: 3}


@dataclass(frozen=True)
class RiskDecision:
    """风险判定结果。"""

    allowed: bool
    require_confirmation: bool
    risk_level: str
    reason: str = ""

    @property
    def blocked(self) -> bool:
        return not self.allowed


class PermissionChecker:
    """按风险等级与配置判定一个动作是否可执行 / 是否需确认。

    allow_critical=False 时，critical 动作一律禁止 AI 直接执行（默认）。
    require_confirm_high=True 时，high 动作必须确认（来自 AISettings）。
    """

    def __init__(
        self,
        *,
        require_confirm_high: bool = True,
        allow_critical: bool = False,
    ) -> None:
        self._require_confirm_high = bool(require_confirm_high)
        self._allow_critical = bool(allow_critical)

    def check(self, spec: ActionSpec) -> RiskDecision:
        risk = spec.risk_level or RISK_LOW
        if risk == RISK_CRITICAL and not self._allow_critical:
            return RiskDecision(
                allowed=False,
                require_confirmation=True,
                risk_level=risk,
                reason="critical 风险动作默认禁止 AI 直接执行，请人工手动操作。",
            )

        require = bool(spec.require_confirmation)
        if risk == RISK_HIGH and self._require_confirm_high:
            require = True
        if risk == RISK_CRITICAL:
            require = True

        return RiskDecision(
            allowed=True,
            require_confirmation=require,
            risk_level=risk,
            reason="",
        )

    @staticmethod
    def risk_rank(risk_level: str) -> int:
        return _RISK_ORDER.get(risk_level, 0)

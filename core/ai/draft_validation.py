"""草案本地校验（AI_Assist.md §12，阶段 3 任务 3.4；F5.3）。

把 AI 产出的序列草案接到现有内核：
  - core/custom_test/serialization.load_sequence_data 反序列化 + 迁移；
  - core/custom_test/validation.preflight_validate 做运行前校验
    （可选接 InstrumentResolver 做仪器解析校验）。

支持两类来源：
  - ScriptDraft：完整序列往返（validate_script_draft）；
  - SequencePatch + base v2 dict：增量 patch（validate_sequence_patch）。

复用现有 error/warning 语义：error 阻止 apply，warning 允许确认继续。

本模块纯逻辑，禁 import Qt。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.ai.schemas import ScriptDraft
from core.ai.sequence_patch import SequencePatch, apply_patch
from core.custom_test.serialization import load_sequence_data
from core.custom_test.validation import preflight_validate
from log_config import get_logger

logger = get_logger(__name__)


@dataclass
class DraftValidationResult:
    """草案校验结果（统一 error/warning 二元语义）。"""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    nodes: list[Any] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    @property
    def can_apply(self) -> bool:
        """无 error 即可 apply（warning 可确认继续）。"""
        return not self.errors


def validate_sequence_data(
    sequence_data: dict[str, Any], resolver: Any = None
) -> DraftValidationResult:
    """校验一个 v2 序列 dict：反序列化 issue + preflight issue 合并。

    resolver 非空时，preflight 额外做仪器解析校验（缺失仪器 → error/warning）。
    """
    result = DraftValidationResult()
    try:
        document = load_sequence_data(sequence_data)
    except Exception as exc:  # noqa: BLE001 - 反序列化任意异常归为 error
        logger.warning("序列反序列化失败", exc_info=True)
        result.errors.append(f"序列反序列化失败：{exc}")
        return result

    for issue in document.issues:
        line = issue.format()
        if issue.severity == "error":
            result.errors.append(line)
        else:
            result.warnings.append(line)

    result.nodes = list(document.nodes)

    try:
        preflight = preflight_validate(
            document.nodes,
            resolver=resolver,
            sequence_version=document.version,
        )
    except Exception as exc:  # noqa: BLE001 - preflight 任意异常归为 error
        logger.warning("序列 preflight 校验失败", exc_info=True)
        result.errors.append(f"preflight 校验失败：{exc}")
        return result

    for issue in preflight.issues:
        line = issue.format()
        if issue.severity == "error":
            result.errors.append(line)
        else:
            result.warnings.append(line)

    return result


def validate_script_draft(draft: ScriptDraft, resolver: Any = None) -> DraftValidationResult:
    """校验 Custom Test 序列草案（完整序列往返）。"""
    return validate_sequence_data(draft.to_sequence_data(), resolver=resolver)


def validate_sequence_patch(
    base_sequence_data: dict[str, Any],
    patch: SequencePatch,
    resolver: Any = None,
) -> DraftValidationResult:
    """校验 patch：先应用于 base v2 dict，再走 validate_sequence_data。

    patch 应用层面的 issue（定位失败/越界等）合并进结果；patch error 即阻止 apply。
    """
    apply_result = apply_patch(base_sequence_data, patch)
    result = validate_sequence_data(apply_result.sequence_data, resolver=resolver)
    for issue in apply_result.issues:
        line = issue.format()
        if issue.severity == "error":
            result.errors.append(line)
        else:
            result.warnings.append(line)
    return result

"""Orchestrator 仪器 capability 解析与运行时 adapter。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

from debug_config import DEBUG_MOCK
from log_config import get_logger
from core.orchestrator.adapters import (
    I2CAdapter,
    RuntimeInstrumentAdapter,
    UARTAdapter,
    create_mock_adapter,
)
from core.orchestrator.nodes.base import BaseNode

logger = get_logger(__name__)


@dataclass(frozen=True)
class CapabilityRequirement:
    runtime_key: str
    role: str
    manager_capability_alternatives: tuple[frozenset[str], ...] = ()
    unsupported_reason: str = ""


@dataclass
class MissingInstrument:
    runtime_key: str
    capabilities: tuple[str, ...]
    message: str
    source: str = "missing"
    busy_owner: str = ""


@dataclass
class ResolvedInstrument:
    runtime_key: str
    adapter: object
    source: str
    capabilities: tuple[str, ...] = ()
    session_id: str = ""
    display_name: str = ""
    owned: bool = False

    @property
    def instance(self) -> object:
        return getattr(self.adapter, "instance", self.adapter)

    def close_if_owned(self) -> None:
        if not self.owned:
            return
        target = self.instance
        close = getattr(target, "close", None)
        if callable(close):
            try:
                close()
            except Exception as exc:
                logger.warning(
                    "Close owned Orchestrator instrument failed (%s): %s",
                    self.runtime_key,
                    exc,
                    exc_info=True,
                )
        self.owned = False


@dataclass
class ResolvedInstruments:
    instruments: Dict[str, ResolvedInstrument] = field(default_factory=dict)
    missing: List[MissingInstrument] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    lease_session_ids: List[str] = field(default_factory=list)

    def as_instrument_dict(self) -> Dict[str, object]:
        return {key: item.adapter for key, item in self.instruments.items()}

    def close_owned(self) -> None:
        for item in self.instruments.values():
            item.close_if_owned()


_CAPABILITY_REQUIREMENTS: Dict[str, CapabilityRequirement] = {
    "power_analyzer.set_voltage": CapabilityRequirement(
        "n6705c", "power_analyzer", (frozenset({"set_voltage"}),),
    ),
    "power_analyzer.set_current_limit": CapabilityRequirement(
        "n6705c", "power_analyzer", (frozenset({"set_current_limit"}),),
    ),
    "power_analyzer.measure": CapabilityRequirement(
        "n6705c", "power_analyzer",
        (frozenset({"measure_current", "measure_voltage"}),),
    ),
    "scope.basic": CapabilityRequirement("scope", "scope"),
    "scope.measurement": CapabilityRequirement(
        "scope", "scope", (frozenset({"measure_waveform"}),),
    ),
    "scope.frequency": CapabilityRequirement(
        "scope", "scope",
        (
            frozenset({"measure_frequency"}),
            frozenset({"dvm_frequency"}),
            frozenset({"measure_waveform"}),
        ),
    ),
    "scope.dvm": CapabilityRequirement(
        "scope", "scope", (frozenset({"dvm_frequency"}),),
    ),
    "chamber.temperature": CapabilityRequirement("chamber", "chamber"),
    "chamber.stabilize_wait": CapabilityRequirement(
        "chamber", "chamber", (frozenset({"stabilize_wait"}),),
    ),
    "counter.frequency": CapabilityRequirement(
        "freq_counter", "counter", (frozenset({"measure_frequency"}),),
    ),
    "i2c.register": CapabilityRequirement(
        "i2c", "i2c_adapter", (frozenset({"i2c_read", "i2c_write"}),),
    ),
    "uart.session": CapabilityRequirement(
        "uart", "serial", (frozenset({"serial_tx", "serial_rx"}),),
    ),
    "mcu_io.gpio": CapabilityRequirement("mcu_io", "mcu_io"),
    "ch9114f.gpio": CapabilityRequirement("ch9114f", "ch9114f"),
    "rf_analyzer.basic": CapabilityRequirement(
        "rf_analyzer",
        "rf_analyzer",
        unsupported_reason="RF Analyzer/CMW270 尚未接入 InstrumentManager。",
    ),
}


def capability_instrument_key(capability: str) -> str:
    requirement = _CAPABILITY_REQUIREMENTS.get(capability)
    if requirement is not None:
        return requirement.runtime_key
    return capability.split(".", 1)[0]


def collect_required_capabilities(nodes: Sequence[BaseNode]) -> set[str]:
    required: set[str] = set()

    def _walk(items: Iterable[BaseNode]) -> None:
        for node in items:
            required.update(node.required_instruments())
            if node.children:
                _walk(node.children)

    _walk(nodes)
    return required


def collect_required_instrument_keys(nodes: Sequence[BaseNode]) -> set[str]:
    return {
        capability_instrument_key(capability)
        for capability in collect_required_capabilities(nodes)
    }


class InstrumentResolver:
    """把节点 capability 解析成 Orchestrator runtime adapter。"""

    def __init__(
        self,
        instrument_manager: object | None = None,
        legacy_sources: Optional[Dict[str, object]] = None,
        legacy_source_labels: Optional[Dict[str, str]] = None,
        owner: str = "orchestrator",
        allow_i2c_autoconnect: bool = True,
        allow_mock: Optional[bool] = None,
    ) -> None:
        self.instrument_manager = instrument_manager
        self.legacy_sources = legacy_sources or {}
        self.legacy_source_labels = legacy_source_labels or {}
        self.owner = owner
        self.allow_i2c_autoconnect = allow_i2c_autoconnect
        self.allow_mock = DEBUG_MOCK if allow_mock is None else bool(allow_mock)

    def resolve(self, nodes: Sequence[BaseNode]) -> ResolvedInstruments:
        resolved = ResolvedInstruments()
        required_by_key: Dict[str, set[str]] = {}

        for capability in collect_required_capabilities(nodes):
            requirement = _CAPABILITY_REQUIREMENTS.get(capability)
            runtime_key = capability_instrument_key(capability)
            if requirement and requirement.unsupported_reason:
                resolved.missing.append(MissingInstrument(
                    runtime_key=runtime_key,
                    capabilities=(capability,),
                    message=requirement.unsupported_reason,
                    source="unsupported",
                ))
                continue
            required_by_key.setdefault(runtime_key, set()).add(capability)

        for runtime_key, capabilities in sorted(required_by_key.items()):
            item = self._resolve_from_manager(runtime_key, capabilities, resolved)
            if item is None:
                item = self._resolve_from_legacy(runtime_key, capabilities)
            if item is None and self.allow_mock:
                item = self._resolve_from_mock(runtime_key, capabilities)
            if item is None and runtime_key == "i2c" and self.allow_i2c_autoconnect:
                item = self._auto_create_i2c(capabilities, resolved)

            if item is None:
                if any(m.runtime_key == runtime_key for m in resolved.missing):
                    continue
                resolved.missing.append(MissingInstrument(
                    runtime_key=runtime_key,
                    capabilities=tuple(sorted(capabilities)),
                    message=self._missing_message(runtime_key, capabilities),
                ))
                continue

            resolved.instruments[runtime_key] = item
            if item.source == "manager" and item.session_id:
                resolved.lease_session_ids.append(item.session_id)
            elif item.source != "manager":
                resolved.warnings.append(
                    f"{runtime_key}: 使用 {item.source} fallback，无法通过 InstrumentLease 独占。"
                )

        return resolved

    def _resolve_from_manager(
        self,
        runtime_key: str,
        capabilities: set[str],
        resolved: ResolvedInstruments,
    ) -> ResolvedInstrument | None:
        if self.instrument_manager is None:
            return None

        requirement = self._combined_requirement(runtime_key, capabilities)
        if requirement is None:
            return None

        sessions_fn = getattr(self.instrument_manager, "sessions", None)
        get_session = getattr(self.instrument_manager, "get_session", None)
        if not callable(sessions_fn) or not callable(get_session):
            return None

        snapshots = [
            snapshot for snapshot in sessions_fn()
            if getattr(snapshot, "connected", False)
            and getattr(snapshot, "role", "") == requirement.role
        ]
        matching = [
            snapshot for snapshot in snapshots
            if self._snapshot_supports(snapshot, capabilities)
        ]
        if not matching:
            return None

        free = [
            snapshot for snapshot in matching
            if not getattr(snapshot, "busy", False)
            or getattr(snapshot, "busy_owner", "") == self.owner
        ]
        if not free:
            first = matching[0]
            busy_owner = getattr(first, "busy_owner", "")
            resolved.missing.append(MissingInstrument(
                runtime_key=runtime_key,
                capabilities=tuple(sorted(capabilities)),
                message=(
                    f"{runtime_key} 对应 session 正被占用"
                    + (f"（owner={busy_owner}）" if busy_owner else "")
                ),
                source="busy",
                busy_owner=busy_owner,
            ))
            return None

        snapshot = free[0]
        session = get_session(snapshot.session_id)
        instance = getattr(session, "instance", None) if session else None
        if instance is None:
            return None

        return ResolvedInstrument(
            runtime_key=runtime_key,
            adapter=self._wrap_adapter(runtime_key, instance),
            source="manager",
            capabilities=tuple(sorted(capabilities)),
            session_id=snapshot.session_id,
            display_name=getattr(snapshot, "display_name", "") or snapshot.session_id,
        )

    def _resolve_from_legacy(
        self,
        runtime_key: str,
        capabilities: set[str],
    ) -> ResolvedInstrument | None:
        instance = self.legacy_sources.get(runtime_key)
        if instance is None:
            return None
        if not self._legacy_source_available(runtime_key, instance):
            return None
        return ResolvedInstrument(
            runtime_key=runtime_key,
            adapter=self._wrap_adapter(runtime_key, instance),
            source=self.legacy_source_labels.get(runtime_key, "legacy"),
            capabilities=tuple(sorted(capabilities)),
        )

    def _auto_create_i2c(
        self,
        capabilities: set[str],
        resolved: ResolvedInstruments,
    ) -> ResolvedInstrument | None:
        try:
            from lib.i2c.i2c_interface_x64 import I2CInterface
            i2c = I2CInterface()
            if not i2c.initialize():
                resolved.missing.append(MissingInstrument(
                    runtime_key="i2c",
                    capabilities=tuple(sorted(capabilities)),
                    message="I2CInterface 初始化失败。",
                    source="auto_i2c",
                ))
                return None
            return ResolvedInstrument(
                runtime_key="i2c",
                adapter=I2CAdapter(i2c),
                source="auto_i2c",
                capabilities=tuple(sorted(capabilities)),
                owned=True,
            )
        except Exception as exc:
            logger.error("I2C auto-create failed: %s", exc, exc_info=True)
            resolved.missing.append(MissingInstrument(
                runtime_key="i2c",
                capabilities=tuple(sorted(capabilities)),
                message=f"I2CInterface 自动创建失败: {exc}",
                source="auto_i2c",
            ))
            return None

    def _resolve_from_mock(
        self,
        runtime_key: str,
        capabilities: set[str],
    ) -> ResolvedInstrument | None:
        adapter = create_mock_adapter(runtime_key)
        if adapter is None:
            return None
        return ResolvedInstrument(
            runtime_key=runtime_key,
            adapter=adapter,
            source="mock",
            capabilities=tuple(sorted(capabilities)),
            display_name=f"Mock {runtime_key}",
            owned=True,
        )

    def _combined_requirement(
        self,
        runtime_key: str,
        capabilities: set[str],
    ) -> CapabilityRequirement | None:
        for capability in capabilities:
            requirement = _CAPABILITY_REQUIREMENTS.get(capability)
            if requirement is not None and requirement.runtime_key == runtime_key:
                return requirement
        return None

    def _snapshot_supports(self, snapshot: object, capabilities: set[str]) -> bool:
        session_caps = set(getattr(snapshot, "capabilities", frozenset()))
        for capability in capabilities:
            requirement = _CAPABILITY_REQUIREMENTS.get(capability)
            if requirement is None:
                return False
            alternatives = requirement.manager_capability_alternatives
            if alternatives and not any(alt.issubset(session_caps) for alt in alternatives):
                return False
        return True

    def _wrap_adapter(self, runtime_key: str, instance: object) -> object:
        if runtime_key == "i2c":
            return I2CAdapter(instance)
        if runtime_key == "uart":
            return UARTAdapter(instance)
        return RuntimeInstrumentAdapter(instance)

    def _legacy_source_available(self, runtime_key: str, instance: object) -> bool:
        if runtime_key == "uart" and hasattr(instance, "is_serial_connected"):
            return bool(instance.is_serial_connected())
        is_connected = getattr(instance, "is_connected", None)
        if callable(is_connected):
            try:
                return bool(is_connected())
            except Exception:
                return True
        if isinstance(is_connected, bool):
            return is_connected
        return True

    def _missing_message(self, runtime_key: str, capabilities: set[str]) -> str:
        cap_text = ", ".join(sorted(capabilities))
        return f"缺少 {runtime_key} 运行时仪器或能力: {cap_text}"

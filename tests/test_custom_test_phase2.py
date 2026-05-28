import os
import sys
import unittest
from dataclasses import dataclass, field

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.custom_test.context import ExecutionContext
from core.custom_test.nodes import (
    LoopRange,
    N6705CMeasure,
    PromptUser,
    ScopeGetDvmDC,
)
from core.custom_test.resolver import InstrumentResolver, collect_required_capabilities
from core.custom_test.validation import preflight_validate


class FakeN6705C:
    def measure_current(self, channel):
        return 0.001 * channel

    def measure_voltage(self, channel):
        return 3.8


@dataclass
class FakeSnapshot:
    session_id: str
    role: str
    capabilities: frozenset[str] = field(default_factory=frozenset)
    connected: bool = True
    busy: bool = False
    busy_owner: str = ""
    display_name: str = ""


@dataclass
class FakeSession:
    session_id: str
    role: str
    capabilities: set[str]
    instance: object
    connected: bool = True
    busy: bool = False
    busy_owner: str = ""
    display_name: str = ""

    def to_snapshot(self):
        return FakeSnapshot(
            session_id=self.session_id,
            role=self.role,
            capabilities=frozenset(self.capabilities),
            connected=self.connected,
            busy=self.busy,
            busy_owner=self.busy_owner,
            display_name=self.display_name,
        )


class FakeLease:
    def __init__(self, manager, session_id, owner):
        self.manager = manager
        self.session_id = session_id
        self.owner = owner
        self.acquired = False

    def acquire(self):
        self.acquired = self.manager.try_set_busy(self.session_id, True, self.owner)
        return self.acquired

    def release(self):
        if self.acquired:
            self.manager.try_set_busy(self.session_id, False, self.owner)
            self.acquired = False


class FakeManager:
    def __init__(self, session):
        self.session = session

    def sessions(self):
        return [self.session.to_snapshot()]

    def get_session(self, session_id):
        if session_id == self.session.session_id:
            return self.session
        return None

    def create_lease(self, session_id, owner):
        return FakeLease(self, session_id, owner)

    def try_set_busy(self, session_id, busy, owner=""):
        session = self.get_session(session_id)
        if session is None:
            return False
        if busy and session.busy and session.busy_owner != owner:
            return False
        session.busy = busy
        session.busy_owner = owner if busy else ""
        return True


class CustomTestPhase2Test(unittest.TestCase):

    def test_nodes_declare_runtime_capabilities(self):
        self.assertIn("power_analyzer.measure", N6705CMeasure.required_capabilities)
        self.assertIn("scope.dvm", ScopeGetDvmDC.required_capabilities)
        self.assertEqual(LoopRange.required_capabilities, ())

    def test_resolver_uses_manager_session_and_context_lease(self):
        session = FakeSession(
            session_id="n6705c:A",
            role="power_analyzer",
            capabilities={"measure_current", "measure_voltage", "set_voltage"},
            instance=FakeN6705C(),
            connected=True,
        )
        manager = FakeManager(session)
        sequence = [N6705CMeasure()]

        resolved = InstrumentResolver(manager).resolve(sequence)

        self.assertEqual(resolved.missing, [])
        self.assertIn("n6705c", resolved.instruments)
        self.assertEqual(resolved.instruments["n6705c"].source, "manager")
        self.assertEqual(resolved.lease_session_ids, ["n6705c:A"])

        context = ExecutionContext(
            instrument_manager=manager,
            instruments=resolved.as_instrument_dict(),
            resolved_instruments=resolved,
            lease_session_ids=resolved.lease_session_ids,
        )
        context.acquire_leases()
        self.assertTrue(session.busy)
        self.assertEqual(session.busy_owner, "custom_test")
        context.release_runtime_resources()
        self.assertFalse(session.busy)

    def test_preflight_reports_missing_required_instrument(self):
        result = preflight_validate([N6705CMeasure()], resolver=InstrumentResolver())

        self.assertTrue(result.has_errors)
        self.assertTrue(any("n6705c" in issue.message for issue in result.errors))

    def test_preflight_reports_unsupported_and_invalid_params(self):
        loop = LoopRange(step=0)
        prompt = PromptUser()

        result = preflight_validate([loop, prompt], resolver=InstrumentResolver())

        self.assertTrue(any("step" in issue.message for issue in result.errors))
        self.assertTrue(any("PromptUser" in issue.format() for issue in result.errors))

    def test_collect_required_capabilities_walks_children(self):
        loop = LoopRange()
        loop.children.append(N6705CMeasure())

        self.assertEqual(
            collect_required_capabilities([loop]),
            {"power_analyzer.measure"},
        )


if __name__ == "__main__":
    unittest.main()

# 临时验证：ChamberConnectionMixin 构造期补拉 manager 已有会话
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QFrame, QVBoxLayout

from ui.modules.chamber_module_frame import ChamberConnectionMixin


class _FakeSession:
    def __init__(self):
        self.session_id = "vt6002:default"
        self.instrument_type = "vt6002"
        self.role = "chamber"
        self.resource = "COM9"
        self.connected = True
        self.instance = object()


class _FakeSnap:
    def __init__(self, session_id):
        self.session_id = session_id


class _FakeManager(QObject):
    session_connected = Signal(str)
    session_disconnected = Signal(str)
    connection_failed = Signal(str, str)

    def __init__(self, session):
        super().__init__()
        self._session = session

    def find_sessions(self, role="", connected_only=True):
        if role == "chamber" and self._session.connected:
            return [_FakeSnap(self._session.session_id)]
        return []

    def get_session(self, session_id):
        if session_id == self._session.session_id:
            return self._session
        return None


class _Widget(ChamberConnectionMixin, QFrame):
    chamber_connection_changed = Signal(bool)

    def __init__(self, manager):
        super().__init__()
        self.init_chamber_connection(instrument_manager=manager)
        layout = QVBoxLayout(self)
        self.build_chamber_connection_widgets(layout)
        self.bind_chamber_signals()


def main():
    app = QApplication([])
    session = _FakeSession()
    mgr = _FakeManager(session)

    # 场景1：先连接（manager 已有会话）再建页面 → 构造期应补拉为已连接
    w = _Widget(mgr)
    assert w.is_chamber_connected is True, "init 补拉失败"
    assert w.chamber is session.instance
    assert w.current_chamber_session_id == "vt6002:default"
    assert "COM9" in w.chamber_status_label.text(), w.chamber_status_label.text()
    assert w.chamber_connect_btn.text() == "Disconnect"
    assert not w.chamber_search_btn.isEnabled()
    print("场景1 构造期补拉: OK ->", w.chamber_status_label.text())

    # 场景2：manager 断开后 sync_chamber_from_manager 应回落为未连接
    session.connected = False
    w.sync_chamber_from_manager()
    assert w.is_chamber_connected is False
    assert w.chamber is None
    assert "Not Connected" in w.chamber_status_label.text()
    assert w.chamber_connect_btn.text() == "Connect"
    print("场景2 拉取断开态: OK ->", w.chamber_status_label.text())

    # 场景3：重新连接后再次拉取 → 恢复已连接且 emit 变化
    session.connected = True
    seen = []
    w.chamber_connection_changed.connect(seen.append)
    w.sync_chamber_from_manager()
    assert w.is_chamber_connected is True and seen == [True], seen
    print("场景3 重连拉取+emit: OK ->", w.chamber_status_label.text())

    # 场景4：无会话时重复拉取不应误 emit
    session.connected = False
    w.sync_chamber_from_manager()
    seen.clear()
    w.sync_chamber_from_manager()
    assert seen == [], seen
    print("场景4 无变化不重复 emit: OK")

    print("ALL PASS")
    app.quit()


if __name__ == "__main__":
    main()

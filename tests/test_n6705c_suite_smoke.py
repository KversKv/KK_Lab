#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N6705CSuiteWindow 冒烟：建窗 → 切换两页 → 自动关闭。"""

import sys
import os

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, QTimer, Signal

from ui.pages.power_analyzer.power_analyzer_suite_ui import (
    N6705CSuiteWindow, N6705CTop,
)


@pytest.mark.qt
def test_it2705_eight_channel_ui_and_model(monkeypatch):
    from instruments.mock.mock_instruments import MockIT2705
    from ui.pages.power_analyzer.datalog.datalog_ui import N6705CDatalogUI
    from ui.pages.power_analyzer.widgets import IT2705_CHANNEL_ACCENTS

    monkeypatch.setattr(
        N6705CDatalogUI, "_auto_connect_enabled_cards", lambda self: None
    )
    app = QApplication.instance() or QApplication([])
    top = N6705CTop()
    top.connect_a("MOCK::IT2705", MockIT2705("MOCK::IT2705"))
    window = N6705CSuiteWindow(n6705c_top=top)

    analyser = window.analyser_page
    assert "IT2705" in analyser.conn_widgets["A"]["status"].text()
    assert analyser._channels_for_device("A") == tuple(range(1, 9))
    assert len(analyser.channel_tab_buttons) == 8
    assert len(analyser.batch_voltage_inputs["A"]) == 8
    assert len(analyser.batch_current_inputs["A"]) == 8
    assert len(analyser.ct_channel_cards) == 8

    datalog = window.datalog_page
    assert datalog.slot_frames["A"].property("assigned_model") == "IT2705"
    assert len(datalog.ch_current_cbs_a) == 8
    assert len(datalog.ch_voltage_cbs_a) == 8
    assert len(datalog.ch_power_cbs_a) == 8

    for channel, accent in enumerate(IT2705_CHANNEL_ACCENTS, start=1):
        assert analyser._channel_theme("A", channel)["accent"] == accent
        value_label = analyser.ct_channel_cards[("A", channel)]["value_label"]
        assert accent in value_label.styleSheet()
        assert datalog.ch_current_cbs_a[channel - 1].property("ch_color") == accent
        assert datalog._color_for_data_label(f"A-I{channel}") == accent

    window.close()
    window.deleteLater()
    app.processEvents()


@pytest.mark.qt
def test_module_whitelist_hides_channels_across_both_pages(monkeypatch):
    from instruments.mock.mock_instruments import MockIT2705, MockN6705C
    from ui.pages.power_analyzer.datalog.datalog_ui import N6705CDatalogUI
    from ui.pages.power_analyzer.datalog import view_recording

    monkeypatch.setattr(
        N6705CDatalogUI, "_auto_connect_enabled_cards", lambda self: None
    )
    app = QApplication.instance() or QApplication([])

    keysight = MockN6705C()
    keysight.channel_module_models = {
        1: "N6781A", 2: "N6784A", 3: "N6782A", 4: "",
    }
    itech = MockIT2705("MOCK::IT2705")
    itech.channel_module_models = {
        1: "IT27814", 2: "IT27814E", 3: "IT27812", 4: "",
        5: "NONE", 6: "IT27814E", 7: "IT27814", 8: "",
    }

    top = N6705CTop()
    top.connect_a("MOCK::N6705C", keysight)
    top.connect_b("MOCK::IT2705", itech)
    window = N6705CSuiteWindow(n6705c_top=top)
    analyser = window.analyser_page
    datalog = window.datalog_page

    assert analyser._channel_theme("A", 1)["accent"] == "#d4a514"
    assert analyser._channel_theme("B", 1)["accent"] == "#4079fa"
    assert datalog.ch_current_cbs_a[0].property("ch_color") == "#d4a514"
    assert datalog.ch_current_cbs_b[0].property("ch_color") == "#4079fa"
    assert datalog._color_for_data_label("A-I1") == "#d4a514"
    assert datalog._color_for_data_label("B-I1") == "#4079fa"

    assert analyser._supported_channels_for_device("A") == (1, 2)
    assert analyser._supported_channels_for_device("B") == (1, 2, 6, 7)
    expected_tabs = {"A": {1, 2}, "B": {1, 2, 6, 7}}
    for btn in analyser.channel_tab_buttons:
        label = btn.property("device_label")
        channel = btn.property("channel")
        assert btn.isEnabled() == (channel in expected_tabs[label])
        assert btn.isHidden() == (channel not in expected_tabs[label])
        assert btn.isChecked() == (label == "A" and channel == 1)
    assert not analyser.setting_frame.isHidden()

    for label, channel, btn in analyser.batch_channel_buttons:
        supported = channel in expected_tabs[label]
        assert btn.isEnabled() == supported
        assert btn.isHidden() == (not supported)
        if not supported:
            assert not btn.isChecked()
    for label, inputs in (
        ("A", analyser.batch_voltage_inputs["A"]),
        ("A", analyser.batch_current_inputs["A"]),
        ("B", analyser.batch_voltage_inputs["B"]),
        ("B", analyser.batch_current_inputs["B"]),
    ):
        for channel, edit in enumerate(inputs, 1):
            assert edit.isHidden() == (channel not in expected_tabs[label])
    analyser.batch_channel_buttons[2][2].setChecked(True)
    assert 3 not in analyser._get_selected_batch_channels("A")

    for (label, channel), card in analyser.ct_channel_cards.items():
        supported = channel in expected_tabs[label]
        assert card["checkbox"].isEnabled() == supported
        assert card["card"].isHidden() == (not supported)
        if not supported:
            assert not card["checkbox"].isChecked()

    for label, groups in (
        ("A", (datalog.ch_current_cbs_a, datalog.ch_voltage_cbs_a, datalog.ch_power_cbs_a)),
        ("B", (datalog.ch_current_cbs_b, datalog.ch_voltage_cbs_b, datalog.ch_power_cbs_b)),
    ):
        for group in groups:
            for index, btn in enumerate(group, 1):
                supported = index in expected_tabs[label]
                assert btn.isEnabled() == supported
                assert btn.property("scale_edit").isEnabled() == supported
                assert btn.property("offset_edit").isEnabled() == supported
                channel_frame = btn.parentWidget().parentWidget()
                assert channel_frame.isHidden() == (not supported)

    captured = {}

    class FakeWorker(QObject):
        data_ready = Signal(dict)
        dlog_raw_ready = Signal(list)
        progress_update = Signal(int, str)
        finished = Signal()
        error = Signal(str)

        def __init__(self, units, channels, labels, record_type, period, monitor,
                     debug=False, voltage_channels_per_unit=None):
            super().__init__()
            captured.update(
                units=units,
                channels=channels,
                labels=labels,
                voltage_channels=voltage_channels_per_unit,
            )

        def moveToThread(self, thread):
            pass

        def run(self):
            pass

        def stop(self):
            pass

    class FakeThread(QObject):
        started = Signal()
        finished = Signal()

        def isRunning(self):
            return False

        def start(self):
            pass

        def quit(self):
            pass

        def wait(self, timeout=None):
            return True

    monkeypatch.setattr(view_recording, "_DatalogWorker", FakeWorker)
    monkeypatch.setattr(view_recording, "QThread", FakeThread)

    datalog.ch_current_cbs_a[0].setChecked(True)
    datalog.ch_voltage_cbs_a[1].setChecked(True)
    datalog.ch_current_cbs_b[0].setChecked(True)
    datalog.ch_voltage_cbs_b[1].setChecked(True)
    datalog.ch_power_cbs_b[5].setChecked(True)
    datalog.ch_current_cbs_a[2].setChecked(True)
    datalog.ch_voltage_cbs_b[2].setChecked(True)
    datalog._start_recording()

    assert captured["units"] == [keysight, itech]
    assert captured["labels"] == ["A", "B"]
    assert captured["channels"] == [[1], [1, 6]]
    assert captured["voltage_channels"] == [[2], [2, 6]]
    assert not datalog.ch_current_cbs_a[2].isChecked()
    assert not datalog.ch_voltage_cbs_b[2].isChecked()

    datalog._record_thread = None
    datalog._record_worker = None
    datalog._update_recording_button_state(False)
    keysight.channel_module_models = {channel: "" for channel in range(1, 5)}
    itech.channel_module_models = {channel: "NONE" for channel in range(1, 9)}
    analyser._rebuild_dynamic_sections()
    datalog._refresh_channel_config(force=True)

    assert not analyser._supported_channels_for_device("A")
    assert not analyser._supported_channels_for_device("B")
    assert all(not btn.isEnabled() for btn in analyser.channel_tab_buttons)
    assert all(btn.isHidden() for btn in analyser.channel_tab_buttons)
    assert all(not btn.isChecked() for btn in analyser.channel_tab_buttons)
    assert analyser.setting_frame.isHidden()
    assert all(button.isHidden() for _, _, button in analyser.batch_channel_buttons)
    assert all(card["card"].isHidden() for card in analyser.ct_channel_cards.values())
    assert all(
        not btn.isEnabled() and btn.parentWidget().parentWidget().isHidden()
        for group in (
            datalog.ch_current_cbs_a, datalog.ch_voltage_cbs_a, datalog.ch_power_cbs_a,
            datalog.ch_current_cbs_b, datalog.ch_voltage_cbs_b, datalog.ch_power_cbs_b,
        )
        for btn in group
    )
    datalog._restore_channel_toggle_states({
        key: True for key, _ in datalog._iter_channel_toggle_buttons()
    })
    assert all(
        not btn.isChecked() for _, btn in datalog._iter_channel_toggle_buttons()
    )

    window.close()
    window.deleteLater()
    app.processEvents()


def main():
    app = QApplication(sys.argv)

    from core.instruments import InstrumentManager
    manager = InstrumentManager()
    top = N6705CTop()
    top.set_instrument_manager(manager)

    w = N6705CSuiteWindow(n6705c_top=top, instrument_manager=manager)
    w.setWindowTitle("Power Control")
    w.resize(1440, 900)
    w.show()

    assert w.current_page_key() == "analyser", w.current_page_key()

    def _check():
        w.switch_page("datalog")
        assert w.current_page_key() == "datalog"
        w.switch_page("analyser")
        assert w.current_page_key() == "analyser"
        print("SMOKE_OK")

    QTimer.singleShot(1500, _check)
    QTimer.singleShot(3000, app.quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

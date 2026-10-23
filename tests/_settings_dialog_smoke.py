# -*- coding: utf-8 -*-
"""n6705c_settings_dialog 无头冒烟测试（临时调试用）。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from ui.pages.n6705c_power_analyzer import n6705c_settings_dialog as m


def test_settings_roundtrip():
    cfg = m.load_datalog_app_settings()
    assert cfg["auto_connect_enabled"] is True
    assert cfg["dlog_save"]["name_template"] == "dlog_{datetime}"
    cfg["dlog_save"]["next_seq"] = 42
    assert m.save_datalog_app_settings(cfg)
    cfg2 = m.load_datalog_app_settings()
    assert cfg2["dlog_save"]["next_seq"] == 42
    # 还原，避免污染开发配置
    cfg["dlog_save"]["next_seq"] = 1
    assert m.save_datalog_app_settings(cfg)
    print("settings roundtrip OK")


def test_waveform_params():
    p = m.waveform_summary_params()
    assert p["max_stages"] >= 1 and p["lttb_threshold"] >= 100 and p["pelt_max_n"] >= 100
    print("waveform params OK:", p)


def test_auto_save_paths():
    cfg = {"dlog_save": {
        "save_dir": "", "name_template": "dlog_{datetime}",
        "auto_increment": True, "next_seq": 7,
    }}
    paths, next_seq = m.build_auto_save_paths(cfg, 2)
    assert next_seq == 8 and len(paths) == 2
    assert "_007.dlog" in paths[0] and paths[1].endswith("_unit1.dlog")
    print("auto_save inc paths OK:", paths)

    cfg["dlog_save"]["name_template"] = "run_{seq}_{date}"
    paths, next_seq = m.build_auto_save_paths(cfg, 1)
    assert "_007_" in paths[0] and next_seq == 8
    print("auto_save template seq OK:", paths)

    cfg["dlog_save"]["auto_increment"] = False
    paths, next_seq = m.build_auto_save_paths(cfg, 1)
    assert next_seq is None and "{seq}" not in paths[0]
    print("auto_save no-inc paths OK:", paths)


def test_dialog_construction():
    app = QApplication.instance() or QApplication([])
    dialog = m.N6705CSettingsDialog(None)
    assert dialog._tabs.count() == 5
    titles = [dialog._tabs.tabText(i) for i in range(5)]
    assert titles == ["Instruments", "Network Scan", "DLog Save",
                      "Waveform Summary", "About"], titles
    # 仪器编辑子对话框
    edit = m._InstrumentEditDialog(dialog)
    edit._ip_edit.setText("10.0.0.5")
    edit._on_save()
    dev = edit.result_device()
    assert dev["visa_resource"] == "TCPIP0::10.0.0.5::hislip0::INSTR"
    # 应用（无主页面联动，应正常落盘）
    assert dialog._apply_all()
    dialog.deleteLater()
    app.processEvents()
    print("dialog construction OK")


if __name__ == "__main__":
    test_settings_roundtrip()
    test_waveform_params()
    test_auto_save_paths()
    test_dialog_construction()
    print("ALL OK")

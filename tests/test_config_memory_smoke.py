# -*- coding: utf-8 -*-
"""ConfigMemory 冒烟验证（DEBUG 临时脚本，非 pytest 用例）。

覆盖：bind 模式各控件类型 / 动态下拉补项 / 接口模式 / DCDC 真实页面恢复。
运行：.venv\\Scripts\\python.exe tests\\test_config_memory_smoke.py
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QApplication, QWidget, QComboBox, QSpinBox, QDoubleSpinBox,
    QLineEdit, QCheckBox, QTabWidget, QLabel,
)

app = QApplication([])

from ui.widgets.config_memory import ConfigMemory
from ui.resource_path import get_user_data_dir

failures = []


def check(name, cond):
    print(("PASS" if cond else "FAIL"), name)
    if not cond:
        failures.append(name)


def _clean(ns):
    p = os.path.join(get_user_data_dir("page_configs"), f"{ns}.json")
    if os.path.isfile(p):
        os.remove(p)
    return p


# ---- 1. bind 模式全控件类型 ----
path = _clean("test/smoke")
w1 = QWidget()
combo = QComboBox(w1); combo.addItems(["A", "B"])
spin = QSpinBox(w1); spin.setRange(0, 100)
dspin = QDoubleSpinBox(w1)
edit = QLineEdit(w1)
chk = QCheckBox(w1)
tabs = QTabWidget(w1); tabs.addTab(QLabel("1"), "t1"); tabs.addTab(QLabel("2"), "t2")

m1 = ConfigMemory("test/smoke", w1)
m1.bind("combo", combo)
m1.bind("spin", spin)
m1.bind("dspin", dspin)
m1.bind("edit", edit)
m1.bind("chk", chk)
m1.bind("tab", tabs)

combo.setCurrentText("B"); spin.setValue(42); dspin.setValue(3.14)
edit.setText("hello"); chk.setChecked(True); tabs.setCurrentIndex(1)
m1.save_now()
check("json written", os.path.isfile(path))

w2 = QWidget()
combo2 = QComboBox(w2); combo2.addItems(["A", "B"])
spin2 = QSpinBox(w2); spin2.setRange(0, 100)
dspin2 = QDoubleSpinBox(w2)
edit2 = QLineEdit(w2)
chk2 = QCheckBox(w2)
tabs2 = QTabWidget(w2); tabs2.addTab(QLabel("1"), "t1"); tabs2.addTab(QLabel("2"), "t2")
m2 = ConfigMemory("test/smoke", w2)
for key, wdg in [("combo", combo2), ("spin", spin2), ("dspin", dspin2),
                 ("edit", edit2), ("chk", chk2), ("tab", tabs2)]:
    m2.bind(key, wdg)
m2.restore()
check("combo restored", combo2.currentText() == "B")
check("spin restored", spin2.value() == 42)
check("dspin restored", abs(dspin2.value() - 3.14) < 1e-9)
check("edit restored", edit2.text() == "hello")
check("chk restored", chk2.isChecked() is True)
check("tab restored", tabs2.currentIndex() == 1)

# ---- 2. 动态下拉补项（上次值不在当前列表，如 VISA/串口地址）----
w3 = QWidget()
combo3 = QComboBox(w3); combo3.addItems(["TCPIP::OTHER"])
m3 = ConfigMemory("test/smoke", w3)
m3.bind("combo", combo3)
m3.restore()
check("missing item appended", combo3.currentText() == "B")

# ---- 3. 接口模式 ----
_clean("test/smoke_iface")
state = {"a": 1, "b": "x"}
applied = {}
w4 = QWidget()
m4 = ConfigMemory("test/smoke_iface", w4)
m4.bind_interface(lambda: dict(state), lambda cfg: applied.update(cfg))
state["a"] = 7
m4.save_now()
w5 = QWidget()
m5 = ConfigMemory("test/smoke_iface", w5)
applied.clear()
m5.bind_interface(lambda: dict(state), lambda cfg: applied.update(cfg))
m5.restore()
check("iface restored", applied.get("a") == 7)

# ---- 4. DCDC 真实页面：改值 → save_now → 新实例恢复 ----
_clean("pmu_test/dcdc_efficiency")
from ui.pages.pmu_test.pmu_dcdc_efficiency import PMUDCDCEfficiencyUI

page1 = PMUDCDCEfficiencyUI()
page1.vin_start_spin.setValue(3.3)
page1.vin_end_spin.setValue(5.0)
page1.average_cnt_spin.setValue(9)
idx = page1.test_item_combo.findText("Vin Sweep")
if idx >= 0:
    page1.test_item_combo.setCurrentIndex(idx)
page1._config_memory.save_now()

page2 = PMUDCDCEfficiencyUI()
check("dcdc vin_start restored", abs(page2.vin_start_spin.value() - 3.3) < 1e-9)
check("dcdc vin_end restored", abs(page2.vin_end_spin.value() - 5.0) < 1e-9)
check("dcdc average_cnt restored", page2.average_cnt_spin.value() == 9)
if idx >= 0:
    check("dcdc test_item restored", page2.test_item_combo.currentText() == "Vin Sweep")

print("\n%d failure(s)" % len(failures))
sys.exit(1 if failures else 0)

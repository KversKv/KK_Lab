"""临时排查：DCDC 构造热点 cProfile + 一次性成本归属判定。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
app.setStyle("Fusion")

import debug_config  # noqa: E402
from ui.pages.pmu_test.gpadc_test.mixins import acquisition_mixin, execution_mixin  # noqa: E402
from ui.widgets.config_memory import ConfigMemory  # noqa: E402

debug_config.DEBUG_MOCK = True
acquisition_mixin.DEBUG_MOCK = True
execution_mixin.DEBUG_MOCK = True
ConfigMemory.watch = lambda self, widget: None
ConfigMemory.restore = lambda self: None

from ui.pages.pmu_test.pmu_output_voltage import PMUOutputVoltageUI  # noqa: E402
from ui.pages.pmu_test.pmu_dcdc_efficiency import PMUDCDCEfficiencyUI  # noqa: E402

# 先构造轻量页吸收一次性成本，再测 DCDC
t = time.perf_counter()
w0 = PMUOutputVoltageUI()
print(f"PMUOutputVoltageUI (first)      {time.perf_counter() - t:8.3f} s", flush=True)
w0.deleteLater()
app.processEvents()

import cProfile  # noqa: E402
import pstats  # noqa: E402
import io  # noqa: E402

pr = cProfile.Profile()
pr.enable()
t = time.perf_counter()
w = PMUDCDCEfficiencyUI()
dt = time.perf_counter() - t
pr.disable()
print(f"PMUDCDCEfficiencyUI (second)    {dt:8.3f} s", flush=True)
w.deleteLater()
app.processEvents()

s = io.StringIO()
pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(30)
print(s.getvalue())

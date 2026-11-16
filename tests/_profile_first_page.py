"""临时排查：首个页面对象构造吸收的一次性成本热点。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
app.setStyle("Fusion")

import debug_config  # noqa: E402
from ui.widgets.config_memory import ConfigMemory  # noqa: E402

debug_config.DEBUG_MOCK = True
ConfigMemory.watch = lambda self, widget: None
ConfigMemory.restore = lambda self: None

from ui.pages.pmu_test.pmu_output_voltage import PMUOutputVoltageUI  # noqa: E402

import cProfile  # noqa: E402
import pstats  # noqa: E402
import io  # noqa: E402

pr = cProfile.Profile()
pr.enable()
t = time.perf_counter()
w = PMUOutputVoltageUI()
dt = time.perf_counter() - t
pr.disable()
print(f"first page construction: {dt:.3f} s", flush=True)
w.deleteLater()
app.processEvents()

s = io.StringIO()
pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(35)
print(s.getvalue())

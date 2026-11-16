"""临时排查：FT Calibration Check 首次切换耗时分解（offscreen）。"""
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.perf_counter()


def tick(label):
    global T0
    now = time.perf_counter()
    print(f"{label:<52} {now - T0:8.3f} s")
    T0 = now


from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
tick("QApplication")

import debug_config  # noqa: E402
from ui.pages.pmu_test.gpadc_test.mixins import acquisition_mixin, execution_mixin  # noqa: E402
from ui.widgets.config_memory import ConfigMemory  # noqa: E402

debug_config.DEBUG_MOCK = True
acquisition_mixin.DEBUG_MOCK = True
execution_mixin.DEBUG_MOCK = True
ConfigMemory.watch = lambda self, widget: None
ConfigMemory.restore = lambda self: None

from ui.pages.pmu_test.gpadc_test_ui import GPADCTestUI  # noqa: E402
from ui.pages.pmu_test.ft_calib_check_ui import FTCalibCheckUI  # noqa: E402
from ui.pages.pmu_test.pmu_test_ui import PMUTestUI  # noqa: E402

tick("imports")

g = GPADCTestUI()
tick("GPADCTestUI() 单独构造")
g.deleteLater()
app.processEvents()

ft = FTCalibCheckUI()
tick("FTCalibCheckUI() 单独构造（含嵌入 GPADC）")
ft.deleteLater()
app.processEvents()

ui = PMUTestUI()
tick("PMUTestUI() 全量构造（8 子页）")

ui.resize(1600, 900)
ui.show()
app.processEvents()
tick("首次 show + processEvents（默认 tab 0）")

ui.set_current_test("ft_calib_check")
app.processEvents()
tick("首次切换到 FT tab + processEvents")

ui.set_current_test("dcdc_efficiency")
app.processEvents()
tick("切回 tab 0")

ui.set_current_test("ft_calib_check")
app.processEvents()
tick("第二次切换到 FT tab")

# cProfile 分解 FT 容器构造热点
import cProfile  # noqa: E402
import pstats  # noqa: E402
import io  # noqa: E402

pr = cProfile.Profile()
pr.enable()
ft2 = FTCalibCheckUI()
pr.disable()
ft2.deleteLater()
app.processEvents()
s = io.StringIO()
pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(25)
print(s.getvalue())

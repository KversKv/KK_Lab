"""临时排查：真实平台各 PMU 子页构造耗时分解。"""
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


def timeit(label, fn):
    t = time.perf_counter()
    w = fn()
    print(f"{label:<32} {time.perf_counter() - t:8.3f} s", flush=True)
    w.deleteLater()
    app.processEvents()
    return w


from ui.pages.pmu_test.pmu_dcdc_efficiency import PMUDCDCEfficiencyUI  # noqa: E402
from ui.pages.pmu_test.pmu_output_voltage import PMUOutputVoltageUI  # noqa: E402
from ui.pages.pmu_test.pmu_isGain_ui import PMUIsGainUI  # noqa: E402
from ui.pages.pmu_test.pmu_oscp_ui import PMUOSCPUI  # noqa: E402
from ui.pages.pmu_test.gpadc_test_ui import GPADCTestUI  # noqa: E402
from ui.pages.pmu_test.clk_test_ui import CLKTestUI  # noqa: E402
from ui.pages.pmu_test.pmu_psrr_ui import PMUPSRRUI  # noqa: E402
from ui.pages.pmu_test.ft_calib_check_ui import FTCalibCheckUI  # noqa: E402

timeit("PMUDCDCEfficiencyUI", lambda: PMUDCDCEfficiencyUI())
timeit("PMUOutputVoltageUI", lambda: PMUOutputVoltageUI())
timeit("PMUIsGainUI", lambda: PMUIsGainUI())
timeit("PMUOSCPUI", lambda: PMUOSCPUI())
timeit("GPADCTestUI", lambda: GPADCTestUI())
timeit("CLKTestUI", lambda: CLKTestUI())
timeit("PMUPSRRUI", lambda: PMUPSRRUI())
timeit("FTCalibCheckUI", lambda: FTCalibCheckUI())

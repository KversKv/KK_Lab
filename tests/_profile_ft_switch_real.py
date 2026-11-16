"""临时验证：懒加载后真实平台首次进入 PMU / 首次切 FT 的耗时（模拟主窗口已启动）。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.perf_counter()


def tick(label):
    global T0
    now = time.perf_counter()
    print(f"{label:<52} {now - T0:8.3f} s", flush=True)
    T0 = now


from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
app.setStyle("Fusion")
tick("QApplication")

# 模拟主窗口启动已支付的一次性成本：先构建一个真实页面（吸收首次 polish/主题初始化）
import debug_config  # noqa: E402
from ui.widgets.config_memory import ConfigMemory  # noqa: E402

debug_config.DEBUG_MOCK = True
ConfigMemory.watch = lambda self, widget: None
ConfigMemory.restore = lambda self: None

from ui.pages.pmu_test.pmu_output_voltage import PMUOutputVoltageUI  # noqa: E402

_warm = PMUOutputVoltageUI()
_warm.resize(1600, 900)
_warm.grab()
_warm.deleteLater()
app.processEvents()
tick("一次性成本预热（模拟 MainWindow 启动）")

from ui.pages.pmu_test.gpadc_test.mixins import acquisition_mixin, execution_mixin  # noqa: E402

acquisition_mixin.DEBUG_MOCK = True
execution_mixin.DEBUG_MOCK = True

from ui.pages.pmu_test.pmu_test_ui import PMUTestUI  # noqa: E402

tick("imports")

ui = PMUTestUI()
tick("PMUTestUI() 构造（懒加载，仅当前 tab）")

ui.resize(1600, 900)
ui.grab()
app.processEvents()
tick("默认 tab 首次 grab")

ui.set_current_test("ft_calib_check")
ui.grab()
app.processEvents()
tick("首次切 FT（构建+渲染）")

ui.set_current_test("dcdc_efficiency")
ui.grab()
app.processEvents()
tick("切回 tab0")

ui.set_current_test("ft_calib_check")
ui.grab()
app.processEvents()
tick("第二次切 FT")

for key in ("gpadc_test", "psrr", "clk_test", "is_gain", "oscp", "output_voltage"):
    ui.set_current_test(key)
    ui.grab()
    app.processEvents()
    tick(f"{key} 首次构建+渲染")

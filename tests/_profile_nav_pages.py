"""临时排查：各 Tab 容器首次切换耗时（offscreen + grab 强制渲染，03 §45）。

用法：python tests/_profile_nav_pages.py <charger|consumption|module|vmin|suite|pmu|all>
每个容器独立进程运行，隔离"首个大型控件树 polish"一次性成本。
"""
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
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
ConfigMemory.bind = lambda self, key, widget: None
ConfigMemory.save_now = lambda self: None


def timeit(label, fn):
    t = time.perf_counter()
    result = fn()
    print(f"{label:<48} {time.perf_counter() - t:8.3f} s", flush=True)
    return result


def render(w):
    app.processEvents()
    w.grab()
    app.processEvents()


def profile_tab_container(name, cls, keys, **kwargs):
    print(f"\n===== {name} =====", flush=True)
    ui = timeit(f"{name}() 构造", lambda: cls(**kwargs))
    ui.resize(1600, 900)
    ui.show()
    timeit("首次 show + grab（默认子页）", lambda: render(ui))
    for key in keys:
        timeit(f"首次切 {key} + grab", lambda k=key: (ui.set_current_test(k), render(ui)))
    for key in keys:
        timeit(f"二次切 {key} + grab", lambda k=key: (ui.set_current_test(k), render(ui)))
    ui.close()
    ui.deleteLater()
    app.processEvents()


def profile_suite():
    from ui.pages.power_analyzer.power_analyzer_suite_ui import N6705CSuiteWindow

    print("\n===== N6705CSuiteWindow（参考，启动页） =====", flush=True)
    ui = timeit("Suite() 构造（analyser+datalog）",
                lambda: N6705CSuiteWindow(standalone=False))
    ui.resize(1600, 900)
    ui.show()
    timeit("首次 show + grab（analyser）", lambda: render(ui))
    timeit("首次切 datalog + grab", lambda: (ui.switch_page("datalog"), render(ui)))
    timeit("二次切 datalog + grab", lambda: (ui.switch_page("analyser"), ui.switch_page("datalog"), render(ui)))
    ui.close()
    ui.deleteLater()
    app.processEvents()


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"

    if which in ("charger", "all"):
        from ui.pages.charger_test.charger_test_ui import ChargerTestUI
        profile_tab_container(
            "ChargerTestUI", ChargerTestUI,
            ["config_traverse", "status_register", "iterm", "regulation_voltage"])

    if which in ("consumption", "all"):
        from ui.pages.consumption_test.consumption_test_wrapper import ConsumptionTestWrapper
        profile_tab_container(
            "ConsumptionTestWrapper", ConsumptionTestWrapper,
            ["auto_test", "high_low_temp"])

    if which in ("module", "all"):
        from ui.pages.module_test.module_test_ui import ModuleTestUI
        profile_tab_container("ModuleTestUI", ModuleTestUI, ["ldo", "dcdc"])

    if which in ("vmin", "all"):
        from ui.pages.vmin_hunter.vmin_hunter_container import VminHunterContainerUI
        profile_tab_container("VminHunterContainerUI", VminHunterContainerUI,
                              ["hunt", "single_test"])

    if which in ("pmu", "all"):
        from ui.pages.pmu_test.pmu_test_ui import PMUTestUI
        profile_tab_container(
            "PMUTestUI（已优化基线）", PMUTestUI,
            ["dcdc_efficiency", "ft_calib_check"])

    if which in ("suite", "all"):
        profile_suite()


if __name__ == "__main__":
    main()

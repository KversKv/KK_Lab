"""临时冒烟：FT Calibration Check 容器页装配与 ft_only 锁定（offscreen）。"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)

# Mock 模式 + 禁用配置记忆落盘（临时冒烟不污染 user_data）
import debug_config  # noqa: E402
from ui.pages.pmu_test.gpadc_test.mixins import acquisition_mixin, execution_mixin  # noqa: E402
from ui.widgets.config_memory import ConfigMemory  # noqa: E402

debug_config.DEBUG_MOCK = True
acquisition_mixin.DEBUG_MOCK = True
execution_mixin.DEBUG_MOCK = True
ConfigMemory.watch = lambda self, widget: None
ConfigMemory.restore = lambda self: None

from ui.pages.pmu_test.pmu_test_ui import PMUTestUI  # noqa: E402

ui = PMUTestUI()
assert ui.TEST_TAB_MAP["ft_calib_check"] == 7
assert ui.tab_widget.count() == 8
# 懒加载：初始只构建当前 tab（默认 0=dcdc），其余子页为 None 占位
assert ui.dcdc_efficiency_ui is not None
assert ui.ft_calib_check_ui is None
assert ui.gpadc_test_ui is None
assert ui.get_test_config("ft_calib_check") is None

ui.set_current_test("ft_calib_check")
assert ui.get_current_test() == "ft_calib_check"
assert ui.ft_calib_check_ui is not None
# 切换后 tab 顺序 / 标签不变
assert ui.tab_widget.count() == 8
assert ui.tab_widget.tabText(7) == "FT Calibration Check"
assert ui.tab_widget.widget(7) is ui.ft_calib_check_ui

ft = ui.ft_calib_check_ui
g = ft.gpadc_ui
assert ft.tab_widget.count() == 2
assert g.current_test_item == g.TEST_FT_CALIB_CHECK
assert g.test_item_combo.count() == 1
assert g.test_item_combo.currentData() == g.TEST_FT_CALIB_CHECK
assert g.test_item_panel.isHidden()
assert g._header_title_label.isHidden()
assert g._header_subtitle_label.isHidden()
assert ft._subtitle_label.text() == "Two-point FT calibration verification of GPADC (IIC / UART)."
assert g.ft_params_frame.isVisibleTo(g)
assert not g.algorithm_combo.isVisibleTo(g)

cfg = ft.get_test_config()
assert cfg["test_item"] == g.TEST_FT_CALIB_CHECK
assert ft.ai_capabilities()
assert ft.is_test_running is False

# 外部 test_item 回填不得切走锁定项
g.apply_config_to_controls({"test_item": g.TEST_1000CNT, "ft_calib_v1": "1.2"}, silent=True)
assert g.current_test_item == g.TEST_FT_CALIB_CHECK
assert g.ft_calib_v1.text() == "1.2"

# Output Voltage Check 占位子项：无 AI 能力，副标题随子项切换
ft.tab_widget.setCurrentIndex(1)
assert ft._subtitle_label.text() == "Output voltage calibration check (to be implemented)."
assert ft.ai_capabilities() == set()
assert ft.ai_get_config() is None
ok, _msg = ft.ai_start_test()
assert not ok
ft.tab_widget.setCurrentIndex(0)
assert ft.ai_capabilities()

# 原 GPADC Test 页不受影响（6 测试项仍在，Test Item 面板可见）——首次切到才构建
assert ui.gpadc_test_ui is None
ui.set_current_test("gpadc_test")
gp = ui.gpadc_test_ui
assert gp is not None
assert gp.test_item_combo.count() == 6
assert not gp.test_item_panel.isHidden()

# 全部 8 子页懒加载均可构建且 tab 位置正确
for key, idx in ui.TEST_TAB_MAP.items():
    ui.set_current_test(key)
    assert ui.get_current_test() == key
    assert ui.tab_widget.widget(idx) is getattr(ui, ui._SUBPAGE_ATTRS[key])
ui.set_current_test("ft_calib_check")

# 容器透传接口
ft.set_system_status("就绪")
ft.clear_results()
ft.update_instrument_info({})
ft.set_test_mode("manual")
ft.set_test_id("X")
assert ft.get_test_config()["test_item"] == g.TEST_FT_CALIB_CHECK

# Mock 端到端：嵌入页直接跑 FT Calibration Check（IIC）
import time  # noqa: E402

g.voltage_min.setValue(1.0)
g.voltage_max.setValue(3.0)
g.voltage_step.setValue(0.5)
g.sample_count.setValue(8)
errors = []
g._on_test_error = errors.append
g._start_test()
deadline = time.time() + 60
while g.is_test_running and time.time() < deadline:
    app.processEvents()
    time.sleep(0.01)
assert not g.is_test_running, "FT mock 测试超时"
assert errors == [], errors
assert g._recent_test_records[-1]["kind"] == "ft_calib_check"
assert g._export_data is not None
g.cleanup_threads()
app.processEvents()
print("MOCK FT RUN OK:", g._recent_test_records[-1]["params"])

print("SMOKE OK")

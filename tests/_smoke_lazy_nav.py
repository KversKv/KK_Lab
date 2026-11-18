"""临时冒烟：MainWindow 导航路径下四个懒加载容器的首次/二次切换行为。

验证：占位 tab 原位替换后索引/标签不变、未构建子页属性为 None、
AI 枢纽下钻命中已构建子页、重访容器 _sync_from_top 不触发未建页构建。
user_data 隔离到临时目录，避免污染真实运行期配置。
"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtCore import QTimer  # noqa: E402

app = QApplication(sys.argv)

import debug_config  # noqa: E402
import resource_path  # noqa: E402

debug_config.DEBUG_MOCK = True
# 先补丁 resource_path，后续所有 from-import 绑定的都是隔离目录
_TMP_USER_DATA = tempfile.mkdtemp(prefix="kk_lazy_nav_smoke_")
resource_path.get_user_data_dir = lambda *parts: os.path.join(_TMP_USER_DATA, *parts)

from ui.widgets.config_memory import ConfigMemory  # noqa: E402

ConfigMemory.watch = lambda self, widget: None
ConfigMemory.restore = lambda self: None
ConfigMemory.bind = lambda self, key, widget: None
ConfigMemory.save_now = lambda self: None

from ui.main_window import MainWindow  # noqa: E402


def check_container(win, container, tab_map, labels, attrs, selected, initial):
    name = type(container).__name__
    tw = container.tab_widget
    assert tw.count() == len(tab_map), f"{name} tab 数量变化"
    for key, index in tab_map.items():
        assert tw.tabText(index) == labels[key], f"{name} tab {index} 标签变化"
    assert container.get_current_test() == selected, f"{name} 当前页错误"
    # 容器构造时先建默认子页（initial），set_current_test 再建目标子页；
    # 其余子页保持未构建（与 PMU 懒加载范式一致）
    built = {initial, selected}
    for key, attr in attrs.items():
        sub = getattr(container, attr)
        if key in built:
            assert sub is not None and tw.widget(tab_map[key]) is sub, f"{name}.{attr} 未构建"
        else:
            assert sub is None, f"{name}.{attr} 应未构建"
    # AI 枢纽下钻命中当前已构建子页
    page = win.resolve_active_ai_page()
    assert page is getattr(container, attrs[selected]), f"{name} AI 下钻错误: {type(page)}"
    # 逐个首次切换其余子页：构建 + 原位替换，索引/标签不变
    for key in tab_map:
        container.set_current_test(key)
        app.processEvents()
        assert container.get_current_test() == key
        assert getattr(container, attrs[key]) is tw.widget(tab_map[key])
        assert tw.count() == len(tab_map)
        for k, i in tab_map.items():
            assert tw.tabText(i) == labels[k]
    print(f"[OK] {name}", flush=True)


def run_checks():
    win = MainWindow(with_ai=False)
    win.show()
    app.processEvents()

    # Charger：直选非默认子页 iterm
    win._create_charger_test_ui(selected_test="iterm")
    app.processEvents()
    check_container(
        win, win.charger_test_ui,
        {"config_traverse": 0, "status_register": 1, "iterm": 2, "regulation_voltage": 3},
        {"config_traverse": "Config Traverse Test", "status_register": "Status Register Test",
         "iterm": "Iterm Test", "regulation_voltage": "Regulation Voltage Test"},
        {"config_traverse": "config_traverse_ui", "status_register": "status_register_ui",
         "iterm": "iterm_ui", "regulation_voltage": "regulation_voltage_ui"},
        "iterm", "config_traverse")

    # Consumption：直选 high_low_temp
    win._create_consumption_test_ui(selected_test="high_low_temp")
    app.processEvents()
    check_container(
        win, win.consumption_test_ui,
        {"auto_test": 0, "high_low_temp": 1},
        {"auto_test": "Auto Test", "high_low_temp": "High-Low Temperature Test"},
        {"auto_test": "auto_test_ui", "high_low_temp": "high_low_temp_ui"},
        "high_low_temp", "auto_test")

    # VminHunter：直选 single_test
    win._create_vmin_hunter_ui(selected_test="single_test")
    app.processEvents()
    check_container(
        win, win.vmin_hunter_ui,
        {"hunt": 0, "single_test": 1},
        {"hunt": "Vmin Hunt", "single_test": "Single Vmin Test"},
        {"hunt": "hunt_ui", "single_test": "single_test_ui"},
        "single_test", "hunt")

    # Module：直选 dcdc（QStackedWidget 变体）
    win._create_module_test_ui(selected_test="dcdc")
    app.processEvents()
    mt = win.module_test_ui
    assert mt.get_current_test() == "dcdc"
    assert mt.dcdc_test_ui is mt.stack.widget(1)
    assert mt.ldo_test_ui is not None  # 初始默认构建 ldo
    assert mt.command_bar.current_module() == "dcdc"
    assert win.resolve_active_ai_page() is mt.dcdc_test_ui
    mt.set_current_test("ldo")
    app.processEvents()
    assert mt.command_bar.current_module() == "ldo"
    assert win.resolve_active_ai_page() is mt.ldo_test_ui
    print("[OK] ModuleTestUI", flush=True)

    # 重访容器（else 分支 _sync_from_top）：不触发未建页构建、不报错
    win._create_charger_test_ui(selected_test="iterm")
    win._create_consumption_test_ui(selected_test="high_low_temp")
    win._create_vmin_hunter_ui(selected_test="single_test")
    win._create_module_test_ui(selected_test="dcdc")
    app.processEvents()
    print("[OK] 重访同步", flush=True)

    print("LAZY_NAV_SMOKE_OK", flush=True)
    # 走正常关闭流程（closeEvent 线程清理），直接退出会 QThread 析构崩溃
    win.close()
    app.quit()


QTimer.singleShot(500, run_checks)
QTimer.singleShot(60000, app.quit)
sys.exit(app.exec())

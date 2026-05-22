__all__ = [
    "PlotWidget",
    "DarkComboBox",
    "SidebarNavButton",
    "SidebarSubMenu",
    "ProgressButton",
    "SpinningSearchButton",
    "search_button_style",
    "connect_button_style",
    "disconnect_button_style",
    "apply_search_button",
    "update_connect_button_state",
    "SCROLLBAR_STYLE",
    "SCROLL_AREA_STYLE",
    "START_BTN_STYLE",
    "create_start_btn",
    "update_start_btn_state",
]


def __getattr__(name):
    if name == "PlotWidget":
        from ui.widgets.plot_widget import PlotWidget
        return PlotWidget
    if name == "DarkComboBox":
        from ui.widgets.dark_combobox import DarkComboBox
        return DarkComboBox
    if name == "SidebarNavButton":
        from ui.widgets.sidebar_nav_button import SidebarNavButton
        return SidebarNavButton
    if name == "SidebarSubMenu":
        from ui.widgets.sidebar_submenu import SidebarSubMenu
        return SidebarSubMenu
    if name == "ProgressButton":
        from ui.widgets.progress_button import ProgressButton
        return ProgressButton
    if name in {
        "SpinningSearchButton",
        "search_button_style",
        "connect_button_style",
        "disconnect_button_style",
        "apply_search_button",
        "update_connect_button_state",
    }:
        from ui.widgets import button
        return getattr(button, name)
    if name in {"SCROLLBAR_STYLE", "SCROLL_AREA_STYLE"}:
        from ui.widgets import scrollbar
        return getattr(scrollbar, name)
    if name in {"START_BTN_STYLE", "create_start_btn", "update_start_btn_state"}:
        from ui.widgets import start_sequence
        return getattr(start_sequence, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

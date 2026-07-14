# I2C 模块 QSS 样式

from ui.modules.IIC_Module.i2c_constants import (
    SLATE_950, SLATE_900, SLATE_800, INDIGO, INDIGO_LIGHT,
    EMERALD, EMERALD_LIGHT, TEXT_MAIN, TEXT_MUTED,
)


def _i2c_input_style():
    return (
        "QLineEdit {"
        f" background-color:{SLATE_950}; border:1px solid {SLATE_800};"
        " border-radius:6px; color:#e2e8f0;"
        " min-height:22px; max-height:22px; padding:0 8px;"
        " selection-background-color:#4f46e5;"
        " font-family:Consolas,'Cascadia Mono',monospace;"
        "}"
        f" QLineEdit:focus {{ border:1px solid {INDIGO}; }}"
        " QLineEdit:disabled { background-color:#0b1120; color:#475569;"
        " border:1px solid #1e293b; }"
    )


def _i2c_read_btn_style():
    return (
        "QPushButton {"
        f" background-color: rgba(16,185,129,0.12); border:1px solid {EMERALD};"
        " border-radius:6px; color:#34d399; font-weight:bold;"
        " min-height:22px; max-height:22px; padding:0 16px;"
        "}"
        " QPushButton:hover { background-color: rgba(16,185,129,0.22); }"
        " QPushButton:pressed { background-color: rgba(16,185,129,0.08); }"
        " QPushButton:disabled { background-color:#0b1120; color:#334155;"
        " border:1px solid #1e293b; }"
    )


def _i2c_write_btn_style():
    return (
        "QPushButton {"
        f" background-color: rgba(99,102,241,0.15); border:1px solid {INDIGO};"
        " border-radius:6px; color:#c7d2fe; font-weight:bold;"
        " min-height:22px; max-height:22px; padding:0 16px;"
        "}"
        " QPushButton:hover { background-color: rgba(99,102,241,0.28); }"
        " QPushButton:pressed { background-color: rgba(99,102,241,0.08); }"
        " QPushButton:disabled { background-color:#0b1120; color:#334155;"
        " border:1px solid #1e293b; }"
    )


def _i2c_subtle_btn_style():
    return (
        "QPushButton {"
        f" background-color:{SLATE_900}; border:1px solid {SLATE_800};"
        " border-radius:6px; color:#cbd5e1; font-weight:bold;"
        " min-height:22px; max-height:22px; padding:0 12px;"
        "}"
        f" QPushButton:hover {{ background-color:#1b2840; border:1px solid {INDIGO};"
        " color:#e2e8f0; }"
        " QPushButton:disabled { background-color:#0b1120; color:#475569;"
        " border:1px solid #1e293b; }"
    )


def _i2c_collapse_arrow_style():
    return (
        "QPushButton#i2cCollapseArrow {"
        " background:transparent; border:none; color:#f8fafc;"
        " font-size:11px; font-weight:bold; padding:0px;"
        "}"
        f" QPushButton#i2cCollapseArrow:hover {{ color:{INDIGO_LIGHT}; }}"
    )


def _bit_val_style(on):
    if on:
        return (
            "QPushButton {"
            " background-color: rgba(16,185,129,0.20); border:1px solid #10b981;"
            " border-radius:4px; color:#34d399; font-weight:bold;"
            " min-height:22px; max-height:22px;"
            "}"
            " QPushButton:hover { background-color: rgba(16,185,129,0.34); }"
        )
    return (
        "QPushButton {"
        f" background-color:{SLATE_950}; border:1px solid {SLATE_800};"
        " border-radius:4px; color:#64748b; font-weight:bold;"
        " min-height:22px; max-height:22px;"
        "}"
        f" QPushButton:hover {{ background-color:{SLATE_900}; color:{TEXT_MUTED}; }}"
    )


def _i2c_table_qss():
    return (
        f"QTableWidget {{ background-color:{SLATE_950}; border:1px solid {SLATE_800};"
        " border-radius:8px; gridline-color:#1e293b; color:#e2e8f0; }"
        f"QHeaderView::section {{ background-color:{SLATE_900}; color:{TEXT_MUTED};"
        " border:0; border-right:1px solid #1e293b; padding:6px;"
        " font-weight:bold; font-size:11px; }"
        "QTableWidget::item { padding:2px 6px; }"
        "QTableWidget::item:selected { background-color: rgba(99,102,241,0.25); }"
        "QTableCornerButton::section { background:#0f172a; border:0; }"
    )


def _i2c_scrollbar_qss():
    return (
        "QScrollBar:vertical { background:transparent; width:8px; margin:0; }"
        "QScrollBar::handle:vertical { background:#334155; border-radius:4px;"
        " min-height:24px; }"
        "QScrollBar::handle:vertical:hover { background:#475569; }"
        "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }"
        "QScrollBar:horizontal { background:transparent; height:8px; margin:0; }"
        "QScrollBar::handle:horizontal { background:#334155; border-radius:4px;"
        " min-width:24px; }"
        "QScrollBar::handle:horizontal:hover { background:#475569; }"
        "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0; }"
    )


def _nav_tab_style():
    return (
        "QPushButton#navTab { background:transparent; border:none;"
        " border-bottom:2px solid transparent; color:#94a3b8;"
        " padding:8px 18px; font-size:11px; font-weight:bold; letter-spacing:1px;"
        "}"
        "QPushButton#navTab:hover { color:#e2e8f0; }"
        "QPushButton#navTab:checked { color:#c7d2fe;"
        " border-bottom:2px solid #6366f1; background: rgba(99,102,241,0.08); }"
    )


_I2C_DARK_STYLE = (
    f"QWidget {{ background-color:{SLATE_950}; color:{TEXT_MAIN}; }}"
    f"QLabel {{ background:transparent; color:{TEXT_MAIN}; border:none; }}"
    "QLabel#cardTitle { font-size:11px; font-weight:bold; color:#f8fafc;"
    " letter-spacing:1px; background:transparent; }"
    "QLabel#sectionTitle { font-size:10px; font-weight:bold; color:#94a3b8;"
    " letter-spacing:1px; background:transparent; }"
    "QLabel#appTitle { font-size:14px; font-weight:bold; color:#f8fafc;"
    " letter-spacing:1px; background:transparent; }"
    "QLabel#appBadge { background-color:#6366f1; color:#ffffff; border-radius:6px;"
    " font-weight:bold; font-size:10px; letter-spacing:1px; }"
    "QLabel#muted { color:#64748b; background:transparent; }"
    "QLabel#mono { font-family:Consolas,'Cascadia Mono',monospace;"
    f" background:transparent; color:{INDIGO_LIGHT}; }}"
    "QLabel#activityVal { font-family:Consolas,'Cascadia Mono',monospace;"
    " font-weight:bold; background:transparent; }"
    f"QFrame#card {{ background-color:{SLATE_900}; border:1px solid {SLATE_800};"
    " border-radius:12px; }"
    f"QFrame#navBar {{ background-color:{SLATE_900}; border:1px solid {SLATE_800};"
    " border-radius:12px; }"
    f"QFrame#workspace {{ background-color:{SLATE_900}; border:1px solid {SLATE_800};"
    " border-radius:12px; }"
    f"QFrame#footer {{ background-color:{SLATE_950}; border:1px solid {SLATE_800};"
    " border-radius:10px; }"
) + _i2c_scrollbar_qss()

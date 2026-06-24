"""Serial console style tokens (Phase 6 样式 token 统一).

本模块是 serialCom 两套皮肤（apple 浅色 / dark 暗色）的**值层 token 单一事实源**：
颜色 / 度量 / 字体 / SVG 路径在此集中定义，皮肤模块仅消费 token、不再各自重复字面量。

命名与 ``ui.theme``（应用级 token：``Colors`` / ``FontSizes`` / ``Spacing`` / ``Radius``）对齐：
- ``ui.theme`` 驱动主程序全局 chrome；
- ``ui.styles.serial_tokens`` 仅驱动 serialCom 模块皮肤。
两者概念边界清晰、互不重叠。

注意：两套皮肤的 QSS 生成逻辑（圆角 / 边框 / checked 状态色板 / SVG 箭头等）本就是不同视觉设计，
因此生成函数仍各自留在 ``serialCom_apple_gpt5p5_style.py`` / ``serialCom_dark_style.py``；
本模块只统一它们共享的**语义 token 词表与取值**。
"""
import os
from dataclasses import dataclass

from PySide6.QtGui import QColor

from ui.resource_path import get_resource_base


SERIAL_BTN_HEIGHT = 26
SERIAL_BTN_ICON_SIZE = 14
TERM_FONT = '"JetBrains Mono", "Fira Code", Consolas, "Menlo", "Courier New", monospace'
UI_FONT = '"Inter", "PingFang SC", "Microsoft YaHei", "Segoe UI", -apple-system, sans-serif'


def dlg_check_svg():
    return os.path.join(
        get_resource_base(), "resources", "modules", "SVG_Serial", "checkmark.svg"
    ).replace("\\", "/")


def spin_up_svg():
    return os.path.join(
        get_resource_base(), "resources", "modules", "SVG_Serial", "spin_up.svg"
    ).replace("\\", "/")


def spin_down_svg():
    return os.path.join(
        get_resource_base(), "resources", "modules", "SVG_Serial", "spin_down.svg"
    ).replace("\\", "/")


class SerialFontSizes:
    tiny = "10px"
    caption = "11px"
    body = "12px"
    body_lg = "13px"
    subtitle = "14px"
    title = "15px"
    title_lg = "18px"


class SerialSpacing:
    xs = 4
    sm = 8
    md = 12
    lg = 16
    xl = 24


class SerialRadius:
    small = 5
    widget = 6
    card = 8
    container = 12


@dataclass(frozen=True)
class SerialColorTokens:
    bg_main: str
    bg_panel: str
    bg_card: str
    bg_log: str

    border: str
    border_hover: str
    border_soft: str
    border_active: str

    text_title: str
    text_accent: str
    text_subtitle: str
    text_label: str
    text_btn: str
    text_btn_log: str
    text_body: str
    text_time: str
    text_lineno: str
    text_info: str
    text_muted: str
    text_white: str
    text_soft: str
    text_tab: str

    input_bg: str
    input_text: str
    cursor: str
    selection_bg: str
    selection_text: str

    scrollbar: str
    scrollbar_hv: str

    connect_fg: str
    connect_bg: str
    connect_text: str
    connect_hover: str
    connect_press: str

    disconnect_bg: str
    disconnect_hover: str
    disconnect_press: str
    disconnect_text: str

    send_bg: str
    send_hover: str
    send_press: str

    warning: str
    error: str
    rx: str
    tx: str

    filter_text: str
    filter_bg: str
    filter_border: str

    toggle_on: str
    disabled: str

    blue: str
    blue_hover: str
    blue_press: str
    blue_light: str

    green_ok: str
    green_ok_hover: str

    rose_icon: str
    warn_icon: str

    history_combo_bg: str
    history_combo_qcolor: QColor

    btn_radius: int


APPLE_TOKENS = SerialColorTokens(
    bg_main="#fcfdfe",
    bg_panel="#fcfdfe",
    bg_card="#FFFFFF",
    bg_log="#FBFBFD",
    border="#D2D2D7",
    border_hover="#A1A1A6",
    border_soft="#E5E5EA",
    border_active="#007AFF",
    text_title="#1D1D1F",
    text_accent="#FF9F0A",
    text_subtitle="#0A84FF",
    text_label="#515154",
    text_btn="#0A84FF",
    text_btn_log="#3A3A3C",
    text_body="#1D1D1F",
    text_time="#8E8E93",
    text_lineno="#A1A1A6",
    text_info="#0A84FF",
    text_muted="#6E6E73",
    text_white="#FFFFFF",
    text_soft="#3A3A3C",
    text_tab="#1D1D1F",
    input_bg="#F2F2F7",
    input_text="#1D1D1F",
    cursor="#007AFF",
    selection_bg="#BBD7FF",
    selection_text="#000000",
    scrollbar="#C7C7CC",
    scrollbar_hv="#AEAEB2",
    connect_fg="#30D158",
    connect_bg="#E8F8EE",
    connect_text="#248A3D",
    connect_hover="#DDF7E6",
    connect_press="#CDEFD9",
    disconnect_bg="#FFECEA",
    disconnect_hover="#FFDAD6",
    disconnect_press="#FFC8C2",
    disconnect_text="#D70015",
    send_bg="#007AFF",
    send_hover="#0A84FF",
    send_press="#0066CC",
    warning="#FF9F0A",
    error="#FF3B30",
    rx="#1D1D1F",
    tx="#007AFF",
    filter_text="#5E5CE6",
    filter_bg="#EFEFFF",
    filter_border="#0A84FF",
    toggle_on="#34C759",
    disabled="#AEAEB2",
    blue="#007AFF",
    blue_hover="#0A84FF",
    blue_press="#0066CC",
    blue_light="#64D2FF",
    green_ok="#34C759",
    green_ok_hover="#30B650",
    rose_icon="#FF375F",
    warn_icon="#FF9F0A",
    history_combo_bg="rgba(242, 242, 247, 0.64)",
    history_combo_qcolor=QColor(242, 242, 247, 163),
    btn_radius=7,
)


DARK_TOKENS = SerialColorTokens(
    bg_main="#020617",
    bg_panel="#020617",
    bg_card="#0F172A",
    bg_log="#020617",
    border="#1E293B",
    border_hover="#334155",
    border_soft="#243044",
    border_active="#3B82F6",
    text_title="#E2E8F0",
    text_accent="#FBBF24",
    text_subtitle="#60A5FA",
    text_label="#94A3B8",
    text_btn="#60A5FA",
    text_btn_log="#CBD5E1",
    text_body="#CBD5E1",
    text_time="#64748B",
    text_lineno="#475569",
    text_info="#06B6D4",
    text_muted="#94A3B8",
    text_white="#FFFFFF",
    text_soft="#CBD5E1",
    text_tab="#E2E8F0",
    input_bg="#020617",
    input_text="#E2E8F0",
    cursor="#60A5FA",
    selection_bg="#1E3A5F",
    selection_text="#E2E8F0",
    scrollbar="#334155",
    scrollbar_hv="#475569",
    connect_fg="#3B82F6",
    connect_bg="#10291F",
    connect_text="#34D399",
    connect_hover="#15311F",
    connect_press="#0E2618",
    disconnect_bg="#2A1418",
    disconnect_hover="#3A1A1F",
    disconnect_press="#451A20",
    disconnect_text="#FB7185",
    send_bg="#2563EB",
    send_hover="#3B82F6",
    send_press="#1D4ED8",
    warning="#FBBF24",
    error="#F87171",
    rx="#CBD5E1",
    tx="#60A5FA",
    filter_text="#A78BFA",
    filter_bg="#1E1B2E",
    filter_border="#3B82F6",
    toggle_on="#2563EB",
    disabled="#475569",
    blue="#2563EB",
    blue_hover="#3B82F6",
    blue_press="#1D4ED8",
    blue_light="#60A5FA",
    green_ok="#10B981",
    green_ok_hover="#059669",
    rose_icon="#F87171",
    warn_icon="#FBBF24",
    history_combo_bg="rgba(13, 14, 17, 0.64)",
    history_combo_qcolor=QColor(13, 14, 17, 163),
    btn_radius=6,
)

class Colors:
    bg_primary = "#020618"
    bg_secondary = "#050b1a"
    bg_card = "#0b1630"
    bg_input = "#091426"
    bg_panel = "#08132d"
    bg_deep = "#07111f"

    border_primary = "#16274d"
    border_secondary = "#1a2d57"
    border_accent = "#25355c"
    border_input = "#1c2f54"

    text_primary = "#f8fbff"
    text_secondary = "#dbe7ff"
    text_muted = "#8ea6cf"
    text_accent = "#7da2d6"
    text_dim = "#6a8ab8"
    text_disabled = "#4a5a7a"

    success = "#15d1a3"
    warning = "#ffb84d"
    error = "#ff5e7a"
    info = "#5b9cf5"

    accent_primary = "#5b3df5"
    accent_hover = "#6548ff"
    accent_pressed = "#4a2fd4"
    accent_soft = "#3f3a8a"

    channel_1_accent = "#d4a514"
    channel_1_bg = "#1a1708"
    channel_1_border = "#3d2e08"

    channel_2_accent = "#18b67a"
    channel_2_bg = "#081a14"
    channel_2_border = "#0a3d28"

    channel_3_accent = "#2f6fed"
    channel_3_bg = "#081028"
    channel_3_border = "#0c2a5e"

    channel_4_accent = "#d14b72"
    channel_4_bg = "#1a080e"
    channel_4_border = "#3d0c22"

    nav_bg = "#0b1020"
    nav_hover = "#171c2b"
    nav_group_title = "#7b93bf"
    nav_item_text = "#c7d3ee"
    nav_item_muted = "#8fa3c2"
    nav_arrow = "#6f7d98"
    nav_icon = "#93a4c3"

    submenu_bg = "#1b2233"
    submenu_item_text = "#d5d9e3"
    submenu_item_hover_bg = "#24314a"
    submenu_item_selected_bg = "#3f3a8a"
    submenu_item_selected_text = "#9cabff"
    submenu_item_selected_hover = "#4942a0"

    scrollbar_bg = "#050a1d"
    scrollbar_handle = "#1f315d"
    scrollbar_handle_hover = "#2a3a6a"
    scrollbar_arrow_bg = "#080e22"
    scrollbar_arrow_hover = "#0e1a35"

    disabled_bg = "#070f1e"
    disabled_border = "#0d1a30"
    disabled_text = "#4a5a7a"
    disabled_btn_bg = "#0D1734"
    disabled_btn_border = "#18264A"


class FontSizes:
    title = "18px"
    subtitle = "12px"
    body = "12px"
    caption = "11px"
    tiny = "10px"
    control = "14px"


FONT_FAMILY = '"Segoe UI", "Microsoft YaHei", sans-serif'
FONT_MONO = '"JetBrains Mono", "Consolas", "Courier New", monospace'


class Spacing:
    xs = 4
    sm = 8
    md = 12
    lg = 16
    xl = 24
    xxl = 32


class Radius:
    container = 16
    card = 12
    widget = 8
    small = 6


CHANNEL_COLORS = {
    1: {"accent": Colors.channel_1_accent, "bg": Colors.channel_1_bg, "border": Colors.channel_1_border},
    2: {"accent": Colors.channel_2_accent, "bg": Colors.channel_2_bg, "border": Colors.channel_2_border},
    3: {"accent": Colors.channel_3_accent, "bg": Colors.channel_3_bg, "border": Colors.channel_3_border},
    4: {"accent": Colors.channel_4_accent, "bg": Colors.channel_4_bg, "border": Colors.channel_4_border},
}

CHANNEL_THEMES = {
    1: {
        "accent": "#d4a514", "accent_hover": "#e3b729",
        "accent_soft": "#342808", "accent_border": "#7a5e12", "text_dim": "#c9b06a",
    },
    2: {
        "accent": "#18b67a", "accent_hover": "#21c487",
        "accent_soft": "#0a2a20", "accent_border": "#14694b", "text_dim": "#7bc7a8",
    },
    3: {
        "accent": "#2f6fed", "accent_hover": "#4680f0",
        "accent_soft": "#0c2048", "accent_border": "#264d9b", "text_dim": "#8db4ff",
    },
    4: {
        "accent": "#d14b72", "accent_hover": "#df5f85",
        "accent_soft": "#34111d", "accent_border": "#7e2f47", "text_dim": "#d79ab1",
    },
}

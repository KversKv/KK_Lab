"""页面基础 QSS（基于 ``ui.theme`` 应用级 token 生成）.

serialCom 模块皮肤不使用本模块：其样式 token 见 ``ui.styles.serial_tokens``，
QSS 生成见 ``ui.modules.serialCom_module.serialCom_apple_gpt5p5_style`` /
``serialCom_dark_style``（由 ``serialCom_module_frame._select_serialcom_style_module`` 切换）。
"""
from ui.theme import Colors, FontSizes, Radius, Spacing, FONT_FAMILY
from ui.widgets.scrollbar import SCROLLBAR_STYLE


def get_page_base_qss(accent_color=None):
    accent = accent_color or Colors.accent_primary

    return f"""
        QWidget {{
            background-color: {Colors.bg_secondary};
            color: {Colors.text_secondary};
        }}

        QWidget#leftPanelInner {{
            background-color: transparent;
        }}

        QLabel {{
            background-color: transparent;
            color: {Colors.text_secondary};
            border: none;
        }}

        QLabel#pageTitle {{
            font-size: {FontSizes.title};
            font-weight: 700;
            color: {Colors.text_primary};
            background-color: transparent;
        }}

        QLabel#pageSubtitle {{
            font-size: {FontSizes.subtitle};
            color: {Colors.text_accent};
            background-color: transparent;
        }}

        QFrame#panelFrame {{
            background-color: {Colors.bg_panel};
            border: 1px solid {Colors.border_primary};
            border-radius: {Radius.container}px;
        }}

        QFrame#cardFrame {{
            background-color: {Colors.bg_card};
            border: 1px solid {Colors.border_secondary};
            border-radius: {Radius.card}px;
        }}

        QLabel#cardTitle {{
            font-size: {FontSizes.caption};
            font-weight: 700;
            color: {Colors.text_primary};
            letter-spacing: 0.5px;
            background-color: transparent;
        }}

        QLabel#sectionTitle {{
            font-size: {FontSizes.body};
            font-weight: 700;
            color: {Colors.text_primary};
            background-color: transparent;
        }}

        QLabel#fieldLabel {{
            color: {Colors.text_muted};
            font-size: {FontSizes.caption};
            background-color: transparent;
        }}

        QLabel#statusOk {{
            color: {Colors.success};
            font-weight: 600;
            background-color: transparent;
        }}

        QLabel#statusWarn {{
            color: {Colors.warning};
            font-weight: 600;
            background-color: transparent;
        }}

        QLabel#statusErr {{
            color: {Colors.error};
            font-weight: 600;
            background-color: transparent;
        }}

        QLabel#mutedLabel {{
            color: {Colors.text_muted};
            font-size: {FontSizes.caption};
            background-color: transparent;
        }}

        QLineEdit {{
            background-color: {Colors.bg_input};
            border: 1px solid {Colors.border_input};
            border-radius: {Radius.small}px;
            padding: 5px 10px;
            color: {Colors.text_secondary};
            min-height: 22px;
            selection-background-color: {Colors.accent_soft};
        }}

        QLineEdit:hover {{
            border: 1px solid {Colors.border_accent};
        }}

        QLineEdit:focus {{
            border: 1px solid {accent};
            background-color: {Colors.bg_panel};
        }}

        QLineEdit:disabled {{
            background-color: {Colors.disabled_bg};
            border: 1px solid {Colors.disabled_border};
            color: {Colors.disabled_text};
        }}

        QPushButton {{
            background-color: {Colors.bg_card};
            border: 1px solid {Colors.border_accent};
            border-radius: {Radius.widget}px;
            padding: 6px 14px;
            color: {Colors.text_secondary};
        }}

        QPushButton:hover {{
            background-color: {Colors.submenu_item_hover_bg};
        }}

        QPushButton:pressed {{
            background-color: {Colors.bg_input};
        }}

        QPushButton:disabled {{
            background-color: {Colors.disabled_btn_bg};
            color: {Colors.disabled_text};
            border: 1px solid {Colors.disabled_btn_border};
        }}

        QCheckBox {{
            color: {Colors.text_secondary};
            spacing: 6px;
            background: transparent;
        }}

        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
        }}

        QComboBox {{
            background-color: {Colors.bg_input};
            border: 1px solid {Colors.border_input};
            border-radius: {Radius.small}px;
            padding: 4px 8px;
            color: {Colors.text_secondary};
            min-height: 22px;
        }}

        QComboBox:hover {{
            border: 1px solid {Colors.border_accent};
        }}

        QComboBox:focus {{
            border: 1px solid {accent};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {Colors.bg_input};
            border: 1px solid {Colors.border_secondary};
            color: {Colors.text_secondary};
            selection-background-color: {Colors.submenu_item_hover_bg};
        }}

        QDoubleSpinBox, QSpinBox {{
            background-color: {Colors.bg_input};
            border: 1px solid {Colors.border_input};
            border-radius: {Radius.small}px;
            padding: 4px 8px;
            color: {Colors.text_secondary};
            min-height: 22px;
        }}

        QDoubleSpinBox:hover, QSpinBox:hover {{
            border: 1px solid {Colors.border_accent};
        }}

        QDoubleSpinBox:focus, QSpinBox:focus {{
            border: 1px solid {accent};
        }}

        QDoubleSpinBox:disabled, QSpinBox:disabled {{
            background-color: {Colors.disabled_bg};
            border: 1px solid {Colors.disabled_border};
            color: {Colors.disabled_text};
        }}

    """ + SCROLLBAR_STYLE


def get_table_qss():
    return f"""
        QTableWidget {{
            background-color: {Colors.bg_input};
            border: 1px solid {Colors.border_secondary};
            border-radius: {Radius.widget}px;
            color: {Colors.text_secondary};
            font-size: {FontSizes.caption};
            gridline-color: {Colors.border_secondary};
        }}

        QTableWidget::item {{
            padding: 2px 6px;
        }}

        QTableWidget::item:selected {{
            background-color: {Colors.border_secondary};
        }}

        QHeaderView::section {{
            background-color: {Colors.bg_input};
            color: {Colors.text_dim};
            border: none;
            border-right: 1px solid {Colors.border_secondary};
            padding: 4px 6px;
            font-size: {FontSizes.caption};
            font-weight: 700;
        }}

        QHeaderView::section:hover {{
            background-color: {Colors.bg_card};
            color: {Colors.text_muted};
        }}

        QHeaderView::section:pressed {{
            background-color: {Colors.border_secondary};
        }}

        QTableCornerButton::section {{
            background-color: {Colors.bg_input};
            border: none;
            border-right: 1px solid {Colors.border_secondary};
            border-bottom: 1px solid {Colors.border_secondary};
        }}
    """ + SCROLLBAR_STYLE

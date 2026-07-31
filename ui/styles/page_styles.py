"""页面基础 QSS（薄壳：样式文本在 ``ui/theme/qss/``，此处仅渲染拼装）.

W1 迁移：``get_page_base_qss`` / ``get_table_qss`` 的 QSS 文本已迁入
``ui/theme/qss/page_base.qss`` / ``page_table.qss``，语义部分 token 化、
legacy 专属值字面量化，渲染结果与迁移前 1:1 一致（基准比对见 tests/_w1_baseline）。

serialCom 模块皮肤不使用本模块：其样式 token 见 ``ui.styles.serial_tokens``，
QSS 生成见 ``ui.modules.serialCom_module.serialCom_apple_gpt5p5_style`` /
``serialCom_dark_style``（由 ``serialCom_module_frame._select_serialcom_style_module`` 切换）。
"""
from ui.theme.legacy import Colors
from ui.theme.theme import load_qss
from ui.widgets.scrollbar import SCROLLBAR_STYLE


def get_page_base_qss(accent_color=None):
    """页面基础 QSS（accent_color 覆盖输入框 focus 边框色）。"""
    accent = accent_color or Colors.accent_primary
    return load_qss("page_base", accent=accent) + SCROLLBAR_STYLE


def get_table_qss():
    """存量 QTableWidget QSS（含滚动条样式）。"""
    return load_qss("page_table") + SCROLLBAR_STYLE

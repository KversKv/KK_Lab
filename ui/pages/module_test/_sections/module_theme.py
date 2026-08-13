"""Module Test 页面专属暗色主题装配（纯视觉，零逻辑）。

集中承接「子页装配处对共享控件的视觉追加」，从而**不修改任何共享控件源文件**
（run_control_bar / card / form / result_table / dark_combobox / status_pill /
banner / log 模块等均保持原样）。所有改动仅限：
- ``setProperty("variant"/objectName/…)`` 追加动态属性（QSS 选择器目标）；
- 进度条 ``setTextVisible`` 等**显示**开关（不改数据/状态流）；
- 通过 ``apply_qss(theme=module_dark_tokens(), **overrides)`` 注入本页 token。

对外仅 ``apply_subpage_theme(subpage)`` 一个入口，由子页基类在 ``_build_ui``
末尾调用。控件查找一律经**已有的公开属性句柄**（``subpage.run_bar`` 等），
不动控件树、不重命名任何 objectName。
"""
from __future__ import annotations

import os

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QLabel, QTableView

from ui.theme import apply_qss, dp, refresh_style

# Module Dark 新增语义 token（未进共享 Tokens，经 overrides 注入 module_dark.qss）
_OVERRIDES = {
    "surface_hover": "rgba(255, 255, 255, 10)",
    "surface_selected": "rgba(88, 150, 255, 36)",
    "text_data": "#7EE0C8",
    "focus_glow": "rgba(88, 150, 255, 51)",
    "progress_track": "#232B36",
    "progress_h": f"{dp(4)}px",
    "progress_radius": f"{dp(2)}px",
    "badge_h": f"{dp(20)}px",
    "badge_radius": f"{dp(10)}px",
}


def _icon_overrides() -> dict[str, str]:
    from ui.resource_path import get_resource_base
    icons = os.path.join(get_resource_base(), "resources", "icons")
    names = ("combo_chevron", "branch_open", "branch_closed", "clear_circle",
             "switch_on", "switch_off", "module_check_on", "module_check_off",
             "module_check_partial")
    return {f"{n}_svg": os.path.join(icons, f"{n}.svg").replace(os.sep, "/")
            for n in names}


def apply_qss_theme(widget) -> None:
    """向指定子页根注入 module_dark 主题（叠加共享 controls/table 之上）。"""
    from ui.theme.tokens import module_dark_tokens
    apply_qss(widget, "module_dark", theme=module_dark_tokens(),
              **_OVERRIDES, **_icon_overrides())


def style_run_bar(run_bar) -> None:
    """RunControlBar 视觉追加：开始=success 实心、进度条外置百分比徽章。

    进度条为 4px 高细条（QSS），不内嵌文字；新增百分比等宽标签插到其右侧，
    并经 ``valueChanged`` 同步（**纯显示**，不改 set_progress 数据流）。
    """
    run_bar.start_btn.setProperty("variant", "success")
    run_bar.progress.setTextVisible(False)
    # 就绪徽章 + 百分比徽章（沿用已有公开句柄，仅追加属性/控件）
    run_bar._current_label.setObjectName("runStateLabel")
    pct = QLabel("0%")
    pct.setProperty("role", "mono")
    run_bar._percent_label = pct
    run_bar.progress.valueChanged.connect(lambda v: pct.setText(f"{v}%"))
    lay = run_bar.layout()
    lay.insertWidget(lay.indexOf(run_bar.progress) + 1, pct)
    # 计数 chips：role 由容器修正到数值 QLabel（原共享实现把 role 打在容器上，
    # QSS QLabel[role=chip-*] 从未命中——纯视觉修复）；并由 watcher 在值 0 时
    # 追加 zero 弱色属性（不包 set_counts，避免破坏共享方法的替换语义）。
    for chip in (run_bar._pass_chip, run_bar._fail_chip, run_bar._skip_chip):
        role = chip.property("role")
        lbl = getattr(chip, "_count_label", None)
        if role and lbl is not None:
            chip.setProperty("role", None)
            lbl.setProperty("role", role)
            refresh_style(lbl)


# ------------------------------------------------------------------ 计数零值弱色
class _ChipZeroWatcher(QObject):
    """监听 chip 数值 QLabel 文本变化，值 0 时打 zero 属性（QSS 降弱色）。

    用 ``installEventFilter`` 在子页侧观察，不改共享 RunControlBar.set_counts。
    """

    def __init__(self, label: QLabel, parent=None):
        super().__init__(parent)
        self._label = label

    def eventFilter(self, obj, event) -> bool:
        if obj is self._label and event.type() == event.Type.Paint:
            zero = "true" if self._label.text() == "0" else "false"
            if self._label.property("zero") != zero:
                self._label.setProperty("zero", zero)
                refresh_style(self._label)
        return False


def watch_chip_zero(run_bar) -> None:
    """为 √/×/⊘ 计数 chip 挂零值弱色观察器（挂在 run_bar 生命周期上）。"""
    for chip in (run_bar._pass_chip, run_bar._fail_chip, run_bar._skip_chip):
        lbl = getattr(chip, "_count_label", None)
        if lbl is not None:
            w = _ChipZeroWatcher(lbl, parent=run_bar)
            lbl.installEventFilter(w)


# ------------------------------------------------------------------ 结果表行高
def style_result_table(result_table) -> None:
    """结果表行高 34px（与本页树表一致；共享 ResultTable 默认 26 不动）。"""
    view = result_table.view
    if isinstance(view, QTableView):
        vh = view.verticalHeader()
        vh.setDefaultSectionSize(dp(34))
        vh.setMinimumSectionSize(dp(34))


# ------------------------------------------------------------------ 表单（仅本页实例，零共享改动）
def style_form_rows(form_grid) -> None:
    """对指定 FormGrid 的既有行：标签右对齐 + 必填红星（仅作用于本页实例）。

    遍历 ``form_grid.rows()`` 拿到的 FormRow 实例，直接重设其 ``_label``
    的对齐/富文本——不 monkey-patch 共享 FormRow，不影响其它页面。
    """
    from PySide6.QtCore import Qt as _Qt
    from ui.theme.tokens import module_dark_tokens
    err = module_dark_tokens().state_error.fg
    for row in form_grid.rows():
        lbl = getattr(row, "_label", None)
        if lbl is None:
            continue
        lbl.setAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
        if row.is_required() and "*" not in lbl.text():
            base = lbl.text()
            lbl.setText(f'{base} <span style="color:{err};">*</span>')


# ------------------------------------------------------------------ Card 折叠箭头图标
_CARD_ARROW = {"open": "chevron-down.svg", "closed": "chevron-right.svg"}


def _set_card_arrow(card, expanded: bool) -> None:
    """把 Card 标题前缀的 ▼/▶ 文本换成 12px SVG chevron（仅视觉）。"""
    from ui.theme.tokens import module_dark_tokens
    from ui.utils.icon_utils import tinted_svg_icon
    btn = getattr(card, "_header_btn", None)
    if btn is None:
        return
    name = _CARD_ARROW["open" if expanded else "closed"]
    path = os.path.join(_icons_dir(), name)
    btn.setIcon(tinted_svg_icon(path, module_dark_tokens().text_muted, 12))
    # 去掉文本里的箭头前缀（Card._refresh_title 生成 "▼  标题"）
    text = btn.text()
    for arrow in ("▼", "▶"):
        if text.startswith(arrow):
            btn.setText(text[1:].lstrip())
            break


def _icons_dir() -> str:
    from ui.resource_path import get_resource_base
    return os.path.join(get_resource_base(), "resources", "icons")


def style_cards(subpage) -> None:
    """左栏三张可折叠 Card：箭头文本 → SVG chevron，并随 toggled 更新。"""
    rail = subpage.left_rail
    for card in (rail.connection_card, rail.config_card, rail.module_config_card):
        _set_card_arrow(card, card.is_expanded())
        card.toggled.connect(
            lambda expanded, c=card: _set_card_arrow(c, expanded))


# ------------------------------------------------------------------ 统一入口
def apply_subpage_extras(subpage) -> None:
    """子页装配末尾的纯视觉增强（全部由本页 helper 完成，不改共享控件源）。"""
    style_run_bar(subpage.run_bar)
    watch_chip_zero(subpage.run_bar)
    style_result_table(subpage.detail_dock.result_table)
    style_cards(subpage)
    # DUT 配置 + 高低温两个 FormGrid 的标签右对齐 / 必填红星（仅本页实例）
    dut = subpage.left_rail.dut_panel
    style_form_rows(dut._grid)
    style_form_rows(dut._temp_grid)

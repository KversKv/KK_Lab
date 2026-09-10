# -*- coding: utf-8 -*-
"""SerialLogPanel — 统一串口日志面板组件。

主面板 / 额外内嵌面板 / 独立浮窗三处共用同一实现：
- 工具栏（Filter/Copy/Export/Save?/Clear/Auto-scroll，可注入前导控件）
- 过滤行（full=Regex/Case/Invert/Highlight/前后文；simple=仅关键字，引擎一致）
- QTextEdit 日志区（append/着色/最大行数/100ms 批量刷新）
- auto-scroll（离底 5px 检测 + appending 守卫 + 冻结恢复）
- Copy/Export/Clear + RX/TX 字节计数状态栏

差异通过构造参数与钩子注入：
- entry_renderer(base_html, line_no, apply_filter_highlight)：主面板加行号/右键高亮
- ntp_timestamp_provider()：主面板 NTP 时间戳
- raw_appended 信号：主面板写日志文件
- export_fast_path()：主面板导出时优先复制临时日志
- save_toggled 信号：主面板手动保存开关
- clicked 信号：焦点切换（主面板/额外面板）
"""

import os
import re
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame, QGraphicsDropShadowEffect,
    QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton, QSpinBox, QTextEdit,
    QVBoxLayout, QWidget,
)
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QTextCursor

from log_config import get_logger
from ui.utils.icon_utils import tinted_svg_icon as _tinted_svg_icon
from ui.modules.serialCom_module.serialCom_module_frame import (
    _SC_HIGHLIGHT_PALETTE,
    _SVG_LOGS_DIR,
    _SVG_SERIAL_DIR,
    _CLR_BG_CARD,
    _CLR_BORDER,
    _CLR_BORDER_HOVER,
    _CLR_ERROR,
    _CLR_FILTER_BG,
    _CLR_FILTER_BORDER,
    _CLR_FILTER_TEXT,
    _CLR_INPUT_TEXT,
    _CLR_RX,
    _CLR_TEXT_ACCENT,
    _CLR_TEXT_BODY,
    _CLR_TEXT_BTN_LOG,
    _CLR_TEXT_INFO,
    _CLR_TEXT_LINENO,
    _CLR_TEXT_MUTED,
    _CLR_TEXT_TIME,
    _CLR_TX,
    _CLR_WARNING,
    _UI_FONT,
    SERIAL_SCROLLBAR_STYLE,
    auto_scroll_icon_colors,
    checkbox_style,
    compact_spinbox_style,
    filter_input_style,
    filter_match_label_style,
    log_document_style,
    log_edit_style,
    log_frame_style,
    log_icon_button_style,
    log_title_icon_color,
    log_title_style,
    section_card_shadow,
    separator_style,
    small_label_style,
    status_bar_style,
    status_label_style,
    transparent_background_style,
)

logger = get_logger(__name__)


def sc_format_bytes(prefix, n):
    if n < 1024:
        return f"{prefix}: {n} B"
    elif n < 1024 * 1024:
        return f"{prefix}: {n / 1024:.1f} KB"
    else:
        return f"{prefix}: {n / (1024 * 1024):.2f} MB"


class SerialLogPanel(QFrame):
    """统一串口日志面板（QFrame#scLogFrame，三处容器共用）。"""

    clicked = Signal()
    raw_appended = Signal(str)
    save_toggled = Signal(bool)
    cleared = Signal()

    _AUTO_COLORS = (
        ("[ERROR]", _CLR_ERROR),
        ("[WARN]", _CLR_WARNING),
        ("[INFO]", _CLR_TEXT_INFO),
        ("[TX]", _CLR_TX),
        ("[RX]", _CLR_RX),
    )

    def __init__(self, title="Serial Log", parent=None, *,
                 filter_mode="full",
                 show_save_button=False,
                 show_title=True,
                 status_bar="primary",
                 compact_toolbar=False,
                 with_border=False,
                 with_shadow=False,
                 max_lines=10000,
                 show_timestamp=True,
                 notify_on_copy_export=False,
                 edit_padding=None,
                 port_text=None,
                 baud_text=None):
        super().__init__(parent)
        self.setObjectName("scLogFrame")
        self.setStyleSheet(log_frame_style(with_border=with_border))

        if with_shadow:
            shadow_cfg = section_card_shadow()
            if shadow_cfg:
                shadow = QGraphicsDropShadowEffect(self)
                shadow.setBlurRadius(shadow_cfg["blur_radius"])
                shadow.setOffset(shadow_cfg["offset_x"], shadow_cfg["offset_y"])
                shadow.setColor(QColor(*shadow_cfg["color"]))
                self.setGraphicsEffect(shadow)

        # --- 日志存储 / 状态 ---
        self.filter_mode = filter_mode
        self.max_lines = max(1, int(max_lines))
        self.show_timestamp = bool(show_timestamp)
        self.notify_on_copy_export = bool(notify_on_copy_export)
        self.all_logs = []          # [(raw, html, line_no)]
        self.pending_html = []
        self.log_line_counter = 0
        self.auto_scroll = True
        self.appending = False
        self.rx_bytes = 0
        self.tx_bytes = 0
        # 过滤状态
        self.filter_applied_pattern = ""
        self.filter_applied_use_regex = False
        self.filter_applied_case = False
        self.filter_applied_invert = False
        self.filter_applied_highlight_only = False
        self.filter_applied_before = 0
        self.filter_applied_after = 0
        self.filter_dirty = False
        self.filter_last_count = 0
        # 右键关键词高亮（组件级，三处容器各自独立）：[{"keyword","bg","fg"}]
        self.highlight_keywords = []
        # 显示暂停（Pause 新语义）：True 时数据照常入 all_logs/写文件，但不渲染；
        # 恢复时全量重建视图，日志不丢失
        self.display_paused = False
        # 宿主钩子
        self.ntp_timestamp_provider = None   # callable() -> str
        self.entry_renderer = None           # callable(base_html, line_no, apply_filter_highlight) -> html
        self.export_fast_path = None         # callable() -> str | None
        self.context_menu_extra = None       # callable(QMenu)：宿主向日志右键菜单追加自定义项

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._build_toolbar(layout, title, show_title, show_save_button, compact_toolbar)
        self._build_filter_row(layout)
        self._build_log_edit(layout, edit_padding, compact_toolbar)
        self._build_status_bar(layout, status_bar, port_text, baud_text)

        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(100)
        self._flush_timer.timeout.connect(self.flush_pending)
        self._flush_timer.start()

    # ------------------------------------------------------------------ UI 构建

    def _build_toolbar(self, layout, title, show_title, show_save_button, compact):
        toolbar = QHBoxLayout()
        if compact:
            toolbar.setContentsMargins(6, 4, 6, 2)
            toolbar.setSpacing(4)
        else:
            toolbar.setContentsMargins(12, 10, 12, 8)
            toolbar.setSpacing(8)
        self._toolbar = toolbar

        if show_title:
            icon_label = QLabel()
            icon = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, "logs.svg"), log_title_icon_color(), 14)
            if not icon.isNull():
                icon_label.setPixmap(icon.pixmap(14, 14))
            icon_label.setFixedSize(16, 16)
            icon_label.setStyleSheet(transparent_background_style())
            toolbar.addWidget(icon_label)

            self.title_label = QLabel(title)
            self.title_label.setStyleSheet(log_title_style())
            toolbar.addWidget(self.title_label)
        else:
            self.title_label = None

        toolbar.addStretch()
        self._buttons_anchor = toolbar.count()  # 标准按钮插入起点（前导控件插在它前面）

        self.filter_btn = self._make_log_btn(
            "filter.svg", "Filter\nShow only log lines matching a keyword or regex",
            checkable=True, checked_variant="blue",
        )
        self.filter_btn.clicked.connect(self.set_filter_visible)
        self._add_toolbar_btn(self.filter_btn)

        self.copy_btn = self._make_log_btn("copy.svg", "Copy\nCopy all current log content to the clipboard")
        self.copy_btn.clicked.connect(self.copy_logs)
        self._add_toolbar_btn(self.copy_btn)

        self.export_btn = self._make_log_btn("export.svg", "Export\nSave the current log content as a file")
        self.export_btn.clicked.connect(self.export_logs)
        self._add_toolbar_btn(self.export_btn)

        self.save_btn = None
        if show_save_button:
            self.save_btn = self._make_log_btn(
                "save.svg", "Save\nSave logs to a file and keep appending new logs",
                checkable=True, checked_variant="blue",
            )
            self.save_btn.clicked.connect(self.save_toggled.emit)
            self._add_toolbar_btn(self.save_btn)

        self.clear_btn = self._make_log_btn("trash.svg", "Clear\nClear all log content in the console")
        self.clear_btn.clicked.connect(self.clear_logs)
        self._add_toolbar_btn(self.clear_btn)

        self.scroll_lock_btn = self._make_log_btn(
            "auto-scroll.svg", "Auto-scroll\nAutomatically scroll to the latest log line",
            checkable=True, checked_variant="green",
        )
        self.scroll_lock_btn.setChecked(True)
        self._bind_toggle_icon(
            self.scroll_lock_btn,
            os.path.join(_SVG_LOGS_DIR, "auto-scroll.svg"),
            auto_scroll_icon_colors(), 14,
        )
        self.scroll_lock_btn.clicked.connect(self._on_scroll_btn_clicked)
        self._add_toolbar_btn(self.scroll_lock_btn)

        layout.addLayout(toolbar)

    @staticmethod
    def _make_log_btn(svg_name, tooltip, checkable=False, checked_variant=None):
        btn = QPushButton("")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(log_icon_button_style(checked_variant=checked_variant, padding="6px"))
        icon = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, svg_name), _CLR_TEXT_BTN_LOG, 14)
        if not icon.isNull():
            btn.setIcon(icon)
        btn.setIconSize(QSize(14, 14))
        btn.setToolTip(tooltip)
        if checkable:
            btn.setCheckable(True)
        return btn

    @staticmethod
    def _bind_toggle_icon(btn, svg_path, colors, size):
        normal_color = colors.get("normal")
        checked_color = colors.get("checked")

        def _apply(checked):
            icon = _tinted_svg_icon(svg_path, checked_color if checked else normal_color, size)
            if not icon.isNull():
                btn.setIcon(icon)

        btn.toggled.connect(_apply)
        _apply(btn.isChecked())

    def _add_toolbar_btn(self, btn):
        self._toolbar.addWidget(btn)

    def add_toolbar_leading(self, widget):
        """在标准按钮组之前插入自定义控件（如独立浮窗的状态标签/Connect 按钮）。"""
        self._toolbar.insertWidget(self._buttons_anchor, widget)
        self._buttons_anchor += 1

    def _build_filter_row(self, layout):
        row = QWidget()
        row.setVisible(False)
        row.setStyleSheet(transparent_background_style())
        self.filter_row = row

        self.filter_input = QLineEdit()
        self.filter_input.setStyleSheet(filter_input_style())
        self.filter_match_label = QLabel("")
        self.filter_match_label.setStyleSheet(filter_match_label_style())

        if self.filter_mode == "full":
            self.filter_input.setPlaceholderText("Enter keyword or regex, press Enter to filter...")
            root = QVBoxLayout(row)
            root.setContentsMargins(12, 0, 12, 8)
            root.setSpacing(6)

            fl = QHBoxLayout()
            fl.setContentsMargins(0, 0, 0, 0)
            fl.setSpacing(8)
            fl.addWidget(self.filter_input, 1)
            fl.addWidget(self.filter_match_label)
            root.addLayout(fl)

            opts = QHBoxLayout()
            opts.setContentsMargins(0, 0, 0, 0)
            opts.setSpacing(10)

            chk_style = checkbox_style(os.path.join(_SVG_SERIAL_DIR, "checkmark.svg").replace("\\", "/"))
            self.filter_regex_cb = QCheckBox("Regex")
            self.filter_regex_cb.setStyleSheet(chk_style)
            self.filter_regex_cb.setToolTip("Enable regex matching")
            opts.addWidget(self.filter_regex_cb)

            self.filter_case_cb = QCheckBox("Match Case")
            self.filter_case_cb.setStyleSheet(chk_style)
            opts.addWidget(self.filter_case_cb)

            self.filter_invert_cb = QCheckBox("Invert")
            self.filter_invert_cb.setStyleSheet(chk_style)
            self.filter_invert_cb.setToolTip("Show non-matching lines")
            opts.addWidget(self.filter_invert_cb)

            self.filter_highlight_only_cb = QCheckBox("Highlight Only")
            self.filter_highlight_only_cb.setStyleSheet(chk_style)
            self.filter_highlight_only_cb.setToolTip(
                "Keep all logs visible, highlight matching text instead of filtering lines"
            )
            opts.addWidget(self.filter_highlight_only_cb)

            opts.addSpacing(8)
            sep = QFrame()
            sep.setFrameShape(QFrame.VLine)
            sep.setFixedHeight(14)
            sep.setStyleSheet(separator_style(transparent=True))
            opts.addWidget(sep)
            opts.addSpacing(4)

            before_lbl = QLabel("Before")
            before_lbl.setStyleSheet(small_label_style())
            opts.addWidget(before_lbl)
            self.filter_before_spin = QSpinBox()
            self.filter_before_spin.setRange(0, 999)
            self.filter_before_spin.setValue(0)
            self.filter_before_spin.setFixedSize(56, 24)
            self.filter_before_spin.setToolTip("Show N lines before matched lines")
            self.filter_before_spin.setStyleSheet(compact_spinbox_style(padding="0px 2px"))
            opts.addWidget(self.filter_before_spin)
            before_unit = QLabel("lines")
            before_unit.setStyleSheet(small_label_style(size=11))
            opts.addWidget(before_unit)

            opts.addSpacing(4)

            after_lbl = QLabel("After")
            after_lbl.setStyleSheet(small_label_style())
            opts.addWidget(after_lbl)
            self.filter_after_spin = QSpinBox()
            self.filter_after_spin.setRange(0, 999)
            self.filter_after_spin.setValue(0)
            self.filter_after_spin.setFixedSize(56, 24)
            self.filter_after_spin.setToolTip("Show N lines after matched lines")
            self.filter_after_spin.setStyleSheet(compact_spinbox_style(padding="0px 2px"))
            opts.addWidget(self.filter_after_spin)
            after_unit = QLabel("lines")
            after_unit.setStyleSheet(small_label_style(size=11))
            opts.addWidget(after_unit)

            opts.addStretch()
            root.addLayout(opts)

            self.filter_input.textChanged.connect(self._update_pending_hint)
            self.filter_regex_cb.toggled.connect(self._update_pending_hint)
            self.filter_case_cb.toggled.connect(self._update_pending_hint)
            self.filter_invert_cb.toggled.connect(self._update_pending_hint)
            self.filter_highlight_only_cb.toggled.connect(self._update_pending_hint)
            self.filter_before_spin.valueChanged.connect(self._update_pending_hint)
            self.filter_after_spin.valueChanged.connect(self._update_pending_hint)
        else:
            self.filter_input.setPlaceholderText("Enter keyword or regex...")
            fl = QHBoxLayout(row)
            fl.setContentsMargins(6, 0, 6, 4)
            fl.setSpacing(6)
            fl.addWidget(self.filter_input, 1)
            fl.addWidget(self.filter_match_label)
            self.filter_regex_cb = None
            self.filter_case_cb = None
            self.filter_invert_cb = None
            self.filter_highlight_only_cb = None
            self.filter_before_spin = None
            self.filter_after_spin = None

        self.filter_input.returnPressed.connect(self.apply_filter)
        layout.addWidget(row)

    def _build_log_edit(self, layout, edit_padding, compact):
        padding = edit_padding if edit_padding is not None else ("6px 8px" if compact else "8px 10px")
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.log_edit.setStyleSheet(log_edit_style(padding=padding) + SERIAL_SCROLLBAR_STYLE)
        self.log_edit.document().setDefaultStyleSheet(log_document_style())
        self.log_edit.document().setMaximumBlockCount(self.max_lines)
        layout.addWidget(self.log_edit, 1)

        if self.log_edit.verticalScrollBar():
            self.log_edit.verticalScrollBar().valueChanged.connect(self._on_user_scroll)

        # 右键菜单（Highlight 关键词 + 宿主追加项）
        self.log_edit.customContextMenuRequested.connect(self._on_log_context_menu)

        # 点击上报（焦点切换用），保留原 selection 行为
        _orig_press = self.log_edit.mousePressEvent

        def _press(event, orig=_orig_press):
            self.clicked.emit()
            orig(event)

        self.log_edit.mousePressEvent = _press

    def _build_status_bar(self, layout, kind, port_text, baud_text):
        self.status_bar = None
        self.status_port_label = None
        self.status_baud_label = None
        self.status_rx_label = None
        self.status_tx_label = None
        self.status_autobaud_label = None

        if kind in ("primary", "basic"):
            frame = QFrame()
            frame.setObjectName("scStatusBar")
            frame.setStyleSheet(status_bar_style())
            sb = QHBoxLayout(frame)
            if kind == "primary":
                frame.setFixedHeight(32)
                sb.setContentsMargins(12, 3, 12, 3)
                sb.setSpacing(18)
            else:
                frame.setFixedHeight(30)
                sb.setContentsMargins(12, 2, 12, 2)
                sb.setSpacing(16)

            self.status_port_label = QLabel(port_text or ("\u2022 Port: Unconnected" if kind == "primary" else "Port: Unconnected"))
            self.status_port_label.setStyleSheet(status_label_style("error", compact=True))
            sb.addWidget(self.status_port_label)

            self.status_baud_label = QLabel(baud_text or ("Baud rate (bps): -" if kind == "primary" else "Baud rate: -"))
            self.status_baud_label.setStyleSheet(status_label_style("muted", compact=(kind == "primary")))
            sb.addWidget(self.status_baud_label)

            self.status_rx_label = QLabel("RX: 0 B")
            self.status_rx_label.setStyleSheet(status_label_style("rx", compact=True))
            sb.addWidget(self.status_rx_label)

            self.status_tx_label = QLabel("TX: 0 B")
            self.status_tx_label.setStyleSheet(status_label_style("tx", compact=True))
            sb.addWidget(self.status_tx_label)

            if kind == "primary":
                self.status_autobaud_label = QLabel("")
                self.status_autobaud_label.setStyleSheet(status_label_style("accent", compact=True))
                self.status_autobaud_label.setVisible(False)
                sb.addWidget(self.status_autobaud_label)

            sb.addStretch()
            self.status_bar = frame
            layout.addWidget(frame)
        elif kind == "rxtx":
            row_widget = QWidget()
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            _style = f"color: {_CLR_TEXT_MUTED}; font-size: 11px;"
            self.status_rx_label = QLabel("RX: 0 B")
            self.status_rx_label.setStyleSheet(_style)
            self.status_tx_label = QLabel("TX: 0 B")
            self.status_tx_label.setStyleSheet(_style)
            row.addWidget(self.status_rx_label)
            row.addWidget(self.status_tx_label)
            row.addStretch()
            self.status_bar = row_widget
            layout.addWidget(row_widget)

    # ------------------------------------------------------------------ 点击上报

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    # ------------------------------------------------------------------ 追加 / 渲染

    def _auto_color(self, message):
        for tag, color in self._AUTO_COLORS:
            if tag in message:
                return color
        return _CLR_TEXT_BODY

    def append_log(self, message, color=None):
        """追加一条日志（color=None 时按 [TAG] 自动着色）。"""
        if color is None:
            color = self._auto_color(message)
        self.log_line_counter += 1
        line_no = self.log_line_counter
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3] if self.show_timestamp else ""
        ntp_ts = self.ntp_timestamp_provider() if self.ntp_timestamp_provider else ""
        escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        ts_html = f'<span style="color:{_CLR_TEXT_TIME};">{ts}</span> ' if ts else ""
        ntp_html = (
            f'<span style="color:{_CLR_TEXT_ACCENT};">[NTP]</span> '
            f'<span style="color:{_CLR_TEXT_TIME};">{ntp_ts}</span> '
            if ntp_ts else ""
        )
        html = f'{ts_html}{ntp_html}<span style="color:{color};">{escaped}</span>'
        prefix = ts
        if ntp_ts:
            prefix = f"{prefix} [NTP] {ntp_ts}" if prefix else f"[NTP] {ntp_ts}"
        raw = f"{prefix} {message}" if prefix else message

        self.all_logs.append((raw, html, line_no))
        if len(self.all_logs) > self.max_lines:
            del self.all_logs[:-self.max_lines]
        self.raw_appended.emit(raw)

        if self.display_paused:
            return
        if self.is_filter_active():
            self.filter_dirty = True
        else:
            self.pending_html.append(
                self.render_entry(html, line_no, apply_filter_highlight=self.is_highlight_only_active())
            )

    def append_rx_data(self, data: bytes):
        """接收字节流：计数 + 按行追加 [RX]（额外面板/独立浮窗路径）。"""
        self.add_rx_bytes(len(data))
        display = data.decode("utf-8", errors="replace")
        for line in display.splitlines():
            if line.strip():
                self.append_log(f"[RX] {line}", _CLR_RX)

    def render_entry(self, base_html, line_no, apply_filter_highlight=False):
        if self.entry_renderer is not None:
            return self.entry_renderer(base_html, line_no, apply_filter_highlight)
        return self.default_render_entry(base_html, line_no, apply_filter_highlight)

    def default_render_entry(self, base_html, line_no, apply_filter_highlight=False):
        return self.apply_highlights(base_html, apply_filter_highlight)

    def apply_highlights(self, html, apply_filter_highlight=False):
        """统一应用过滤高亮 + 右键关键词高亮（主面板 entry_renderer 亦复用）。"""
        if apply_filter_highlight and self.filter_applied_pattern:
            html = self.html_with_filter_highlight(
                html, self.filter_applied_pattern,
                self.filter_applied_use_regex, self.filter_applied_case,
            )
        return self.apply_keyword_highlights(html)

    def apply_keyword_highlights(self, html):
        """对所有右键高亮关键词着色，多关键词使用不同颜色。"""
        if not self.highlight_keywords:
            return html
        keywords = [kw["keyword"] for kw in self.highlight_keywords]
        try:
            combined = re.compile(
                '|'.join(re.escape(k) for k in keywords), re.IGNORECASE
            )
        except re.error:
            return html
        kw_lower_map = {}
        for kw_info in self.highlight_keywords:
            kw_lower_map[kw_info["keyword"].lower()] = kw_info

        parts = re.split(r'(<[^>]*>)', html)
        for idx, seg in enumerate(parts):
            if not seg or seg.startswith('<'):
                continue
            def _replace(m):
                matched = m.group(0)
                info = kw_lower_map.get(matched.lower())
                if info is None:
                    return matched
                return (
                    f'<span style="background-color:{info["bg"]};'
                    f'color:{info["fg"]};'
                    f'border-radius:2px;padding:0 1px;">{matched}</span>'
                )
            try:
                parts[idx] = combined.sub(_replace, seg)
            except re.error:
                continue
        return ''.join(parts)

    @staticmethod
    def html_with_filter_highlight(html, pattern, use_regex, case_sensitive):
        if not pattern:
            return html
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            source = pattern if use_regex else re.escape(pattern)
            compiled = re.compile(source, flags)
        except re.error:
            return html

        wrap_open = (
            f'<span style="background-color:{_CLR_FILTER_BG};'
            f'color:{_CLR_FILTER_TEXT};'
            f'border:1px solid {_CLR_FILTER_BORDER};'
            f'border-radius:2px;padding:0 1px;">'
        )
        wrap_close = '</span>'

        parts = re.split(r'(<[^>]*>)', html)
        for idx, seg in enumerate(parts):
            if not seg or seg.startswith('<'):
                continue
            try:
                parts[idx] = compiled.sub(
                    lambda m: f'{wrap_open}{m.group(0)}{wrap_close}', seg
                )
            except re.error:
                continue
        return ''.join(parts)

    # ------------------------------------------------------------------ 批量刷新

    def flush_pending(self):
        if self.is_filter_active():
            if self.filter_dirty:
                self.filter_dirty = False
                if self.filter_applied_before == 0 and self.filter_applied_after == 0:
                    self._flush_filter_incremental()
                else:
                    self.apply_filter()
        elif self.pending_html:
            batch = self.pending_html[:200]
            del self.pending_html[:200]
            self._append_html_batch(batch)

    def _append_html_batch(self, html_list):
        if not html_list:
            return
        sb = self.log_edit.verticalScrollBar()
        prev_value = sb.value() if sb else 0
        self.appending = True
        try:
            self.log_edit.setUpdatesEnabled(False)
            cursor = self.log_edit.textCursor()
            cursor.beginEditBlock()
            for html in html_list:
                self.log_edit.append(html)
            cursor.endEditBlock()
            self.log_edit.setUpdatesEnabled(True)
            if self.auto_scroll:
                self.scroll_to_bottom()
            elif sb:
                sb.setValue(prev_value)
        finally:
            self.appending = False

    def _flush_filter_incremental(self):
        pattern = self.filter_applied_pattern
        if not pattern:
            return
        compiled = self._compile_matcher(
            pattern, self.filter_applied_use_regex, self.filter_applied_case
        )

        start_idx = self.filter_last_count
        new_html = []
        new_match_count = 0
        for i in range(start_idx, len(self.all_logs)):
            raw = self.all_logs[i][0]
            if self._entry_matches(compiled, raw, pattern,
                                   self.filter_applied_use_regex,
                                   self.filter_applied_case,
                                   self.filter_applied_invert):
                new_match_count += 1
                new_html.append(self.render_entry(
                    self.all_logs[i][1], self.all_logs[i][2],
                    apply_filter_highlight=not self.filter_applied_invert,
                ))

        self.filter_last_count = len(self.all_logs)
        prev_text = self.filter_match_label.text()
        prev_count = 0
        if prev_text.startswith("Matched: "):
            try:
                prev_count = int(prev_text.split(":")[1].strip().split()[0])
            except (ValueError, IndexError):
                pass
        self.filter_match_label.setText(f"Matched: {prev_count + new_match_count} lines")

        if new_html:
            self._append_html_batch(new_html)

    # ------------------------------------------------------------------ 过滤

    @staticmethod
    def _compile_matcher(pattern, use_regex, case_sensitive):
        if not use_regex:
            return None
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            return re.compile(pattern, flags)
        except re.error:
            return None

    @staticmethod
    def _entry_matches(compiled, raw, pattern, use_regex, case_sensitive, invert):
        if compiled is not None:
            hit = bool(compiled.search(raw))
        elif case_sensitive:
            hit = pattern in raw
        else:
            hit = pattern.lower() in raw.lower()
        return (not hit) if invert else hit

    def matched_indices(self, pattern, use_regex, case_sensitive, invert):
        compiled = self._compile_matcher(pattern, use_regex, case_sensitive)
        if use_regex and compiled is None:
            return []
        return [
            i for i, (raw, _html, _no) in enumerate(self.all_logs)
            if self._entry_matches(compiled, raw, pattern, use_regex, case_sensitive, invert)
        ]

    def set_filter_visible(self, checked):
        self.filter_row.setVisible(checked)
        if not checked:
            self.filter_input.clear()
            self.filter_match_label.setText("")
            self.filter_dirty = False
            self.filter_last_count = len(self.all_logs)
            self._reset_applied_filter()
            self.rebuild_view()
        else:
            self.filter_input.setFocus()

    def _reset_applied_filter(self):
        self.filter_applied_pattern = ""
        self.filter_applied_use_regex = False
        self.filter_applied_case = False
        self.filter_applied_invert = False
        self.filter_applied_before = 0
        self.filter_applied_after = 0
        self.filter_applied_highlight_only = False

    def _filter_inputs_match_applied(self):
        if self.filter_mode != "full":
            return True
        return (
            self.filter_input.text().strip() == self.filter_applied_pattern
            and self.filter_regex_cb.isChecked() == self.filter_applied_use_regex
            and self.filter_case_cb.isChecked() == self.filter_applied_case
            and self.filter_invert_cb.isChecked() == self.filter_applied_invert
            and self.filter_highlight_only_cb.isChecked() == self.filter_applied_highlight_only
            and self.filter_before_spin.value() == self.filter_applied_before
            and self.filter_after_spin.value() == self.filter_applied_after
        )

    def _update_pending_hint(self, *_args):
        if not self.filter_row.isVisible():
            return
        if self._filter_inputs_match_applied():
            return
        self.filter_match_label.setText("Press Enter to apply")

    def apply_filter(self, _text=None):
        self.filter_dirty = False
        pattern = self.filter_input.text().strip()
        self.filter_applied_pattern = pattern
        if self.filter_mode == "full":
            self.filter_applied_use_regex = self.filter_regex_cb.isChecked()
            self.filter_applied_case = self.filter_case_cb.isChecked()
            self.filter_applied_invert = self.filter_invert_cb.isChecked()
            self.filter_applied_highlight_only = self.filter_highlight_only_cb.isChecked()
            self.filter_applied_before = self.filter_before_spin.value()
            self.filter_applied_after = self.filter_after_spin.value()
        else:
            self.filter_applied_use_regex = False
            self.filter_applied_case = False
            self.filter_applied_invert = False
            self.filter_applied_highlight_only = False
            self.filter_applied_before = 0
            self.filter_applied_after = 0

        if not pattern:
            self.filter_last_count = len(self.all_logs)
            self.rebuild_view()
            self.filter_match_label.setText("")
            return

        use_regex = self.filter_applied_use_regex
        case_sensitive = self.filter_applied_case
        invert = self.filter_applied_invert
        before = self.filter_applied_before
        after = self.filter_applied_after

        matched = self.matched_indices(pattern, use_regex, case_sensitive, invert)
        self.filter_match_label.setText(f"Matched: {len(matched)} lines")

        if self.filter_applied_highlight_only:
            self.filter_last_count = len(self.all_logs)
            self.rebuild_view()
            return

        matched_set = set(matched)
        visible = set()
        for idx in matched:
            start = max(0, idx - before)
            end = min(len(self.all_logs) - 1, idx + after)
            for i in range(start, end + 1):
                visible.add(i)

        html_list = []
        prev_shown = -2
        for i in sorted(visible):
            if (before > 0 or after > 0) and prev_shown >= 0 and i - prev_shown > 1:
                html_list.append(f'<span style="color:{_CLR_TEXT_LINENO};">  ───</span>')
            html_list.append(self.render_entry(
                self.all_logs[i][1], self.all_logs[i][2],
                apply_filter_highlight=(i in matched_set and not invert),
            ))
            prev_shown = i

        self.log_edit.setUpdatesEnabled(False)
        self.log_edit.clear()
        cursor = self.log_edit.textCursor()
        cursor.beginEditBlock()
        for html in html_list:
            self.log_edit.append(html)
        cursor.endEditBlock()
        self.log_edit.setUpdatesEnabled(True)
        self.filter_last_count = len(self.all_logs)
        if self.auto_scroll:
            self.scroll_to_bottom()

    def is_filter_active(self):
        if not self.filter_row.isVisible():
            return False
        if not self.filter_applied_pattern:
            return False
        if self.filter_applied_highlight_only:
            return False
        return True

    def is_highlight_only_active(self):
        return (self.filter_row.isVisible()
                and bool(self.filter_applied_pattern)
                and self.filter_applied_highlight_only)

    def rebuild_view(self):
        highlight_only = self.is_highlight_only_active()
        html_list = [
            self.render_entry(html, line_no, apply_filter_highlight=highlight_only)
            for _raw, html, line_no in self.all_logs
        ]
        self.log_edit.setUpdatesEnabled(False)
        self.log_edit.clear()
        cursor = self.log_edit.textCursor()
        cursor.beginEditBlock()
        for html in html_list:
            self.log_edit.append(html)
        cursor.endEditBlock()
        self.log_edit.setUpdatesEnabled(True)
        if self.auto_scroll:
            self.scroll_to_bottom()

    # ------------------------------------------------------------------ Copy / Export / Clear

    def copy_logs(self):
        cb = QApplication.clipboard()
        if not cb:
            return
        lines = []
        if self.is_filter_active():
            before = self.filter_applied_before
            after = self.filter_applied_after
            matched = self.matched_indices(
                self.filter_applied_pattern, self.filter_applied_use_regex,
                self.filter_applied_case, self.filter_applied_invert,
            )
            visible = set()
            for idx in matched:
                start = max(0, idx - before)
                end = min(len(self.all_logs) - 1, idx + after)
                for i in range(start, end + 1):
                    visible.add(i)
            prev_shown = -2
            for i in sorted(visible):
                if (before > 0 or after > 0) and prev_shown >= 0 and i - prev_shown > 1:
                    lines.append("  ───")
                lines.append(self.all_logs[i][0])
                prev_shown = i
        else:
            for raw, _html, _no in self.all_logs:
                lines.append(raw)
        if lines:
            cb.setText("\n".join(lines))
            if self.notify_on_copy_export:
                self.append_log("[INFO] Log copied to clipboard", _CLR_TEXT_INFO)

    def export_logs(self):
        if self.filter_mode == "full":
            default_name = f"serial_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            name_filter = "Text Files (*.txt);;All Files (*)"
        else:
            default_name = f"{self._title_slug()}.log"
            name_filter = "Log Files (*.log);;Text Files (*.txt);;All (*.*)"
        path, _ = QFileDialog.getSaveFileName(self, "Export Log", default_name, name_filter)
        if not path:
            return
        try:
            fast = self.export_fast_path() if self.export_fast_path else None
            if fast and os.path.isfile(fast):
                import shutil
                shutil.copy2(fast, path)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    for raw, _html, _no in self.all_logs:
                        f.write(raw + "\n")
            if self.notify_on_copy_export:
                self.append_log(f"[INFO] Log exported: {path}", _CLR_TEXT_INFO)
        except OSError as e:
            if self.notify_on_copy_export:
                self.append_log(f"[ERROR] Export failed: {e}", _CLR_ERROR)
            else:
                logger.error("Export log failed: %s", e, exc_info=True)

    def _title_slug(self):
        title = self.title_label.text() if self.title_label is not None else "serial_log"
        return (title or "serial_log").replace(" ", "_").lower()

    def clear_logs(self):
        self.all_logs.clear()
        self.pending_html.clear()
        self.log_edit.clear()
        self.log_line_counter = 0
        self.reset_byte_counters()
        self.filter_last_count = 0
        self.filter_dirty = False
        self.filter_match_label.setText("")
        self._reset_applied_filter()
        self.auto_scroll = True
        self.scroll_lock_btn.setChecked(True)
        self.cleared.emit()

    # ------------------------------------------------------------------ 右键关键词高亮

    def add_highlight_keyword(self, keyword):
        """添加右键高亮关键词，自动分配调色板中的颜色。"""
        keyword = keyword.strip()
        if not keyword or len(keyword) > 200:
            return
        for kw_info in self.highlight_keywords:
            if kw_info["keyword"].lower() == keyword.lower():
                return
        idx = len(self.highlight_keywords) % len(_SC_HIGHLIGHT_PALETTE)
        bg, fg = _SC_HIGHLIGHT_PALETTE[idx]
        self.highlight_keywords.append({"keyword": keyword, "bg": bg, "fg": fg})
        self.rebuild_view()

    def remove_highlight_keyword(self, keyword):
        """移除指定右键高亮关键词（原地修改，保持与宿主的共享引用）。"""
        self.highlight_keywords[:] = [
            kw for kw in self.highlight_keywords
            if kw["keyword"].lower() != keyword.lower()
        ]
        self.rebuild_view()

    def clear_highlight_keywords(self):
        """清除所有右键高亮关键词。"""
        if not self.highlight_keywords:
            return
        self.highlight_keywords.clear()
        self.rebuild_view()

    def _on_log_context_menu(self, pos):
        """日志区右键菜单：高亮选中词 / 管理已有高亮 + 宿主追加项。"""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {_CLR_BG_CARD}; border: 1px solid {_CLR_BORDER_HOVER};
                border-radius: 6px; padding: 4px 0px;
            }}
            QMenu::item {{
                padding: 6px 20px; color: {_CLR_INPUT_TEXT}; font-size: 12px; font-family: {_UI_FONT};
            }}
            QMenu::item:selected {{
                background-color: {_CLR_BORDER}; color: #ffffff;
            }}
            QMenu::separator {{
                height: 1px; background: {_CLR_BORDER}; margin: 4px 8px;
            }}
        """)
        cursor = self.log_edit.textCursor()
        word = ""
        if cursor.hasSelection():
            word = cursor.selectedText().strip()
        if not word:
            try:
                cursor = self.log_edit.cursorForPosition(pos)
                cursor.select(QTextCursor.WordUnderCursor)
                word = cursor.selectedText().strip()
            except Exception:
                word = ""
        if word:
            display = word if len(word) <= 40 else word[:37] + "..."
            act = QAction(f'Highlight "{display}"', self)
            act.triggered.connect(lambda checked, w=word: self.add_highlight_keyword(w))
            menu.addAction(act)
        if self.highlight_keywords:
            if word:
                menu.addSeparator()
            for kw_info in self.highlight_keywords:
                kw = kw_info["keyword"]
                display = kw if len(kw) <= 40 else kw[:37] + "..."
                act = QAction(f'Remove "{display}"', self)
                act.triggered.connect(
                    lambda checked, k=kw: self.remove_highlight_keyword(k)
                )
                menu.addAction(act)
            menu.addSeparator()
            clear_act = QAction("Clear All Highlights", self)
            clear_act.triggered.connect(self.clear_highlight_keywords)
            menu.addAction(clear_act)

        has_highlight_items = bool(word) or bool(self.highlight_keywords)
        if self.context_menu_extra is not None:
            if has_highlight_items:
                menu.addSeparator()
            self.context_menu_extra(menu)

        if menu.isEmpty():
            return
        menu.exec(self.log_edit.mapToGlobal(pos))

    # ------------------------------------------------------------------ 显示暂停（Pause）

    def set_display_paused(self, paused):
        """Pause 新语义：暂停渲染但保留数据；恢复时全量重建视图，日志不丢失。"""
        paused = bool(paused)
        if paused == self.display_paused:
            return
        self.display_paused = paused
        if not paused:
            if self.is_filter_active():
                self.apply_filter()
            else:
                self.rebuild_view()

    # ------------------------------------------------------------------ 滚动

    def _on_scroll_btn_clicked(self, checked):
        self.auto_scroll = checked
        if checked:
            self.scroll_to_bottom()

    def set_auto_scroll(self, checked):
        self.auto_scroll = bool(checked)
        self.scroll_lock_btn.setChecked(bool(checked))
        if checked:
            self.scroll_to_bottom()

    def _on_user_scroll(self, value):
        if self.appending:
            return
        sb = self.log_edit.verticalScrollBar()
        if sb and sb.maximum() > 0:
            at_bottom = value >= sb.maximum() - 5
            if not at_bottom and self.auto_scroll:
                self.auto_scroll = False
                self.scroll_lock_btn.setChecked(False)
            elif at_bottom and not self.auto_scroll:
                self.auto_scroll = True
                self.scroll_lock_btn.setChecked(True)

    def scroll_to_bottom(self):
        sb = self.log_edit.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    # ------------------------------------------------------------------ 状态栏 / 配置

    def add_rx_bytes(self, n):
        self.rx_bytes += n
        if self.status_rx_label is not None:
            self.status_rx_label.setText(sc_format_bytes("RX", self.rx_bytes))

    def add_tx_bytes(self, n):
        self.tx_bytes += n
        if self.status_tx_label is not None:
            self.status_tx_label.setText(sc_format_bytes("TX", self.tx_bytes))

    def reset_byte_counters(self):
        self.rx_bytes = 0
        self.tx_bytes = 0
        if self.status_rx_label is not None:
            self.status_rx_label.setText("RX: 0 B")
        if self.status_tx_label is not None:
            self.status_tx_label.setText("TX: 0 B")

    def set_max_lines(self, value):
        value = max(1, int(value))
        self.max_lines = value
        self.log_edit.document().setMaximumBlockCount(value)
        if len(self.all_logs) > value:
            del self.all_logs[:-value]
            if not self.is_filter_active():
                self.rebuild_view()

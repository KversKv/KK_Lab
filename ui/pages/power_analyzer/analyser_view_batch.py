#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QLabel, QPushButton, QMenu,
)
from PySide6.QtCore import Qt
from log_config import get_logger
from ui.pages.power_analyzer.widgets import (
    _batch_channel_button_style,
    collapsible_header_style,
    SelectAllLineEdit,
    SYNC_GROUP_COLORS,
    PANEL_BG, PANEL_BORDER, CONTAINER_RADIUS, WIDGET_RADIUS,
    CARD_BG, CARD_BORDER, LABEL_DIM,
    DISABLED_TEXT, DISABLED_BTN_BG, DISABLED_BTN_BORDER,
)
from ui.pages.power_analyzer.datalog_style import menu_style

logger = get_logger(__name__)


def _batch_input_style(slave_border=None):
    """Quick Setup 电压/限流输入框样式；slave_border 给从通道描同步组色边框。"""
    disabled_border = slave_border if slave_border else DISABLED_BTN_BORDER
    return f"""
        QLineEdit {{
            background-color: #111d36; color: #99aacc;
            border: 1px solid #1e3050; border-radius: {WIDGET_RADIUS};
            padding: 3px 4px; font-size: 11px; font-weight: 600;
            text-align: center;
        }}
        QLineEdit:focus {{ border: 1px solid #3a5a90; color: #b0c0e0; }}
        QLineEdit:disabled {{ background-color: #0b1730; color: {DISABLED_TEXT}; border: 1px solid {disabled_border}; }}
    """


class BatchViewMixin:
    _AUTO_SET_SPECIAL_VOLTAGES = [0.625, 0.67, 0.725, 0.78]

    def _create_batch_tools_panel(self):
        self.batch_collapsed = False

        outer = QWidget()
        outer.setStyleSheet("QWidget { background: #0b1020; border: none; }")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.batch_toggle_btn = QPushButton("\u25bc  Quick Setup")
        self.batch_toggle_btn.setStyleSheet(collapsible_header_style(False))
        self.batch_toggle_btn.clicked.connect(self._toggle_batch_panel)
        outer_layout.addWidget(self.batch_toggle_btn)

        self.batch_content = QFrame()
        self.batch_content.setStyleSheet(f"""
            QFrame {{
                background-color: {PANEL_BG};
                border: 1px solid {PANEL_BORDER};
                border-top: none;
                border-bottom-left-radius: {CONTAINER_RADIUS};
                border-bottom-right-radius: {CONTAINER_RADIUS};
            }}
        """)
        # setVisible 推迟到 outer_layout.addWidget(self.batch_content) 之后
        # （见本文件末尾，紧随 addWidget 的 setVisible(not self.batch_collapsed)）：
        # 此处 batch_content 尚无 parent，setVisible(True) 会让它独立成顶层窗口
        # 闪现（standalone / main.py 启动均可见，640×480 白框一闪而过）。见 03§31。

        content_layout = QVBoxLayout(self.batch_content)
        content_layout.setContentsMargins(10, 8, 10, 8)
        content_layout.setSpacing(8)

        self.batch_channel_buttons = []
        self.batch_voltage_inputs = {}
        self.batch_current_inputs = {}
        # 通道同步组：dev_label -> [set(ch, ...), ...]；页面级状态，重建矩阵不丢
        if not hasattr(self, "_batch_sync_groups"):
            self._batch_sync_groups = {}

        self._batch_columns_widget = QWidget()
        self._batch_columns_widget.setStyleSheet("QWidget { background: transparent; border: none; }")
        self._batch_columns_layout = QHBoxLayout(self._batch_columns_widget)
        self._batch_columns_layout.setContentsMargins(0, 0, 0, 0)
        self._batch_columns_layout.setSpacing(8)
        content_layout.addWidget(self._batch_columns_widget)

        self._build_batch_columns()

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {PANEL_BORDER}; border: none;")
        content_layout.addWidget(sep)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(6)

        self._batch_measure_btn = QPushButton("Measure")
        self._batch_set_btn = QPushButton("Set")
        self._batch_auto_btn = QPushButton("Auto Set")
        self._batch_auto_20mv_btn = QPushButton("Auto Set (+20mV)")

        _batch_btn_base = f"""
            QPushButton {{{{
                background-color: {{bg}}; color: {{fg}};
                border: 1px solid {{border}}; border-radius: {WIDGET_RADIUS};
                padding: 4px 10px; font-size: 11px; font-weight: 700;
            }}}}
            QPushButton:hover {{{{ background-color: {{hover_bg}}; color: {{hover_fg}}; border: 1px solid {{hover_border}}; }}}}
            QPushButton:disabled {{{{ background-color: {DISABLED_BTN_BG}; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}}}
        """

        self._batch_measure_btn.setStyleSheet(_batch_btn_base.format(
            bg="#0c1a38", fg="#8eb4e8", border="#23417a",
            hover_bg="#122448", hover_fg="#b8d4ff", hover_border="#3a6cc8"
        ))
        self._batch_set_btn.setStyleSheet(_batch_btn_base.format(
            bg="#0c1a38", fg="#8eb4e8", border="#23417a",
            hover_bg="#122448", hover_fg="#b8d4ff", hover_border="#3a6cc8"
        ))
        _batch_auto_style = f"""
            QPushButton {{
                background-color: #4318d9; color: #ffffff;
                border: 1px solid #5a2ef0; border-radius: {WIDGET_RADIUS};
                padding: 4px 12px; font-size: 11px; font-weight: 700;
            }}
            QPushButton:hover {{ background-color: #5628f0; color: #ffffff; border: 1px solid #7040ff; }}
            QPushButton:disabled {{ background-color: #1a1040; color: #4a3a7a; border: 1px solid #2a1860; }}
        """
        self._batch_auto_btn.setStyleSheet(_batch_auto_style)
        self._batch_auto_20mv_btn.setStyleSheet(_batch_auto_style)

        buttons_layout.addWidget(self._batch_measure_btn, 1)
        buttons_layout.addWidget(self._batch_set_btn, 1)
        buttons_layout.addWidget(self._batch_auto_btn, 1)
        buttons_layout.addWidget(self._batch_auto_20mv_btn, 1)

        self._batch_measure_btn.clicked.connect(self._on_batch_measure)
        self._batch_set_btn.clicked.connect(self._on_batch_set)
        self._batch_auto_btn.clicked.connect(self._on_batch_auto_set)
        self._batch_auto_20mv_btn.clicked.connect(self._on_batch_auto_20mv)

        content_layout.addLayout(buttons_layout)

        outer_layout.addWidget(self.batch_content)
        return outer

    def _toggle_batch_panel(self):
        self.batch_collapsed = not self.batch_collapsed
        self.batch_content.setVisible(not self.batch_collapsed)
        if self.batch_collapsed:
            self.batch_toggle_btn.setText("\u25b6  Quick Setup")
        else:
            self.batch_toggle_btn.setText("\u25bc  Quick Setup")
        self.batch_toggle_btn.setStyleSheet(collapsible_header_style(self.batch_collapsed))

    def _build_batch_columns(self):
        for i in reversed(range(self._batch_columns_layout.count())):
            item = self._batch_columns_layout.takeAt(i)
            w = item.widget()
            if w:
                w.deleteLater()

        self.batch_channel_buttons.clear()
        self.batch_voltage_inputs.clear()
        self.batch_current_inputs.clear()

        _label_style = f"font-size: 11px; color: {LABEL_DIM}; font-weight: 600; border: none; background: transparent;"
        _input_style = _batch_input_style()

        dual = self._is_dual_mode()
        if dual:
            device_list = [("A", "#00f5c4"), ("B", "#f2994a")]
        else:
            single_label = self._get_single_device_label()
            device_list = [(single_label, "#00f5c4")]

        default_voltages = [3.8, 0.8, 1.2, 1.8, 3.3, 1.8, 1.2, 0.8]
        default_currents = [0.2, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02]

        for dev_label, dev_color in device_list:
            channels = self._channels_for_device(dev_label)
            dev_frame = QFrame()
            dev_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {CARD_BG};
                    border: 1px solid {CARD_BORDER};
                    border-radius: {CONTAINER_RADIUS};
                }}
            """)
            grid = QGridLayout(dev_frame)
            grid.setContentsMargins(8, 6, 8, 6)
            grid.setHorizontalSpacing(4)
            grid.setVerticalSpacing(4)

            row = 0
            if dual:
                col_title = QLabel(f"Device {dev_label}")
                col_title.setStyleSheet(f"color: {dev_color}; font-weight: 800; font-size: 13px; border: none; background: transparent;")
                grid.addWidget(col_title, row, 0, 1, len(channels) + 1)
                row += 1

            ch_label = QLabel("通道选择")
            ch_label.setStyleSheet(_label_style)
            ch_label.setFixedWidth(56)
            grid.addWidget(ch_label, row, 0)
            for col_idx, ch_idx in enumerate(channels):
                cb = QPushButton(f"CH {ch_idx}")
                cb.setCheckable(True)
                supported = self._is_channel_supported(dev_label, ch_idx)
                cb.setChecked(
                    supported and dev_label != "B" and ch_idx in [2, 3, 4]
                )
                cb.setEnabled(supported)
                cb.setToolTip(self._channel_module_tooltip(dev_label, ch_idx))
                cb.setStyleSheet(_batch_channel_button_style())
                cb.setContextMenuPolicy(Qt.CustomContextMenu)
                cb.customContextMenuRequested.connect(
                    lambda pos, dl=dev_label, c=ch_idx, b=cb:
                    self._show_batch_channel_menu(dl, c, b, pos)
                )
                self.batch_channel_buttons.append((dev_label, ch_idx, cb))
                grid.addWidget(cb, row, col_idx + 1)
            row += 1

            v_label = QLabel("电压 (V)")
            v_label.setStyleSheet(_label_style)
            v_label.setFixedWidth(56)
            grid.addWidget(v_label, row, 0)
            self.batch_voltage_inputs[dev_label] = []
            for col_idx, v in enumerate(default_voltages[:len(channels)]):
                inp = SelectAllLineEdit(f"{v:.4f}")
                inp.setAlignment(Qt.AlignCenter)
                inp.setStyleSheet(_input_style)
                inp.setEnabled(self._is_channel_supported(dev_label, channels[col_idx]))
                inp.textChanged.connect(
                    lambda _t, dl=dev_label, c=channels[col_idx]:
                    self._on_batch_input_text_changed(dl, c)
                )
                self.batch_voltage_inputs[dev_label].append(inp)
                grid.addWidget(inp, row, col_idx + 1)
            row += 1

            c_label = QLabel("限流 (A)")
            c_label.setStyleSheet(_label_style)
            c_label.setFixedWidth(56)
            grid.addWidget(c_label, row, 0)
            self.batch_current_inputs[dev_label] = []
            for col_idx, c in enumerate(default_currents[:len(channels)]):
                inp = SelectAllLineEdit(f"{c:.4f}")
                inp.setAlignment(Qt.AlignCenter)
                inp.setStyleSheet(_input_style)
                inp.setEnabled(self._is_channel_supported(dev_label, channels[col_idx]))
                inp.textChanged.connect(
                    lambda _t, dl=dev_label, c=channels[col_idx]:
                    self._on_batch_input_text_changed(dl, c)
                )
                self.batch_current_inputs[dev_label].append(inp)
                grid.addWidget(inp, row, col_idx + 1)

            for col in range(1, len(channels) + 1):
                grid.setColumnStretch(col, 1)

            self._batch_columns_layout.addWidget(dev_frame, 1)

    def _get_selected_batch_channels(self, dev_label):
        return [
            ch for dl, ch, cb in self.batch_channel_buttons
            if dl == dev_label and cb.isEnabled() and cb.isChecked()
        ]

    # ---- 通道同步（Quick Setup 右键菜单） ----------------------------------

    def _batch_sync_group_of(self, dev_label, ch):
        for group in self._batch_sync_groups.get(dev_label, []):
            if ch in group:
                return group
        return None

    def _batch_sync_master_map(self, dev_label):
        """返回 {从通道: 主通道}；主通道 = 组内序号最小者。"""
        mapping = {}
        for group in self._batch_sync_groups.get(dev_label, []):
            if len(group) < 2:
                continue
            master = min(group)
            for ch in group:
                if ch != master:
                    mapping[ch] = master
        return mapping

    def _batch_sync_group_color(self, dev_label, ch):
        """返回通道所在同步组的 (边框, 选中边框) 配色；不在组内返回 None。"""
        groups = self._batch_sync_groups.get(dev_label, [])
        for idx, group in enumerate(groups):
            if ch in group and len(group) >= 2:
                return SYNC_GROUP_COLORS[idx % len(SYNC_GROUP_COLORS)]
        return None

    def _prune_batch_sync_groups(self):
        """剔除已连接设备中不再可用的成员；不足 2 个通道的组解散。

        断连设备的分组原样保留，重连后按新可用通道再裁剪。
        """
        for dev_label in list(self._batch_sync_groups.keys()):
            dev = self.devices.get(dev_label, {})
            if not dev.get("is_connected"):
                continue
            valid = set(self._supported_channels_for_device(dev_label))
            pruned = []
            for group in self._batch_sync_groups[dev_label]:
                group &= valid
                if len(group) >= 2:
                    pruned.append(group)
            if pruned:
                self._batch_sync_groups[dev_label] = pruned
            else:
                self._batch_sync_groups.pop(dev_label, None)

    def _show_batch_channel_menu(self, dev_label, ch, button, pos):
        menu = QMenu(button)
        menu.setStyleSheet(menu_style(small=True))
        sync_menu = menu.addMenu("Sync")
        group = self._batch_sync_group_of(dev_label, ch)
        others = [
            c for c in self._supported_channels_for_device(dev_label) if c != ch
        ]
        if not others:
            sync_menu.setEnabled(False)
        else:
            for other in others:
                act = sync_menu.addAction(f"CH {other}")
                act.setCheckable(True)
                act.setChecked(group is not None and other in group)
                act.toggled.connect(
                    lambda checked, o=other:
                    self._toggle_batch_sync(dev_label, ch, o, checked)
                )
        menu.exec(button.mapToGlobal(pos))

    def _toggle_batch_sync(self, dev_label, ch, other, checked):
        groups = self._batch_sync_groups.setdefault(dev_label, [])
        g_ch = next((g for g in groups if ch in g), None)
        g_other = next((g for g in groups if other in g), None)
        if checked:
            if g_ch is None and g_other is None:
                groups.append({ch, other})
            elif g_ch is not None and g_other is None:
                g_ch.add(other)
            elif g_ch is None:
                g_other.add(ch)
            elif g_ch is not g_other:
                g_ch |= g_other
                groups.remove(g_other)
            logger.info(
                "[%s] CH%d synced with CH%d (group: %s)",
                dev_label, ch, other,
                sorted(next(g for g in groups if ch in g)),
            )
        else:
            if g_ch is not None and other in g_ch:
                g_ch.discard(other)
                if len(g_ch) < 2:
                    groups.remove(g_ch)
                logger.info(
                    "[%s] CH%d removed from sync group of CH%d",
                    dev_label, other, ch,
                )
        if not groups:
            self._batch_sync_groups.pop(dev_label, None)
        self._apply_batch_sync_ui()

    def _on_batch_input_text_changed(self, dev_label, ch):
        """主通道输入变化时，把值镜像给同组从通道的输入框。"""
        group = self._batch_sync_group_of(dev_label, ch)
        if group is None or ch != min(group):
            return
        channels = self._channels_for_device(dev_label)
        if ch not in channels:
            return
        m_idx = channels.index(ch)
        for inputs in (
            self.batch_voltage_inputs.get(dev_label, []),
            self.batch_current_inputs.get(dev_label, []),
        ):
            if m_idx >= len(inputs):
                continue
            text = inputs[m_idx].text()
            for slave in group:
                if slave == ch or slave not in channels:
                    continue
                s_idx = channels.index(slave)
                if s_idx < len(inputs) and inputs[s_idx].text() != text:
                    inputs[s_idx].setText(text)

    def _apply_batch_sync_ui(self):
        """把同步状态落到 Quick Setup 矩阵：按钮高亮 + 从通道输入禁用并镜像主通道值。"""
        buttons = getattr(self, "batch_channel_buttons", None)
        if not buttons:
            return
        self._prune_batch_sync_groups()
        dev_labels = []
        for dl, _ch, _btn in buttons:
            if dl not in dev_labels:
                dev_labels.append(dl)
        for dl in dev_labels:
            master_map = self._batch_sync_master_map(dl)
            masters = set(master_map.values())
            channels = self._channels_for_device(dl)
            for bdl, ch, btn in buttons:
                if bdl != dl:
                    continue
                color = self._batch_sync_group_color(dl, ch)
                btn.setStyleSheet(
                    _batch_channel_button_style(synced=color is not None, sync_color=color)
                )
                tooltip = self._channel_module_tooltip(dl, ch)
                if ch in master_map:
                    tooltip += f" · Synced to CH {master_map[ch]}"
                elif ch in masters:
                    group = self._batch_sync_group_of(dl, ch)
                    followers = sorted(g for g in group if g != ch)
                    tooltip += " · Sync master (also sets " + ", ".join(
                        f"CH {c}" for c in followers
                    ) + ")"
                btn.setToolTip(tooltip)
            for input_group in ("batch_voltage_inputs", "batch_current_inputs"):
                inputs = getattr(self, input_group, {}).get(dl, [])
                for idx, ch in enumerate(channels):
                    if idx >= len(inputs):
                        continue
                    edit = inputs[idx]
                    master = master_map.get(ch)
                    if master is None:
                        edit.setEnabled(self._is_channel_supported(dl, ch))
                        edit.setStyleSheet(_batch_input_style())
                    else:
                        edit.setEnabled(False)
                        edit.setToolTip(f"Synced to CH {master}")
                        color = self._batch_sync_group_color(dl, ch)
                        edit.setStyleSheet(
                            _batch_input_style(slave_border=color[0] if color else None)
                        )
                        if master in channels:
                            m_idx = channels.index(master)
                            if m_idx < len(inputs) and edit.text() != inputs[m_idx].text():
                                edit.setText(inputs[m_idx].text())

    def _expand_batch_sync_channels(self, dev_label, selected):
        """任一组成员被选中即整组生效，返回排序后的完整通道列表。"""
        effective = set(selected)
        for group in self._batch_sync_groups.get(dev_label, []):
            if len(group) >= 2 and effective & group:
                effective |= group
        return sorted(effective)

    def _on_batch_measure(self):
        with self._state_poller.writing():
            for label, dev in self.devices.items():
                if not dev["is_connected"] or not dev["n6705c"]:
                    continue
                channels = self._get_selected_batch_channels(label)
                for ch in channels:
                    try:
                        dev["n6705c"].set_mode(ch, "VMETer")
                        dev["n6705c"].channel_on(ch)
                    except Exception as e:
                        logger.error("[%s] CH%d VMeter failed: %s", label, ch, e)
        self._start_channel_sync()

    def _on_batch_set(self):
        with self._state_poller.writing():
            for label, dev in self.devices.items():
                if not dev["is_connected"] or not dev["n6705c"]:
                    continue
                channels = self._expand_batch_sync_channels(
                    label, self._get_selected_batch_channels(label)
                )
                if label not in self.batch_voltage_inputs:
                    continue
                voltages = [float(inp.text()) for inp in self.batch_voltage_inputs[label]]
                currents = [float(inp.text()) for inp in self.batch_current_inputs[label]]
                master_map = self._batch_sync_master_map(label)
                for ch in channels:
                    try:
                        src = master_map.get(ch, ch)
                        idx = src - 1
                        dev["n6705c"].set_mode(ch, "PS2Q")
                        dev["n6705c"].set_voltage(ch, voltages[idx])
                        dev["n6705c"].set_current_limit(ch, currents[idx])
                        dev["n6705c"].channel_on(ch)
                    except Exception as e:
                        logger.error("[%s] CH%d Set failed: %s", label, ch, e)
        self._start_channel_sync()

    def _on_batch_auto_20mv(self):
        self._on_batch_auto_with_offset(0.02)

    @staticmethod
    def _align_voltage(v, special_values=None):
        if special_values is None:
            special_values = BatchViewMixin._AUTO_SET_SPECIAL_VOLTAGES
        grid_v = round(round(v / 0.05) * 0.05, 4)
        best = grid_v
        best_dist = abs(v - grid_v)
        for sv in special_values:
            dist = abs(v - sv)
            if dist < best_dist:
                best = sv
                best_dist = dist
        return best

    def _on_batch_auto_set(self):
        with self._state_poller.writing():
            for label, dev in self.devices.items():
                if not dev["is_connected"] or not dev["n6705c"]:
                    continue
                channels = self._get_selected_batch_channels(label)
                if label not in self.batch_current_inputs:
                    continue
                currents = [float(inp.text()) for inp in self.batch_current_inputs[label]]
                for ch in channels:
                    try:
                        dev["n6705c"].set_mode(ch, "VMETer")
                        v = float(dev["n6705c"].measure_voltage(ch))
                        new_v = self._align_voltage(v)
                        dev["n6705c"].set_mode(ch, "PS2Q")
                        dev["n6705c"].set_voltage(ch, new_v)
                        dev["n6705c"].set_current_limit(ch, 0.02)
                        dev["n6705c"].channel_on(ch)
                        dev["n6705c"].set_current_limit(ch, currents[ch - 1])
                    except Exception as e:
                        logger.error("[%s] CH%d Auto Set failed: %s", label, ch, e)
        self._start_channel_sync()

    def _on_batch_auto_with_offset(self, offset):
        with self._state_poller.writing():
            for label, dev in self.devices.items():
                if not dev["is_connected"] or not dev["n6705c"]:
                    continue
                channels = self._get_selected_batch_channels(label)
                if label not in self.batch_current_inputs:
                    continue
                currents = [float(inp.text()) for inp in self.batch_current_inputs[label]]
                for ch in channels:
                    try:
                        dev["n6705c"].set_mode(ch, "VMETer")
                        v = float(dev["n6705c"].measure_voltage(ch))
                        new_v = v + offset
                        dev["n6705c"].set_mode(ch, "PS2Q")
                        dev["n6705c"].set_voltage(ch, new_v)
                        dev["n6705c"].set_current_limit(ch, 0.02)
                        dev["n6705c"].channel_on(ch)
                        dev["n6705c"].set_current_limit(ch, currents[ch - 1])
                    except Exception as e:
                        logger.error("[%s] CH%d Auto failed: %s", label, ch, e)
        self._start_channel_sync()

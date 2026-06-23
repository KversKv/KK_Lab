#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consumption Test 结果卡片视图构建（Mixin）。

从 consumption_test.py 平移而来，行为零变更：
  - _refresh_result_cards : 按 channel_configs 重建结果卡片
  - _create_result_card   : 单个结果卡片构建

依赖宿主类（ConsumptionTestUI）提供以下属性/方法：
  - self.result_cards_layout
  - self.channel_cards
  - self._vbat_remain_card
  - self._channel_configs
  - self.CHANNEL_COLORS_LIST
"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
)
from PySide6.QtCore import Qt
from ui.theme import FONT_MONO


class ConsumptionTestViewResultsMixin:

    def _refresh_result_cards(self):
        while self.result_cards_layout.count():
            item = self.result_cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.deleteLater()
        self.channel_cards = {}
        self._vbat_remain_card = None

        vbat_idx = None
        has_sub_channel = False
        for i, cfg in enumerate(self._channel_configs):
            if not cfg["enabled"]:
                continue
            if cfg["name"].lower().startswith("vbat"):
                vbat_idx = i
            else:
                has_sub_channel = True
            colors = self.CHANNEL_COLORS_LIST[i % len(self.CHANNEL_COLORS_LIST)]
            card = self._create_result_card(i, cfg["name"], cfg["channel"], colors)
            self.result_cards_layout.addWidget(card, 1)

        if has_sub_channel and vbat_idx is not None:
            remain_colors = {"accent": "#a0a0a0", "bg": "#121218", "border": "#2a2a36"}
            remain_card = self._create_result_card(-1, "Vbat_remain", "", remain_colors)
            self.result_cards_layout.addWidget(remain_card, 1)
            self._vbat_remain_card = self.channel_cards.pop(-1)

    def _create_result_card(self, idx, name, channel_key, colors):
        card = QFrame()
        card_id = f"resultCard{idx}"
        card.setObjectName(card_id)
        card.setStyleSheet(f"""
            QFrame#{card_id} {{
                background-color: {colors['bg']};
                border: 1px solid {colors['border']};
                border-radius: 10px;
            }}
        """)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        title_label = QLabel(f"{name}")
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['accent']};
                font-size: 13px;
                font-weight: 700;
                background: transparent;
            }}
        """)
        top_row.addWidget(title_label)
        top_row.addStretch()

        ch_tag = QLabel(channel_key)
        ch_tag.setStyleSheet(f"""
            QLabel {{
                color: #7e96bf;
                font-size: 10px;
                background: transparent;
            }}
        """)
        top_row.addWidget(ch_tag)
        layout.addLayout(top_row)

        layout.addStretch()

        avg_label = QLabel("AVG CURRENT")
        avg_label.setAlignment(Qt.AlignCenter)
        avg_label.setStyleSheet("color: #7e96bf; font-size: 11px; font-weight: 600;")
        layout.addWidget(avg_label)

        value_label = QLabel("- - -")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['accent']};
                font-family: {FONT_MONO};
                font-size: 18px;
                font-weight: 700;
                letter-spacing: 4px;
            }}
        """)
        layout.addWidget(value_label)

        layout.addStretch()

        self.channel_cards[idx] = {
            "card": card,
            "value_label": value_label,
            "name": name,
            "channel_key": channel_key,
        }

        return card

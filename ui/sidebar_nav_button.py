from PySide6.QtWidgets import QPushButton, QLabel, QHBoxLayout, QVBoxLayout, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor


class SidebarNavButton(QPushButton):
    def __init__(self, title, subtitle="", icon_text="◈", parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(72)

        # 整体布局
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 10, 16, 10)
        main_layout.setSpacing(12)

        # 左侧图标
        self.icon_label = QLabel(icon_text)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedWidth(22)
        self.icon_label.setStyleSheet("""
            QLabel {
                color: #93a4c3;
                font-size: 18px;
                background: transparent;
                border: none;
            }
        """)
        main_layout.addWidget(self.icon_label)

        # 中间文字区域
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #d7e3ff;
                font-size: 15px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)
        text_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet("""
            QLabel {
                color: #8ea0bf;
                font-size: 12px;
                background: transparent;
                border: none;
            }
        """)
        self.subtitle_label.setVisible(bool(subtitle))
        text_layout.addWidget(self.subtitle_label)

        main_layout.addWidget(text_widget, 1)

        # 右侧箭头
        self.arrow_label = QLabel("›")
        self.arrow_label.setAlignment(Qt.AlignCenter)
        self.arrow_label.setFixedWidth(16)
        self.arrow_label.setStyleSheet("""
            QLabel {
                color: #7f8fb0;
                font-size: 18px;
                background: transparent;
                border: none;
            }
        """)
        main_layout.addWidget(self.arrow_label)

        # 默认样式
        self._update_style(False)

        # 监听选中状态变化
        self.toggled.connect(self._update_style)

    def _update_style(self, checked):
        if checked:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #5b3df5;
                    border: none;
                    border-radius: 16px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #6548ff;
                }
            """)
            self.icon_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 18px;
                    background: transparent;
                    border: none;
                }
            """)
            self.title_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 15px;
                    font-weight: 700;
                    background: transparent;
                    border: none;
                }
            """)
            self.subtitle_label.setStyleSheet("""
                QLabel {
                    color: #e4dcff;
                    font-size: 12px;
                    background: transparent;
                    border: none;
                }
            """)
            self.arrow_label.setStyleSheet("""
                QLabel {
                    color: #d9d0ff;
                    font-size: 18px;
                    background: transparent;
                    border: none;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 16px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #171c2b;
                }
            """)
            self.icon_label.setStyleSheet("""
                QLabel {
                    color: #93a4c3;
                    font-size: 18px;
                    background: transparent;
                    border: none;
                }
            """)
            self.title_label.setStyleSheet("""
                QLabel {
                    color: #c7d3ee;
                    font-size: 15px;
                    font-weight: 500;
                    background: transparent;
                    border: none;
                }
            """)
            self.subtitle_label.setStyleSheet("""
                QLabel {
                    color: #7f8da9;
                    font-size: 12px;
                    background: transparent;
                    border: none;
                }
            """)
            self.arrow_label.setStyleSheet("""
                QLabel {
                    color: #6f7d98;
                    font-size: 18px;
                    background: transparent;
                    border: none;
                }
            """)
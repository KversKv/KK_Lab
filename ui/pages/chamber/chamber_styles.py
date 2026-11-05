"""通用温箱控制页样式。"""


def build_chamber_stylesheet() -> str:
    return """
        QWidget#rootWidget {
            background-color: #030b23;
            color: #eaf1ff;
            font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            font-size: 14px;
        }

        QScrollArea#pageScrollArea {
            background: transparent;
            border: none;
        }

        QScrollArea#pageScrollArea > QWidget > QWidget {
            background: transparent;
        }

        QScrollBar:vertical {
            background: transparent;
            width: 10px;
            margin: 0px;
        }

        QScrollBar::handle:vertical {
            background: #1a315d;
            min-height: 30px;
            border-radius: 5px;
        }

        QScrollBar::handle:vertical:hover {
            background: #27457d;
        }

        QScrollBar:horizontal {
            background: transparent;
            height: 10px;
            margin: 0px;
        }

        QScrollBar::handle:horizontal {
            background: #1a315d;
            min-width: 30px;
            border-radius: 5px;
        }

        QScrollBar::handle:horizontal:hover {
            background: #27457d;
        }

        QScrollBar::add-line, QScrollBar::sub-line {
            width: 0px;
            height: 0px;
        }

        QScrollBar::add-page, QScrollBar::sub-page {
            background: transparent;
        }

        QLabel {
            background: transparent;
        }

        #titleLabel {
            font-size: 20px;
            font-weight: 800;
            color: #f4f7ff;
        }

        #subtitleLabel {
            font-size: 13px;
            color: #7f95bf;
        }

        QGroupBox#cardGroup {
            background-color: #0a1738;
            border: 1px solid rgba(94, 126, 190, 0.18);
            border-radius: 16px;
            margin-top: 0px;
            padding-top: 14px;
            font-size: 16px;
            font-weight: 700;
            color: #f4f7ff;
        }

        QGroupBox#cardGroup::title {
            subcontrol-origin: margin;
            left: 18px;
            top: 14px;
            padding: 0 4px 0 4px;
            color: #f4f7ff;
            font-size: 16px;
            font-weight: 700;
        }

        QFrame#connectionCard {
            background-color: #0a1738;
            border: 1px solid rgba(94, 126, 190, 0.22);
            border-radius: 14px;
        }

        QFrame#connectionPanel {
            background-color: #07132e;
            border: 1px solid #17305f;
            border-radius: 10px;
        }

        #connectionTitle {
            font-size: 15px;
            font-weight: 800;
            color: #f4f7ff;
        }

        #connectionSubtitle {
            font-size: 12px;
            color: #8ca5d3;
        }

        #fieldLabel {
            font-size: 12px;
            font-weight: 650;
            color: #8ca5d3;
        }

        #comboBox {
            background-color: #04102b;
            border: 1px solid #1a315d;
            border-radius: 8px;
            padding: 0 12px;
            min-height: 36px;
            color: #eef4ff;
        }

        #comboBox:hover {
            border-color: #27457d;
        }

        #comboBox::drop-down {
            border: none;
            width: 24px;
        }

        #comboBox QAbstractItemView {
            background-color: #04102b;
            color: #eef4ff;
            border: 1px solid #1a315d;
            selection-background-color: #1a3260;
            outline: 0px;
        }

        #comboBox QAbstractItemView::item {
            background-color: #04102b;
            color: #eef4ff;
            padding: 4px 8px;
        }

        #comboBox QAbstractItemView::item:hover {
            background-color: #1a3260;
        }

        QComboBox QFrame {
            background-color: #04102b;
            border: 1px solid #1a315d;
        }

        #iconButton {
            background-color: #13254b;
            border: 1px solid #22365d;
            border-radius: 8px;
            color: #b7c7e6;
            font-size: 16px;
            font-weight: 700;
        }

        #iconButton:hover {
            background-color: #213258;
        }

        #iconButton:pressed {
            background-color: #182847;
        }

        #statusWrap {
            background-color: #07132e;
            border: 1px solid #17305f;
            border-radius: 10px;
        }

        #statusDot {
            color: #5d78a7;
            font-size: 18px;
        }

        #statusTitle {
            font-size: 14px;
            font-weight: 700;
            color: #dfe8fb;
        }

        #statusDesc {
            font-size: 12px;
            color: #7e95bf;
        }

        QPushButton#connectButton {
            min-height: 38px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 800;
            padding: 0 14px;
        }

        #miniInfoBox {
            background-color: #040d28;
            border: 1px solid #17305f;
            border-radius: 12px;
        }

        #miniInfoLabel {
            color: #8ca5d3;
            font-size: 13px;
        }

        #miniInfoValue {
            color: #6f7dff;
            font-size: 18px;
            font-weight: 800;
        }

        #innerPanel {
            background-color: #040d28;
            border: 1px solid #17305f;
            border-radius: 12px;
        }

        #compactHeader {
            background-color: #061436;
            border: 1px solid #17305f;
            border-radius: 12px;
        }

        #summaryBox {
            background-color: #040d28;
            border: 1px solid #17305f;
            border-radius: 12px;
        }

        #summaryCaption {
            color: #7e95bf;
            font-size: 12px;
            font-weight: 600;
            border: none;
        }

        #summaryValue {
            color: #eaf1ff;
            font-size: 16px;
            font-weight: 800;
            border: none;
        }

        #mainTabs::pane {
            background-color: #040d28;
            border: 1px solid #17305f;
            border-radius: 12px;
            top: -1px;
        }

        #mainTabs QTabBar::tab {
            background-color: #0a1c40;
            color: #7e95bf;
            border: 1px solid #17305f;
            border-bottom: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            padding: 8px 16px;
            margin-right: 2px;
            font-size: 13px;
            font-weight: 700;
        }

        #mainTabs QTabBar::tab:selected {
            background-color: #173a7a;
            color: #eaf1ff;
        }

        #mainTabs QTabBar::tab:hover:!selected {
            background-color: #102a59;
        }

        #powerButton {
            background-color: #223150;
            border: 1px solid #34486f;
            border-radius: 8px;
            color: #5f7397;
            font-size: 15px;
            font-weight: 800;
            padding: 10px 16px;
        }

        #powerButton:hover:!disabled {
            background-color: #2a3a5e;
        }

        #powerButton:pressed:!disabled {
            background-color: #243350;
        }

        #powerButton:disabled {
            background-color: #1a2642;
            color: #4f6287;
            border: 1px solid #2a3b63;
        }

        #tempInput {
            background-color: #06122f;
            border: 1px solid #183261;
            border-radius: 8px;
            color: #eaf1ff;
            padding: 0 14px;
            font-size: 16px;
            font-weight: 600;
        }

        #tempInput:focus {
            border: 1px solid #4a68ff;
        }

        #setButton {
            background-color: #3d2bc6;
            border: none;
            border-radius: 8px;
            color: #cfd5f3;
            font-weight: 800;
            padding: 0 22px;
        }

        #setButton:hover:!disabled {
            background-color: #4b38df;
            color: white;
        }

        #setButton:pressed:!disabled {
            background-color: #3726b7;
        }

        #setButton:disabled {
            background-color: #20294a;
            color: #5a6d96;
        }

        #presetButton {
            background-color: #182545;
            border: 1px solid #1d2d53;
            border-radius: 8px;
            color: #7f93bd;
            padding: 6px 10px;
            font-size: 12px;
            font-weight: 600;
        }

        #presetButton:hover:!disabled {
            background-color: #22345d;
            color: #dfe8fb;
        }

        #presetButton:pressed:!disabled {
            background-color: #1b2b4d;
        }

        #presetButton:disabled {
            background-color: #121d38;
            color: #51658f;
            border: 1px solid #1b2948;
        }

        #fieldLabelSmall {
            font-size: 11px;
            font-weight: 600;
            color: #7e95bf;
        }

        #loopInput {
            background-color: #06122f;
            border: 1px solid #183261;
            border-radius: 8px;
            color: #eaf1ff;
            padding: 0 12px;
            font-size: 14px;
            font-weight: 600;
        }

        #loopInput:focus {
            border: 1px solid #4a68ff;
        }

        #loopInput:disabled {
            background-color: #0a1430;
            color: #51658f;
            border: 1px solid #16264a;
        }

        QCheckBox#loopCheck {
            color: #8ca5d3;
            font-size: 12px;
            font-weight: 600;
            spacing: 6px;
        }

        QCheckBox#loopCheck::indicator {
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1px solid #2a3b63;
            background-color: #06122f;
        }

        QCheckBox#loopCheck::indicator:checked {
            background-color: #3d2bc6;
            border: 1px solid #4b38df;
        }

        QCheckBox#loopCheck:disabled {
            color: #51658f;
        }

        #loopStartButton {
            background-color: #0f8f63;
            border: 1px solid #15e6a3;
            border-radius: 8px;
            color: white;
            font-size: 13px;
            font-weight: 800;
        }

        #loopStartButton:hover:!disabled {
            background-color: #11a36f;
            border-color: #42f0bd;
        }

        #loopStartButton:pressed:!disabled {
            background-color: #0d7f58;
        }

        #loopStartButton:disabled {
            background-color: #1a2642;
            color: #4f6287;
            border: 1px solid #2a3b63;
        }

        #loopStopButton {
            background-color: #a9153e;
            border: 1px solid #ff4f7b;
            border-radius: 8px;
            color: white;
            font-size: 13px;
            font-weight: 800;
        }

        #loopStopButton:hover:!disabled {
            background-color: #c31d4c;
            border-color: #ff6b91;
        }

        #loopStopButton:pressed:!disabled {
            background-color: #8d1134;
        }

        #loopStopButton:disabled {
            background-color: #1a2642;
            color: #4f6287;
            border: 1px solid #2a3b63;
        }

        #loopStatusLabel {
            font-size: 12px;
            font-weight: 600;
            color: #8ca5d3;
        }
        """

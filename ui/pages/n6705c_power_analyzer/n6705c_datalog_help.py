#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""N6705C Datalog 页帮助系统：帮助手册对话框 + 一键引导（Guided Tour）覆盖层。

- load_datalog_help_html(): 读取 helps/datalog.html（打包/开发环境均可），失败返回兜底文本。
- DatalogHelpDialog: 手册浏览对话框，底部提供「一键引导」入口（done(GUIDE_REQUESTED) 退出码）。
- GuideTourOverlay: 通用逐步引导层——半透明遮罩镂空高亮目标控件 + 气泡步骤卡片，
  步骤由调用方定义（target/title/text/on_enter），Esc 退出，左右方向键翻页。
"""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QDialog, QTextBrowser, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, Signal, QRect, QPoint, QEvent
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QFont

from ui.resource_path import get_resource_base
from log_config import get_logger

logger = get_logger(__name__)


def load_datalog_help_html():
    """读取 helps/datalog.html 帮助手册内容，读取失败返回兜底提示。"""
    path = os.path.join(get_resource_base(), "helps", "datalog.html")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        logger.warning("帮助文档读取失败: %s", path, exc_info=True)
        return "<h2>N6705C Datalog 帮助</h2><p>未找到帮助文档 helps/datalog.html。</p>"


class DatalogHelpDialog(QDialog):
    """Datalog 帮助手册对话框：手册内容 + 「一键引导」/「关闭」按钮。

    exec() 返回 GUIDE_REQUESTED 表示用户点击了「一键引导」，调用方应启动 GuideTourOverlay。
    """

    GUIDE_REQUESTED = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Datalog Help")
        self.resize(760, 640)
        # 首帧防闪白：样式表 polish 前用调色板锁定深色背景
        self.setAttribute(Qt.WA_StyledBackground, True)
        pal = self.palette()
        pal.setColor(self.backgroundRole(), QColor("#0b1424"))
        self.setPalette(pal)
        self.setStyleSheet("""
            QDialog {
                background-color: #0b1424;
            }
            QTextBrowser {
                background-color: #0b1424;
                color: #d5def2;
                border: 1px solid #16294a;
                border-radius: 6px;
                font-size: 13px;
                padding: 12px;
            }
            QPushButton#helpCloseBtn {
                min-height: 32px;
                max-height: 32px;
                min-width: 88px;
                padding: 0px 18px;
                border-radius: 4px;
                border: 1px solid #2a4268;
                background-color: #16284f;
                color: #dfe8ff;
                font-weight: 600;
            }
            QPushButton#helpCloseBtn:hover {
                background-color: #1e3466;
            }
            QPushButton#guideStartBtn {
                min-height: 32px;
                max-height: 32px;
                min-width: 108px;
                padding: 0px 18px;
                border-radius: 4px;
                border: 1px solid #645bff;
                background-color: #5b5cf6;
                color: #ffffff;
                font-weight: 700;
            }
            QPushButton#guideStartBtn:hover {
                background-color: #6b6cff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(load_datalog_help_html())
        layout.addWidget(browser, 1)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)

        guide_btn = QPushButton("一键引导")
        guide_btn.setObjectName("guideStartBtn")
        guide_btn.setToolTip("跟随高亮提示，逐步完成 连接仪器 → 配置 → 采集 → 分析 → 导出")
        guide_btn.setAutoDefault(False)
        guide_btn.setDefault(False)
        guide_btn.clicked.connect(lambda: self.done(self.GUIDE_REQUESTED))
        btn_row.addWidget(guide_btn)

        btn_row.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setObjectName("helpCloseBtn")
        close_btn.setAutoDefault(False)
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)


class GuideTourOverlay(QWidget):
    """覆盖在宿主窗口上的逐步引导层。

    steps: list[dict]，每项：
        target   QWidget | None — 高亮目标控件（None 时气泡居中、无镂空）
        title    str            — 步骤标题
        text     str            — 步骤说明（纯文本，\\n 换行）
        on_enter callable|None  — 进入该步时调用（如展开对应面板）
    finished: 完成 / 跳过 / Esc 均发出（overlay 销毁前）。
    """

    finished = Signal()

    _BUBBLE_WIDTH = 380
    _GAP = 14          # 气泡与高亮区间距
    _MARGIN = 12       # 气泡距窗口边缘最小间距
    _HOLE_PAD = 6      # 高亮镂空外扩

    def __init__(self, host, steps, parent=None):
        super().__init__(host)
        self._host = host
        self._steps = steps
        self._index = -1

        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(False)
        self.setGeometry(host.rect())
        self.show()
        self.raise_()

        host.installEventFilter(self)

        self._bubble = QFrame(self)
        self._bubble.setObjectName("tourBubble")
        self._bubble.setAttribute(Qt.WA_StyledBackground, True)
        self._bubble.setFixedWidth(self._BUBBLE_WIDTH)
        self._bubble.setStyleSheet("""
            QFrame#tourBubble {
                background-color: #101d38;
                border: 1px solid #2a4a7a;
                border-radius: 10px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
            QLabel#tourStepTag {
                color: #4cc9f0;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#tourTitle {
                color: #eaf1ff;
                font-size: 14px;
                font-weight: 800;
            }
            QLabel#tourBody {
                color: #b9c8e6;
                font-size: 12px;
            }
            QPushButton#tourNavBtn {
                min-height: 26px;
                max-height: 26px;
                min-width: 64px;
                padding: 0px 12px;
                border-radius: 4px;
                border: 1px solid #2a4268;
                background-color: #16284f;
                color: #dfe8ff;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton#tourNavBtn:hover {
                background-color: #1e3466;
            }
            QPushButton#tourNavBtn:disabled {
                background-color: #0d1734;
                border: 1px solid #18264a;
                color: #4a5a7a;
            }
            QPushButton#tourPrimaryBtn {
                min-height: 26px;
                max-height: 26px;
                min-width: 64px;
                padding: 0px 12px;
                border-radius: 4px;
                border: 1px solid #645bff;
                background-color: #5b5cf6;
                color: #ffffff;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#tourPrimaryBtn:hover {
                background-color: #6b6cff;
            }
        """)

        bubble_layout = QVBoxLayout(self._bubble)
        bubble_layout.setContentsMargins(16, 14, 16, 14)
        bubble_layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        self._step_tag = QLabel()
        self._step_tag.setObjectName("tourStepTag")
        top_row.addWidget(self._step_tag)
        top_row.addStretch()
        self._skip_btn = QPushButton("跳过引导")
        self._skip_btn.setObjectName("tourNavBtn")
        self._skip_btn.setAutoDefault(False)
        self._skip_btn.setDefault(False)
        self._skip_btn.clicked.connect(self.finish)
        top_row.addWidget(self._skip_btn)
        bubble_layout.addLayout(top_row)

        self._title_label = QLabel()
        self._title_label.setObjectName("tourTitle")
        bubble_layout.addWidget(self._title_label)

        self._body_label = QLabel()
        self._body_label.setObjectName("tourBody")
        self._body_label.setWordWrap(True)
        self._body_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        bubble_layout.addWidget(self._body_label)

        nav_row = QHBoxLayout()
        nav_row.setContentsMargins(0, 4, 0, 0)
        nav_row.addStretch()
        self._back_btn = QPushButton("上一步")
        self._back_btn.setObjectName("tourNavBtn")
        self._back_btn.setAutoDefault(False)
        self._back_btn.setDefault(False)
        self._back_btn.clicked.connect(self.prev_step)
        nav_row.addWidget(self._back_btn)
        self._next_btn = QPushButton("下一步")
        self._next_btn.setObjectName("tourPrimaryBtn")
        self._next_btn.setAutoDefault(False)
        self._next_btn.setDefault(False)
        self._next_btn.clicked.connect(self.next_step)
        nav_row.addWidget(self._next_btn)
        bubble_layout.addLayout(nav_row)

        self._bubble.show()
        self.setFocus()
        self.next_step()

    # ------------------------------------------------------------------ 步骤流转

    def next_step(self):
        if self._index + 1 >= len(self._steps):
            self.finish()
            return
        self._show_step(self._index + 1)

    def prev_step(self):
        if self._index > 0:
            self._show_step(self._index - 1)

    def _show_step(self, index):
        self._index = index
        step = self._steps[index]
        on_enter = step.get("on_enter")
        if callable(on_enter):
            try:
                on_enter()
            except Exception:
                logger.warning("引导步骤 on_enter 执行失败", exc_info=True)
        self._step_tag.setText(f"STEP {index + 1} / {len(self._steps)}")
        self._title_label.setText(step.get("title", ""))
        self._body_label.setText(step.get("text", ""))
        self._back_btn.setEnabled(index > 0)
        self._next_btn.setText("完成" if index == len(self._steps) - 1 else "下一步")
        # 面板展开/收起后布局几何需经事件循环生效，延迟重定位
        QTimer.singleShot(60, self._reposition)

    def finish(self):
        if self._host is not None:
            self._host.removeEventFilter(self)
            self._host = None
        self.finished.emit()
        self.hide()
        self.deleteLater()

    # ------------------------------------------------------------------ 定位与绘制

    def _target_rect(self):
        """当前步骤目标在 overlay 坐标系中的矩形；无目标或目标隐藏返回 None。"""
        if self._index < 0 or self._index >= len(self._steps):
            return None
        target = self._steps[self._index].get("target")
        if target is None or target.isHidden():
            return None
        top_left = self.mapFromGlobal(target.mapToGlobal(QPoint(0, 0)))
        rect = QRect(top_left, target.size())
        if not rect.isValid() or not self.rect().intersects(rect):
            return None
        return rect

    def _reposition(self):
        if self._host is None:
            return
        self.setGeometry(self._host.rect())
        # 高度按文本换行显式量出：wordWrap QLabel 的 sizeHint 依赖布局已分配宽度，
        # adjustSize() 在文本刚更新时会按旧宽度把高度算小，导致内容截断
        text_w = self._BUBBLE_WIDTH - 32  # 气泡布局左右 margin 各 16
        body_h = self._body_label.fontMetrics().boundingRect(
            QRect(0, 0, text_w, 100000), Qt.TextWordWrap, self._body_label.text()
        ).height()
        # 上下 margin 各14 + top_row 26 + title + body + nav_row 26 + 3×spacing 8 + nav 上间距 4
        bh = 14 + 14 + 26 + self._title_label.fontMetrics().height() + body_h + 26 + 8 * 3 + 4
        bh = min(bh, self.height() - 2 * self._MARGIN)
        self._bubble.setFixedHeight(bh)
        bw = self._BUBBLE_WIDTH
        rect = self._target_rect()
        if rect is None:
            x = (self.width() - bw) // 2
            y = (self.height() - bh) // 2
        else:
            hole = rect.adjusted(-self._HOLE_PAD, -self._HOLE_PAD, self._HOLE_PAD, self._HOLE_PAD)
            # 优先下方，其次上方，再退化为目标区内居中（目标过大时）
            if hole.bottom() + self._GAP + bh <= self.height() - self._MARGIN:
                y = hole.bottom() + self._GAP
            elif hole.top() - self._GAP - bh >= self._MARGIN:
                y = hole.top() - self._GAP - bh
            else:
                y = max(self._MARGIN, hole.center().y() - bh // 2)
            x = hole.center().x() - bw // 2
            x = max(self._MARGIN, min(x, self.width() - bw - self._MARGIN))
        self._bubble.move(x, y)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        mask = QPainterPath()
        mask.addRect(self.rect())
        rect = self._target_rect()
        if rect is not None:
            hole_rect = rect.adjusted(-self._HOLE_PAD, -self._HOLE_PAD, self._HOLE_PAD, self._HOLE_PAD)
            hole = QPainterPath()
            hole.addRoundedRect(hole_rect, 8, 8)
            p.fillPath(mask.subtracted(hole), QColor(2, 6, 18, 190))
            p.setPen(QPen(QColor("#4cc9f0"), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(hole_rect, 8, 8)
        else:
            p.fillPath(mask, QColor(2, 6, 18, 190))
        p.end()

    # ------------------------------------------------------------------ 事件

    def eventFilter(self, watched, event):
        if watched is self._host and event.type() in (QEvent.Resize, QEvent.Move):
            self._reposition()
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self.finish()
        elif key in (Qt.Key_Right, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.next_step()
        elif key == Qt.Key_Left:
            self.prev_step()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        # 吞掉遮罩上的点击，防止误触底层控件；气泡内部点击由子控件正常处理
        event.accept()

"""ElementPicker：类浏览器 F12 的页面元素拾取器（Ctrl+Shift+C）。

职责：
  - 注册全局快捷键进入拾取模式；
  - 用置顶半透明遮罩跟随鼠标高亮命中控件（等价 F12 蓝框）；
  - 单击选定后按控件类型抽取结构化内容（文本 / 表格 / pyqtgraph 曲线 / 兜底），
    经回调注入 AIAssistPanel 作为下一条消息的附带上下文；
  - ESC / 右键取消。

约束：纯 UI 层，不触碰 instruments / core 仪器逻辑，不做阻塞 IO；
拾取内容体量交由面板侧的 extra_context 与 core 的 context_budget 裁剪。
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, QPoint, QRect, Qt
from PySide6.QtGui import (
    QColor,
    QKeySequence,
    QPainter,
    QPen,
    QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QTextEdit,
    QWidget,
)

from log_config import get_logger

logger = get_logger(__name__)

_MAX_TABLE_ROWS = 200
_MAX_TABLE_COLS = 40
_MAX_CURVE_POINTS = 400
_MAX_TEXT_CHARS = 4000


class _PickOverlay(QWidget):
    """主窗口内置顶遮罩：跟随鼠标高亮命中控件，单击选定，ESC/右键取消。

    作为主窗口的子级覆盖层（非独立顶层窗口），仅覆盖主窗口客户区，
    不影响系统其它区域；命中检测限定在主窗口控件树内，无需 hide/show
    顶层窗口，避免桌面/其它窗口反复重绘导致的屏幕闪烁。
    """

    def __init__(self, picker: "ElementPicker", host: QWidget):
        super().__init__(host)
        self._picker = picker
        self._host = host
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setGeometry(host.rect())
        self._hover_rect = QRect()
        self._hover_label = ""

    def _update_hover(self, global_pos: QPoint) -> None:
        widget = self._picker.widget_at(global_pos)
        if widget is None:
            self._hover_rect = QRect()
            self._hover_label = ""
        else:
            top_left = widget.mapToGlobal(QPoint(0, 0))
            self._hover_rect = QRect(
                self.mapFromGlobal(top_left), widget.size()
            )
            self._hover_label = self._picker.describe_widget(widget)
        self.update()

    def mouseMoveEvent(self, event) -> None:
        self._update_hover(event.globalPosition().toPoint())

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.RightButton:
            self._picker.cancel()
            return
        if event.button() == Qt.LeftButton:
            self._picker.pick_at(event.globalPosition().toPoint())

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self._picker.cancel()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(2, 6, 23, 60))
        if not self._hover_rect.isNull():
            painter.fillRect(self._hover_rect, QColor(59, 130, 246, 60))
            pen = QPen(QColor(59, 130, 246), 2)
            painter.setPen(pen)
            painter.drawRect(self._hover_rect.adjusted(0, 0, -1, -1))
            if self._hover_label:
                self._draw_badge(painter, self._hover_rect, self._hover_label)
        painter.end()

    def _draw_badge(self, painter: QPainter, rect: QRect, text: str) -> None:
        metrics = painter.fontMetrics()
        text = metrics.elidedText(text, Qt.ElideRight, 320)
        pad_x, pad_y = 8, 4
        tw = metrics.horizontalAdvance(text) + pad_x * 2
        th = metrics.height() + pad_y * 2
        bx = rect.left()
        by = rect.top() - th - 2
        if by < 0:
            by = rect.top() + 2
        badge = QRect(bx, by, tw, th)
        painter.fillRect(badge, QColor(37, 99, 235))
        painter.setPen(QColor(248, 250, 252))
        painter.drawText(badge.adjusted(pad_x, pad_y, 0, 0), Qt.AlignLeft, text)


class ElementPicker(QObject):
    """页面元素拾取协调器，挂在 MainWindow 上。

    on_pick(label, content) 由外部注入，用于把拾取结果交给 AIAssistPanel。
    """

    def __init__(
        self,
        main_window: QWidget,
        on_pick: Callable[[str, str], None],
        shortcut: str = "Ctrl+Shift+C",
        parent: QObject | None = None,
    ):
        super().__init__(parent or main_window)
        self._main_window = main_window
        self._on_pick = on_pick
        self._overlay: _PickOverlay | None = None
        self._shortcut = QShortcut(QKeySequence(shortcut), main_window)
        self._shortcut.setContext(Qt.ApplicationShortcut)
        self._shortcut.activated.connect(self.toggle)

    def toggle(self) -> None:
        if self._overlay is not None:
            self.cancel()
        else:
            self.start()

    def start(self) -> None:
        if self._overlay is not None:
            return
        host = self._main_window
        self._overlay = _PickOverlay(self, host)
        self._overlay.setGeometry(host.rect())
        self._overlay.show()
        self._overlay.raise_()
        self._overlay.setFocus()
        logger.info("元素拾取模式已开启")

    def cancel(self) -> None:
        overlay = self._overlay
        self._overlay = None
        if overlay is not None:
            try:
                overlay.close()
            except RuntimeError:
                pass
        logger.debug("元素拾取模式已取消/关闭")

    def widget_at(self, global_pos: QPoint) -> QWidget | None:
        """返回鼠标下控件（限主窗口控件树内），排除遮罩自身。

        用主窗口本地坐标递归 childAt 命中，不 hide/show 顶层窗口，
        因此不会触发桌面/其它窗口重绘，无屏幕闪烁。
        """
        host = self._main_window
        local = host.mapFromGlobal(global_pos)
        if not host.rect().contains(local):
            return None
        overlay = self._overlay
        if overlay is not None:
            overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            widget = QApplication.widgetAt(global_pos)
            overlay.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        else:
            widget = QApplication.widgetAt(global_pos)
        if widget is None:
            return None
        if widget.window() is not host.window():
            return None
        if overlay is not None and (widget is overlay or overlay.isAncestorOf(widget)):
            return None
        return widget

    def pick_at(self, global_pos: QPoint) -> None:
        widget = self.widget_at(global_pos)
        self.cancel()
        if widget is None:
            return
        try:
            label, content = self._extract(widget)
        except Exception:
            logger.error("拾取控件内容失败", exc_info=True)
            return
        if not content.strip():
            content = "（该元素无可读取的文本内容，已附其类型与名称）"
        try:
            self._on_pick(label, content)
        except Exception:
            logger.error("回传拾取内容失败", exc_info=True)

    @staticmethod
    def describe_widget(widget: QWidget) -> str:
        name = widget.objectName()
        cls = widget.metaObject().className()
        return f"{cls}#{name}" if name else cls

    def _extract(self, widget: QWidget) -> tuple[str, str]:
        label = self.describe_widget(widget)
        curve_text = self._extract_pyqtgraph(widget)
        if curve_text is not None:
            return label, curve_text
        table_text = self._extract_table(widget)
        if table_text is not None:
            return label, table_text
        text = self._extract_text(widget)
        if text:
            return label, text
        return label, ""

    @staticmethod
    def _clip(text: str) -> str:
        if len(text) > _MAX_TEXT_CHARS:
            return text[:_MAX_TEXT_CHARS] + "\n…（已截断）"
        return text

    def _extract_text(self, widget: QWidget) -> str:
        if isinstance(widget, QLabel):
            return self._clip(widget.text())
        if isinstance(widget, (QPlainTextEdit,)):
            return self._clip(widget.toPlainText())
        if isinstance(widget, (QTextEdit,)):
            return self._clip(widget.toPlainText())
        if isinstance(widget, QLineEdit):
            return self._clip(widget.text())
        if isinstance(widget, QComboBox):
            return self._clip(widget.currentText())
        getter = getattr(widget, "text", None)
        if callable(getter):
            try:
                value = getter()
            except (RuntimeError, TypeError):
                return ""
            if isinstance(value, str):
                return self._clip(value)
        return ""

    def _extract_table(self, widget: QWidget) -> str | None:
        view = widget
        if not isinstance(widget, QAbstractItemView):
            parent = widget.parentWidget()
            view = parent if isinstance(parent, QAbstractItemView) else None
        if view is None:
            return None
        model = view.model()
        if model is None:
            return None
        rows = min(model.rowCount(), _MAX_TABLE_ROWS)
        cols = min(model.columnCount(), _MAX_TABLE_COLS)
        if rows == 0 or cols == 0:
            return None
        lines: list[str] = []
        headers = []
        for c in range(cols):
            head = model.headerData(c, Qt.Horizontal)
            headers.append("" if head is None else str(head))
        if any(headers):
            lines.append(" | ".join(headers))
        for r in range(rows):
            cells = []
            for c in range(cols):
                idx = model.index(r, c)
                value = model.data(idx)
                cells.append("" if value is None else str(value))
            lines.append(" | ".join(cells))
        note = ""
        if model.rowCount() > rows or model.columnCount() > cols:
            note = f"\n…（表格较大，已截断为 {rows}×{cols}）"
        return "\n".join(lines) + note

    def _extract_pyqtgraph(self, widget: QWidget) -> str | None:
        plot_item = self._find_plot_item(widget)
        if plot_item is None:
            return None
        try:
            curves = plot_item.listDataItems()
        except (RuntimeError, AttributeError):
            return None
        if not curves:
            return None
        blocks: list[str] = []
        for i, item in enumerate(curves):
            getter = getattr(item, "getData", None)
            if not callable(getter):
                continue
            try:
                xs, ys = getter()
            except (RuntimeError, TypeError, ValueError):
                continue
            if xs is None or ys is None or len(xs) == 0:
                continue
            blocks.append(self._format_curve(i, xs, ys))
        if not blocks:
            return None
        title = ""
        try:
            title_obj = plot_item.titleLabel.text if plot_item.titleLabel else ""
            title = str(title_obj or "")
        except (RuntimeError, AttributeError):
            title = ""
        header = f"曲线图{('：' + title) if title else ''}，共 {len(blocks)} 条曲线。"
        return header + "\n" + "\n".join(blocks)

    @staticmethod
    def _find_plot_item(widget: QWidget):
        for attr in ("getPlotItem", "plotItem"):
            obj = getattr(widget, attr, None)
            if callable(obj):
                try:
                    return obj()
                except (RuntimeError, TypeError):
                    continue
            if obj is not None:
                return obj
        return None

    @staticmethod
    def _format_curve(index: int, xs, ys) -> str:
        n = len(xs)
        step = max(1, n // _MAX_CURVE_POINTS)
        try:
            x_first, x_last = float(xs[0]), float(xs[-1])
            y_min = min(float(v) for v in ys)
            y_max = max(float(v) for v in ys)
        except (TypeError, ValueError):
            x_first = x_last = y_min = y_max = 0.0
        sample = []
        for k in range(0, n, step):
            try:
                sample.append(f"({float(xs[k]):.4g},{float(ys[k]):.4g})")
            except (TypeError, ValueError):
                continue
        return (
            f"- 曲线{index + 1}：{n} 点，X∈[{x_first:.4g},{x_last:.4g}]，"
            f"Y∈[{y_min:.4g},{y_max:.4g}]\n  采样点：" + " ".join(sample)
        )

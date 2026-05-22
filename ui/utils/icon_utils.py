import os
from functools import lru_cache

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QColor, QIcon
from PySide6.QtSvg import QSvgRenderer


_renderer_cache: dict[str, QSvgRenderer] = {}


def _get_renderer(svg_path: str) -> QSvgRenderer | None:
    if svg_path not in _renderer_cache:
        if not os.path.isfile(svg_path):
            _renderer_cache[svg_path] = None
        else:
            _renderer_cache[svg_path] = QSvgRenderer(svg_path)
    return _renderer_cache[svg_path]


@lru_cache(maxsize=256)
def _render_cached(svg_path: str, color: str, size: int) -> QIcon:
    renderer = _get_renderer(svg_path)
    if renderer is None:
        return QIcon()

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    renderer.render(painter)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()

    return QIcon(pixmap)


def tinted_svg_icon(svg_path: str, color: str, size: int = 16) -> QIcon:
    return _render_cached(svg_path, color, size)


def tinted_svg_pixmap(svg_path: str, color: str, size: int = 16) -> QPixmap:
    renderer = _get_renderer(svg_path)
    if renderer is None:
        return QPixmap()

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    renderer.render(painter)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()

    return pixmap


def clear_icon_cache():
    _render_cached.cache_clear()
    _renderer_cache.clear()

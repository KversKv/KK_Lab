"""SVG -> Multi-size Windows ICO converter.

Renders an SVG via PySide6 QSvgRenderer at multiple resolutions and packs
them into a single Windows .ico container using Pillow.

Usage (CLI):
    python tools/svg_to_ico.py <input.svg> <output.ico> [options]

Options:
    --sizes 16,24,32,48,64,128,256   Comma-separated icon sizes (px).
    --stroke "#34d399"               Replace stroke="currentColor" with this color.
                                     Use "none" to keep original SVG stroke.
    --fill "#34d399"                 Replace fill="currentColor" with this color.
                                     Use "none" to keep original SVG fill.
    --bg "#050b1e" | "transparent"   Background color. Default: transparent.
    --padding 0.12                   Inner padding ratio (0~0.49). Default: 0.0.

Examples:
    # Generic transparent icon, no recoloring.
    python tools/svg_to_ico.py resources/pages/foo/bar.svg dist/bar.ico

    # SerialCom style (emerald stroke on dark background, 12% padding).
    python tools/svg_to_ico.py \\
        resources/pages/main_window_SVGs/terminal.svg \\
        resources/icons/serialcom_module.ico \\
        --stroke "#34d399" --bg "#050b1e" --padding 0.12

Programmatic:
    from tools.svg_to_ico import svg_to_ico
    svg_to_ico("foo.svg", "foo.ico", stroke="#34d399", bg="#050b1e", padding=0.12)
"""

from __future__ import annotations

import argparse
import os
import sys
from io import BytesIO
from typing import Iterable, Optional, Sequence

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from PySide6.QtCore import QRectF, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from PIL import Image


DEFAULT_SIZES = (16, 24, 32, 48, 64, 128, 256)


def _ensure_qapp() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


def _parse_color(value: Optional[str]) -> Optional[QColor]:
    if value is None:
        return None
    v = value.strip().lower()
    if v in ("", "none", "transparent"):
        return None
    color = QColor(value)
    if not color.isValid():
        raise ValueError(f"Invalid color: {value!r}")
    return color


def _patch_svg(svg_text: str, stroke: Optional[str], fill: Optional[str]) -> str:
    if stroke:
        svg_text = svg_text.replace('stroke="currentColor"', f'stroke="{stroke}"')
    if fill:
        svg_text = svg_text.replace('fill="currentColor"', f'fill="{fill}"')
    return svg_text


def _render_png_bytes(
    svg_text: str,
    size: int,
    bg: Optional[QColor],
    padding: float,
) -> bytes:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(bg if bg is not None else QColor(0, 0, 0, 0))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

    pad_px = int(size * max(0.0, min(padding, 0.49)))
    target = QRectF(pad_px, pad_px, size - 2 * pad_px, size - 2 * pad_px)

    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    if not renderer.isValid():
        painter.end()
        raise ValueError("Failed to parse SVG content")
    renderer.render(painter, target)
    painter.end()

    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    image.save(buf, "PNG")
    return bytes(buf.data())


def svg_to_ico(
    svg_path: str,
    ico_path: str,
    sizes: Sequence[int] = DEFAULT_SIZES,
    stroke: Optional[str] = None,
    fill: Optional[str] = None,
    bg: Optional[str] = None,
    padding: float = 0.0,
) -> str:
    """Convert an SVG file into a multi-resolution Windows ICO file.

    Args:
        svg_path: Source SVG file path.
        ico_path: Destination ICO file path.
        sizes: Iterable of pixel sizes to embed. Defaults to common Windows set.
        stroke: Replace `stroke="currentColor"` with this color (e.g. "#34d399").
        fill: Replace `fill="currentColor"` with this color.
        bg: Background color, or None / "transparent" for transparent canvas.
        padding: Inner padding as a ratio of the canvas (0~0.49).

    Returns:
        The absolute output path actually written.
    """
    if not os.path.isfile(svg_path):
        raise FileNotFoundError(svg_path)

    sizes_sorted = sorted({int(s) for s in sizes if int(s) > 0})
    if not sizes_sorted:
        raise ValueError("`sizes` must contain at least one positive integer")

    bg_color = _parse_color(bg)
    _ensure_qapp()

    with open(svg_path, "r", encoding="utf-8") as f:
        svg_text = f.read()
    svg_text = _patch_svg(svg_text, stroke, fill)

    images = [
        Image.open(BytesIO(_render_png_bytes(svg_text, s, bg_color, padding)))
        .convert("RGBA")
        for s in sizes_sorted
    ]

    base = images[-1]
    extras = images[:-1]

    out_dir = os.path.dirname(os.path.abspath(ico_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    base.save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes_sorted],
        append_images=extras,
    )
    return os.path.abspath(ico_path)


def _parse_sizes(text: str) -> list:
    return [int(x) for x in text.replace(" ", "").split(",") if x]


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert an SVG into a multi-resolution Windows ICO file.",
    )
    parser.add_argument("svg", help="Input SVG path")
    parser.add_argument("ico", help="Output ICO path")
    parser.add_argument(
        "--sizes",
        default=",".join(str(s) for s in DEFAULT_SIZES),
        help="Comma-separated icon sizes (default: %(default)s)",
    )
    parser.add_argument(
        "--stroke", default=None,
        help='Replace stroke="currentColor" with this color (e.g. "#34d399")',
    )
    parser.add_argument(
        "--fill", default=None,
        help='Replace fill="currentColor" with this color',
    )
    parser.add_argument(
        "--bg", default=None,
        help='Background color or "transparent" (default: transparent)',
    )
    parser.add_argument(
        "--padding", type=float, default=0.0,
        help="Inner padding ratio (0~0.49). Default: 0.0",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        out = svg_to_ico(
            svg_path=args.svg,
            ico_path=args.ico,
            sizes=_parse_sizes(args.sizes),
            stroke=args.stroke,
            fill=args.fill,
            bg=args.bg,
            padding=args.padding,
        )
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"[OK] Wrote {out} ({os.path.getsize(out)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

__all__ = [
    "tinted_svg_icon",
    "tinted_svg_pixmap",
]


def __getattr__(name):
    if name in __all__:
        from ui.utils import icon_utils
        return getattr(icon_utils, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

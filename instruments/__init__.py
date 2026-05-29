"""Instrument factory entry points.

Keep this package import lightweight so mock-only paths and tests do not load
real VISA drivers until a concrete factory is called.
"""

from __future__ import annotations

from typing import Any


def create_oscilloscope(*args: Any, **kwargs: Any) -> Any:
    from instruments.factory import create_oscilloscope as factory

    return factory(*args, **kwargs)


def create_power_analyzer(*args: Any, **kwargs: Any) -> Any:
    from instruments.factory import create_power_analyzer as factory

    return factory(*args, **kwargs)


def create_chamber(*args: Any, **kwargs: Any) -> Any:
    from instruments.factory import create_chamber as factory

    return factory(*args, **kwargs)


def create_mcu_io(*args: Any, **kwargs: Any) -> Any:
    from instruments.factory import create_mcu_io as factory

    return factory(*args, **kwargs)


__all__ = [
    "create_oscilloscope",
    "create_power_analyzer",
    "create_chamber",
    "create_mcu_io",
]

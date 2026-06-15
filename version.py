#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KK_Lab 版本号唯一事实源。

研发初期：版本号手动、低频维护，与 git 解耦（不打 tag、不从 git 反推）。
日常 commit 不动版本号；仅在想标记一个里程碑 / 对外发包时手动改这里。
其它任何地方禁止再写死版本号字符串，一律从本模块引用。

详见 docs/ai/10_VERSIONING.md。
"""

__all__ = ["__version__", "__build__", "APP_NAME", "version_string"]

__version__ = "0.1.0"
__build__ = "20260615"
APP_NAME = "KK_Lab"


def version_string() -> str:
    return f"{APP_NAME} v{__version__} (build {__build__})"

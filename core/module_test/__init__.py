"""Module Test（LDO / DCDC）核心编排包。

分层铁律：本包禁止依赖 Qt Widget（可依赖 QtCore 的 QThread/Signal）；
仪器一律由调用方注入（经 instruments/factory.py 创建的 N6705C / Scope / Chamber 或其 Mock）。
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时 DEBUG 启动器：带 VISA close 追踪的 Datalog 独立窗口。

用法：python tests\\_run_datalog_traced.py
然后按平常操作复现 "A+B 无法 Start"。所有 rm.close() / A 机 instr.close()
调用连同调用栈写入 tests\\_visa_trace.log。复现后把该文件发我。
"""

import os
import sys
import time
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

_TRACE_LOG = os.path.join(os.path.dirname(__file__), "_visa_trace.log")
_trace_fp = open(_TRACE_LOG, "w", encoding="utf-8")


def _tlog(msg):
    _trace_fp.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    _trace_fp.flush()


# ---- 追踪 ResourceManager.close ----
import pyvisa.highlevel as _hl  # noqa: E402
import pyvisa.resources.resource as _res  # noqa: E402

_orig_rm_close = _hl.ResourceManager.close


def _traced_rm_close(self):
    backend = getattr(getattr(self, "visalib", None), "library_path", "?")
    _tlog(f"!!! ResourceManager.close() backend={backend}")
    _tlog("".join(traceback.format_stack()))
    return _orig_rm_close(self)


_hl.ResourceManager.close = _traced_rm_close

# ---- 追踪 N6705C(98) 的 instr.close ----
_orig_res_close = _res.Resource.close


def _traced_res_close(self):
    name = str(getattr(self, "_resource_name", ""))
    if "10.31.71.98" in name:
        _tlog(f"!!! A instr.close() resource={name}")
        _tlog("".join(traceback.format_stack()))
    return _orig_res_close(self)


_res.Resource.close = _traced_res_close

# ---- 以下复刻 power_analyzer_datalog_ui.py 的 __main__ 块 ----
from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtCore import qInstallMessageHandler, QtMsgType  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402

from resource_path import get_resource_base  # noqa: E402
from ui.pages.power_analyzer.power_analyzer_datalog_ui import (  # noqa: E402
    _StandaloneDatalogWindow,
)


def _msg_handler(msg_type, context, message):
    if msg_type == QtMsgType.QtWarningMsg and "QPainter::end" in message:
        return


def main():
    _tlog("traced launcher start")
    qInstallMessageHandler(_msg_handler)
    app = QApplication(sys.argv)
    _icon_path = os.path.join(get_resource_base(), "resources", "icons", "n6705c_datalog.ico")
    if os.path.exists(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))
    app.setStyle("Fusion")

    from core.instruments import InstrumentManager
    manager = InstrumentManager()
    w = _StandaloneDatalogWindow(instrument_manager=manager)
    w.setWindowTitle("Datalog (traced)")
    if os.path.exists(_icon_path):
        w.setWindowIcon(QIcon(_icon_path))
    w.apply_window_geometry()
    if getattr(w, "_restore_maximized", False):
        w.showMaximized()
    else:
        w.show()
    ret = app.exec()
    _tlog("app exit")
    _trace_fp.close()
    return ret


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时 DEBUG 启动器：带 VISA close 追踪的 main.py 主程序。

用法：python tests\\_run_main_traced.py
然后按平常操作复现 "A+B 无法 Start"。所有 rm.close() 与两台电源的
instr.close() 调用连同调用栈写入 tests\\_visa_trace.log。
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


# ---- 在创建任何 RM 之前打补丁 ----
import pyvisa.highlevel as _hl  # noqa: E402
import pyvisa.resources.resource as _res  # noqa: E402

_orig_rm_close = _hl.ResourceManager.close


def _traced_rm_close(self):
    backend = getattr(getattr(self, "visalib", None), "library_path", "?")
    _tlog(f"!!! ResourceManager.close() backend={backend}")
    _tlog("".join(traceback.format_stack()))
    return _orig_rm_close(self)


_hl.ResourceManager.close = _traced_rm_close

_orig_res_close = _res.Resource.close
_WATCH = ("10.31.71.98", "10.31.71.168")


def _traced_res_close(self):
    name = str(getattr(self, "_resource_name", ""))
    if any(ip in name for ip in _WATCH):
        _tlog(f"!!! instr.close() resource={name}")
        _tlog("".join(traceback.format_stack()))
    return _orig_res_close(self)


_res.Resource.close = _traced_res_close

_tlog("traced main launcher start")

import main as _main  # noqa: E402

if __name__ == "__main__":
    try:
        _main.main()
    finally:
        _tlog("app exit")
        _trace_fp.close()

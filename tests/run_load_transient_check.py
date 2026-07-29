#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 user_data/module_test_configs/ldo/BES1811/LDO_01.json 真机执行 Load Transient Response。

复用应用内 LDOTestRunner 路径（DEBUG_MOCK=False），连接真实 N6705C + MSO64B，
仅运行 ldo_load_transient 单测试项，打印过程日志与结果摘要。
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtCore import QCoreApplication, QTimer

from core.module_test.ldo.ldo_runner import LDOTestRunner
from instruments.factory import create_oscilloscope, create_power_analyzer
from log_config import get_logger

logger = get_logger(__name__)

N6705C_ADDR = "TCPIP0::K-N6705C-06098.local::hislip0::INSTR"
DSOX4034A_ADDR = "TCPIP0::10.31.30.181::inst0::INSTR"
CFG_PATH = r"user_data\module_test_configs\ldo\BES1811\LDO_01.json"
TIMEOUT_MS = 180_000


def main() -> int:
    with open(CFG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)["config"]
    cfg["selected_items"] = ["ldo_load_transient"]

    app = QCoreApplication(sys.argv)

    n6705c = create_power_analyzer(N6705C_ADDR)
    logger.info("N6705C connected: %s", n6705c.instr.query("*IDN?").strip())

    scope = create_oscilloscope("dsox4034a", DSOX4034A_ADDR)
    logger.info("DSOX4034A connected: %s", scope.identify_instrument())

    runner = LDOTestRunner(config=cfg, n6705c=n6705c, scope=scope)
    runner.log.connect(lambda m: print(m, flush=True))
    runner.progress.connect(
        lambda p, s: print(f"[PROGRESS {p:3d}%] {s}", flush=True))
    runner.item_finished.connect(
        lambda k, d: print(f"[ITEM_DONE] {k}: {d}", flush=True))

    exit_code = [1]

    def on_finished(result):
        print("\n===== RESULT =====", flush=True)
        for it in result.items:
            print(f"item={it.item_key} passed={it.passed}", flush=True)
            print(f"measured={it.measured}", flush=True)
            print(f"csv={it.raw_csv_path}", flush=True)
            print(f"waveform={it.waveform_png}", flush=True)
        print(f"summary={result.summary}", flush=True)
        exit_code[0] = 0
        app.quit()

    def on_failed(msg):
        print(f"[FAILED] {msg}", flush=True)
        app.quit()

    runner.finished_result.connect(on_finished)
    runner.failed.connect(on_failed)
    QTimer.singleShot(TIMEOUT_MS, lambda: (print("[TIMEOUT] 强制退出", flush=True),
                                           runner.request_stop(), app.quit()))
    runner.start()
    app.exec()
    return exit_code[0]


if __name__ == "__main__":
    sys.exit(main())

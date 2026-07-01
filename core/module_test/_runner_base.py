"""Module Test 通用 Runner（QThread）。

LDO/DCDC 各自的 runner 继承本类，仅绑定 module_type + items 注册表，
避免重复 QThread 编排逻辑。规划 §6。

分层：本类依赖 QtCore（QThread/Signal），禁依赖 Qt Widget；
仪器由 UI 注入（N6705C/Scope/Chamber 或 Mock），耗时全在本线程。
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Callable

from PySide6.QtCore import QThread, Signal

from core.module_test._common import ItemContext
from core.module_test.report import save_html_report
from core.module_test.result_model import ItemResult, ModuleTestResult
from debug_config import DEBUG_MOCK
from log_config import get_logger

logger = get_logger(__name__)


class ModuleTestRunner(QThread):
    """按勾选项串行调度各 item worker 的编排线程。

    Signals:
        progress(int, str): 总进度百分比 + 当前项名。
        item_finished(str, dict): 单项完成（item_key, 摘要）。
        log(str): 日志行。
        finished_result(object): 全部完成，传 ModuleTestResult。
        failed(str): 致命错误。
    """

    progress = Signal(int, str)
    item_finished = Signal(str, dict)
    log = Signal(str)
    finished_result = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        *,
        module_type: str,
        items_registry: dict[str, tuple[str, Any, bool]],
        config: dict,
        n6705c: Any,
        scope: Any | None = None,
        chamber: Any | None = None,
        out_dir: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self._module_type = module_type
        self._items_registry = items_registry
        self._cfg = dict(config)
        self._n6705c = n6705c
        self._scope = scope
        self._chamber = chamber
        self._out_dir = out_dir or os.path.join("Results", "module_test", module_type,
                                                datetime.now().strftime("%Y%m%d_%H%M%S"))
        self._stop_flag = False
        self._result = ModuleTestResult(
            module_type=module_type,
            chip_name=str(self._cfg.get("chip_name", "")),
            operator=str(self._cfg.get("operator", "")),
            temperature=str(self._cfg.get("temperature", "")),
            started_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def request_stop(self):
        """协作式中断（检查标志位，禁强杀线程）。"""
        self._stop_flag = True

    def _log(self, msg: str) -> None:
        self.log.emit(msg)

    def _progress(self, percent: int, label: str) -> None:
        self.progress.emit(percent, label)

    def run(self):  # noqa: D401 - QThread 入口
        selected: list[str] = [k for k in self._cfg.get("selected_items", []) if k in self._items_registry]
        if not selected:
            self._log("[WARN] 未勾选任何测试项。")
            self.failed.emit("未勾选任何测试项")
            return

        os.makedirs(self._out_dir, exist_ok=True)
        total = len(selected)
        self._log(f"[RUN] {self._module_type.upper()} Module Test 开始，共 {total} 项，输出目录: {self._out_dir}")

        for idx, item_key in enumerate(selected):
            if self._stop_flag:
                self._log("[STOP] 收到停止请求，终止后续项。")
                break
            name, run_fn, needs_scope = self._items_registry[item_key]
            self._log(f"[{idx + 1}/{total}] 执行 {name}（{item_key}）...")
            self._progress(int(idx / total * 100), name)

            ctx = ItemContext(
                n6705c=self._n6705c,
                scope=self._scope,
                chamber=self._chamber,
                config=self._cfg,
                out_dir=self._out_dir,
                is_mock=bool(DEBUG_MOCK) or self._n6705c is None,
                stop_flag_fn=lambda: self._stop_flag,
                log_fn=self._log,
                progress_fn=self._progress,
            )
            try:
                result: ItemResult = run_fn(ctx)
            except Exception:  # noqa: BLE001 - 单项异常不阻断整体
                logger.error("item %s 执行异常", item_key, exc_info=True)
                self._log(f"[ERROR] {item_key} 执行异常，记为 FAIL。")
                result = ItemResult(item_key=item_key, name=name, passed=False,
                                    notes="执行异常，见日志")
            self._result.items.append(result)
            self.item_finished.emit(item_key, result.to_summary())
            self._progress(int((idx + 1) / total * 100), name)

        self._result.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._result.build_summary()

        try:
            report_path = save_html_report(self._result, self._out_dir)
            self._result.summary["report_path"] = report_path
            self._log(f"[DONE] 报告已生成: {report_path}")
        except Exception:  # noqa: BLE001 - 报告生成失败不影响结果返回
            logger.error("生成报告失败", exc_info=True)
            self._log("[ERROR] 生成报告失败，见日志。")

        self._log(f"[SUMMARY] {self._result.summary.get('overall', 'N/A')} - "
                  f"PASS {self._result.summary.get('pass', 0)} / "
                  f"FAIL {self._result.summary.get('fail', 0)} / "
                  f"N/A {self._result.summary.get('norec', 0)}")
        self.finished_result.emit(self._result)

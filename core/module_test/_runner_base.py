"""Module Test 通用 Runner（QThread）。

LDO/DCDC 各自的 runner 继承本类，仅绑定 module_type + items 注册表，
避免重复 QThread 编排逻辑。规划 §6。

分层：本类依赖 QtCore（QThread/Signal），禁依赖 Qt Widget；
仪器由 UI 注入（N6705C/Scope/Chamber 或 Mock），耗时全在本线程。
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, Callable

from PySide6.QtCore import QThread, Signal

from core.module_test._common import ItemContext
from core.module_test.judge import evaluate_item
from core.module_test.report import save_html_report
from core.module_test.result_model import ItemResult, ModuleTestResult
from debug_config import DEBUG_MOCK
from log_config import get_logger

logger = get_logger(__name__)

_INVALID_DIR_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')


def _safe_dir_part(text: str) -> str:
    """清洗用户输入为合法目录名片段（非法字符→下划线，去首尾空格与点）。"""
    cleaned = _INVALID_DIR_CHARS.sub("_", text.strip()).strip(" .")
    return cleaned


class ModuleTestRunner(QThread):
    """按勾选项串行调度各 item worker 的编排线程。

    Signals:
        progress(int, str): 总进度百分比 + 当前项名。
        item_started(str): 单项开始执行（item_key）。
        item_finished(str, dict): 单项完成（item_key, 摘要）。
        log(str): 日志行。
        finished_result(object): 全部完成，传 ModuleTestResult。
        failed(str): 致命错误。
    """

    progress = Signal(int, str)
    item_started = Signal(str)
    item_finished = Signal(str, dict)
    log = Signal(str)
    finished_result = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        *,
        module_type: str,
        items_registry: dict[str, tuple[str, Any, bool, bool, tuple]],
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
        self._item_overrides = dict(self._cfg.get("item_overrides", {}) or {})
        self._n6705c = n6705c
        self._scope = scope
        self._chamber = chamber
        # 结果目录名 = 芯片_模块_时间戳（芯片描述/模块描述取自 DUT 配置，
        # 非法字符清洗，空段省略，全空回落纯时间戳），便于在 Results 下辨识报告归属
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parts = [p for p in (
            _safe_dir_part(str(self._cfg.get("chip_name") or "")),
            _safe_dir_part(str(self._cfg.get("module_name") or "")),
        ) if p]
        parts.append(stamp)
        self._out_dir = out_dir or os.path.join(
            "Results", "module_test", module_type, "_".join(parts))
        self._stop_flag = False
        self._result = ModuleTestResult(
            module_type=module_type,
            chip_name=str(self._cfg.get("chip_name", "")),
            module_name=str(self._cfg.get("module_name", "")),
            operator=str(self._cfg.get("operator", "")),
            temperature=str(self._cfg.get("temperature", "")),
            started_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def request_stop(self):
        """协作式中断（检查标志位，禁强杀线程）。"""
        self._stop_flag = True

    def _apply_judge(self, item_key: str, result: ItemResult) -> None:
        """按用户判定标准（cfg["judge_criteria"]）判定 PASS/FAIL。

        仅对项本身未判定的结果（passed=None）生效；执行异常的 FAIL 不覆盖。
        与报告异常点标红（table.rules）相互独立：此处决定项 verdict。
        """
        if result.passed is not None:
            return
        criteria = (self._cfg.get("judge_criteria") or {}).get(item_key)
        if not criteria:
            return
        passed, note = evaluate_item(item_key, criteria, result.measured)
        if passed is None:
            if note:
                self._log(f"[JUDGE] {item_key}: {note}")
            return
        result.passed = passed
        result.notes = f"{result.notes}；{note}" if result.notes else note
        verdict = "PASS" if passed else "FAIL"
        self._log(f"[JUDGE] {item_key} → {verdict}（{note}）")

    def _log(self, msg: str) -> None:
        self.log.emit(msg)

    def _progress(self, percent: int, label: str) -> None:
        self.progress.emit(percent, label)

    @staticmethod
    def _query_idn(inst: Any) -> str:
        """取仪器 *IDN? 标识（N6705C 无 identify()，用 .instr.query；示波器有
        identify_instrument()；其它退 identify()）。失败返回空串，不阻断流程。"""
        if inst is None:
            return ""
        try:
            if hasattr(inst, "identify_instrument"):
                return str(inst.identify_instrument()).strip()
            if hasattr(inst, "identify"):
                return str(inst.identify()).strip()
            instr = getattr(inst, "instr", None)
            if instr is not None and hasattr(instr, "query"):
                return str(instr.query("*IDN?")).strip()
        except Exception:  # noqa: BLE001 - IDN 失败不影响测试
            logger.error("查询 *IDN? 失败", exc_info=True)
        return ""

    def _collect_instruments(self) -> list[dict[str, Any]]:
        """汇总本次用到的仪器标识（厂商,型号,序列号,固件 → name/model/sn）。"""
        entries: list[dict[str, Any]] = []
        for label, inst in (("N6705C 电源分析仪", self._n6705c),
                            ("示波器", self._scope),
                            ("温箱", self._chamber)):
            if inst is None:
                continue
            idn = self._query_idn(inst)
            if not idn:
                continue
            parts = [p.strip() for p in idn.split(",")]
            entries.append({
                "name": label,
                "model": parts[1] if len(parts) > 1 else idn,
                "sn": parts[2] if len(parts) > 2 else None,
                "idn": idn,
            })
        return entries

    def run(self):  # noqa: D401 - QThread 入口
        selected: list[str] = [k for k in self._cfg.get("selected_items", []) if k in self._items_registry]
        if not selected:
            self._log("[WARN] 未勾选任何测试项。")
            self.failed.emit("未勾选任何测试项")
            return

        os.makedirs(self._out_dir, exist_ok=True)
        self._result.instruments = self._collect_instruments()
        total = len(selected)
        self._log(f"[RUN] {self._module_type.upper()} Module Test 开始，共 {total} 项，输出目录: {self._out_dir}")

        for idx, item_key in enumerate(selected):
            if self._stop_flag:
                self._log("[STOP] 收到停止请求，终止后续项。")
                break
            name, run_fn, needs_scope, _default_checked, _params = self._items_registry[item_key]
            self._log(f"[{idx + 1}/{total}] 执行 {name}（{item_key}）...")
            self.item_started.emit(item_key)
            self._progress(int(idx / total * 100), name)

            # per-item 参数覆盖：弹窗设置的 override 浅合并进该项专用 cfg（仅本项生效）
            item_cfg = dict(self._cfg)
            override = self._item_overrides.get(item_key)
            if override:
                item_cfg.update(override)

            ctx = ItemContext(
                n6705c=self._n6705c,
                scope=self._scope,
                chamber=self._chamber,
                config=item_cfg,
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
            else:
                self._apply_judge(item_key, result)
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

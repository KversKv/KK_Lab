"""Module Test 通用 Runner（QThread）。

LDO/DCDC 各自的 runner 继承本类，仅绑定 module_type + items 注册表，
避免重复 QThread 编排逻辑。规划 §6。

分层：本类依赖 QtCore（QThread/Signal），禁依赖 Qt Widget；
仪器由 UI 注入（N6705C/Scope/Chamber 或 Mock），耗时全在本线程。
"""
from __future__ import annotations

import csv
import math
import os
import re
import threading
import time
from datetime import datetime
from typing import Any, Callable

from PySide6.QtCore import QThread, Signal

from core.module_test._common import (
    ItemContext,
    load_reg_summary,
    measure_vout,
    parse_channel,
    settle,
    setup_load_channel,
    setup_vout_meter,
    teardown_load,
    vin_current_limit_a,
    write_csv,
)
from core.module_test.judge import evaluate_item
from core.module_test.report import save_html_report
from core.module_test.result_model import ItemResult, ModuleTestResult
from debug_config import DEBUG_MOCK, REPORT_ITEM_TIMING
from log_config import get_logger

logger = get_logger(__name__)

_INVALID_DIR_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')

# 逐项 Vout 偏差门禁：每项结束后 Vout 与首项前基准 V0 的允许偏差（±20 mV）
_VOUT_GUARD_LIMIT_V = 0.020
_VOUT_GUARD_SAMPLES = 3      # 门禁测量采样次数（多次采样去极值均值）
_VOUT_GUARD_SETTLE_S = 0.05  # 门禁采样间隔稳定等待


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
        confirm_request(str, str): 需用户确认的弹窗请求（标题, 正文），
            UI 应答经 respond_confirm() 回传（item 内经 ctx.confirm_fn 调用）。
    """

    progress = Signal(int, str)
    item_started = Signal(str)
    item_finished = Signal(str, dict)
    log = Signal(str)
    finished_result = Signal(object)
    failed = Signal(str)
    confirm_request = Signal(str, str)

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
        # 用户确认弹窗应答（confirm_request 信号 → UI 弹窗 → respond_confirm 回传）
        self._confirm_reply = threading.Event()
        self._confirm_continue = False
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

    def respond_confirm(self, continue_test: bool) -> None:
        """UI 弹窗应答：是否继续（经 confirm_request 信号的回传出口）。"""
        self._confirm_continue = bool(continue_test)
        self._confirm_reply.set()

    def _wait_user_confirm(self, title: str, message: str) -> tuple[bool, bool]:
        """请求 UI 弹窗确认并阻塞等待应答（期间可响应停止请求）。

        返回 (是否已应答, 是否继续)：等待期间用户停止时返回 (False, False)。
        """
        self._confirm_reply.clear()
        self._confirm_continue = False
        self.confirm_request.emit(title, message)
        while not self._confirm_reply.wait(0.1):
            if self._stop_flag:
                return False, False
        return True, self._confirm_continue

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

    def _make_ctx(self, config: dict) -> ItemContext:
        """构造测试项执行上下文（config 为该项专用 cfg）。"""
        return ItemContext(
            n6705c=self._n6705c,
            scope=self._scope,
            chamber=self._chamber,
            config=config,
            out_dir=self._out_dir,
            is_mock=bool(DEBUG_MOCK) or self._n6705c is None,
            stop_flag_fn=lambda: self._stop_flag,
            log_fn=self._log,
            progress_fn=self._progress,
            confirm_fn=self._wait_user_confirm,
        )

    def _setup_vin_current_limit(self) -> None:
        """第一项测试前把 Vin 通道限流设为 (Max Iload + 0.1) A。

        Max Iload 为 DUT 配置的设计最大带载电流（cfg["max_iload_ma"]）；
        各测试项重配 Vin 通道时经 vin_current_limit_a 保持同一限流。
        设置失败降级记日志，不阻断测试启动。
        """
        ctx = self._make_ctx(dict(self._cfg))
        ch = parse_channel(ctx.config.get("vin_channel", 1))
        limit_a = vin_current_limit_a(ctx.config)
        max_iload_ma = max(float(ctx.config.get("max_iload_ma", 400)), 0.0)
        self._log(f"[PRE] Vin 通道 ch{ch} 限流设为 {limit_a:.3f} A"
                  f"（Max Iload {max_iload_ma:g} mA + 0.1 A）。")
        try:
            self._n6705c.set_current_limit(ch, limit_a)
        except Exception:  # noqa: BLE001 - 限流下发失败降级记录，不阻断流程
            logger.error("set vin current limit ch%d failed", ch, exc_info=True)
            self._log(f"[WARN] Vin 通道 ch{ch} 限流设置失败，继续测试。")

    def _preload_iload(self) -> None:
        """配置完成后、第一项测试前的 Iload 通道预拉载步骤。

        1mA 持续 1s 后关断：setup_load_channel 先写电流（非 0）再开启，
        满足 CCLoad 禁 0mA 开机红线；收尾 teardown_load 仅 channel_off。
        Mock 模式 settle 跳过（通道调用为安全 no-op）。
        """
        ctx = self._make_ctx(dict(self._cfg))
        ch = parse_channel(ctx.config.get("iload_channel", 3))
        self._log(f"[PRE] Iload 通道 ch{ch} 预拉载 1mA，持续 1s...")
        setup_load_channel(ctx, ch, initial_current_a=0.001)
        settle(ctx, 1.0)
        teardown_load(ctx, ch)
        self._log("[PRE] Iload 通道预拉载完成，通道已关断。")

    def _record_vout_baseline(self) -> float | None:
        """第一项测试开始前记录 Vout 基准电压 V0（逐项偏差门禁基准）。

        读取失败返回 None：记 WARN 后门禁降级为跳过，不阻断测试启动。
        """
        ctx = self._make_ctx(dict(self._cfg))
        # force=True：序列开头做首次完整 Step1~3 入位并写模块级缓存，
        # 后续各项 setup_vout_meter 走快路径仅重放缓存的 scale/offset
        setup_vout_meter(ctx, force=True)
        v0 = measure_vout(ctx, count=_VOUT_GUARD_SAMPLES,
                          settle_s=_VOUT_GUARD_SETTLE_S, default=float("nan"))
        if math.isnan(v0):
            self._log("[WARN] Vout 基准电压 V0 读取失败，跳过逐项电压偏差门禁。")
            return None
        self._log(f"[VOUT] 基准电压 V0 = {v0:.4f} V")
        return v0

    def _check_vout_deviation(self, ctx: ItemContext, baseline: float | None,
                              item_key: str) -> bool:
        """单项结束后 Vout 偏差门禁：与 V0 偏差超过 ±20 mV 返回 False。

        baseline 为 None（基准读取失败）时跳过检查；本次读取失败仅记 WARN
        不中断（测量异常不等于 DUT 输出异常，避免误停）。
        """
        if baseline is None:
            return True
        setup_vout_meter(ctx)
        v = measure_vout(ctx, count=_VOUT_GUARD_SAMPLES,
                         settle_s=_VOUT_GUARD_SETTLE_S, default=float("nan"))
        if math.isnan(v):
            self._log(f"[WARN] {item_key} 结束后 Vout 读取失败，跳过偏差检查。")
            return True
        dev_v = v - baseline
        if abs(dev_v) > _VOUT_GUARD_LIMIT_V:
            self._log(f"[ERROR] {item_key} 结束后 Vout = {v:.4f} V，与基准 "
                      f"V0 = {baseline:.4f} V 偏差 {dev_v * 1000.0:+.1f} mV，"
                      f"超过 ±{_VOUT_GUARD_LIMIT_V * 1000.0:.0f} mV，停止后续测试。")
            return False
        self._log(f"[VOUT] {item_key} 结束后 Vout = {v:.4f} V"
                  f"（偏差 {dev_v * 1000.0:+.1f} mV，在 ±"
                  f"{_VOUT_GUARD_LIMIT_V * 1000.0:.0f} mV 内）。")
        return True

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

        # 配置完成后、第一项测试前：Vin 通道限流设为 (Max Iload + 0.1) A
        self._setup_vin_current_limit()

        # 配置完成后、第一项测试前：Iload 通道 1mA 预拉载 1s 后关断
        self._preload_iload()

        # 第一项测试开始前：记录 Vout 基准电压 V0（逐项偏差门禁基准）
        vout_baseline = self._record_vout_baseline()
        aborted_reason = ""

        # 待回填的 Load Regulation 项（ripple_key -> load_reg item_key）：
        # 开关开启时跳过本项测量，待 ripple 完成后以其 CSV 数据生成结果
        pending_follow: dict[str, str] = {}

        for idx, item_key in enumerate(selected):
            if self._stop_flag:
                self._log("[STOP] 收到停止请求，终止后续项。")
                break
            name, run_fn, needs_scope, _default_checked, _params = self._items_registry[item_key]

            # Load Regulation「直接使用 Load Capability&Ripple 测试值」：
            # 开关开启且 ripple 项已勾选时直接跳过本项（不进入运行态展示），
            # 待 ripple 完成后以其实测数据回填本项结果；ripple 未勾选则回退自身参数
            if (item_key.endswith("_load_reg")
                    and (self._item_overrides.get(item_key) or {}).get("use_ripple_sweep")):
                ripple_key = item_key.replace("_load_reg", "_ripple")
                if ripple_key in selected:
                    self._log(f"[{idx + 1}/{total}] [SKIP] {name} 已启用「直接使用 Load "
                              "Capability&Ripple 测试值」，跳过本项测量，"
                              "结果将在 Load Capability&Ripple 完成后生成。")
                    pending_follow[ripple_key] = item_key
                    continue
                self._log("[WARN] Load Regulation 已开启「直接使用 Load "
                          "Capability&Ripple 测试值」，但该测试项本次未勾选，"
                          "回退使用本项自身参数。")

            self._log(f"[{idx + 1}/{total}] 执行 {name}（{item_key}）...")
            self.item_started.emit(item_key)
            self._progress(int(idx / total * 100), name)

            # per-item 参数覆盖：弹窗设置的 override 浅合并进该项专用 cfg（仅本项生效）
            item_cfg = dict(self._cfg)
            override = self._item_overrides.get(item_key)
            if override:
                item_cfg.update(override)

            ctx = self._make_ctx(item_cfg)
            item_t0 = time.monotonic()
            try:
                result: ItemResult = run_fn(ctx)
            except Exception:  # noqa: BLE001 - 单项异常不阻断整体
                logger.error("item %s 执行异常", item_key, exc_info=True)
                self._log(f"[ERROR] {item_key} 执行异常，记为 FAIL。")
                result = ItemResult(item_key=item_key, name=name, passed=False,
                                    notes="执行异常，见日志")
            else:
                self._apply_judge(item_key, result)
            if REPORT_ITEM_TIMING:
                result.duration_s = time.monotonic() - item_t0
                self._log(f"[TIME] {name} 耗时 {result.duration_s:.1f} s")
            self._result.items.append(result)
            self.item_finished.emit(item_key, result.to_summary())
            self._progress(int((idx + 1) / total * 100), name)

            # 回填：Load Regulation 直接使用 Load Capability&Ripple 数据作为结果
            if item_key in pending_follow:
                lr_key = pending_follow.pop(item_key)
                lr_result = self._build_follow_load_reg_result(lr_key, result)
                self._apply_judge(lr_key, lr_result)
                self._result.items.append(lr_result)
                self.item_finished.emit(lr_key, lr_result.to_summary())
                self._progress(int((idx + 1) / total * 100), name)

            # 逐项 Vout 偏差门禁：与 V0 偏差超 ±20 mV 则停止后续项
            if not self._check_vout_deviation(ctx, vout_baseline, item_key):
                aborted_reason = f"{item_key} 结束后 Vout 与基准 V0 偏差超过 ±20 mV"
                break

        self._result.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._result.build_summary()
        if aborted_reason:
            self._result.summary["aborted"] = aborted_reason

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

    def _build_follow_load_reg_result(self, load_reg_key: str,
                                      ripple_result: ItemResult) -> ItemResult:
        """由 Load Capability&Ripple 的实测数据生成 Load Regulation 结果。

        读取 ripple CSV 的 Iload/Vout 前两列重算 load_reg_summary，写独立
        {load_reg_key}.csv（报告表格/曲线/判断标准照常渲染）；ripple 未产生
        有效数据（跳过/异常/无 CSV）时回落 N/A 备注结果。
        """
        name = self._items_registry[load_reg_key][0]
        lr_cfg = dict(self._cfg)
        lr_cfg.update(self._item_overrides.get(load_reg_key) or {})
        knee_ma = float(lr_cfg.get("iload_knee_ma", 0) or 0)

        rows: list[list[float]] = []
        csv_src = ripple_result.raw_csv_path
        if csv_src and os.path.exists(csv_src):
            try:
                with open(csv_src, "r", encoding="utf-8", newline="") as f:
                    for rec in csv.reader(f):
                        if len(rec) < 2:
                            continue
                        try:
                            rows.append([float(rec[0]), float(rec[1])])
                        except ValueError:
                            continue  # 跳过表头/非数值行
            except OSError:
                logger.error("读取 Load Capability&Ripple CSV 失败: %s",
                            csv_src, exc_info=True)

        if not rows:
            reason = ripple_result.notes or "无 CSV 数据"
            return ItemResult(item_key=load_reg_key, name=name, passed=None,
                              notes=f"Load Capability&Ripple 未产生有效数据"
                                    f"（{reason}），本项无结果")

        csv_path = os.path.join(self._out_dir, f"{load_reg_key}.csv")
        write_csv(csv_path, ["Iload (mA)", "Vout (mV)"], rows)
        s = load_reg_summary(rows, knee_ma)
        measured: dict[str, Any] = {
            "points": len(rows),
            "knee_ma": s["knee_ma"],
            "vout_drop_mv": s["vout_drop_mv"],
            "load_reg_pct": s["load_reg_pct"],
            "vout_drop_linear_mv": s["vout_drop_linear_mv"],
            "load_reg_linear_pct": s["load_reg_linear_pct"],
        }
        if self._module_type == "ldo":
            # LDO 额外指标：全量程负载调整率（mV/A），与 load_line_reg 对齐
            i_start, i_end = rows[0][0], rows[-1][0]
            measured["load_reg_mv_per_a"] = round(
                s["vout_drop_mv"] / max((i_end - i_start) / 1000.0, 1e-6), 4)
        self._log(f"[FOLLOW] {load_reg_key} 已取 Load Capability&Ripple 实测数据："
                  f"{len(rows)} 点，Vout 跌落 {s['vout_drop_mv']:.4f} mV")
        return ItemResult(item_key=load_reg_key, name=name, unit="mV",
                          passed=None, measured=measured, raw_csv_path=csv_path,
                          notes="数据取自 Load Capability&Ripple 实测结果")

"""ModuleTestAIContract — Module Test 子页 AI 契约（mixin，从 _base_subpage 拆出）。

宿主（``ModuleTestSubPageBase``）须具备：``PAGE_KEY / MODULE_TYPE /
is_test_running / get_test_config / _missing_instruments / _on_start_test /
_on_stop_test / _on_open_report / _on_clear_results / _on_select_all_items /
_last_result / _last_report_path / left_rail.dut_panel /
detail_dock.log_panel / _ui_action_registry``。

为什么这样拆：AI 契约方法（§8.1/§8.2）是稳定的对外接口，与页面装配/
run flow 变化频率不同；独立 mixin 后基类只剩装配与 run flow（<500 行）。
"""
from __future__ import annotations

from typing import Any

from core.ai.page_contract import (
    CAP_APPLY_CONFIG, CAP_GET_CONFIG, CAP_GET_RESULT, CAP_START_TEST, CAP_STOP_TEST,
)
from core.ai.ui_action_registry import UIActionSpec
from log_config import get_logger
from ui.widgets.toast import Toast

_logger = get_logger(__name__)


class ModuleTestAIContract:
    """AI 契约方法集（capabilities / get / apply / start / stop / result + UIActionSpec）。"""

    def ai_capabilities(self) -> set[str]:
        return {CAP_GET_CONFIG, CAP_APPLY_CONFIG, CAP_START_TEST, CAP_STOP_TEST, CAP_GET_RESULT}

    def ai_get_config(self) -> dict[str, Any] | None:
        try:
            cfg = self.get_test_config()
            cfg["sweep_dimensions"] = ["load_current"]
            # 仅暴露当前勾选项会遍历的维度
            sel = set(cfg.get("selected_items", []))
            if any(k.endswith("_line_reg") for k in sel):
                cfg["sweep_dimensions"].append("vin")
            return cfg
        except Exception:  # noqa: BLE001
            _logger.error("AI 读取 %s 配置失败", self.PAGE_KEY, exc_info=True)
            return None

    def ai_apply_config(self, payload: Any) -> tuple[bool, str]:
        if self.is_test_running:
            return False, "测试运行中，无法修改配置，请先停止测试。"
        if not isinstance(payload, dict):
            return False, "配置草案格式无效（期望 dict）。"
        dut = self.left_rail.dut_panel
        changed: list[str] = []
        try:
            if "chip_name" in payload:
                dut.chip_name_edit.setText(str(payload["chip_name"]))
                changed.append("chip_name")
            if "module_name" in payload:
                dut.module_name_edit.setText(str(payload["module_name"]))
                changed.append("module_name")
            if "operator" in payload:
                dut.operator_edit.setText(str(payload["operator"]))
                changed.append("operator")
            if "vout_nominal_mv" in payload:
                dut.vout_nominal_spin.setValue(int(payload["vout_nominal_mv"]))
                changed.append("vout_nominal_mv")
        except Exception:  # noqa: BLE001
            _logger.error("apply_config 落地失败", exc_info=True)
            return False, "配置落地异常，见日志。"
        Toast.popup(self, f"已应用配置：{', '.join(changed) if changed else '无变更'}",
                    severity="info")
        return True, f"已应用配置：{', '.join(changed) if changed else '无变更'}"

    def ai_start_test(self) -> tuple[bool, str]:
        if self.is_test_running:
            return False, "测试已在运行中。"
        cfg = self.get_test_config()
        if not cfg.get("selected_items"):
            return False, "未勾选任何测试项，请先勾选。"
        missing = self._missing_instruments(cfg)
        if missing:
            detail = "；".join(missing)
            self.detail_dock.log_panel.append_log(f"[AI] 启动被拒绝：仪器未连接：{detail}")
            return False, f"仪器未连接，无法启动测试：{detail}。"
        self.detail_dock.log_panel.append_log(
            f"[AI] 请求启动 {self.MODULE_TYPE.upper()} 测试，勾选 {len(cfg['selected_items'])} 项。"
        )
        try:
            self._on_start_test()
        except Exception:  # noqa: BLE001
            _logger.error("AI 启动 %s 测试失败", self.PAGE_KEY, exc_info=True)
            return False, "启动测试异常，请查看日志。"
        return (True, "已请求启动测试。") if self.is_test_running else (False, "启动未成功，请查看执行日志。")

    def ai_stop_test(self) -> tuple[bool, str]:
        if not self.is_test_running:
            return False, "当前未在运行测试。"
        self.detail_dock.log_panel.append_log("[AI] 请求停止测试。")
        try:
            self._on_stop_test()
        except Exception:  # noqa: BLE001
            _logger.error("AI 停止 %s 测试失败", self.PAGE_KEY, exc_info=True)
            return False, "停止测试异常，请查看日志。"
        return True, "已发送停止请求。"

    def ai_get_result_summary(self) -> dict[str, Any] | None:
        # 无结果时返回最小摘要（available=False），让 AI 能区分"未跑过"与
        # "不支持"，避免枢纽拿到 None 后无法给用户可读反馈。
        if self._last_result is None:
            return {
                "available": False,
                "running": self.is_test_running,
                "module_type": self.MODULE_TYPE,
            }
        r = self._last_result
        s = dict(r.summary)
        s["available"] = True
        s["running"] = self.is_test_running
        s["module_type"] = r.module_type
        # 元数据：让 AI 给出带上下文的结果解读（芯片 / 操作员 / 温度 / 起止时间）
        s["chip_name"] = r.chip_name
        s["operator"] = r.operator
        s["temperature"] = r.temperature
        s["started_at"] = r.started_at
        s["finished_at"] = r.finished_at
        # 逐项结果：仅凭汇总计数（pass/fail/norec）AI 无法定位失败项与原因，
        # 补 item_key / name / unit / verdict / notes，使结果摘要可被准确解读。
        s["items"] = [
            {
                "item_key": it.item_key,
                "name": it.name,
                "unit": it.unit,
                "passed": "N/A" if it.passed is None else ("PASS" if it.passed else "FAIL"),
                "notes": it.notes,
            }
            for it in r.items
        ]
        return s

    # ------------------------------------------------------------------ UIActionSpec
    def _register_ai_ui_actions(self) -> None:
        if self._ui_action_registry is None:
            return
        self._ui_action_registry.register_many([
            UIActionSpec(
                id=f"{self.PAGE_KEY}.open_report", label="打开报告",
                page_key=self.PAGE_KEY, handler=self._ai_open_report,
                risk="low", confirm=False,
                enabled_when=lambda: self._last_report_path is not None,
                description="打开最近一次 Module Test 的 HTML 报告。",
            ),
            UIActionSpec(
                id=f"{self.PAGE_KEY}.clear_results", label="清空结果",
                page_key=self.PAGE_KEY, handler=self._ai_clear_results,
                risk="low", confirm=False,
            ),
            UIActionSpec(
                id=f"{self.PAGE_KEY}.select_all_items", label="全选测试项",
                page_key=self.PAGE_KEY, handler=self._on_select_all_items,
                risk="low", confirm=False,
            ),
        ])

    def _ai_open_report(self) -> tuple[bool, str]:
        if not self._last_report_path:
            return False, "暂无报告，请先执行测试。"
        self._on_open_report()
        return True, "已打开报告。"

    def _ai_clear_results(self) -> tuple[bool, str]:
        self._on_clear_results()
        return True, "已清空结果。"

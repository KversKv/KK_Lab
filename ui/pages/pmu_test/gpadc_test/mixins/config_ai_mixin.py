"""GPADCTestUI 配置读写 / AI 契约 Mixin。

从 ui/pages/pmu_test/gpadc_test_ui.py 平移而来，行为零变更。
类装配见 gpadc_test_ui.py。"""

from PySide6.QtWidgets import QFileDialog
from PySide6.QtCore import QTimer
import math
import threading
from typing import Any
from pathlib import Path
from log_config import get_logger
from core.pmu_test.gpadc import parse_raw_lsb_value, ALGORITHM_REGISTRY
from resource_path import get_user_data_dir
from core.ai.page_contract import (
    CAP_APPLY_CONFIG,
    CAP_GET_CONFIG,
    CAP_GET_RESULT,
    CAP_START_TEST,
    CAP_STOP_TEST,
)
from core.ai.ui_action_registry import UIActionSpec

logger = get_logger(__name__)

# AI 回填可视化（AIAssist_PageScopedControlPlan.md §4.2 / Phase 3）：
# 被 AI 修改的控件临时高亮边框色 + 持续时长。
_AI_HIGHLIGHT_QSS = "border: 1px solid #15d1a3;"
_AI_HIGHLIGHT_MS = 1500


class _ConfigAiMixin:
    """配置读写 / AI 契约 Mixin"""

    def _register_ai_ui_actions(self):
        """§5b.5：登记本页无专用接口的按钮为 AI 可触发的具名 UI 动作。

        handler 复用按钮原槽；启停已有专用契约，不在此重复登记。
        """
        registry = self._ui_action_registry
        if registry is None:
            return

        def _wrap(label, fn):
            def _run() -> tuple[bool, str]:
                try:
                    fn()
                    return True, f"{label} 已执行。"
                except Exception as exc:  # noqa: BLE001
                    logger.error("%s 执行失败", label, exc_info=True)
                    return False, f"{label} 执行失败：{exc}"
            return _run

        registry.register_many([
            UIActionSpec(
                id="pmu_gpadc.export_result",
                label="导出结果",
                page_key="pmu_gpadc",
                handler=_wrap("导出结果", self.export_result),
                risk="low",
                confirm=False,
                enabled_when=lambda: self._export_data is not None,
                description="导出当前 GPADC 测试结果为 Excel。需已有测试结果数据。",
            ),
            UIActionSpec(
                id="pmu_gpadc.export_search_gif",
                label="导出寻优动图",
                page_key="pmu_gpadc",
                handler=_wrap("启动寻优动图导出", self.export_search_gif),
                risk="low",
                confirm=False,
                enabled_when=self._can_export_search_gif,
                description="后台导出 GPADC Auto Best 搜索过程 GIF，需已有完整候选结果。",
            ),
        ])

    def _on_save_multi_ch_config(self):
        """保存页面完整配置（含多通道与前置配置）到 JSON 文件。"""
        import json
        from pathlib import Path

        cfg = self.get_test_config()
        cfg['test_item'] = self.TEST_MULTI_CH_TEMP
        payload = {"schema_version": 1, "page": "gpadc", "config": cfg}

        start_dir = Path(get_user_data_dir("gpadc_configs"))
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 GPADC 配置", str(start_dir / "multi_ch_temp.json"),
            "JSON Files (*.json)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self._append_log(f"[INFO] 配置已保存: {path}")
        except Exception as e:
            logger.error("保存 GPADC 配置失败: %s", e, exc_info=True)
            self._append_log(f"[ERROR] 配置保存失败: {e}")

    def _on_load_multi_ch_config(self):
        """从 JSON 文件加载配置并回填（含测试项切换、多通道与前置配置）。"""
        import json

        start_dir = get_user_data_dir("gpadc_configs")
        path, _ = QFileDialog.getOpenFileName(
            self, "加载 GPADC 配置", start_dir, "JSON Files (*.json)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as e:
            logger.error("加载 GPADC 配置失败: %s", e, exc_info=True)
            self._append_log(f"[ERROR] 配置加载失败: {e}")
            return
        cfg = payload.get("config") if isinstance(payload, dict) else None
        if not isinstance(cfg, dict):
            self._append_log("[ERROR] 配置文件格式无效（缺少 config 段）")
            return
        ok, msg = self.apply_config_to_controls(cfg)
        self._append_log(f"[INFO] 配置加载: {msg}")

    def get_test_config(self):
        acquisition_mode = 'IIC' if self.iic_radio.isChecked() else 'UART'
        dut_port = self.get_selected_serial_port() or ""

        return {
            'n6705c_connected': self.is_connected,
            'chamber_connected': self.is_chamber_connected,
            'test_item': self.current_test_item,
            'data_acquisition_mode': acquisition_mode,
            'iic_device_address': self.iic_device_address.text(),
            'iic_data_address': self.iic_data_address.text(),
            'iic_width': self.iic_width_combo.currentData(),
            'iic_speed': self.iic_speed_combo.currentData(),
            'dut_port': dut_port,
            'uart_keyword': self.uart_keyword.text(),
            'voltage_channel': self.voltage_channel.currentData(),
            'voltage_min': self.voltage_min.value(),
            'voltage_max': self.voltage_max.value(),
            'voltage_step': self.voltage_step.value(),
            'linearity_n_reg_addr': self.linearity_n_reg_addr.text(),
            'linearity_p_reg_addr': self.linearity_p_reg_addr.text(),
            'linearity_link_np': self.linearity_link_np.isChecked(),
            'linearity_auto_best': self.linearity_auto_best.isChecked(),
            'linearity_auto_strategy': self.linearity_auto_strategy.currentData(),
            'linearity_auto_repeat': self.linearity_auto_repeat.value(),
            'linearity_start': self.linearity_start.text(),
            'linearity_end': self.linearity_end.text(),
            'linearity_value_start': self.linearity_value_start.text(),
            'linearity_value_end': self.linearity_value_end.text(),
            'linearity_value_step': self.linearity_value_step.text(),
            'linearity_n_start': self.linearity_n_start.text(),
            'linearity_n_end': self.linearity_n_end.text(),
            'linearity_n_value_start': self.linearity_n_value_start.text(),
            'linearity_n_value_end': self.linearity_n_value_end.text(),
            'linearity_n_value_step': self.linearity_n_value_step.text(),
            'linearity_p_start': self.linearity_p_start.text(),
            'linearity_p_end': self.linearity_p_end.text(),
            'linearity_p_value_start': self.linearity_p_value_start.text(),
            'linearity_p_value_end': self.linearity_p_value_end.text(),
            'linearity_p_value_step': self.linearity_p_value_step.text(),
            'temp_min': self.temp_min.value(),
            'temp_max': self.temp_max.value(),
            'temp_step': self.temp_step.value(),
            'soak_time': self.soak_time.value(),
            'sample_count': self.sample_count.value(),
            'calib_low': self.calib_low.text(),
            'calib_high': self.calib_high.text(),
            'ft_calib_v1': self.ft_calib_v1.text(),
            'ft_calib_c1': self.ft_calib_c1.text(),
            'ft_calib_v2': self.ft_calib_v2.text(),
            'ft_calib_c2': self.ft_calib_c2.text(),
            'ft_raw_tol': self.ft_raw_tol.value(),
            'ft_err_limit': self.ft_err_limit.value(),
            'ft_divider_ratio': self.ft_divider_ratio.value(),
            'algorithm': self._collect_algorithm_config(),
            'outlier_filter': {
                'enabled': self.outlier_filter_switch.isChecked(),
                'pos_offset': self.outlier_pos_offset.value(),
                'neg_offset': self.outlier_neg_offset.value(),
            },
            'current_monitor': {
                'enabled': self.current_monitor_switch.isChecked(),
                'channel': self.current_monitor_channel.currentData(),
            },
            'metrics_options': dict(self._metrics_options),
            'multi_channels': self.multi_ch_panel.get_channels(),
            'pre_config': self.multi_ch_panel.get_pre_config(),
        }

    @staticmethod
    def _fmt_code_hex(v):
        """ADC code 指标卡格式：十进制 + 括号内十六进制（均值取整换算）。"""
        return f"{float(v):.3f} (0x{int(round(float(v))):X})"

    @staticmethod
    def _set_metric_value(label, text, object_name=None):
        """指标卡值写入；object_name 变化时重刷 QSS 配色（绿/黄/蓝）。"""
        label.setText(text)
        if object_name is not None and label.objectName() != object_name:
            label.setObjectName(object_name)
            label.style().unpolish(label)
            label.style().polish(label)

    def _reset_fv_cards(self, text="---"):
        self.linearity_value.setText("---")
        for label in (self.inl_value, self.step_nl_value, self.sigma_noise_value,
                      self.enob_value, self.gain_error_value, self.offset_error_value,
                      self.coverage_value):
            label.setText(text)
        self._set_metric_value(self.inl_value, text, "metric_value_green")
        self.gain_name_label.setText("GAIN")
        self.offset_name_label.setText("OFFSET")

    def _reset_cnt_cards(self):
        for label in (self.avg_value, self.min_value, self.max_value,
                      self.std_value, self.pp_value, self.samples_value,
                      self.raw_minmax_value, self.outliers_value, self.noise_free_value):
            label.setText("---")
        self.std_name_label.setText("STD (code)")

    def _update_fv_cards(self, params):
        """Force Voltage 指标卡刷新（新口径：拟合残差 INL / Step NL / σ / 双 ENOB / 参照模式）。"""
        if not params.get('valid'):
            self._reset_fv_cards("N/A")
            return
        self.linearity_value.setText(f"{params['linearity']:.3f}")

        inl_color = ("metric_value_yellow" if params.get('inl_below_noise')
                     else "metric_value_green")
        self._set_metric_value(
            self.inl_value,
            f"{params['inl_max']:+.2f} / {params['inl_min']:+.2f}",
            inl_color,
        )
        inl_tip = ("INL = mean - (k_fit*v + b_fit), least-squares fit.\n"
                   "Display: +max / min (LSB).")
        if params.get('inl_below_noise'):
            mean_noise = params.get('mean_noise_lsb')
            inl_tip += (f"\nBelow noise floor: max|INL| < 4*mean_noise"
                        f" (mean_noise = {mean_noise:.2f} LSB)."
                        if mean_noise is not None else "\nBelow noise floor.")
        self.inl_value.setToolTip(inl_tip)

        if params.get('step_nl_max') is not None:
            self.step_nl_value.setText(
                f"{params['step_nl_max']:+.3f} / {params['step_nl_min']:+.3f}")
        else:
            self.step_nl_value.setText("N/A")

        sigma = params.get('sigma_noise_lsb')
        self.sigma_noise_value.setText(f"{sigma:.2f}" if sigma is not None else "N/A")

        enob_parts = [
            f"{params[key]:.2f}" if params.get(key) is not None else "N/A"
            for key in ('enob_noise', 'enob_dc')
        ]
        enob_text = " / ".join(enob_parts)
        if params.get('enob_spec') is not None:
            enob_text += f" / {params['enob_spec']:.2f} (spec)"
        self.enob_value.setText(enob_text)

        ref_mode = params.get('ref_mode') or 'none'
        if ref_mode == 'spec':
            self.gain_name_label.setText("GAIN ERR")
            self.offset_name_label.setText("OFFSET ERR")
            self.gain_error_value.setText(f"{params['gain_error_pct']:+.3f} %")
            self.offset_error_value.setText(f"{params['offset_error_lsb']:+.2f} LSB")
        elif ref_mode == 'batch_nominal':
            self.gain_name_label.setText("GAIN DEV vs BATCH")
            self.offset_name_label.setText("OFFSET DEV vs BATCH")
            self.gain_error_value.setText(f"{params['gain_error_pct']:+.3f} %")
            self.offset_error_value.setText(f"{params['offset_error_lsb']:+.2f} LSB")
        else:
            self.gain_name_label.setText("SLOPE")
            self.offset_name_label.setText("INTERCEPT")
            self.gain_error_value.setText(f"{params['k_fit']:.1f} LSB/V")
            self.offset_error_value.setText(f"{params['b_fit']:.1f} LSB")

        self.coverage_value.setText(
            f"{params['v_min']:.3f}~{params['v_max']:.3f} V | "
            f"{params['code_coverage_pct']:.1f}%")

    def update_test_result(self, result):
        result = result or {}
        if self.current_test_item == self.TEST_1000CNT:
            self.avg_value.setText(self._fmt_code_hex(result['avg']) if 'avg' in result else "---")
            self.min_value.setText(self._fmt_code_hex(result['min']) if 'min' in result else "---")
            self.max_value.setText(self._fmt_code_hex(result['max']) if 'max' in result else "---")
            self.std_value.setText(f"{result['std']:.3f}" if 'std' in result else "---")
            self.pp_value.setText(f"{result['pp']:.0f}" if 'pp' in result else "---")
            self.samples_value.setText(str(result['count']) if 'count' in result else "---")
            avg_tip = "Arithmetic mean of all samples."
            if result.get('trimmed_avg') is not None:
                avg_tip += f"\n5% trimmed mean: {result['trimmed_avg']:.3f}"
            self.avg_value.setToolTip(avg_tip)
            divisor = int(result.get('algo_divisor') or 1)
            self.std_name_label.setText(
                "STD (code)" if divisor <= 1 else f"STD (code, avg of {divisor})")
            if 'raw_min' in result and 'raw_max' in result:
                self.raw_minmax_value.setText(
                    f"{self._fmt_data_value(result['raw_min'])} / "
                    f"{self._fmt_data_value(result['raw_max'])}")
            else:
                self.raw_minmax_value.setText("---")
            self.outliers_value.setText(
                str(int(result['outliers_removed'])) if 'outliers_removed' in result else "---")
            self.noise_free_value.setText(
                f"{result['noise_free_bits']:.2f}"
                if result.get('noise_free_bits') is not None else "N/A")
            self._reset_fv_cards()
        else:
            self._reset_cnt_cards()
            self._update_fv_cards(result)

    def clear_results(self):
        self._reset_fv_cards()
        # 清除1000CNT TEST的结果
        self._reset_cnt_cards()
        # 清除 FT Calibration Check 的结果
        self.ft_p1_value.setText("---")
        self.ft_p2_value.setText("---")
        self.ft_max_err_value.setText("---")
        self.ft_rms_err_value.setText("---")
        self.ft_cons_value.setText("---")
        self.ft_result_value.setText("---")
        self.ft_result_value.setStyleSheet("")

    # ------------------------------------------------------------------
    # 最近测试管理：记录 / 对比 / 载入 / 清空
    # ------------------------------------------------------------------

    def get_test_mode(self):
        return "GPADC Test"

    def set_test_mode(self, mode):
        pass

    def get_test_id(self):
        return "GPADC_TEST_001"

    def set_test_id(self, test_id):
        pass

    def _parse_ft_calib_inputs(self):
        """解析 FT Calibration Check 的两点四值与判定阈值；无效时记录日志并返回 None。"""
        try:
            v1 = float(self.ft_calib_v1.text().strip())
            c1 = parse_raw_lsb_value(self.ft_calib_c1.text())
            v2 = float(self.ft_calib_v2.text().strip())
            c2 = parse_raw_lsb_value(self.ft_calib_c2.text())
        except ValueError:
            self._append_log("[ERROR] FT 校准点格式无效（电压填数值 V；校准码支持十进制/0x 十六进制及 base+offset，如 0x13F+2000）")
            self.set_system_status("错误: FT 校准点格式无效", is_error=True)
            return None
        if not all(math.isfinite(x) for x in (v1, c1, v2, c2)):
            self._append_log("[ERROR] FT 校准点需为有限数值")
            self.set_system_status("错误: FT 校准点格式无效", is_error=True)
            return None
        if v1 == v2 or c1 == c2:
            self._append_log("[ERROR] FT 两校准点的电压或校准码相同，K/B 不可解")
            self.set_system_status("错误: FT 校准点退化", is_error=True)
            return None
        return {
            'calib_p1': (v1, c1),
            'calib_p2': (v2, c2),
            'raw_tol_lsb': self.ft_raw_tol.value(),
            'err_limit_mv': self.ft_err_limit.value(),
            'divider_ratio': self.ft_divider_ratio.value(),
        }

    def _parse_calib_points(self):
        """解析用户填写的两个校准点；均留空返回 None 表示自动选取。"""
        low_text = self.calib_low.text().strip()
        high_text = self.calib_high.text().strip()
        if not low_text and not high_text:
            return None
        try:
            v_low = float(low_text)
            v_high = float(high_text)
        except ValueError:
            self._append_log("[WARN] 校准点格式无效（需填写两个数值），回退为自动选取")
            return None
        if not (math.isfinite(v_low) and math.isfinite(v_high)):
            self._append_log("[WARN] 校准点需为有限数值，回退为自动选取")
            return None
        if v_low == v_high:
            self._append_log("[WARN] 两个校准点相同，回退为自动选取")
            return None
        return (min(v_low, v_high), max(v_low, v_high))

    # ------------------------------------------------------------------
    # 采样算法配置：注册表驱动，新增算法无需改动此处以外的 UI 代码
    # ------------------------------------------------------------------

    def _collect_algorithm_config(self):
        """收集当前算法配置；未选用（None）时返回 None，等同原始流程。"""
        algo_id = self.algorithm_combo.currentData()
        if not algo_id or algo_id not in ALGORITHM_REGISTRY:
            return None
        params = {}
        for key, spin in self._algo_param_widgets.items():
            val = spin.value()
            params[key] = int(round(val)) if spin.decimals() == 0 else float(val)
        return {'id': algo_id, 'params': params}

    def ai_capabilities(self) -> set[str]:
        return {
            CAP_GET_CONFIG,
            CAP_APPLY_CONFIG,
            CAP_START_TEST,
            CAP_STOP_TEST,
            CAP_GET_RESULT,
        }

    def ai_get_config(self) -> dict[str, Any] | None:
        try:
            return self.get_test_config()
        except Exception:  # noqa: BLE001 - 快照失败降级为 None
            logger.error("AI 读取 GPADC 测试配置失败", exc_info=True)
            return None

    def ai_apply_config(self, payload: Any) -> tuple[bool, str]:
        """落地配置草案到控件（写操作，经确认+审计后由枢纽调用）。

        运行中拒绝改配置（§6.3），避免与正在执行的测试冲突。
        """
        if self.is_test_running:
            return False, "测试运行中，无法修改配置，请先停止测试。"
        return self.apply_config_to_controls(payload if isinstance(payload, dict) else {})

    def ai_start_test(self) -> tuple[bool, str]:
        if self.is_test_running:
            return False, "测试已在运行中。"
        # 按当前测试项与电流监控开关的仪器需求前置校验
        required = self._required_instruments()
        if "n6705c" in required and (not self.is_connected or self.n6705c is None):
            return False, f"当前测试项 {self.current_test_item} 需要电源仪器，请先连接再启动。"
        if "chamber" in required and (not self.is_chamber_connected or self.chamber is None):
            return False, f"当前测试项 {self.current_test_item} 需要温箱，请先连接温箱再启动。"
        # I2C 模式下校验地址可解析
        if self.iic_radio.isChecked():
            try:
                int(self.iic_device_address.text(), 16)
                int(self.iic_data_address.text(), 16)
            except ValueError:
                return False, "I2C 设备/寄存器地址格式无效（应为 16 进制）。"
        self.append_log(f"[AI] 请求启动 GPADC 测试：{self.current_test_item}。")
        try:
            self._start_test()
        except Exception:  # noqa: BLE001 - 启动异常转可读结果
            logger.error("AI 启动 GPADC 测试失败", exc_info=True)
            return False, "启动测试异常，请查看日志。"
        if self.is_test_running:
            return True, f"已请求启动 GPADC 测试：{self.current_test_item}。"
        return False, "启动未成功，请查看执行日志。"

    def ai_stop_test(self) -> tuple[bool, str]:
        if not self.is_test_running:
            return False, "当前未在运行测试。"
        self.append_log("[AI] 请求停止测试。")
        try:
            self._stop_test()
        except Exception:  # noqa: BLE001 - 停止异常转可读结果
            logger.error("AI 停止 GPADC 测试失败", exc_info=True)
            return False, "停止测试异常，请查看日志。"
        return True, "已发送停止请求。"

    def ai_get_result_summary(self) -> dict[str, Any] | None:
        summary: dict[str, Any] = {
            "available": True,
            "running": self.is_test_running,
            "test_item": self.current_test_item,
        }
        if not self._export_data:
            return summary
        params = self._export_data.get("params") if isinstance(self._export_data, dict) else None
        if params:
            summary["params"] = params
        return summary

    # ------------------------------------------------------------------
    # UI 回填单一写入口（AIAssist_PageScopedControlPlan.md §4.2）
    #
    # apply_config_to_controls(cfg) 是回填测试配置控件的唯一入口，
    # AI 回填与未来轮询/手动刷新共用，杜绝两套逻辑漂移。键名与
    # get_test_config() 输出对齐。
    # ------------------------------------------------------------------

    def apply_config_to_controls(self, cfg: dict, silent: bool = False) -> tuple[bool, str]:
        """silent=True 时跳过 AI 高亮与日志（供 ConfigMemory 恢复上次配置用）。"""
        if not isinstance(cfg, dict):
            return False, "配置草案格式无效（期望 dict）。"

        # 线程边界（§4.2-2）：AI 决策在 QThread，回填须经主线程执行；
        # dispatcher 经 QTimer.singleShot(0) 已切回主线程，此处加防御性守卫，
        # 杜绝 worker 线程直接 setValue 违反「UI 禁阻塞 / 跨线程改控件」铁律。
        if threading.current_thread() is not threading.main_thread():
            logger.error(
                "apply_config_to_controls 在非主线程被调用，拒绝回填以防违反线程边界"
            )
            return False, "配置回填未在主线程执行，已拒绝。"

        applied: list[str] = []
        touched: list = []

        def _set_spin(spin, key):
            val = cfg.get(key)
            if val is None:
                return
            try:
                spin.setValue(float(val))
            except (TypeError, ValueError):
                return
            applied.append(key)
            touched.append(spin)

        def _set_int_spin(spin, key):
            val = cfg.get(key)
            if val is None:
                return
            try:
                spin.setValue(int(float(val)))
            except (TypeError, ValueError):
                return
            applied.append(key)
            touched.append(spin)

        def _set_text(edit, key):
            val = cfg.get(key)
            if val is None:
                return
            edit.setText(str(val))
            applied.append(key)
            touched.append(edit)

        def _set_combo_data(combo, key):
            val = cfg.get(key)
            if val is None:
                return
            idx = combo.findData(val)
            if idx >= 0:
                combo.setCurrentIndex(idx)
                applied.append(key)
                touched.append(combo)

        # 测试项（按 data 匹配，触发 _on_test_item_changed → _set_test_item）
        test_item = cfg.get("test_item")
        if test_item is not None:
            idx = self.test_item_combo.findData(test_item)
            if idx >= 0:
                self.test_item_combo.setCurrentIndex(idx)
                applied.append("test_item")
                touched.append(self.test_item_combo)

        # 数据采集模式
        mode = cfg.get("data_acquisition_mode")
        if mode is not None:
            is_iic = str(mode).upper().startswith("IIC")
            self.iic_radio.setChecked(is_iic)
            self.uart_radio.setChecked(not is_iic)
            self._update_data_acquisition_ui()
            applied.append("data_acquisition_mode")
            touched.extend([self.iic_radio, self.uart_radio])

        # I2C 地址
        _set_text(self.iic_device_address, "iic_device_address")
        _set_text(self.iic_data_address, "iic_data_address")
        _set_combo_data(self.iic_width_combo, "iic_width")
        _set_combo_data(self.iic_speed_combo, "iic_speed")

        # UART 配置
        _set_text(self.uart_keyword, "uart_keyword")

        # 电压扫描参数
        _set_combo_data(self.voltage_channel, "voltage_channel")
        _set_spin(self.voltage_min, "voltage_min")
        _set_spin(self.voltage_max, "voltage_max")
        _set_spin(self.voltage_step, "voltage_step")
        _set_text(self.linearity_n_reg_addr, "linearity_n_reg_addr")
        _set_text(self.linearity_p_reg_addr, "linearity_p_reg_addr")
        link_np = cfg.get("linearity_link_np")
        if link_np is not None:
            self.linearity_link_np.setChecked(bool(link_np))
            applied.append("linearity_link_np")
            touched.append(self.linearity_link_np)
        auto_best = cfg.get("linearity_auto_best")
        if auto_best is not None:
            self.linearity_auto_best.setChecked(bool(auto_best))
            applied.append("linearity_auto_best")
            touched.append(self.linearity_auto_best)
        auto_strategy = cfg.get("linearity_auto_strategy", "coarse_fine")
        strategy_idx = self.linearity_auto_strategy.findData(auto_strategy)
        if strategy_idx < 0:
            strategy_idx = self.linearity_auto_strategy.findData("coarse_fine")
        self.linearity_auto_strategy.setCurrentIndex(strategy_idx)
        if "linearity_auto_strategy" in cfg:
            applied.append("linearity_auto_strategy")
            touched.append(self.linearity_auto_strategy)
        _set_int_spin(self.linearity_auto_repeat, "linearity_auto_repeat")
        self._sync_linearity_auto_controls()
        _set_text(self.linearity_start, "linearity_start")
        _set_text(self.linearity_end, "linearity_end")
        _set_text(self.linearity_value_start, "linearity_value_start")
        _set_text(self.linearity_value_end, "linearity_value_end")
        _set_text(self.linearity_value_step, "linearity_value_step")
        _set_text(self.linearity_n_start, "linearity_n_start")
        _set_text(self.linearity_n_end, "linearity_n_end")
        _set_text(self.linearity_n_value_start, "linearity_n_value_start")
        _set_text(self.linearity_n_value_end, "linearity_n_value_end")
        _set_text(self.linearity_n_value_step, "linearity_n_value_step")
        _set_text(self.linearity_p_start, "linearity_p_start")
        _set_text(self.linearity_p_end, "linearity_p_end")
        _set_text(self.linearity_p_value_start, "linearity_p_value_start")
        _set_text(self.linearity_p_value_end, "linearity_p_value_end")
        _set_text(self.linearity_p_value_step, "linearity_p_value_step")
        self._on_linearity_link_toggled(self.linearity_link_np.isChecked())

        # 温度扫描参数
        _set_spin(self.temp_min, "temp_min")
        _set_spin(self.temp_max, "temp_max")
        _set_spin(self.temp_step, "temp_step")
        _set_int_spin(self.soak_time, "soak_time")

        # 采样次数
        _set_int_spin(self.sample_count, "sample_count")

        # 校准点（留空 = 自动选取）
        _set_text(self.calib_low, "calib_low")
        _set_text(self.calib_high, "calib_high")

        # FT Calibration Check 两点四值与判定阈值
        _set_text(self.ft_calib_v1, "ft_calib_v1")
        _set_text(self.ft_calib_c1, "ft_calib_c1")
        _set_text(self.ft_calib_v2, "ft_calib_v2")
        _set_text(self.ft_calib_c2, "ft_calib_c2")
        _set_spin(self.ft_raw_tol, "ft_raw_tol")
        _set_spin(self.ft_err_limit, "ft_err_limit")
        _set_spin(self.ft_divider_ratio, "ft_divider_ratio")

        # 采样算法（id + params，按注册表回填）
        algo_cfg = cfg.get("algorithm")
        if isinstance(algo_cfg, dict):
            algo_id = algo_cfg.get("id") or ""
            idx = self.algorithm_combo.findData(algo_id)
            if idx >= 0:
                self.algorithm_combo.setCurrentIndex(idx)
                self._rebuild_algorithm_params()
                for key, spin in self._algo_param_widgets.items():
                    val = (algo_cfg.get("params") or {}).get(key)
                    if val is None:
                        continue
                    try:
                        spin.setValue(float(val))
                    except (TypeError, ValueError):
                        continue
                applied.append("algorithm")
                touched.append(self.algorithm_combo)

        # 离群样本筛选（enabled + 正/负向最大偏移）
        filter_cfg = cfg.get("outlier_filter")
        if isinstance(filter_cfg, dict):
            enabled = filter_cfg.get("enabled")
            if enabled is not None:
                self.outlier_filter_switch.setChecked(bool(enabled))
                applied.append("outlier_filter")
                touched.append(self.outlier_filter_switch)
            for spin, key in ((self.outlier_pos_offset, 'pos_offset'),
                              (self.outlier_neg_offset, 'neg_offset')):
                val = filter_cfg.get(key)
                if val is None:
                    continue
                try:
                    spin.setValue(float(val))
                except (TypeError, ValueError):
                    continue
                if "outlier_filter" not in applied:
                    applied.append("outlier_filter")
                touched.append(spin)

        # 指标卡计算配置（无控件，仅存 _metrics_options；全部可选）
        metrics_cfg = cfg.get("metrics_options")
        if isinstance(metrics_cfg, dict):
            for key in ('n_bits', 'v_spec_range', 'k_ideal', 'b_ideal', 'ref_mode'):
                if key not in metrics_cfg:
                    continue
                val = metrics_cfg[key]
                if key == 'ref_mode':
                    val = str(val).lower()
                    if val not in ('none', 'spec', 'batch_nominal'):
                        continue
                elif val is not None:
                    try:
                        val = int(val) if key == 'n_bits' else float(val)
                    except (TypeError, ValueError):
                        continue
                    if key == 'n_bits' and not 1 <= val <= 32:
                        continue
                self._metrics_options[key] = val
            applied.append("metrics_options")

        # High-Low Temp Test 电流监控（启用状态 + N6705C 通道）
        monitor_cfg = cfg.get("current_monitor")
        if isinstance(monitor_cfg, dict):
            channel = monitor_cfg.get("channel")
            if channel is not None:
                idx = self.current_monitor_channel.findData(channel)
                if idx >= 0:
                    self.current_monitor_channel.setCurrentIndex(idx)
                    if "current_monitor" not in applied:
                        applied.append("current_monitor")
                    touched.append(self.current_monitor_channel)
            enabled = monitor_cfg.get("enabled")
            if enabled is not None:
                self.current_monitor_switch.setChecked(bool(enabled))
                if "current_monitor" not in applied:
                    applied.append("current_monitor")
                touched.append(self.current_monitor_switch)
            self._refresh_instruments_visibility()

        # 多通道高低温测试：通道列表与前置配置
        channels = cfg.get("multi_channels")
        if channels is not None:
            self.multi_ch_panel.set_channels(channels)
            applied.append("multi_channels")
            touched.append(self.multi_ch_panel)
        pre_config = cfg.get("pre_config")
        if pre_config is not None:
            self.multi_ch_panel.set_pre_config(pre_config)
            applied.append("pre_config")
            touched.append(self.multi_ch_panel)

        if not applied:
            return False, "配置草案未包含任何可识别的配置项。"
        if not silent:
            # §4.2-3 可视化反馈：被 AI 修改的控件临时高亮（Phase 3）。
            self._highlight_widgets(touched)
            self.append_log(f"[AI] 已应用配置：{', '.join(applied)}")
        return True, f"已应用配置项：{', '.join(applied)}。"

    def _highlight_widgets(self, widgets: list) -> None:
        """被 AI 修改的控件临时高亮边框（§4.2-3 / Phase 3）。"""
        if not widgets:
            return
        for widget in widgets:
            if widget is None:
                continue
            widget.setStyleSheet(_AI_HIGHLIGHT_QSS)
            widget.setProperty("aiHighlighted", True)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

            def _clear(_w=widget):
                try:
                    _w.setStyleSheet("")
                    _w.setProperty("aiHighlighted", False)
                    _w.style().unpolish(_w)
                    _w.style().polish(_w)
                except RuntimeError:  # noqa: BLE001 - widget 可能已销毁
                    pass
            QTimer.singleShot(_AI_HIGHLIGHT_MS, _clear)

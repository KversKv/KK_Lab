#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consumption Test AI 契约与配置记忆（Mixin）。

从 consumption_test.py 平移而来，行为零变更：
  - UI Action 注册：_register_ai_ui_actions / _stop_running_test
  - 页面契约：ai_capabilities / ai_get_config / ai_apply_config /
    ai_start_test / ai_stop_test / ai_get_result_summary
  - ConfigMemory 恢复入口：apply_config_to_controls

依赖宿主类（ConsumptionTestUI）与其它 Mixin 提供属性与槽。
"""

import os
import threading
from log_config import get_logger
from core.ai.ui_action_registry import UIActionSpec
from core.ai.page_contract import (
    CAP_GET_CONFIG,
    CAP_APPLY_CONFIG,
    CAP_START_TEST,
    CAP_STOP_TEST,
    CAP_GET_RESULT,
)

logger = get_logger(__name__)


class ConsumptionTestViewAiMixin:

    def _register_ai_ui_actions(self):
        """§5b.5：登记本页按钮为 AI 可触发的具名 UI 动作（白名单制）。

        handler 直接复用按钮原 clicked.connect 的槽（_on_chip_check /
        _on_auto_test 等），行为与人点按钮完全一致；enabled_when 校验最小前置条件，
        不满足时 list_ui_actions 不返回、ui_invoke 明示不可用（不盲点）。
        """
        registry = self._ui_action_registry
        if registry is None:
            return

        def _has_n6705c() -> bool:
            return self.is_connected_a or self.is_connected_b

        def _has_mcu() -> bool:
            return bool(self.is_mcu_connected and self.mcu_io is not None)

        def _has_firmware() -> bool:
            return bool(getattr(self, "firmware_paths", []) or self.firmware_path)

        def _has_serial_port() -> bool:
            return bool(self.get_selected_serial_port())

        def _has_enabled_channel() -> bool:
            return any(cfg.get("enabled") for cfg in self._channel_configs)

        def _has_chip() -> bool:
            return self.selected_chip_config is not None

        def _is_testing() -> bool:
            return bool(self.is_testing)

        def _wrap(label, fn, pre_msg=None):
            def _run() -> tuple[bool, str]:
                try:
                    if pre_msg is not None:
                        self.append_log(f"[AI] 触发 {label}")
                    fn()
                    return True, f"{label} 已触发。"
                except Exception as exc:  # noqa: BLE001
                    logger.error("%s 执行失败", label, exc_info=True)
                    return False, f"{label} 执行失败：{exc}"
            return _run

        registry.register_many([
            UIActionSpec(
                id="consumption_test.chip_check",
                label="Chip Check (I2C)",
                page_key="consumption_test",
                handler=_wrap("Chip Check", self._on_chip_check, pre_msg=True),
                risk="medium",
                confirm=True,
                enabled_when=lambda: not _is_testing(),
                description=(
                    "经 I2C 探测 DUT 芯片型号并自动匹配 chip_combo。"
                    "需 MCU/I2C 接口可用（CH9114F/YD-RP2040 已连接或 I2C 接口已初始化）。"
                ),
            ),
            UIActionSpec(
                id="consumption_test.chip_save",
                label="Save Chip Rails",
                page_key="consumption_test",
                handler=_wrap("Save Chip Rails", self._on_chip_save, pre_msg=True),
                risk="low",
                confirm=True,
                enabled_when=_has_chip,
                description=(
                    "把当前 5 个电源轨 (Vcore/VcoreM/VcoreL/VANA/VHPPA) 的 YAML 配置"
                    "写入 chips/bes_chip_configs/main_chip_configs/<chip>.yaml。"
                    "需先在 Chip 下拉中选择芯片。"
                ),
            ),
            UIActionSpec(
                id="consumption_test.start_test",
                label="Start Consumption Test",
                page_key="consumption_test",
                handler=_wrap("Start Consumption Test", self._on_start_test, pre_msg=True),
                risk="high",
                confirm=True,
                enabled_when=lambda: (
                    _has_n6705c() and _has_enabled_channel() and not _is_testing()
                ),
                description=(
                    "启动 Force-High 功耗测试：对启用的非 Vbat 通道拉高电压，"
                    "在 test_time 时间内采样电流并统计 Vbat_remain。"
                    "需至少一台 N6705C 已连接、Vbat 通道已配置、且至少一个通道启用。"
                ),
            ),
            UIActionSpec(
                id="consumption_test.auto_test",
                label="Start Auto Test",
                page_key="consumption_test",
                handler=_wrap("Start Auto Test", self._on_auto_test, pre_msg=True),
                risk="high",
                confirm=True,
                enabled_when=lambda: (
                    _has_n6705c() and _has_firmware() and _has_serial_port()
                    and _has_enabled_channel() and not _is_testing()
                ),
                description=(
                    "启动 Auto Test 全流程：固件下载 → POWERON → RESET → I2C 配置 → 功耗测试。"
                    "需 N6705C 已连接、固件已选、DUT 串口已选、通道已配置；"
                    "MCU 控制方式下另需 MCU 已连接。"
                ),
            ),
            UIActionSpec(
                id="consumption_test.stop_test",
                label="Stop Running Test",
                page_key="consumption_test",
                handler=_wrap("Stop Running Test", self._stop_running_test, pre_msg=True),
                risk="medium",
                confirm=True,
                enabled_when=_is_testing,
                description=(
                    "停止当前正在运行的功耗测试或 Auto Test。"
                    "包括 _test_worker（force-high/force-auto）与 _auto_test_worker。"
                ),
            ),
        ])

    def _stop_running_test(self):
        """AI 触发 stop_test 的统一入口：自动判别 force-high / auto_test 两类 worker。"""
        if getattr(self, "_auto_test_worker", None) is not None or \
                getattr(self, "_controller", None) and self._controller.is_auto_test_running():
            self._stop_auto_test()
            return
        if self._test_worker is not None:
            self._stop_test()
            return
        # 兜底：直接复位状态
        self._stop_test()

    # ------------------------------------------------------------------
    # AIControllablePage 契约实现（AIAssist_PageScopedControlPlan.md §2 / Phase 5）
    #
    # Consumption Test 接入 AI 受控契约，薄封装既有方法：
    #   - ai_get_config 复用 get_test_config()
    #   - ai_apply_config 经 apply_config_to_controls() 单一写入口回填控件
    #   - ai_start_test 复用 _on_auto_test()（最完整流程：下载 + POWERON + 测试）
    #       若未配置固件/串口，则回退到 _on_start_test()（仅功耗测试）
    #   - ai_stop_test 复用 _stop_running_test()（统一判别 worker 类型）
    # 枢纽（MainWindow.resolve_active_ai_page）经 Tab 子页下钻拿到本实例，
    # 鸭子调用契约方法，无需 core / handler 改动。
    # ------------------------------------------------------------------
    def ai_capabilities(self) -> set[str]:
        return {
            CAP_GET_CONFIG,
            CAP_APPLY_CONFIG,
            CAP_START_TEST,
            CAP_STOP_TEST,
            CAP_GET_RESULT,
        }

    def ai_get_config(self) -> dict | None:
        try:
            return self.get_test_config()
        except Exception:  # noqa: BLE001 - 快照失败降级为 None
            logger.error("AI 读取 Consumption Test 配置失败", exc_info=True)
            return None

    def ai_apply_config(self, payload) -> tuple[bool, str]:
        """落地配置草案到控件（写操作，经确认+审计后由枢纽调用）。

        运行中拒绝改配置（§6.3），避免与正在执行的测试/下载冲突。
        """
        if self.is_testing:
            return False, "测试运行中，无法修改配置，请先停止测试。"
        if self._controller is not None and (
            self._controller.is_download_running() or self._controller.is_auto_test_running()
        ):
            return False, "下载或 Auto Test 运行中，无法修改配置。"
        return self.apply_config_to_controls(payload if isinstance(payload, dict) else {})

    def ai_start_test(self) -> tuple[bool, str]:
        """启动本页测试：优先 Auto Test，前置条件不足时回退到 Force-High 测试。"""
        if not (self.is_connected_a or self.is_connected_b):
            return False, "未连接 N6705C 仪器，请先连接再启动测试。"
        if self.is_testing:
            return False, "测试已在运行中。"
        if not any(cfg.get("enabled") for cfg in self._channel_configs):
            return False, "未启用任何通道，请先在 Channel Config 中启用至少一个通道。"

        has_firmware = bool(getattr(self, "firmware_paths", []) or self.firmware_path)
        has_serial = bool(self.get_selected_serial_port())
        cfg = self.get_test_config()

        if has_firmware and has_serial:
            mode_desc = "Std V (配置模式)" if cfg.get("test_mode") == "standard" else "High V (外供高压)"
            self.append_log(
                f"[AI] 请求启动 Auto Test：模式={mode_desc}，"
                f"Vbat 通道={cfg.get('poweron_channel', '')}，"
                f"test_time={cfg.get('test_time_s')}s。"
            )
            try:
                self._on_auto_test()
            except Exception:  # noqa: BLE001 - 启动异常转可读结果
                logger.error("AI 启动 Auto Test 失败", exc_info=True)
                return False, "启动 Auto Test 异常，请查看日志。"
            if self.is_testing:
                return True, "已请求启动 Auto Test。"
            return False, "Auto Test 启动未成功，请查看执行日志。"

        # 无固件或无串口 → 回退到仅功耗测试
        self.append_log(
            f"[AI] 固件或串口未配置，回退到 Force-High 功耗测试："
            f"test_time={cfg.get('test_time_s')}s。"
        )
        try:
            self._on_start_test()
        except Exception:  # noqa: BLE001
            logger.error("AI 启动 Force-High 测试失败", exc_info=True)
            return False, "启动测试异常，请查看日志。"
        if self.is_testing:
            return True, "已请求启动 Force-High 功耗测试。"
        return False, "启动未成功，请查看执行日志。"

    def ai_stop_test(self) -> tuple[bool, str]:
        if not self.is_testing:
            return False, "当前未在运行测试。"
        self.append_log("[AI] 请求停止测试。")
        try:
            self._stop_running_test()
        except Exception:  # noqa: BLE001
            logger.error("AI 停止测试失败", exc_info=True)
            return False, "停止测试异常，请查看日志。"
        return True, "已发送停止请求。"

    def ai_get_result_summary(self) -> dict | None:
        """读最近一次测试结果摘要（禁止臆造，直接回读结构化数据）。"""
        cfg = self.get_test_config()
        summary: dict = {
            "available": True,
            "running": bool(self.is_testing),
            "test_mode": cfg.get("test_mode"),
            "enabled_channels": [
                {"name": c["name"], "channel": c["channel"]}
                for c in cfg.get("channel_configs", []) if c["enabled"]
            ],
            "bin_count": len(self._bin_results_data),
            "expected_total_bins": self._current_total_bins,
        }
        if not self._bin_results_data:
            return summary
        # 汇总首末 BIN 的 Vbat / Vbat_remain（单位 A，由 AI 端按需换算）
        first = self._bin_results_data[0]
        last = self._bin_results_data[-1]
        summary["first_bin"] = {
            "bin_name": first.get("bin_name"),
            "vbat_current_A": first.get("vbat"),
            "vbat_remain_A": first.get("vbat_remain"),
        }
        summary["last_bin"] = {
            "bin_name": last.get("bin_name"),
            "vbat_current_A": last.get("vbat"),
            "vbat_remain_A": last.get("vbat_remain"),
        }
        return summary

    # ------------------------------------------------------------------
    # UI 回填单一写入口（AIAssist_PageScopedControlPlan.md §4.2）
    #
    # apply_config_to_controls(cfg) 是回填测试配置控件的唯一入口，
    # AI 回填与未来轮询/手动刷新共用，杜绝两套逻辑漂移。键名与
    # get_test_config() 输出对齐。
    # ------------------------------------------------------------------
    def apply_config_to_controls(self, cfg: dict, silent: bool = False) -> tuple[bool, str]:
        """silent=True 供 ConfigMemory 恢复上次配置：依赖联动的控件让信号正常
        触发（芯片联动加载 rail YAML、测试模式/控制方式/MCU 类型纯 UI 刷新，
        均已确认不写仪器、不弹模态对话框）；silent=False（AI 路径）行为不变。"""
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

        def _set_line_edit(edit, key, cast_fn=None):
            val = cfg.get(key)
            if val is None or edit is None:
                return
            try:
                text = str(cast_fn(val)) if cast_fn else str(val)
            except (TypeError, ValueError):
                return
            if edit.text() != text:
                edit.blockSignals(True)
                edit.setText(text)
                edit.blockSignals(False)
            applied.append(key)

        def _set_combo_text(combo, key):
            val = cfg.get(key)
            if val is None or combo is None:
                return
            idx = combo.findText(str(val))
            if idx >= 0 and combo.currentIndex() != idx:
                combo.blockSignals(True)
                combo.setCurrentIndex(idx)
                combo.blockSignals(False)
                applied.append(key)

        def _set_combo_data(combo, key, live=False):
            val = cfg.get(key)
            if val is None or combo is None:
                return
            for i in range(combo.count()):
                if combo.itemData(i) == val:
                    if combo.currentIndex() != i:
                        if not live:
                            combo.blockSignals(True)
                        combo.setCurrentIndex(i)
                        if not live:
                            combo.blockSignals(False)
                        applied.append(key)
                    return

        def _set_toggle(toggle, key, live=False):
            val = cfg.get(key)
            if val is None or toggle is None:
                return
            try:
                cur = toggle.value()
            except Exception:  # noqa: BLE001
                return
            if cur != val:
                if not live:
                    toggle.blockSignals(True)
                toggle.setValue(val)
                if not live:
                    toggle.blockSignals(False)
                applied.append(key)

        # 1. chip_name → chip_combo
        # silent（ConfigMemory 恢复）时不屏蔽信号，让 _on_chip_selected 联动
        # 加载 rail YAML 并同步 selected_chip_config（纯文件读 + 页面日志，
        # 无模态对话框）；AI 路径保持屏蔽，行为不变
        chip_combo = getattr(self, "chip_combo", None)
        chip_name = cfg.get("chip_name")
        if chip_name is not None and chip_combo is not None:
            chip_idx = chip_combo.findText(str(chip_name))
            if chip_idx >= 0 and chip_combo.currentIndex() != chip_idx:
                if not silent:
                    chip_combo.blockSignals(True)
                chip_combo.setCurrentIndex(chip_idx)
                if not silent:
                    chip_combo.blockSignals(False)
                applied.append("chip_name")

        # 2. 测试模式 / 控制方式 / 下载模式 / MCU 类型
        # silent 时 test_mode / control_method / mcu_type 让信号正常触发：
        # 其槽均为纯 UI 刷新（_test_mode 同步、通道选项重建、MCU 行显隐），
        # 是恢复后页面状态自洽的前提；download_mode 无槽，保持屏蔽
        _set_toggle(getattr(self, "test_mode_toggle", None), "test_mode", live=silent)
        _set_toggle(getattr(self, "control_method_toggle", None), "control_method", live=silent)
        _set_toggle(getattr(self, "download_mode_toggle", None), "download_mode")
        _set_combo_data(getattr(self, "mcu_type_combo", None), "mcu_type", live=silent)
        if silent:
            # 控制方式为 N6705C 时联动槽不会重建 PwrON/Reset 通道选项，
            # 统一重建一次（内部自带 blockSignals），保证第 4 步 findText 命中
            self._update_available_channels()

        # 3. 数值输入
        _set_line_edit(getattr(self, "test_time_input", None), "test_time_s", cast_fn=float)
        _set_line_edit(getattr(self, "stable_delay_input", None), "stable_delay_s", cast_fn=float)
        _set_line_edit(getattr(self, "download_baudrate_input", None), "download_baudrate", cast_fn=int)

        # 4. PowerON / RESET 通道与极性
        _set_combo_text(getattr(self, "poweron_channel_combo", None), "poweron_channel")
        _set_toggle(getattr(self, "poweron_polarity_toggle", None), "poweron_polarity")

        reset_enabled = cfg.get("reset_enabled")
        if reset_enabled is not None and getattr(self, "reset_enable_cb", None) is not None:
            if self.reset_enable_cb.isChecked() != bool(reset_enabled):
                self.reset_enable_cb.blockSignals(True)
                self.reset_enable_cb.setChecked(bool(reset_enabled))
                self.reset_enable_cb.blockSignals(False)
                # 手动触发联动（blockSignals 跳过了原槽）
                if hasattr(self, "_on_reset_enable_toggled"):
                    self._on_reset_enable_toggled(bool(reset_enabled))
                applied.append("reset_enabled")
        _set_combo_text(getattr(self, "reset_channel_combo", None), "reset_channel")
        _set_toggle(getattr(self, "reset_polarity_toggle", None), "reset_polarity")

        # 5. 通道配置（按 index 顺序回填，不增删通道，只改字段）
        chan_cfgs = cfg.get("channel_configs")
        if isinstance(chan_cfgs, list) and chan_cfgs:
            applied_chan: list[str] = []
            for idx, src in enumerate(chan_cfgs):
                if idx >= len(self._channel_configs) or idx >= len(self._channel_config_widgets):
                    break
                if not isinstance(src, dict):
                    continue
                dst = self._channel_configs[idx]
                wdata = self._channel_config_widgets[idx]

                name = src.get("name")
                if name is not None:
                    name_combo = wdata.get("name_input")
                    if name_combo is not None:
                        i = name_combo.findText(str(name))
                        if i >= 0 and name_combo.currentIndex() != i:
                            # silent 时让 _on_config_name_changed 触发（纯 UI 同步：
                            # 字典回写 + Vbat 简化布局 + 结果卡刷新）
                            if not silent:
                                name_combo.blockSignals(True)
                            name_combo.setCurrentIndex(i)
                            if not silent:
                                name_combo.blockSignals(False)
                channel = src.get("channel")
                if channel is not None:
                    ch_combo = wdata.get("channel_combo")
                    if ch_combo is not None:
                        i = ch_combo.findText(str(channel))
                        if i >= 0 and ch_combo.currentIndex() != i:
                            if not silent:
                                ch_combo.blockSignals(True)
                            ch_combo.setCurrentIndex(i)
                            if not silent:
                                ch_combo.blockSignals(False)
                enabled = src.get("enabled")
                if enabled is not None:
                    enable_cb = wdata.get("enable_cb")
                    if enable_cb is not None and enable_cb.isChecked() != bool(enabled):
                        # silent 时让 _on_config_enable_changed 触发（纯 UI 同步：
                        # 卡片禁用态 + 结果卡刷新）
                        if not silent:
                            enable_cb.blockSignals(True)
                        enable_cb.setChecked(bool(enabled))
                        if not silent:
                            enable_cb.blockSignals(False)
                # 同步 dst dict（与 _on_config_*_changed 槽保持一致的字段集）
                if name is not None:
                    dst["name"] = str(name)
                if channel is not None:
                    dst["channel"] = str(channel)
                if enabled is not None:
                    dst["enabled"] = bool(enabled)
                if "force_mode" in src:
                    dst["force_mode"] = str(src["force_mode"])
                if "force_value" in src:
                    dst["force_value"] = str(src.get("force_value", ""))
                if "boost_mode" in src:
                    dst["boost_mode"] = str(src["boost_mode"])
                if "boost_value" in src:
                    dst["boost_value"] = str(src.get("boost_value", ""))
                # 回填 force/boost 输入控件文本
                fv_input = wdata.get("force_value_input")
                if fv_input is not None and "force_value" in src:
                    fv_input.blockSignals(True)
                    fv_input.setText(str(src.get("force_value", "")))
                    fv_input.blockSignals(False)
                bv_input = wdata.get("boost_value_input")
                if bv_input is not None and "boost_value" in src:
                    bv_input.blockSignals(True)
                    bv_input.setText(str(src.get("boost_value", "")))
                    bv_input.blockSignals(False)
                applied_chan.append(f"#{idx}")
            if applied_chan:
                applied.append(f"channel_configs[{','.join(applied_chan)}]")

        # 6. 固件路径列表（仅回填到 firmware_paths，不自动选文件）
        fw_paths = cfg.get("firmware_paths")
        if isinstance(fw_paths, list) and fw_paths:
            self.firmware_paths = [str(p) for p in fw_paths if p]
            if self.firmware_paths:
                self.firmware_path = self.firmware_paths[0]
                if hasattr(self, "firmware_file_input") and self.firmware_file_input is not None:
                    names = "; ".join(os.path.basename(p) for p in self.firmware_paths)
                    self.firmware_file_input.setText(names)
                applied.append("firmware_paths")

        if not applied:
            return True, "配置草案无可应用字段，控件保持原状。"
        return True, f"已应用配置草案，受影响字段：{', '.join(applied)}。"

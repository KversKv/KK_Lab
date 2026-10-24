#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consumption Test Chip YAML 配置（Mixin）。

从 consumption_test.py 平移而来，行为零变更：
  - Chip 选择/加载：_on_chip_selected / _clear_rail_config_edits /
    _clear_pre_config_areas / _load_rail_configs_from_chip /
    _load_pre_config_areas_from_parsed
  - 配置文本读取：_get_rail_config_text / _get_pre_config_text /
    _get_pre_config_enabled / _on_pre_config_toggled /
    _get_combined_rail_config_text / _build_config_text_for_standard_mode
  - Chip Check：_on_chip_check / _on_chip_check_finished /
    _on_chip_check_error / _on_chip_check_thread_cleaned
  - 保存/执行/回写 YAML：_on_chip_save / _execute_config_area /
    _update_chip_rail_yaml / _update_chip_config_file
  - 命令解析与寄存器写入：_compare_chip_info / _chip_values_equal /
    _parse_config_commands / _to_int_addr / _resolve_device / _run_config_commands

依赖宿主类（ConsumptionTestUI）与其它 Mixin 提供属性与槽。
"""

import os
try:
    import yaml
except ImportError:
    yaml = None
from resource_path import get_resource_base
from PySide6.QtCore import (
    Qt,
    QThread,
)
from chips.bes_chip_configs.bes_chip_configs import get_chip_config
from log_config import get_logger
from core.consumption_test.workers import _ChipCheckWorker

_MAIN_CHIP_CONFIGS_DIR = os.path.join(
    get_resource_base(),
    "chips", "bes_chip_configs", "main_chip_configs"
)

logger = get_logger(__name__)


class ConsumptionTestViewChipConfigMixin:

    def _on_chip_selected(self, index):
        if index <= 0:
            self.selected_chip_config = None
            self._clear_rail_config_edits()
            return
        chip_name = self.chip_combo.currentText()
        cfg = get_chip_config(chip_name)
        self.selected_chip_config = cfg
        if cfg:
            logger.info("Chip selected: %s", chip_name)
            self.append_log(f"[SYSTEM] Chip selected: {chip_name}")
        else:
            logger.warning("No config found for chip: %s", chip_name)
            self.append_log(f"[WARNING] No config found for chip: {chip_name}")
        self._load_rail_configs_from_chip(chip_name)

    def _clear_rail_config_edits(self):
        """清空所有电源 YAML 文本框, 并复位测试前配置区域(开关 ON + 空文本)。"""
        edits = getattr(self, "_rail_config_edits", {}) or {}
        for rail, edit in edits.items():
            edit.clear()
        self._clear_pre_config_areas()

    def _clear_pre_config_areas(self):
        """清空 2 个测试前配置区域文本框, 开关复位为 ON。"""
        for area_key, edit in (getattr(self, "_pre_config_edits", {}) or {}).items():
            edit.clear()
        for area_key, toggle in (getattr(self, "_pre_config_toggles", {}) or {}).items():
            toggle.setChecked(True)

    def _load_rail_configs_from_chip(self, chip_name):
        """根据所选芯片, 从 main_chip_configs/<chip>.yaml 加载 5 个电源轨配置。

        YAML 文件顶层 key 与 _RAIL_NAMES(Vcore/VcoreM/VcoreL/VANA/VHPPA)
        大小写不敏感匹配; 每个 key 的值应为命令字符串列表, 会用换行拼接后
        填入对应的电源 YAML 文本框。
        另加载 2 个测试前配置区域 key(vbat_pre_test / power_pre_distribution),
        值为 {enabled: bool, commands: [...]}, 同时回填开关与文本框。
        """
        edits = getattr(self, "_rail_config_edits", {}) or {}
        if not edits:
            return
        # 先清空(含测试前配置区域, 开关复位 ON)
        for edit in edits.values():
            edit.clear()
        self._clear_pre_config_areas()

        if not chip_name:
            return

        yaml_path = os.path.join(_MAIN_CHIP_CONFIGS_DIR, f"{chip_name}.yaml")
        if not os.path.isfile(yaml_path):
            self.append_log(f"[CONFIG] No saved YAML for {chip_name} (file not found: {chip_name}.yaml).")
            return

        if yaml is None:
            self.append_log("[WARNING] PyYAML not installed; cannot parse chip rail configs.")
            return

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                parsed = yaml.safe_load(f.read()) or {}
        except Exception as e:
            logger.warning("Failed to parse chip YAML %s: %s", yaml_path, e)
            self.append_log(f"[WARNING] Failed to parse chip YAML for {chip_name}: {e}")
            return

        if not isinstance(parsed, dict):
            self.append_log(f"[CONFIG] {chip_name}.yaml has no top-level dict, rail edits left empty.")
            return

        # 构造大小写不敏感的 key → rail 映射
        lower_to_rail = {rail.lower(): rail for rail in self._RAIL_NAMES}
        loaded_rails = []
        for key, val in parsed.items():
            rail = lower_to_rail.get(str(key).strip().lower())
            if rail is None:
                continue
            if isinstance(val, list):
                text = "\n".join(str(line) for line in val)
            elif isinstance(val, str):
                text = val
            else:
                text = str(val)
            edits[rail].setPlainText(text)
            loaded_rails.append(rail)

        total = len(self._RAIL_NAMES)
        loaded_count = len(loaded_rails)
        if loaded_count > 0:
            self.append_log(
                f"[CONFIG] Auto-loaded {loaded_count}/{total} rail configs from {chip_name}.yaml: "
                f"{', '.join(loaded_rails)}"
            )
        else:
            # 没有匹配到任何 rail key, 列出 yaml 中的实际 key 供用户判断
            available_keys = list(parsed.keys())
            keys_str = ", ".join(str(k) for k in available_keys) if available_keys else "(empty)"
            self.append_log(
                f"[CONFIG] {chip_name}.yaml exists but has no rail-name keys "
                f"(expected: {', '.join(self._RAIL_NAMES)}; found: {keys_str}). "
                f"Rail edits left empty."
            )

        # 加载 2 个测试前配置区域(vbat_pre_test / power_pre_distribution)
        loaded_areas = self._load_pre_config_areas_from_parsed(parsed)
        if loaded_areas:
            self.append_log(
                f"[CONFIG] Auto-loaded pre-config areas from {chip_name}.yaml: "
                f"{', '.join(loaded_areas)}"
            )

    def _load_pre_config_areas_from_parsed(self, parsed):
        """从已解析的 chip YAML dict 回填 2 个测试前配置区域(开关 + 文本框)。

        支持的值格式:
          - {enabled: bool, commands: [str...]}  (Save 按钮写入的标准格式)
          - [str...] / "..."                      (裸命令列表, 开关默认 ON)
        返回本次实际命中的区域描述列表(用于日志), 未命中返回空列表。
        """
        loaded_areas = []
        pre_edits = getattr(self, "_pre_config_edits", {}) or {}
        pre_toggles = getattr(self, "_pre_config_toggles", {}) or {}
        for area_key, area_label in self._PRE_CONFIG_AREAS:
            edit = pre_edits.get(area_key)
            toggle = pre_toggles.get(area_key)
            if edit is None or toggle is None:
                continue
            if area_key not in parsed:
                continue
            val = parsed.get(area_key)
            enabled = True
            if isinstance(val, dict):
                enabled = bool(val.get("enabled", True))
                commands = val.get("commands")
                if isinstance(commands, list):
                    text = "\n".join(str(line) for line in commands)
                elif isinstance(commands, str):
                    text = commands
                else:
                    text = ""
            elif isinstance(val, list):
                text = "\n".join(str(line) for line in val)
            elif isinstance(val, str):
                text = val
            else:
                text = str(val)
            edit.setPlainText(text)
            toggle.setChecked(enabled)
            cmd_count = len([ln for ln in text.splitlines() if ln.strip()])
            loaded_areas.append(f"{area_label}({'on' if enabled else 'off'},{cmd_count})")
        return loaded_areas

    def _get_rail_config_text(self, rail_name):
        """获取指定电源轨的 YAML 配置文本。"""
        edits = getattr(self, "_rail_config_edits", {}) or {}
        edit = edits.get(rail_name)
        if edit is None:
            return ""
        return edit.toPlainText().strip()

    def _get_pre_config_text(self, area_key):
        """获取指定测试前配置区域的 YAML 配置文本。"""
        edit = (getattr(self, "_pre_config_edits", {}) or {}).get(area_key)
        if edit is None:
            return ""
        return edit.toPlainText().strip()

    def _get_pre_config_enabled(self, area_key):
        """获取指定测试前配置区域的开关状态(ON=参与配置)。"""
        toggle = (getattr(self, "_pre_config_toggles", {}) or {}).get(area_key)
        if toggle is None:
            return False
        return toggle.isChecked()

    def _on_pre_config_toggled(self, area_key, checked):
        """测试前配置区域开关切换: OFF 时禁用该区域文本框与 Exec 按钮。"""
        edit = (getattr(self, "_pre_config_edits", {}) or {}).get(area_key)
        exec_btn = (getattr(self, "_pre_config_exec_btns", {}) or {}).get(area_key)
        if edit is not None:
            edit.setEnabled(checked)
        if exec_btn is not None:
            exec_btn.setEnabled(checked)

    def _get_combined_rail_config_text(self):
        """合并所有非空电源轨配置(用换行分隔),用于 Exec 立即执行。"""
        parts = []
        for rail in self._RAIL_NAMES:
            text = self._get_rail_config_text(rail)
            if text:
                parts.append(text)
        return "\n".join(parts)

    def _build_config_text_for_standard_mode(self, enabled_configs):
        """标准电压模式: 根据启用的通道 Name 匹配电源配置, 合并成 config_text。

        仅包含与启用通道 Name 匹配的电源轨配置(Vcore 通道 → Vcore 配置)。
        匹配规则: 通道 Name 与电源轨名称大小写不敏感完全匹配。
        """
        matched_rails = set()
        for _i, cfg in enabled_configs:
            name = cfg.get("name", "").strip().lower()
            for rail in self._RAIL_NAMES:
                if rail.lower() == name:
                    matched_rails.add(rail)
                    break
        parts = []
        for rail in self._RAIL_NAMES:
            if rail in matched_rails:
                text = self._get_rail_config_text(rail)
                if text:
                    parts.append(text)
        return "\n".join(parts)

    def _on_chip_check(self):
        if self._chip_check_thread is not None and self._chip_check_thread.isRunning():
            self.append_log("[WARNING] Chip check already in progress.")
            return

        self.chip_check_btn.setEnabled(False)
        self.append_log("[SYSTEM] Starting chip check via I2C...")

        worker = _ChipCheckWorker()
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_chip_check_finished)
        worker.error.connect(self._on_chip_check_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(self._on_chip_check_thread_cleaned)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._chip_check_thread = thread
        self._chip_check_worker = worker
        thread.start()

    def _on_chip_check_finished(self, chip_info):
        self.chip_check_btn.setEnabled(True)

        self.append_log(
            f"[CHIP_CHECK] chip={chip_info.get('chip_name') or 'N/A'}"
            f"  main_die={chip_info.get('main_die') or 'N/A'}({chip_info.get('main_die_version') or '?'}, addr={chip_info.get('main_die_i2c_addr') or 'N/A'}, {chip_info.get('main_die_i2c_width') or 'N/A'}bit)"
            f"  main_die_pmu={chip_info.get('main_die_pmu') or 'N/A'}(addr={chip_info.get('main_die_pmu_i2c_addr') or 'N/A'}, {chip_info.get('main_die_pmu_i2c_width') or 'N/A'}bit)"
            f"  has_pmu={chip_info.get('has_pmu', False)}"
            f"  pmu={chip_info.get('pmu') or 'N/A'}({chip_info.get('pmu_version') or '?'}, addr={chip_info.get('pmu_i2c_addr') or 'N/A'}, {chip_info.get('pmu_i2c_width') or 'N/A'}bit)"
        )

        warning = chip_info.get("warning")
        if warning:
            self.append_log(f"[CHIP_CHECK] ⚠ {warning}")

        detected_name = chip_info.get("chip_name")
        if not detected_name:
            self.append_log("[WARNING] Chip check: no chip detected.")
            return

        exact_idx = self.chip_combo.findText(detected_name, Qt.MatchExactly)
        if exact_idx >= 0:
            self.chip_combo.setCurrentIndex(exact_idx)
            self.append_log(f"[CHIP_CHECK] Chip matched: {detected_name}")
            return

        prefix_match = detected_name.split("_")[0] if "_" in detected_name else detected_name
        for i in range(1, self.chip_combo.count()):
            item = self.chip_combo.itemText(i)
            if item == prefix_match or item.startswith(detected_name):
                self.chip_combo.setCurrentIndex(i)
                self.append_log(f"[CHIP_CHECK] Chip matched (prefix): {item}")
                return

        self.append_log(f"[WARNING] No matching chip found in list for: {detected_name}")

    def _on_chip_check_error(self, err_msg):
        self.chip_check_btn.setEnabled(True)
        logger.error("Chip check error: %s", err_msg)
        self.append_log(f"[ERROR] Chip check failed: {err_msg}")

    def _on_chip_check_thread_cleaned(self):
        self._chip_check_worker = None
        self._chip_check_thread = None

    def _on_chip_save(self):
        """把当前 5 个 YAML 文本框内容一次性写入 <chip>.yaml 文件。

        会保留文件中已有的非 rail-name 顶层 key(例如 voltage_low/voltage_default
        等模板配置),仅按 _RAIL_NAMES 逐轨覆盖/新增对应的 rail key。
        空 YAML 文本框也会写入空列表,等效于清空对应 rail key。
        另写入 2 个测试前配置区域 key(vbat_pre_test / power_pre_distribution),
        值为 {enabled, commands}, 开关状态一并持久化。
        """
        if self.chip_combo.currentIndex() <= 0:
            self.append_log("[WARNING] No chip selected. Please select a chip before saving.")
            return
        chip_name = self.chip_combo.currentText()

        if yaml is None:
            self.append_log("[WARNING] PyYAML not installed; cannot save rail configs.")
            return

        yaml_path = os.path.join(_MAIN_CHIP_CONFIGS_DIR, f"{chip_name}.yaml")

        # 读取已有内容(保留非 rail key)
        try:
            if os.path.isfile(yaml_path):
                with open(yaml_path, "r", encoding="utf-8") as f:
                    existing_text = f.read()
                parsed = yaml.safe_load(existing_text) or {}
                if not isinstance(parsed, dict):
                    parsed = {}
            else:
                parsed = {}
        except Exception as e:
            logger.warning("Failed to read existing YAML %s, will overwrite: %s", yaml_path, e)
            parsed = {}

        # 逐轨写入(空文本写入空列表)
        saved_rails = []
        for rail in self._RAIL_NAMES:
            text = self._get_rail_config_text(rail)
            config_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            parsed[rail] = config_lines
            if config_lines:
                saved_rails.append(f"{rail}({len(config_lines)})")

        # 测试前配置区域写入 {enabled, commands}
        saved_areas = []
        for area_key, area_label in self._PRE_CONFIG_AREAS:
            enabled = self._get_pre_config_enabled(area_key)
            text = self._get_pre_config_text(area_key)
            config_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            parsed[area_key] = {"enabled": enabled, "commands": config_lines}
            if config_lines:
                saved_areas.append(f"{area_label}({'on' if enabled else 'off'},{len(config_lines)})")

        try:
            os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    parsed, f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
            saved_summary = ", ".join(saved_rails) if saved_rails else "(all empty)"
            logger.info("All rail configs saved to %s", yaml_path)
            self.append_log(
                f"[CONFIG] Saved 5 rail configs to {chip_name}.yaml: {saved_summary}"
            )
            if saved_areas:
                self.append_log(
                    f"[CONFIG] Saved pre-config areas to {chip_name}.yaml: {', '.join(saved_areas)}"
                )
        except Exception as e:
            logger.error("Failed to write chip YAML %s: %s", yaml_path, e)
            self.append_log(f"[ERROR] Failed to save chip config: {e}")

    def _execute_config_area(self, area_key):
        """执行单个配置区域的 I2C 配置(电源轨或测试前配置区域, 跳过其它区域)。

        仅根据指定区域的 YAML 文本框内容解析命令并下发 I2C,
        不会触碰其它区域的配置,也不会修改 N6705C 通道设置。
        """
        valid_keys = set(self._RAIL_NAMES) | {k for k, _ in self._PRE_CONFIG_AREAS}
        if area_key not in valid_keys:
            logger.warning("Unknown config area name: %s", area_key)
            return

        chip_name = self.chip_combo.currentText()
        if self.chip_combo.currentIndex() <= 0 or self.selected_chip_config is None:
            logger.warning("No chip selected for %s execution", area_key)
            self.append_log(f"[WARNING] No chip selected. Please select a chip first for {area_key}.")
            return

        refreshed = get_chip_config(chip_name, force_reload=True)
        if refreshed:
            self.selected_chip_config = refreshed

        if area_key in self._RAIL_NAMES:
            config_text = self._get_rail_config_text(area_key)
        else:
            config_text = self._get_pre_config_text(area_key)
        if not config_text:
            self.append_log(f"[WARNING] {area_key} config is empty, nothing to execute.")
            return

        config_commands = self._parse_config_commands(config_text)
        if not config_commands:
            self.append_log(f"[WARNING] {area_key} config has no valid commands.")
            return

        self.append_log(
            f"[EXECUTE] Starting {area_key} configuration for chip: {chip_name} "
            f"({len(config_commands)} commands)"
        )

        try:
            from lib.i2c.i2c_interface_x64 import I2CInterface
            i2c = I2CInterface()
            if not i2c.initialize():
                self.append_log("[ERROR] I2C interface initialization failed.")
                return
            self.append_log("[EXECUTE] I2C interface initialized successfully.")
        except Exception as e:
            logger.error("I2C initialization error: %s", e)
            self.append_log(f"[ERROR] I2C initialization error: {e}")
            return

        try:
            chip_info = i2c.bes_chip_check()
            self.append_log(f"[EXECUTE] Chip detected: {chip_info.get('chip_name', 'N/A')}")
        except Exception as e:
            logger.error("bes_chip_check failed: %s", e)
            self.append_log(f"[ERROR] Chip check failed: {e}")
            return

        self._compare_chip_info(chip_info, self.selected_chip_config)
        self._run_config_commands(i2c, chip_info, config_commands)
        self.append_log(f"[EXECUTE] {area_key} configuration execution completed.")

    def _update_chip_rail_yaml(self, chip_name, rail_name, config_text):
        """将单轨配置写入 <chip>.yaml 文件中对应 rail 的 key 下。

        若文件不存在则创建; 若存在则只更新该 rail key, 其它 rail key 保留。
        """
        if rail_name not in self._RAIL_NAMES:
            return
        if yaml is None:
            self.append_log("[WARNING] PyYAML not installed; cannot save rail config.")
            return

        # 解析为命令行列表(过滤空行)
        config_lines = []
        for raw_line in config_text.strip().splitlines():
            line = raw_line.strip()
            if line:
                config_lines.append(line)

        yaml_path = os.path.join(_MAIN_CHIP_CONFIGS_DIR, f"{chip_name}.yaml")

        # 读取已有内容(若文件存在)
        try:
            if os.path.isfile(yaml_path):
                with open(yaml_path, "r", encoding="utf-8") as f:
                    existing_text = f.read()
                parsed = yaml.safe_load(existing_text) or {}
                if not isinstance(parsed, dict):
                    parsed = {}
            else:
                parsed = {}
        except Exception as e:
            logger.warning("Failed to read existing YAML %s, will overwrite: %s", yaml_path, e)
            parsed = {}

        # 仅更新该 rail 的 key
        parsed[rail_name] = config_lines

        try:
            os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    parsed, f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
            logger.info("Rail %s config saved to %s", rail_name, yaml_path)
            self.append_log(
                f"[SYSTEM] {rail_name} config saved to {chip_name}.yaml ({len(config_lines)} lines)"
            )
        except Exception as e:
            logger.error("Failed to write rail YAML %s: %s", yaml_path, e)
            self.append_log(f"[ERROR] Failed to save {rail_name} config: {e}")

    def _compare_chip_info(self, detected, config):
        compare_keys = [
            "chip_name", "main_die", "main_die_version",
            "main_die_i2c_width", "main_die_i2c_addr",
            "main_die_pmu", "main_die_pmu_version",
            "main_die_pmu_i2c_width", "main_die_pmu_i2c_addr",
            "has_pmu", "pmu", "pmu_version", "pmu_i2c_width", "pmu_i2c_addr",
        ]
        for key in compare_keys:
            det_val = detected.get(key)
            cfg_val = config.get(key)
            if cfg_val in (None, "", {}):
                continue
            if self._chip_values_equal(det_val, cfg_val):
                continue
            logger.warning(
                "Chip info mismatch [%s]: detected=%s, config=%s",
                key, det_val, cfg_val
            )
            self.append_log(
                f"[WARNING] Chip info mismatch [{key}]: detected={det_val}, config={cfg_val}"
            )

    @staticmethod
    def _chip_values_equal(a, b):
        if a == b:
            return True
        if a is None or b is None:
            return False
        str_a = str(a).strip().lower()
        str_b = str(b).strip().lower()
        if str_a == str_b:
            return True
        try:
            return int(str_a, 0) == int(str_b, 0)
        except (ValueError, TypeError):
            pass
        if isinstance(a, bool) or isinstance(b, bool):
            truthy = {"true", "1", "yes"}
            falsy = {"false", "0", "no", ""}
            a_bool = str_a in truthy
            b_bool = str_b in truthy
            a_is_bool = str_a in truthy or str_a in falsy
            b_is_bool = str_b in truthy or str_b in falsy
            if a_is_bool and b_is_bool:
                return a_bool == b_bool
        return False

    @staticmethod
    def _parse_config_commands(text):
        commands = []
        lines = text.strip().splitlines()
        for raw_line in lines:
            line = raw_line.strip()
            if line.startswith("-"):
                line = line[1:].strip()
            if line.startswith("'") or line.startswith('"'):
                line = line[1:]
            if line.endswith("'") or line.endswith('"'):
                line = line[:-1]
            line = line.strip()

            comment_idx = line.find("//")
            if comment_idx >= 0:
                line = line[:comment_idx].strip()

            if not line:
                continue

            upper = line.upper()
            if not any(kw in upper for kw in ("WRITE_BITS", "WRITE", "READ")):
                continue

            target = "NO_PREFIX"
            if ":" in line:
                prefix, rest = line.split(":", 1)
                prefix_upper = prefix.strip().upper()
                rest_upper = rest.strip().upper()
                has_command = any(kw in rest_upper for kw in ("WRITE_BITS", "WRITE", "READ"))
                if has_command:
                    if prefix_upper == "DUT":
                        target = "DUT"
                        line = rest.strip()
                    elif prefix_upper == "PMU":
                        target = "MAIN_DIE_PMU"
                        line = rest.strip()
                    elif prefix_upper == "MAIN_DIE_PMU":
                        target = "MAIN_DIE_PMU"
                        line = rest.strip()
                    elif prefix_upper.endswith("_PMU"):
                        target = "EXT_PMU"
                        line = rest.strip()
                    elif prefix_upper.endswith("_DUT") or prefix_upper.endswith("_MAIN"):
                        target = "DUT"
                        line = rest.strip()

            parts = line.split()
            if len(parts) < 2:
                continue

            op = parts[0].upper()
            if op == "WRITE_BITS" and len(parts) >= 5:
                reg_addr = int(parts[1], 0)
                msb = int(parts[2], 0)
                lsb = int(parts[3], 0)
                value = int(parts[4], 0)
                commands.append({
                    "op": "WRITE_BITS",
                    "target": target,
                    "reg_addr": reg_addr,
                    "msb": msb,
                    "lsb": lsb,
                    "value": value,
                })
            elif op == "WRITE" and len(parts) >= 3:
                reg_addr = int(parts[1], 0)
                value = int(parts[2], 0)
                commands.append({
                    "op": "WRITE",
                    "target": target,
                    "reg_addr": reg_addr,
                    "value": value,
                })
            elif op == "READ" and len(parts) >= 2:
                reg_addr = int(parts[1], 0)
                commands.append({
                    "op": "READ",
                    "target": target,
                    "reg_addr": reg_addr,
                })

        return commands

    @staticmethod
    def _to_int_addr(addr):
        if addr is None:
            return None
        if isinstance(addr, int):
            return addr
        if isinstance(addr, str):
            return int(addr, 0)
        return None

    def _resolve_device(self, chip_info, target):
        if target == "DUT":
            addr = self._to_int_addr(chip_info.get("main_die_i2c_addr"))
            width = chip_info.get("main_die_i2c_width")
            return addr, width
        if target == "EXT_PMU":
            addr = self._to_int_addr(chip_info.get("pmu_i2c_addr"))
            width = chip_info.get("pmu_i2c_width")
            return addr, width
        if target == "MAIN_DIE_PMU":
            addr = self._to_int_addr(chip_info.get("main_die_pmu_i2c_addr"))
            width = chip_info.get("main_die_pmu_i2c_width")
            return addr, width
        if chip_info.get("has_pmu") and chip_info.get("pmu_i2c_addr"):
            addr = self._to_int_addr(chip_info.get("pmu_i2c_addr"))
            width = chip_info.get("pmu_i2c_width")
        else:
            addr = self._to_int_addr(chip_info.get("main_die_pmu_i2c_addr"))
            width = chip_info.get("main_die_pmu_i2c_width")
        return addr, width

    def _run_config_commands(self, i2c, chip_info, commands):
        for idx, cmd in enumerate(commands):
            op = cmd["op"]
            target = cmd.get("target", "NO_PREFIX")
            reg_addr = cmd["reg_addr"]

            device_addr, width = self._resolve_device(chip_info, target)
            if device_addr is None or width is None:
                self.append_log(
                    f"[ERROR] Cannot resolve device address for target={target}, skipping command #{idx+1}"
                )
                continue

            try:
                if op == "WRITE_BITS":
                    msb = cmd["msb"]
                    lsb = cmd["lsb"]
                    value = cmd["value"]
                    current_val = i2c.read(device_addr, reg_addr, width)
                    bit_mask = ((1 << (msb - lsb + 1)) - 1) << lsb
                    new_val = (current_val & ~bit_mask) | ((value << lsb) & bit_mask)
                    i2c.write(device_addr, reg_addr, new_val, width)
                    self.append_log(
                        f"[EXECUTE] #{idx+1} WRITE_BITS dev=0x{device_addr:02X} "
                        f"reg=0x{reg_addr:08X} [{msb}:{lsb}]=0x{value:X} "
                        f"(0x{current_val:X} -> 0x{new_val:X})"
                    )

                elif op == "WRITE":
                    value = cmd["value"]
                    i2c.write(device_addr, reg_addr, value, width)
                    self.append_log(
                        f"[EXECUTE] #{idx+1} WRITE dev=0x{device_addr:02X} "
                        f"reg=0x{reg_addr:08X} data=0x{value:X}"
                    )

                elif op == "READ":
                    read_val = i2c.read(device_addr, reg_addr, width)
                    self.append_log(
                        f"[EXECUTE] #{idx+1} READ dev=0x{device_addr:02X} "
                        f"reg=0x{reg_addr:08X} => 0x{read_val:X}"
                    )

            except Exception as e:
                logger.error("Command #%d failed: %s", idx + 1, e)
                self.append_log(f"[ERROR] Command #{idx+1} failed: {e}")

    def _update_chip_config_file(self, chip_name, config_text):
        try:
            config_lines = []
            for raw_line in config_text.strip().splitlines():
                line = raw_line.strip()
                if line:
                    config_lines.append(line)

            chips_dir = os.path.join(
                get_resource_base(),
                "chips", "bes_chip_configs"
            )
            if chip_name.startswith("pmu_"):
                config_file = os.path.join(chips_dir, "pmu_chips", f"{chip_name}.py")
            else:
                config_file = os.path.join(chips_dir, "main_chips", f"{chip_name}.py")

            if not os.path.exists(config_file):
                logger.warning("Chip config file not found: %s", config_file)
                self.append_log(f"[WARNING] Chip config file not found: {config_file}")
                return

            with open(config_file, "r", encoding="utf-8") as f:
                content = f.read()

            import ast
            tree = ast.parse(content)
            chip_config_dict = None
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name) and t.id == "CHIP_CONFIG":
                            chip_config_dict = ast.literal_eval(content[node.value.col_offset:].split("\n}")[0] + "\n}")
                            break

            if chip_config_dict is None:
                chip_config_dict = {}

            chip_config_dict["power_distribution"] = {"user_config": config_lines}

            lines = ["CHIP_CONFIG = {\n"]
            for key, val in chip_config_dict.items():
                lines.append(f"    {key!r}: {val!r},\n")
            lines.append("}\n")

            with open(config_file, "w", encoding="utf-8") as f:
                f.writelines(lines)

            logger.info("Chip config updated: %s", config_file)
            self.append_log(f"[SYSTEM] Chip config updated: {chip_name}")

            refreshed = get_chip_config(chip_name, force_reload=True)
            if refreshed:
                self.selected_chip_config = refreshed
        except Exception as e:
            logger.error("Failed to update chip config: %s", e)
            self.append_log(f"[ERROR] Failed to update chip config: {e}")

"""ModuleConfigStore — 配置的收集 / 回填 / 文件读写（从 _base_subpage 拆出）。

职责：
- ``collect()``：从 ``DutConfigPanel`` + ``TestPlanPanel`` + ``_item_overrides``
  收集完整 cfg（键集合与旧 ``get_test_config`` 完全一致，schema 不变）；
- ``restore(cfg)``：把完整配置回填到控件（含勾选 / 参数覆写）；
- 配置文件读写（schema_version 包装）与命名弹窗（另存为）。

为什么这样拆：配置 IO 是"数据装配"而非"页面行为"，独立后子页基类只留
信号接线与 run flow；键集合变化只需改这一个文件。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from PySide6.QtWidgets import QInputDialog, QMessageBox

from log_config import get_logger
from ui.resource_path import get_user_data_dir

_logger = get_logger(__name__)

_CONFIG_SCHEMA_VERSION = 1


class ModuleConfigStore:
    """Module Test 配置存取助手（每子页一个实例）。"""

    def __init__(self, *, module_type: str, dut_panel, test_plan,
                 item_overrides: dict, items_registry, module_config_panel=None,
                 judge_criteria: dict | None = None):
        self._module_type = module_type
        self._dut = dut_panel
        self._plan = test_plan
        self._overrides = item_overrides  # 子页持有的 dict（共享引用）
        self._registry = items_registry
        self._modcfg = module_config_panel
        self._judge = judge_criteria  # 子页持有的 dict（共享引用，None=不持久化）

    # ------------------------------------------------------------------ 收集
    def collect(self) -> dict[str, Any]:
        """收集完整配置（键集合与旧 get_test_config 一致）。"""
        dut = self._dut
        temp_enabled = dut.temp_test_check.isChecked()
        return {
            "selected_items": self._plan.selected_keys(),
            "chip_name": dut.chip_name_edit.text().strip(),
            "module_name": dut.module_name_edit.text().strip(),
            "operator": dut.operator_edit.text().strip(),
            "temp_test_enabled": temp_enabled,
            "temperature": dut.temperature_edit.text().strip() if temp_enabled else "",
            "temp_soak_s": dut.temp_soak_spin.value(),
            "temp_tolerance_c": dut.temp_tolerance_spin.value(),
            "temp_wait_s": dut.temp_wait_spin.value(),
            "vin_channel": dut.vin_ch_combo.currentText(),
            "vout_channel": dut.vout_ch_combo.currentText(),
            "iload_channel": dut.iload_ch_combo.currentText(),
            "vout_nominal_mv": dut.vout_nominal_spin.value(),
            "device_addr": dut.device_addr_edit.text().strip(),
            "width_flag": dut.width_flag_combo.currentData(),
            # 示波器输出电压通道：控件为 "CH n"，存整数 n 供 core cfg 直接 int 用
            "scope_vout_channel": dut.scope_vout_ch_combo.currentIndex() + 1,
            "item_overrides": {k: dict(v) for k, v in self._overrides.items()},
            # Module Config（测试前模块 I2C 配置）随模块配置一并保存
            "module_config_enabled": (
                self._modcfg.is_enabled() if self._modcfg is not None else False),
            "module_config_yaml": (
                self._modcfg.config_text() if self._modcfg is not None else ""),
            # 判定标准（PASS/FAIL Criteria）随模块配置一并保存
            "judge_criteria": (
                {k: {"rules": [dict(r) for r in v.get("rules", ())]}
                 for k, v in self._judge.items() if isinstance(v, dict)}
                if self._judge is not None else {}),
        }

    # ------------------------------------------------------------------ 回填
    def restore(self, cfg: dict) -> None:
        """把一份完整配置回填到所有控件（含通道 / 温度 / 勾选 / 参数覆写）。"""
        dut = self._dut

        def _set_combo(combo, value):
            if value is None:
                return
            idx = combo.findText(str(value))
            if idx >= 0:
                combo.setCurrentIndex(idx)

        if "chip_name" in cfg:
            dut.chip_name_edit.setText(str(cfg["chip_name"]))
        if "module_name" in cfg:
            dut.module_name_edit.setText(str(cfg["module_name"]))
        if "operator" in cfg:
            dut.operator_edit.setText(str(cfg["operator"]))
        _set_combo(dut.vin_ch_combo, cfg.get("vin_channel"))
        _set_combo(dut.vout_ch_combo, cfg.get("vout_channel"))
        _set_combo(dut.iload_ch_combo, cfg.get("iload_channel"))
        if "scope_vout_channel" in cfg:
            _idx = int(cfg["scope_vout_channel"]) - 1
            if 0 <= _idx < dut.scope_vout_ch_combo.count():
                dut.scope_vout_ch_combo.setCurrentIndex(_idx)
        if "vout_nominal_mv" in cfg:
            dut.vout_nominal_spin.setValue(int(cfg["vout_nominal_mv"]))
        if "device_addr" in cfg:
            dut.device_addr_edit.setText(str(cfg["device_addr"]))
        if "width_flag" in cfg:
            idx = dut.width_flag_combo.findData(int(cfg["width_flag"]))
            if idx >= 0:
                dut.width_flag_combo.setCurrentIndex(idx)

        if "temp_test_enabled" in cfg:
            dut.temp_test_check.setChecked(bool(cfg["temp_test_enabled"]))
        if "temperature" in cfg:
            dut.temperature_edit.setText(str(cfg["temperature"]))
        if "temp_soak_s" in cfg:
            dut.temp_soak_spin.setValue(int(cfg["temp_soak_s"]))
        if "temp_tolerance_c" in cfg:
            dut.temp_tolerance_spin.setValue(int(cfg["temp_tolerance_c"]))
        if "temp_wait_s" in cfg:
            dut.temp_wait_spin.setValue(int(cfg["temp_wait_s"]))

        # 测试项勾选
        selected = cfg.get("selected_items")
        if isinstance(selected, list):
            self._plan.set_checked_keys(set(selected))

        # 参数覆写
        overrides = cfg.get("item_overrides")
        if isinstance(overrides, dict):
            self._overrides.clear()
            self._overrides.update(
                {k: dict(v) for k, v in overrides.items()
                 if k in self._registry and isinstance(v, dict)})
            for key in self._registry:
                self._plan.set_item_customized(key, key in self._overrides)

        # Module Config（测试前模块 I2C 配置）
        if self._modcfg is not None:
            if "module_config_enabled" in cfg:
                self._modcfg.set_enabled(bool(cfg["module_config_enabled"]))
            if "module_config_yaml" in cfg:
                self._modcfg.set_config_text(str(cfg["module_config_yaml"]))

        # 判定标准（PASS/FAIL Criteria）
        criteria = cfg.get("judge_criteria")
        if self._judge is not None and isinstance(criteria, dict):
            self._judge.clear()
            self._judge.update(
                {k: {"rules": [dict(r) for r in v.get("rules", ())
                               if isinstance(r, dict)]}
                 for k, v in criteria.items()
                 if k in self._registry and isinstance(v, dict)})

    # ------------------------------------------------------------------ 文件
    def configs_root(self) -> str:
        """配置文件根目录：user_data/module_test_configs/<module_type>。"""
        return get_user_data_dir("module_test_configs", self._module_type)

    @staticmethod
    def safe_name(text: str, fallback: str) -> str:
        """把用户输入清洗成合法文件/目录名。"""
        cleaned = re.sub(r'[\\/:*?"<>|]+', "_", (text or "").strip()).strip(" .")
        return cleaned or fallback

    def write_file(self, path: str, cfg: dict) -> bool:
        payload = {
            "schema_version": _CONFIG_SCHEMA_VERSION,
            "module_type": self._module_type,
            "config": cfg,
        }
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return True
        except OSError:
            _logger.error("写入配置文件失败：%s", path, exc_info=True)
            return False

    def read_file(self, path: str) -> dict | None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError):
            _logger.error("读取配置文件失败：%s", path, exc_info=True)
            return None
        if not isinstance(payload, dict):
            return None
        cfg = payload.get("config")
        return cfg if isinstance(cfg, dict) else None

    def prompt_save_path(self, parent) -> str | None:
        """弹出命名对话框，按芯片名分类到子目录，返回目标路径。"""
        cfg = self.collect()
        chip = self.safe_name(cfg.get("chip_name", ""), "未分类芯片")
        default_name = self.safe_name(
            cfg.get("module_name", "") or self._module_type, self._module_type)
        name, ok = QInputDialog.getText(
            parent, "另存配置", f"配置名称（将归入芯片「{chip}」分类）：", text=default_name)
        if not ok:
            return None
        name = self.safe_name(name, default_name)
        target_dir = os.path.join(self.configs_root(), chip)
        path = os.path.join(target_dir, f"{name}.json")
        if os.path.exists(path):
            resp = QMessageBox.question(
                parent, "覆盖确认", f"配置「{name}」已存在，是否覆盖？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if resp != QMessageBox.Yes:
                return None
        return path

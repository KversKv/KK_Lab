# -*- coding: utf-8 -*-
"""页面配置自动记忆（用户无感）。

页面 UI 构建完成后 ``restore()`` 回填上次配置；被监听控件变更后去抖自动
保存；应用退出（``aboutToQuit``）兜底立即保存。仅恢复控件值，绝不触发
仪器连接。

用法 A —— 页面已有 ``get_test_config()`` / ``apply_config_to_controls()``::

    self._config_memory = ConfigMemory("pmu_test/dcdc_efficiency", self)
    self._config_memory.bind_interface(
        self.get_test_config,
        lambda cfg: self.apply_config_to_controls(cfg, silent=True),
    )
    self._config_memory.watch(self)
    self._config_memory.restore()

用法 B —— 无配置接口页面，逐控件绑定（bind 内部已挂变更信号，无需 watch）::

    self._config_memory = ConfigMemory("chamber", self)
    self._config_memory.bind("target_temp", self.temp_input)
    self._config_memory.bind("loop_forever", self.loop_forever_check)
    self._config_memory.restore()

存储：``user_data/page_configs/<namespace>.json``（schema_version 包装，
损坏时记日志并回落默认，不抛异常）。
"""
from __future__ import annotations

import json
import os

from PySide6.QtCore import QCoreApplication, QObject, QTimer
from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QDoubleSpinBox,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QTabWidget,
    QWidget,
)

from log_config import get_logger
from ui.resource_path import get_user_data_dir

logger = get_logger(__name__)

_SCHEMA_VERSION = 1
_ROOT_NAMESPACE = "page_configs"


class ConfigMemory(QObject):
    """单页面粒度的配置自动保存 / 恢复。"""

    SAVE_DELAY_MS = 800

    def __init__(self, namespace: str, parent: QWidget):
        """namespace 用 "/" 分级（如 "pmu_test/dcdc_efficiency"），映射为同名 json 文件。"""
        super().__init__(parent)
        safe = namespace.replace("\\", "/").strip("/")
        self._path = os.path.join(get_user_data_dir(_ROOT_NAMESPACE), f"{safe}.json")
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
        except OSError:
            logger.error("ConfigMemory 创建目录失败: %s", self._path, exc_info=True)
        self._bindings: list = []  # [(key, getter, setter)]
        self._collect_fn = None
        self._apply_fn = None
        self._restoring = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.save_now)
        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.save_now)

    # ---------- 绑定 ----------

    def bind_interface(self, collect_fn, apply_fn) -> None:
        """接口模式：collect_fn() -> dict，apply_fn(cfg: dict)。恢复走 apply_fn。"""
        self._collect_fn = collect_fn
        self._apply_fn = apply_fn

    def bind(self, key: str, widget: QWidget) -> None:
        """控件绑定模式：登记键名与控件的双向映射，并挂变更信号自动保存。"""
        accessors = self._accessors(widget)
        if accessors is None:
            logger.warning(
                "ConfigMemory 不支持的控件类型: %s (%s)", key, type(widget).__name__
            )
            return
        getter, setter = accessors
        self._bindings.append((key, getter, setter))
        self._hook(widget)

    def watch(self, root: QWidget) -> None:
        """递归挂 root 下所有输入控件的变更信号 → 去抖保存（接口模式用）。"""
        for widget in root.findChildren(QWidget):
            self._hook(widget)

    # ---------- 生命周期 ----------

    def restore(self) -> None:
        """读取上次配置并回填。文件不存在 / 损坏时静默回落，不打扰用户。"""
        cfg = self._read_file()
        if not cfg:
            return
        self._restoring = True
        try:
            if self._apply_fn is not None:
                self._apply_fn(cfg)
            # 绑定项在接口回填后覆盖（接口未覆盖的页面级控件靠 bind 补充）
            for key, _getter, setter in self._bindings:
                if key not in cfg:
                    continue
                try:
                    setter(cfg[key])
                except Exception:  # noqa: BLE001 - 单项失败不阻塞其余回填
                    logger.error("ConfigMemory 回填失败: %s", key, exc_info=True)
        except Exception:  # noqa: BLE001 - 恢复失败回落默认
            logger.error("ConfigMemory 恢复配置失败: %s", self._path, exc_info=True)
        finally:
            self._restoring = False

    def save_now(self) -> None:
        """立即采集并写盘（去抖定时器与 aboutToQuit 都会走到这里）。"""
        if self._restoring:
            return
        cfg = {}
        if self._collect_fn is not None:
            try:
                collected = self._collect_fn()
            except Exception:  # noqa: BLE001 - 采集失败不炸页面
                logger.error("ConfigMemory 采集配置失败: %s", self._path, exc_info=True)
                return
            if isinstance(collected, dict):
                cfg.update(collected)
        # 绑定项补充 / 覆盖接口采集结果
        for key, getter, _setter in self._bindings:
            try:
                cfg[key] = getter()
            except Exception:  # noqa: BLE001
                logger.error("ConfigMemory 读取控件失败: %s", key, exc_info=True)
        if not cfg:
            return
        self._write_file(cfg)

    # ---------- 内部 ----------

    def _hook(self, widget: QWidget) -> None:
        signal = self._change_signal(widget)
        if signal is not None:
            try:
                signal.connect(self._schedule_save)
            except (RuntimeError, TypeError):  # noqa: BLE001
                pass

    def _schedule_save(self, *args) -> None:
        if self._restoring:
            return
        self._timer.start(self.SAVE_DELAY_MS)

    @staticmethod
    def _change_signal(widget: QWidget):
        if isinstance(widget, QComboBox):
            return widget.currentIndexChanged
        if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            return widget.valueChanged
        if isinstance(widget, QLineEdit):
            return widget.textChanged
        if isinstance(widget, QPlainTextEdit):
            return widget.textChanged
        if isinstance(widget, QTabWidget):
            return widget.currentChanged
        if isinstance(widget, QAbstractButton):
            return widget.toggled
        return getattr(widget, "toggled", None)  # ToggleSwitch 等自定义控件

    @staticmethod
    def _accessors(widget: QWidget):
        """按控件类型返回 (getter, setter)，不支持的类型返回 None。"""
        if isinstance(widget, QComboBox):
            def _set_combo(value):
                text = str(value)
                idx = widget.findText(text)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                elif widget.isEditable():
                    widget.setCurrentText(text)
                else:
                    # 动态下拉（VISA/串口扫描结果）：补回上次文本，仅显示不触发连接
                    widget.addItem(text)
                    widget.setCurrentIndex(widget.count() - 1)
            return widget.currentText, _set_combo
        if isinstance(widget, QDoubleSpinBox):
            return widget.value, lambda v: widget.setValue(float(v))
        if isinstance(widget, QSpinBox):
            return widget.value, lambda v: widget.setValue(int(v))
        if isinstance(widget, QLineEdit):
            return widget.text, lambda v: widget.setText(str(v))
        if isinstance(widget, QPlainTextEdit):
            return widget.toPlainText, lambda v: widget.setPlainText(str(v))
        if isinstance(widget, QTabWidget):
            return widget.currentIndex, lambda v: widget.setCurrentIndex(int(v))
        if isinstance(widget, QAbstractButton):
            return widget.isChecked, lambda v: widget.setChecked(bool(v))
        # ToggleSwitch 等自定义控件（duck-typing：checked/set_checked）
        checked = getattr(widget, "checked", None)
        set_checked = getattr(widget, "set_checked", None)
        if callable(checked) and callable(set_checked):
            return checked, lambda v: set_checked(bool(v))
        return None

    def _read_file(self) -> dict | None:
        if not os.path.isfile(self._path):
            return None
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                payload = json.load(f) or {}
        except (OSError, json.JSONDecodeError):
            logger.error("ConfigMemory 读取配置失败: %s", self._path, exc_info=True)
            return None
        cfg = payload.get("config")
        if not isinstance(cfg, dict):
            return None
        return cfg

    def _write_file(self, cfg: dict) -> None:
        payload = {"schema_version": _SCHEMA_VERSION, "config": cfg}
        tmp_path = self._path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._path)
        except (OSError, TypeError, ValueError):
            logger.error("ConfigMemory 写入配置失败: %s", self._path, exc_info=True)
            try:
                if os.path.isfile(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass

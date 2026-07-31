"""ConfigManagerDialog — 按芯片分类管理配置（打开 / 新增 / 重命名 / 移动 / 删除）。

目录结构：``<root>/<芯片名>/<配置名>.json``；树顶层为芯片分类，子节点为配置。
由 ``_base_subpage._ConfigManagerDialog`` 原样迁出（行为零变更），样式改走
``apply_qss(self, "dialog")``（token 化，视觉与旧 DIALOG_QSS 一致）。

为什么这样拆：~340 行的配置管理 UI 与子页基类的"装配/契约"职责无关，
独立文件后子页基类只面对 ``ConfigManagerDialog(root, module_type, parent)``
+ ``selected_path()`` 两个接口。
"""
from __future__ import annotations

import json
import os
import re
import shutil

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QInputDialog, QLabel, QMessageBox, QPushButton,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)

from log_config import get_logger
from ui.theme import apply_qss

from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag

_logger = get_logger(__name__)

_CONFIG_SCHEMA_VERSION = 1


class ConfigManagerDialog(QDialog):
    """配置管理器：按芯片分类管理（打开 / 新增 / 重命名 / 移动归属 / 删除）配置。"""

    def __init__(self, root: str, module_type: str, parent=None):
        super().__init__(parent)
        self._root = root
        self._module_type = module_type
        self.setWindowTitle(f"{module_type.upper()} Config Manager")
        self.setMinimumSize(520, 480)
        apply_qss(self, "dialog")
        self._selected_path: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        layout.addWidget(QLabel("按芯片分类管理配置，双击打开；右侧按钮进行管理："))

        body = QHBoxLayout()
        body.setSpacing(8)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["名称", "归属芯片"])
        self.tree.setColumnWidth(0, 220)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.currentItemChanged.connect(self._on_current_changed)
        body.addWidget(self.tree, 1)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(6)
        self.open_btn = QPushButton("打开")
        self.open_btn.setDefault(True)
        self.open_btn.setAutoDefault(True)
        self.new_btn = QPushButton("新增配置…")
        self.rename_btn = QPushButton("重命名…")
        self.move_btn = QPushButton("移动归属…")
        self.delete_btn = QPushButton("删除")
        for _b in (self.open_btn, self.new_btn, self.rename_btn, self.move_btn, self.delete_btn):
            _b.setMinimumWidth(88)
            _b.setCursor(Qt.PointingHandCursor)
        self.open_btn.clicked.connect(self._accept_selection)
        self.new_btn.clicked.connect(self._on_new_config)
        self.rename_btn.clicked.connect(self._on_rename)
        self.move_btn.clicked.connect(self._on_move)
        self.delete_btn.clicked.connect(self._on_delete)
        btn_col.addWidget(self.open_btn)
        btn_col.addWidget(self.new_btn)
        btn_col.addWidget(self.rename_btn)
        btn_col.addWidget(self.move_btn)
        btn_col.addWidget(self.delete_btn)
        btn_col.addStretch()
        body.addLayout(btn_col)
        layout.addLayout(body, 1)

        close_btn = QPushButton("关闭")
        close_btn.setDefault(False)
        close_btn.setAutoDefault(False)
        close_btn.setMinimumWidth(88)
        close_btn.clicked.connect(self.reject)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

        self._populate()
        self._on_current_changed(self.tree.currentItem(), None)

    # ------------------------------------------------------------------ data
    @staticmethod
    def _safe(text: str, fallback: str) -> str:
        cleaned = re.sub(r'[\\/:*?"<>|]+', "_", (text or "").strip()).strip(" .")
        return cleaned or fallback

    def _chip_names(self) -> list[str]:
        if not os.path.isdir(self._root):
            return []
        return sorted(
            d for d in os.listdir(self._root)
            if os.path.isdir(os.path.join(self._root, d))
        )

    def _populate(self, select_path: str | None = None) -> None:
        self.tree.clear()
        chip_dirs = self._chip_names()
        has_any = False
        select_item: QTreeWidgetItem | None = None
        for chip in chip_dirs:
            chip_path = os.path.join(self._root, chip)
            files = sorted(
                f for f in os.listdir(chip_path)
                if f.lower().endswith(".json")
            )
            if not files:
                continue
            chip_node = QTreeWidgetItem([chip, ""])
            chip_node.setFlags(Qt.ItemIsEnabled)
            chip_node.setData(0, Qt.UserRole, None)
            chip_node.setData(1, Qt.UserRole, chip)
            self.tree.addTopLevelItem(chip_node)
            for f in files:
                cfg_path = os.path.join(chip_path, f)
                cfg_node = QTreeWidgetItem([os.path.splitext(f)[0], chip])
                cfg_node.setData(0, Qt.UserRole, cfg_path)
                cfg_node.setData(1, Qt.UserRole, chip)
                chip_node.addChild(cfg_node)
                if select_path and os.path.normpath(cfg_path) == os.path.normpath(select_path):
                    select_item = cfg_node
            chip_node.setExpanded(True)
            has_any = True
        if not has_any:
            placeholder = QTreeWidgetItem(["（暂无已保存的配置）", ""])
            placeholder.setFlags(Qt.ItemIsEnabled)
            placeholder.setData(0, Qt.UserRole, None)
            self.tree.addTopLevelItem(placeholder)
        if select_item is not None:
            self.tree.setCurrentItem(select_item)

    def _current_cfg(self) -> tuple[str | None, str | None]:
        """返回 (配置路径, 归属芯片)，未选中配置返回 (None, None)。"""
        item = self.tree.currentItem()
        if not item:
            return None, None
        path = item.data(0, Qt.UserRole)
        chip = item.data(1, Qt.UserRole)
        if not path:
            return None, None
        return path, chip

    def _on_current_changed(self, current: QTreeWidgetItem, _prev) -> None:
        is_cfg = bool(current and current.data(0, Qt.UserRole))
        self.open_btn.setEnabled(is_cfg)
        self.rename_btn.setEnabled(is_cfg)
        self.move_btn.setEnabled(is_cfg)
        self.delete_btn.setEnabled(is_cfg)

    # ------------------------------------------------------------------ open
    def _on_item_double_clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        if item and item.data(0, Qt.UserRole):
            self._selected_path = item.data(0, Qt.UserRole)
            self.accept()

    def _accept_selection(self) -> None:
        path, _chip = self._current_cfg()
        if path:
            self._selected_path = path
            self.accept()

    def selected_path(self) -> str | None:
        return self._selected_path

    # ------------------------------------------------------------------ manage
    def _on_new_config(self) -> None:
        chips = self._chip_names()
        chip, ok = QInputDialog.getItem(
            self, "新增配置", "归属芯片（可输入新名称新建分类）：",
            chips, 0, True)
        if not ok or not chip.strip():
            return
        chip = self._safe(chip, "未分类芯片")
        name, ok = QInputDialog.getText(
            self, "新增配置", f"配置名称（归入芯片「{chip}」）：",
            text=self._module_type)
        if not ok:
            return
        name = self._safe(name, self._module_type)
        target_dir = os.path.join(self._root, chip)
        path = os.path.join(target_dir, f"{name}.json")
        if os.path.exists(path):
            QMessageBox.warning(self, "新增失败", f"配置「{name}」已存在。")
            return
        default_cfg = self._default_config(chip)
        payload = {
            "schema_version": _CONFIG_SCHEMA_VERSION,
            "module_type": self._module_type,
            "config": default_cfg,
        }
        try:
            os.makedirs(target_dir, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except OSError:
            _logger.error("新增配置文件失败：%s", path, exc_info=True)
            QMessageBox.warning(self, "新增失败", "配置写入失败，详见日志。")
            return
        self._populate(select_path=path)

    def _default_config(self, chip: str) -> dict:
        return {
            "selected_items": [],
            "chip_name": chip,
            "module_name": "",
            "operator": "",
            "temp_test_enabled": False,
            "temperature": "",
            "temp_soak_s": 300,
            "temp_tolerance_c": 2,
            "temp_wait_s": 1800,
            "vin_channel": "CH 1",
            "vout_channel": "CH 2",
            "iload_channel": "CH 3",
            "vout_nominal_mv": 1800 if self._module_type == "ldo" else 1200,
            "device_addr": "0x00",
            "width_flag": int(I2CWidthFlag.BIT_10),
            "scope_vout_channel": 1,
            "item_overrides": {},
        }

    def _on_rename(self) -> None:
        path, chip = self._current_cfg()
        if not path:
            return
        old_name = os.path.splitext(os.path.basename(path))[0]
        name, ok = QInputDialog.getText(
            self, "重命名配置", "新的配置名称：", text=old_name)
        if not ok:
            return
        name = self._safe(name, old_name)
        if name == old_name:
            return
        new_path = os.path.join(os.path.dirname(path), f"{name}.json")
        if os.path.exists(new_path):
            QMessageBox.warning(self, "重命名失败", f"配置「{name}」已存在。")
            return
        try:
            os.replace(path, new_path)
        except OSError:
            _logger.error("重命名配置失败：%s -> %s", path, new_path, exc_info=True)
            QMessageBox.warning(self, "重命名失败", "无法重命名，详见日志。")
            return
        self._populate(select_path=new_path)

    def _on_move(self) -> None:
        path, chip = self._current_cfg()
        if not path:
            return
        chips = self._chip_names()
        current_idx = chips.index(chip) if chip in chips else 0
        target, ok = QInputDialog.getItem(
            self, "移动归属", f"将配置移到哪个芯片分类（可输入新名称）：",
            chips, current_idx, True)
        if not ok or not target.strip():
            return
        target = self._safe(target, chip)
        if target == chip:
            return
        fname = os.path.basename(path)
        target_dir = os.path.join(self._root, target)
        new_path = os.path.join(target_dir, fname)
        if os.path.exists(new_path):
            QMessageBox.warning(
                self, "移动失败",
                f"芯片「{target}」下已存在同名配置「{os.path.splitext(fname)[0]}」。")
            return
        try:
            os.makedirs(target_dir, exist_ok=True)
            shutil.move(path, new_path)
        except OSError:
            _logger.error("移动配置失败：%s -> %s", path, new_path, exc_info=True)
            QMessageBox.warning(self, "移动失败", "无法移动配置，详见日志。")
            return
        self._populate(select_path=new_path)

    def _on_delete(self) -> None:
        path, chip = self._current_cfg()
        if not path:
            return
        name = os.path.splitext(os.path.basename(path))[0]
        resp = QMessageBox.question(
            self, "删除确认",
            f"确定删除配置「{name}」（芯片「{chip}」）？此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resp != QMessageBox.Yes:
            return
        try:
            os.remove(path)
        except OSError:
            _logger.error("删除配置失败：%s", path, exc_info=True)
            QMessageBox.warning(self, "删除失败", "无法删除配置，详见日志。")
            return
        self._populate()

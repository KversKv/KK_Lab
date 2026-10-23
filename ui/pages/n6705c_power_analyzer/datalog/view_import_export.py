#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import traceback
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)
from instruments.power.keysight.n6705c_datalog_process import build_marker_dlog_bytes, import_csv_file, import_dlog_file, import_edlg_file
from ui.pages.n6705c_power_analyzer import datalog_style as dss
from ui.pages.n6705c_power_analyzer.datalog.helpers import _display_label, _parse_ch_label, _sort_key_for_label
from log_config import get_logger

logger = get_logger(__name__)

class ImportExportViewMixin:
    """Datalog 页导入导出视图：CSV / eDlog / Dlog 导入与标准 / 合并 / Marker 导出。"""

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Datalog", "",
            "Datalog Files (*.csv *.dlog *.edlg);;CSV Files (*.csv);;Dlog Files (*.dlog);;EDLG Files (*.edlg);;All Files (*)"
        )
        if not path:
            return

        try:
            if path.lower().endswith(".edlg"):
                self._import_edlg(path)
            elif path.lower().endswith(".dlog"):
                self._import_dlog(path)
            else:
                self._import_csv(path)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Import failed: {e}\n{tb}")
            QMessageBox.critical(
                self,
                "Import Failed",
                f"{type(e).__name__}: {e}\n\n{tb}"
            )

    def _import_csv(self, path):
        result = import_csv_file(path)
        if not result:
            return

        if len(result) == 4:
            all_data, custom_labels, ch_name_renames, combined_meta = result
        else:
            all_data, custom_labels, ch_name_renames = result
            combined_meta = None
        if not all_data:
            return

        if combined_meta:
            self._import_combined_csv(path, all_data, custom_labels, ch_name_renames, combined_meta)
            return

        self._import_counter += 1
        prefix = f"F{self._import_counter}-"
        prefixed = {f"{prefix}{k}": v for k, v in all_data.items()}
        new_keys = set(prefixed.keys())
        self.datalog_data.update(prefixed)
        tab_name = os.path.basename(path)
        self._build_imported_channel_config(tab_name=tab_name, data_keys=new_keys, file_prefix=prefix.rstrip("-"))
        self._sync_checkboxes_to_data()

        if custom_labels:
            for lbl in custom_labels:
                lbl["channel"] = f"{prefix}{lbl['channel']}" if lbl.get("channel") else ""
            self.custom_labels.extend(custom_labels)
            self._refresh_labels_display()

        if ch_name_renames:
            for key, display_name in ch_name_renames.items():
                self.ch_name_renames[f"{prefix}{key}"] = display_name

        self._refresh_plot()

    def _import_combined_csv(self, path, all_data, custom_labels, ch_name_renames, combined_meta):
        time_offsets = combined_meta.get("time_offsets", {}) or {}
        source_files = combined_meta.get("source_files", []) or []

        logger.info(
            "[CombinedImport] path=%s, keys=%d, sources=%d, time_offsets=%d",
            path, len(all_data), len(source_files), len(time_offsets)
        )

        source_name_map = {orig_prefix: src_name for orig_prefix, src_name in source_files}

        orig_prefixes_in_data = set()
        for key in all_data.keys():
            m = re.match(r'^(F\d+)-', key)
            if m:
                orig_prefixes_in_data.add(m.group(1))
            else:
                orig_prefixes_in_data.add("")

        logger.info("[CombinedImport] orig_prefixes=%s", sorted(orig_prefixes_in_data))

        prefix_remap = {}
        for orig_prefix in sorted(orig_prefixes_in_data, key=lambda s: (0, int(s[1:])) if s else (1, 0)):
            self._import_counter += 1
            new_prefix = f"F{self._import_counter}"
            prefix_remap[orig_prefix] = new_prefix

        logger.info("[CombinedImport] prefix_remap=%s", prefix_remap)

        def _remap_key(key):
            m = re.match(r'^(F\d+)-(.*)', key)
            if m:
                orig = m.group(1)
                rest = m.group(2)
                new_p = prefix_remap.get(orig, orig)
                return f"{new_p}-{rest}"
            new_p = prefix_remap.get("", "")
            if new_p:
                return f"{new_p}-{key}"
            return key

        remapped_data = {_remap_key(k): v for k, v in all_data.items()}
        self.datalog_data.update(remapped_data)

        logger.info("[CombinedImport] remapped_keys=%s", list(remapped_data.keys()))

        per_group_keys = {}
        for orig_prefix in orig_prefixes_in_data:
            new_prefix = prefix_remap[orig_prefix]
            group_keys = set()
            for k in remapped_data.keys():
                km = re.match(r'^(F\d+)-', k)
                if km and km.group(1) == new_prefix:
                    group_keys.add(k)
                elif not km and new_prefix == prefix_remap.get(""):
                    group_keys.add(k)
            per_group_keys[orig_prefix] = (new_prefix, group_keys)

        base_name = os.path.basename(path)
        for orig_prefix, (new_prefix, group_keys) in per_group_keys.items():
            if not group_keys:
                logger.warning("[CombinedImport] skip empty group orig=%s new=%s", orig_prefix, new_prefix)
                continue
            src_name = source_name_map.get(orig_prefix)
            if src_name:
                tab_name = src_name
            elif len(per_group_keys) == 1:
                tab_name = base_name
            else:
                tab_name = f"{base_name} [{orig_prefix}]" if orig_prefix else base_name
            logger.info(
                "[CombinedImport] build tab orig=%s new=%s tab_name=%s keys=%s",
                orig_prefix, new_prefix, tab_name, sorted(group_keys)
            )
            try:
                self._build_imported_channel_config(
                    tab_name=tab_name, data_keys=group_keys, file_prefix=new_prefix
                )
            except Exception as e:
                logger.error(
                    "[CombinedImport] build tab FAILED for %s: %s\n%s",
                    tab_name, e, traceback.format_exc()
                )

        for scope, off_val in time_offsets.items():
            if scope == "B_slot":
                if not self._b_time_offset:
                    self._b_time_offset = off_val
            else:
                new_prefix = prefix_remap.get(scope)
                if new_prefix:
                    self._file_time_offsets[new_prefix] = off_val

        self._sync_checkboxes_to_data()

        if custom_labels:
            for lbl in custom_labels:
                ch_raw = lbl.get("channel", "")
                if ch_raw:
                    lbl["channel"] = _remap_key(ch_raw)
            self.custom_labels.extend(custom_labels)
            self._refresh_labels_display()

        if ch_name_renames:
            for key, display_name in ch_name_renames.items():
                self.ch_name_renames[_remap_key(key)] = display_name

        self._refresh_plot()

    def _import_edlg(self, path):
        result = import_edlg_file(path)
        if result is None or result[0] is None:
            return

        all_data, raw_data = result
        self._raw_dlog_list.append(raw_data)
        self._import_counter += 1
        prefix = f"F{self._import_counter}-"
        prefixed = {f"{prefix}{k}": v for k, v in all_data.items()}
        new_keys = set(prefixed.keys())
        self.datalog_data.update(prefixed)
        tab_name = os.path.basename(path)
        self._build_imported_channel_config(tab_name=tab_name, data_keys=new_keys, file_prefix=prefix.rstrip("-"))
        self._sync_checkboxes_to_data()
        self._refresh_plot()

    def _import_dlog(self, path):
        result = import_dlog_file(path)
        if result is None or result[0] is None:
            return

        all_data, raw_data = result
        self._raw_dlog_list.append(raw_data)
        self._import_counter += 1
        prefix = f"F{self._import_counter}-"
        prefixed = {f"{prefix}{k}": v for k, v in all_data.items()}
        new_keys = set(prefixed.keys())
        self.datalog_data.update(prefixed)
        tab_name = os.path.basename(path)
        self._build_imported_channel_config(tab_name=tab_name, data_keys=new_keys, file_prefix=prefix.rstrip("-"))
        self._sync_checkboxes_to_data()
        self._refresh_plot()

    def _on_export(self):
        if not self.datalog_data:
            return

        mode = self._show_export_dialog()
        if mode is None:
            return
        if mode == "combined":
            self._export_combined_csv()
        elif mode == "marker":
            self._export_marker_csv()
        else:
            self._export_standard()

    def _show_export_dialog(self):
        visible_keys = self._get_visible_keys()
        visible_count = len(visible_keys)
        marker_window = self.get_marker_window()
        has_markers = marker_window is not None

        dialog = QDialog(self)
        dialog.setWindowTitle("Export Datalog")
        dialog.setFixedWidth(420)
        dialog.setStyleSheet(dss.dlg_style(radio=True))

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Export Datalog")
        title.setStyleSheet(dss.DIALOG_TITLE_STYLE)
        layout.addWidget(title)

        desc = QLabel("Choose how to export the current dataset.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        group = QButtonGroup(dialog)

        rb_standard = QRadioButton("Standard Export  (Dlog / CSV, all data)")
        rb_standard.setChecked(True)
        group.addButton(rb_standard)
        layout.addWidget(rb_standard)

        std_hint = QLabel("    Exports the full dataset in the original format.\n"
                          "    Supports .dlog (raw) and .csv (legacy layout).")
        std_hint.setStyleSheet(dss.HINT_TEXT_STYLE)
        layout.addWidget(std_hint)

        rb_combined = QRadioButton(
            f"Combined CSV  (visible channels only: {visible_count})"
        )
        group.addButton(rb_combined)
        layout.addWidget(rb_combined)

        cmb_hint = QLabel("    Merges all currently visible channels from different\n"
                          "    files into one CSV, sorted automatically. LABELS,\n"
                          "    rename map, time offsets and source files are kept.")
        cmb_hint.setStyleSheet(dss.HINT_TEXT_STYLE)
        layout.addWidget(cmb_hint)

        if visible_count == 0:
            rb_combined.setEnabled(False)
            cmb_hint.setText("    (No visible channels — enable at least one in Channel Config)")
            cmb_hint.setStyleSheet(dss.HINT_ERROR_STYLE)

        rb_marker = QRadioButton(
            f"Marker Export  (visible channels only: {visible_count})"
        )
        group.addButton(rb_marker)
        layout.addWidget(rb_marker)

        mk_hint = QLabel("    Exports only the region between Marker A and Marker B\n"
                         "    for currently visible channels (.csv or .dlog).")
        mk_hint.setStyleSheet(dss.HINT_TEXT_STYLE)
        layout.addWidget(mk_hint)

        if not has_markers:
            rb_marker.setEnabled(False)
            mk_hint.setText("    (Place both Marker A and Marker B to enable this option)")
            mk_hint.setStyleSheet(dss.HINT_ERROR_STYLE)
        elif visible_count == 0:
            rb_marker.setEnabled(False)
            mk_hint.setText("    (No visible channels — enable at least one in Channel Config)")
            mk_hint.setStyleSheet(dss.HINT_ERROR_STYLE)
        else:
            lo = min(marker_window["a"], marker_window["b"])
            hi = max(marker_window["a"], marker_window["b"])
            mk_hint.setText("    Exports only the region between Marker A and Marker B\n"
                            f"    for currently visible channels (.csv or .dlog).\n"
                            f"    Region: {lo:.4f}s ~ {hi:.4f}s")

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        ok_btn = QPushButton("Continue")
        ok_btn.setDefault(True)
        ok_btn.setStyleSheet(dss.EXPORT_OK_BTN_STYLE)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

        result = {"mode": None}

        def _accept():
            if rb_marker.isChecked():
                result["mode"] = "marker"
            elif rb_combined.isChecked():
                result["mode"] = "combined"
            else:
                result["mode"] = "standard"
            dialog.accept()

        ok_btn.clicked.connect(_accept)
        cancel_btn.clicked.connect(dialog.reject)

        if dialog.exec() != QDialog.Accepted:
            return None
        return result["mode"]

    def _export_standard(self):
        path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Datalog", "",
            "Dlog Files (*.dlog);;CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return

        try:
            if path.lower().endswith(".dlog"):
                if self._raw_dlog_list:
                    with open(path, 'wb') as f:
                        f.write(self._raw_dlog_list[0])
                    if len(self._raw_dlog_list) > 1:
                        base, ext = os.path.splitext(path)
                        for idx in range(1, len(self._raw_dlog_list)):
                            with open(f"{base}_unit{idx}{ext}", 'wb') as f:
                                f.write(self._raw_dlog_list[idx])
            else:
                sorted_labels = sorted(self.datalog_data.keys(), key=_sort_key_for_label)

                group_a = []
                group_b = []
                for lbl in sorted_labels:
                    if self._is_b_label(lbl):
                        group_b.append(lbl)
                    else:
                        group_a.append(lbl)

                has_both = bool(group_a) and bool(group_b)

                len_a = max((len(self.datalog_data[l]["time"]) for l in group_a), default=0)
                len_b = max((len(self.datalog_data[l]["time"]) for l in group_b), default=0)
                max_len = max(len_a, len_b)

                with open(path, "w", newline="") as f:
                    header_parts = []
                    if has_both:
                        header_parts.append("Time_A(s)")
                        for lbl in group_a:
                            header_parts.append(_display_label(lbl))
                        header_parts.append("Time_B(s)")
                        for lbl in group_b:
                            header_parts.append(_display_label(lbl))
                    else:
                        header_parts.append("Time(s)")
                        for lbl in sorted_labels:
                            header_parts.append(_display_label(lbl))
                    f.write(",".join(header_parts) + "\n")

                    for i in range(max_len):
                        row_parts = []
                        if has_both:
                            if group_a and i < len_a:
                                ref_a_lbl = group_a[0]
                                ref_a = self.datalog_data[ref_a_lbl]
                                t_val = ref_a["time"][i] + self._get_total_time_offset(ref_a_lbl)
                                row_parts.append(f"{t_val:.6f}")
                            else:
                                row_parts.append("")
                            for lbl in group_a:
                                ch = self.datalog_data[lbl]
                                if i < len(ch["values"]):
                                    row_parts.append(f"{ch['values'][i]:.9f}")
                                else:
                                    row_parts.append("")

                            if group_b and i < len_b:
                                ref_b_lbl = group_b[0]
                                ref_b = self.datalog_data[ref_b_lbl]
                                t_val = ref_b["time"][i] + self._get_total_time_offset(ref_b_lbl)
                                row_parts.append(f"{t_val:.6f}")
                            else:
                                row_parts.append("")
                            for lbl in group_b:
                                ch = self.datalog_data[lbl]
                                if i < len(ch["values"]):
                                    row_parts.append(f"{ch['values'][i]:.9f}")
                                else:
                                    row_parts.append("")
                        else:
                            all_labels = sorted_labels
                            first_lbl = all_labels[0]
                            first = self.datalog_data[first_lbl]
                            if i < len(first["time"]):
                                t_val = first["time"][i] + self._get_total_time_offset(first_lbl)
                                row_parts.append(f"{t_val:.6f}")
                            else:
                                row_parts.append("")
                            for lbl in all_labels:
                                ch = self.datalog_data[lbl]
                                if i < len(ch["values"]):
                                    row_parts.append(f"{ch['values'][i]:.9f}")
                                else:
                                    row_parts.append("")

                        f.write(",".join(row_parts) + "\n")

                    if self.custom_labels:
                        f.write("\n[CUSTOM_LABELS]\n")
                        f.write("time,text,channel\n")
                        for lbl in self.custom_labels:
                            t_str = f"{lbl['time']:.6f}"
                            ch_raw = lbl.get("channel", "")
                            ch_display = _display_label(ch_raw) if ch_raw else ""
                            text_escaped = lbl["text"].replace('"', '""')
                            ch_escaped = ch_display.replace('"', '""')
                            if "," in lbl["text"] or '"' in lbl["text"]:
                                text_escaped = f'"{text_escaped}"'
                            if "," in ch_display or '"' in ch_display:
                                ch_escaped = f'"{ch_escaped}"'
                            f.write(f"{t_str},{text_escaped},{ch_escaped}\n")

                    if self.ch_name_renames:
                        f.write("\n[CH_NAME_RENAMES]\n")
                        f.write("key,display_name\n")
                        for key, display_name in self.ch_name_renames.items():
                            key_display = _display_label(key)
                            key_escaped = key_display.replace('"', '""')
                            name_escaped = display_name.replace('"', '""')
                            if "," in key_display or '"' in key_display:
                                key_escaped = f'"{key_escaped}"'
                            if "," in display_name or '"' in display_name:
                                name_escaped = f'"{name_escaped}"'
                            f.write(f"{key_escaped},{name_escaped}\n")
        except Exception:
            logger.error("Standard datalog export failed", exc_info=True)

    @staticmethod
    def _csv_escape(s):
        """CSV 字段转义：含逗号/引号/换行时加双引号包裹。"""
        s = str(s)
        if "," in s or '"' in s or "\n" in s:
            return '"' + s.replace('"', '""') + '"'
        return s

    def _write_csv_meta_sections(self, f, sorted_keys, visible_keys, label_filter=None):
        """写入 combined/marker CSV 共用的尾部元数据段。

        依次输出 [TIME_OFFSETS] / [SOURCE_FILES] / [CUSTOM_LABELS] /
        [CH_NAME_RENAMES] 四段；label_filter 可选，用于 marker 导出时
        过滤掉落在标记区间外的自定义标签（签名为 (t_val)->bool）。
        """
        esc = self._csv_escape

        prefixes_in_use = set()
        for lbl in sorted_keys:
            p = self._get_file_prefix(lbl)
            if p:
                prefixes_in_use.add(p)

        has_b_visible = any(self._is_b_label(lbl) for lbl in sorted_keys)
        time_offset_rows = []
        if has_b_visible and self._b_time_offset:
            time_offset_rows.append(("B_slot", f"{self._b_time_offset:.9f}"))
        for prefix in sorted(prefixes_in_use):
            off = self._file_time_offsets.get(prefix, 0.0)
            if off:
                time_offset_rows.append((prefix, f"{off:.9f}"))
        if time_offset_rows:
            f.write("\n[TIME_OFFSETS]\n")
            f.write("scope,offset_s\n")
            for scope, val in time_offset_rows:
                f.write(f"{esc(scope)},{val}\n")

        source_rows = []
        for tc in self._imported_tab_configs:
            prefix = tc.get("file_prefix", "")
            if prefix and prefix in prefixes_in_use:
                source_rows.append((prefix, tc.get("tab_name", "")))
        if source_rows:
            f.write("\n[SOURCE_FILES]\n")
            f.write("file_prefix,source_name\n")
            for prefix, name in source_rows:
                f.write(f"{esc(prefix)},{esc(name)}\n")

        if self.custom_labels:
            label_rows = []
            for lbl in self.custom_labels:
                ch_raw = lbl.get("channel", "")
                if ch_raw and ch_raw not in visible_keys:
                    continue
                t_val = lbl.get("time", 0.0)
                if ch_raw:
                    t_val = t_val + self._get_total_time_offset(ch_raw)
                if label_filter is not None and not label_filter(t_val):
                    continue
                ch_display = _display_label(ch_raw) if ch_raw else ""
                label_rows.append((t_val, lbl.get("text", ""), ch_display))
            if label_rows:
                f.write("\n[CUSTOM_LABELS]\n")
                f.write("time,text,channel\n")
                for t_val, text, ch_display in label_rows:
                    f.write(f"{t_val:.6f},{esc(text)},{esc(ch_display)}\n")

        if self.ch_name_renames:
            rename_rows = []
            for key, display_name in self.ch_name_renames.items():
                if key not in visible_keys:
                    continue
                rename_rows.append((_display_label(key), display_name))
            if rename_rows:
                f.write("\n[CH_NAME_RENAMES]\n")
                f.write("key,display_name\n")
                for key_display, display_name in rename_rows:
                    f.write(f"{esc(key_display)},{esc(display_name)}\n")

    def _write_combined_csv(self, path):
        """把当前可见通道数据写入 CSV（核心导出逻辑，非交互）。

        返回 {"ok": bool, "path": str, "rows": int, "channels": int, "bytes": int, "message": str}。
        供 _export_combined_csv（对话框）与 export_combined_csv_to_path（AI 受控）复用。
        """
        visible_keys = self._get_visible_keys()
        if not visible_keys:
            return {"ok": False, "message": "当前无可见通道数据。"}
        try:
            sorted_keys = sorted(visible_keys, key=_sort_key_for_label)

            max_len = 0
            for lbl in sorted_keys:
                ch = self.datalog_data.get(lbl)
                if ch is None:
                    continue
                max_len = max(max_len, len(ch.get("time", [])), len(ch.get("values", [])))

            display_names = []
            for lbl in sorted_keys:
                disp = self.ch_name_renames.get(lbl) or _display_label(lbl)
                display_names.append(disp)

            esc = self._csv_escape

            with open(path, "w", newline="") as f:
                f.write("[COMBINED_EXPORT]\n")
                f.write("version,1\n\n")

                header_parts = []
                for disp in display_names:
                    header_parts.append(esc(f"Time_{disp}(s)"))
                    header_parts.append(esc(disp))
                f.write(",".join(header_parts) + "\n")

                for i in range(max_len):
                    row_parts = []
                    for lbl in sorted_keys:
                        ch = self.datalog_data.get(lbl, {})
                        times = ch.get("time", [])
                        values = ch.get("values", [])
                        if i < len(times):
                            t_val = times[i] + self._get_total_time_offset(lbl)
                            row_parts.append(f"{t_val:.6f}")
                        else:
                            row_parts.append("")
                        if i < len(values):
                            row_parts.append(f"{values[i]:.9f}")
                        else:
                            row_parts.append("")
                    f.write(",".join(row_parts) + "\n")

                self._write_csv_meta_sections(f, sorted_keys, visible_keys)
        except Exception:
            logger.error("Combined CSV export failed:\n%s", traceback.format_exc())
            return {"ok": False, "message": "CSV 导出失败，请查看日志。"}
        bytes_written = os.path.getsize(path) if os.path.exists(path) else 0
        return {
            "ok": True,
            "path": path,
            "rows": max_len,
            "channels": len(sorted_keys),
            "bytes": bytes_written,
            "message": f"已导出 {len(sorted_keys)} 通道 / {max_len} 行。",
        }

    def _export_combined_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Combined CSV", "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path = path + ".csv"
        self._write_combined_csv(path)

    def export_combined_csv_to_path(self, path):
        """非交互式导出当前可见通道数据到指定 CSV 路径（供 AI 受控导出，P6）。

        path 须为可写绝对路径（AI 侧已限定在用户数据目录下）；自动补 .csv 后缀。
        返回 _write_combined_csv 的结果 dict。
        """
        if not path.lower().endswith(".csv"):
            path = path + ".csv"
        return self._write_combined_csv(path)

    def _export_marker_csv(self):
        visible_keys = self._get_visible_keys()
        if not visible_keys:
            return

        marker_window = self.get_marker_window()
        if marker_window is None:
            return

        lo = min(marker_window["a"], marker_window["b"])
        hi = max(marker_window["a"], marker_window["b"])

        path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Marker Region", "",
            "CSV Files (*.csv);;Dlog Files (*.dlog);;All Files (*)"
        )
        if not path:
            return

        want_dlog = path.lower().endswith(".dlog") or "*.dlog" in (selected_filter or "")
        if want_dlog:
            if not path.lower().endswith(".dlog"):
                path = path + ".dlog"
            self._export_marker_dlog(path, sorted(visible_keys, key=_sort_key_for_label), lo, hi)
            return

        if not path.lower().endswith(".csv"):
            path = path + ".csv"

        try:
            sorted_keys = sorted(visible_keys, key=_sort_key_for_label)
            esc = self._csv_escape

            channel_rows = {}
            max_len = 0
            for lbl in sorted_keys:
                ch = self.datalog_data.get(lbl)
                if ch is None:
                    channel_rows[lbl] = []
                    continue
                off = self._get_total_time_offset(lbl)
                times = ch.get("time", [])
                values = ch.get("values", [])
                rows = []
                for j in range(min(len(times), len(values))):
                    t_eff = times[j] + off
                    if lo <= t_eff <= hi:
                        rows.append((t_eff, values[j]))
                channel_rows[lbl] = rows
                max_len = max(max_len, len(rows))

            display_names = []
            for lbl in sorted_keys:
                disp = self.ch_name_renames.get(lbl) or _display_label(lbl)
                display_names.append(disp)

            with open(path, "w", newline="") as f:
                f.write("[COMBINED_EXPORT]\n")
                f.write("version,1\n\n")

                header_parts = []
                for disp in display_names:
                    header_parts.append(esc(f"Time_{disp}(s)"))
                    header_parts.append(esc(disp))
                f.write(",".join(header_parts) + "\n")

                for i in range(max_len):
                    row_parts = []
                    for lbl in sorted_keys:
                        rows = channel_rows.get(lbl, [])
                        if i < len(rows):
                            t_val, v_val = rows[i]
                            row_parts.append(f"{t_val:.6f}")
                            row_parts.append(f"{v_val:.9f}")
                        else:
                            row_parts.append("")
                            row_parts.append("")
                    f.write(",".join(row_parts) + "\n")

                self._write_csv_meta_sections(
                    f, sorted_keys, visible_keys,
                    label_filter=lambda t_val: lo <= t_val <= hi,
                )
        except Exception:
            logger.error("Marker region CSV export failed:\n%s", traceback.format_exc())

    def _export_marker_dlog(self, path, sorted_keys, lo, hi):
        try:
            units = {"A": {}, "B": {}}
            for lbl in sorted_keys:
                ch_num, mtype, is_b = _parse_ch_label(lbl)
                if ch_num is None or mtype == "P":
                    continue
                ch = self.datalog_data.get(lbl)
                if ch is None:
                    continue
                slot = "B" if is_b else "A"
                units[slot].setdefault(ch_num, {})[mtype] = {
                    "times": ch.get("time", []),
                    "values": ch.get("values", []),
                    "offset": self._get_total_time_offset(lbl),
                }

            blobs = []
            for slot in ("A", "B"):
                if units[slot]:
                    blob = build_marker_dlog_bytes(units[slot], lo, hi)
                    if blob:
                        blobs.append(blob)

            if not blobs:
                logger.warning("Marker region dlog export: no valid samples in window.")
                return

            with open(path, "wb") as f:
                f.write(blobs[0])
            if len(blobs) > 1:
                base, ext = os.path.splitext(path)
                for idx in range(1, len(blobs)):
                    with open(f"{base}_unit{idx}{ext}", "wb") as f:
                        f.write(blobs[idx])
        except Exception:
            logger.error("Marker region dlog export failed:\n%s", traceback.format_exc())

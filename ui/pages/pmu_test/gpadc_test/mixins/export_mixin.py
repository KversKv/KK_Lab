"""GPADCTestUI Excel 导出 Mixin。

从 ui/pages/pmu_test/gpadc_test_ui.py 平移而来，行为零变更。
类装配见 gpadc_test_ui.py。"""

import datetime
from pathlib import Path
import re

from PySide6.QtCore import QThread, QTimer

from core.pmu_test.gpadc import TestWorker, build_linearity_auto_search_timeline
from core.pmu_test.gpadc.gpadc_gif import encode_search_gif_frames
from log_config import get_logger
from ui.pages.pmu_test.gpadc_test.search_gif_renderer import SearchGifFrameRenderer

logger = get_logger(__name__)


class _ExportMixin:
    """Excel / Auto Best 搜索 GIF 导出 Mixin"""

    def _search_gif_runtime(self):
        if not hasattr(self, "_search_gif_state"):
            self._search_gif_state = {
                "state": "idle", "timer": None, "renderer": None,
                "index": 0, "frames": [], "output": None,
                "thread": None, "worker": None,
            }
        return self._search_gif_state

    def _auto_best_export_result(self):
        if not isinstance(self._export_data, dict):
            return None
        result = self._export_data.get("linearity_traverse")
        if not isinstance(result, dict):
            return None
        if not (result.get("linearity") or {}).get("auto_best"):
            return None
        if not result.get("groups") or result.get("best_index") is None:
            return None
        if not (result.get("auto_search") or {}).get("evaluated_values"):
            return None
        return result

    def _can_export_search_gif(self):
        runtime = self._search_gif_runtime()
        if self.is_test_running or runtime["state"] != "idle":
            return False
        result = self._auto_best_export_result()
        if result is None:
            return False
        try:
            build_linearity_auto_search_timeline(result)
        except (KeyError, TypeError, ValueError):
            return False
        return True

    def _refresh_search_gif_export_ui(self):
        button = getattr(self, "export_search_gif_btn", None)
        if button is None:
            return
        state = self._search_gif_runtime()["state"]
        if state == "idle":
            button.setText("Export Search GIF")
            button.setEnabled(self._can_export_search_gif())
        elif state == "stopping":
            button.setText("Stopping GIF Export...")
            button.setEnabled(False)
        else:
            button.setText("Stop GIF Export")
            button.setEnabled(state in ("rendering", "encoding"))

    def export_search_gif(self):
        runtime = self._search_gif_runtime()
        if runtime["state"] != "idle":
            self._stop_search_gif_export()
            return False
        result = self._auto_best_export_result()
        if result is None or self.is_test_running:
            self._append_log("[WARN] No completed Auto Best result available for GIF export.")
            return False
        try:
            renderer = SearchGifFrameRenderer(result)
        except Exception as exc:
            logger.error("Unable to prepare Auto Best GIF", exc_info=True)
            self._append_log(f"[ERROR] Unable to prepare Auto Best GIF: {exc}")
            return False

        chip, channel, case = self._naming_fields()

        def _safe(text):
            return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text).strip() or "UNKNOWN"

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = (
            f"GPADC_AutoBestSearch_{_safe(chip)}_{_safe(channel)}_{_safe(case)}_{timestamp}.gif"
        )
        output = Path(__file__).resolve().parents[5] / "Results" / filename
        timer = QTimer(self)
        timer.setInterval(0)
        timer.timeout.connect(self._render_next_search_gif_frame)
        runtime.update({
            "state": "rendering", "timer": timer, "renderer": renderer,
            "index": 0, "frames": [], "output": output,
            "thread": None, "worker": None,
        })
        self._append_log(f"[INFO] Rendering Auto Best search GIF: {len(renderer)} frames")
        self._refresh_search_gif_export_ui()
        timer.start()
        return True

    def _render_next_search_gif_frame(self):
        runtime = self._search_gif_runtime()
        if runtime["state"] != "rendering":
            return
        try:
            index = runtime["index"]
            runtime["frames"].append(runtime["renderer"].render_event(index))
            runtime["index"] = index + 1
            if runtime["index"] < len(runtime["renderer"]):
                return
            runtime["timer"].stop()
            self._start_search_gif_encoding()
        except Exception as exc:
            logger.error("Auto Best GIF frame rendering failed", exc_info=True)
            self._append_log(f"[ERROR] Auto Best GIF frame rendering failed: {exc}")
            self._reset_search_gif_export()

    def _start_search_gif_encoding(self):
        runtime = self._search_gif_runtime()
        runtime["state"] = "encoding"
        thread = QThread()
        worker = TestWorker(
            encode_search_gif_frames,
            {"frames": runtime["frames"], "output_path": runtime["output"]},
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_search_gif_finished)
        worker.error.connect(self._on_search_gif_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_search_gif_thread_finished)
        runtime["thread"] = thread
        runtime["worker"] = worker
        self._append_log("[INFO] Encoding Auto Best search GIF in background...")
        self._refresh_search_gif_export_ui()
        thread.start()

    def _on_search_gif_finished(self, result):
        runtime = self._search_gif_runtime()
        runtime["state"] = "finishing"
        if result.get("saved"):
            self._append_log(f"[INFO] Auto Best search GIF exported to: {result['path']}")
            self.set_system_status("Auto Best search GIF exported")
        else:
            self._append_log("[INFO] Auto Best search GIF export stopped.")
        self._refresh_search_gif_export_ui()

    def _on_search_gif_error(self, message):
        runtime = self._search_gif_runtime()
        runtime["state"] = "finishing"
        logger.error("Auto Best GIF encoding failed: %s", message, exc_info=True)
        self._append_log(f"[ERROR] Auto Best GIF encoding failed: {message}")
        self.set_system_status("Auto Best GIF export failed", is_error=True)
        self._refresh_search_gif_export_ui()

    def _on_search_gif_thread_finished(self):
        self._reset_search_gif_export()

    def _reset_search_gif_export(self):
        runtime = self._search_gif_runtime()
        timer = runtime.get("timer")
        if timer is not None:
            timer.stop()
            timer.deleteLater()
        runtime.update({
            "state": "idle", "timer": None, "renderer": None,
            "index": 0, "frames": [], "output": None,
            "thread": None, "worker": None,
        })
        self._refresh_search_gif_export_ui()

    def _stop_search_gif_export(self):
        runtime = self._search_gif_runtime()
        state = runtime["state"]
        if state == "rendering":
            self._append_log("[INFO] Auto Best search GIF export stopped during rendering.")
            self._reset_search_gif_export()
        elif state == "encoding":
            runtime["state"] = "stopping"
            worker = runtime.get("worker")
            if worker is not None:
                worker.request_stop()
            self._refresh_search_gif_export_ui()

    def _cleanup_search_gif_export(self):
        runtime = self._search_gif_runtime()
        timer = runtime.get("timer")
        if timer is not None:
            timer.stop()
        worker = runtime.get("worker")
        if worker is not None:
            worker.request_stop()

    def export_result(self):
        import openpyxl
        from openpyxl.styles import (Font, PatternFill, Alignment,
                                     Border, Side)
        from openpyxl.utils import get_column_letter
        from pathlib import Path
        import datetime

        if self._export_data is None:
            self._append_log("[WARN] No test result to export.")
            return

        # 多通道高低温测试：每通道一个 sheet 的专用导出
        if 'multi_ch_temp' in self._export_data:
            self._export_multi_ch_temp(self._export_data['multi_ch_temp'])
            return

        # FT Calibration Check：校准汇总 + 逐点数据的专用导出
        if 'ft_calib' in self._export_data:
            self._export_ft_calib(self._export_data['ft_calib'])
            return

        if 'linearity_traverse' in self._export_data:
            self._export_linearity_traverse(self._export_data['linearity_traverse'])
            return

        params   = self._export_data['params']
        raw      = self._export_data['raw']
        calib    = self._export_data['calibration']

        results_dir = Path(__file__).parent.parent.parent.parent / "Results"
        results_dir.mkdir(exist_ok=True)

        ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = results_dir / f"GPADC_Result_{ts}.xlsx"

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "GPADC Result"

        hdr_fill   = PatternFill("solid", fgColor="0A1735")
        hdr_font   = Font(bold=True, color="00D39A", size=11)
        val_font   = Font(color="000000", size=10)
        sub_fill   = PatternFill("solid", fgColor="0D1F40")
        sub_font   = Font(bold=True, color="7E96BF", size=10)
        thin_side  = Side(style="thin", color="1B2847")
        thin_border = Border(left=thin_side, right=thin_side,
                             top=thin_side, bottom=thin_side)

        def _hdr(ws, row, col, text):
            c = ws.cell(row=row, column=col, value=text)
            c.fill = hdr_fill
            c.font = hdr_font
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = thin_border
            return c

        def _val(ws, row, col, value):
            c = ws.cell(row=row, column=col, value=value)
            c.font = val_font
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = thin_border
            if isinstance(value, float):
                c.number_format = "0.000000"
            return c

        def _sub(ws, row, col, text):
            c = ws.cell(row=row, column=col, value=text)
            c.fill = sub_fill
            c.font = sub_font
            c.alignment = Alignment(horizontal="left", vertical="center")
            c.border = thin_border
            return c

        ws.column_dimensions["A"].width = 22
        ws.column_dimensions["B"].width = 18
        ws.column_dimensions["C"].width = 22
        ws.column_dimensions["D"].width = 18

        row = 1
        _hdr(ws, row, 1, "GPADC ADC Parameters")
        ws.merge_cells(start_row=row, start_column=1,
                       end_row=row, end_column=4)
        row += 1

        param_items = [
            ("Linearity (R²)",   params.get("linearity",    0.0)),
            ("INL (LSB)",        params.get("inl",          0.0)),
            ("DNL (LSB)",        params.get("dnl",          0.0)),
            ("ENOB (bits)",      params.get("enob",         0.0)),
            ("Gain Error (%)",   params.get("gain_error",   0.0)),
            ("Offset Error (LSB)", params.get("offset_error", 0.0)),
        ]
        _sub(ws, row, 1, "Parameter")
        _sub(ws, row, 2, "Value")
        _sub(ws, row, 3, "Parameter")
        _sub(ws, row, 4, "Value")
        row += 1
        for i in range(0, len(param_items), 2):
            _val(ws, row, 1, param_items[i][0])
            _val(ws, row, 2, param_items[i][1])
            if i + 1 < len(param_items):
                _val(ws, row, 3, param_items[i + 1][0])
                _val(ws, row, 4, param_items[i + 1][1])
            row += 1

        row += 1

        chart_data_start_row = row
        _hdr(ws, row, 1, "Chart Data")
        ws.merge_cells(start_row=row, start_column=1,
                       end_row=row, end_column=4)
        row += 1
        _sub(ws, row, 1, "Input Voltage (V)")
        _sub(ws, row, 2, "Mean Cali (V)")
        _sub(ws, row, 3, "Min Cali (V)")
        _sub(ws, row, 4, "Max Cali (V)")
        row += 1
        chart_data_body_start = row
        v_list   = calib['voltage']
        mc_list  = calib['mean_cali']
        mn_list  = calib['min_cali']
        mx_list  = calib['max_cali']
        for i in range(len(v_list)):
            _val(ws, row, 1, float(v_list[i]))
            _val(ws, row, 2, float(mc_list[i]))
            _val(ws, row, 3, float(mn_list[i]))
            _val(ws, row, 4, float(mx_list[i]))
            row += 1
        chart_data_end = row - 1

        chart_anchor_col = get_column_letter(6)
        if self._chart_image_bytes is not None:
            try:
                from openpyxl.drawing.image import Image as XLImage
                self._chart_image_bytes.seek(0)
                img = XLImage(self._chart_image_bytes)
                img.width  = 600
                img.height = 350
                ws.add_image(img, f"{chart_anchor_col}{chart_data_start_row}")
            except Exception as ex:
                self._append_log(f"[WARN] Embed chart image failed: {ex}")
                self._embed_native_chart(ws, chart_data_start_row, chart_data_body_start,
                                         chart_data_end, chart_anchor_col)
        else:
            self._embed_native_chart(ws, chart_data_start_row, chart_data_body_start,
                                     chart_data_end, chart_anchor_col)

        row += 2

        current_list = raw.get('current_a')
        current_channel = raw.get('current_channel')
        has_current = current_list is not None and current_channel is not None
        raw_data_columns = 5 if has_current else 4
        _hdr(ws, row, 1, "Raw Data")
        ws.merge_cells(start_row=row, start_column=1,
                       end_row=row, end_column=raw_data_columns)
        row += 1
        _sub(ws, row, 1, "Input Voltage (V)")
        _sub(ws, row, 2, "ADC Mean (LSB)")
        _sub(ws, row, 3, "ADC Min (LSB)")
        _sub(ws, row, 4, "ADC Max (LSB)")
        if has_current:
            _sub(ws, row, 5, f"CH{current_channel} Current (A)")
            ws.column_dimensions["E"].width = 20
        row += 1
        rv_list  = raw['voltage']
        rm_list  = raw['mean']
        rn_list  = raw['min']
        rx_list  = raw['max']
        for i in range(len(rv_list)):
            _val(ws, row, 1, float(rv_list[i]))
            _val(ws, row, 2, float(rm_list[i]))
            _val(ws, row, 3, float(rn_list[i]))
            _val(ws, row, 4, float(rx_list[i]))
            if has_current:
                _val(ws, row, 5, float(current_list[i]))
            row += 1

        row += 2

        _hdr(ws, row, 1, "Calibrated Data")
        ws.merge_cells(start_row=row, start_column=1,
                       end_row=row, end_column=4)
        row += 1
        _sub(ws, row, 1, "Input Voltage (V)")
        _sub(ws, row, 2, "Mean Cali (V)")
        _sub(ws, row, 3, "Min Cali (V)")
        _sub(ws, row, 4, "Max Cali (V)")
        row += 1
        for i in range(len(v_list)):
            _val(ws, row, 1, float(v_list[i]))
            _val(ws, row, 2, float(mc_list[i]))
            _val(ws, row, 3, float(mn_list[i]))
            _val(ws, row, 4, float(mx_list[i]))
            row += 1

        wb.save(str(filename))
        self._append_log(f"[INFO] Result exported to: {filename}")

    def _embed_native_chart(self, ws, chart_data_start_row, chart_data_body_start,
                            chart_data_end, chart_anchor_col):
        from openpyxl.chart import LineChart, Reference
        chart = LineChart()
        chart.title        = "ADC Transfer Curve (Calibrated)"
        chart.style        = 10
        chart.y_axis.title = "Calibrated Voltage (V)"
        chart.x_axis.title = "Input Voltage (V)"
        chart.width        = 22
        chart.height       = 14
        ref_x    = Reference(ws, min_col=1, min_row=chart_data_body_start, max_row=chart_data_end)
        ref_mean = Reference(ws, min_col=2, min_row=chart_data_body_start - 1, max_row=chart_data_end)
        ref_min  = Reference(ws, min_col=3, min_row=chart_data_body_start - 1, max_row=chart_data_end)
        ref_max  = Reference(ws, min_col=4, min_row=chart_data_body_start - 1, max_row=chart_data_end)
        chart.add_data(ref_mean, titles_from_data=True)
        chart.add_data(ref_min,  titles_from_data=True)
        chart.add_data(ref_max,  titles_from_data=True)
        chart.set_categories(ref_x)
        chart.series[0].graphicalProperties.line.solidFill = "00D39A"
        chart.series[0].graphicalProperties.line.width     = 20000
        chart.series[1].graphicalProperties.line.solidFill = "F0A040"
        chart.series[2].graphicalProperties.line.solidFill = "F0A040"
        ws.add_chart(chart, f"{chart_anchor_col}{chart_data_start_row}")

    def _export_linearity_traverse(self, result):
        """导出 Linearity Traverse 汇总、各组指标及逐点 Error 数据。"""
        import datetime
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        results_dir = Path(__file__).resolve().parents[5] / "Results"
        results_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = results_dir / f"GPADC_LinearityTraverse_{ts}.xlsx"

        hdr_fill = PatternFill("solid", fgColor="0A1735")
        hdr_font = Font(bold=True, color="00D39A", size=11)
        sub_fill = PatternFill("solid", fgColor="0D1F40")
        sub_font = Font(bold=True, color="7E96BF", size=10)
        best_fill = PatternFill("solid", fgColor="D9EAD3")

        def _header(ws, row, col, text):
            cell = ws.cell(row=row, column=col, value=text)
            cell.fill = hdr_fill
            cell.font = hdr_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            return cell

        def _sub(ws, row, col, text):
            cell = ws.cell(row=row, column=col, value=text)
            cell.fill = sub_fill
            cell.font = sub_font
            cell.alignment = Alignment(horizontal="left", vertical="center")
            return cell

        def _value(ws, row, col, value, best=False):
            cell = ws.cell(row=row, column=col, value=value)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            if isinstance(value, float):
                cell.number_format = "0.000000"
            if best:
                cell.fill = best_fill
                cell.font = Font(bold=True, color="006100")
            return cell

        groups = result.get('groups') or []
        best_index = result.get('best_index')
        best = groups[best_index] if best_index is not None else {}
        linearity = result.get('linearity') or {}
        auto_best = bool(linearity.get('auto_best'))
        auto_search = result.get('auto_search') or {}
        strategy = auto_search.get('strategy') or 'unimodal'
        strategy_label = {
            'coarse_fine': "Coarse + Fine (Multi-Basin)",
            'unimodal': "Unimodal (Fast)",
        }.get(strategy, "Unimodal (Fast)")

        def _format_hex_values(values):
            return ", ".join(f"0x{int(value):X}" for value in values or [])

        def _format_neighborhoods(neighborhoods):
            return ", ".join(
                f"0x{int(start):X}-0x{int(end):X}"
                for start, end in neighborhoods or []
            )

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Summary"
        _header(ws, 1, 1, "Linearity Traverse Summary")
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=11 if auto_best else 7)
        summary_items = [
            ("N Weight Register", f"0x{linearity.get('n_reg_addr', 0):X}"),
            ("P Weight Register", f"0x{linearity.get('p_reg_addr', 0):X}"),
            ("Original N", f"0x{result.get('original_n', 0):X}"),
            ("Original P", f"0x{result.get('original_p', 0):X}"),
            ("Mode", "Link N = P" if linearity.get('link_np') else "Independent N/P Matrix"),
        ]
        if linearity.get('link_np'):
            summary_items.extend([
                ("Shared Start (LSB)", linearity.get('start')),
                ("Shared End (LSB)", linearity.get('end')),
                ("Shared Start (Value)", linearity.get('value_start')),
                ("Shared End (Value)", linearity.get('value_end')),
                ("Shared Step (Value)", "Auto (Disabled)" if auto_best else linearity.get('value_step')),
            ])
        else:
            summary_items.extend([
                ("N Start (LSB)", linearity.get('n_start')),
                ("N End (LSB)", linearity.get('n_end')),
                ("N Start (Value)", linearity.get('n_value_start')),
                ("N End (Value)", linearity.get('n_value_end')),
                ("N Step (Value)", linearity.get('n_value_step')),
                ("P Start (LSB)", linearity.get('p_start')),
                ("P End (LSB)", linearity.get('p_end')),
                ("P Start (Value)", linearity.get('p_value_start')),
                ("P End (Value)", linearity.get('p_value_end')),
                ("P Step (Value)", linearity.get('p_value_step')),
            ])
        if auto_best:
            auto_items = [
                ("Auto Best", strategy_label),
                ("Repeat (Runs)", linearity.get('auto_repeat')),
                ("Evaluated Values", _format_hex_values(auto_search.get('evaluated_values'))),
                ("Search Ambiguous", bool(auto_search.get('ambiguous'))),
            ]
            stage_items = []
            if strategy == 'coarse_fine':
                stage_items.extend([
                    ("Coarse Values", _format_hex_values(auto_search.get('coarse_values'))),
                    ("Fine Values", _format_hex_values(auto_search.get('fine_values'))),
                    ("Neighborhoods", _format_neighborhoods(auto_search.get('neighborhoods'))),
                    ("Finalist Values", _format_hex_values(auto_search.get('finalist_values'))),
                ])
            elif auto_search.get('finalist_values'):
                stage_items.append((
                    "Finalist Values", _format_hex_values(auto_search.get('finalist_values')),
                ))
            summary_items[5:5] = auto_items + stage_items
        summary_items.extend([
            ("Best N", f"0x{best.get('n_value', 0):X}"),
            ("Best P", f"0x{best.get('p_value', 0):X}"),
            ("Best Max Abs Error (mV)", best.get('max_abs_mv')),
            ("Best RMS Error (mV)", best.get('rms_mv')),
            ("Completed Groups", len(groups)),
            ("Total Sweeps", sum(group.get('repeat_count', 1) for group in groups)),
            ("Stopped", bool(result.get('stopped'))),
        ])
        row = 2
        for name, value in summary_items:
            _sub(ws, row, 1, name)
            _value(ws, row, 2, value)
            row += 1

        row += 1
        headers = ("N Weight", "P Weight", "K (LSB/V)", "B (LSB)",
                   "Max Abs Error (mV)", "RMS Error (mV)", "Result")
        if auto_best:
            headers += ("Repeat", "Representative", "Max Abs Range (mV)", "RMS Range (mV)")
        for col, name in enumerate(headers, 1):
            _header(ws, row, col, name)
        row += 1
        for index, group in enumerate(groups):
            is_best = index == best_index
            values = (
                f"0x{group['n_value']:X}", f"0x{group['p_value']:X}",
                group['k'], group['b'], group['max_abs_mv'], group['rms_mv'],
                "BEST" if is_best else "",
            )
            if auto_best:
                values += (
                    group.get('repeat_count', 1), group.get('representative_repeat', 1),
                    group.get('max_abs_range_mv'), group.get('rms_range_mv'),
                )
            for col, value in enumerate(values, 1):
                _value(ws, row, col, value, best=is_best)
            row += 1

        widths = (28, 20, 20, 20, 22, 20, 14)
        if auto_best:
            widths += (12, 18, 22, 20)
        for col, width in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(col)].width = width

        if self._chart_image_bytes is not None:
            from openpyxl.drawing.image import Image as XLImage
            self._chart_image_bytes.seek(0)
            image = XLImage(self._chart_image_bytes)
            image.width = 600
            image.height = 350
            ws.add_image(image, "M2" if auto_best else "H2")

        sweep_ws = wb.create_sheet("Sweep Data")
        sweep_headers = ("N Weight", "P Weight", "Input Voltage (V)",
                         "ADC Mean (LSB)", "Mean Cali (V)", "Error (mV)")
        if auto_best:
            sweep_headers += (
                "Repeat", "Representative", "Repeat Max Abs Error (mV)",
                "Repeat RMS Error (mV)",
            )
        for col, name in enumerate(sweep_headers, 1):
            _header(sweep_ws, 1, col, name)
            sweep_ws.column_dimensions[get_column_letter(col)].width = 22
        row = 2
        for group in groups:
            repeat_groups = (group.get('repeat_results') or [group]) if auto_best else [group]
            representative = group.get('representative_repeat', 1)
            for repeat_group in repeat_groups:
                raw = repeat_group.get('raw') or {}
                voltage = raw.get('voltage') or result.get('voltage') or []
                raw_mean = raw.get('mean') or []
                mean_cali = repeat_group.get('mean_cali') or []
                error_mv = repeat_group.get('error_mv') or []
                count = min(len(voltage), len(raw_mean), len(mean_cali), len(error_mv))
                for index in range(count):
                    values = (
                        f"0x{group['n_value']:X}", f"0x{group['p_value']:X}",
                        float(voltage[index]), float(raw_mean[index]),
                        float(mean_cali[index]), float(error_mv[index]),
                    )
                    if auto_best:
                        repeat_index = repeat_group.get('repeat_index', 1)
                        values += (
                            repeat_index,
                            "YES" if repeat_index == representative else "",
                            repeat_group.get('max_abs_mv'), repeat_group.get('rms_mv'),
                        )
                    for col, value in enumerate(values, 1):
                        _value(sweep_ws, row, col, value)
                    row += 1

        wb.save(str(filename))
        self._append_log(f"[INFO] Linearity Traverse result exported to: {filename}")

    def _export_ft_calib(self, result):
        """FT Calibration Check 导出：Summary（K/B + 校准点确认 + 误差统计 + 判定）+ Sweep Data。"""
        import openpyxl
        from openpyxl.styles import (Font, PatternFill, Alignment,
                                     Border, Side)
        from openpyxl.utils import get_column_letter
        from pathlib import Path
        import datetime

        results_dir = Path(__file__).parent.parent.parent.parent / "Results"
        results_dir.mkdir(exist_ok=True)

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = results_dir / f"GPADC_FT_CalibCheck_{ts}.xlsx"

        hdr_fill = PatternFill("solid", fgColor="0A1735")
        hdr_font = Font(bold=True, color="00D39A", size=11)
        val_font = Font(color="000000", size=10)
        sub_fill = PatternFill("solid", fgColor="0D1F40")
        sub_font = Font(bold=True, color="7E96BF", size=10)
        thin_side = Side(style="thin", color="1B2847")
        thin_border = Border(left=thin_side, right=thin_side,
                             top=thin_side, bottom=thin_side)

        def _hdr(ws, row, col, text):
            c = ws.cell(row=row, column=col, value=text)
            c.fill = hdr_fill
            c.font = hdr_font
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = thin_border
            return c

        def _val(ws, row, col, value):
            c = ws.cell(row=row, column=col, value=value)
            c.font = val_font
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = thin_border
            if isinstance(value, float):
                c.number_format = "0.000000"
            return c

        def _sub(ws, row, col, text):
            c = ws.cell(row=row, column=col, value=text)
            c.fill = sub_fill
            c.font = sub_font
            c.alignment = Alignment(horizontal="left", vertical="center")
            c.border = thin_border
            return c

        mode = result.get('mode', '')
        stats = result.get('stats') or {}
        cons_stats = result.get('cons_stats')
        (v1, c1), (v2, c2) = result.get('calib_points') or [(0.0, 0.0), (0.0, 0.0)]

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Summary"
        ws.column_dimensions["A"].width = 26
        ws.column_dimensions["B"].width = 20

        row = 1
        _hdr(ws, row, 1, "FT Calibration Check Summary")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        row += 1
        summary_items = [
            ("Mode", mode),
            ("K (LSB/V)", result.get('k')),
            ("B (LSB)", result.get('b')),
            ("Calib Point 1 (V)", v1),
            ("Calib Raw 1 (LSB)", c1),
            ("Calib Point 2 (V)", v2),
            ("Calib Raw 2 (LSB)", c2),
            ("Raw Tol (±LSB)", result.get('raw_tol_lsb')),
            ("Error Limit (±mV)", result.get('err_limit_mv')),
            ("Divider Ratio (×)", result.get('divider_ratio')),
        ]
        for name, value in summary_items:
            _sub(ws, row, 1, name)
            _val(ws, row, 2, value)
            row += 1

        point_checks = result.get('point_checks') or []
        if point_checks:
            row += 1
            _hdr(ws, row, 1, "Calib Point Check (IIC)")
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
            row += 1
            for col, name in enumerate(
                    ("Voltage (V)", "Set Voltage (V)", "Calib Code (LSB)",
                     "Measured (LSB)", "Dev (LSB)", "Result"), 1):
                _sub(ws, row, col, name)
            row += 1
            for pc in point_checks:
                _val(ws, row, 1, pc.get('voltage'))
                _val(ws, row, 2, pc.get('set_voltage'))
                _val(ws, row, 3, pc.get('calib_code'))
                _val(ws, row, 4, pc.get('measured'))
                _val(ws, row, 5, pc.get('dev_lsb'))
                _val(ws, row, 6, "PASS" if pc.get('passed') else "FAIL")
                row += 1

        row += 1
        _hdr(ws, row, 1, "Error Statistics")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        row += 1
        stat_items = [
            ("Max Abs Error (mV)", stats.get('max_abs_mv')),
            ("Avg Error (mV)", stats.get('avg_mv')),
            ("RMS Error (mV)", stats.get('rms_mv')),
            ("Sweep Points", stats.get('count')),
        ]
        if cons_stats is not None:
            stat_items.extend([
                ("Cons Max Abs (mV)", cons_stats.get('max_abs_mv')),
                ("Cons Avg (mV)", cons_stats.get('avg_mv')),
                ("Cons RMS (mV)", cons_stats.get('rms_mv')),
            ])
        stat_items.append(("Verdict", "PASS" if result.get('passed') else "FAIL"))
        for name, value in stat_items:
            _sub(ws, row, 1, name)
            _val(ws, row, 2, value)
            row += 1

        ws2 = wb.create_sheet("Sweep Data")
        is_uart = mode == 'UART'
        headers = ["Set Voltage (V)", "DUT Voltage (V)", "Raw Mean (LSB)",
                   "Calib Voltage (V)", "Error (mV)"]
        if is_uart:
            headers += ["DUT Volt (mV)", "Consistency (mV)"]
        for col, name in enumerate(headers, 1):
            _sub(ws2, row=1, col=col, text=name)
            ws2.column_dimensions[get_column_letter(col)].width = 20
        voltage = result.get('voltage') or []
        actual_voltage = result.get('actual_voltage') or voltage
        raw_mean = result.get('raw_mean') or []
        cal_volt = result.get('cal_volt') or []
        err_mv = result.get('err_mv') or []
        dut_volt = result.get('dut_volt_mv') or []
        cons_mv = result.get('cons_mv') or []
        for i in range(len(voltage)):
            r = i + 2
            _val(ws2, r, 1, float(voltage[i]))
            _val(ws2, r, 2, float(actual_voltage[i]))
            _val(ws2, r, 3, float(raw_mean[i]))
            _val(ws2, r, 4, float(cal_volt[i]))
            _val(ws2, r, 5, float(err_mv[i]))
            if is_uart:
                _val(ws2, r, 6, float(dut_volt[i]))
                _val(ws2, r, 7, float(cons_mv[i]))

        wb.save(filename)
        self._append_log(f"[INFO] FT Calibration Check 结果已导出: {filename}")

    def _export_multi_ch_temp(self, result):
        """多通道高低温测试导出：Summary 汇总 + 每通道一个 sheet（原始 + 标定数据）。"""
        import openpyxl
        from openpyxl.styles import (Font, PatternFill, Alignment,
                                     Border, Side)
        from openpyxl.utils import get_column_letter
        from pathlib import Path
        import datetime
        import re

        results_dir = Path(__file__).parent.parent.parent.parent / "Results"
        results_dir.mkdir(exist_ok=True)

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = results_dir / f"GPADC_MultiChTemp_{ts}.xlsx"

        hdr_fill = PatternFill("solid", fgColor="0A1735")
        hdr_font = Font(bold=True, color="00D39A", size=11)
        val_font = Font(color="000000", size=10)
        sub_fill = PatternFill("solid", fgColor="0D1F40")
        sub_font = Font(bold=True, color="7E96BF", size=10)
        thin_side = Side(style="thin", color="1B2847")
        thin_border = Border(left=thin_side, right=thin_side,
                             top=thin_side, bottom=thin_side)

        def _hdr(ws, row, col, text):
            c = ws.cell(row=row, column=col, value=text)
            c.fill = hdr_fill
            c.font = hdr_font
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = thin_border
            return c

        def _val(ws, row, col, value):
            c = ws.cell(row=row, column=col, value=value)
            c.font = val_font
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = thin_border
            if isinstance(value, float):
                c.number_format = "0.000000"
            return c

        def _sub(ws, row, col, text):
            c = ws.cell(row=row, column=col, value=text)
            c.fill = sub_fill
            c.font = sub_font
            c.alignment = Alignment(horizontal="left", vertical="center")
            c.border = thin_border
            return c

        temp_list = result.get('temp') or []
        channels = result.get('channels') or []

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Summary"
        ws.column_dimensions["A"].width = 26
        ws.column_dimensions["B"].width = 20
        ws.column_dimensions["C"].width = 22
        ws.column_dimensions["D"].width = 22

        row = 1
        _hdr(ws, row, 1, "GPADC Multi-Ch Temp Test Summary")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        row += 1
        meta_items = [
            ("Test Time", ts),
            ("Temp Range (°C)", f"{temp_list[0]:.1f} ~ {temp_list[-1]:.1f}" if temp_list else "N/A"),
            ("Temp Points", len(temp_list)),
            ("Points", result.get('points', result.get('sample_cnt', 0))),
            ("Channel Count", len(channels)),
        ]
        for key, value in meta_items:
            _sub(ws, row, 1, key)
            _val(ws, row, 2, value)
            row += 1

        row += 1
        _hdr(ws, row, 1, "Channels")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        row += 1
        for col, text in enumerate(("Name", "Sweep", "Voltage Range (V)", "Data Rows"), start=1):
            _sub(ws, row, col, text)
        row += 1
        for ch in channels:
            _val(ws, row, 1, ch.get('name') or "CH")
            _val(ws, row, 2, "Yes" if ch.get('sweep') else "No")
            if ch.get('sweep'):
                vpts = ch.get('voltage') or []
                vrange = f"{vpts[0]:.3f} ~ {vpts[-1]:.3f}" if vpts else "N/A"
            else:
                vrange = "(fixed-point)"
            _val(ws, row, 3, vrange)
            _val(ws, row, 4, len(ch.get('mean') or []))
            row += 1

        if self._chart_image_bytes is not None:
            try:
                from openpyxl.drawing.image import Image as XLImage
                self._chart_image_bytes.seek(0)
                img = XLImage(self._chart_image_bytes)
                img.width = 720
                img.height = 420
                ws.add_image(img, f"{get_column_letter(6)}1")
            except Exception as ex:
                self._append_log(f"[WARN] Embed chart image failed: {ex}")

        for ch in channels:
            ch_name = ch.get('name') or "CH"
            sheet_name = re.sub(r"[\[\]:*?/\\]", "_", f"CH_{ch_name}")[:31]
            ws = wb.create_sheet(sheet_name)
            for col_idx in range(1, 12):
                ws.column_dimensions[get_column_letter(col_idx)].width = 14

            row = 1
            _hdr(ws, row, 1, f"Channel: {ch_name} ({'voltage sweep' if ch.get('sweep') else 'fixed-point'})")
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
            row += 2

            if ch.get('sweep'):
                vpts = ch.get('voltage') or []
                matrices = [("Mean (LSB)", ch.get('mean') or []),
                            ("Min (LSB)", ch.get('min') or []),
                            ("Max (LSB)", ch.get('max') or [])]
                if ch.get('mean_cali'):
                    matrices.append(("Mean Cali (V)", ch['mean_cali']))
                for tag, matrix in matrices:
                    _hdr(ws, row, 1, tag)
                    ws.merge_cells(start_row=row, start_column=1,
                                   end_row=row, end_column=max(2, len(vpts) + 1))
                    row += 1
                    _sub(ws, row, 1, "Temp \\ Voltage (V)")
                    for j, v in enumerate(vpts):
                        _sub(ws, row, 2 + j, f"{v:.3f}")
                    row += 1
                    for i, t in enumerate(temp_list):
                        if i >= len(matrix):
                            break
                        _val(ws, row, 1, f"{t:.1f}")
                        for j in range(len(matrix[i])):
                            _val(ws, row, 2 + j, float(matrix[i][j]))
                        row += 1
                    row += 1
            else:
                _sub(ws, row, 1, "Temp (°C)")
                _sub(ws, row, 2, "ADC Mean (LSB)")
                _sub(ws, row, 3, "ADC Min (LSB)")
                _sub(ws, row, 4, "ADC Max (LSB)")
                row += 1
                mean_list = ch.get('mean') or []
                min_list = ch.get('min') or []
                max_list = ch.get('max') or []
                for i in range(len(mean_list)):
                    t = temp_list[i] if i < len(temp_list) else i
                    _val(ws, row, 1, float(t))
                    _val(ws, row, 2, float(mean_list[i]))
                    if i < len(min_list):
                        _val(ws, row, 3, float(min_list[i]))
                    if i < len(max_list):
                        _val(ws, row, 4, float(max_list[i]))
                    row += 1

        wb.save(str(filename))
        self._append_log(f"[INFO] Result exported to: {filename}")

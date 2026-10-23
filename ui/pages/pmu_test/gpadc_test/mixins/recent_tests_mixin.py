"""GPADCTestUI Recent 记录 / 自动命名 / 对比 Mixin。

从 ui/pages/pmu_test/gpadc_test_ui.py 平移而来，行为零变更。
类装配见 gpadc_test_ui.py。"""

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QGridLayout,
    QFrame, QButtonGroup, QSizePolicy, QListWidget, QListWidgetItem,
    QAbstractItemView, QMenu, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QAction
import datetime
from core.pmu_test.gpadc import describe_algorithm


class _RecentTestsMixin:
    """Recent 记录 / 自动命名 / 对比 Mixin"""

    def _create_recent_tests_panel(self):
        """Curve 右侧最近测试管理栏：列表 + Curve View 选项 + 对比/载入/清空。"""
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        panel.setMinimumWidth(220)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        title = QLabel("Recent Tests")
        title.setObjectName("section_title")
        title.setStyleSheet("border: none;")
        title_row.addWidget(title)
        title_row.addStretch()

        self.compare_recent_btn = QPushButton("Compare")
        self.compare_recent_btn.setObjectName("tool_btn")
        self.compare_recent_btn.setToolTip("对比勾选的多条测试记录曲线")
        self.load_recent_btn = QPushButton("Load")
        self.load_recent_btn.setObjectName("tool_btn")
        self.load_recent_btn.setToolTip("载入勾选记录的曲线与指标")
        self.clear_recent_btn = QPushButton("Clear")
        self.clear_recent_btn.setObjectName("tool_btn")
        self.clear_recent_btn.setToolTip("清空最近测试记录")

        title_row.addWidget(self.compare_recent_btn)
        title_row.addWidget(self.load_recent_btn)
        title_row.addWidget(self.clear_recent_btn)
        layout.addLayout(title_row)

        # 测试命名：芯片 / 通道 / CASE 组合 + 组合内自动递增序号
        naming_title = QLabel("Test Naming")
        naming_title.setObjectName("section_title")
        naming_title.setStyleSheet("border: none;")
        naming_title.setToolTip("测试完成后按 芯片_通道_CASE_序号 自动命名，序号在相同组合内自动递增")
        layout.addWidget(naming_title)

        naming_grid = QGridLayout()
        naming_grid.setContentsMargins(0, 0, 0, 0)
        naming_grid.setHorizontalSpacing(6)
        naming_grid.setVerticalSpacing(4)

        chip_label = QLabel("Chip")
        chip_label.setObjectName("muted_label")
        naming_grid.addWidget(chip_label, 0, 0, 1, 2)
        self.naming_chip_edit = QLineEdit("BES")
        self.naming_chip_edit.setPlaceholderText("芯片名")
        self.naming_chip_edit.setToolTip("芯片名（用于自动命名）")
        naming_grid.addWidget(self.naming_chip_edit, 1, 0, 1, 2)

        channel_label = QLabel("Channel")
        channel_label.setObjectName("muted_label")
        naming_grid.addWidget(channel_label, 2, 0)
        case_label = QLabel("CASE")
        case_label.setObjectName("muted_label")
        naming_grid.addWidget(case_label, 2, 1)
        self.naming_channel_edit = QLineEdit("CH1")
        self.naming_channel_edit.setPlaceholderText("通道名")
        self.naming_channel_edit.setToolTip("通道名（用于自动命名）")
        naming_grid.addWidget(self.naming_channel_edit, 3, 0)
        self.naming_case_edit = QLineEdit("CASE1")
        self.naming_case_edit.setPlaceholderText("用例名")
        self.naming_case_edit.setToolTip("CASE 用例名（用于自动命名）")
        naming_grid.addWidget(self.naming_case_edit, 3, 1)

        layout.addLayout(naming_grid)

        self.naming_preview_label = QLabel()
        self.naming_preview_label.setObjectName("recent_hint_label")
        self.naming_preview_label.setWordWrap(True)
        self.naming_preview_label.setToolTip("下一次测试完成时将使用的自动命名（相同组合序号自动递增）")
        layout.addWidget(self.naming_preview_label)
        self._update_naming_preview()

        for edit in (self.naming_chip_edit, self.naming_channel_edit, self.naming_case_edit):
            edit.textEdited.connect(self._update_naming_preview)

        self.recent_test_list = QListWidget()
        self.recent_test_list.setObjectName("recent_test_list")
        self.recent_test_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.recent_test_list.setToolTip(
            "单击选中高亮对应曲线；勾选多条后 Compare 对比；双击载入曲线与指标；右键重命名/删除"
        )
        self.recent_test_list.setContextMenuPolicy(Qt.CustomContextMenu)
        layout.addWidget(self.recent_test_list, 1)

        # Curve View：控制载入/对比图显示哪些曲线（Mean / Min-Max / Error 可组合）
        view_title = QLabel("Curve View")
        view_title.setObjectName("section_title")
        view_title.setStyleSheet("border: none;")
        layout.addWidget(view_title)

        self.curve_view_group = QButtonGroup()
        self.curve_view_group.setExclusive(False)
        self.show_mean_btn = QPushButton("Mean")
        self.show_band_btn = QPushButton("Min-Max")
        self.show_error_btn = QPushButton("Error")
        for btn, name, tip in (
            (self.show_mean_btn, "Mean", "显示均值校准曲线"),
            (self.show_band_btn, "Min-Max", "在主图下方子图显示最大/最小值偏差带（Max/Min - Mean）"),
            (self.show_error_btn, "Error", "仅显示误差曲线（Actual - Ideal，右轴）"),
        ):
            btn.setObjectName("tool_btn")
            btn.setCheckable(True)
            btn.setToolTip(tip)
            self.curve_view_group.addButton(btn)

        self.show_mean_btn.setChecked(True)

        view_row = QHBoxLayout()
        view_row.setSpacing(4)
        view_row.addWidget(self.show_mean_btn)
        view_row.addWidget(self.show_band_btn)
        view_row.addWidget(self.show_error_btn)
        layout.addLayout(view_row)

        hint = QLabel("勾选记录进行对比；双击记录载入曲线与指标")
        hint.setObjectName("recent_hint_label")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        return panel

    def _on_toggle_recent_panel(self, checked: bool):
        """折叠/展开 Curve 右侧 Recent 管理栏（记住展开宽度）。"""
        panel = self.recent_curve_splitter.widget(1)
        if panel is None:
            return
        if checked:
            panel.setVisible(True)
            self.recent_curve_splitter.setSizes(self._recent_panel_sizes)
            self.toggle_recent_btn.setText("Recent ◀")
        else:
            self._recent_panel_sizes = self.recent_curve_splitter.sizes()
            panel.setVisible(False)
            self.toggle_recent_btn.setText("Recent ▶")

    def _naming_fields(self):
        """读取命名三要素（空值回退占位），返回 (chip, channel, case)。"""
        chip = self.naming_chip_edit.text().strip() or "CHIP"
        channel = self.naming_channel_edit.text().strip() or "CH"
        case = self.naming_case_edit.text().strip() or "CASE"
        return chip, channel, case

    def _compose_test_name(self, chip, channel, case, seq):
        """自动命名规则：芯片_通道_CASE_序号（序号三位零填充）。"""
        return f"{chip}_{channel}_{case}_{seq:03d}"

    def _update_naming_preview(self):
        """命名输入变化时刷新下一次测试的预览名。"""
        key = self._naming_fields()
        seq = self._naming_counters.get(key, 0) + 1
        self.naming_preview_label.setText(f"Next: {self._compose_test_name(*key, seq)}")

    def _generate_test_name(self):
        """生成测试名：芯片/通道/CASE 组合内自动递增序号。"""
        key = self._naming_fields()
        self._naming_counters[key] = self._naming_counters.get(key, 0) + 1
        name = self._compose_test_name(*key, self._naming_counters[key])
        self._update_naming_preview()
        return name

    def _record_tooltip(self, record) -> str:
        """记录悬浮提示：测试时间 / 性能参数 / 算法 / 命名信息。"""
        lines = [
            self._record_display_name(record),
            f"测试时间: {record['time'].strftime('%Y-%m-%d %H:%M:%S')}",
            f"测试项: {record['test_item']}",
            f"性能参数: {record.get('summary') or '—'}",
            f"算法: {describe_algorithm(record.get('algorithm'))}",
        ]
        naming = record.get('naming')
        if naming:
            lines.append(f"命名: {naming.get('chip')}/{naming.get('channel')}/{naming.get('case')}")
        return "\n".join(lines)

    def _record_recent_test(self, kind, result):
        """测试完成后记入最近测试列表（result 为 None 时不记录）。"""
        if result is None:
            return
        self._recent_test_seq += 1
        chip, channel, case = self._naming_fields()
        record = {
            'id': self._recent_test_seq,
            'time': datetime.datetime.now(),
            'test_item': self.current_test_item,
            'kind': kind,
            'label': '',
            'name': self._generate_test_name(),
            'naming': {'chip': chip, 'channel': channel, 'case': case},
            'algorithm': self._algorithm_snapshot,
            'params': None,
            'raw': None,
            'calibration': None,
            'summary': "",
        }
        if kind == '1000cnt':
            record['params'] = dict(result)
            record['summary'] = (
                f"AVG={result.get('avg', 0):.3f} STD={result.get('std', 0):.3f} "
                f"P-P={result.get('pp', 0):.0f} N={result.get('count', 0)}"
            )
        elif kind in ('force_voltage', 'high_low_temp'):
            export_data = self._export_data or {}
            record['params'] = export_data.get('params')
            record['raw'] = export_data.get('raw')
            record['calibration'] = export_data.get('calibration')
            params = record['params'] or {}
            record['summary'] = (
                f"INL={params.get('inl', 0.0):.3f} DNL={params.get('dnl', 0.0):.3f} "
                f"ENOB={params.get('enob', 0.0):.3f} R²={params.get('linearity', 0.0):.4f}"
            )
        elif kind == 'multi_ch_temp':
            record['raw'] = result
            temps = result.get('temp') or []
            chs = result.get('channels') or []
            record['summary'] = f"{len(chs)} CH x {len(temps)} T"
        elif kind == 'ft_calib_check':
            record['params'] = (self._export_data or {}).get('params')
            record['raw'] = result
            stats = result.get('stats') or {}
            record['summary'] = (
                f"MaxErr={stats.get('max_abs_mv', 0):.2f}mV "
                f"{'PASS' if result.get('passed') else 'FAIL'}"
            )
        else:  # temp_consistency
            record['raw'] = result
            temps = result.get('temp') or []
            if temps:
                record['summary'] = f"T {temps[0]:.1f}~{temps[-1]:.1f}°C · {len(temps)} rows"
            else:
                record['summary'] = "no data"

        self._recent_test_records.append(record)
        while len(self._recent_test_records) > self.RECENT_TEST_LIMIT:
            self._recent_test_records.pop(0)
        self._refresh_recent_test_list()
        self._append_log(f"[INFO] 已记录最近测试 #{record['id']} {record['name']}：{record['summary']}")

    def _record_color(self, record_id: int) -> str:
        """按记录 id 稳定分配专属曲线颜色（列表装饰、图例、曲线共用）。"""
        return self._COMPARE_PALETTE[record_id % len(self._COMPARE_PALETTE)]

    def _record_display_name(self, record) -> str:
        """记录显示名：优先用户重命名的 label，其次自动命名，最后测试项名。"""
        return record.get('label') or record.get('name') or record['test_item']

    def _refresh_recent_test_list(self):
        # 记忆勾选与选中状态（按 record id），重建列表后恢复
        checked_ids = set()
        for i in range(self.recent_test_list.count()):
            item = self.recent_test_list.item(i)
            if item.checkState() == Qt.Checked:
                rec = item.data(Qt.UserRole)
                if rec is not None:
                    checked_ids.add(rec['id'])
        current_id = self._highlight_record_id
        self.recent_test_list.blockSignals(True)
        self.recent_test_list.clear()
        for record in self._recent_test_records:
            ts = record['time'].strftime("%m-%d %H:%M:%S")
            item = QListWidgetItem(
                f"● #{record['id']} [{ts}] {self._record_display_name(record)} · {record['summary']}"
            )
            color = self._record_color(record['id'])
            item.setForeground(QBrush(QColor(color)))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if record['id'] in checked_ids else Qt.Unchecked)
            item.setData(Qt.UserRole, record)
            item.setToolTip(self._record_tooltip(record))
            self.recent_test_list.addItem(item)
            if record['id'] == current_id:
                self.recent_test_list.setCurrentItem(item)
        self.recent_test_list.blockSignals(False)

    def _on_recent_selection_changed(self):
        """列表选中变化：同步高亮目标并重绘对比图（选中记录加粗、其余淡化）。"""
        items = self.recent_test_list.selectedItems()
        record = items[0].data(Qt.UserRole) if items else None
        self._highlight_record_id = record['id'] if record is not None else None
        checked = self._get_checked_records()
        curve_records = [r for r in checked if r['kind'] in self._CURVE_KINDS]
        if len(curve_records) >= 2:
            self._plot_comparison_curves(curve_records)

    def _show_recent_item_menu(self, pos):
        """Recent 列表右键菜单：重命名 / 载入 / 勾选对比 / 删除 / 清空。"""
        item = self.recent_test_list.itemAt(pos)
        menu = QMenu(self)

        if item is not None:
            record = item.data(Qt.UserRole)
            act_rename = QAction("Rename…", menu)
            act_rename.triggered.connect(lambda: self._rename_recent_record(record))
            menu.addAction(act_rename)

            act_load = QAction("Load Curve", menu)
            act_load.triggered.connect(lambda: self._load_recent_record(record))
            menu.addAction(act_load)

            act_check = QAction("Uncheck" if item.checkState() == Qt.Checked else "Check for Compare", menu)
            act_check.triggered.connect(
                lambda: item.setCheckState(
                    Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked)
            )
            menu.addAction(act_check)

            menu.addSeparator()
            act_remove = QAction("Remove", menu)
            act_remove.triggered.connect(lambda: self._delete_recent_record(record))
            menu.addAction(act_remove)
            menu.addSeparator()

        act_clear = QAction("Clear All", menu)
        act_clear.triggered.connect(self._on_clear_recent_tests)
        menu.addAction(act_clear)

        menu.exec(self.recent_test_list.mapToGlobal(pos))

    def _rename_recent_record(self, record):
        """重命名记录显示名（列表、对比图图例、单次图图例同步）。"""
        text, ok = QInputDialog.getText(
            self, "Rename", "Display name:",
            text=self._record_display_name(record),
        )
        if not ok:
            return
        record['label'] = text.strip()
        self._refresh_recent_test_list()
        self._append_log(f"[INFO] 记录 #{record['id']} 已重命名为「{record['label'] or record['test_item']}」")
        # 该记录在当前对比图中时重绘更新图例
        checked = self._get_checked_records()
        curve_records = [r for r in checked if r['kind'] in self._CURVE_KINDS]
        if len(curve_records) >= 2:
            self._plot_comparison_curves(curve_records)
        elif self._loaded_record is record:
            self._load_recent_record(record)

    def _delete_recent_record(self, record):
        """删除单条最近测试记录。"""
        try:
            self._recent_test_records.remove(record)
        except ValueError:
            return
        if self._loaded_record is record:
            self._loaded_record = None
        if self._highlight_record_id == record['id']:
            self._highlight_record_id = None
        self._refresh_recent_test_list()
        self._append_log(f"[INFO] 已删除记录 #{record['id']}")

    def _get_checked_records(self):
        records = []
        for i in range(self.recent_test_list.count()):
            item = self.recent_test_list.item(i)
            if item.checkState() == Qt.Checked:
                record = item.data(Qt.UserRole)
                if record is not None:
                    records.append(record)
        return records

    def _on_compare_recent_tests(self):
        records = self._get_checked_records()
        if len(records) < 2:
            self._append_log("[WARN] 对比至少需要勾选 2 条记录")
            return
        stat_records = [r for r in records if r['kind'] == '1000cnt']
        curve_records = [r for r in records if r['kind'] in self._CURVE_KINDS]
        if stat_records:
            self._compare_stats_to_log(stat_records)
        if not curve_records:
            self._append_log("[INFO] 勾选记录无曲线数据，统计对比已输出到日志")
            return
        if not self.chart_panel.isVisible():
            self._append_log(
                "[WARN] 当前测试项不显示曲线面板，请切换到曲线类测试项（如 Force Voltage Test）后重试"
            )
            return
        self._plot_comparison_curves(curve_records)

    def _compare_stats_to_log(self, records):
        self._append_log("===== 1000CNT 记录对比 =====")
        self._append_log(
            f"{'#':<4}{'Time':<14}{'AVG':>10}{'MIN':>10}{'MAX':>10}{'STD':>10}{'P-P':>8}{'N':>8}"
        )
        for r in records:
            p = r.get('params') or {}
            ts = r['time'].strftime("%m-%d %H:%M")
            self._append_log(
                f"#{r['id']:<3}{ts:<14}"
                f"{p.get('avg', 0):>10.3f}{p.get('min', 0):>10.3f}{p.get('max', 0):>10.3f}"
                f"{p.get('std', 0):>10.3f}{p.get('pp', 0):>8.0f}{p.get('count', 0):>8d}"
            )

    def _on_load_recent_test(self):
        records = self._get_checked_records()
        if not records:
            self._append_log("[WARN] 请先勾选一条要载入的记录")
            return
        if len(records) > 1:
            self._append_log("[WARN] 载入仅支持单条记录，已取勾选的第一条")
        self._load_recent_record(records[0])

    def _on_recent_item_double_clicked(self, item):
        record = item.data(Qt.UserRole)
        if record is not None:
            self._load_recent_record(record)

    def _load_recent_record(self, record):
        """载入历史记录：恢复其曲线、指标卡与可导出数据。"""
        kind = record['kind']
        if kind == '1000cnt':
            params = record.get('params') or {}
            self._append_log(
                f"[INFO] 已载入记录 #{record['id']}：AVG={params.get('avg', 0):.3f}, "
                f"STD={params.get('std', 0):.3f}, P-P={params.get('pp', 0):.0f}, N={params.get('count', 0)}"
            )
            if self.current_test_item == self.TEST_1000CNT:
                self.update_test_result(params)
                # 载入记录时同步恢复分布图（旧记录无 raw 字段时跳过）
                if params.get('raw'):
                    self._loaded_record = record
                    self._plot_cnt_distribution(params, record.get('algorithm'))
            else:
                self._append_log("[INFO] 切换到 1000CNT TEST 测试项可在指标卡查看该记录统计")
            return
        if not self.chart_panel.isVisible():
            self._append_log(
                "[WARN] 当前测试项不显示曲线面板，请切换到曲线类测试项（如 Force Voltage Test）后重试"
            )
            return
        self._export_data = None
        self._chart_image_bytes = None
        self._loaded_record = record
        if kind in ('force_voltage', 'high_low_temp'):
            calib = record.get('calibration') or {}
            if kind == 'force_voltage':
                # 恢复该记录的逐点悬浮预览数据（旧记录无 raw_samples 时悬浮提示无数据）
                raw = record.get('raw') or {}
                self._fv_hover_data = {
                    'mode': 'fv',
                    'x': list(calib.get('voltage') or []),
                    'y': list(calib.get('mean_cali') or []),
                    'raw_samples': raw.get('raw_samples') or [],
                    'raw_before': raw.get('raw_before_samples') or [],
                    'algorithm': record.get('algorithm'),
                }
            else:
                self._fv_hover_data = None
            self._plot_voltage_adc_curve(
                calib.get('voltage'), calib.get('mean_cali'),
                calib.get('min_cali'), calib.get('max_cali'),
                is_temp_mode=(kind == 'high_low_temp'),
            )
            params = record.get('params')
            if params:
                self.update_test_result(params)
            self._export_data = {
                'params': record.get('params'),
                'raw': record.get('raw'),
                'calibration': record.get('calibration'),
            }
        elif kind == 'multi_ch_temp':
            raw = record.get('raw') or {}
            self._plot_multi_ch_temp_curves(raw)
            self._export_data = {'multi_ch_temp': raw}
        elif kind == 'ft_calib_check':
            raw = record.get('raw') or {}
            self._update_ft_result_cards(raw)
            self._plot_ft_check_curve(raw)
            self._export_data = {'params': record.get('params'), 'ft_calib': raw}
        else:  # temp_consistency
            raw = record.get('raw') or {}
            self._plot_temp_consistency_curves(raw)
            self._export_data = {'raw': raw}
        self._append_log(f"[INFO] 已载入记录 #{record['id']} 的曲线与指标（{record['test_item']}）")

    def _on_clear_recent_tests(self):
        if not self._recent_test_records:
            return
        self._recent_test_records.clear()
        self.recent_test_list.clear()
        self._highlight_record_id = None
        self._loaded_record = None
        self._append_log("[INFO] 已清空最近测试记录")

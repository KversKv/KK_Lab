"""DetailDock — 下部 Dock（Tab：结果 | 执行日志）。

- 结果页：汇总条（总数/通过/失败/耗时 + 打开报告/打开输出目录）+ ``ResultTable``；
- 日志页：``LogPanel``（批量 flush / 右键菜单 / 行数上限）；
- 状态机联动：开始测试自动切日志页，结束自动切结果页；
- 双击结果行 → ``locateLogRequested(str)``（子页转发到 LogPanel.locate）。

为什么这样拆：结果/日志是"运行产物"的两个视图，归同一 Dock 后
"开始→看日志、结束→看结果"的自动跳转只在此一处实现。
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from ui.models.result_model import LOG_KEY, STATUS_KEY
from ui.widgets.log_panel import LogPanel
from ui.widgets.result_table import ResultTable


def _summarize_item(item) -> str:
    """单测试项结果摘要（measured 头几个键值 / 行数 / notes）。"""
    measured = getattr(item, "measured", None)
    notes = getattr(item, "notes", "") or ""
    if isinstance(measured, dict) and measured:
        head = "，".join(f"{k}={v}" for k, v in list(measured.items())[:3]
                         if k != "screenshots")
        return f"{head}（共 {len(measured)} 项）" + (f"；{notes}" if notes else "")
    if isinstance(measured, list) and measured:
        return f"{len(measured)} 行数据" + (f"；{notes}" if notes else "")
    return notes or "—"


class DetailDock(QWidget):
    """结果 / 日志 Tab 容器。"""

    openReportRequested = Signal()
    openOutputDirRequested = Signal()
    clearResultsRequested = Signal()
    locateLogRequested = Signal(str)

    TAB_RESULT = 0
    TAB_LOG = 1

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("detailTabs")
        self.tabs.setDocumentMode(True)
        root.addWidget(self.tabs)

        # —— 结果页 ——
        result_page = QWidget()
        r_lay = QVBoxLayout(result_page)
        r_lay.setContentsMargins(0, 6, 0, 0)
        r_lay.setSpacing(6)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(10)
        self._summary_label = QLabel("尚未执行测试")
        self._summary_label.setProperty("role", "caption")
        summary_row.addWidget(self._summary_label)
        summary_row.addStretch()
        self.open_report_btn = QPushButton("打开报告")
        self.open_report_btn.setProperty("variant", "ghost")
        self.open_report_btn.setEnabled(False)
        self.open_report_btn.clicked.connect(self.openReportRequested)
        summary_row.addWidget(self.open_report_btn)
        self.open_dir_btn = QPushButton("打开输出目录")
        self.open_dir_btn.setProperty("variant", "ghost")
        self.open_dir_btn.clicked.connect(self.openOutputDirRequested)
        summary_row.addWidget(self.open_dir_btn)
        self.clear_btn = QPushButton("清空结果")
        self.clear_btn.setProperty("variant", "ghost")
        self.clear_btn.clicked.connect(self.clearResultsRequested)
        summary_row.addWidget(self.clear_btn)
        r_lay.addLayout(summary_row)

        self.result_table = ResultTable()
        self.result_table.locateRequested.connect(self.locateLogRequested)
        r_lay.addWidget(self.result_table, 1)
        self.tabs.addTab(result_page, "结果")

        # —— 日志页 ——
        self.log_panel = LogPanel(title="执行日志")
        self.tabs.addTab(self.log_panel, "执行日志")

    # ------------------------------------------------------------------ API
    def show_result_tab(self) -> None:
        self.tabs.setCurrentIndex(self.TAB_RESULT)

    def show_log_tab(self) -> None:
        self.tabs.setCurrentIndex(self.TAB_LOG)

    def set_summary(self, total: int, passed: int, failed: int,
                    elapsed_s: float | None) -> None:
        elapsed = "--:--" if elapsed_s is None else self._fmt(elapsed_s)
        self._summary_label.setText(
            f"总数 {total} · 通过 {passed} · 失败 {failed} · 耗时 {elapsed}")

    def clear_summary(self) -> None:
        self._summary_label.setText("尚未执行测试")

    def set_result(self, result, elapsed_s: float | None = None) -> None:
        """填充一次完整测试结果（行 + 汇总条 + 报告可用态）。"""
        summary = getattr(result, "summary", {}) or {}
        rows = []
        for item in getattr(result, "items", []):
            verdict = ("PASS" if item.passed is True
                       else "FAIL" if item.passed is False else "N/A")
            rows.append({
                STATUS_KEY: verdict,
                "item": item.name,
                "detail": _summarize_item(item),
                "ts": getattr(item, "ts", ""),
                LOG_KEY: item.item_key,
            })
        self.result_table.set_columns(
            [(STATUS_KEY, "判定"), ("item", "测试项"),
             ("detail", "结果摘要"), ("ts", "完成时间")])
        self.result_table.set_rows(rows)
        self.set_summary(summary.get("total", 0), summary.get("pass", 0),
                         summary.get("fail", 0), elapsed_s)
        self.set_report_available(summary.get("report_path") is not None)

    def set_report_available(self, available: bool) -> None:
        self.open_report_btn.setEnabled(available)

    # 兼容旧引用：`execution_logs` 等价于日志面板
    execution_logs = property(lambda self: self.log_panel)

    @staticmethod
    def _fmt(seconds: float) -> str:
        s = max(0, int(seconds))
        return f"{s // 60:02d}:{s % 60:02d}"

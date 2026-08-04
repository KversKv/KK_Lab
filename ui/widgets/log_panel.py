"""LogPanel — 执行日志面板（包装增强 ExecutionLogsFrame，不改其内部实现）。

增强点（对 frame 透明）：
- 批量刷新：``append_log`` 入队，``QTimer`` 每 100ms 合并 flush，
  flush 期间 ``setUpdatesEnabled(False)`` 抑制高频重绘；
- 行数上限：``QTextDocument.setMaximumBlockCount(20000)``，防止长跑内存膨胀；
- 右键菜单：复制选中 / 复制全部 / 导出 .log / 清空。

既有能力（等级 Pill 过滤、搜索、自动跟随、复制/导出、计时/ETA）由
ExecutionLogsFrame 提供，直接透传。等级"多选 chips"在 P4 阶段随
ExecutionLogsFrame 过滤器改造落地（W2 范畴外，见 REFACTOR_PLAN）。

布局说明：本组件用于 DetailDock 的 Tab 容器（QSplitter 的角色由 Tab 替代），
故不强制 wrap_with 的 QSplitter 装配；禁 setMaximumHeight 等约束仍遵守。

为什么这样拆：批量 flush/行数上限是性能增强而非行为变更，包一层即可
获得收益且零回归风险；frame 内部逻辑（过滤/HTML 格式化）保持原样。
"""
from __future__ import annotations

from collections import deque

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import QMenu, QVBoxLayout, QWidget

from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from ui.theme import refresh_style

_FLUSH_MS = 100
_MAX_BLOCKS = 20000
# 单次 flush 上限：避免整批灌入阻塞事件循环（5 万条注入时保持 UI 可交互）
_FLUSH_MAX_PER_TICK = 400
_FLUSH_TIME_BUDGET_MS = 40.0


class LogPanel(QWidget):
    """执行日志面板（批量 flush + 行数上限 + 右键菜单）。"""

    def __init__(self, title: str = "执行日志", *, compact: bool = False,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._queue: deque[str] = deque()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.frame = ExecutionLogsFrame(title=title, show_progress=True, parent=self)
        root.addWidget(self.frame)

        # compact 模式：去 logContainer 外框/圆角，融入 Tab pane 等无外框容器
        if compact:
            self.frame.setProperty("compact", True)
            refresh_style(self.frame)

        doc = self.frame.log_edit.document()
        doc.setMaximumBlockCount(_MAX_BLOCKS)

        self.frame.log_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.frame.log_edit.customContextMenuRequested.connect(self._on_context_menu)

        self._flush_timer = QTimer(self)
        # 注入高峰用 0 间隔尽快排空，空闲时段由上限/预算保证 UI 节拍响应
        self._flush_timer.setInterval(0)
        self._flush_timer.timeout.connect(self._flush)

    # ------------------------------------------------------------------ 写入
    def append_log(self, message: str) -> None:
        """入队日志（线程安全约定：仅在 UI 线程调用，与 runner 信号直连）。"""
        self._queue.append(message)
        if not self._flush_timer.isActive():
            self._flush_timer.start()

    def _flush(self) -> None:
        """限批 flush：每次最多 _FLUSH_MAX_PER_TICK 条或 _FLUSH_TIME_BUDGET_MS，
        余量留待下一节拍，保证事件循环持续可响应（5 万条注入不卡顿）。"""
        if not self._queue:
            self._flush_timer.stop()
            return
        import time as _time
        edit = self.frame.log_edit
        edit.setUpdatesEnabled(False)
        try:
            budget = _time.perf_counter() + _FLUSH_TIME_BUDGET_MS / 1000.0
            n = 0
            while self._queue and n < _FLUSH_MAX_PER_TICK:
                self.frame.append_log(self._queue.popleft())
                n += 1
                if n % 64 == 0 and _time.perf_counter() > budget:
                    break
        finally:
            edit.setUpdatesEnabled(True)
            edit.viewport().update()
        if not self._queue:
            self._flush_timer.stop()

    def flush_now(self) -> None:
        """立即 flush（测试结束/页面切换前调用，避免尾批丢失）。"""
        self._flush()

    # ------------------------------------------------------------------ 透传
    def clear_log(self) -> None:
        self._queue.clear()
        self.frame.clear_log()

    def set_progress(self, value: int) -> None:
        self.frame.set_progress(value)

    def start_timer(self, total_steps: int = 0) -> None:
        self.frame.start_timer(total_steps)

    def stop_timer(self) -> None:
        self.frame.stop_timer()

    def update_step(self, index: int, text: str = "") -> None:
        self.frame.update_step(index, text)

    def locate(self, keyword: str) -> bool:
        """定位到包含关键字的日志行（双击结果行联动）。返回是否命中。"""
        if not keyword:
            return False
        cursor = self.frame.log_edit.document().find(keyword)
        if cursor.isNull():
            return False
        self.frame.log_edit.setTextCursor(cursor)
        return True

    # ------------------------------------------------------------------ 右键菜单
    def _on_context_menu(self, pos) -> None:
        edit = self.frame.log_edit
        menu = QMenu(self)

        act_copy = QAction("复制选中", menu)
        act_copy.setEnabled(edit.textCursor().hasSelection())
        act_copy.triggered.connect(edit.copy)
        menu.addAction(act_copy)

        act_copy_all = QAction("复制全部", menu)
        act_copy_all.triggered.connect(
            lambda: QGuiApplication.clipboard().setText(edit.toPlainText()))
        menu.addAction(act_copy_all)

        menu.addSeparator()
        act_export = QAction("导出 .log…", menu)
        act_export.triggered.connect(self.frame._export_logs)
        menu.addAction(act_export)

        act_clear = QAction("清空", menu)
        act_clear.triggered.connect(self.clear_log)
        menu.addAction(act_clear)

        menu.exec(edit.viewport().mapToGlobal(pos))


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

    from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout

    app = QApplication(sys.argv)
    win = QWidget()
    win.setWindowTitle("LogPanel Demo")
    lay = QVBoxLayout(win)

    panel = LogPanel()
    lay.addWidget(panel)

    burst = QPushButton("注入 1000 条日志")
    burst.clicked.connect(lambda: [panel.append_log(f"[INFO] 第 {i} 条批量日志") for i in range(1000)])
    lay.addWidget(burst)

    win.resize(720, 480)
    win.show()
    sys.exit(app.exec())

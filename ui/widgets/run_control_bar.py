"""RunControlBar — 运行控制条（开始/暂停/停止 + 进度 + 计时 + 计数 chips）。

- ``RunState`` 状态机枚举定义于此（页面层唯一引用点）；
- ``set_state()`` 单一入口驱动：按钮可用性 / 文案 / 进度条模式；
- 停止为内联二次确认：RUNNING 下首次点击进入 3s「确认停止？」武装态，
  再次点击才发 ``stopRequested``，超时自动还原（不用模态弹窗）；
- 暂停按钮为占位（Runner 无 pause API，core 不可改），禁用 + tooltip 说明。

为什么这样拆：运行态"禁用矩阵"是易错点（AGENTS.md 多处踩坑记录），
收敛为单一 ``set_state`` 入口后页面不可能漏设某个控件。
"""
from __future__ import annotations

import os
from enum import Enum, auto

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QWidget

from ui.resource_path import get_resource_base
from ui.theme import refresh_style
from ui.utils.icon_utils import tinted_svg_icon

_ICONS_DIR = os.path.join(get_resource_base(), "resources", "icons")
_ICON_PLAY = os.path.join(_ICONS_DIR, "play.svg")
_ICON_STOP = os.path.join(_ICONS_DIR, "square.svg")
_ICON_CHECK = os.path.join(_ICONS_DIR, "check.svg")
_ICON_X = os.path.join(_ICONS_DIR, "x-close.svg")
_ICON_MINUS = os.path.join(_ICONS_DIR, "more-horizontal.svg")
_ICON_COLOR = "#dbe7ff"
_ICON_SIZE = QSize(14, 14)


class RunState(Enum):
    """Module Test 运行状态机（页面层 _apply_run_state 的唯一事实源）。"""

    IDLE = auto()
    PRECHECK = auto()
    RUNNING = auto()
    PAUSED = auto()      # 预留：Runner 不支持暂停
    STOPPING = auto()
    FINISHED = auto()
    ERROR = auto()


_STOP_CONFIRM_MS = 3000


class RunControlBar(QFrame):
    """运行控制条。"""

    startRequested = Signal()
    pauseRequested = Signal()
    stopRequested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("RunControlBar")
        self._state = RunState.IDLE
        self._stop_armed = False

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(10)

        self.start_btn = QPushButton("开始测试")
        self.start_btn.setProperty("variant", "primary")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setToolTip("开始执行勾选的测试项（F5）")
        self.start_btn.setIcon(tinted_svg_icon(_ICON_PLAY, _ICON_COLOR, 14))
        self.start_btn.setIconSize(_ICON_SIZE)
        self.start_btn.clicked.connect(self.startRequested)
        lay.addWidget(self.start_btn)

        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setProperty("variant", "ghost")
        self.pause_btn.setEnabled(False)
        self.pause_btn.setToolTip("Runner 暂不支持暂停（预留）")
        self.pause_btn.clicked.connect(self.pauseRequested)
        lay.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setProperty("variant", "danger-ghost")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setToolTip("停止当前测试（Esc）")
        self.stop_btn.setIcon(tinted_svg_icon(_ICON_STOP, _ICON_COLOR, 14))
        self.stop_btn.setIconSize(_ICON_SIZE)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        lay.addWidget(self.stop_btn)

        self._confirm_timer = QTimer(self)
        self._confirm_timer.setSingleShot(True)
        self._confirm_timer.timeout.connect(self._disarm_stop)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        self.progress.setMinimumWidth(160)
        lay.addWidget(self.progress, 1)

        self._total_label = QLabel("-/-")
        self._total_label.setProperty("role", "mono")
        lay.addWidget(self._total_label)

        self._current_label = QLabel("就绪")
        self._current_label.setProperty("role", "caption")
        lay.addWidget(self._current_label, 1)

        self._elapsed_label = QLabel("已用 --:--")
        self._elapsed_label.setProperty("role", "mono")
        lay.addWidget(self._elapsed_label)

        self._eta_label = QLabel("剩余 --:--")
        self._eta_label.setProperty("role", "mono")
        lay.addWidget(self._eta_label)

        self._pass_chip = self._make_chip("chip-pass", _ICON_CHECK, 0)
        self._fail_chip = self._make_chip("chip-fail", _ICON_X, 0)
        self._skip_chip = self._make_chip("chip-skip", _ICON_MINUS, 0)
        lay.addWidget(self._pass_chip)
        lay.addWidget(self._fail_chip)
        lay.addWidget(self._skip_chip)

        self.set_state(RunState.IDLE)

    # ------------------------------------------------------------------ 构造
    @staticmethod
    def _make_chip(role: str, icon_path: str, count: int) -> QWidget:
        w = QWidget()
        w.setProperty("role", role)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(tinted_svg_icon(icon_path, _ICON_COLOR, 13).pixmap(13, 13))
        count_lbl = QLabel(str(count))
        w._count_label = count_lbl
        lay.addWidget(icon_lbl)
        lay.addWidget(count_lbl)
        return w

    # ------------------------------------------------------------------ 状态
    def state(self) -> RunState:
        return self._state

    def set_state(self, state: RunState) -> None:
        """单一入口：按钮可用性 / 文案 / 进度条模式全部由状态推导。"""
        self._state = state
        self._disarm_stop()

        if state is RunState.IDLE:
            self._set_buttons(start=True, pause=False, stop=False)
            self.start_btn.setText("开始测试")
            self._set_progress_busy(False)
            self.progress.setValue(0)
            self._current_label.setText("就绪")
        elif state is RunState.PRECHECK:
            self._set_buttons(start=False, pause=False, stop=False)
            self.start_btn.setText("检查中…")
            self._set_progress_busy(True)
        elif state is RunState.RUNNING:
            self._set_buttons(start=False, pause=False, stop=True)
            self.start_btn.setText("运行中…")
            self._set_progress_busy(False)
        elif state is RunState.PAUSED:  # 预留
            self._set_buttons(start=False, pause=True, stop=True)
            self.start_btn.setText("已暂停")
        elif state is RunState.STOPPING:
            self._set_buttons(start=False, pause=False, stop=False)
            self.stop_btn.setText("停止中…")
        elif state is RunState.FINISHED:
            self._set_buttons(start=True, pause=False, stop=False)
            self.start_btn.setText("开始测试")
            self._set_progress_busy(False)
            self.progress.setProperty("state", "done")
        elif state is RunState.ERROR:
            self._set_buttons(start=True, pause=False, stop=False)
            self.start_btn.setText("开始测试")
            self._set_progress_busy(False)
            self.progress.setProperty("state", "error")

        refresh_style(self.progress)

    def _set_buttons(self, *, start: bool, pause: bool, stop: bool) -> None:
        self.start_btn.setEnabled(start)
        # 暂停为占位（Runner 无 pause API），任何状态都保持禁用
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(stop)
        if stop:
            self.stop_btn.setText("停止")

    def _set_progress_busy(self, busy: bool) -> None:
        self.progress.setRange(0, 0 if busy else 100)
        if not busy:
            self.progress.setProperty("state", None)

    # ------------------------------------------------------------------ 数据
    def set_progress(self, percent: int | None) -> None:
        """percent 为 None 时切不确定态（busy）。"""
        if percent is None:
            self._set_progress_busy(True)
            return
        if self.progress.maximum() == 0:
            self._set_progress_busy(False)
        self.progress.setValue(max(0, min(100, percent)))

    def set_counts(self, passed: int = 0, failed: int = 0, skipped: int = 0) -> None:
        self._pass_chip._count_label.setText(str(passed))
        self._fail_chip._count_label.setText(str(failed))
        self._skip_chip._count_label.setText(str(skipped))

    def set_timing(self, elapsed_s: float | None = None,
                   eta_s: float | None = None) -> None:
        self._elapsed_label.setText(f"已用 {self._fmt(elapsed_s)}")
        self._eta_label.setText(f"剩余 {self._fmt(eta_s)}")

    def set_current_item(self, text: str) -> None:
        self._current_label.setText(text or "—")

    def set_total_text(self, text: str) -> None:
        self._total_label.setText(text)

    @staticmethod
    def _fmt(seconds: float | None) -> str:
        if seconds is None:
            return "--:--"
        s = max(0, int(seconds))
        return f"{s // 60:02d}:{s % 60:02d}"

    # ------------------------------------------------------------------ 停止确认
    def _on_stop_clicked(self) -> None:
        if not self._stop_armed:
            self._stop_armed = True
            self.stop_btn.setText("确认停止？")
            self._confirm_timer.start(_STOP_CONFIRM_MS)
            return
        self._disarm_stop()
        self.stopRequested.emit()

    def _disarm_stop(self) -> None:
        self._stop_armed = False
        self._confirm_timer.stop()
        if self._state is RunState.RUNNING:
            self.stop_btn.setText("停止")


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

    from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout

    from ui.theme import apply_qss

    app = QApplication(sys.argv)
    win = QWidget()
    win.setWindowTitle("RunControlBar Demo")
    apply_qss(win, "controls")
    lay = QVBoxLayout(win)

    bar = RunControlBar()
    lay.addWidget(bar)
    bar.set_total_text("3/15")
    bar.set_current_item("当前: Load Transient")
    bar.set_timing(59, 130)
    bar.set_counts(8, 1, 0)
    bar.set_progress(42)

    for st in RunState:
        btn = QPushButton(f"切到 {st.name}")
        btn.clicked.connect(lambda _c=False, s=st: bar.set_state(s))
        lay.addWidget(btn)
    bar.stopRequested.connect(lambda: print("stop confirmed"))
    bar.startRequested.connect(lambda: bar.set_state(RunState.RUNNING))

    win.resize(860, 300)
    win.show()
    sys.exit(app.exec())

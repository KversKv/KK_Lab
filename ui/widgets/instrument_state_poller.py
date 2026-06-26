#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generic instrument state poller for keeping UI panels in sync with hardware.

This widget-layer helper periodically reads a snapshot of an instrument's
state on a background QThread and emits it back to the UI thread, so a page
can reflect changes made manually on the physical instrument.

Design goals:
- UI layer only. No dependency on core/ or InstrumentManager, so pages that
  are compiled and run standalone keep working.
- IO never runs on the UI thread (project hard rule).
- Pausable: only the visible page should poll, idle pages pause to save
  resources without destroying/recreating threads.
- Lease aware: when an optional busy-checker reports the instrument is busy
  (leased by a long test flow), the poller skips that round to avoid bus
  contention.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from PySide6.QtCore import QObject, QThread, Signal

from log_config import get_logger

logger = get_logger(__name__)


class _WriteGuard:
    """Shared coordination state between UI writes and the poll worker.

    Solves two problems caused by a background poller racing with manual UI
    writes on the same instrument:

    1. Stale snapshot rebound: a snapshot read *before* the user changed a
       setting could still be applied afterwards, flipping the widget back to
       the old value. We tag every snapshot with the generation counter that
       was current when the read started; the UI thread drops snapshots whose
       generation is older than the latest user write.
    2. Lock contention / freeze: while the worker holds the IO lock for a full
       (potentially slow) read round, a user write would block the UI thread.
       During a short quiet window after each write the worker skips the whole
       round (it does not even try to acquire the lock), so user writes stay
       responsive and never deadlock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._generation = 0
        self._quiet_until = 0.0

    def begin_write(self, quiet_window_s: float) -> None:
        with self._lock:
            self._generation += 1
            self._quiet_until = time.monotonic() + max(0.0, quiet_window_s)

    def current_generation(self) -> int:
        with self._lock:
            return self._generation

    def in_quiet_window(self) -> bool:
        with self._lock:
            return time.monotonic() < self._quiet_until

    def is_fresh(self, generation: int) -> bool:
        with self._lock:
            return generation == self._generation and time.monotonic() >= self._quiet_until


class _StatePollWorker(QObject):
    state_ready = Signal(dict, int)
    finished = Signal()

    def __init__(
        self,
        read_state_fn: Callable[[], Optional[dict]],
        interval_s: float,
        busy_check_fn: Optional[Callable[[], bool]] = None,
        io_lock: Optional[threading.RLock] = None,
        write_guard: Optional[_WriteGuard] = None,
        io_lock_provider: Optional[Callable[[], threading.RLock]] = None,
    ):
        super().__init__()
        self._read_state_fn = read_state_fn
        self._interval_s = max(0.05, float(interval_s))
        self._busy_check_fn = busy_check_fn
        self._io_lock = io_lock
        self._io_lock_provider = io_lock_provider
        self._write_guard = write_guard
        self._running = False
        self._paused = True
        self._lock = threading.Lock()

    def set_interval(self, interval_s: float) -> None:
        with self._lock:
            self._interval_s = max(0.05, float(interval_s))

    def set_paused(self, paused: bool) -> None:
        with self._lock:
            self._paused = bool(paused)

    def stop(self) -> None:
        with self._lock:
            self._running = False

    def start_polling(self) -> None:
        self._running = True
        while True:
            with self._lock:
                running = self._running
                paused = self._paused
                interval_s = self._interval_s
            if not running:
                break
            if paused:
                QThread.msleep(100)
                continue
            if self._write_guard is not None and self._write_guard.in_quiet_window():
                QThread.msleep(50)
                continue
            if self._busy_check_fn is not None:
                try:
                    if self._busy_check_fn():
                        QThread.msleep(int(interval_s * 1000))
                        continue
                except Exception:
                    logger.debug("busy_check_fn raised, polling anyway", exc_info=True)
            generation = (
                self._write_guard.current_generation()
                if self._write_guard is not None
                else 0
            )
            try:
                io_lock = self._io_lock
                if self._io_lock_provider is not None:
                    try:
                        provided = self._io_lock_provider()
                        if provided is not None:
                            io_lock = provided
                    except Exception:
                        logger.debug("io_lock_provider raised, using default lock", exc_info=True)
                if io_lock is not None:
                    with io_lock:
                        snapshot = self._read_state_fn()
                else:
                    snapshot = self._read_state_fn()
            except Exception as e:
                logger.warning("状态轮询读取失败: %s", e, exc_info=True)
                snapshot = None
            with self._lock:
                running = self._running
            if running and snapshot is not None:
                self.state_ready.emit(snapshot, generation)
            QThread.msleep(int(interval_s * 1000))
        self.finished.emit()


class InstrumentStatePoller(QObject):
    """Page-owned poller that mirrors instrument state into the UI.

    Usage::

        self._poller = InstrumentStatePoller(
            read_state_fn=self._read_instrument_snapshot,
            apply_state_fn=self._apply_instrument_snapshot,
            interval_s=1.0,
            busy_check_fn=self._is_session_busy,  # optional
            parent=self,
        )
        # in showEvent: self._poller.resume()
        # in hideEvent: self._poller.pause()
        # in closeEvent: self._poller.stop()

    ``read_state_fn`` runs on the worker thread and must only touch the
    instrument (no Qt widgets). ``apply_state_fn`` runs on the UI thread and
    receives the emitted dict to update widgets.
    """

    def __init__(
        self,
        read_state_fn: Callable[[], Optional[dict]],
        apply_state_fn: Callable[[dict], None],
        interval_s: float = 1.0,
        busy_check_fn: Optional[Callable[[], bool]] = None,
        parent: Optional[QObject] = None,
        quiet_window_s: Optional[float] = None,
        io_lock: Optional[threading.RLock] = None,
        io_lock_provider: Optional[Callable[[], threading.RLock]] = None,
    ):
        super().__init__(parent)
        self._read_state_fn = read_state_fn
        self._apply_state_fn = apply_state_fn
        self._interval_s = interval_s
        self._busy_check_fn = busy_check_fn
        self._io_lock = io_lock if io_lock is not None else threading.RLock()
        self._io_lock_provider = io_lock_provider
        self._write_guard = _WriteGuard()
        self._quiet_window_s = (
            quiet_window_s if quiet_window_s is not None else max(0.3, interval_s * 1.5)
        )
        self._thread: Optional[QThread] = None
        self._worker: Optional[_StatePollWorker] = None

    def _resolve_io_lock(self) -> threading.RLock:
        """解析当前应使用的 IO 锁：优先 provider（按当前目标会话动态返回）。

        provider 为空或抛错时回退到固定锁，保证 UI 写入始终有锁可持。
        """
        if self._io_lock_provider is not None:
            try:
                provided = self._io_lock_provider()
                if provided is not None:
                    return provided
            except Exception:
                logger.debug("io_lock_provider raised, using default lock", exc_info=True)
        return self._io_lock

    @property
    def io_lock(self) -> threading.RLock:
        """Shared lock guarding instrument IO.

        Wrap manual writes (e.g. set output / set temperature) issued from the
        UI thread with ``with poller.io_lock:`` so they never overlap a worker
        read on the same VISA/serial connection.

        Prefer the :meth:`writing` context manager, which also opens a quiet
        window so a stale in-flight snapshot cannot rebound onto the UI.
        """
        return self._resolve_io_lock()

    def begin_write(self) -> None:
        """Signal that the UI is about to issue a manual write.

        Bumps the generation counter (so any snapshot already read by the
        worker is treated as stale and dropped on the UI thread) and opens a
        short quiet window during which the worker skips polling entirely.
        """
        self._write_guard.begin_write(self._quiet_window_s)

    def writing(self):
        """Context manager wrapping a manual instrument write.

        Opens the quiet window, then holds the IO lock only for the duration of
        the write itself::

            with self._state_poller.writing():
                inst.set_channel_display(ch, on)
        """
        poller = self

        class _WritingCtx:
            def __enter__(self_inner):
                poller.begin_write()
                self_inner._lock = poller._resolve_io_lock()
                self_inner._lock.acquire()
                return self_inner

            def __exit__(self_inner, exc_type, exc, tb):
                self_inner._lock.release()
                poller._write_guard.begin_write(poller._quiet_window_s)
                return False

        return _WritingCtx()

    def _ensure_thread(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        self._worker = _StatePollWorker(
            self._read_state_fn,
            self._interval_s,
            self._busy_check_fn,
            self._io_lock,
            self._write_guard,
            self._io_lock_provider,
        )
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start_polling)
        self._worker.state_ready.connect(self._on_state_ready)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

    def _on_state_ready(self, snapshot: dict, generation: int) -> None:
        if not self._write_guard.is_fresh(generation):
            logger.debug("丢弃过期状态快照 (gen=%s)", generation)
            return
        try:
            self._apply_state_fn(snapshot)
        except Exception as e:
            logger.warning("状态轮询应用到 UI 失败: %s", e, exc_info=True)

    def _on_thread_finished(self) -> None:
        self._worker = None
        self._thread = None

    def set_interval(self, interval_s: float) -> None:
        self._interval_s = interval_s
        if self._worker is not None:
            self._worker.set_interval(interval_s)

    def resume(self) -> None:
        self._ensure_thread()
        if self._worker is not None:
            self._worker.set_paused(False)

    def pause(self) -> None:
        if self._worker is not None:
            self._worker.set_paused(True)

    def stop(self) -> None:
        if self._worker is not None:
            self._worker.stop()
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
        self._worker = None
        self._thread = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

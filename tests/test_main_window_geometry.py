#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主窗口几何状态持久化回归测试（offscreen）。"""

import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QRect, QSettings
from PySide6.QtWidgets import QApplication, QMainWindow

app = QApplication.instance() or QApplication([])

from ui.main_window import MainWindow  # noqa: E402


class _GeometryHost(QMainWindow):
    _screen_available_geometry_for = MainWindow._screen_available_geometry_for
    _clamped_window_geometry = MainWindow._clamped_window_geometry
    _load_window_geometry = MainWindow._load_window_geometry
    _collect_window_state = MainWindow._collect_window_state
    _restore_window_geometry = MainWindow._restore_window_geometry
    _save_window_geometry = MainWindow._save_window_geometry

    def __init__(self, settings_path):
        super().__init__()
        self._settings_path = settings_path
        self._compact_view = False
        self._pre_compact_state = None
        self._restore_maximized = False
        self.setMinimumSize(966, 640)

    def _main_window_settings(self):
        return QSettings(self._settings_path, QSettings.IniFormat)


class MainWindowGeometryTest(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self._settings_path = os.path.join(self._temp_dir.name, "geometry.ini")
        self._hosts = []

    def _host(self):
        host = _GeometryHost(self._settings_path)
        self._hosts.append(host)
        return host

    def test_first_launch_keeps_default_geometry(self):
        host = self._host()
        host.setGeometry(40, 50, 1100, 700)

        host._restore_window_geometry()

        self.assertFalse(host._restore_maximized)
        self.assertEqual(host.geometry(), QRect(40, 50, 1100, 700))

    def test_restores_size_and_position(self):
        source = self._host()
        source.setGeometry(80, 100, 1200, 780)
        source.show()
        app.processEvents()
        expected = source.geometry()
        source._save_window_geometry()

        restored = self._host()
        restored.setGeometry(0, 0, 1600, 900)
        restored._screen_available_geometry_for = (
            lambda point=None: QRect(0, 0, 1920, 1080)
        )
        restored._restore_window_geometry()

        self.assertEqual(restored.geometry(), expected)
        self.assertFalse(restored._restore_maximized)

    def test_restores_maximized_state(self):
        source = self._host()
        source.setGeometry(100, 120, 1200, 780)
        source.showMaximized()
        app.processEvents()
        source._save_window_geometry()

        restored = self._host()
        restored._restore_window_geometry()
        self.assertTrue(restored._restore_maximized)
        restored.showMaximized()
        app.processEvents()

        self.assertTrue(restored.isMaximized())

    def test_compact_close_saves_pre_compact_geometry(self):
        source = self._host()
        source.setGeometry(110, 130, 1280, 820)
        source.show()
        app.processEvents()
        expected = source.geometry()
        source._pre_compact_state = (
            False,
            source.saveGeometry(),
            source._collect_window_state(),
        )
        source._compact_view = True
        source.setFixedSize(600, 200)
        source._save_window_geometry()

        restored = self._host()
        restored._screen_available_geometry_for = (
            lambda point=None: QRect(0, 0, 1920, 1080)
        )
        restored._restore_window_geometry()

        self.assertEqual(restored.geometry(), expected)
        self.assertFalse(restored._restore_maximized)

    def test_secondary_monitor_geometry_is_not_offset_or_shrunk(self):
        settings = QSettings(self._settings_path, QSettings.IniFormat)
        for key, value in {
            "x": 2300,
            "y": -180,
            "width": 1500,
            "height": 920,
            "maximized": False,
        }.items():
            settings.setValue(f"geometry/{key}", value)
        settings.sync()

        restored = self._host()
        restored._screen_available_geometry_for = (
            lambda point=None: QRect(1920, -360, 2560, 1440)
        )
        restored._restore_window_geometry()

        self.assertEqual(restored.geometry(), QRect(2300, -180, 1500, 920))


if __name__ == "__main__":
    unittest.main()

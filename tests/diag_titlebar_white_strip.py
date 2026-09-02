#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断主窗口自绘标题栏顶部异常白条。

启动 MainWindow → 等待渲染 → 抓屏 → 分析窗口顶部 N 行像素颜色，
同时输出 GetWindowRect / GetClientRect 差值（非客户区高度）。
仅诊断用，不参与业务。运行：python tests/diag_titlebar_white_strip.py
"""

import ctypes
import ctypes.wintypes
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def _analyze(app, win, done_cb):
    user32 = ctypes.windll.user32
    hwnd = int(win.winId())

    wr = _RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(wr))
    cr = _RECT()
    user32.GetClientRect(hwnd, ctypes.byref(cr))
    pt = ctypes.wintypes.POINT(cr.left, cr.top)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))

    win_h = wr.bottom - wr.top
    win_w = wr.right - wr.left
    nc_left = pt.x - wr.left
    nc_top = pt.y - wr.top
    state = "MAXIMIZED" if win.isMaximized() else "NORMAL"
    print(f"\n===== state={state} =====")
    print(f"[rect] window=({wr.left},{wr.top},{wr.right},{wr.bottom}) "
          f"{win_w}x{win_h}")
    print(f"[nc] client origin offset vs window origin: "
          f"left={nc_left}, top={nc_top} "
          f"(client={cr.right - cr.left}x{cr.bottom - cr.top})")
    print(f"[qt] geometry={win.geometry()} frameGeometry={win.frameGeometry()}")

    screen = win.screen()
    user32.SetForegroundWindow(hwnd)
    img = screen.grabWindow(hwnd).toImage()
    print(f"[shot] window grab img={img.width()}x{img.height()} "
          f"dpr={screen.devicePixelRatio()} win={win_w}x{win_h}")

    # 逐行分析窗口顶部 48 物理像素（避开左右按钮，取中间 30%~70%）
    x0 = int(win_w * 0.30)
    x1 = int(win_w * 0.70)
    rows = []
    max_y = min(48, win_h)
    for dy in range(max_y):
        y = dy
        if y < 0 or y >= img.height():
            rows.append((dy, None))
            continue
        r = g = b = n = 0
        for x in range(x0, x1, 7):
            if 0 <= x < img.width():
                c = img.pixelColor(x, y)
                r += c.red()
                g += c.green()
                b += c.blue()
                n += 1
        if n:
            rows.append((dy, (r // n, g // n, b // n)))
        else:
            rows.append((dy, None))

    light_rows = []
    for dy, rgb in rows:
        if rgb is None:
            print(f"row {dy:>3}: <out of image>")
            continue
        lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        marker = ""
        if lum > 180:
            marker = "  <-- LIGHT"
            light_rows.append((dy, rgb, lum))
        if dy < 12 or marker:
            print(f"row {dy:>3}: rgb={rgb} lum={lum:.0f}{marker}")

    if light_rows:
        dy_list = [d for d, _, _ in light_rows]
        print(f"[RESULT] LIGHT rows: {dy_list} "
              f"(height ~{len(dy_list)}, first={dy_list[0]})")
        print("[RESULT] 判定：窗口顶部存在浅色条带")
    else:
        print("[RESULT] 顶部 48 行内未发现浅色行")


def main():
    app = QApplication(sys.argv)
    win = MainWindow(with_ai=False)
    win.show()

    def step2():
        _analyze(app, win, None)
        win.showMaximized()
        QTimer.singleShot(2000, lambda: _analyze(app, win, app.quit))

    QTimer.singleShot(2000, step2)
    app.exec()


if __name__ == "__main__":
    main()

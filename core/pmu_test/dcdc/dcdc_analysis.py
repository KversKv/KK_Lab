# -*- coding: utf-8 -*-
"""
DCDC 效率测试纯算法/解析函数（无 PySide6，可 pytest 直测）。

从 ui/pages/pmu_test/pmu_dcdc_efficiency.py 平移而来，行为零变更。
"""

import math

SMOOTH_WINDOW = 5
SMOOTH_POLY_ORDER = 2


def polyfit(xs, ys, order):
    n = len(xs)
    mat = [[0.0] * (order + 1) for _ in range(order + 1)]
    rhs = [0.0] * (order + 1)
    for i in range(order + 1):
        for j in range(order + 1):
            mat[i][j] = sum(x ** (i + j) for x in xs)
        rhs[i] = sum(ys[k] * xs[k] ** i for k in range(n))
    for col in range(order + 1):
        pivot = col
        for row in range(col + 1, order + 1):
            if abs(mat[row][col]) > abs(mat[pivot][col]):
                pivot = row
        mat[col], mat[pivot] = mat[pivot], mat[col]
        rhs[col], rhs[pivot] = rhs[pivot], rhs[col]
        diag = mat[col][col]
        if abs(diag) < 1e-15:
            continue
        for j in range(col, order + 1):
            mat[col][j] /= diag
        rhs[col] /= diag
        for row in range(order + 1):
            if row == col:
                continue
            factor = mat[row][col]
            for j in range(col, order + 1):
                mat[row][j] -= factor * mat[col][j]
            rhs[row] -= factor * rhs[col]
    return rhs


def savgol_smooth(y_vals, window=SMOOTH_WINDOW, poly_order=SMOOTH_POLY_ORDER):
    n = len(y_vals)
    if n < window or window < poly_order + 1:
        return list(y_vals)
    if window % 2 == 0:
        window += 1
    half = window // 2
    result = list(y_vals)
    for i in range(half, n - half):
        xs = list(range(-half, half + 1))
        ys = y_vals[i - half: i + half + 1]
        coeffs = polyfit(xs, ys, poly_order)
        result[i] = coeffs[0]
    return result


def generate_current_points(cfg):
    start_a = abs(cfg["start_current_a"])
    end_a = abs(cfg["end_current_a"])
    sweep_mode = cfg["sweep_mode"]

    if sweep_mode == "Log":
        points_per_dec = cfg["points_per_dec"]
        log_start = math.log10(start_a)
        log_end = math.log10(end_a)
        dec_start = math.floor(log_start)
        dec_end = math.ceil(log_end)
        current_points = []
        for d in range(dec_start, dec_end):
            for k in range(points_per_dec):
                val = 10 ** (d + k / points_per_dec)
                if start_a <= val <= end_a:
                    current_points.append(val)
        val_end = 10 ** dec_end
        if start_a <= val_end <= end_a and (not current_points or abs(current_points[-1] - val_end) > 1e-12):
            current_points.append(val_end)
        if not current_points:
            current_points = [start_a, end_a]
    else:
        step_a = abs(cfg["step_current_a"])
        total_points = max(2, int(round(abs(end_a - start_a) / step_a)) + 1)
        current_points = [start_a + i * step_a for i in range(total_points) if start_a + i * step_a <= end_a + step_a * 0.001]

    return current_points


def trimmed_mean(samples):
    s = sorted(samples)
    return sum(s[1:-1]) / (len(s) - 2)


"use strict";
/* ================================================================
 * 数据（后端注入，唯一事实源）
 * ================================================================ */
const REPORT_DATA = {"meta": {"report_title": "Module Test Report — DCDC", "module_type": "DCDC", "chip": "BES1811", "sample_id": null, "operator": "KK", "temperature_c": 25.0, "vin_nominal_v": null, "vout_nominal_mv": null, "start_time": "2026-07-31 09:12:00", "end_time": "2026-07-31 09:31:24", "duration_s": 1164.0, "generated_at": "2026-07-31 19:32:44+08:00", "sw_version": "0.1.0", "hw_setup": null, "instruments": [], "environment": {"ta_c": 25.0, "humidity_pct": null}}, "summary": {"verdict": "FAIL", "pass": 7, "fail": 2, "warn": 0, "na": 1, "total": 10}, "items": [{"index": 1, "item_key": "dcdc_vout_scan", "title": "Output Voltage Scan", "verdict": "PASS", "unit": "mV", "ts": "2026-07-31 19:32:44", "metrics": [{"key": "default_mv", "label": "Default", "value": 800.0, "unit": "mV", "precision": 3, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}, {"key": "vout_min", "label": "Min", "value": 305.681, "unit": "mV", "precision": 3, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}, {"key": "vout_max", "label": "Max", "value": 761.2, "unit": "mV", "precision": 3, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}, {"key": "step_mv", "label": "Avg Step", "value": 3.575, "unit": "mV", "precision": 3, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}], "charts": [{"kind": "xy", "title": "Vout vs Code", "x": {"key": "c0", "label": "Code", "unit": ""}, "series": [{"key": "c1", "name": "Vout (mV)", "type": "line", "axis": "left", "unit": "mV", "label": "Vout"}, {"key": "c2", "name": "Diff (mV)", "type": "bar", "axis": "right", "unit": "mV", "label": "Diff"}], "mark_extrema": true, "zoom": true, "id": "dcdc_vout_scan_0"}], "table": {"file": "dcdc_vout_scan.csv", "rows": 126, "columns": [{"key": "c0", "label": "Code", "unit": "", "align": "right", "precision": 0}, {"key": "c1", "label": "Vout", "unit": "mV", "align": "right", "precision": 3}, {"key": "c2", "label": "Diff", "unit": "mV", "align": "right", "precision": 3}], "data": [[0.0, 312.859, 0.0], [1.0, 316.296, 3.437], [2.0, 320.271, 3.975], [3.0, 323.383, 3.112], [4.0, 327.329, 3.946], [5.0, 330.768, 3.439], [6.0, 334.096, 3.329], [7.0, 338.031, 3.935], [8.0, 341.23, 3.199], [9.0, 345.122, 3.892], [10.0, 348.406, 3.284], [11.0, 351.998, 3.592], [12.0, 355.84, 3.842], [13.0, 359.736, 3.897], [14.0, 362.749, 3.013], [15.0, 366.404, 3.655], [16.0, 370.302, 3.898], [17.0, 374.133, 3.831], [18.0, 377.412, 3.279], [19.0, 380.842, 3.431], [20.0, 384.881, 4.039], [21.0, 387.712, 2.831], [22.0, 391.937, 4.225], [23.0, 395.057, 3.12], [24.0, 398.515, 3.459], [25.0, 402.069, 3.554], [26.0, 405.797, 3.728], [27.0, 409.778, 3.981], [28.0, 412.845, 3.067], [29.0, 416.74, 3.896], [30.0, 420.361, 3.621], [31.0, 423.723, 3.362], [32.0, 427.438, 3.715], [33.0, 430.625, 3.187], [34.0, 434.198, 3.572], [35.0, 437.89, 3.692], [36.0, 441.844, 3.955], [37.0, 445.217, 3.373], [38.0, 448.701, 3.484], [39.0, 452.493, 3.792], [40.0, 455.963, 3.469], [41.0, 459.415, 3.452], [42.0, 463.386, 3.971], [43.0, 466.884, 3.499], [44.0, 470.095, 3.211], [45.0, 473.935, 3.839], [46.0, 477.47, 3.536], [47.0, 481.325, 3.855], [48.0, 484.784, 3.458], [49.0, 488.005, 3.222], [50.0, 492.134, 4.129], [51.0, 495.019, 2.885], [52.0, 498.834, 3.815], [53.0, 502.681, 3.846], [54.0, 505.772, 3.091], [55.0, 509.616, 3.845], [56.0, 512.831, 3.215], [57.0, 516.91, 4.078], [58.0, 520.562, 3.652], [59.0, 523.983, 3.422], [60.0, 527.8, 3.817], [61.0, 530.926, -18.4], [62.0, 534.806, 3.88], [63.0, 538.3, 3.494], [64.0, 541.864, 3.563], [65.0, 545.34, 3.476], [66.0, 549.222, 3.882], [67.0, 552.881, 3.659], [68.0, 556.079, 3.199], [69.0, 559.806, 3.727], [70.0, 562.899, 3.092], [71.0, 566.986, 4.088], [72.0, 570.518, 3.532], [73.0, 574.369, 3.852], [74.0, 577.808, 3.438], [75.0, 580.953, 3.145], [76.0, 584.609, 3.656], [77.0, 588.41, 3.801], [78.0, 591.468, 3.058], [79.0, 595.394, 3.926], [80.0, 598.734, 3.34], [81.0, 602.269, 3.534], [82.0, 605.797, 3.528], [83.0, 609.94, 4.142], [84.0, 613.003, 3.064], [85.0, 616.673, 3.67], [86.0, 620.363, 3.69], [87.0, 624.322, 3.959], [88.0, 627.264, 21.2], [89.0, 631.134, 3.87], [90.0, 634.79, 3.655], [91.0, 638.632, 3.842], [92.0, 642.155, 3.524], [93.0, 645.766, 3.611], [94.0, 648.873, 3.107], [95.0, 652.557, 3.685], [96.0, 656.087, 3.53], [97.0, 660.082, 3.995], [98.0, 663.716, 3.634], [99.0, 666.646, 2.93], [100.0, 670.241, 3.595], [101.0, 673.861, 3.62], [102.0, 677.437, 3.576], [103.0, 681.213, 3.776], [104.0, 684.871, 3.658], [105.0, 688.185, 3.314], [106.0, 691.553, 3.368], [107.0, 695.46, 3.907], [108.0, 698.995, 3.535], [109.0, 702.728, 3.733], [110.0, 706.612, 3.884], [111.0, 709.977, 3.365], [112.0, 713.412, 3.435], [113.0, 717.069, 3.657], [114.0, 720.691, 3.622], [115.0, 723.768, 3.077], [116.0, 728.02, 4.251], [117.0, 731.499, 3.479], [118.0, 735.15, 3.651], [119.0, 738.663, 3.514], [120.0, 741.914, 3.251], [121.0, 745.494, 3.58], [122.0, 748.833, 3.339], [123.0, 752.832, 4.0], [124.0, 755.95, 3.117], [125.0, 759.529, 3.579]], "rules": [{"column": "c2", "op": "outlier", "k": 5, "level": "warn", "hint": "步进异常跳变(>5×MAD)"}]}, "attachments": [], "note": "有效段步进 3.575mV，线性度 2.026%"}, {"index": 2, "item_key": "dcdc_efficiency", "title": "Efficiency", "verdict": "FAIL", "unit": "%", "ts": "2026-07-31 19:32:44", "metrics": [{"key": "max_eff", "label": "Max η", "value": 104.7, "unit": "%", "precision": 2, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}, {"key": "max_eff_at", "label": "Peak @ Iload", "value": 750.0, "unit": "mA", "precision": 0, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}, {"key": "avg_eff", "label": "Avg η", "value": 88.2, "unit": "%", "precision": 2, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}], "charts": [{"kind": "xy", "title": "Efficiency vs Iload", "x": {"key": "c0", "label": "Iload", "unit": "mA"}, "series": [{"key": "c2", "name": "Efficiency (%)", "type": "line", "axis": "left", "unit": "%", "label": "Efficiency"}], "ref_y": 100, "logx": true, "anomaly": {"key": "c2", "op": "gt", "value": 100}, "id": "dcdc_efficiency_0"}], "table": {"file": "dcdc_efficiency.csv", "rows": 36, "columns": [{"key": "c0", "label": "Iload", "unit": "mA", "align": "right", "precision": 0}, {"key": "c1", "label": "Vout", "unit": "mV", "align": "right", "precision": 2}, {"key": "c2", "label": "Efficiency", "unit": "%", "align": "right", "precision": 2}], "data": [[25.0, 795.95, 62.79], [50.0, 794.63, 64.85], [75.0, 795.82, 65.5], [100.0, 798.36, 67.47], [125.0, 804.49, 68.91], [150.0, 795.78, 72.34], [175.0, 798.17, 72.92], [200.0, 795.47, 74.93], [225.0, 805.92, 78.05], [250.0, 799.81, 78.56], [275.0, 795.23, 79.09], [300.0, 797.18, 81.53], [325.0, 795.94, 84.65], [350.0, 805.41, 83.9], [375.0, 795.76, 87.08], [400.0, 794.32, 88.8], [425.0, 805.74, 90.42], [450.0, 802.35, 93.09], [475.0, 798.4, 89.62], [500.0, 803.26, 87.67], [525.0, 803.35, 87.1], [550.0, 796.68, 84.82], [575.0, 805.82, 84.6], [600.0, 803.67, 83.06], [625.0, 802.88, 81.29], [650.0, 800.21, 77.85], [675.0, 794.35, 76.57], [700.0, 797.35, 73.92], [725.0, 802.31, 72.94], [750.0, 799.37, 104.7], [775.0, 805.86, 71.64], [800.0, 798.38, 70.03], [825.0, 796.72, 66.16], [850.0, 796.45, 64.42], [875.0, 804.8, 64.04], [900.0, 799.75, 63.02]], "rules": [{"column": "c2", "op": "gt", "value": 100, "level": "fail", "hint": "效率超过 100%"}]}, "attachments": [], "note": "存在 >100% 异常点"}, {"index": 3, "item_key": "dcdc_load_reg", "title": "Load Regulation", "verdict": "PASS", "unit": "%", "ts": "2026-07-31 19:32:44", "metrics": [{"key": "load_reg_pct", "label": "Load Reg", "value": -4.660678839343317, "unit": "%", "precision": 3, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}, {"key": "vout_drop", "label": "ΔV", "value": -38.1, "unit": "mV", "precision": 3, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}], "charts": [{"kind": "xy", "title": "Vout vs Iload", "x": {"key": "c0", "label": "Iload", "unit": "mA"}, "series": [{"key": "c1", "name": "Vout (mV)", "type": "scatter", "axis": "left", "unit": "mV", "label": "Vout"}], "fit": true, "id": "dcdc_load_reg_0"}], "table": {"file": "dcdc_load_reg.csv", "rows": 21, "columns": [{"key": "c0", "label": "Iload", "unit": "mA", "align": "right", "precision": 0}, {"key": "c1", "label": "Vout", "unit": "mV", "align": "right", "precision": 3}], "data": [[0.0, 812.092], [50.0, 810.28], [100.0, 807.951], [150.0, 806.396], [200.0, 804.646], [250.0, 802.669], [300.0, 800.75], [350.0, 798.687], [400.0, 796.607], [450.0, 795.073], [500.0, 792.9], [550.0, 791.28], [600.0, 789.483], [650.0, 787.238], [700.0, 785.341], [750.0, 783.768], [800.0, 781.735], [850.0, 779.502], [900.0, 777.576], [950.0, 775.691], [1000.0, 774.243]], "rules": []}, "attachments": [], "note": ""}, {"index": 4, "item_key": "dcdc_line_reg", "title": "Line Regulation", "verdict": "PASS", "unit": "%", "ts": "2026-07-31 19:32:44", "metrics": [{"key": "line_reg_pct", "label": "Line Reg", "value": 0.2896626669200616, "unit": "%", "precision": 3, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}, {"key": "vout_span", "label": "ΔV", "value": 2.4, "unit": "mV", "precision": 3, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}], "charts": [{"kind": "xy", "title": "Vout vs Vin", "x": {"key": "c0", "label": "Vin", "unit": "V"}, "series": [{"key": "c1", "name": "Vout (mV)", "type": "scatter", "axis": "left", "unit": "mV", "label": "Vout"}], "fit": true, "id": "dcdc_line_reg_0"}], "table": {"file": "dcdc_line_reg.csv", "rows": 21, "columns": [{"key": "c0", "label": "Vin", "unit": "V", "align": "right", "precision": 1}, {"key": "c1", "label": "Vout", "unit": "mV", "align": "right", "precision": 3}], "data": [[3.0, 801.236], [3.1, 799.651], [3.2, 801.284], [3.3, 801.653], [3.4, 800.877], [3.5, 800.141], [3.6, 800.617], [3.7, 799.614], [3.8, 799.334], [3.9, 801.63], [4.0, 800.859], [4.1, 800.564], [4.2, 801.541], [4.3, 800.341], [4.4, 801.392], [4.5, 801.283], [4.6, 799.807], [4.7, 799.904], [4.8, 800.003], [4.9, 799.877], [5.0, 800.707]], "rules": []}, "attachments": [], "note": ""}, {"index": 5, "item_key": "dcdc_quiescent", "title": "Quiescent Current", "verdict": "PASS", "unit": "uA", "ts": "2026-07-31 19:32:44", "metrics": [{"key": "iq", "label": "Iq", "value": 11.3, "unit": "uA", "precision": 3, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}, {"key": "divin", "label": "dIvin", "value": 12.4, "unit": "uA", "precision": 3, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}, {"key": "divout", "label": "dIvout", "value": 1.1, "unit": "uA", "precision": 3, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}], "charts": [], "table": null, "attachments": [], "note": "单点差分测"}, {"index": 6, "item_key": "dcdc_load_capability_ripple", "title": "Load Capability & Ripple", "verdict": "PASS", "unit": "mV", "ts": "2026-07-31 19:32:44", "metrics": [{"key": "max_vpp", "label": "Max Vpp", "value": 41.6, "unit": "mV", "precision": 2, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}, {"key": "max_vpp_at", "label": "@ Iload", "value": 1000.0, "unit": "mA", "precision": 0, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}], "charts": [{"kind": "xy", "title": "Vout & Ripple Vpp vs Iload", "x": {"key": "c0", "label": "Iload", "unit": "mA"}, "series": [{"key": "c1", "name": "Vout (mV)", "type": "line", "axis": "left", "unit": "mV", "label": "Vout"}, {"key": "c2", "name": "Vpp (mV)", "type": "bar", "axis": "right", "unit": "mV", "label": "Vpp"}], "id": "dcdc_load_capability_ripple_0"}], "table": {"file": "dcdc_ripple.csv", "rows": 11, "columns": [{"key": "c0", "label": "Iload", "unit": "mA", "align": "right", "precision": 0}, {"key": "c1", "label": "Vout", "unit": "mV", "align": "right", "precision": 1}, {"key": "c2", "label": "Vpp", "unit": "mV", "align": "right", "precision": 2}], "data": [[0.0, 805.0, 7.52], [100.0, 802.8, 11.24], [200.0, 800.6, 14.06], [300.0, 798.4, 19.02], [400.0, 796.2, 21.31], [500.0, 794.0, 24.92], [600.0, 791.8, 28.57], [700.0, 789.6, 32.61], [800.0, 787.4, 35.04], [900.0, 785.2, 39.44], [1000.0, 783.0, 42.0]], "rules": []}, "attachments": [], "note": ""}, {"index": 7, "item_key": "dcdc_switching_freq", "title": "Switching Frequency", "verdict": "PASS", "unit": "kHz", "ts": "2026-07-31 19:32:44", "metrics": [{"key": "fsw_min", "label": "Fsw Min", "value": 2200.0, "unit": "kHz", "precision": 3, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}, {"key": "fsw_max", "label": "Fsw Max", "value": 2200.0, "unit": "kHz", "precision": 3, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}, {"key": "fsw_pts", "label": "点数", "value": 3.0, "unit": "", "precision": 0, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}], "charts": [{"kind": "xy", "title": "Fsw vs Iload", "x": {"key": "c0", "label": "Iload", "unit": "mA"}, "series": [{"key": "c1", "name": "Fsw (kHz)", "type": "line", "axis": "left", "unit": "kHz", "label": "Fsw"}], "logx": true, "logy": true, "id": "dcdc_switching_freq_0"}], "table": {"file": "dcdc_switching_freq.csv", "rows": 12, "columns": [{"key": "c0", "label": "Iload", "unit": "mA", "align": "right", "precision": 0}, {"key": "c1", "label": "Fsw", "unit": "kHz", "align": "right", "precision": 2}], "data": [[0.0, 2201.91], [100.0, 2201.41], [200.0, 2171.12], [300.0, 2196.41], [400.0, 2180.99], [500.0, 2170.24], [600.0, 0.05], [700.0, 2180.34], [800.0, 2198.41], [900.0, 2213.51], [1000.0, 2203.39], [1100.0, 2189.56]], "rules": [{"column": "c1", "op": "outlier", "k": 5, "level": "warn", "hint": "开关频率异常突变"}]}, "attachments": [], "note": "变频模式"}, {"index": 8, "item_key": "dcdc_load_transient", "title": "Load Transient", "verdict": "PASS", "unit": "mV", "ts": "2026-07-31 19:32:44", "metrics": [{"key": "max_over", "label": "最大过冲", "value": 54.0, "unit": "mV", "precision": 1, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}, {"key": "max_under", "label": "最大欠冲", "value": 48.0, "unit": "mV", "precision": 1, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}, {"key": "groups", "label": "组数", "value": 3.0, "unit": "", "precision": 0, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}], "charts": [{"kind": "grouped_bars", "title": "Transient 分组对比", "x": {"key": "c0", "label": "Group", "unit": ""}, "series": [{"key": "c1", "name": "Overshoot (mV)", "unit": "mV", "label": "Overshoot"}, {"key": "c2", "name": "Undershoot (mV)", "unit": "mV", "label": "Undershoot"}, {"key": "c3", "name": "Vpp (mV)", "unit": "mV", "label": "Vpp"}], "id": "dcdc_load_transient_0"}], "table": {"file": "dcdc_load_transient.csv", "rows": 3, "columns": [{"key": "c0", "label": "Group", "unit": "", "align": "right", "precision": 0}, {"key": "c1", "label": "Overshoot", "unit": "mV", "align": "right", "precision": 1}, {"key": "c2", "label": "Undershoot", "unit": "mV", "align": "right", "precision": 1}, {"key": "c3", "label": "Vpp", "unit": "mV", "align": "right", "precision": 1}], "data": [[1.0, 48.0, 43.0, 107.0], [2.0, 54.0, 48.0, 119.0], [3.0, 60.0, 53.0, 131.0]], "rules": []}, "attachments": [], "note": ""}, {"index": 9, "item_key": "dcdc_line_transient", "title": "Line Transient", "verdict": "N/A", "unit": "mV", "ts": "2026-07-31 19:32:44", "metrics": [{"key": "max_over", "label": "最大过冲", "value": 31.0, "unit": "mV", "precision": 1, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}, {"key": "max_under", "label": "最大欠冲", "value": 29.5, "unit": "mV", "precision": 1, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}, {"key": "groups", "label": "组数", "value": 3.0, "unit": "", "precision": 0, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}], "charts": [{"kind": "grouped_bars", "title": "Transient 分组对比", "x": {"key": "c0", "label": "Group", "unit": ""}, "series": [{"key": "c1", "name": "Overshoot (mV)", "unit": "mV", "label": "Overshoot"}, {"key": "c2", "name": "Undershoot (mV)", "unit": "mV", "label": "Undershoot"}, {"key": "c3", "name": "Vpp (mV)", "unit": "mV", "label": "Vpp"}], "id": "dcdc_line_transient_0"}], "table": {"file": "dcdc_line_transient.csv", "rows": 3, "columns": [{"key": "c0", "label": "Group", "unit": "", "align": "right", "precision": 0}, {"key": "c1", "label": "Overshoot", "unit": "mV", "align": "right", "precision": 1}, {"key": "c2", "label": "Undershoot", "unit": "mV", "align": "right", "precision": 1}, {"key": "c3", "label": "Vpp", "unit": "mV", "align": "right", "precision": 1}], "data": [[1.0, 48.0, 43.0, 107.0], [2.0, 54.0, 48.0, 119.0], [3.0, 60.0, 53.0, 131.0]], "rules": []}, "attachments": [], "note": ""}, {"index": 10, "item_key": "dcdc_current_limit", "title": "Current Limit", "verdict": "FAIL", "unit": "mA", "ts": "2026-07-31 19:32:44", "metrics": [{"key": "limit", "label": "Current Limit", "value": 0.0, "unit": "mA", "precision": 1, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}, {"key": "peak", "label": "Peak", "value": 0.0, "unit": "mA", "precision": 1, "spec_min": null, "spec_max": null, "margin_pct": null, "verdict": null}], "charts": [{"kind": "xy", "title": "Vout vs Iload", "x": {"key": "c0", "label": "Iload", "unit": "mA"}, "series": [{"key": "c1", "name": "Vout (mV)", "type": "line", "axis": "left", "unit": "mV", "label": "Vout"}], "id": "dcdc_current_limit_0"}], "table": {"file": "dcdc_current_limit.csv", "rows": 36, "columns": [{"key": "c0", "label": "Iload", "unit": "mA", "align": "right", "precision": 0}, {"key": "c1", "label": "Vout", "unit": "mV", "align": "right", "precision": 1}], "data": [[100.0, 0.0], [200.0, 0.0], [300.0, 0.0], [400.0, 0.0], [500.0, 0.0], [600.0, 0.0], [700.0, 0.0], [800.0, 0.0], [900.0, 0.0], [1000.0, 0.0], [1100.0, 0.0], [1200.0, 0.0], [1300.0, 0.0], [1400.0, 0.0], [1500.0, 0.0], [1600.0, 0.0], [1700.0, 0.0], [1800.0, 0.0], [1900.0, 0.0], [2000.0, 0.0], [2100.0, 0.0], [2200.0, 0.0], [2300.0, 0.0], [2400.0, 0.0], [2500.0, 0.0], [2600.0, 0.0], [2700.0, 0.0], [2800.0, 0.0], [2900.0, 0.0], [3000.0, 0.0], [3100.0, 0.0], [3200.0, 0.0], [3300.0, 0.0], [3400.0, 0.0], [3500.0, 0.0], [3600.0, 0.0]], "rules": [{"type": "constant", "columns": ["c0", "c1"], "level": "warn", "hint": "列值恒定，疑似仪器/接线异常"}]}, "attachments": [], "note": "限流点未触发，恒 0"}]};

/* ================================================================
 * i18n —— 中/英文案集中管理
 * ================================================================ */
const I18N = {
  zh:{pdf:"导出 PDF",theme_dark:"深色模式",theme_light:"浅色模式",lang:"EN",
      unit:"自动量纲",unit_on:"原始量纲",expand:"全部展开",collapse:"全部折叠",
      top:"返回顶部",search_ph:"搜索测试项 / 指标 / item_key …",
      chip_all:"全部",kpi_total:"总项数",kpi_pass:"PASS",kpi_fail:"FAIL",
      kpi_na:"WARN / N/A",kpi_dur:"测试总时长",kpi_anom:"异常点",
      sec:"秒",meta:"元信息（被测件 / 环境 / 仪器 / 软件）",
      matrix:"结论汇总表",col_idx:"#",col_item:"测试项",col_verdict:"结论",
      col_metric:"关键指标（实测）",col_spec:"规格",col_margin:"余量",
      col_note:"备注",col_anom:"异常",items_title:"测试项明细",
      nospec:"未定义规格",anomalies:"个异常点",only_anom:"只看异常行",
      all_rows:"全部行",full_data:"完整测试数据",rows:"行",download:"下载 CSV",
      note:"备注",shots:"示波器截图",no_data:"无数据",no_chart:"无可绘制数据",
      no_shots:"无截图",appendix:"附录",files:"原始文件清单",conds:"测试条件",
      glossary:"术语与缩写",revision:"修订历史",signoff:"签核区",
      sign_test:"测试",sign_review:"复核",sign_approve:"批准",
      sign_date:"日期",rev_a:"Rev A",rev_init:"初版发布",
      copy_link:"复制链接",copied:"链接已复制",chart_png:"导出 PNG",
      chart_reset:"重置缩放",chart_logx:"log X",chart_logy:"log Y",
      chart_band:"规格带",chart_data:"图表数据",fit:"拟合",
      page:"页",of:"/",density:"紧凑",per_page:"每页",
      render_all:"渲染全部（便于查找）",virtual_on:"虚拟滚动",
      truncated:"仅打印前",rows_omitted:"行，其余省略（屏幕版可查看全部）",
      filter:"列筛选",export_view:"导出当前视图 CSV",
      kbd:"快捷键",kbd_open:"显示快捷键面板",
      confidential:"机密 · Confidential",generated:"生成时间",
      footer_page:"KK_Lab Module Test Report",
      gl:{Iq:"静态电流（Quiescent Current）",Vpp:"峰峰值电压（纹波）",
          fsw:"开关频率",LoadReg:"负载调整率",LineReg:"线性调整率",
          DAC:"数模转换器编码",MAD:"中位数绝对偏差（异常检测）"}},
  en:{pdf:"Export PDF",theme_dark:"Dark",theme_light:"Light",lang:"中文",
      unit:"Auto scale",unit_on:"Raw units",expand:"Expand all",collapse:"Collapse all",
      top:"Back to top",search_ph:"Search items / metrics / item_key …",
      chip_all:"All",kpi_total:"Total",kpi_pass:"PASS",kpi_fail:"FAIL",
      kpi_na:"WARN / N/A",kpi_dur:"Duration",kpi_anom:"Anomalies",
      sec:"s",meta:"Meta (DUT / Environment / Instruments / SW)",
      matrix:"Verdict Matrix",col_idx:"#",col_item:"Test Item",col_verdict:"Verdict",
      col_metric:"Key Metrics",col_spec:"Spec",col_margin:"Margin",
      col_note:"Note",col_anom:"Anom.",items_title:"Test Item Details",
      nospec:"No spec defined",anomalies:"anomalies",only_anom:"Anomalies only",
      all_rows:"All rows",full_data:"Full test data",rows:"rows",download:"Download CSV",
      note:"Note",shots:"Scope shots",no_data:"No data",no_chart:"Nothing to plot",
      no_shots:"No shots",appendix:"Appendix",files:"Raw files",conds:"Test conditions",
      glossary:"Glossary",revision:"Revision history",signoff:"Sign-off",
      sign_test:"Tested by",sign_review:"Reviewed by",sign_approve:"Approved by",
      sign_date:"Date",rev_a:"Rev A",rev_init:"Initial release",
      copy_link:"Copy link",copied:"Link copied",chart_png:"Export PNG",
      chart_reset:"Reset zoom",chart_logx:"log X",chart_logy:"log Y",
      chart_band:"Spec band",chart_data:"Chart data",fit:"fit",
      page:"Page",of:"/",density:"Compact",per_page:"Per page",
      render_all:"Render all (for find)",virtual_on:"Virtual scroll",
      truncated:"Prints first",rows_omitted:"rows; remainder omitted (see on-screen)",
      filter:"Column filters",export_view:"Export view CSV",
      kbd:"Keyboard shortcuts",kbd_open:"Show shortcuts",
      confidential:"Confidential",generated:"Generated",
      footer_page:"KK_Lab Module Test Report",
      gl:{Iq:"Quiescent current",Vpp:"Peak-to-peak voltage (ripple)",
          fsw:"Switching frequency",LoadReg:"Load regulation",LineReg:"Line regulation",
          DAC:"DAC code",MAD:"Median absolute deviation (outlier detection)"}}
};
let S = {
  lang: localStorage.getItem("rpt.lang") || "zh",
  theme: localStorage.getItem("rpt.theme") ||
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
  unitScaled: localStorage.getItem("rpt.unit") === "1",
  expandedAll: true,
  chip: "ALL",
};
const T = () => I18N[S.lang];

/* ================================================================
 * utils —— 格式化 / 量纲 / DOM
 * ================================================================ */
const $ = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined && text !== null) n.textContent = text;
  return n;
};
const esc = s => String(s ?? "").replace(/[&<>"]/g,
  c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const DASH = "—";
/* 有效位格式化（缺失 → —） */
function fmt(v, p) {
  if (v === null || v === undefined || v === "" || Number.isNaN(Number(v))) return DASH;
  const n = Number(v);
  if (p === null || p === undefined) return String(n);
  return n.toFixed(Math.min(Math.max(p, 0), 9));
}
/* 自动量纲映射（mV↔V, uA↔mA） */
const UNIT_MAP = {"mV":"V","uA":"mA","µA":"mA"};
function scaleVal(v, unit) {
  if (!S.unitScaled || !UNIT_MAP[unit] || v === null || isNaN(Number(v))) return v;
  return Number(v) / 1000;
}
function scaleUnit(u) { return (S.unitScaled && UNIT_MAP[u]) ? UNIT_MAP[u] : u; }
function unitSpan(u) {
  if (!u) return "";
  return ' <span class="unit">' + esc(scaleUnit(u)) + "</span>";
}
/* 数值节点：值 + 独立小字单位（量纲开关重渲染时更新） */
function numHTML(v, p, u) {
  const sv = scaleVal(v, u);
  const pp = (S.unitScaled && UNIT_MAP[u] && p !== null) ? Math.min(p + 3, 9) : p;
  return '<span class="num">' + fmt(sv, pp) + "</span>" + unitSpan(u);
}
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 1600);
}
/* 调色板：读 CSS 变量，保证图表导出 PNG 与主题一致 */
function pal() {
  const cs = getComputedStyle(document.documentElement);
  const g = k => cs.getPropertyValue(k).trim();
  return {accent:g("--accent"),pass:g("--pass"),fail:g("--fail"),warn:g("--warn"),
    na:g("--na"),ink2:g("--ink-2"),ink3:g("--ink-3"),grid:g("--grid"),
    raised:g("--bg-raised"),line:g("--line"),
    seq:[g("--c1"),g("--c2"),g("--c3"),g("--c4"),g("--c5"),g("--c6"),g("--c7"),g("--c8")]};
}
const VERDICT_CLS = v => v === "PASS" ? "pass" : v === "FAIL" ? "fail" : v === "WARN" ? "warn" : "na";
function badge(v, lg) {
  return '<span class="badge badge--' + VERDICT_CLS(v) + (lg ? " badge--lg" : "") +
    '" role="status">' + esc(v) + "</span>";
}

/* ================================================================
 * 规则引擎 —— 表格异常检测（gt/lt/abs_gt/eq/outlier/constant）
 * ================================================================ */
function evalRules(table) {
  const res = {cells:{}, rows:{}, count:0, banners:[]};
  if (!table || !table.rules) return res;
  const colIdx = {}; table.columns.forEach((c, i) => colIdx[c.key] = i);
  const flag = (r, c, level) => {
    const k = r + ":" + c;
    if (res.cells[k] !== "fail") res.cells[k] = level;
    res.rows[r] = res.rows[r] === "fail" ? "fail" : level;
  };
  for (const rule of table.rules) {
    if (rule.type === "constant") {
      for (const ck of (rule.columns || [])) {
        const ci = colIdx[ck]; if (ci === undefined) continue;
        const vals = table.data.map(r => r[ci]).filter(v => typeof v === "number");
        if (vals.length > 1 && vals.every(v => v === vals[0])) {
          res.banners.push("⚠ " + (table.columns[ci].label || ck) + ": " + rule.hint);
        }
      }
      continue;
    }
    const ci = colIdx[rule.column]; if (ci === undefined) continue;
    let thresh = rule.value;
    if (rule.op === "outlier") {  /* k × MAD（中位数绝对偏差） */
      const vals = table.data.map(r => r[ci])
        .filter(v => typeof v === "number").sort((a, b) => a - b);
      if (vals.length < 4) continue;
      const med = vals[Math.floor(vals.length / 2)];
      const mads = vals.map(v => Math.abs(v - med)).sort((a, b) => a - b);
      const mad = mads[Math.floor(mads.length / 2)];
      if (mad < 1e-12) continue;
      thresh = {med, lim: (rule.k || 5) * mad};
    }
    table.data.forEach((row, ri) => {
      const v = row[ci]; if (typeof v !== "number") return;
      let hit = false;
      switch (rule.op) {
        case "gt": hit = v > thresh; break;
        case "lt": hit = v < thresh; break;
        case "abs_gt": hit = Math.abs(v) > thresh; break;
        case "eq": hit = v === thresh; break;
        case "outlier": hit = Math.abs(v - thresh.med) > thresh.lim; break;
      }
      if (hit) flag(ri, ci, rule.level || "warn");
    });
  }
  res.count = Object.keys(res.rows).length;
  return res;
}

/* ================================================================
 * render: cover / KPI / meta / matrix
 * ================================================================ */
function renderCover() {
  const m = REPORT_DATA.meta || {}, t = T(), s = REPORT_DATA.summary || {};
  $("#rptTitle").textContent = m.report_title || "Module Test Report";
  $("#rptSub").innerHTML =
    (m.chip ? '<b class="mono">' + esc(m.chip) + "</b> · " : "") +
    esc(m.module_type || DASH) + " &nbsp; " + badge(s.verdict || "N/A", true);
  const dur = m.duration_s != null ? fmt(m.duration_s, 1) + " " + t.sec : DASH;
  $("#rptMeta").innerHTML =
    "<span>" + esc(t.generated) + "：<b>" + esc(m.generated_at || DASH) + "</b></span>" +
    "<span>SW：<b class='mono'>" + esc(m.sw_version || DASH) + "</b></span>" +
    "<span>" + (S.lang === "zh" ? "耗时" : "Duration") + "：<b class='num'>" + dur + "</b></span>";
  $("#printHeader").textContent =
    (m.chip ? m.chip + " · " : "") + (m.report_title || "");
  $("#printFooter").innerHTML =
    "<span>" + esc(t.footer_page) + "</span><span>" + esc(t.confidential) +
    " · " + esc(m.generated_at || "") + "</span>";
}
function renderKpis() {
  const t = T(), s = REPORT_DATA.summary || {};
  const m = REPORT_DATA.meta || {};
  const dur = m.duration_s != null ? fmt(m.duration_s, 1) : DASH;
  const cards = [
    ["", t.kpi_total, s.total, ""], ["kpi--pass", t.kpi_pass, s.pass, ""],
    ["kpi--fail", t.kpi_fail, s.fail, ""], ["kpi--na", t.kpi_na, s.na, ""],
    ["", t.kpi_dur, dur, t.sec], ["kpi--warn", t.kpi_anom, '<span id="kpiAnom">0</span>', ""],
  ];
  $("#kpis").innerHTML = cards.map(c =>
    '<div class="card kpi ' + c[0] + '"><div class="kpi__label">' + esc(c[1]) +
    '</div><div class="kpi__value">' + (String(c[2]).startsWith("<") ? c[2] : esc(c[2] ?? DASH)) +
    (c[3] ? "<small>" + esc(c[3]) + "</small>" : "") + "</div></div>").join("");
  const tot = Math.max(s.total || 0, 1);
  const seg = (cls, v) => '<i class="' + cls + '" style="width:' +
    (100 * (v || 0) / tot).toFixed(2) + '%"></i>';
  $("#stackbar").innerHTML =
    '<div class="stackbar" role="img" aria-label="verdict distribution">' +
    seg("s-pass", s.pass) + seg("s-fail", s.fail) + seg("s-na", s.na) + "</div>" +
    '<div class="stackbar-legend"><span style="color:var(--pass)">■ PASS <b>' + (s.pass || 0) +
    '</b></span><span style="color:var(--fail)">■ FAIL <b>' + (s.fail || 0) +
    '</b></span><span style="color:var(--na)">■ N/A <b>' + (s.na || 0) + "</b></span></div>";
}
function renderMeta() {
  const m = REPORT_DATA.meta || {}, t = T();
  $("#metaSummary").textContent = t.meta;
  const pair = (k, v) =>
    "<div><dt>" + esc(k) + '</dt><dd class="' +
    (typeof v === "number" ? "num" : "") + '">' +
    (v === null || v === undefined || v === "" ? DASH : esc(v)) + "</dd></div>";
  let html = '<dl class="dl">' +
    pair("Chip", m.chip) + pair("Module", m.module_type) +
    pair("Sample ID", m.sample_id) + pair("Operator", m.operator) +
    pair("Temperature (°C)", m.temperature_c) +
    pair("Start", m.start_time) + pair("End", m.end_time) +
    pair("SW Version", m.sw_version) + pair("HW Setup", m.hw_setup) +
    pair("Env TA (°C)", (m.environment || {}).ta_c) +
    pair("Humidity (%)", (m.environment || {}).humidity_pct) + "</dl>";
  const ins = m.instruments || [];
  html += '<dl class="dl" style="margin-top:8px">' +
    (ins.length ? ins.map(i =>
      pair(esc(i.name || "Instrument"),
        [i.model, i.sn, i.cal_due].filter(Boolean).join(" · ") || DASH)).join("")
      : pair("Instruments", DASH)) + "</dl>";
  $("#metaBody").innerHTML = html;
}
function metricText(it) {
  const ms = (it.metrics || []).slice(0, 2);
  if (!ms.length) return DASH;
  return ms.map(mm => '<span class="num">' + esc(mm.label) + " " +
    fmt(scaleVal(mm.value, mm.unit), mm.precision) +
    (mm.unit ? " " + esc(scaleUnit(mm.unit)) : "") + "</span>").join("；");
}
function renderMatrix() {
  const t = T(), items = REPORT_DATA.items || [];
  const rows = items.map(it => {
    const anom = (window._anom || {})[it.item_key] || 0;
    return "<tr data-v='" + it.verdict + "'>" +
      "<td class='num' style='color:var(--ink-3)'>" + it.index + "</td>" +
      "<td><a href='#item-" + it.index + "'>" + esc(it.title) + "</a>" +
      "<div class='mono' style='font-size:10.5px;color:var(--ink-3)'>" + esc(it.item_key) + "</div></td>" +
      "<td>" + badge(it.verdict) + "</td>" +
      "<td style='font-size:12px'>" + metricText(it) + "</td>" +
      "<td class='tag'>" + t.nospec + "</td><td class='num'>" + DASH + "</td>" +
      "<td style='font-size:12px;color:var(--ink-3);max-width:220px;overflow:hidden;" +
      "text-overflow:ellipsis;white-space:nowrap'>" + esc(it.note || DASH) + "</td>" +
      "<td class='num'>" + (anom ? '<span style="color:var(--warn)">⚠ ' + anom + "</span>" : DASH) +
      "</td></tr>";
  }).join("");
  $("#matrix").innerHTML =
    "<h2 class='block-title'>" + esc(t.matrix) + "</h2>" +
    "<div class='tbl-wrap'><table class='tbl compact'><thead><tr>" +
    ["col_idx","col_item","col_verdict","col_metric","col_spec","col_margin","col_note","col_anom"]
      .map(k => "<th scope='col'>" + esc(t[k]) + "</th>").join("") +
    "</tr></thead><tbody>" + rows + "</tbody></table></div>";
}

/* ================================================================
 * render: items（四段式 section）
 * ================================================================ */
function metricCard(mm) {
  const t = T();
  const hasSpec = mm.spec_min !== null && mm.spec_min !== undefined;
  const cls = mm.verdict ? " metric-card--" + VERDICT_CLS(mm.verdict) : "";
  let spec = '<span class="metric-card__nospec">' + esc(t.nospec) + "</span>";
  let bar = "";
  if (hasSpec) {
    spec = '<div class="metric-card__spec num">' + fmt(mm.spec_min, mm.precision) +
      " ~ " + fmt(mm.spec_max, mm.precision) + esc(scaleUnit(mm.unit)) + "</div>";
    const over = mm.margin_pct !== null && (mm.margin_pct < 0 || mm.margin_pct > 100);
    bar = '<div class="marginbar' + (over ? " over" : "") + '"><i style="width:' +
      Math.max(0, Math.min(100, mm.margin_pct || 0)) + '%"></i></div>';
  }
  return '<div class="metric-card' + cls + '">' +
    '<div class="metric-card__label">' + esc(mm.label) + "</div>" +
    '<div class="metric-card__value">' + numHTML(mm.value, mm.precision, mm.unit) + "</div>" +
    spec + bar + "</div>";
}
function renderItems() {
  const t = T();
  $("#items").innerHTML = (REPORT_DATA.items || []).map(it => {
    const hasTbl = !!it.table;
    const shots = (it.attachments || []).filter(a => a.type === "image");
    return '<section class="card item" id="item-' + it.index + '" data-key="' + esc(it.item_key) + '">' +
      '<div class="item__head">' +
      '<span class="idx">' + String(it.index).padStart(2, "0") + "</span>" +
      "<h3>" + esc(it.title) + "</h3>" + badge(it.verdict) +
      '<span class="item-key mono">' + esc(it.item_key) + "</span>" +
      (it.unit ? '<span class="tag">' + esc(scaleUnit(it.unit)) + "</span>" : "") +
      '<span class="item__anom" data-anom="' + it.item_key + '"></span>' +
      '<span class="item__spacer"></span>' +
      '<button class="icon-btn" data-act="link" title="' + esc(t.copy_link) + '" aria-label="' + esc(t.copy_link) + '">🔗</button>' +
      '<button class="icon-btn" data-act="fold" aria-label="collapse">▾</button></div>' +
      '<div class="item__body">' +
      ((it.metrics || []).length
        ? '<div class="metrics">' + it.metrics.map(metricCard).join("") + "</div>"
        : '<div class="empty">' + t.no_data + "</div>") +
      '<div class="charts">' + (it.charts || []).map((c, i) =>
        '<div class="chart-card"><div class="chart-card__head"><h4>' + esc(c.title) + "</h4>" +
        '<span class="sp"></span>' +
        '<button class="tbtn" data-cact="png">' + esc(t.chart_png) + "</button>" +
        (c.kind === "xy"
          ? '<button class="tbtn" data-cact="reset">' + esc(t.chart_reset) + "</button>" +
            '<button class="tbtn" data-cact="logx" aria-pressed="false">' + esc(t.chart_logx) + "</button>" +
            '<button class="tbtn" data-cact="logy" aria-pressed="false">' + esc(t.chart_logy) + "</button>" +
            '<button class="tbtn" data-cact="band" aria-pressed="true">' + esc(t.chart_band) + "</button>"
          : "") +
        '</div><div class="chart-legend"></div>' +
        '<div class="chart-box" data-item="' + esc(it.item_key) + '" data-chart="' + i + '"></div>' +
        '<details class="chart-alt"><summary>' + esc(t.chart_data) + "</summary>" +
        '<div class="chart-alt-body"></div></details></div>').join("") + "</div>" +
      (hasTbl
        ? '<details class="panel"><summary>' + esc(t.full_data) +
          "（" + esc(it.table.file || "") + " · " + it.table.rows + " " + esc(t.rows) + "）" +
          '</summary><div class="tbl-host" data-item="' + esc(it.item_key) + '"></div></details>'
        : '<div class="empty">' + t.no_data + "</div>") +
      (shots.length
        ? '<div class="block-title" style="padding:0 0 4px;font-size:12.5px">' + esc(t.shots) +
          '</div><div class="shots">' + shots.map((a, i) =>
          '<button class="shot" data-item="' + esc(it.item_key) + '" data-shot="' + i + '">' +
          '<img loading="lazy" src="' + a.full + '" alt="' + esc(a.label || "shot") + '">' +
          "<span>" + esc(a.label || "") + "</span></button>").join("") + "</div>"
        : "") +
      (it.note ? '<div class="note">' + esc(t.note) + "：" + esc(it.note) + "</div>" : "") +
      "</div></section>";
  }).join("");
}

/* ================================================================
 * render: appendix / toc
 * ================================================================ */
function renderAppendix() {
  const t = T(), m = REPORT_DATA.meta || {};
  const files = (REPORT_DATA.items || []).filter(it => it.table && it.table.file)
    .map(it => "<tr><td class='mono' style='font-size:11.5px'>" + esc(it.table.file) +
      "</td><td>" + esc(it.title) + "</td><td class='num'>" + it.table.rows + "</td></tr>").join("");
  const gl = T().gl;
  $("#appendix").innerHTML =
    "<h2 class='block-title' style='padding:0 0 8px'>" + esc(t.appendix) + "</h2>" +
    "<h4 style='margin:12px 0 4px;font-size:13px'>" + esc(t.files) + "</h4>" +
    (files ? "<table class='tbl compact'><thead><tr><th>File</th><th>Item</th><th>" +
      esc(t.rows) + "</th></tr></thead><tbody>" + files + "</tbody></table>"
      : '<div class="empty">' + t.no_data + "</div>") +
    "<h4 style='margin:16px 0 4px;font-size:13px'>" + esc(t.conds) + "</h4>" +
    '<dl class="dl">' +
    "<div><dt>Vin nominal (V)</dt><dd class='num'>" + (m.vin_nominal_v ?? DASH) + "</dd></div>" +
    "<div><dt>Vout nominal (mV)</dt><dd class='num'>" + (m.vout_nominal_mv ?? DASH) + "</dd></div>" +
    "<div><dt>Temperature (°C)</dt><dd class='num'>" + (m.temperature_c ?? DASH) + "</dd></div>" +
    "<div><dt>Operator</dt><dd>" + esc(m.operator || DASH) + "</dd></div></dl>" +
    "<h4 style='margin:16px 0 4px;font-size:13px'>" + esc(t.glossary) + "</h4>" +
    '<dl class="glossary">' + Object.keys(gl).map(k =>
      "<div><dt>" + esc(k) + "</dt><dd>" + esc(gl[k]) + "</dd></div>").join("") + "</dl>" +
    "<h4 style='margin:16px 0 4px;font-size:13px'>" + esc(t.revision) + "</h4>" +
    "<table class='tbl compact'><thead><tr><th>Rev</th><th>" + esc(t.generated) +
    "</th><th></th></tr></thead><tbody><tr><td class='mono'>" + esc(t.rev_a) + "</td><td>" +
    esc(m.generated_at || DASH) + "</td><td>" + esc(t.rev_init) + "</td></tr></tbody></table>" +
    "<h4 style='margin:16px 0 4px;font-size:13px'>" + esc(t.signoff) + "</h4>" +
    '<div class="signoff">' + [t.sign_test, t.sign_review, t.sign_approve].map(r =>
      "<div><div class='role'>" + esc(r) + "</div><div class='line'></div>" +
      "<div class='role' style='margin-top:4px'>" + esc(t.sign_date) + "</div></div>").join("") +
    "</div>";
}
function renderToc() {
  const t = T();
  $("#toc").innerHTML =
    '<div class="progress" aria-hidden="true"><i id="readBar"></i></div>' +
    '<div class="toc__title">' + esc(t.items_title) + "</div>" +
    (REPORT_DATA.items || []).map(it =>
      "<a href='#item-" + it.index + "' data-target='item-" + it.index + "'>" +
      "<span class='idx'>" + it.index + "</span>" +
      '<span class="badge badge--' + VERDICT_CLS(it.verdict) +
      '" style="padding:0;width:8px;height:8px;border-radius:50%"></span>' +
      "<span class='name'>" + esc(it.title) + "</span></a>").join("");
}

/* ================================================================
 * charts —— 纯 SVG 自绘引擎（懒渲染 / 缩放 / log / 拟合 / PNG）
 * ================================================================ */
const _chartState = new WeakMap();
function colArr(table, key) {
  const i = table.columns.findIndex(c => c.key === key);
  return i < 0 ? [] : table.data.map(r => (typeof r[i] === "number" ? r[i] : null));
}
function niceTicks(lo, hi, n) {
  if (!isFinite(lo) || !isFinite(hi)) return [0, 1];
  if (lo === hi) { lo -= 1; hi += 1; }
  const span = hi - lo, step0 = span / Math.max(n, 1);
  const mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const norm = step0 / mag;
  const step = (norm >= 5 ? 10 : norm >= 2 ? 5 : norm >= 1 ? 2 : 1) * mag;
  const t0 = Math.ceil(lo / step) * step, out = [];
  for (let v = t0; v <= hi + 1e-12; v += step) out.push(Number(v.toPrecision(12)));
  return out.length ? out : [lo, hi];
}
function logTicks(lo, hi) {
  const out = [];
  for (let e = Math.ceil(Math.log10(Math.max(lo, 1e-12))); e <= Math.floor(Math.log10(hi)); e++)
    out.push(Math.pow(10, e));
  return out.length ? out : [lo, hi];
}
function fmtTick(v) {
  if (v === 0) return "0";
  const a = Math.abs(v);
  if (a >= 1e6 || a < 1e-3) return v.toExponential(0);
  return Number(v.toPrecision(4)).toString();
}
const SVGNS = "http://www.w3.org/2000/svg";
function svgEl(tag, attrs, parent) {
  const n = document.createElementNS(SVGNS, tag);
  for (const k in (attrs || {})) n.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(n);
  return n;
}
function drawChart(box) {
  const item = (REPORT_DATA.items || []).find(it => it.item_key === box.dataset.item);
  if (!item || !item.table) return;
  const spec = item.charts[Number(box.dataset.chart)];
  if (!spec) return;
  let st = _chartState.get(box);
  if (!st) { st = {logx:false, logy:false, band:true, dom:null, hidden:{}, zoom:null};
    _chartState.set(box, st); }
  const P = pal(), table = item.table;
  const W = box.clientWidth || 720, H = box.clientHeight || 340;
  const M = {l:64, r:(spec.series || []).some(s => s.axis === "right") ? 64 : 20, t:14, b:46};
  const iw = W - M.l - M.r, ih = H - M.t - M.b;
  box.innerHTML = "";
  const svg = svgEl("svg", {width:W, height:H, role:"img",
    "aria-label":spec.title + " — " + (item.title || "")}, box);
  svgEl("rect", {x:0, y:0, width:W, height:H, fill:"transparent"}, svg);
  const tip = el("div", "chart-tip"); box.appendChild(tip);

  const col = key => colArr(table, key);
  if (spec.kind === "grouped_bars") return drawGrouped(svg, spec, table, P, M, iw, ih, st, box);
  const xs = col(spec.x.key);
  const series = (spec.series || []).filter(s => !st.hidden[s.key]);
  if (!series.length) { box.appendChild(emptyNode(T().no_chart)); return; }
  const leftS = series.filter(s => s.axis !== "right"),
        rightS = series.filter(s => s.axis === "right");
  const pairs = s => {
    const ys = col(s.key), out = [];
    xs.forEach((x, i) => { if (x !== null && ys[i] !== null &&
      (!st.logx || x > 0) && (!st.logy || ys[i] > 0)) out.push([x, ys[i]]); });
    return out;
  };
  const allPts = series.map(pairs);
  /* 值域（含缩放状态） */
  const domOf = (pts, pad) => {
    let lo = Infinity, hi = -Infinity;
    pts.flat().forEach(p => { lo = Math.min(lo, p); hi = Math.max(hi, p); });
    if (!isFinite(lo)) { lo = 0; hi = 1; }
    if (lo === hi) { lo -= 1; hi += 1; }
    const d = (hi - lo) * (pad || 0.06);
    return [lo - d, hi + d];
  };
  const xAll = allPts.map(p => p.map(q => q[0]));
  let xDom = st.dom ? st.dom.x : domOf(xAll, 0.04);
  const yDomFor = ss => {
    const pts = allPts.filter((p, i) => ss.includes(series[i])).map(p => p.map(q => q[1]));
    return domOf(pts, 0.1);
  };
  let yL = st.dom ? st.dom.yL : yDomFor(leftS.length ? leftS : series);
  let yR = rightS.length ? (st.dom && st.dom.yR ? st.dom.yR : yDomFor(rightS)) : null;
  if (spec.ref_y !== undefined && !st.dom) {
    yL = [Math.min(yL[0], spec.ref_y * 0.9), Math.max(yL[1], spec.ref_y * 1.05)];
  }
  const sx = v => {
    if (st.logx) v = Math.log10(Math.max(v, 1e-12));
    const lo = st.logx ? Math.log10(Math.max(xDom[0], 1e-12)) : xDom[0];
    const hi = st.logx ? Math.log10(Math.max(xDom[1], 1e-12)) : xDom[1];
    return M.l + (v - lo) / (hi - lo || 1) * iw;
  };
  const mkY = (dom, log) => v => {
    if (log) v = Math.log10(Math.max(v, 1e-12));
    const lo = log ? Math.log10(Math.max(dom[0], 1e-12)) : dom[0];
    const hi = log ? Math.log10(Math.max(dom[1], 1e-12)) : dom[1];
    return M.t + ih - (v - lo) / (hi - lo || 1) * ih;
  };
  const syL = mkY(yL, st.logy), syR = yR ? mkY(yR, st.logy) : null;
  /* 网格 + 轴 */
  const drawAxis = (dom, log, yFn, right, label) => {
    const ticks = log ? logTicks(dom[0], dom[1]) : niceTicks(dom[0], dom[1], 6);
    ticks.forEach(tv => {
      const y = yFn(tv);
      if (y < M.t - 1 || y > M.t + ih + 1) return;
      if (!right) svgEl("line", {x1:M.l, x2:M.l + iw, y1:y, y2:y, stroke:P.grid}, svg);
      const tx = svgEl("text", {x:right ? M.l + iw + 8 : M.l - 8, y:y + 4,
        "text-anchor":right ? "start" : "end", "font-size":10, fill:P.ink3}, svg);
      tx.textContent = fmtTick(tv);
    });
    if (label) {
      const lb = svgEl("text", {x:right ? W - 6 : 10, y:M.t + ih / 2,
        "text-anchor":"middle", "font-size":11, fill:P.ink3,
        transform:"rotate(" + (right ? 90 : -90) + " " + (right ? W - 6 : 10) + " " + (M.t + ih / 2) + ")"}, svg);
      lb.textContent = label;
    }
  };
  const xt = st.logx ? logTicks(xDom[0], xDom[1]) : niceTicks(xDom[0], xDom[1], 8);
  xt.forEach(tv => {
    const x = sx(tv);
    if (x < M.l - 1 || x > M.l + iw + 1) return;
    svgEl("line", {x1:x, x2:x, y1:M.t, y2:M.t + ih, stroke:P.grid}, svg);
    const tx = svgEl("text", {x:x, y:M.t + ih + 16, "text-anchor":"middle",
      "font-size":10, fill:P.ink3}, svg);
    tx.textContent = fmtTick(tv);
  });
  const xlab = svgEl("text", {x:M.l + iw / 2, y:H - 6, "text-anchor":"middle",
    "font-size":11, fill:P.ink3}, svg);
  xlab.textContent = spec.x.label + (spec.x.unit ? " (" + spec.x.unit + ")" : "");
  drawAxis(yL, st.logy, syL, false,
    leftS[0] ? leftS[0].label + (leftS[0].unit ? " (" + leftS[0].unit + ")" : "") : "");
  if (yR) drawAxis(yR, st.logy, syR, true,
    rightS[0] ? rightS[0].label + (rightS[0].unit ? " (" + rightS[0].unit + ")" : "") : "");
  svgEl("rect", {x:M.l, y:M.t, width:iw, height:ih, fill:"none", stroke:P.line}, svg);
  /* 规格带 */
  if (st.band && spec.spec_band) {
    const b = spec.spec_band;
    const y1 = syL(b.y_max), y2 = syL(b.y_min);
    svgEl("rect", {x:M.l, y:y1, width:iw, height:Math.max(y2 - y1, 0),
      fill:P.pass, opacity:.08}, svg);
  }
  /* 参考线（如效率 100%） */
  if (spec.ref_y !== undefined) {
    const y = syL(spec.ref_y);
    svgEl("line", {x1:M.l, x2:M.l + iw, y1:y, y2:y, stroke:P.warn,
      "stroke-dasharray":"5 4", "stroke-width":1.2}, svg);
    const tx = svgEl("text", {x:M.l + iw - 4, y:y - 5, "text-anchor":"end",
      "font-size":10, fill:P.warn}, svg);
    tx.textContent = fmtTick(spec.ref_y);
  }
  /* 系列 */
  series.forEach((s, si) => {
    const pts = allPts[series.indexOf(s)];
    const color = P.seq[si % P.seq.length];
    const yFn = s.axis === "right" && syR ? syR : syL;
    if (s.type === "bar") {
      const bw = Math.max(2, Math.min(18, iw / Math.max(pts.length, 1) * 0.5));
      pts.forEach(p => {
        const y0 = yFn(Math.max(0, yR ? yR[0] : yL[0])), y1 = yFn(p[1]);
        svgEl("rect", {x:sx(p[0]) - bw / 2, y:Math.min(y0, y1), width:bw,
          height:Math.abs(y1 - y0), fill:color, opacity:.55}, svg);
      });
    } else {
      if (s.type === "line") {
        let d = "";
        pts.forEach((p, i) => { d += (i ? "L" : "M") + sx(p[0]).toFixed(1) + " " + yFn(p[1]).toFixed(1); });
        svgEl("path", {d:d, fill:"none", stroke:color, "stroke-width":2}, svg);
      }
      if (s.type === "scatter" || pts.length <= 80) {
        pts.forEach(p => svgEl("circle", {cx:sx(p[0]), cy:yFn(p[1]), r:3,
          fill:color}, svg));
      }
    }
    /* 异常点：红色菱形异形 marker（形状+颜色双编码） */
    if (spec.anomaly && spec.anomaly.key === s.key) {
      pts.forEach(p => {
        if (spec.anomaly.op === "gt" && p[1] > spec.anomaly.value) {
          const x = sx(p[0]), y = yFn(p[1]);
          svgEl("path", {d:"M" + x + " " + (y - 6) + "L" + (x + 5) + " " + y +
            "L" + x + " " + (y + 6) + "L" + (x - 5) + " " + y + "Z",
            fill:P.fail, stroke:"#fff", "stroke-width":1}, svg);
        }
      });
    }
    /* Min/Max 标注 */
    if (spec.mark_extrema && pts.length > 2 && s.type !== "bar") {
      let mn = pts[0], mx = pts[0];
      pts.forEach(p => { if (p[1] < mn[1]) mn = p; if (p[1] > mx[1]) mx = p; });
      [["Min", mn, P.fail], ["Max", mx, P.pass]].forEach(([tag, p, c2]) => {
        svgEl("circle", {cx:sx(p[0]), cy:yFn(p[1]), r:5, fill:"none",
          stroke:c2, "stroke-width":2}, svg);
        const tx = svgEl("text", {x:sx(p[0]) + 8, cy:0, y:yFn(p[1]) - 8,
          "font-size":10, fill:c2, "font-weight":600}, svg);
        tx.textContent = tag + " " + fmtTick(p[1]);
      });
    }
    /* 线性拟合（最小二乘）+ 斜率/R² */
    if (spec.fit && pts.length > 2) {
      const n = pts.length;
      let sxv = 0, syv = 0, sxy = 0, sxx = 0;
      pts.forEach(p => { sxv += p[0]; syv += p[1]; sxy += p[0] * p[1]; sxx += p[0] * p[0]; });
      const k = (n * sxy - sxv * syv) / (n * sxx - sxv * sxv || 1);
      const b = (syv - k * sxv) / n;
      const mean = syv / n;
      let ssRes = 0, ssTot = 0;
      pts.forEach(p => { const f = k * p[0] + b;
        ssRes += (p[1] - f) * (p[1] - f); ssTot += (p[1] - mean) * (p[1] - mean); });
      const r2 = ssTot > 0 ? 1 - ssRes / ssTot : 0;
      const x0 = xDom[0], x1 = xDom[1];
      svgEl("line", {x1:sx(x0), y1:yFn(k * x0 + b), x2:sx(x1), y2:yFn(k * x1 + b),
        stroke:P.ink3, "stroke-dasharray":"6 4", "stroke-width":1.5}, svg);
      const tx = svgEl("text", {x:M.l + 8, y:M.t + 14, "font-size":11, fill:P.ink3}, svg);
      tx.textContent = T().fit + ": k=" + k.toExponential(2) + "  R²=" + r2.toFixed(4);
    }
  });
  /* 图例 */
  const legend = box.parentElement.querySelector(".chart-legend");
  if (legend) {
    legend.innerHTML = "";
    (spec.series || []).forEach((s, i) => {
      const b = el("button", st.hidden[s.key] ? "off" : "");
      b.innerHTML = '<span class="sw" style="background:' +
        P.seq[i % P.seq.length] + '"></span>' + esc(s.name);
      b.setAttribute("aria-pressed", String(!st.hidden[s.key]));
      b.onclick = () => { st.hidden[s.key] = !st.hidden[s.key]; drawChart(box); };
      legend.appendChild(b);
    });
  }
  /* 十字准线 + tooltip */
  const cross = svgEl("line", {x1:0, x2:0, y1:M.t, y2:M.t + ih, stroke:P.ink3,
    "stroke-dasharray":"3 3", visibility:"hidden"}, svg);
  svg.addEventListener("mousemove", ev => {
    if (st.zoom) return;
    const r = svg.getBoundingClientRect();
    const mx = ev.clientX - r.left;
    if (mx < M.l || mx > M.l + iw) { cross.setAttribute("visibility", "hidden");
      tip.style.display = "none"; return; }
    cross.setAttribute("x1", mx); cross.setAttribute("x2", mx);
    cross.setAttribute("visibility", "visible");
    let best = null, bd = Infinity;
    series.forEach((s, i) => allPts[i].forEach(p => {
      const d = Math.abs(sx(p[0]) - mx);
      if (d < bd) { bd = d; best = p; }
    }));
    if (!best) return;
    let h = '<div class="tt-x">' + esc(spec.x.label) + " = " +
      fmtTick(best[0]) + (spec.x.unit ? " " + esc(spec.x.unit) : "") + "</div>";
    series.forEach((s, i) => {
      const p = allPts[i].reduce((a, q) =>
        Math.abs(q[0] - best[0]) < Math.abs((a || [Infinity])[0] - best[0]) ? q : a, null);
      if (p) h += "<div>" + esc(s.name) + ": <b class='num'>" + fmtTick(p[1]) + "</b></div>";
    });
    tip.innerHTML = h; tip.style.display = "block";
    tip.style.left = Math.min(mx + 14, W - 150) + "px"; tip.style.top = "16px";
  });
  svg.addEventListener("mouseleave", () => {
    cross.setAttribute("visibility", "hidden"); tip.style.display = "none"; });
  /* 框选缩放 */
  let zr = null, zx0 = 0;
  svg.addEventListener("pointerdown", ev => {
    if (ev.button !== 0) return;
    const r = svg.getBoundingClientRect();
    const x = ev.clientX - r.left, y = ev.clientY - r.top;
    if (x < M.l || x > M.l + iw || y < M.t || y > M.t + ih) return;
    zx0 = x; st.zoom = true;
    zr = svgEl("rect", {"class":"zoom-rect", x:x, y:M.t, width:0, height:ih}, svg);
    svg.setPointerCapture(ev.pointerId);
  });
  svg.addEventListener("pointermove", ev => {
    if (!zr) return;
    const r = svg.getBoundingClientRect();
    const x = Math.max(M.l, Math.min(M.l + iw, ev.clientX - r.left));
    zr.setAttribute("x", Math.min(zx0, x));
    zr.setAttribute("width", Math.abs(x - zx0));
  });
  svg.addEventListener("pointerup", ev => {
    if (!zr) return;
    const r = svg.getBoundingClientRect();
    const x1 = Math.max(M.l, Math.min(M.l + iw, ev.clientX - r.left));
    const w = Math.abs(x1 - zx0); zr.remove(); zr = null; st.zoom = false;
    if (w > 12) {
      const inv = px => {
        const lo = st.logx ? Math.log10(Math.max(xDom[0], 1e-12)) : xDom[0];
        const hi = st.logx ? Math.log10(Math.max(xDom[1], 1e-12)) : xDom[1];
        const v = lo + (px - M.l) / iw * (hi - lo);
        return st.logx ? Math.pow(10, v) : v;
      };
      st.dom = {x:[inv(Math.min(zx0, x1)), inv(Math.max(zx0, x1))],
        yL:yL, yR:yR};
      drawChart(box);
    }
  });
  /* 图表数据替代表（无障碍） */
  const alt = box.parentElement.querySelector(".chart-alt-body");
  if (alt && !alt.dataset.done) {
    alt.dataset.done = "1";
    const cols = [spec.x].concat(spec.series || []);
    const ixs = cols.map(c => table.columns.findIndex(cc => cc.key === c.key));
    let h = "<table class='tbl compact'><thead><tr>" + cols.map(c =>
      "<th scope='col'>" + esc(c.label || c.name || "") + "</th>").join("") +
      "</tr></thead><tbody>";
    table.data.slice(0, 50).forEach(row => {
      h += "<tr>" + ixs.map(i => "<td class='num'>" +
        (i >= 0 && row[i] !== null ? esc(row[i]) : DASH) + "</td>").join("") + "</tr>";
    });
    alt.innerHTML = h + "</tbody></table>";
  }
}
function drawGrouped(svg, spec, table, P, M, iw, ih, st, box) {
  const ci = table.columns.findIndex(c => c.key === spec.x.key);
  const cats = table.data.map(r => String(r[ci] ?? ""));
  const series = spec.series.filter(s => !st.hidden[s.key]);
  const vals = series.map(s => colArr(table, s.key));
  let hi = 0;
  vals.flat().forEach(v => { if (typeof v === "number") hi = Math.max(hi, v); });
  if (!isFinite(hi) || hi <= 0) hi = 1;
  hi *= 1.15;
  const ticks = niceTicks(0, hi, 5);
  const yFn = v => M.t + ih - v / (ticks[ticks.length - 1] || 1) * ih;
  ticks.forEach(tv => {
    const y = yFn(tv);
    svgEl("line", {x1:M.l, x2:M.l + iw, y1:y, y2:y, stroke:P.grid}, svg);
    const tx = svgEl("text", {x:M.l - 8, y:y + 4, "text-anchor":"end",
      "font-size":10, fill:P.ink3}, svg);
    tx.textContent = fmtTick(tv);
  });
  const gw = iw / Math.max(cats.length, 1);
  const bw = Math.min(20, gw / (series.length + 1));
  cats.forEach((c, gi) => {
    series.forEach((s, si) => {
      const v = vals[si][gi];
      if (typeof v !== "number") return;
      const x = M.l + gi * gw + gw / 2 + (si - (series.length - 1) / 2) * (bw + 2);
      svgEl("rect", {x:x - bw / 2, y:yFn(v), width:bw, height:yFn(0) - yFn(v),
        fill:P.seq[si % P.seq.length], opacity:.85}, svg);
    });
    const tx = svgEl("text", {x:M.l + gi * gw + gw / 2, y:M.t + ih + 16,
      "text-anchor":"middle", "font-size":10, fill:P.ink3}, svg);
    tx.textContent = c.length > 8 ? c.slice(0, 8) + "…" : c;
  });
  svgEl("rect", {x:M.l, y:M.t, width:iw, height:ih, fill:"none", stroke:P.line}, svg);
  const legend = box.parentElement.querySelector(".chart-legend");
  if (legend) {
    legend.innerHTML = "";
    spec.series.forEach((s, i) => {
      const b = el("button", st.hidden[s.key] ? "off" : "");
      b.innerHTML = '<span class="sw" style="background:' +
        P.seq[i % P.seq.length] + '"></span>' + esc(s.name);
      b.onclick = () => { st.hidden[s.key] = !st.hidden[s.key]; drawChart(box); };
      legend.appendChild(b);
    });
  }
}
function emptyNode(msg) { return el("div", "empty", msg); }
/* 懒渲染：进入视口才实例化 */
let _chartIO = null;
function armLazyCharts() {
  if (_chartIO) _chartIO.disconnect();
  _chartIO = new IntersectionObserver(entries => {
    entries.forEach(en => {
      if (en.isIntersecting && !en.target.dataset.rendered) {
        en.target.dataset.rendered = "1";
        drawChart(en.target);
        _chartIO.unobserve(en.target);
      }
    });
  }, {rootMargin:"200px"});
  $$(".chart-box").forEach(b => { if (!b.dataset.rendered) _chartIO.observe(b); });
}
function renderAllCharts() {
  $$(".chart-box").forEach(b => { if (!b.dataset.rendered) {
    b.dataset.rendered = "1"; drawChart(b); } });
}
/* SVG → PNG 导出（内联属性保证离屏渲染一致） */
function exportChartPng(box, name) {
  const svg = box.querySelector("svg");
  if (!svg) return;
  const xml = new XMLSerializer().serializeToString(svg);
  const img = new Image();
  img.onload = () => {
    const cv = document.createElement("canvas");
    cv.width = svg.getAttribute("width") * 2; cv.height = svg.getAttribute("height") * 2;
    const cx = cv.getContext("2d");
    cx.fillStyle = pal().raised; cx.fillRect(0, 0, cv.width, cv.height);
    cx.drawImage(img, 0, 0, cv.width, cv.height);
    const a = document.createElement("a");
    a.download = (name || "chart") + ".png";
    a.href = cv.toDataURL("image/png"); a.click();
  };
  img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(xml);
}

/* ================================================================
 * DataTable —— 排序/列筛选/密度/分页/虚拟滚动/导出/异常高亮
 * ================================================================ */
const _tblState = new WeakMap();
function buildTable(host, item) {
  const table = item.table;
  if (!table) return;
  const t = T();
  const flags = evalRules(table);
  (window._anom = window._anom || {})[item.item_key] = flags.count;
  const st = {sort:null, filters:{}, page:1, per:25, compact:false,
    onlyAnom:host.dataset.onlyAnom === "1", renderAll:false, showFlt:false};
  _tblState.set(host, st);

  const view = () => {
    let rows = table.data.map((r, i) => ({r, i}));
    if (st.onlyAnom) rows = rows.filter(o => flags.rows[o.i]);
    const fi = Object.keys(st.filters).filter(k => st.filters[k]);
    if (fi.length) rows = rows.filter(o => fi.every(k => {
      const ci = table.columns.findIndex(c => c.key === k);
      const v = o.r[ci], f = st.filters[k].trim().toLowerCase();
      if (/^[<>]=?\s*[-\d.]/.test(f) && typeof v === "number") {
        const m = f.match(/^([<>]=?)\s*([-\d.e]+)/);
        if (m) { const rhs = parseFloat(m[2]);
          return m[1] === ">" ? v > rhs : m[1] === ">=" ? v >= rhs :
                 m[1] === "<" ? v < rhs : v <= rhs; }
      }
      return String(v ?? "").toLowerCase().includes(f);
    }));
    if (st.sort !== null) {
      const dir = st.sort.dir;
      rows = rows.slice().sort((a, b) => {
        const x = a.r[st.sort.col], y = b.r[st.sort.col];
        if (typeof x === "number" && typeof y === "number") return (x - y) * dir;
        return String(x ?? "").localeCompare(String(y ?? "")) * dir;
      });
    }
    return rows;
  };
  const cellHTML = (row, ri) => {
    let h = "";
    table.columns.forEach((c, ci) => {
      const v = row[ci];
      const fl = flags.cells[ri + ":" + ci];
      const cls = [c.align === "right" ? "r num" : "",
        fl ? "cell-" + fl : "", ci === 0 ? "fcol" : ""].join(" ").trim();
      const full = typeof v === "number" ? ' title="' + v + '"' : "";
      h += "<td class='" + cls + "'" + full + ">" +
        (typeof v === "number"
          ? esc(fmt(scaleVal(v, c.unit), S.unitScaled && UNIT_MAP[c.unit]
              ? Math.min((c.precision ?? 3) + 3, 9) : c.precision))
          : (v === null ? DASH : esc(v))) + "</td>";
    });
    return h;
  };
  const headHTML = () => {
    let h = "<tr>";
    table.columns.forEach((c, ci) => {
      const sorted = st.sort && st.sort.col === ci;
      h += "<th scope='col' class='" + (c.align === "right" ? "r" : "") +
        (ci === 0 ? " fcol" : "") + "' data-col='" + ci + "'>" + esc(c.label) +
        (c.unit ? " <span class='u'>(" + esc(scaleUnit(c.unit)) + ")</span>" : "") +
        (sorted ? "<span class='arrow'>" + (st.sort.dir > 0 ? "▲" : "▼") + "</span>" : "") +
        "</th>";
    });
    h += "</tr>";
    if (st.showFlt) {
      h += "<tr class='flt'>" + table.columns.map((c, ci) =>
        "<th class='" + (ci === 0 ? "fcol" : "") + "'><input data-fcol='" + c.key +
        "' value='" + esc(st.filters[c.key] || "") + "' aria-label='filter " +
        esc(c.label) + "'></th>").join("") + "</tr>";
    }
    return h;
  };
  const render = () => {
    const rows = view();
    const useVirtual = rows.length > 500 && !st.renderAll;
    let bodyH = "", toolsH = "";
    flags.banners.forEach(b => { toolsH += "<div class='tbl-banner'>" + esc(b) + "</div>"; });
    const rh = st.compact ? 26 : 34;
    if (useVirtual) {
      st.per = 0;  /* 虚拟滚动时不分页 */
      bodyH = "__VIRTUAL__";
    } else {
      const per = st.per || rows.length || 1;
      const pages = Math.max(1, Math.ceil(rows.length / per));
      st.page = Math.min(st.page, pages);
      const slice = rows.slice((st.page - 1) * per, st.page * per);
      bodyH = slice.map(o =>
        "<tr data-ri='" + o.i + "'>" +
        (flags.rows[o.i] ? "" : "") + cellHTML(o.r, o.i) + "</tr>").join("");
      host._pages = pages;
    }
    host.innerHTML =
      '<div class="tbl-tools">' +
      "<span>" + rows.length + " " + esc(t.rows) + (useVirtual ? " · " + esc(t.virtual_on) : "") + "</span>" +
      '<button class="tbtn btn" data-tact="flt" aria-pressed="' + st.showFlt + '">' + esc(t.filter) + "</button>" +
      '<button class="tbtn btn" data-tact="density" aria-pressed="' + st.compact + '">' + esc(t.density) + "</button>" +
      (flags.count ? '<button class="tbtn btn" data-tact="anom" aria-pressed="' + st.onlyAnom +
        '">⚠ ' + flags.count + " " + esc(t.anomalies) + "</button>" : "") +
      (useVirtual ? '<button class="tbtn btn" data-tact="all">' + esc(t.render_all) + "</button>" : "") +
      '<span style="flex:1"></span>' +
      (useVirtual ? "" : '<label>' + esc(t.per_page) +
        " <select data-tact='per'>" + [25, 50, 100, 0].map(n =>
        "<option value='" + n + "'" + (st.per === n ? " selected" : "") + ">" +
        (n || esc(t.all_rows)) + "</option>").join("") + "</select></label>") +
      '<button class="tbtn btn" data-tact="csv">' + esc(t.export_view) + "</button>" +
      '<button class="tbtn btn" data-tact="csvfile">' + esc(t.download) + "</button>" +
      "</div>" + toolsH +
      "<div class='tbl-wrap'><table class='tbl" + (st.compact ? " compact" : "") +
      "'><thead>" + headHTML() + "</thead><tbody></tbody></table></div>" +
      (useVirtual ? "" : "<div class='pager'></div>");
    const tbody = host.querySelector("tbody");
    const wr = host.querySelector(".tbl-wrap");
    if (useVirtual) {
      const total = rows.length;
      const paint = () => {
        const st2 = wr.scrollTop;
        const vh = wr.clientHeight || 480;
        const start = Math.max(0, Math.floor(st2 / rh) - 10);
        const end = Math.min(total, Math.ceil((st2 + vh) / rh) + 10);
        let h = "<tr style='height:" + (start * rh) + "px'><td colspan='" +
          table.columns.length + "'></td></tr>";
        for (let i = start; i < end; i++) {
          const o = rows[i];
          h += "<tr data-ri='" + o.i + "'>" + cellHTML(o.r, o.i) + "</tr>";
        }
        h += "<tr style='height:" + ((total - end) * rh) + "px'><td colspan='" +
          table.columns.length + "'></td></tr>";
        tbody.innerHTML = h;
      };
      wr.onscroll = () => requestAnimationFrame(paint);
      paint();
    } else {
      tbody.innerHTML = bodyH;
      const pages = host._pages || 1;
      const pg = host.querySelector(".pager");
      if (pg) {
        pg.innerHTML =
          "<button data-pg='-1'" + (st.page <= 1 ? " disabled" : "") + ">‹</button>" +
          "<span class='num'>" + esc(t.page) + " " + st.page + " " + esc(t.of) + " " + pages + "</span>" +
          "<button data-pg='1'" + (st.page >= pages ? " disabled" : "") + ">›</button>";
      }
    }
    /* 事件委托 */
    host.querySelectorAll("thead th[data-col]").forEach(th => {
      th.onclick = () => {
        const ci = Number(th.dataset.col);
        st.sort = st.sort && st.sort.col === ci && st.sort.dir > 0
          ? {col:ci, dir:-1} : {col:ci, dir:1};
        render();
      };
    });
    host.querySelectorAll("input[data-fcol]").forEach(inp => {
      inp.oninput = () => { st.filters[inp.dataset.fcol] = inp.value;
        st.page = 1; clearTimeout(inp._h);
        inp._h = setTimeout(() => { render();
          const again = host.querySelector("input[data-fcol='" + inp.dataset.fcol + "']");
          if (again) { again.focus(); again.setSelectionRange(again.value.length, again.value.length); } }, 250); };
    });
    host.querySelectorAll("[data-tact]").forEach(b => {
      const act = b.dataset.tact;
      if (act === "per") { b.onchange = () => { st.per = Number(b.value); st.page = 1; render(); }; return; }
      b.onclick = () => {
        if (act === "flt") st.showFlt = !st.showFlt;
        if (act === "density") st.compact = !st.compact;
        if (act === "anom") { st.onlyAnom = !st.onlyAnom; st.page = 1; }
        if (act === "all") st.renderAll = true;
        if (act === "csv") exportCSV(item, rows);
        if (act === "csvfile") exportCSV(item, table.data.map((r, i) => ({r, i})), table.file);
        if (act !== "csv" && act !== "csvfile") render();
      };
    });
    const pg = host.querySelector(".pager");
    if (pg) pg.querySelectorAll("[data-pg]").forEach(b => {
      b.onclick = () => { st.page += Number(b.dataset.pg); render(); };
    });
    tbody.querySelectorAll("tr[data-ri]").forEach(tr => {
      tr.onclick = () => { tbody.querySelectorAll("tr.sel")
        .forEach(x => x.classList.remove("sel")); tr.classList.add("sel"); };
    });
    /* 异常标记：行首图标 */
    tbody.querySelectorAll("tr[data-ri]").forEach(tr => {
      const ri = Number(tr.dataset.ri);
      if (flags.rows[ri]) {
        const td = tr.querySelector("td");
        if (td) td.insertAdjacentHTML("afterbegin",
          "<span class='rowflag' style='color:var(--" +
          (flags.rows[ri] === "fail" ? "fail'>✗" : "warn'>⚠") + ")</span>");
      }
    });
  };
  render();
}
function exportCSV(item, rows, fname) {
  const table = item.table;
  const head = table.columns.map(c =>
    c.label + (c.unit ? " (" + c.unit + ")" : ""));
  const lines = [head.join(",")].concat(rows.map(o =>
    o.r.map(v => {
      if (v === null || v === undefined) return "";
      const s = String(v);
      return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    }).join(",")));
  const blob = new Blob(["﻿" + lines.join("\r\n")], {type:"text/csv;charset=utf-8"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = fname || (item.item_key + "_view.csv");
  a.click(); URL.revokeObjectURL(a.href);
}
function armTables() {
  $$(".tbl-host").forEach(host => {
    if (host.dataset.done) return;
    const item = (REPORT_DATA.items || []).find(it => it.item_key === host.dataset.item);
    if (item) { host.dataset.done = "1"; buildTable(host, item); }
  });
  /* 更新 section 头部异常聚合 */
  const t = T();
  $$("[data-anom]").forEach(n => {
    const c = (window._anom || {})[n.dataset.anom] || 0;
    n.textContent = c ? "⚠ " + c + " " + t.anomalies : "";
    n.style.display = c ? "" : "none";
    n.onclick = () => {
      const item2 = (REPORT_DATA.items || [])
        .find(it => it.item_key === n.dataset.anom);
      const host = $(".tbl-host[data-item='" + n.dataset.anom + "']");
      if (!host || !item2) return;
      const det = host.closest("details");
      if (det) det.open = true;
      host.dataset.onlyAnom = "1";
      host.innerHTML = ""; host.dataset.done = "1";
      buildTable(host, item2);
    };
  });
  const k = $("#kpiAnom");
  if (k) k.textContent = Object.values(window._anom || {}).reduce((a, b) => a + b, 0);
}

/* ================================================================
 * lightbox —— 截图灯箱（←/→/Esc、滚轮缩放、caption）
 * ================================================================ */
const LB = {list:[], idx:0, scale:1};
function openLightbox(itemKey, shotIdx) {
  const item = (REPORT_DATA.items || []).find(it => it.item_key === itemKey);
  if (!item) return;
  LB.list = (item.attachments || []).filter(a => a.type === "image");
  LB.idx = Math.max(0, shotIdx); LB.scale = 1;
  paintLb();
  $("#lightbox").classList.add("show");
}
function paintLb() {
  const a = LB.list[LB.idx]; if (!a) return;
  const img = $("#lbImg");
  img.src = a.full; img.style.transform = "scale(" + LB.scale + ")";
  $("#lbCap").textContent = (a.label || "") + "  (" + (LB.idx + 1) + "/" + LB.list.length + ")";
}
function closeLightbox() { $("#lightbox").classList.remove("show"); }
function stepLb(d) {
  if (!LB.list.length) return;
  LB.idx = (LB.idx + d + LB.list.length) % LB.list.length; LB.scale = 1; paintLb();
}

/* ================================================================
 * search —— 跨测试项/指标/item_key 模糊匹配
 * ================================================================ */
function doSearch(q) {
  const pop = $("#searchPop");
  q = q.trim().toLowerCase();
  if (!q) { pop.classList.remove("show"); return; }
  const hits = [];
  (REPORT_DATA.items || []).forEach(it => {
    const hay = [it.title, it.item_key,
      ...(it.metrics || []).map(m => m.label)].join(" ").toLowerCase();
    if (hay.includes(q)) hits.push(it);
  });
  pop.innerHTML = hits.length
    ? hits.map(it => "<button role='option' data-jump='item-" + it.index + "'>" +
      "<b>" + esc(it.title) + "</b> <span class='mono' style='color:var(--ink-3)'>" +
      esc(it.item_key) + "</span></button>").join("")
    : "<button disabled>" + esc(T().no_data) + "</button>";
  pop.classList.add("show");
  pop.querySelectorAll("[data-jump]").forEach(b => {
    b.onclick = () => { jumpTo(b.dataset.jump); pop.classList.remove("show"); };
  });
}
function jumpTo(id) {
  const sec = document.getElementById(id);
  if (!sec) return;
  sec.classList.remove("collapsed");
  const det = sec.querySelector("details.panel");
  if (location.hash === "#" + id) {} else history.replaceState(null, "", "#" + id);
  sec.scrollIntoView({behavior:"smooth", block:"start"});
  sec.classList.remove("flash"); void sec.offsetWidth; sec.classList.add("flash");
}

/* ================================================================
 * scroll-spy + 阅读进度
 * ================================================================ */
function armSpy() {
  const links = $$("#toc a[data-target]");
  const bar = $("#readBar");
  let ticking = false;
  const onScroll = () => {
    if (ticking) return; ticking = true;
    requestAnimationFrame(() => {
      const pos = window.pageYOffset + 120;
      let id = null;
      $$(".item[id]").forEach(s2 => {
        if (s2.getBoundingClientRect().top + window.pageYOffset <= pos) id = s2.id;
      });
      links.forEach(l => l.classList.toggle("active", l.dataset.target === id));
      const h = document.documentElement;
      const p = h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight);
      if (bar) bar.style.width = (p * 100).toFixed(1) + "%";
      ticking = false;
    });
  };
  window.addEventListener("scroll", onScroll, {passive:true});
  onScroll();
}

/* ================================================================
 * toolbar / 状态持久化 / 键盘 / 打印
 * ================================================================ */
function paintToolbar() {
  const t = T();
  $("#btnPdf").textContent = t.pdf;
  $("#btnTheme").textContent = S.theme === "dark" ? t.theme_light : t.theme_dark;
  $("#btnTheme").setAttribute("aria-pressed", String(S.theme === "dark"));
  $("#btnLang").textContent = t.lang;
  $("#btnUnit").textContent = S.unitScaled ? t.unit_on : t.unit;
  $("#btnUnit").setAttribute("aria-pressed", String(S.unitScaled));
  $("#btnExpandAll").textContent = S.expandedAll ? t.collapse : t.expand;
  $("#btnExpandAll").setAttribute("aria-pressed", String(S.expandedAll));
  $("#btnTop").textContent = t.top;
  $("#searchInput").placeholder = t.search_ph;
  const chips = [["ALL", t.chip_all], ["PASS", "PASS"], ["FAIL", "FAIL"], ["N/A", "N/A"]];
  $("#verdictChips").innerHTML = chips.map(c =>
    "<button class='chip' data-chip='" + c[0] + "' aria-pressed='" +
    String(S.chip === c[0]) + "'>" + esc(c[1]) + "</button>").join("");
  $$("#verdictChips .chip").forEach(b => {
    b.onclick = () => {
      S.chip = b.dataset.chip; paintToolbar();
      $$("#matrix tbody tr").forEach(tr => {
        tr.style.display = S.chip === "ALL" || tr.dataset.v === S.chip ? "" : "none";
      });
    };
  });
  document.title = (REPORT_DATA.meta || {}).report_title || "Report";
}
function rerender() {
  document.documentElement.dataset.theme = S.theme;
  document.documentElement.lang = S.lang === "zh" ? "zh-CN" : "en";
  paintToolbar(); renderCover(); renderKpis(); renderMeta();
  renderItems(); renderAppendix(); renderToc();
  armTables(); renderMatrix(); armLazyCharts(); armSpy();
}
function bindGlobal() {
  $("#btnPdf").onclick = () => window.print();
  $("#btnTheme").onclick = () => {
    S.theme = S.theme === "dark" ? "light" : "dark";
    localStorage.setItem("rpt.theme", S.theme);
    document.documentElement.dataset.theme = S.theme;
    paintToolbar();
    /* 图表颜色随主题：强制重绘已渲染图表 */
    $$(".chart-box").forEach(b => { if (b.dataset.rendered) drawChart(b); });
  };
  $("#btnLang").onclick = () => {
    S.lang = S.lang === "zh" ? "en" : "zh";
    localStorage.setItem("rpt.lang", S.lang);
    rerender();
  };
  $("#btnUnit").onclick = () => {
    S.unitScaled = !S.unitScaled;
    localStorage.setItem("rpt.unit", S.unitScaled ? "1" : "0");
    rerender();
  };
  $("#btnExpandAll").onclick = () => {
    S.expandedAll = !S.expandedAll;
    $$(".item").forEach(s2 => s2.classList.toggle("collapsed", !S.expandedAll));
    $$(".item details.panel").forEach(d => { d.open = S.expandedAll; });
    paintToolbar();
  };
  $("#btnTop").onclick = () => window.scrollTo({top:0, behavior:"smooth"});
  $("#btnToc").onclick = () => $("#toc").classList.toggle("open");
  $("#searchInput").addEventListener("input", e => doSearch(e.target.value));
  $("#searchInput").addEventListener("keydown", e => {
    if (e.key === "Enter") {
      const first = $("#searchPop [data-jump]");
      if (first) { jumpTo(first.dataset.jump); $("#searchPop").classList.remove("show"); }
    }
    if (e.key === "Escape") $("#searchPop").classList.remove("show");
  });
  document.addEventListener("click", e => {
    if (!e.target.closest(".search")) $("#searchPop").classList.remove("show");
  });
  /* item 卡片内按钮/图表工具条（事件委托） */
  $("#items").addEventListener("click", e => {
    const fold = e.target.closest("[data-act='fold']");
    if (fold) {
      const sec2 = fold.closest(".item");
      sec2.classList.toggle("collapsed");
      fold.textContent = sec2.classList.contains("collapsed") ? "▸" : "▾";
      return;
    }
    const link = e.target.closest("[data-act='link']");
    if (link) {
      const sec2 = link.closest(".item");
      const url = location.href.split("#")[0] + "#" + sec2.id;
      (navigator.clipboard ? navigator.clipboard.writeText(url)
        : Promise.reject()).then(() => toast(T().copied),
        () => toast(url));
      return;
    }
    const cb = e.target.closest("[data-cact]");
    if (cb) {
      const box = cb.closest(".chart-card").querySelector(".chart-box");
      const st = _chartState.get(box);
      const act = cb.dataset.cact;
      if (act === "png") exportChartPng(box,
        (REPORT_DATA.items.find(it => it.item_key === box.dataset.item) || {}).item_key);
      if (act === "reset" && st) { st.dom = null; drawChart(box); }
      if (act === "logx" && st) { st.logx = !st.logx; st.dom = null;
        cb.setAttribute("aria-pressed", String(st.logx)); drawChart(box); }
      if (act === "logy" && st) { st.logy = !st.logy; st.dom = null;
        cb.setAttribute("aria-pressed", String(st.logy)); drawChart(box); }
      if (act === "band" && st) { st.band = !st.band;
        cb.setAttribute("aria-pressed", String(st.band)); drawChart(box); }
      return;
    }
    const shot = e.target.closest(".shot");
    if (shot) openLightbox(shot.dataset.item, Number(shot.dataset.shot));
  });
  /* lightbox */
  $("#lbClose").onclick = closeLightbox;
  $("#lbPrev").onclick = () => stepLb(-1);
  $("#lbNext").onclick = () => stepLb(1);
  $("#lightbox").addEventListener("click", e => {
    if (e.target.id === "lightbox") closeLightbox(); });
  $("#lightbox").addEventListener("wheel", e => {
    e.preventDefault();
    LB.scale = Math.max(0.4, Math.min(5, LB.scale * (e.deltaY < 0 ? 1.15 : 0.87)));
    paintLb();
  }, {passive:false});
  /* details 展开时武装表格（懒） */
  document.addEventListener("toggle", e => {
    if (e.target.matches("details") && e.target.open) armTables();
  }, true);
  /* 键盘 */
  document.addEventListener("keydown", e => {
    if (e.target.matches("input,textarea")) return;
    const items = $$(".item[id]");
    const cur = items.findIndex(s2 => {
      const r = s2.getBoundingClientRect();
      return r.top <= 140 && r.bottom > 140;
    });
    if (e.key === "/") { e.preventDefault(); $("#searchInput").focus(); }
    if (e.key === "?" ) { paintKbd(); $("#kbdModal").classList.add("show"); }
    if (e.key === "Escape") { closeLightbox(); $("#kbdModal").classList.remove("show"); }
    if (e.key === "ArrowLeft" && $("#lightbox").classList.contains("show")) stepLb(-1);
    if (e.key === "ArrowRight" && $("#lightbox").classList.contains("show")) stepLb(1);
    if (e.key === "j" || e.key === "k") {
      const nxt = items[Math.max(0, Math.min(items.length - 1,
        cur + (e.key === "j" ? 1 : -1)))];
      if (nxt) jumpTo(nxt.id);
    }
    if (e.key === "e" && cur >= 0) items[cur].classList.toggle("collapsed");
  });
  $("#kbdModal").addEventListener("click", e => {
    if (e.target.id === "kbdModal") $("#kbdModal").classList.remove("show"); });
  /* 打印前：强制浅色 + 展开全部 + 渲染全部图表；表格截断提示 */
  window.addEventListener("beforeprint", () => {
    document.documentElement.dataset.theme = "light";
    $$(".item").forEach(s2 => s2.classList.remove("collapsed"));
    $$("details").forEach(d => { d.dataset.wasOpen = d.open ? "1" : ""; d.open = true; });
    renderAllCharts(); armTables();
    $$(".tbl-wrap").forEach(w2 => {
      const rows = w2.querySelectorAll("tbody tr[data-ri]");
      if (rows.length > 200 && !w2.dataset.trimmed) {
        w2.dataset.trimmed = "1";
        rows.forEach((tr, i) => { if (i >= 100) tr.remove(); });
        const note = el("div", "tbl-banner",
          T().truncated + " 100 " + T().rows_omitted);
        w2.after(note);
      }
    });
  });
  window.addEventListener("afterprint", () => {
    document.documentElement.dataset.theme = S.theme;
    $$("details").forEach(d => { if (!d.dataset.wasOpen) d.open = false; });
  });
  window.addEventListener("resize", () => {
    $$(".chart-box").forEach(b => { if (b.dataset.rendered) drawChart(b); });
  });
}
function paintKbd() {
  const t = T();
  $("#kbdTitle").textContent = t.kbd;
  const rows = [["/", t.search_ph], ["j / k", "↑/↓ item"], ["e", "collapse"],
    ["?", t.kbd_open], ["Esc", "close"], ["← / →", "lightbox"]];
  $("#kbdTable").innerHTML = rows.map(r =>
    "<tr><td>" + esc(r[0]) + "</td><td>" + esc(r[1]) + "</td></tr>").join("");
}

/* ================================================================ boot */
rerender();
bindGlobal();
/* URL Hash 深链：#item-N 直达并展开数据表 */
if (location.hash) {
  const sec = document.querySelector(location.hash);
  if (sec && sec.classList.contains("item")) {
    sec.classList.remove("collapsed");
    const det = sec.querySelector("details.panel");
    if (det) det.open = true;
    setTimeout(() => sec.scrollIntoView({block:"start"}), 60);
  }
}

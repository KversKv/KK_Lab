# -*- coding: utf-8 -*-
r"""
APx500 驱动演示脚本
===================

演示 apx500_driver 的典型用法 (与 GUI 测试工具的调用范式一致)。

用法::

    python apx500_demo.py --list-only                     # 连接后只枚举信号路径/测量/结果图
    python apx500_demo.py                                # 默认: 跑 "Level and Gain" 并读 Level
    python apx500_demo.py --meas "Noise (RMS)" --attr Level --filters
    python apx500_demo.py --meas "THD+N" --attr ThdNRatio --gen 0.8
    python apx500_demo.py --spectrum spectrum.png         # 频谱测量并导出图片
    python apx500_demo.py --api-path "C:\Program Files\Audio Precision\APx500 9.1\API"

说明:
  * --filters 使用与 GUI 工具一致的 20Hz-20kHz 椭圆滤波 + SignalPath 加权
  * THD+N 结果: AP 文本为百分比(如 "0.0312 %")时, dB = 20*log10(|百分比|/100)
"""

import argparse
import math
import os
import sys

import apx500_driver
from apx500_driver import APxConnection

STD_FILTERS = {
    "highpass": {"enabled": True, "type": "Elliptic", "freq_hz": 20.0},
    "lowpass": {"enabled": True, "type": "Elliptic", "freq_hz": 20000.0},
    "weighting": "SignalPath",
}


def thdn_percent_to_db(percent_value):
    if percent_value is None or percent_value <= 0:
        return -999.0
    return 20 * math.log10(abs(percent_value) / 100.0)


def main():
    parser = argparse.ArgumentParser(description="APx500 驱动演示")
    parser.add_argument("--api-path", default=None,
                        help="APx500 API 目录, 默认自动检测 APx500 9.3")
    parser.add_argument("--sp", default=None, help="Signal Path 名称, 默认取第一个")
    parser.add_argument("--meas", default="Level and Gain", help="测量名 (默认 Level and Gain)")
    parser.add_argument("--attr", default="Level", help="结果属性名, 如 Level / ThdNRatio (默认 Level)")
    parser.add_argument("--filters", action="store_true", help="应用标准滤波 (20Hz-20kHz 椭圆 + SignalPath 加权)")
    parser.add_argument("--gen", type=float, default=None, metavar="VRMS", help="运行前打开发生器并设置电平 (V)")
    parser.add_argument("--spectrum", default=None, metavar="PNG", help="运行 Signal Analyzer 频谱测量并导出图片")
    parser.add_argument("--list-only", action="store_true", help="只枚举, 不运行测量")
    args = parser.parse_args()

    if args.api_path:
        ok = apx500_driver.load_ap_api(args.api_path)
        print("load_ap_api(%s) -> %s" % (args.api_path, ok))
        if not ok:
            print("加载失败:", apx500_driver._AP_LOAD_ERROR)
            return 1

    ap = APxConnection()
    print("连接 APx500 ...")
    ap.connect()
    gen_on = False
    try:
        sp_names = ap.get_signal_path_names()
        print("Signal Paths:", sp_names)
        if not sp_names:
            print("没有可用 Signal Path")
            return 1
        sp = args.sp if args.sp else sp_names[0]
        print("使用 Signal Path:", sp)

        meas_names = ap.get_measurement_names(sp)
        print("Measurements:", meas_names)
        if args.list_only:
            for mn in meas_names:
                print("  [%s] 结果图: %s" % (mn, ap.get_result_graph_names(sp, mn)))
            return 0

        meas = args.meas
        resolved = ap.resolve_measurement_name(sp, meas)
        if resolved is None:
            print("未找到测量:", meas, "(可先 --list-only 查看可用测量)")
            return 1
        print("解析测量名:", resolved)

        if args.filters:
            prop = ap.MEASUREMENT_PROPS.get(resolved)
            if prop:
                print("应用滤波:", ap.apply_analyzer_filters(prop, STD_FILTERS))
            else:
                print("跳过滤波: 未知测量的 AP 属性名")

        if args.spectrum:
            print("运行频谱测量并导出:", args.spectrum)
            ap.run_and_export_spectrum(sp, "Signal Analyzer", args.spectrum)
            print("已导出:", args.spectrum, "(%d bytes)" % os.path.getsize(args.spectrum))
            return 0

        if args.gen is not None:
            print("打开发生器: %.3f Vrms" % args.gen)
            ap.set_generator_on(args.gen)
            gen_on = True

        print("运行测量:", resolved)
        ap.run_measurement(sp, resolved)

        prefer_seq = "level" in resolved.lower() or "gain" in resolved.lower()
        prefer_meter = "thd" in resolved.lower()
        values, texts, r_name, ch_count = ap.read_by_attr(
            sp, resolved, args.attr,
            prefer_sequence=prefer_seq, prefer_active_meter=prefer_meter)
        print("-" * 50)
        print("结果: %s (%d 通道)" % (r_name, ch_count))
        print("数值:", values)
        print("AP 显示文本:", texts)
        if prefer_meter and texts and "%" in str(texts[0]):
            print("THD+N 换算: %.2f dB" % thdn_percent_to_db(values[0]))
        return 0
    finally:
        if gen_on:
            print("关闭发生器")
            ap.set_generator_off()
        ap.disconnect()
        print("已断开 APx500")


if __name__ == "__main__":
    sys.exit(main())

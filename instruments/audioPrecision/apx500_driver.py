# -*- coding: utf-8 -*-
r"""
APx500 Python 仪器驱动 (APxConnection)
=====================================

Audio Precision APx500 .NET API (`AudioPrecision.API`) 的 Python 封装, 提供:

  * 连接 / 断开 APx500 应用 (pythonnet 桥接, 自动附带显示 APx500 界面)
  * 枚举 Signal Path / Measurement / Result Graph
  * 运行单个测量或整条 Sequence, 并等待完成 (按 Sequence.Status 轮询)
  * 读取测量结果: 实时 meter 与序列结果双通道, 可配置优先策略
    (prefer_active_meter / prefer_sequence), 与 AP 软件界面对齐
  * 发生器控制: 开 / 关 / 电平设置 (BenchMode、各测量 Generator、
    SignalPathSetup、SequenceSettings 多层写入, 兼容不同 APx 版本)
  * 分析仪滤波器配置: 高通 / 低通 / 加权 (写入 active measurement、
    Analyzer、InputFilters、MeasurementFilters、SequenceMeasurement 等
    多层目标对象, 确保与 AP 界面显示一致)
  * FFT 频谱数据采集 (自动枚举候选图并按评分选择最佳频谱图, 单位可设 dBV)
  * 时域波形采集 (Signal Acquisition)
  * 频谱图导出为 PNG/图片, 以及 CSV 导出

来源: 提取自《Audio Precision 音频自动化测试工具》主程序 ap_noise_test.py
的 class APxConnection (原文件 457-2264 行)。驱动逻辑与原工具完全一致,
仅去除 GUI 依赖, 可独立 import 使用。

环境要求:
  * Windows 64 位, 已安装 Audio Precision APx500 (默认支持路径: 9.3)
  * Python 3.8+, 安装 pythonnet (pip install pythonnet)
  * .NET Framework 4.6.1+ (APx500 自带依赖)
  * 运行时 APx500 软件需可正常启动, 仪器已连接并开机

快速上手::

    from apx500_driver import APxConnection

    ap = APxConnection()
    ap.connect()
    print(ap.get_signal_path_names())

    ap.run_measurement("Signal Path 1", "Level and Gain")
    values, texts, name, ch = ap.read_by_attr(
        "Signal Path 1", "Level and Gain", "Level", prefer_sequence=True)
    print(values, texts)
    ap.disconnect()

自定义 APx500 安装路径::

    import apx500_driver
    apx500_driver.load_ap_api(r"C:\Program Files\Audio Precision\APx500 9.1\API")
"""

import os
import sys
import math
import time
import csv

__all__ = ["APxConnection", "load_ap_api", "AP_API_PATH", "HAS_AP_API", "APx500Class"]

DEFAULT_AP_API_PATH = r"C:\Program Files\Audio Precision\APx500 9.3\API"


def load_ap_api(api_path=None):
    """加载 AudioPrecision.API 程序集, 成功返回 True。

    模块 import 时已自动按默认路径 (APx500 9.3) 尝试加载一次;
    若 APx500 安装在其他位置, 可在 import 后调用本函数重新指定路径。
    加载失败原因保存在模块全局变量 ``_AP_LOAD_ERROR``。
    """
    global AP_API_PATH, HAS_AP_API, APx500Class, _AP_LOAD_ERROR
    AP_API_PATH = api_path or DEFAULT_AP_API_PATH
    try:
        if AP_API_PATH not in sys.path:
            sys.path.append(AP_API_PATH)
        import clr
        clr.AddReference("AudioPrecision.API")
        from AudioPrecision.API import APx500 as _APx500Class
        APx500Class = _APx500Class
        HAS_AP_API = True
        _AP_LOAD_ERROR = None
    except Exception as e:
        HAS_AP_API = False
        APx500Class = None
        _AP_LOAD_ERROR = e
    return HAS_AP_API


AP_API_PATH = DEFAULT_AP_API_PATH
HAS_AP_API = False
APx500Class = None
_AP_LOAD_ERROR = None

load_ap_api(AP_API_PATH)


class APxConnection:
    def __init__(self):
        self.apx = None
        self.log_callback = None

    def _diag(self, msg):
        try:
            print(msg)
        except Exception:
            pass
        cb = self.log_callback
        if cb is not None:
            try:
                cb(msg)
            except Exception:
                pass

    def connect(self):
        if not HAS_AP_API:
            raise RuntimeError(f"无法加载 AudioPrecision.API.dll\n请确认路径: {AP_API_PATH}\n并确认已安装 pythonnet (pip install pythonnet)")
        self.apx = APx500Class()
        self.apx.Visible = True
        time.sleep(1)
        return True

    def disconnect(self):
        if self.apx is not None:
            try:
                self.apx.Visible = False
            except Exception:
                pass
        self.apx = None

    @property
    def connected(self):
        if self.apx is None:
            return False
        try:
            _ = self.apx.Visible
            return True
        except Exception:
            self.apx = None
            return False

    def get_active_signal_path(self):
        return self.apx.ActiveSignalPathName

    def get_signal_path_names(self):
        names = []
        seq = self.apx.Sequence
        for i in range(seq.Count):
            try:
                sp = seq.GetSignalPath(i)
                names.append(sp.Name)
            except Exception:
                pass
        return names

    SKIP_MEASUREMENTS = {"Signal Path Setup"}

    def get_measurement_names(self, signal_path_name):
        names = []
        seq = self.apx.Sequence
        for i in range(seq.Count):
            try:
                sp = seq.GetSignalPath(i)
                if sp.Name == signal_path_name:
                    for j in range(sp.Count):
                        try:
                            m = sp.GetMeasurement(j)
                            if m.Name not in self.SKIP_MEASUREMENTS:
                                names.append(m.Name)
                        except Exception:
                            pass
                    break
            except Exception:
                pass
        return names

    def get_result_graph_names(self, signal_path_name, measurement_name):
        names = []
        try:
            self.apx.ShowMeasurement(signal_path_name, measurement_name)
            obj = self._get_active_measurement_object()
            if obj is not None:
                graphs = obj.Graphs
                for i in range(graphs.Count):
                    try:
                        g = graphs.get_Item(i)
                        names.append(g.Name)
                    except Exception:
                        pass
        except Exception:
            pass
        if not names:
            names = self._get_result_names_via_sequence(signal_path_name, measurement_name)
        return names

    def _get_result_names_via_sequence(self, signal_path_name, measurement_name):
        names = []
        try:
            seq = self.apx.Sequence
            for i in range(seq.Count):
                sp = seq.GetSignalPath(i)
                if sp.Name == signal_path_name:
                    for j in range(sp.Count):
                        m = sp.GetMeasurement(j)
                        if m.Name == measurement_name:
                            rgs = m.ResultGraphs
                            for k in range(rgs.Count):
                                try:
                                    rg = rgs.get_Item(k)
                                    names.append(rg.Name)
                                except Exception:
                                    pass
                            break
                    break
        except Exception:
            pass
        return names

    MEASUREMENT_PROPS = {
        "Noise (RMS)": "Noise",
        "Noise Recorder (RMS)": "NoiseRecorder",
        "Noise (Q-peak per ITU-R BS.468-4)": "QpeakNoise",
        "Signal to Noise Ratio": "SignalToNoiseRatio",
        "Modulated Noise": "ModulatedNoise",
        "Level and Gain": "LevelAndGain",
        "THD+N": "ThdN",
        "Frequency Response": "FrequencyResponse",
        "Signal Analyzer": "SignalAnalyzer",
        "Signal Acquisition": "SignalAcquisition",
        "DC Level": "DCLevel",
        "SINAD": "Sinad",
        "Dynamic Range - AES17": "DynamicRange",
        "Maximum Output": "MaxOutput",
        "Crosstalk, One Channel Driven": "CrosstalkOneChannelDriven",
    }

    def _get_active_measurement_object(self):
        mt = self.apx.ActiveMeasurementName
        prop_name = self.MEASUREMENT_PROPS.get(mt)
        if prop_name:
            return getattr(self.apx, prop_name, None)
        for known_name, prop in self.MEASUREMENT_PROPS.items():
            if known_name.lower() in mt.lower() or mt.lower() in known_name.lower():
                return getattr(self.apx, prop, None)
        return None

    def show_measurement(self, signal_path_name, measurement_name):
        self.apx.ShowMeasurement(signal_path_name, measurement_name)

    def resolve_measurement_name(self, signal_path_name, expected_name, auto_add=True):
        available = self.get_measurement_names(signal_path_name)
        if expected_name in available:
            return expected_name
        en_lo = expected_name.lower()
        for name in available:
            if name.lower() == en_lo:
                return name
        for name in available:
            n_lo = name.lower()
            if en_lo in n_lo or n_lo in en_lo:
                return name
        keywords = en_lo.replace("(", " ").replace(")", " ").split()
        for name in available:
            n_lo = name.lower()
            if all(kw in n_lo for kw in keywords):
                return name
        if auto_add:
            try:
                self.add_measurement(signal_path_name, expected_name)
                return expected_name
            except Exception:
                pass
        return None

    def add_measurement(self, signal_path_name, measurement_name):
        self.apx.AddMeasurement(signal_path_name, measurement_name)

    def _wait_for_sequence_done(self, timeout=15):
        # 实测: API 无 SequenceState 枚举, 正确属性为 Sequence.Status (如 "Running"/"SequenceCompleted")
        deadline = time.time() + timeout
        saw_running = False
        time.sleep(0.1)
        while time.time() < deadline:
            try:
                status = str(self.apx.Sequence.Status)
            except Exception:
                status = ""
            if "Running" in status:
                saw_running = True
            elif status and (saw_running or "Completed" in status):
                return True
            time.sleep(0.2)
        return False

    def run_measurement(self, signal_path_name, measurement_name):
        self.apx.ShowMeasurement(signal_path_name, measurement_name)
        obj = self._get_active_measurement_object()
        if obj is not None and hasattr(obj, "SequenceMeasurement"):
            sm = obj.SequenceMeasurement
            sm.Checked = True
            sm.Run()
            self._wait_for_sequence_done(timeout=15)
            return
        try:
            self.apx.Sequence.StartFromMeasurement(signal_path_name, measurement_name)
            self._wait_for_sequence_done(timeout=15)
        except Exception:
            try:
                self.apx.Sequence.Run()
                self._wait_for_sequence_done(timeout=15)
            except Exception:
                pass

    def run_sequence(self):
        self.apx.Sequence.Run()

    def _read_meter_graph(self, meter_graph):
        ch_count = meter_graph.ChannelCount
        raw_values = meter_graph.GetValues()
        raw_texts = meter_graph.GetText()
        values = [float(raw_values[i]) for i in range(ch_count)]
        texts = [str(raw_texts[i]) for i in range(ch_count)]
        name = str(meter_graph.Name)
        return values, texts, name, ch_count

    def read_measurement_result(self, signal_path_name, measurement_name, result_name=None):
        self.apx.ShowMeasurement(signal_path_name, measurement_name)
        obj = self._get_active_measurement_object()
        if obj is None:
            raise RuntimeError(f"无法获取 {measurement_name} 的测量对象")
        if result_name:
            for attr_name in dir(obj):
                if attr_name.startswith("_"):
                    continue
                try:
                    attr = getattr(obj, attr_name)
                    if hasattr(attr, "GetValues") and hasattr(attr, "ChannelCount"):
                        if hasattr(attr, "Name") and str(attr.Name) == result_name:
                            return self._read_meter_graph(attr)
                except Exception:
                    continue
        for attr_name in dir(obj):
            if attr_name.startswith("_") or attr_name.startswith("get_") or attr_name.startswith("set_"):
                continue
            try:
                attr = getattr(obj, attr_name)
                if hasattr(attr, "GetValues") and hasattr(attr, "ChannelCount"):
                    return self._read_meter_graph(attr)
            except Exception:
                continue
        return self._read_sequence_result_meter(signal_path_name, measurement_name, result_name)

    def _is_valid_result(self, result):
        if result is None:
            return False
        values = result[0]
        if not values:
            return False
        return any(abs(v) > 1e-15 and not math.isnan(v) and not math.isinf(v) for v in values)

    def _dump_measurement_attrs(self, signal_path_name, measurement_name):
        info_lines = []
        try:
            obj = self._get_active_measurement_object()
            if obj is not None:
                for attr_name in sorted(dir(obj)):
                    if attr_name.startswith("_") or attr_name.startswith("get_") or attr_name.startswith("set_"):
                        continue
                    try:
                        attr = getattr(obj, attr_name)
                        if hasattr(attr, "GetValues") and hasattr(attr, "ChannelCount"):
                            vals = attr.GetValues()
                            ch = attr.ChannelCount
                            name = str(attr.Name) if hasattr(attr, "Name") else attr_name
                            v_list = [float(vals[i]) for i in range(ch)]
                            info_lines.append(f"    meter.{attr_name} [{name}] = {v_list}")
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            seq = self.apx.Sequence
            for i in range(seq.Count):
                sp = seq.GetSignalPath(i)
                if sp.Name != signal_path_name:
                    continue
                for j in range(sp.Count):
                    m = sp.GetMeasurement(j)
                    if m.Name != measurement_name:
                        continue
                    if m.HasSequenceResults:
                        sr = m.SequenceResults
                        for k in range(sr.Count):
                            r = sr.get_Item(k)
                            rn = str(r.Name)
                            if r.HasMeterValues:
                                ch = r.ChannelCount
                                rv = r.GetMeterValues()
                                v_list = [float(rv[c]) for c in range(ch)]
                                info_lines.append(f"    seq.{rn} = {v_list}")
                    break
                break
        except Exception:
            pass
        return info_lines

    def read_by_attr(self, signal_path_name, measurement_name, attr_name, debug_log=None, prefer_active_meter=False, prefer_sequence=False):
        self.apx.ShowMeasurement(signal_path_name, measurement_name)
        if debug_log is not None:
            try:
                dump = self._dump_measurement_attrs(signal_path_name, measurement_name)
                for line in dump:
                    debug_log(line)
            except Exception:
                pass
        for attempt in range(3):
            meter_result = None
            seq_result = None
            obj = self._get_active_measurement_object()
            if obj is not None:
                meter = getattr(obj, attr_name, None)
                if meter is not None and hasattr(meter, "GetValues"):
                    try:
                        meter_result = self._read_meter_graph(meter)
                    except Exception:
                        pass
            try:
                seq_result = self._read_sequence_result_by_name(signal_path_name, measurement_name, attr_name)
            except Exception:
                pass
            if prefer_active_meter and self._is_valid_result(meter_result):
                return meter_result
            # prefer_sequence: 序列运行期间的值才是测量真值, meter读取时刻的瞬时值可能已是
            # 发生器关闭后的底噪(如"输出幅度"在测完Level后关信号测底噪的流程)
            if prefer_sequence and self._is_valid_result(seq_result):
                if debug_log is not None:
                    try:
                        debug_log(f"取值来源: 序列结果 [{seq_result[2]}] = {seq_result[0]} (prefer_sequence生效)")
                    except Exception:
                        pass
                return seq_result
            if prefer_sequence and debug_log is not None and seq_result is None:
                try:
                    debug_log(f"取值警告: 序列结果 [{attr_name}] 未找到, 回退meter {meter_result[0] if meter_result else None}")
                except Exception:
                    pass
            if self._is_valid_result(meter_result) and self._is_valid_result(seq_result):
                return meter_result
            if self._is_valid_result(meter_result):
                return meter_result
            if self._is_valid_result(seq_result):
                return seq_result
            if meter_result is not None or seq_result is not None:
                if attempt < 2:
                    time.sleep(1)
                    continue
                return meter_result if meter_result is not None else seq_result
            if attempt < 2:
                time.sleep(1)
        raise RuntimeError(f"无法读取 {measurement_name}.{attr_name} 的结果")

    def _camel_to_display(self, name):
        import re
        s = re.sub(r'([A-Z])', r' \1', name).strip()
        s = re.sub(r'\s+', ' ', s)
        return s

    def _read_sequence_result_by_name(self, signal_path_name, measurement_name, result_name):
        seq = self.apx.Sequence
        display_name = self._camel_to_display(result_name) if result_name else ""
        for i in range(seq.Count):
            sp = seq.GetSignalPath(i)
            if sp.Name != signal_path_name:
                continue
            for j in range(sp.Count):
                m = sp.GetMeasurement(j)
                if m.Name != measurement_name:
                    continue
                if not m.HasSequenceResults:
                    return None
                sr = m.SequenceResults
                for k in range(sr.Count):
                    r = sr.get_Item(k)
                    r_name = str(r.Name)
                    if result_name:
                        rn_lo = r_name.lower().replace("+", "").replace("-", "").replace(" ", "")
                        attr_lo = result_name.lower().replace("+", "").replace("-", "").replace(" ", "")
                        disp_lo = display_name.lower().replace("+", "").replace("-", "").replace(" ", "")
                        name_match = (
                            r_name == result_name
                            or rn_lo == attr_lo
                            or rn_lo == disp_lo
                            or result_name.lower() in r_name.lower()
                            or display_name.lower() in r_name.lower()
                        )
                    else:
                        name_match = True
                    if name_match and r.HasMeterValues:
                        ch_count = r.ChannelCount
                        raw_values = r.GetMeterValues()
                        values = [float(raw_values[c]) for c in range(ch_count)]
                        raw_texts = r.GetMeterText()
                        texts = [str(raw_texts[c]) for c in range(ch_count)]
                        return values, texts, r_name, ch_count
        return None

    def _read_sequence_result_meter(self, signal_path_name, measurement_name, result_name):
        seq = self.apx.Sequence
        for i in range(seq.Count):
            sp = seq.GetSignalPath(i)
            if sp.Name != signal_path_name:
                continue
            for j in range(sp.Count):
                m = sp.GetMeasurement(j)
                if m.Name != measurement_name:
                    continue
                if not m.HasSequenceResults:
                    raise RuntimeError("该测量尚未执行，没有结果数据。请先运行测试。")
                sr = m.SequenceResults
                for k in range(sr.Count):
                    r = sr.get_Item(k)
                    if result_name and r.Name != result_name:
                        continue
                    if r.HasMeterValues:
                        ch_count = r.ChannelCount
                        raw_values = r.GetMeterValues()
                        values = [float(raw_values[c]) for c in range(ch_count)]
                        raw_texts = r.GetMeterText()
                        texts = [str(raw_texts[c]) for c in range(ch_count)]
                        return values, texts, str(r.Name), ch_count
                raise RuntimeError(f"未找到可用结果: {result_name or '(any)'}")
            raise RuntimeError(f"未找到测量: {measurement_name}")
        raise RuntimeError(f"未找到信号路径: {signal_path_name}")

    def get_all_measurement_types(self):
        try:
            return list(self.apx.GetAllMeasurementNames())
        except Exception:
            return []

    def _resolve_weighting_filter_type(self, weighting_str):
        try:
            from AudioPrecision.API import WeightingFilterType
        except ImportError:
            return None
        candidates = [weighting_str]
        aliases = {
            "AWeighting": ["AWeighting", "AWeighted", "AWeight", "A"],
            "SignalPath": ["SignalPath", "SignalPathWeighting", "SignalPathFilter", "Signal Path"],
            "None": ["None", "NoWeighting", "Flat", "Unweighted"],
        }
        candidates.extend(aliases.get(weighting_str, []))
        for name in candidates:
            member = getattr(WeightingFilterType, name.replace(" ", ""), None)
            if member is not None:
                return member
        return None

    def set_noise_weighting(self, weighting_str, measurement_prop_name=None, extra_targets=None):
        try:
            wt = self._resolve_weighting_filter_type(weighting_str)
            if wt is None:
                return False
            success = False
            targets = []
            active_meas = self._get_active_measurement_object()
            if active_meas is not None:
                targets.append(active_meas)
            if measurement_prop_name and hasattr(self.apx, measurement_prop_name):
                targets.append(getattr(self.apx, measurement_prop_name))
            if hasattr(self.apx, "Noise"):
                targets.append(self.apx.Noise)
            if extra_targets:
                targets.extend(extra_targets)
            seen = set()
            for target in targets:
                if target is None:
                    continue
                target_id = id(target)
                if target_id in seen:
                    continue
                seen.add(target_id)
                for attr in ("NoiseWeighting", "WeightingFilter", "AnalyzerWeighting", "Weighting", "FilterType", "WeightingFilterType"):
                    if hasattr(target, attr):
                        try:
                            setattr(target, attr, wt)
                            success = True
                            break
                        except Exception:
                            pass
                for en_attr in ("NoiseWeightingEnabled", "WeightingFilterEnabled", "AnalyzerWeightingEnabled", "WeightingEnabled"):
                    if hasattr(target, en_attr):
                        try:
                            setattr(target, en_attr, weighting_str != "None")
                            success = True
                        except Exception:
                            pass
            return success
        except Exception as e:
            print(f"设置加权滤波失败: {e}")
        return False

    def set_bandwidth_22k(self, measurement_prop_name):
        results = []
        try:
            meas = getattr(self.apx, measurement_prop_name, None)
            if meas is None:
                return "meas not found"
            if hasattr(meas, "LowpassFilterFrequencyEnabled"):
                meas.LowpassFilterFrequencyEnabled = True
                results.append("Enabled=True")
            if hasattr(meas, "LowpassFilterFrequency"):
                lpf = meas.LowpassFilterFrequency
                if hasattr(lpf, "Value"):
                    lpf.Value = 22400.0
                    results.append("LPF.Value=22400")
                elif hasattr(lpf, "SetValue"):
                    lpf.SetValue(22400.0)
                    results.append("LPF.SetValue=22400")
                else:
                    meas.LowpassFilterFrequency = 22400.0
                    results.append("LPF=22400")
        except Exception as e:
            results.append(f"error:{e}")
        return ", ".join(results) if results else "no action"

    def _set_filter_value(self, container, attr_name, value):
        if not hasattr(container, attr_name):
            return False
        target = getattr(container, attr_name)
        try:
            if hasattr(target, "Value"):
                target.Value = value
                return True
            if hasattr(target, "SetValue"):
                target.SetValue(value)
                return True
            setattr(container, attr_name, value)
            return True
        except Exception:
            return False

    def _resolve_filter_type_enum(self, type_str):
        try:
            from AudioPrecision import API as _ap_api
        except Exception:
            return None
        for enum_name in ("HighpassFilterType", "LowpassFilterType", "FilterType",
                           "AnalyzerFilterType", "FilterShape"):
            enum_cls = getattr(_ap_api, enum_name, None)
            if enum_cls is None:
                continue
            member = getattr(enum_cls, type_str, None)
            if member is not None:
                return member
        return None

    def _get_filter_targets(self, measurement_prop_name):
        targets = []
        active_meas = self._get_active_measurement_object()
        if active_meas is not None:
            targets.append(("active", active_meas))
        meas = getattr(self.apx, measurement_prop_name, None)
        if meas is not None:
            targets.append((measurement_prop_name, meas))
        expanded = []
        seen = set()
        for name, target in targets:
            if target is None:
                continue
            for child_name in (None, "Analyzer", "InputFilters", "MeasurementFilters", "Filters", "SequenceMeasurement"):
                child = target if child_name is None else getattr(target, child_name, None)
                if child is None:
                    continue
                child_id = id(child)
                if child_id in seen:
                    continue
                seen.add(child_id)
                expanded.append((name if child_name is None else f"{name}.{child_name}", child))
        return expanded

    def _apply_filter_to_target(self, target, filter_cfg, prefix, results, target_name):
        if not filter_cfg:
            return
        enabled = bool(filter_cfg.get("enabled", True))
        en_attrs = (f"{prefix}FilterFrequencyEnabled", f"{prefix}FilterEnabled", f"{prefix}Enabled")
        for en_attr in en_attrs:
            if hasattr(target, en_attr):
                try:
                    setattr(target, en_attr, enabled)
                    results.append(f"{target_name}.{prefix}.{en_attr}={enabled}")
                    break
                except Exception:
                    pass
        ft = self._resolve_filter_type_enum(filter_cfg.get("type", ""))
        if ft is not None:
            for t_attr in (f"{prefix}FilterType", f"{prefix}Shape", f"{prefix}Type"):
                if hasattr(target, t_attr):
                    try:
                        setattr(target, t_attr, ft)
                        results.append(f"{target_name}.{prefix}.type={filter_cfg.get('type')}")
                        break
                    except Exception:
                        pass
        if filter_cfg.get("freq_hz") is not None:
            for f_attr in (f"{prefix}FilterFrequency", f"{prefix}Frequency", f"{prefix}CutoffFrequency"):
                if self._set_filter_value(target, f_attr, float(filter_cfg["freq_hz"])):
                    results.append(f"{target_name}.{prefix}.freq={filter_cfg['freq_hz']}")
                    break

    def apply_analyzer_filters(self, measurement_prop_name, filters):
        if not filters:
            return "no filters"
        results = []
        try:
            targets = self._get_filter_targets(measurement_prop_name)
            if not targets:
                return "meas not found"
            hp = filters.get("highpass")
            lp = filters.get("lowpass")
            for target_name, target in targets:
                self._apply_filter_to_target(target, hp, "Highpass", results, target_name)
                self._apply_filter_to_target(target, lp, "Lowpass", results, target_name)
            weighting = filters.get("weighting")
            if weighting:
                ok = self.set_noise_weighting(weighting, measurement_prop_name, [target for _, target in targets])
                results.append(f"weighting={weighting}({'OK' if ok else 'NA'})")
        except Exception as e:
            results.append(f"error:{e}")
        return ", ".join(results) if results else "no action"

    def set_generator_on(self, level_vrms=0.8):
        from AudioPrecision.API import OutputConnectorType, OutputChannelIndex
        try:
            setup = self.apx.SignalPathSetup
            setup.SequenceSettings.OutputConnector = OutputConnectorType.AnalogBalanced
        except Exception:
            pass
        try:
            self.apx.BenchMode.Generator.AutoOn = True
        except Exception:
            pass
        try:
            bench_gen = self.apx.BenchMode.Generator
            bench_gen.On = True
            bench_gen.Levels.SetValue(OutputChannelIndex.Ch1, level_vrms)
            try:
                bench_gen.Levels.SetValue(OutputChannelIndex.Ch2, level_vrms)
            except Exception:
                pass
        except Exception:
            pass
        measurement_props = ["LevelAndGain", "ThdN", "Noise"]
        for prop_name in measurement_props:
            try:
                meas = getattr(self.apx, prop_name, None)
                if meas is None:
                    continue
                gen = meas.Generator
                gen.On = True
                gen.Levels.SetValue(OutputChannelIndex.Ch1, level_vrms)
                try:
                    gen.Levels.SetValue(OutputChannelIndex.Ch2, level_vrms)
                except Exception:
                    pass
            except Exception:
                pass
            try:
                meas = getattr(self.apx, prop_name, None)
                if meas is not None and hasattr(meas, "SequenceMeasurement"):
                    sm = meas.SequenceMeasurement
                    if hasattr(sm, "Generator"):
                        sm.Generator.On = True
                        sm.Generator.Levels.SetValue(OutputChannelIndex.Ch1, level_vrms)
            except Exception:
                pass
        try:
            setup = self.apx.SignalPathSetup
            gen = setup.Generator
            gen.On = True
            gen.Levels.SetValue(OutputChannelIndex.Ch1, level_vrms)
            try:
                gen.Levels.SetValue(OutputChannelIndex.Ch2, level_vrms)
            except Exception:
                pass
        except Exception:
            pass
        try:
            gen_setup = self.apx.SignalPathSetup.SequenceSettings.Generator
            gen_setup.On = True
            gen_setup.Levels.SetValue(OutputChannelIndex.Ch1, level_vrms)
        except Exception:
            pass

    def set_generator_off(self):
        errors = []
        try:
            self.apx.BenchMode.Generator.AutoOn = False
        except Exception as e:
            errors.append(f"BenchMode.AutoOn: {e}")
        try:
            self.apx.BenchMode.Generator.On = False
        except Exception as e:
            errors.append(f"BenchMode.On: {e}")
        measurement_props = ["LevelAndGain", "ThdN", "Noise"]
        from AudioPrecision.API import OutputChannelIndex
        for prop_name in measurement_props:
            try:
                meas = getattr(self.apx, prop_name, None)
                if meas is None:
                    continue
                meas.Generator.On = False
                meas.Generator.Levels.SetValue(OutputChannelIndex.Ch1, 0.0)
            except Exception as e:
                errors.append(f"{prop_name}.Generator: {e}")
            try:
                meas = getattr(self.apx, prop_name, None)
                if meas is not None and hasattr(meas, "SequenceMeasurement"):
                    sm = meas.SequenceMeasurement
                    if hasattr(sm, "Generator"):
                        sm.Generator.On = False
            except Exception:
                pass
        try:
            setup = self.apx.SignalPathSetup
            setup.Generator.On = False
        except Exception:
            pass
        try:
            self.apx.SignalPathSetup.SequenceSettings.Generator.On = False
        except Exception:
            pass
        return errors

    def set_measurement_generator(self, ap_prop, on, level_vrms=0.0):
        try:
            meas = getattr(self.apx, ap_prop, None)
            if meas is None:
                return
            gen = meas.Generator
            if on:
                gen.On = True
                if level_vrms > 0:
                    from AudioPrecision.API import OutputChannelIndex
                    gen.Levels.SetValue(OutputChannelIndex.Ch1, level_vrms)
            else:
                from AudioPrecision.API import OutputChannelIndex
                gen.Levels.SetValue(OutputChannelIndex.Ch1, 0.0)
                gen.On = False
        except Exception:
            pass

    def set_active_generator(self, on, level_vrms=0.8):
        from AudioPrecision.API import OutputChannelIndex
        try:
            active_meas = self._get_active_measurement_object()
            if active_meas is not None:
                gen = active_meas.Generator
                gen.On = on
                if on and level_vrms > 0:
                    gen.Levels.SetValue(OutputChannelIndex.Ch1, level_vrms)
                    try:
                        gen.Levels.SetValue(OutputChannelIndex.Ch2, level_vrms)
                    except Exception:
                        pass
                elif not on:
                    try:
                        gen.Levels.SetValue(OutputChannelIndex.Ch1, 0.0)
                    except Exception:
                        pass
                return True
        except Exception:
            pass
        try:
            self.apx.BenchMode.Generator.On = on
            if on and level_vrms > 0:
                self.apx.BenchMode.Generator.Levels.SetValue(OutputChannelIndex.Ch1, level_vrms)
        except Exception:
            pass
        return False

    def _clean_api_name(self, text):
        return "".join(ch.lower() for ch in str(text) if ch.isalnum())

    def _resolve_api_member_by_names(self, enum_names, candidate_names):
        try:
            from AudioPrecision import API as _ap_api
        except Exception:
            return None
        wanted = {self._clean_api_name(name) for name in candidate_names}
        for enum_name in enum_names:
            enum_cls = getattr(_ap_api, enum_name, None)
            if enum_cls is None:
                continue
            for member_name in dir(enum_cls):
                if member_name.startswith("_"):
                    continue
                if self._clean_api_name(member_name) in wanted:
                    try:
                        return getattr(enum_cls, member_name)
                    except Exception:
                        pass
        return None

    def _try_set_unit_attr(self, target, attr_name, unit_value):
        if target is None or not hasattr(target, attr_name):
            return False
        try:
            current = getattr(target, attr_name)
            if hasattr(current, "Value"):
                current.Value = unit_value
            elif hasattr(current, "SetValue"):
                current.SetValue(unit_value)
            else:
                setattr(target, attr_name, unit_value)
            return True
        except Exception:
            return False

    def _try_set_unit_method(self, target, method_name, unit_value):
        if target is None or not hasattr(target, method_name):
            return False
        try:
            method = getattr(target, method_name)
            try:
                method(unit_value)
                return True
            except Exception:
                pass
            try:
                from AudioPrecision.API import VerticalAxis
                method(VerticalAxis.Left, unit_value)
                return True
            except Exception:
                pass
        except Exception:
            pass
        return False

    def set_spectrum_unit_dbv(self, measurement_obj=None, log_success=True, log_failure=False):
        enum_names = (
            "AmplitudeUnit", "AmplitudeUnits", "LevelUnit", "LevelUnits", "MeasurementUnit",
            "MeterUnit", "GraphUnit", "VerticalAxisUnit", "SpectrumUnit", "FftSpectrumUnit",
            "FftAmplitudeUnit", "FFTAmplitudeUnit", "Unit", "Units",
        )
        candidate_names = ("dBV", "DBV", "Dbv", "dBVrms", "DBVrms", "VoltsDb", "VoltsDB", "VoltDb", "VoltDB")
        unit_values = []
        enum_value = self._resolve_api_member_by_names(enum_names, candidate_names)
        if enum_value is not None:
            unit_values.append(enum_value)
        unit_values.extend(["dBV", "DBV"])
        attr_names = (
            "AmplitudeUnit", "AmplitudeUnits", "LevelUnit", "LevelUnits", "MeasurementUnit",
            "ResultUnit", "ResultUnits", "SpectrumUnit", "SpectrumUnits", "MagnitudeUnit", "MagnitudeUnits",
            "VerticalAxisUnit", "VerticalAxisUnits", "YAxisUnit", "YAxisUnits", "YUnit", "YUnits",
            "FftAmplitudeUnit", "FFTAmplitudeUnit", "Unit", "Units",
        )
        method_names = (
            "SetAmplitudeUnit", "SetAmplitudeUnits", "SetLevelUnit", "SetLevelUnits", "SetMeasurementUnit",
            "SetResultUnit", "SetSpectrumUnit", "SetMagnitudeUnit", "SetVerticalAxisUnit", "SetYAxisUnit",
            "SetYUnit", "SetUnit", "SetUnits",
        )
        targets = []
        if measurement_obj is not None:
            targets.append(measurement_obj)
        active = self._get_active_measurement_object()
        if active is not None and all(id(active) != id(t) for t in targets):
            targets.append(active)
        for target in list(targets):
            try:
                if hasattr(target, "Graphs"):
                    graphs = target.Graphs
                    for i in range(int(graphs.Count)):
                        try:
                            targets.append(graphs.get_Item(i))
                        except Exception:
                            pass
            except Exception:
                pass
            for axis_attr in ("YAxis", "YAxisLeft", "LeftAxis", "VerticalAxis", "VerticalAxisLeft", "AmplitudeAxis"):
                try:
                    axis = getattr(target, axis_attr, None)
                    if axis is not None:
                        targets.append(axis)
                except Exception:
                    pass
        applied = []
        seen = set()
        for target in targets:
            try:
                key = id(target)
            except Exception:
                key = str(target)
            if key in seen:
                continue
            seen.add(key)
            for unit_value in unit_values:
                for attr_name in attr_names:
                    if self._try_set_unit_attr(target, attr_name, unit_value):
                        applied.append(f"{type(target).__name__}.{attr_name}=dBV")
                        break
                for method_name in method_names:
                    if self._try_set_unit_method(target, method_name, unit_value):
                        applied.append(f"{type(target).__name__}.{method_name}=dBV")
                        break
        if applied and log_success:
            self._diag(f"[APController] AP频谱单位设置为 dBV: {applied[:8]}")
        elif not applied and log_failure:
            self._diag("[APController] AP频谱单位 dBV 未找到可写属性，保留AP当前显示单位")
        return applied

    def configure_fft_settings(self, signal_path_name, measurement_name):
        from AudioPrecision.API import FFTLength, WindowType, AveragingType, TriggerType
        resolved = self.resolve_measurement_name(signal_path_name, measurement_name, auto_add=True)
        if resolved is None:
            return
        self.apx.ShowMeasurement(signal_path_name, resolved)
        obj = self._get_active_measurement_object()
        if obj is None:
            return
        try:
            obj.FFTLength = FFTLength.FFT_48000
        except Exception:
            pass
        try:
            obj.WindowType = WindowType.Equiripple
        except Exception:
            pass
        try:
            obj.AveragingType = AveragingType.Power
        except Exception:
            pass
        try:
            obj.Averages = 7
        except Exception:
            pass
        try:
            obj.TriggerType = TriggerType.FreeRun
        except Exception:
            pass
        try:
            obj.DelayTimeInSeconds = 0.250
            obj.UseDelayTimeInSeconds = True
        except Exception:
            pass
        self.set_spectrum_unit_dbv(obj, log_success=False, log_failure=False)

    def configure_signal_acquisition_settings(self, signal_path_name, measurement_name, acquisition_time=10.0):
        resolved = self.resolve_measurement_name(signal_path_name, measurement_name, auto_add=True)
        if resolved is None:
            return None
        self.apx.ShowMeasurement(signal_path_name, resolved)
        obj = self._get_active_measurement_object()
        if obj is None:
            return resolved

        try:
            related = [a for a in dir(obj) if not a.startswith("_") and any(
                k in a.lower() for k in ("acq", "length", "unit", "trigger", "delay", "duration", "second"))]
            self._diag(f"[APController] Signal Acquisition 对象相关属性: {related}")
        except Exception:
            pass

        applied = []
        secs = float(acquisition_time)

        if hasattr(obj, "AcquisitionType"):
            try:
                from AudioPrecision import API as _ap_api
                acq_type_enum = getattr(_ap_api, "AcquisitionType", None)
                seconds_member = None
                if acq_type_enum is not None:
                    for member_name in ("Seconds", "FixedLength", "FixedTime", "Time", "Length"):
                        if hasattr(acq_type_enum, member_name):
                            seconds_member = getattr(acq_type_enum, member_name)
                            break
                if seconds_member is not None:
                    obj.AcquisitionType = seconds_member
                    applied.append(f"AcquisitionType={member_name}")
            except Exception:
                pass

        if hasattr(obj, "AcquisitionSeconds"):
            try:
                obj.AcquisitionSeconds = secs
                applied.append("AcquisitionSeconds")
            except Exception:
                pass

        if not any(a.startswith("AcquisitionSeconds") for a in applied) and hasattr(obj, "set_AcquisitionSeconds"):
            try:
                obj.set_AcquisitionSeconds(secs)
                applied.append("set_AcquisitionSeconds")
            except Exception:
                pass

        try:
            cur = None
            if hasattr(obj, "AcquisitionSeconds"):
                cur = obj.AcquisitionSeconds
            self._diag(f"[APController] Signal Acquisition 读回 AcquisitionSeconds={cur}")
        except Exception:
            pass

        try:
            self._diag(f"[APController] Signal Acquisition 采集时长设置 {secs}s -> 已应用: {applied if applied else '(无匹配属性, 见上方相关属性列表)'}")
        except Exception:
            pass
        return resolved

    def run_and_export_spectrum(self, signal_path_name, measurement_name, save_path):
        resolved = self.resolve_measurement_name(signal_path_name, measurement_name, auto_add=True)
        if resolved is None:
            raise RuntimeError(f"无法找到或添加测量: {measurement_name}")
        self.apx.ShowMeasurement(signal_path_name, resolved)
        self.configure_fft_settings(signal_path_name, measurement_name)
        obj = self._get_active_measurement_object()
        if obj is not None and hasattr(obj, "SequenceMeasurement"):
            sm = obj.SequenceMeasurement
            sm.Checked = True
            sm.Run()
            self._wait_for_sequence_done(timeout=30)
        else:
            try:
                self.apx.Sequence.StartFromMeasurement(signal_path_name, resolved)
                self._wait_for_sequence_done(timeout=30)
            except Exception:
                self.apx.Sequence.Run()
                self._wait_for_sequence_done(timeout=30)
        self.apx.ShowMeasurement(signal_path_name, resolved)
        obj = self._get_active_measurement_object()
        self.set_spectrum_unit_dbv(obj, log_success=False, log_failure=False)
        if self._save_spectrum_image(signal_path_name, resolved, obj, save_path):
            return resolved
        raise RuntimeError(f"无法保存频谱图片: {measurement_name}")

    def _save_spectrum_image(self, signal_path_name, measurement_name, measurement_obj, save_path):
        candidates = []
        seen = set()

        def add_candidate(graph):
            if graph is None:
                return
            try:
                key = id(graph)
            except Exception:
                key = str(graph)
            if key in seen:
                return
            seen.add(key)
            candidates.append(graph)

        try:
            if measurement_obj is not None and hasattr(measurement_obj, "Graphs"):
                graphs = measurement_obj.Graphs
                for gi in range(graphs.Count):
                    add_candidate(graphs.get_Item(gi))
        except Exception:
            pass
        try:
            seq = self.apx.Sequence
            for i in range(seq.Count):
                sp = seq.GetSignalPath(i)
                if sp.Name != signal_path_name:
                    continue
                for j in range(sp.Count):
                    m = sp.GetMeasurement(j)
                    if m.Name != measurement_name:
                        continue
                    if hasattr(m, "ResultGraphs"):
                        rgs = m.ResultGraphs
                        for k in range(rgs.Count):
                            rg = rgs.get_Item(k)
                            try:
                                if hasattr(rg, "Show"):
                                    rg.Show()
                            except Exception:
                                pass
                            self.apx.ShowMeasurement(signal_path_name, measurement_name)
                            measurement_obj = self._get_active_measurement_object()
                            try:
                                if measurement_obj is not None and hasattr(measurement_obj, "Graphs"):
                                    graphs = measurement_obj.Graphs
                                    for gi in range(graphs.Count):
                                        add_candidate(graphs.get_Item(gi))
                            except Exception:
                                pass
                            add_candidate(rg)
                    break
                break
        except Exception:
            pass
        try:
            if measurement_obj is not None:
                for attr_name in sorted(dir(measurement_obj)):
                    if attr_name.startswith("_"):
                        continue
                    attr = getattr(measurement_obj, attr_name)
                    if hasattr(attr, "Save") or (hasattr(attr, "GetXValues") and hasattr(attr, "GetYValues")):
                        add_candidate(attr)
        except Exception:
            pass
        ordered_candidates = sorted(candidates, key=self._score_spectrum_graph_candidate, reverse=True)
        unit_logged = False
        for graph in ordered_candidates:
            applied = self.set_spectrum_unit_dbv(graph, log_success=False, log_failure=False)
            if applied and not unit_logged:
                self._diag(f"[APController] AP频谱单位设置为 dBV: {applied[:8]}")
                unit_logged = True
            if self._try_save_graph_image(graph, save_path):
                return True
        if not unit_logged:
            self._diag("[APController] AP频谱单位 dBV 未找到图表轴可写属性，保留AP当前显示单位")
        return False

    def _score_spectrum_graph_candidate(self, graph):
        score = 0
        try:
            title = str(getattr(graph, "Title", ""))
            name = str(getattr(graph, "Name", ""))
            text = f"{title} {name}".lower()
            if "fft" in text and "spectrum" in text:
                score += 20
            elif any(keyword in text for keyword in ("spectrum", "spectral", "frequency", "频谱")):
                score += 10
            if any(keyword in text for keyword in ("scope", "waveform", "time")):
                score -= 50
        except Exception:
            pass
        try:
            if self._looks_like_xy_graph(graph):
                score += 5
        except Exception:
            pass
        try:
            x_vals, y_vals = self._get_xy_data_from_graph(graph, 0, 1, prefer="frequency")
            data_score, info = self._score_graph_data("fft", x_vals, y_vals)
            score += data_score
            if info and info.get("x_max") is not None and info.get("x_max") <= 1.5:
                score -= 50
        except Exception:
            pass
        return score

    def _looks_like_xy_graph(self, graph):
        try:
            title = str(getattr(graph, "Title", ""))
            name = str(getattr(graph, "Name", ""))
            text = f"{title} {name}".lower()
            if any(keyword in text for keyword in ("fft", "spectrum", "spectral", "frequency", "频谱")):
                return True
        except Exception:
            pass
        if hasattr(graph, "GetValues") and hasattr(graph, "GetXValues") and hasattr(graph, "GetYValues"):
            try:
                from AudioPrecision.API import VerticalAxis
                for ch in (0, 1):
                    try:
                        x_vals = graph.GetXValues(ch, 1, VerticalAxis.Left)
                        y_vals = graph.GetYValues(ch, 1, VerticalAxis.Left)
                        if len(x_vals) > 1 and len(y_vals) > 1:
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
        return False

    def _try_save_graph_image(self, graph, save_path):
        try:
            if hasattr(graph, "Show"):
                graph.Show()
                time.sleep(0.2)
        except Exception:
            pass
        try:
            from AudioPrecision.API import GraphImageType
            image_type = getattr(GraphImageType, os.path.splitext(save_path)[1].lstrip(".").upper(), GraphImageType.PNG)
            if hasattr(graph, "Save"):
                if os.path.exists(save_path):
                    try:
                        os.remove(save_path)
                    except Exception:
                        pass
                try:
                    graph.Save(save_path, image_type, 1600, 900)
                except Exception:
                    graph.Save(save_path, image_type)
                if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                    return True
        except Exception:
            pass
        method_names = (
            "SaveImage",
            "SaveImageFile",
            "SaveToImage",
            "SaveGraphImage",
            "ExportImage",
            "ExportGraphImage",
            "CopyToFile",
        )
        for method_name in method_names:
            try:
                method = getattr(graph, method_name, None)
                if method is None:
                    continue
                method(save_path)
                if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                    return True
            except Exception:
                continue
        return False

    def _to_py_list(self, seq):
        if seq is None:
            return None
        try:
            n = len(seq)
        except Exception:
            try:
                n = int(getattr(seq, "Length", 0)) or int(getattr(seq, "Count", 0))
            except Exception:
                return None
        if n is None or n <= 0:
            return None
        out = []
        for i in range(n):
            try:
                v = seq[i]
            except Exception:
                try:
                    v = seq.get_Item(i)
                except Exception:
                    return None
            try:
                out.append(float(v))
            except Exception:
                try:
                    out.append(float(str(v)))
                except Exception:
                    return None
        return out

    def _get_xy_data_from_graph(self, graph, channel=0, acquisition_number=1, prefer=None):
        try:
            from AudioPrecision.API import VerticalAxis
            axis_left = VerticalAxis.Left
            axis_right = VerticalAxis.Right
        except Exception:
            axis_left = 0
            axis_right = 1

        ch_index = None
        try:
            from AudioPrecision.API import InputChannelIndex
            members = [m for m in ("Ch1", "Ch2", "Ch3", "Ch4")]
            if 0 <= channel < len(members) and hasattr(InputChannelIndex, members[channel]):
                ch_index = getattr(InputChannelIndex, members[channel])
        except Exception:
            ch_index = None

        freq_attempts = [
            ("GetFrequencyValues/GetMagnitudeValues(ch)",
             lambda: (graph.GetFrequencyValues(channel), graph.GetMagnitudeValues(channel))),
            ("GetFrequencyValues/GetValues(ch)",
             lambda: (graph.GetFrequencyValues(channel), graph.GetValues(channel))),
        ]
        acq0 = max(0, int(acquisition_number) - 1)
        all_attempts = []
        if ch_index is not None:
            all_attempts += [
                ("GetAllXValues/GetAllYValues(ChIdx,acq0,Left)",
                 lambda: (graph.GetAllXValues(ch_index, acq0, axis_left),
                          graph.GetAllYValues(ch_index, acq0, axis_left))),
                ("GetAllXValues/GetAllYValues(ChIdx,acq,Left)",
                 lambda: (graph.GetAllXValues(ch_index, acquisition_number, axis_left),
                          graph.GetAllYValues(ch_index, acquisition_number, axis_left))),
            ]
        all_attempts += [
            ("GetAllXValues/GetAllYValues(ch,acq0,Left)",
             lambda: (graph.GetAllXValues(channel, acq0, axis_left),
                      graph.GetAllYValues(channel, acq0, axis_left))),
            ("GetAllXValues/GetAllYValues(ch,acq,Left)",
             lambda: (graph.GetAllXValues(channel, acquisition_number, axis_left),
                      graph.GetAllYValues(channel, acquisition_number, axis_left))),
            ("GetAllXValues/GetAllYValues(ch,Left)",
             lambda: (graph.GetAllXValues(channel, axis_left),
                      graph.GetAllYValues(channel, axis_left))),
            ("GetAllXValues/GetAllYValues(ch)",
             lambda: (graph.GetAllXValues(channel), graph.GetAllYValues(channel))),
        ]
        generic_attempts = []
        if ch_index is not None:
            generic_attempts += [
                ("GetXValues/GetYValues(ChIdx,acq0,Left)",
                 lambda: (graph.GetXValues(ch_index, acq0, axis_left),
                          graph.GetYValues(ch_index, acq0, axis_left))),
                ("GetXValues/GetYValues(ChIdx,acq,Left)",
                 lambda: (graph.GetXValues(ch_index, acquisition_number, axis_left),
                          graph.GetYValues(ch_index, acquisition_number, axis_left))),
            ]
        generic_attempts += [
            ("GetXValues/GetYValues(ch,acq0,Left)",
             lambda: (graph.GetXValues(channel, acq0, axis_left),
                      graph.GetYValues(channel, acq0, axis_left))),
            ("GetXValues/GetYValues(ch,acq0,Right)",
             lambda: (graph.GetXValues(channel, acq0, axis_right),
                      graph.GetYValues(channel, acq0, axis_right))),
            ("GetXValues/GetYValues(ch,acq,Left)",
             lambda: (graph.GetXValues(channel, acquisition_number, axis_left),
                      graph.GetYValues(channel, acquisition_number, axis_left))),
            ("GetXValues/GetYValues(ch,acq,Right)",
             lambda: (graph.GetXValues(channel, acquisition_number, axis_right),
                      graph.GetYValues(channel, acquisition_number, axis_right))),
            ("GetXValues/GetYValues(ch,acq)",
             lambda: (graph.GetXValues(channel, acquisition_number),
                      graph.GetYValues(channel, acquisition_number))),
            ("GetXValues/GetYValues(ch)",
             lambda: (graph.GetXValues(channel), graph.GetYValues(channel))),
            ("GetXValues/GetYValues()",
             lambda: (graph.GetXValues(), graph.GetYValues())),
            ("GetMeasuredValues/GetValues(ch,Left)",
             lambda: (graph.GetMeasuredValues(channel, axis_left),
                      graph.GetValues(channel, axis_left))),
            ("GetMeasuredValues/GetValues(ch)",
             lambda: (graph.GetMeasuredValues(channel), graph.GetValues(channel))),
            ("XValues/YValues prop",
             lambda: (getattr(graph, "XValues"), getattr(graph, "YValues"))),
        ]
        if prefer == "frequency":
            attempts_xy = freq_attempts + generic_attempts + all_attempts
        elif prefer == "all":
            attempts_xy = all_attempts + generic_attempts + freq_attempts
        else:
            attempts_xy = generic_attempts + freq_attempts

        errors = []
        for desc, attempt in attempts_xy:
            try:
                x_vals, y_vals = attempt()
                x_list = self._to_py_list(x_vals)
                y_list = self._to_py_list(y_vals)
                if x_list and y_list and len(x_list) > 1 and len(y_list) > 1:
                    return x_list, y_list
                errors.append(f"{desc}: empty/short result")
            except Exception as e:
                errors.append(f"{desc}: {e.__class__.__name__}: {e}")
        try:
            sigs = []
            for mname in ("GetXValues", "GetFrequencyValues", "GetMeasuredValues"):
                m = getattr(graph, mname, None)
                if m is None:
                    continue
                ov = getattr(m, "__overloads__", None)
                if ov is not None:
                    try:
                        sigs.append(f"{mname}: {str(ov)}")
                    except Exception:
                        sigs.append(f"{mname}: <overloads>")
                else:
                    sigs.append(f"{mname}: <no overloads info>")
            members = [a for a in dir(graph) if not a.startswith("_") and (
                "value" in a.lower() or "frequenc" in a.lower() or a.lower().startswith("get") or a.lower().startswith("as"))]
            self._diag(f"[APController] 图签名诊断 {self._describe_graph(graph)} 方法成员={members} 签名={sigs}")
        except Exception:
            pass
        diag = "; ".join(errors)
        raise RuntimeError(f"无法读取图表XY数据 ({diag})")

    def _describe_graph(self, graph):
        try:
            title = str(getattr(graph, "Title", "")) or ""
        except Exception:
            title = ""
        try:
            name = str(getattr(graph, "Name", "")) or ""
        except Exception:
            name = ""
        try:
            cls = type(graph).__name__
        except Exception:
            cls = ""
        return f"<{cls} title='{title}' name='{name}'>"

    def _summarize_xy_data(self, x_list, y_list):
        try:
            n = min(len(x_list), len(y_list))
        except Exception:
            n = 0
        if n <= 0:
            return {"n": 0, "x_min": None, "x_max": None, "y_min": None, "y_max": None, "x_span": None}
        try:
            xs = [float(v) for v in x_list[:n]]
            ys = [float(v) for v in y_list[:n]]
            x_min = min(xs)
            x_max = max(xs)
            y_min = min(ys)
            y_max = max(ys)
            return {
                "n": n,
                "x_min": x_min,
                "x_max": x_max,
                "y_min": y_min,
                "y_max": y_max,
                "x_span": x_max - x_min,
            }
        except Exception:
            return {"n": n, "x_min": None, "x_max": None, "y_min": None, "y_max": None, "x_span": None}

    def _score_graph_data(self, kind, x_list, y_list):
        info = self._summarize_xy_data(x_list, y_list)
        score = 0
        n = info["n"] or 0
        x_min = info["x_min"]
        x_max = info["x_max"]
        x_span = info["x_span"]
        y_min = info["y_min"]
        y_max = info["y_max"]

        if n >= 1000:
            score += 2
        elif n >= 100:
            score += 1

        if kind == "fft":
            if x_min is not None and x_max is not None:
                if x_min >= 0 and x_max > 1000:
                    score += 6
                elif x_min >= 0 and x_max > 20:
                    score += 3
                elif x_min >= 0 and x_max <= 1.5:
                    score -= 8
            if y_min is not None and y_max is not None:
                if -300 <= y_min <= 100 and -300 <= y_max <= 100:
                    score += 3
                elif 0 <= y_min <= 1 and 0 <= y_max <= 1:
                    score -= 3
        elif kind == "time":
            if x_min is not None and x_max is not None and x_span is not None:
                if x_min >= 0 and x_span >= 0.05:
                    score += 5
                elif x_min >= 0 and x_span >= 0.005:
                    score += 2
                elif x_min >= 0 and x_max <= 1.5:
                    score += 1
            if n >= 10000:
                score += 4
            elif n >= 2000:
                score += 2

        return score, info

    def get_signal_analyzer_fft_data(self, signal_path_name, measurement_name="Signal Analyzer", channel=0, acquisition_number=1):
        resolved = self.resolve_measurement_name(signal_path_name, measurement_name, auto_add=True)
        if resolved is None:
            raise RuntimeError(f"无法找到或添加测量: {measurement_name}")
        self.apx.ShowMeasurement(signal_path_name, resolved)
        self.configure_fft_settings(signal_path_name, resolved)
        obj = self._get_active_measurement_object()
        if obj is not None and hasattr(obj, "SequenceMeasurement"):
            sm = obj.SequenceMeasurement
            sm.Checked = True
            sm.Run()
            self._wait_for_sequence_done(timeout=30)
        else:
            self.apx.Sequence.StartFromMeasurement(signal_path_name, resolved)
            self._wait_for_sequence_done(timeout=30)
        self.apx.ShowMeasurement(signal_path_name, resolved)
        obj = self._get_active_measurement_object()
        self.set_spectrum_unit_dbv(obj, log_success=False, log_failure=False)
        graph_candidates = []
        seen_ids = set()

        def add_graph(g):
            if g is None:
                return
            try:
                gid = id(g)
            except Exception:
                gid = None
            if gid is not None and gid in seen_ids:
                return
            if gid is not None:
                seen_ids.add(gid)
            graph_candidates.append(g)

        if obj is not None:
            for attr_name in ("FFTSpectrum", "FftSpectrum", "Spectrum",
                              "FrequencyResponse", "Graph"):
                try:
                    attr = getattr(obj, attr_name, None)
                    if attr is not None:
                        add_graph(attr)
                except Exception:
                    pass
            try:
                if hasattr(obj, "Graphs"):
                    graphs = obj.Graphs
                    cnt = 0
                    try:
                        cnt = int(graphs.Count)
                    except Exception:
                        cnt = 0
                    for gi in range(cnt):
                        try:
                            add_graph(graphs.get_Item(gi))
                        except Exception:
                            try:
                                add_graph(graphs[gi])
                            except Exception:
                                continue
            except Exception:
                pass
            try:
                for attr_name in sorted(dir(obj)):
                    if attr_name.startswith("_"):
                        continue
                    try:
                        attr = getattr(obj, attr_name)
                    except Exception:
                        continue
                    if attr is None:
                        continue
                    if hasattr(attr, "GetXValues") or hasattr(attr, "GetFrequencyValues") \
                            or hasattr(attr, "GetMeasuredValues"):
                        add_graph(attr)
            except Exception:
                pass

        try:
            descs = ", ".join(self._describe_graph(g) for g in graph_candidates[:8])
            self._diag(f"[APController] Signal Analyzer 候选图 {len(graph_candidates)} 个: {descs}")
        except Exception:
            pass

        all_errors = []
        best_data = None
        best_score = -10**9
        best_desc = ""
        best_info = None
        unit_logged = False
        for graph in graph_candidates:
            try:
                gname = ""
                try:
                    gname = str(getattr(graph, "Name", "")).lower()
                except Exception:
                    gname = ""
                if any(k in gname for k in ("scope", "waveform", "time")):
                    self._diag(f"[APController] FFT候选跳过时域图 {self._describe_graph(graph)}")
                    continue
                if "density" in gname:
                    continue
                if not (hasattr(graph, "GetXValues") or hasattr(graph, "GetFrequencyValues") or hasattr(graph, "GetAllXValues")):
                    continue
                applied = self.set_spectrum_unit_dbv(graph, log_success=False, log_failure=False)
                if applied and not unit_logged:
                    self._diag(f"[APController] AP频谱单位设置为 dBV: {applied[:8]}")
                    unit_logged = True
                x_vals, y_vals = self._get_xy_data_from_graph(graph, channel, acquisition_number, prefer="frequency")
                score, info = self._score_graph_data("fft", x_vals, y_vals)
                score += self._score_spectrum_graph_candidate(graph)
                self._diag(f"[APController] FFT候选 {self._describe_graph(graph)} -> score={score}, n={info['n']}, x={info['x_min']}~{info['x_max']}, y={info['y_min']}~{info['y_max']}")
                if score > best_score:
                    best_score = score
                    best_data = (x_vals, y_vals)
                    best_desc = self._describe_graph(graph)
                    best_info = info
            except Exception as e:
                msg = f"{self._describe_graph(graph)}: {e}"
                all_errors.append(msg)
                self._diag(f"[APController] FFT候选读取失败 {msg}")

        if best_data is not None:
            if not unit_logged:
                self._diag("[APController] AP频谱单位 dBV 未找到图表轴可写属性，保留AP当前显示单位")
            self._diag(f"[APController] FFT最终选择 {best_desc} -> score={best_score}, n={best_info['n']}, x={best_info['x_min']}~{best_info['x_max']}")
            if best_info and best_info.get('x_max') is not None and best_info.get('x_max') <= 1.5:
                raise RuntimeError(f"读取到的FFT横轴范围异常: {best_info['x_min']}~{best_info['x_max']}，疑似不是频率轴")
            return best_data

        diag = "; ".join(all_errors[-3:]) if all_errors else "无候选图"
        raise RuntimeError(f"无法读取FFT频谱数据 ({diag})")

    def get_signal_acquisition_data(self, signal_path_name, measurement_name="Signal Acquisition", channel=0, acquisition_number=1, acquisition_time=None):
        resolved = self.resolve_measurement_name(signal_path_name, measurement_name, auto_add=True)
        if resolved is None:
            raise RuntimeError(f"无法找到或添加测量: {measurement_name}")
        if acquisition_time is not None:
            try:
                self.configure_signal_acquisition_settings(signal_path_name, resolved, acquisition_time)
            except Exception:
                pass
        self.apx.ShowMeasurement(signal_path_name, resolved)
        obj = self._get_active_measurement_object()
        if obj is not None and hasattr(obj, "SequenceMeasurement"):
            sm = obj.SequenceMeasurement
            sm.Checked = True
            sm.Run()
            self._wait_for_sequence_done(timeout=30)
        else:
            self.apx.Sequence.StartFromMeasurement(signal_path_name, resolved)
            self._wait_for_sequence_done(timeout=30)
        self.apx.ShowMeasurement(signal_path_name, resolved)
        obj = self._get_active_measurement_object()
        graph_candidates = []
        seen_ids = set()

        def add_graph(g):
            if g is None:
                return
            try:
                gid = id(g)
            except Exception:
                gid = None
            if gid is not None and gid in seen_ids:
                return
            if gid is not None:
                seen_ids.add(gid)
            graph_candidates.append(g)

        def add_graph_deep(g):
            """IGraph 本身无数据方法, 数据在 Result 子对象里: 尝试 AsWaveformDataGraph 等转换。"""
            add_graph(g)
            if g is None:
                return
            if hasattr(g, "GetXValues") or hasattr(g, "GetAllXValues") or hasattr(g, "GetMeasuredValues"):
                return
            try:
                result = getattr(g, "Result", None)
            except Exception:
                result = None
            if result is None:
                return
            for conv_name in ("AsWaveformDataGraph", "AsXYGraph", "AsCustomXYGraph"):
                try:
                    conv = getattr(result, conv_name, None)
                    if conv is None:
                        continue
                    sub = conv()
                    if sub is not None and (hasattr(sub, "GetXValues") or hasattr(sub, "GetAllXValues")):
                        add_graph(sub)
                        self._diag(f"[APController] 图已转换 {conv_name}: {self._describe_graph(g)} -> {self._describe_graph(sub)}")
                        break
                except Exception:
                    continue

        if obj is not None:
            for attr_name in ("AcquiredWaveform", "Waveform", "Scope", "Graph"):
                try:
                    attr = getattr(obj, attr_name, None)
                    if attr is not None:
                        add_graph_deep(attr)
                except Exception:
                    pass
            try:
                if hasattr(obj, "Graphs"):
                    graphs = obj.Graphs
                    cnt = 0
                    try:
                        cnt = int(graphs.Count)
                    except Exception:
                        cnt = 0
                    for gi in range(cnt):
                        try:
                            add_graph_deep(graphs.get_Item(gi))
                        except Exception:
                            try:
                                add_graph_deep(graphs[gi])
                            except Exception:
                                continue
            except Exception:
                pass
            try:
                for attr_name in sorted(dir(obj)):
                    if attr_name.startswith("_"):
                        continue
                    try:
                        attr = getattr(obj, attr_name)
                    except Exception:
                        continue
                    if attr is None:
                        continue
                    if hasattr(attr, "GetXValues") or hasattr(attr, "GetMeasuredValues"):
                        add_graph(attr)
            except Exception:
                pass

        try:
            descs = ", ".join(self._describe_graph(g) for g in graph_candidates[:8])
            self._diag(f"[APController] Signal Acquisition 候选图 {len(graph_candidates)} 个: {descs}")
        except Exception:
            pass

        all_errors = []
        best_y = None
        best_score = -10**9
        best_desc = ""
        best_info = None
        sig_diag_done = False
        for graph in graph_candidates:
            try:
                if not (hasattr(graph, "GetXValues") or hasattr(graph, "GetAllXValues")):
                    continue
                if not sig_diag_done:
                    sig_diag_done = True
                    try:
                        sigs = []
                        for mname in ("GetAllYValues", "GetAllXValues", "GetYValues", "GetXValues"):
                            m = getattr(graph, mname, None)
                            if m is None:
                                continue
                            ov = getattr(m, "__overloads__", None)
                            sigs.append(f"{mname}: {str(ov) if ov is not None else '<no overloads>'}")
                        self._diag(f"[APController] 时域图签名 {self._describe_graph(graph)} 签名={sigs}")
                    except Exception:
                        pass
                x_vals, y_vals = self._get_xy_data_from_graph(graph, channel, acquisition_number, prefer="all")
                score, info = self._score_graph_data("time", x_vals, y_vals)
                self._diag(f"[APController] 时域候选 {self._describe_graph(graph)} -> score={score}, n={info['n']}, x={info['x_min']}~{info['x_max']}, y={info['y_min']}~{info['y_max']}")
                if score > best_score:
                    best_score = score
                    best_y = y_vals
                    best_desc = self._describe_graph(graph)
                    best_info = info
            except Exception as e:
                all_errors.append(f"{self._describe_graph(graph)}: {e}")
        if best_y is not None:
            self._diag(f"[APController] 时域最终选择 {best_desc} -> score={best_score}, n={best_info['n']}, x={best_info['x_min']}~{best_info['x_max']}")
            return best_y
        diag = "; ".join(all_errors[-3:]) if all_errors else "无候选图"
        raise RuntimeError(f"无法读取时域波形数据 ({diag})")

    def _export_spectrum_manual(self, signal_path_name, measurement_name, save_path):
        import csv
        obj = self._get_active_measurement_object()
        if obj is None:
            raise RuntimeError(f"无法获取 {measurement_name} 的测量对象")
        data_found = False
        rows = []
        for attr_name in sorted(dir(obj)):
            if attr_name.startswith("_"):
                continue
            try:
                attr = getattr(obj, attr_name)
                if hasattr(attr, "GetXValues") and hasattr(attr, "GetYValues"):
                    x_vals = attr.GetXValues()
                    y_vals = attr.GetYValues()
                    ch_count = getattr(attr, "ChannelCount", 1)
                    name = str(attr.Name) if hasattr(attr, "Name") else attr_name
                    x_list = [float(x_vals[i]) for i in range(len(x_vals))]
                    for ch in range(ch_count):
                        y_ch = y_vals[ch] if ch_count > 1 else y_vals
                        y_list = [float(y_ch[i]) for i in range(len(y_ch))]
                        if not rows:
                            rows = [["Frequency(Hz)"] + [f"CH{ch+1}_{name}"]]
                            rows.extend([[x] for x in x_list])
                        for ri, y in enumerate(y_list):
                            if ri + 1 < len(rows):
                                rows[ri + 1].append(y)
                    data_found = True
                    break
            except Exception:
                continue
        if not data_found:
            try:
                seq = self.apx.Sequence
                for i in range(seq.Count):
                    sp = seq.GetSignalPath(i)
                    if sp.Name != signal_path_name:
                        continue
                    for j in range(sp.Count):
                        m = sp.GetMeasurement(j)
                        if m.Name != measurement_name:
                            continue
                        if m.HasSequenceResults:
                            sr = m.SequenceResults
                            for k in range(sr.Count):
                                r = sr.get_Item(k)
                                if hasattr(r, "GetXValues") and hasattr(r, "GetYValues"):
                                    x_vals = r.GetXValues()
                                    y_vals = r.GetYValues()
                                    rn = str(r.Name)
                                    x_list = [float(x_vals[xi]) for xi in range(len(x_vals))]
                                    ch = getattr(r, "ChannelCount", 1)
                                    rows = [["Frequency(Hz)"] + [f"CH{c+1}_{rn}" for c in range(ch)]]
                                    for xi, x in enumerate(x_list):
                                        row = [x]
                                        for c in range(ch):
                                            yc = y_vals[c] if ch > 1 else y_vals
                                            row.append(float(yc[xi]))
                                        rows.append(row)
                                    data_found = True
                                    break
                        break
                    break
            except Exception:
                pass
        if not data_found:
            raise RuntimeError(f"无法获取频谱数据: {measurement_name}")
        with open(save_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)


if __name__ == "__main__":
    print("HAS_AP_API =", HAS_AP_API)
    print("AP_API_PATH =", AP_API_PATH)
    if not HAS_AP_API:
        print("AudioPrecision.API 未加载:", _AP_LOAD_ERROR)
        print("请确认 APx500 已安装, 或用 load_ap_api('你的 API 路径') 指定安装位置")
        raise SystemExit(1)
    ap = APxConnection()
    try:
        ap.connect()
        print("连接成功")
        names = ap.get_signal_path_names()
        print("Signal Paths:", names)
        if names:
            sp = names[0]
            print("[%s] Measurements: %s" % (sp, ap.get_measurement_names(sp)))
    finally:
        ap.disconnect()
        print("已断开")

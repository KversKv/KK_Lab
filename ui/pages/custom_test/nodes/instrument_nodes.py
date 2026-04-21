"""仪器控制节点集合"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from log_config import get_logger
from ui.pages.custom_test.nodes.base_node import BaseNode, register_node

logger = get_logger(__name__)


@register_node
class ChamberSetTemp(BaseNode):
    """温箱设置目标温度"""

    node_type = "ChamberSetTemp"
    display_name = "Chamber Set Temp"
    category = "instrument"
    icon = "🌡"
    color = "#e07b39"

    PARAM_SCHEMA = [
        {"key": "temperature", "label": "目标温度 (°C)", "type": "float", "default": 25.0},
        {"key": "wait_stable", "label": "等待稳定", "type": "bool", "default": True},
        {"key": "stable_time", "label": "稳定等待时间 (s)", "type": "float", "default": 60.0},
        {"key": "tolerance", "label": "温度容差 (°C)", "type": "float", "default": 1.0},
    ]

    def execute(self, context: Any) -> None:
        chamber = context.instruments.get("chamber")
        if chamber is None:
            raise RuntimeError("温箱未连接")

        temp = context.resolve_value(self.params["temperature"])
        wait_stable = context.resolve_value(self.params["wait_stable"])
        stable_time = context.resolve_value(self.params["stable_time"])
        tolerance = context.resolve_value(self.params["tolerance"])

        temp = float(temp)
        stable_time = float(stable_time)
        tolerance = float(tolerance)

        logger.info("设置温箱温度: %.1f°C", temp)
        chamber.set_temperature(temp)

        if wait_stable:
            logger.info("等待温度稳定 (容差=%.1f°C, 最大等待=%ds)", tolerance, int(stable_time))
            deadline = time.time() + stable_time
            while time.time() < deadline:
                if context.should_stop:
                    return
                current_temp = chamber.get_current_temp()
                if current_temp is not None and abs(current_temp - temp) <= tolerance:
                    logger.info("温度已稳定: %.1f°C", current_temp)
                    return
                time.sleep(2.0)
            logger.warning("等待温度稳定超时")


@register_node
class N6705CSetVoltage(BaseNode):
    """N6705C 设置通道电压"""

    node_type = "N6705CSetVoltage"
    display_name = "N6705C Set Voltage"
    category = "instrument"
    icon = "⚡"
    color = "#f2994a"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道号", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
        {"key": "voltage", "label": "电压 (V)", "type": "float", "default": 3.8},
        {"key": "current_limit", "label": "限流 (A)", "type": "float", "default": 1.0},
        {"key": "output_on", "label": "开启输出", "type": "bool", "default": True},
    ]

    def execute(self, context: Any) -> None:
        n6705c = context.instruments.get("n6705c")
        if n6705c is None:
            raise RuntimeError("N6705C 未连接")

        ch = int(context.resolve_value(self.params["channel"]))
        voltage = float(context.resolve_value(self.params["voltage"]))
        current_limit = float(context.resolve_value(self.params["current_limit"]))
        output_on = context.resolve_value(self.params["output_on"])

        logger.info("N6705C CH%d: 设置电压=%.3fV, 限流=%.3fA", ch, voltage, current_limit)
        n6705c.set_voltage(ch, voltage)
        n6705c.set_current_limit(ch, current_limit)
        if output_on:
            n6705c.channel_on(ch)


@register_node
class N6705CMeasure(BaseNode):
    """N6705C 测量电压/电流/功率"""

    node_type = "N6705CMeasure"
    display_name = "N6705C Measure"
    category = "instrument"
    icon = "📊"
    color = "#f2994a"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道号", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
        {"key": "measure_type", "label": "测量类型", "type": "str", "default": "current",
         "options": ["voltage", "current", "power"]},
        {"key": "result_var", "label": "结果存入变量", "type": "str", "default": "N6705C_result"},
    ]

    def execute(self, context: Any) -> None:
        n6705c = context.instruments.get("n6705c")
        if n6705c is None:
            raise RuntimeError("N6705C 未连接")

        ch = int(context.resolve_value(self.params["channel"]))
        measure_type = str(context.resolve_value(self.params["measure_type"]))
        result_var = str(context.resolve_value(self.params["result_var"]))

        if measure_type == "voltage":
            value = float(n6705c.measure_voltage(ch))
        elif measure_type == "current":
            value = float(n6705c.measure_current(ch))
        elif measure_type == "power":
            v = float(n6705c.measure_voltage(ch))
            i = float(n6705c.measure_current(ch))
            value = v * i
        else:
            raise ValueError(f"未知测量类型: {measure_type}")

        logger.info("N6705C CH%d %s = %s", ch, measure_type, value)
        context.set_variable(result_var, value)
        auto_key = f"N6705C_CH{ch}_{measure_type}"
        context.set_variable(auto_key, value)


@register_node
class ScopeMeasureFreq(BaseNode):
    """示波器测量频率"""

    node_type = "ScopeMeasureFreq"
    display_name = "Scope Measure Freq"
    category = "instrument"
    icon = "📈"
    color = "#27ae60"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
        {"key": "result_var", "label": "结果存入变量", "type": "str", "default": "scope_freq"},
    ]

    def execute(self, context: Any) -> None:
        scope = context.instruments.get("scope")
        if scope is None:
            raise RuntimeError("示波器未连接")

        ch = int(context.resolve_value(self.params["channel"]))
        result_var = str(context.resolve_value(self.params["result_var"]))

        if hasattr(scope, "get_dvm_frequency"):
            freq = scope.get_dvm_frequency()
        elif hasattr(scope, "get_channel_frequency"):
            freq = scope.get_channel_frequency(ch)
        else:
            raise RuntimeError("示波器不支持频率测量")

        logger.info("Scope CH%d freq = %.4f Hz", ch, freq)
        context.set_variable(result_var, freq)
        context.set_variable(f"scope_CH{ch}_freq", freq)


@register_node
class ScopeMeasure(BaseNode):
    """示波器通用测量"""

    node_type = "ScopeMeasure"
    display_name = "Scope Measure"
    category = "instrument"
    icon = "📈"
    color = "#27ae60"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
        {"key": "measure_type", "label": "测量类型", "type": "str", "default": "pk2pk",
         "options": ["pk2pk", "rms", "mean", "max", "min", "frequency"]},
        {"key": "result_var", "label": "结果存入变量", "type": "str", "default": "scope_result"},
    ]

    def execute(self, context: Any) -> None:
        scope = context.instruments.get("scope")
        if scope is None:
            raise RuntimeError("示波器未连接")

        ch = int(context.resolve_value(self.params["channel"]))
        mtype = str(context.resolve_value(self.params["measure_type"]))
        result_var = str(context.resolve_value(self.params["result_var"]))

        method_map = {
            "pk2pk": "get_channel_pk2pk",
            "rms": "get_channel_rms",
            "mean": "get_channel_mean",
            "max": "get_channel_max",
            "min": "get_channel_min",
            "frequency": "get_channel_frequency",
        }
        method_name = method_map.get(mtype)
        if method_name is None or not hasattr(scope, method_name):
            raise RuntimeError(f"示波器不支持 {mtype} 测量")

        value = getattr(scope, method_name)(ch)
        logger.info("Scope CH%d %s = %s", ch, mtype, value)
        context.set_variable(result_var, value)
        context.set_variable(f"scope_CH{ch}_{mtype}", value)


@register_node
class RFAnalyzerMeasure(BaseNode):
    """综测仪测量（预留接口）"""

    node_type = "RFAnalyzerMeasure"
    display_name = "RF Analyzer Measure"
    category = "instrument"
    icon = "📡"
    color = "#8e44ad"

    PARAM_SCHEMA = [
        {"key": "measure_type", "label": "测量类型", "type": "str", "default": "tx_power",
         "options": ["tx_power", "rx_sensitivity", "evm", "aclr"]},
        {"key": "frequency_mhz", "label": "频率 (MHz)", "type": "float", "default": 2402.0},
        {"key": "result_var", "label": "结果存入变量", "type": "str", "default": "rf_result"},
    ]

    def execute(self, context: Any) -> None:
        rf = context.instruments.get("rf_analyzer")
        if rf is None:
            raise RuntimeError("综测仪未连接（该仪器接口尚未实现，请后续接入 CMW270/CMW500 驱动）")

        mtype = str(context.resolve_value(self.params["measure_type"]))
        freq = float(context.resolve_value(self.params["frequency_mhz"]))
        result_var = str(context.resolve_value(self.params["result_var"]))

        if hasattr(rf, "measure"):
            value = rf.measure(mtype, freq)
        else:
            raise RuntimeError("综测仪驱动未实现 measure() 方法")

        context.set_variable(result_var, value)

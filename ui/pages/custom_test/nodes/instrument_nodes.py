"""仪器控制节点集合"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from log_config import get_logger
from ui.pages.custom_test.nodes.base_node import BaseNode, register_node

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
#  N6705C  —  Config / Set / Get
# ═══════════════════════════════════════════════════════════════

@register_node
class N6705CSetMode(BaseNode):
    node_type = "N6705CSetMode"
    display_name = "N6705C Set Mode"
    category = "instrument"
    icon = "⚙"
    color = "#f2994a"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道号", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
        {"key": "mode", "label": "模式", "type": "str", "default": "PS2Q",
         "options": ["PS2Q", "VMETer", "CC"]},
    ]

    def execute(self, context: Any) -> None:
        n6705c = context.instruments.get("n6705c")
        if n6705c is None:
            raise RuntimeError("N6705C 未连接")
        ch = int(context.resolve_value(self.params["channel"]))
        mode = str(context.resolve_value(self.params["mode"]))
        n6705c.set_mode(ch, mode)
        context.log_output(f"N6705C CH{ch}: mode={mode}")


@register_node
class N6705CSetRange(BaseNode):
    node_type = "N6705CSetRange"
    display_name = "N6705C Set Range"
    category = "instrument"
    icon = "⚙"
    color = "#f2994a"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道号", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
        {"key": "range_auto", "label": "自动量程", "type": "bool", "default": True},
    ]

    def execute(self, context: Any) -> None:
        n6705c = context.instruments.get("n6705c")
        if n6705c is None:
            raise RuntimeError("N6705C 未连接")
        ch = int(context.resolve_value(self.params["channel"]))
        auto = context.resolve_value(self.params["range_auto"])
        if auto:
            n6705c.set_channel_range(ch)
        else:
            n6705c.set_channel_range_off(ch)
        context.log_output(f"N6705C CH{ch}: range_auto={'ON' if auto else 'OFF'}")


@register_node
class N6705CChannelOn(BaseNode):
    node_type = "N6705CChannelOn"
    display_name = "N6705C Channel ON"
    category = "instrument"
    icon = "⏚"
    color = "#f2994a"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道号", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
    ]

    def execute(self, context: Any) -> None:
        n6705c = context.instruments.get("n6705c")
        if n6705c is None:
            raise RuntimeError("N6705C 未连接")
        ch = int(context.resolve_value(self.params["channel"]))
        n6705c.channel_on(ch)
        context.log_output(f"N6705C CH{ch}: ON")


@register_node
class N6705CChannelOff(BaseNode):
    node_type = "N6705CChannelOff"
    display_name = "N6705C Channel OFF"
    category = "instrument"
    icon = "⏚"
    color = "#f2994a"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道号", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
    ]

    def execute(self, context: Any) -> None:
        n6705c = context.instruments.get("n6705c")
        if n6705c is None:
            raise RuntimeError("N6705C 未连接")
        ch = int(context.resolve_value(self.params["channel"]))
        n6705c.channel_off(ch)
        context.log_output(f"N6705C CH{ch}: OFF")


@register_node
class N6705CSetVoltage(BaseNode):
    node_type = "N6705CSetVoltage"
    display_name = "N6705C Set Voltage"
    category = "instrument"
    icon = "⏚"
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
        context.log_output(f"N6705C CH{ch}: set_voltage={voltage:.4f}V, current_limit={current_limit:.3f}A")
        n6705c.set_voltage(ch, voltage)
        n6705c.set_current_limit(ch, current_limit)
        if output_on:
            n6705c.channel_on(ch)


@register_node
class N6705CSetCurrent(BaseNode):
    node_type = "N6705CSetCurrent"
    display_name = "N6705C Set Current"
    category = "instrument"
    icon = "⏚"
    color = "#f2994a"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道号", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
        {"key": "current", "label": "电流 (A)", "type": "float", "default": 0.1},
        {"key": "voltage_limit", "label": "限压 (V)", "type": "float", "default": 5.0},
    ]

    def execute(self, context: Any) -> None:
        n6705c = context.instruments.get("n6705c")
        if n6705c is None:
            raise RuntimeError("N6705C 未连接")
        ch = int(context.resolve_value(self.params["channel"]))
        current = float(context.resolve_value(self.params["current"]))
        vlimit = float(context.resolve_value(self.params["voltage_limit"]))
        n6705c.set_current(ch, current)
        n6705c.set_voltage_limit(ch, vlimit)
        context.log_output(f"N6705C CH{ch}: set_current={current:.4f}A, voltage_limit={vlimit:.3f}V")


@register_node
class N6705CSetCurrentLimit(BaseNode):
    node_type = "N6705CSetCurrentLimit"
    display_name = "N6705C Set Current Limit"
    category = "instrument"
    icon = "⏚"
    color = "#f2994a"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道号", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
        {"key": "current_limit", "label": "限流 (A)", "type": "float", "default": 1.0},
    ]

    def execute(self, context: Any) -> None:
        n6705c = context.instruments.get("n6705c")
        if n6705c is None:
            raise RuntimeError("N6705C 未连接")
        ch = int(context.resolve_value(self.params["channel"]))
        limit_val = float(context.resolve_value(self.params["current_limit"]))
        n6705c.set_current_limit(ch, limit_val)
        context.log_output(f"N6705C CH{ch}: current_limit={limit_val:.4f}A")


@register_node
class N6705CMeasure(BaseNode):
    node_type = "N6705CMeasure"
    display_name = "N6705C Measure"
    category = "instrument"
    icon = "⊞"
    color = "#f2994a"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道号", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
        {"key": "measure_type", "label": "测量类型", "type": "str", "default": "current",
         "options": ["voltage", "current", "power"]},
        {"key": "result_var", "label": "结果存入变量", "type": "str", "default": "N6705C_result"},
        {"key": "export_var", "label": "导出变量到记录", "type": "bool", "default": True},
    ]

    def execute(self, context: Any) -> None:
        n6705c = context.instruments.get("n6705c")
        if n6705c is None:
            raise RuntimeError("N6705C 未连接")
        ch = int(context.resolve_value(self.params["channel"]))
        measure_type = str(context.resolve_value(self.params["measure_type"]))
        result_var = str(self.params["result_var"])
        export_var = bool(self.params.get("export_var", True))
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
        context.log_output(f"N6705C CH{ch}: {measure_type}={value}")
        context.set_variable(result_var, value, export=export_var)
        auto_key = f"N6705C_CH{ch}_{measure_type}"
        context.set_variable(auto_key, value, export=export_var)


@register_node
class N6705CGetMode(BaseNode):
    node_type = "N6705CGetMode"
    display_name = "N6705C Get Mode"
    category = "instrument"
    icon = "⊞"
    color = "#f2994a"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道号", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
        {"key": "result_var", "label": "结果存入变量", "type": "str", "default": "N6705C_mode"},
        {"key": "export_var", "label": "导出变量到记录", "type": "bool", "default": True},
    ]

    def execute(self, context: Any) -> None:
        n6705c = context.instruments.get("n6705c")
        if n6705c is None:
            raise RuntimeError("N6705C 未连接")
        ch = int(context.resolve_value(self.params["channel"]))
        result_var = str(self.params["result_var"])
        export_var = bool(self.params.get("export_var", True))
        mode = n6705c.get_mode(ch)
        context.log_output(f"N6705C CH{ch}: mode={mode}")
        context.set_variable(result_var, mode, export=export_var)


@register_node
class N6705CGetChannelState(BaseNode):
    node_type = "N6705CGetChannelState"
    display_name = "N6705C Get CH State"
    category = "instrument"
    icon = "⊞"
    color = "#f2994a"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道号", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
        {"key": "result_var", "label": "结果存入变量", "type": "str", "default": "N6705C_ch_state"},
        {"key": "export_var", "label": "导出变量到记录", "type": "bool", "default": True},
    ]

    def execute(self, context: Any) -> None:
        n6705c = context.instruments.get("n6705c")
        if n6705c is None:
            raise RuntimeError("N6705C 未连接")
        ch = int(context.resolve_value(self.params["channel"]))
        result_var = str(self.params["result_var"])
        export_var = bool(self.params.get("export_var", True))
        state = n6705c.get_channel_state(ch)
        context.log_output(f"N6705C CH{ch}: state={'ON' if state else 'OFF'}")
        context.set_variable(result_var, state, export=export_var)


# ═══════════════════════════════════════════════════════════════
#  Scope (MSO64B / DSOX4034A)  —  Config / Set / Get
# ═══════════════════════════════════════════════════════════════

@register_node
class ScopeSetChannel(BaseNode):
    node_type = "ScopeSetChannel"
    display_name = "Scope Set Channel"
    category = "instrument"
    icon = "⚙"
    color = "#27ae60"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
        {"key": "display", "label": "显示", "type": "bool", "default": True},
        {"key": "coupling", "label": "耦合", "type": "str", "default": "DC",
         "options": ["DC", "AC"]},
    ]

    def execute(self, context: Any) -> None:
        scope = context.instruments.get("scope")
        if scope is None:
            raise RuntimeError("示波器未连接")
        ch = int(context.resolve_value(self.params["channel"]))
        display = context.resolve_value(self.params["display"])
        coupling = str(context.resolve_value(self.params["coupling"]))
        scope.set_channel_display(ch, display)
        scope.set_channel_coupling(ch, coupling)
        context.log_output(f"Scope CH{ch}: display={'ON' if display else 'OFF'}, coupling={coupling}")


@register_node
class ScopeSetScale(BaseNode):
    node_type = "ScopeSetScale"
    display_name = "Scope Set Scale"
    category = "instrument"
    icon = "⚙"
    color = "#27ae60"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
        {"key": "volts_per_div", "label": "V/div", "type": "float", "default": 1.0},
        {"key": "offset", "label": "偏移 (V)", "type": "float", "default": 0.0},
    ]

    def execute(self, context: Any) -> None:
        scope = context.instruments.get("scope")
        if scope is None:
            raise RuntimeError("示波器未连接")
        ch = int(context.resolve_value(self.params["channel"]))
        vpd = float(context.resolve_value(self.params["volts_per_div"]))
        offset = float(context.resolve_value(self.params["offset"]))
        scope.set_channel_scale(ch, vpd)
        scope.set_channel_offset(ch, offset)
        context.log_output(f"Scope CH{ch}: scale={vpd}V/div, offset={offset}V")


@register_node
class ScopeSetTimebase(BaseNode):
    node_type = "ScopeSetTimebase"
    display_name = "Scope Set Timebase"
    category = "instrument"
    icon = "⚙"
    color = "#27ae60"

    PARAM_SCHEMA = [
        {"key": "seconds_per_div", "label": "时基 (s/div)", "type": "float", "default": 0.001},
    ]

    def execute(self, context: Any) -> None:
        scope = context.instruments.get("scope")
        if scope is None:
            raise RuntimeError("示波器未连接")
        spd = float(context.resolve_value(self.params["seconds_per_div"]))
        scope.set_timebase_scale(spd)
        context.log_output(f"Scope: timebase={spd}s/div")


@register_node
class ScopeSetTrigger(BaseNode):
    node_type = "ScopeSetTrigger"
    display_name = "Scope Set Trigger"
    category = "instrument"
    icon = "⚙"
    color = "#27ae60"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "触发源通道", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
        {"key": "level", "label": "触发电平 (V)", "type": "float", "default": 1.5},
        {"key": "slope", "label": "触发沿", "type": "str", "default": "POS",
         "options": ["POS", "NEG"]},
    ]

    def execute(self, context: Any) -> None:
        scope = context.instruments.get("scope")
        if scope is None:
            raise RuntimeError("示波器未连接")
        ch = int(context.resolve_value(self.params["channel"]))
        level = float(context.resolve_value(self.params["level"]))
        slope = str(context.resolve_value(self.params["slope"]))
        scope.set_trigger_edge(ch, level, slope)
        context.log_output(f"Scope: trigger CH{ch} level={level}V slope={slope}")


@register_node
class ScopeRunStop(BaseNode):
    node_type = "ScopeRunStop"
    display_name = "Scope Run/Stop"
    category = "instrument"
    icon = "≋"
    color = "#27ae60"

    PARAM_SCHEMA = [
        {"key": "action", "label": "操作", "type": "str", "default": "run",
         "options": ["run", "stop"]},
    ]

    def execute(self, context: Any) -> None:
        scope = context.instruments.get("scope")
        if scope is None:
            raise RuntimeError("示波器未连接")
        action = str(context.resolve_value(self.params["action"]))
        if action == "run":
            scope.run()
        else:
            scope.stop()
        context.log_output(f"Scope: {action}")


@register_node
class ScopeMeasure(BaseNode):
    node_type = "ScopeMeasure"
    display_name = "Scope Measure"
    category = "instrument"
    icon = "∿"
    color = "#27ae60"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
        {"key": "measure_type", "label": "测量类型", "type": "str", "default": "pk2pk",
         "options": ["pk2pk", "rms", "mean", "max", "min", "frequency"]},
        {"key": "result_var", "label": "结果存入变量", "type": "str", "default": "scope_result"},
        {"key": "export_var", "label": "导出变量到记录", "type": "bool", "default": True},
    ]

    def execute(self, context: Any) -> None:
        scope = context.instruments.get("scope")
        if scope is None:
            raise RuntimeError("示波器未连接")
        ch = int(context.resolve_value(self.params["channel"]))
        mtype = str(context.resolve_value(self.params["measure_type"]))
        result_var = str(self.params["result_var"])
        export_var = bool(self.params.get("export_var", True))
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
        context.set_variable(result_var, value, export=export_var)
        context.set_variable(f"scope_CH{ch}_{mtype}", value, export=export_var)


@register_node
class ScopeMeasureFreq(BaseNode):
    node_type = "ScopeMeasureFreq"
    display_name = "Scope Measure Freq"
    category = "instrument"
    icon = "≋"
    color = "#27ae60"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
        {"key": "result_var", "label": "结果存入变量", "type": "str", "default": "scope_freq"},
        {"key": "export_var", "label": "导出变量到记录", "type": "bool", "default": True},
    ]

    def execute(self, context: Any) -> None:
        scope = context.instruments.get("scope")
        if scope is None:
            raise RuntimeError("示波器未连接")
        ch = int(context.resolve_value(self.params["channel"]))
        result_var = str(self.params["result_var"])
        export_var = bool(self.params.get("export_var", True))
        if hasattr(scope, "get_dvm_frequency"):
            freq = scope.get_dvm_frequency()
        elif hasattr(scope, "get_channel_frequency"):
            freq = scope.get_channel_frequency(ch)
        else:
            raise RuntimeError("示波器不支持频率测量")
        logger.info("Scope CH%d freq = %.4f Hz", ch, freq)
        context.set_variable(result_var, freq, export=export_var)
        context.set_variable(f"scope_CH{ch}_freq", freq, export=export_var)


@register_node
class ScopeGetDvmDC(BaseNode):
    node_type = "ScopeGetDvmDC"
    display_name = "Scope Get DVM DC"
    category = "instrument"
    icon = "∿"
    color = "#27ae60"

    PARAM_SCHEMA = [
        {"key": "channel", "label": "通道", "type": "int", "default": 1,
         "options": [1, 2, 3, 4]},
        {"key": "result_var", "label": "结果存入变量", "type": "str", "default": "dvm_dc"},
        {"key": "export_var", "label": "导出变量到记录", "type": "bool", "default": True},
    ]

    def execute(self, context: Any) -> None:
        scope = context.instruments.get("scope")
        if scope is None:
            raise RuntimeError("示波器未连接")
        ch = int(context.resolve_value(self.params["channel"]))
        result_var = str(self.params["result_var"])
        export_var = bool(self.params.get("export_var", True))
        value = scope.get_dvm_dc(ch)
        context.set_variable(result_var, value, export=export_var)


# ═══════════════════════════════════════════════════════════════
#  VT6002 Chamber  —  Config / Set / Get
# ═══════════════════════════════════════════════════════════════

@register_node
class ChamberStartStop(BaseNode):
    node_type = "ChamberStartStop"
    display_name = "Chamber Start/Stop"
    category = "instrument"
    icon = "◊"
    color = "#e07b39"

    PARAM_SCHEMA = [
        {"key": "action", "label": "操作", "type": "str", "default": "start",
         "options": ["start", "stop"]},
    ]

    def execute(self, context: Any) -> None:
        chamber = context.instruments.get("chamber")
        if chamber is None:
            raise RuntimeError("温箱未连接")
        action = str(context.resolve_value(self.params["action"]))
        if action == "start":
            chamber.start()
        else:
            chamber.stop()
        context.log_output(f"Chamber: {action}")


@register_node
class ChamberSetTemp(BaseNode):
    node_type = "ChamberSetTemp"
    display_name = "Chamber Set Temp"
    category = "instrument"
    icon = "◊"
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
        temp = float(context.resolve_value(self.params["temperature"]))
        wait_stable = context.resolve_value(self.params["wait_stable"])
        stable_time = float(context.resolve_value(self.params["stable_time"]))
        tolerance = float(context.resolve_value(self.params["tolerance"]))
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
class ChamberGetTemp(BaseNode):
    node_type = "ChamberGetTemp"
    display_name = "Chamber Get Temp"
    category = "instrument"
    icon = "◊"
    color = "#e07b39"

    PARAM_SCHEMA = [
        {"key": "result_var", "label": "结果存入变量", "type": "str", "default": "chamber_temp"},
        {"key": "export_var", "label": "导出变量到记录", "type": "bool", "default": True},
    ]

    def execute(self, context: Any) -> None:
        chamber = context.instruments.get("chamber")
        if chamber is None:
            raise RuntimeError("温箱未连接")
        result_var = str(self.params["result_var"])
        export_var = bool(self.params.get("export_var", True))
        temp = chamber.get_current_temp()
        context.log_output(f"Chamber: current_temp={temp}°C")
        context.set_variable(result_var, temp, export=export_var)


@register_node
class ChamberGetSetTemp(BaseNode):
    node_type = "ChamberGetSetTemp"
    display_name = "Chamber Get Set Temp"
    category = "instrument"
    icon = "◊"
    color = "#e07b39"

    PARAM_SCHEMA = [
        {"key": "result_var", "label": "结果存入变量", "type": "str", "default": "chamber_set_temp"},
        {"key": "export_var", "label": "导出变量到记录", "type": "bool", "default": True},
    ]

    def execute(self, context: Any) -> None:
        chamber = context.instruments.get("chamber")
        if chamber is None:
            raise RuntimeError("温箱未连接")
        result_var = str(self.params["result_var"])
        export_var = bool(self.params.get("export_var", True))
        temp = chamber.get_set_temp()
        context.log_output(f"Chamber: set_temp={temp}°C")
        context.set_variable(result_var, temp, export=export_var)


@register_node
class ChamberGetHumidity(BaseNode):
    node_type = "ChamberGetHumidity"
    display_name = "Chamber Get Humidity"
    category = "instrument"
    icon = "◊"
    color = "#e07b39"

    PARAM_SCHEMA = [
        {"key": "result_var", "label": "结果存入变量", "type": "str", "default": "chamber_humidity"},
        {"key": "export_var", "label": "导出变量到记录", "type": "bool", "default": True},
    ]

    def execute(self, context: Any) -> None:
        chamber = context.instruments.get("chamber")
        if chamber is None:
            raise RuntimeError("温箱未连接")
        result_var = str(self.params["result_var"])
        export_var = bool(self.params.get("export_var", True))
        humidity = chamber.read_humidity_pv()
        context.log_output(f"Chamber: humidity={humidity}")
        context.set_variable(result_var, humidity, export=export_var)


# ═══════════════════════════════════════════════════════════════
#  CMW270 RF Analyzer  —  Get
# ═══════════════════════════════════════════════════════════════

@register_node
class RFAnalyzerMeasure(BaseNode):
    node_type = "RFAnalyzerMeasure"
    display_name = "RF Analyzer Measure"
    category = "instrument"
    icon = "⌁"
    color = "#8e44ad"

    PARAM_SCHEMA = [
        {"key": "measure_type", "label": "测量类型", "type": "str", "default": "tx_power",
         "options": ["tx_power", "rx_sensitivity", "evm", "aclr"]},
        {"key": "frequency_mhz", "label": "频率 (MHz)", "type": "float", "default": 2402.0},
        {"key": "result_var", "label": "结果存入变量", "type": "str", "default": "rf_result"},
        {"key": "export_var", "label": "导出变量到记录", "type": "bool", "default": True},
    ]

    def execute(self, context: Any) -> None:
        rf = context.instruments.get("rf_analyzer")
        if rf is None:
            raise RuntimeError("综测仪未连接（该仪器接口尚未实现，请后续接入 CMW270/CMW500 驱动）")
        mtype = str(context.resolve_value(self.params["measure_type"]))
        freq = float(context.resolve_value(self.params["frequency_mhz"]))
        result_var = str(self.params["result_var"])
        export_var = bool(self.params.get("export_var", True))
        if hasattr(rf, "measure"):
            value = rf.measure(mtype, freq)
        else:
            raise RuntimeError("综测仪驱动未实现 measure() 方法")
        context.set_variable(result_var, value, export=export_var)


# ═══════════════════════════════════════════════════════════════
#  REG Controller (I2C)  —  Set / Get
# ═══════════════════════════════════════════════════════════════

def _resolve_hex(context: Any, raw: Any) -> int:
    val = context.resolve_value(raw)
    if isinstance(val, int):
        return val
    s = str(val).strip()
    if s.startswith(("0x", "0X")):
        return int(s, 16)
    try:
        return int(s, 16)
    except ValueError:
        return int(s)

@register_node
class I2CRead(BaseNode):
    node_type = "I2CRead"
    display_name = "I2C Read"
    category = "instrument"
    icon = "⇤"
    color = "#fb923c"

    PARAM_SCHEMA = [
        {"key": "device_addr", "label": "Device Addr (hex)", "type": "str", "default": "0x17"},
        {"key": "reg_addr", "label": "Reg Addr (hex)", "type": "str", "default": "0x0000"},
        {"key": "width", "label": "I2C Width", "type": "int", "default": 10,
         "options": [8, 10, 32]},
        {"key": "result_var", "label": "结果存入变量", "type": "str", "default": "i2c_read_val"},
        {"key": "export_var", "label": "导出变量到记录", "type": "bool", "default": True},
        {"key": "auto_record", "label": "自动记录数据", "type": "bool", "default": True},
    ]

    def execute(self, context: Any) -> None:
        i2c = context.instruments.get("i2c")
        if i2c is None:
            raise RuntimeError("I2C 接口未连接")
        dev = _resolve_hex(context, self.params["device_addr"])
        reg = _resolve_hex(context, self.params["reg_addr"])
        width = int(context.resolve_value(self.params["width"]))
        result_var = str(self.params["result_var"])
        export_var = bool(self.params.get("export_var", True))
        val = i2c.read(dev, reg, width)
        logger.info("I2C Read: dev=0x%02X reg=0x%X width=%d => 0x%X", dev, reg, width, val)
        context.set_variable(result_var, val, export=export_var)
        auto_record = self.params.get("auto_record", True)
        if auto_record:
            context.record_data({
                "device_addr": f"0x{dev:02X}",
                "reg_addr": f"0x{reg:X}",
                "width": width,
                result_var: f"0x{val:X}",
            })


@register_node
class I2CWrite(BaseNode):
    node_type = "I2CWrite"
    display_name = "I2C Write"
    category = "instrument"
    icon = "⇥"
    color = "#fb923c"

    PARAM_SCHEMA = [
        {"key": "device_addr", "label": "Device Addr (hex)", "type": "str", "default": "0x17"},
        {"key": "reg_addr", "label": "Reg Addr (hex)", "type": "str", "default": "0x0000"},
        {"key": "write_data", "label": "Write Data (hex)", "type": "str", "default": "0x0000"},
        {"key": "width", "label": "I2C Width", "type": "int", "default": 10,
         "options": [8, 10, 32]},
    ]

    def execute(self, context: Any) -> None:
        i2c = context.instruments.get("i2c")
        if i2c is None:
            raise RuntimeError("I2C 接口未连接")
        dev = _resolve_hex(context, self.params["device_addr"])
        reg = _resolve_hex(context, self.params["reg_addr"])
        data = _resolve_hex(context, self.params["write_data"])
        width = int(context.resolve_value(self.params["width"]))
        i2c.write(dev, reg, data, width)
        logger.info("I2C Write: dev=0x%02X reg=0x%X data=0x%X width=%d => OK", dev, reg, data, width)


@register_node
class I2CTraverse(BaseNode):
    node_type = "I2CTraverse"
    display_name = "I2C Traverse"
    category = "instrument"
    icon = "⋯"
    color = "#fb923c"

    PARAM_SCHEMA = [
        {"key": "device_addr", "label": "Device Addr (hex)", "type": "str", "default": "0x17"},
        {"key": "reg_start", "label": "Start Reg (hex)", "type": "str", "default": "0x0000"},
        {"key": "reg_end", "label": "End Reg (hex)", "type": "str", "default": "0x00FF"},
        {"key": "width", "label": "I2C Width", "type": "int", "default": 10,
         "options": [8, 10, 32]},
        {"key": "iter_var", "label": "当前寄存器变量名", "type": "str", "default": "reg"},
        {"key": "val_var", "label": "当前读取值变量名", "type": "str", "default": "reg_val"},
        {"key": "result_var", "label": "结果存入变量(dict)", "type": "str", "default": "i2c_traverse"},
        {"key": "auto_record", "label": "逐行记录数据", "type": "bool", "default": True},
    ]

    @property
    def accepts_children(self) -> bool:
        return True

    def execute(self, context: Any) -> None:
        from ui.pages.custom_test.context import BreakLoop
        i2c = context.instruments.get("i2c")
        if i2c is None:
            raise RuntimeError("I2C 接口未连接")
        dev = _resolve_hex(context, self.params["device_addr"])
        reg_start = _resolve_hex(context, self.params["reg_start"])
        reg_end = _resolve_hex(context, self.params["reg_end"])
        width = int(context.resolve_value(self.params["width"]))
        iter_var = str(self.params.get("iter_var", "reg"))
        val_var = str(self.params.get("val_var", "reg_val"))
        result_var = str(self.params["result_var"])
        auto_record = self.params.get("auto_record", True)
        results = {}
        total = reg_end - reg_start + 1
        for idx, reg in enumerate(range(reg_start, reg_end + 1)):
            if context.should_stop:
                break
            try:
                val = i2c.read(dev, reg, width)
                results[reg] = val
                context.set_variable(iter_var, reg, export=False)
                context.set_variable(f"{iter_var}_hex", f"0x{reg:X}", export=False)
                context.set_variable(val_var, val, export=False)
                context.set_variable(f"{val_var}_hex", f"0x{val:X}", export=False)
                context.set_variable(f"{iter_var}_index", idx, export=False)
                context.set_variable(f"{iter_var}_total", total, export=False)
                if auto_record:
                    context.record_data({
                        "device_addr": f"0x{dev:02X}",
                        "reg_addr": f"0x{reg:X}",
                        "value_hex": f"0x{val:X}",
                        "value_dec": val,
                    })
                if self.children:
                    from ui.pages.custom_test.executor import _execute_children
                    _execute_children(self.children, context)
            except BreakLoop:
                logger.info("I2C Traverse: break at reg=0x%X", reg)
                break
            except Exception as e:
                logger.warning("I2C Traverse: dev=0x%02X reg=0x%X => %s", dev, reg, e)
                results[reg] = None
        logger.info("I2C Traverse: dev=0x%02X reg=0x%X..0x%X => %d regs", dev, reg_start, reg_end, len(results))
        context.set_variable(result_var, results)


# ═══════════════════════════════════════════════════════════════
#  UART  —  Set / Get
# ═══════════════════════════════════════════════════════════════

@register_node
class UARTSend(BaseNode):
    node_type = "UARTSend"
    display_name = "UART Send"
    category = "instrument"
    icon = "📤"
    color = "#94a3b8"

    PARAM_SCHEMA = [
        {"key": "data", "label": "发送数据", "type": "str", "default": "AT\\r\\n"},
        {"key": "hex_mode", "label": "HEX模式", "type": "bool", "default": False},
    ]

    def execute(self, context: Any) -> None:
        uart = context.instruments.get("uart")
        if uart is None:
            raise RuntimeError("UART 未连接")
        raw = str(context.resolve_value(self.params["data"]))
        hex_mode = context.resolve_value(self.params.get("hex_mode", False))
        if hex_mode:
            payload = bytes.fromhex(raw.replace(" ", ""))
        else:
            payload = raw.replace("\\r", "\r").replace("\\n", "\n").encode("utf-8")
        if hasattr(uart, "serial_send"):
            ok = uart.serial_send(payload)
        elif hasattr(uart, "write"):
            uart.write(payload)
            ok = True
        else:
            raise RuntimeError("UART 对象不支持发送")
        logger.info("UART Send: %r => %s", payload, "OK" if ok else "FAIL")


@register_node
class UARTReceive(BaseNode):
    node_type = "UARTReceive"
    display_name = "UART Receive"
    category = "instrument"
    icon = "📥"
    color = "#94a3b8"

    PARAM_SCHEMA = [
        {"key": "timeout_s", "label": "超时(秒)", "type": "float", "default": 2.0},
        {"key": "expect", "label": "期望关键词(可空)", "type": "str", "default": ""},
        {"key": "result_var", "label": "结果存入变量", "type": "str", "default": "uart_rx"},
        {"key": "auto_record", "label": "自动记录数据", "type": "bool", "default": True},
    ]

    def execute(self, context: Any) -> None:
        uart = context.instruments.get("uart")
        if uart is None:
            raise RuntimeError("UART 未连接")
        timeout_s = float(context.resolve_value(self.params.get("timeout_s", 2.0)))
        expect = str(context.resolve_value(self.params.get("expect", "")))
        result_var = str(self.params["result_var"])
        auto_record = self.params.get("auto_record", True)
        conn = None
        if hasattr(uart, "get_serial_connection"):
            conn = uart.get_serial_connection()
        elif hasattr(uart, "read"):
            conn = uart
        if conn is None:
            raise RuntimeError("UART 无法获取串口连接")
        buf = b""
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if context.should_stop:
                break
            try:
                if hasattr(conn, "in_waiting") and conn.in_waiting > 0:
                    buf += conn.read(conn.in_waiting)
                else:
                    time.sleep(0.05)
            except Exception:
                break
            if expect and expect.encode("utf-8") in buf:
                break
        text = buf.decode("utf-8", errors="replace")
        logger.info("UART Receive (%d bytes): %s", len(buf), text[:200])
        context.set_variable(result_var, text)
        if auto_record:
            context.record_data({
                "uart_rx_len": len(buf),
                result_var: text[:500],
            })

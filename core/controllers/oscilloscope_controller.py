# -*- coding: utf-8 -*-
"""
示波器高层编排控制器（仅依赖 instruments/，无 QtWidgets）。

继承 instruments.scopes.base.OscilloscopeController，
补充 UI 中直接访问 instrument 的"粗粒度操作"：
  - set_all_channels_default: 一键 Ripple 默认配置
  - run_ripple_test: AutoRipple 测试
  - set_channel_scale_offset / set_channel_coupling / set_channel_display
  - set_timebase_position
  - set_trigger_config_safe

从 ui/pages/oscilloscope/oscilloscope_base_ui.py 平移而来，行为零变更。
"""

from typing import Optional

from instruments.scopes.base import OscilloscopeController


class OscilloscopeControllerEx(OscilloscopeController):

    def set_channel_scale_offset(self, channel: int, scale: float, offset: float):
        if not self._instrument:
            self._log("[WARN] Instrument not connected.")
            return
        try:
            self._instrument.set_channel_scale(channel, scale)
            self._instrument.set_channel_offset(channel, offset)
            self._log(f"[SETTING] CH{channel}: Scale={scale} V/div, Offset={offset} V")
        except Exception as e:
            self._log(f"[ERROR] CH{channel} setting failed: {e}")

    def set_channel_coupling(self, channel: int, coupling: str):
        if not self._instrument:
            self._log("[WARN] Instrument not connected.")
            return
        try:
            if hasattr(self._instrument, 'set_channel_coupling'):
                self._instrument.set_channel_coupling(channel, coupling)
                self._log(f"[SETTING] CH{channel}: Coupling={coupling}")
            else:
                self._log(f"[SETTING] CH{channel}: Coupling={coupling} (not supported by this instrument)")
        except Exception as e:
            self._log(f"[ERROR] CH{channel} coupling failed: {e}")

    def set_channel_display(self, channel: int, enabled: bool):
        if not self._instrument:
            self._log("[WARN] Instrument not connected.")
            return
        try:
            self._instrument.set_channel_display(channel, enabled)
            self._log(f"[SETTING] CH{channel}: {'ON' if enabled else 'OFF'}")
        except Exception as e:
            self._log(f"[ERROR] CH{channel} display failed: {e}")

    def set_channel_bandwidth(self, channel: int, bandwidth: str):
        if not self._instrument:
            self._log("[WARN] Instrument not connected.")
            return
        try:
            if hasattr(self._instrument, 'set_channel_bandwidth'):
                self._instrument.set_channel_bandwidth(channel, bandwidth)
                self._log(f"[SETTING] CH{channel}: BW={bandwidth}")
        except Exception as e:
            self._log(f"[ERROR] CH{channel} bandwidth failed: {e}")

    def set_timebase_position(self, value: float):
        if not self._instrument:
            self._log("[WARN] Instrument not connected.")
            return
        if not hasattr(self._instrument, "set_timebase_position"):
            self._log("[WARN] This instrument does not support horizontal offset.")
            return
        try:
            self._instrument.set_timebase_position(value)
            self._log(f"[SETTING] Timebase Position: {value}")
        except Exception as e:
            self._log(f"[ERROR] Timebase position failed: {e}")

    def set_trigger_config_safe(self, source_channel: int, level: float, slope: str = 'POS'):
        if not self._instrument:
            self._log("[WARN] Instrument not connected.")
            return
        try:
            self._instrument.set_trigger_config(source_channel, level, slope)
            self._log(f"[SETTING] Trigger: CH{source_channel}, Level={level} V, Slope={slope}")
        except Exception as e:
            self._log(f"[ERROR] Trigger setting failed: {e}")

    def set_all_channels_default(self, num_channels: int = 4):
        if not self._instrument:
            self._log("[WARN] Instrument not connected.")
            return False

        from instruments.scopes.tektronix.mso64b import MSO64B
        from instruments.scopes.keysight.dsox4034a import DSOX4034A

        inst = self._instrument
        if not isinstance(inst, (MSO64B, DSOX4034A)):
            self._log("[WARN] This function is only available for Tektronix MSO64B / Keysight DSO-X 4034A.")
            return False

        self._log("[QUICK] Setting all channels to default ripple config...")
        try:
            for ch in range(1, num_channels + 1):
                inst.set_channel_display(ch, True)
                if hasattr(inst, 'set_channel_bandwidth'):
                    inst.set_channel_bandwidth(ch, '20E+6')
                inst.set_channel_scale(ch, 0.5)
                inst.set_channel_offset(ch, 1.8)
            inst.set_timebase_scale(0.001)
            if hasattr(inst, 'set_timebase_position'):
                inst.set_timebase_position(50 if isinstance(inst, MSO64B) else 0.0)
            self._log("[QUICK] All channels set: ON, BW=20MHz, Scale=500mV/div, Offset=1.8V; TimeScale=1ms/div")
            return True
        except Exception as e:
            self._log(f"[ERROR] All Channel Set Default failed: {e}")
            return False

    def run_ripple_test(self, channel: int) -> bool:
        if not self._instrument:
            self._log("[WARN] Instrument not connected.")
            return False

        from instruments.scopes.tektronix.mso64b import MSO64B
        from instruments.scopes.keysight.dsox4034a import DSOX4034A

        inst = self._instrument
        if not isinstance(inst, (MSO64B, DSOX4034A)):
            self._log("[WARN] This function is only available for Tektronix MSO64B / Keysight DSO-X 4034A.")
            return False

        self._log(f"[QUICK] Running RippleSet on CH{channel}...")
        try:
            inst.set_AutoRipple_test(channel)
            self._log(f"[QUICK] RippleSet on CH{channel} completed.")
            return True
        except Exception as e:
            self._log(f"[ERROR] RippleSet on CH{channel} failed: {e}")
            return False

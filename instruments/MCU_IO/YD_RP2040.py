import re
import time

import serial

from instruments.base.instrument_base import InstrumentBase
from log_config import get_logger


logger = get_logger(__name__)


# RP2040 ADC 通道: GP26~GP29 (GP29 在 Pico 上接 VSYS), 通道 4 为内部温度传感器
ADC_PINS = (26, 27, 28, 29)
ADC_TEMP_CHANNEL = 4
ADC_VREF = 3.3
ADC_FULL_SCALE = 65535


class PicoGPIO(InstrumentBase):
    def __init__(self, port="COM9", baud=921600, timeout=0.5):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.ser = None

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
            time.sleep(2)
            self._flush()
            self._enter_raw_repl()
            logger.info("YD RP2040 connected: %s @ %s", self.port, self.baud)
            return True
        except Exception as e:
            logger.error("YD RP2040 connect failed: %s", e, exc_info=True)
            self.ser = None
            return False

    def _flush(self):
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

    def _enter_raw_repl(self):
        self.ser.write(b'\r\x03\x03')   # Ctrl+C
        time.sleep(0.1)
        self.ser.write(b'\r\x01')       # Ctrl+A
        time.sleep(0.1)
        self.ser.write(b'\x04')         # Ctrl+D
        time.sleep(0.1)
        self._flush()

    def _send(self, cmd):
        if not cmd.endswith("\n"):
            cmd += "\n"
        self.ser.write(cmd.encode())
        self.ser.write(b'\x04')   # 执行
        time.sleep(0.05)

    def _query(self, cmd, read_timeout=2.0):
        if not cmd.endswith("\n"):
            cmd += "\n"
        self._flush()
        self.ser.write(cmd.encode())
        self.ser.write(b'\x04')   # 执行
        deadline = time.time() + read_timeout
        buf = bytearray()
        while time.time() < deadline:
            chunk = self.ser.read(self.ser.in_waiting or 1)
            if chunk:
                buf.extend(chunk)
                if buf.count(b'\x04') >= 2:
                    break
            else:
                time.sleep(0.01)
        return bytes(buf).decode(errors="ignore")

    def exec(self, cmd, expect_output=False, read_timeout=2.0):
        self._ensure_connected()
        if not cmd.endswith("\n"):
            cmd += "\n"
        self._flush()
        self.ser.write(b'\x01')          # 进入原始 REPL
        time.sleep(0.02)
        self.ser.write(cmd.encode())
        self.ser.write(b'\x04')          # Ctrl+D 执行
        if not expect_output:
            time.sleep(0.05)
            return None
        return self._read_response(read_timeout)

    def _read_response(self, read_timeout=2.0):
        deadline = time.time() + read_timeout
        buf = bytearray()
        while time.time() < deadline:
            chunk = self.ser.read(self.ser.in_waiting or 1)
            if chunk:
                buf.extend(chunk)
                if b'\x04>' in buf or buf.count(b'\x04') >= 2:
                    break
            else:
                time.sleep(0.01)
        text = bytes(buf).replace(b'\x04', b'').replace(b'>', b'')
        result = text.replace(b'OK', b'', 1).decode(errors="ignore").strip()
        lines = [ln.strip() for ln in result.splitlines() if ln.strip()]
        return lines[-1] if lines else ""

    def out(self, pin, value):
        self._ensure_connected()
        cmd = f"""
from machine import Pin
Pin({pin}, Pin.OUT).value({int(value)})
"""
        self._send(cmd)

    def high(self, pin):
        self.out(pin, 1)

    def low(self, pin):
        self.out(pin, 0)

    def toggle(self, pin):
        self._ensure_connected()
        cmd = f"""
from machine import Pin
p = Pin({pin}, Pin.OUT)
p.value(0 if p.value() else 1)
"""
        self._send(cmd)

    def pulse(self, pin, width_ms=10, active=1, release_high_z=True):
        self._ensure_connected()
        release = "Pin({pin}, Pin.IN, None)".format(pin=pin) if release_high_z else ""
        cmd = f"""
from machine import Pin
import time
p = Pin({pin}, Pin.OUT)
p.value({int(active)})
time.sleep_ms({int(width_ms)})
p.value({int(not active)})
{release}
"""
        self._send(cmd)

    def hiz(self, pin):
        self.in_pull(pin, "none")

    def in_pull(self, pin, pull="none"):
        self._ensure_connected()
        if pull == "up":
            p = "Pin.PULL_UP"
        elif pull == "down":
            p = "Pin.PULL_DOWN"
        else:
            p = "None"

        cmd = f"""
from machine import Pin
Pin({pin}, Pin.IN, {p})
"""
        self._send(cmd)

    def read(self, pin):
        self._ensure_connected()
        cmd = f"""
from machine import Pin
print(Pin({pin}).value())
"""
        resp = self._query(cmd)
        return self._parse_int(resp)

    def read_pull(self, pin, pull="none"):
        self.in_pull(pin, pull)
        return self.read(pin)

    def read_adc(self, pin):
        self._ensure_connected()
        cmd = f"""
from machine import ADC, Pin
print(ADC(Pin({pin})).read_u16())
"""
        resp = self._query(cmd)
        return self._parse_int(resp)

    def read_voltage(self, pin):
        raw = self.read_adc(pin)
        if raw is None:
            return None
        return raw * ADC_VREF / ADC_FULL_SCALE

    def read_temperature(self):
        self._ensure_connected()
        cmd = f"""
from machine import ADC
raw = ADC({ADC_TEMP_CHANNEL}).read_u16()
v = raw * {ADC_VREF} / {ADC_FULL_SCALE}
print(27 - (v - 0.706) / 0.001721)
"""
        resp = self._query(cmd)
        return self._parse_float(resp)

    def pwm(self, pin, freq=1000, duty_u16=32768):
        self._ensure_connected()
        cmd = f"""
from machine import Pin, PWM
p = PWM(Pin({pin}))
p.freq({int(freq)})
p.duty_u16({int(duty_u16)})
"""
        self._send(cmd)

    def pwm_off(self, pin):
        self._ensure_connected()
        cmd = f"""
from machine import Pin, PWM
PWM(Pin({pin})).deinit()
"""
        self._send(cmd)

    def soft_reset(self):
        self._ensure_connected()
        self.ser.write(b'\r\x04')
        time.sleep(0.5)
        self._flush()
        self._enter_raw_repl()

    def _parse_int(self, resp):
        m = re.findall(r"-?\d+", resp or "")
        if not m:
            logger.warning("YD RP2040 read: no int in response %r", resp)
            return None
        return int(m[-1])

    def _parse_float(self, resp):
        m = re.findall(r"-?\d+\.?\d*", resp or "")
        for token in reversed(m):
            try:
                return float(token)
            except ValueError:
                continue
        logger.warning("YD RP2040 read: no float in response %r", resp)
        return None

    def identify(self):
        return f"YD RP2040 GPIO ({self.port})"

    def is_connected(self):
        return self.ser is not None and getattr(self.ser, "is_open", False)

    def disconnect(self):
        if self.ser is not None:
            try:
                self.ser.close()
            finally:
                self.ser = None

    def close(self):
        self.disconnect()

    def _ensure_connected(self):
        if not self.is_connected():
            raise RuntimeError("YD RP2040 is not connected")



# 使用示例
if __name__ == "__main__":
    gpio = PicoGPIO("COM9")
    gpio.connect()
    test_pin = 0

    gpio.high(test_pin)
    time.sleep(0.1)
    gpio.low(test_pin)
    gpio.pulse(test_pin, width_ms=20)

    gpio.in_pull(6, "up")
    val = gpio.read(6)
    logger.info("GPIO6 = %s", val)

    logger.info("ADC0 voltage = %.3f V", gpio.read_voltage(26))
    logger.info("Chip temperature = %.2f C", gpio.read_temperature())

    gpio.disconnect()

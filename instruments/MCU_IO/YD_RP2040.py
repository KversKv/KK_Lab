import time

import serial

from instruments.base.instrument_base import InstrumentBase
from log_config import get_logger


logger = get_logger(__name__)


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

    def _send(self, cmd):
        if not cmd.endswith("\n"):
            cmd += "\n"
        self.ser.write(cmd.encode())
        self.ser.write(b'\x04')   # 执行
        time.sleep(0.05)

    def out(self, pin, value):
        self._ensure_connected()
        cmd = f"""
from machine import Pin
Pin({pin}, Pin.OUT).value({int(value)})
"""
        self._send(cmd)

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
print(Pin({pin}, Pin.IN).value())
"""
        self._send(cmd)
        return self._readline()

    def _readline(self):
        while True:
            line = self.ser.readline().decode().strip()
            if line and line.isdigit():
                return int(line)

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
    # 输出
    while True:
        gpio.out(test_pin, 1)
        time.sleep(0.01)
        gpio.out(test_pin, 0)

    # 输入
    gpio.in_pull(6, "up")
    val = gpio.read(6)
    logger.info("GPIO6 = %s", val)

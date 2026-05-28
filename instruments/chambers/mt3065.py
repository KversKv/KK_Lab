import serial

from instruments.chambers.base import ChamberBase
from log_config import get_logger

logger = get_logger(__name__)


class MT3065(ChamberBase):
    """MT3065 serial temperature chamber driver."""

    def __init__(self, port: str, baudrate: int = 19200, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self._last_set_temp = None

    def connect(self, *args, **kwargs):
        if self.ser is None:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        elif not self.ser.is_open:
            self.ser.open()
        return True

    def disconnect(self):
        if self.ser is not None and self.ser.is_open:
            self.ser.close()

    def close(self):
        self.disconnect()

    def is_connected(self) -> bool:
        return bool(self.ser is not None and self.ser.is_open)

    def identify(self) -> str:
        return "MT3065 Temperature Chamber"

    def _build_command(self, command: str) -> bytes:
        return (command + "\r").encode()

    def _send_command(self, command: str) -> str:
        if not self.is_connected():
            raise ConnectionError("MT3065 serial port is not open")
        request = self._build_command(command)
        self.ser.write(request)
        response = self.ser.read(1024)
        return response.decode(errors="ignore").strip()

    def _read_temperature_fields(self):
        response = self._send_command("1,TEMP?")
        lines = [line.strip() for line in response.splitlines() if line.strip()]
        if not lines:
            logger.warning("MT3065 temperature response is empty")
            return None
        parts = [part.strip() for part in lines[0].split(",")]
        if len(parts) < 2:
            logger.warning("MT3065 temperature response format invalid: %s", response)
            return None
        try:
            current = float(parts[0])
            setpoint = float(parts[1])
            upper = float(parts[2]) if len(parts) > 2 and parts[2] else None
            lower = float(parts[3]) if len(parts) > 3 and parts[3] else None
            return current, setpoint, upper, lower
        except ValueError:
            logger.warning("MT3065 temperature response parse failed: %s", response)
            return None

    def get_current_temp(self):
        values = self._read_temperature_fields()
        if values is None:
            return None
        return values[0]

    def get_set_temp(self):
        values = self._read_temperature_fields()
        if values is None:
            return self._last_set_temp
        return values[1]

    def set_temperature(self, temp_celsius: float):
        response = self._send_command(f"1,TEMP,S{temp_celsius}")
        if "OK" not in response.upper():
            raise RuntimeError(f"MT3065 set temperature failed: {response}")
        self._last_set_temp = float(temp_celsius)
        logger.info("MT3065 temperature set to %.1f°C", temp_celsius)

    def start(self):
        response = self._send_command("1,POWER,ON")
        if "OK" not in response.upper():
            raise RuntimeError(f"MT3065 start failed: {response}")
        logger.info("MT3065 chamber started")

    def stop(self):
        response = self._send_command("1,POWER,OFF")
        if "OK" not in response.upper():
            raise RuntimeError(f"MT3065 stop failed: {response}")
        logger.info("MT3065 chamber stopped")

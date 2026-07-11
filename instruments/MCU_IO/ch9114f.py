import ctypes
import os
import re
import sys
import time
from contextlib import contextmanager
from ctypes import wintypes

if __package__ in (None, ""):
    _PROJECT_ROOT = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from instruments.base.exceptions import InstrumentConnectionError, InstrumentError
from instruments.base.instrument_base import InstrumentBase
from log_config import get_logger


logger = get_logger(__name__)


_DRIVER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CH343SER")
_DLL_CANDIDATES = (
    os.path.join(_DRIVER_DIR, "Driver", "CH343PTA64.dll"),
    os.path.join(_DRIVER_DIR, "Driver", "CH343PT.DLL"),
    "CH343PTA64.dll",
    "CH343PT.DLL",
)

USER_TYPE_CH9114L = 0xF0
USER_TYPE_CH9114W = 0xF1
USER_TYPE_CH9114F = 0xF2
USER_TYPE_UNKNOWN = 0xFF

CH9114_USB_VID = 0x1A86
CH9114_USB_PID = 0x55E8

CH910x_SUCCESS = 0x00
CH910x_INVALID_HANDLE = 0x01
CH910x_INVALID_PARAMETER = 0x02
CH910x_DEVICE_IO_FAILED = 0x03
CH910x_FUNCTION_NOT_SUPPORTED = 0x04
CH910x_NOT_INIT = 0x05

_RETURN_MESSAGES = {
    CH910x_SUCCESS: "success",
    CH910x_INVALID_HANDLE: "invalid handle",
    CH910x_INVALID_PARAMETER: "invalid parameter",
    CH910x_DEVICE_IO_FAILED: "device io failed",
    CH910x_FUNCTION_NOT_SUPPORTED: "function not supported",
    CH910x_NOT_INIT: "not initialized",
}

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

DIR_INPUT = 0
DIR_OUTPUT = 1
LEVEL_LOW = 0
LEVEL_HIGH = 1

LOW = 0
HIGH = 1

CH9114_GPIO_COUNT = 16
CH9114_GPIO_MAX = 31


class _ChipPropertyS(ctypes.Structure):
    _fields_ = [
        ("ChipType", ctypes.c_ubyte),
        ("ChipTypeStr", ctypes.c_char * 32),
        ("FwVerStr", ctypes.c_char * 32),
        ("GpioCount", ctypes.c_ubyte),
        ("IsEmbbedEeprom", wintypes.BOOL),
        ("IsSupportMcuBootCtrl", wintypes.BOOL),
        ("ManufacturerString", ctypes.c_char * 64),
        ("ProductString", ctypes.c_char * 64),
        ("bcdDevice", ctypes.c_ushort),
        ("PortIndex", ctypes.c_ubyte),
        ("IsSupportGPIOInit", wintypes.BOOL),
        ("PortName", ctypes.c_char * 32),
        ("ResvD", ctypes.c_ulong * 8),
    ]


def _load_dll():
    last_error = None
    for path in _DLL_CANDIDATES:
        try:
            return ctypes.WinDLL(path)
        except OSError as exc:
            last_error = exc
    raise InstrumentConnectionError(
        f"Failed to load CH343PT DLL, tried: {_DLL_CANDIDATES}; last error: {last_error}"
    )


def _uart_index(info):
    desc = info.description or ""
    match = re.search(r"SERIAL-([A-Z])\b", desc)
    if match:
        return ord(match.group(1)) - ord("A")
    location = info.location or ""
    if "." in location:
        digits = "".join(filter(str.isdigit, location.rsplit(".", 1)[-1]))
        if digits:
            return int(digits) // 2
    return 0xFFFF


def list_ch9114f_ports():
    from serial.tools import list_ports
    entries = []
    for info in list_ports.comports():
        if info.vid == CH9114_USB_VID and info.pid == CH9114_USB_PID:
            entries.append((_uart_index(info), info.device))
    entries.sort(key=lambda item: item[0])
    ports = [device for _, device in entries]
    logger.info("Detected CH9114F ports (UART order): %s", ports)
    return ports


def find_ch9114f_port():
    ports = list_ch9114f_ports()
    return ports[0] if ports else None


def find_ch9114f_last_port():
    ports = list_ch9114f_ports()
    return ports[-1] if ports else None


class CH9114F(InstrumentBase):

    def __init__(self, port="auto"):
        self.port = port
        self._dll = None
        self._handle = None
        self._prop = None

    def connect(self):
        try:
            if not self.port or str(self.port).strip().lower() == "auto":
                detected = find_ch9114f_last_port()
                if detected is None:
                    raise InstrumentConnectionError("No CH9114F device detected")
                logger.info("CH9114F auto-selected last UART port: %s", detected)
                self.port = detected
            self._dll = _load_dll()
            self._configure_prototypes()
            self._handle = self._open_port(self.port)
            self._prop = self._read_chip_property()
            self._gpio_init()
            logger.info(
                "CH9114F connected: %s, chip=%s, gpio=%d",
                self.port,
                self._prop.ChipTypeStr.decode(errors="ignore"),
                self._prop.GpioCount,
            )
            return True
        except Exception as exc:
            logger.error("CH9114F connect failed: %s", exc, exc_info=True)
            self._close_handle()
            self._dll = None
            self._prop = None
            return False

    def disconnect(self):
        self._close_handle()
        self._prop = None
        self._dll = None

    def close(self):
        self.disconnect()

    def is_connected(self):
        return self._handle is not None and self._dll is not None

    def __enter__(self):
        if not self.is_connected():
            if not self.connect():
                raise InstrumentConnectionError(
                    f"CH9114F failed to connect on {self.port}"
                )
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.disconnect()
        return False

    @contextmanager
    def _session(self):
        opened_here = False
        if not self.is_connected():
            if not self.connect():
                raise InstrumentConnectionError(
                    f"CH9114F failed to connect on {self.port}"
                )
            opened_here = True
        try:
            yield self
        finally:
            if opened_here:
                self.disconnect()

    def set_gpio(self, pin, level):
        with self._session():
            self.set_output(pin)
            self.out(pin, HIGH if int(level) else LOW)
        return int(bool(level))

    def get_gpio(self, pin):
        with self._session():
            return self.read(pin)

    def read_input(self, pin):
        with self._session():
            self.set_input(pin)
            return self.read(pin)

    def toggle_gpio(self, pin):
        with self._session():
            self.set_output(pin)
            new_level = LOW if self.read(pin) else HIGH
            self.out(pin, new_level)
        return new_level

    def identify(self):
        if self._prop is None:
            return f"CH9114F GPIO ({self.port})"
        return (
            f"{self._prop.ChipTypeStr.decode(errors='ignore')} GPIO "
            f"({self.port}, fw={self._prop.FwVerStr.decode(errors='ignore')}, "
            f"pins={self._prop.GpioCount})"
        )

    @property
    def gpio_count(self):
        return 0 if self._prop is None else int(self._prop.GpioCount)

    def config(self, pin, direction=DIR_OUTPUT, gpio_func=True):
        self._ensure_connected()
        mask = self._pin_mask(pin)
        func_set = mask if gpio_func else 0
        dir_out = mask if direction == DIR_OUTPUT else 0
        ret = self._dll.CH910x_GpioConfig(
            self._handle,
            ctypes.byref(self._prop),
            ctypes.c_ulong(mask),
            ctypes.c_ulong(func_set),
            ctypes.c_ulong(dir_out),
        )
        self._check(ret, "CH910x_GpioConfig")

    def set_output(self, pin):
        self.config(pin, direction=DIR_OUTPUT, gpio_func=True)

    def set_input(self, pin, gpio_func=True):
        self.config(pin, direction=DIR_INPUT, gpio_func=gpio_func)

    def out(self, pin, value):
        self._ensure_connected()
        self.set_output(pin)
        mask = self._pin_mask(pin)
        data_out = mask if int(value) else 0
        ret = self._dll.CH910x_GpioSet(
            self._handle,
            ctypes.byref(self._prop),
            ctypes.c_ulong(mask),
            ctypes.c_ulong(data_out),
        )
        self._check(ret, "CH910x_GpioSet")

    def in_pull(self, pin, pull="none"):
        self._ensure_connected()
        self.set_input(pin, gpio_func=True)

    def pulse(self, pin, width_ms=10, active=1, release_high_z=True):
        # 对齐 PicoGPIO.pulse 接口；CH9114F 通过 out+sleep+out 实现
        self._ensure_connected()
        self.set_output(pin)
        idle = 0 if int(active) else 1
        self.out(pin, idle)
        self.out(pin, 1 if int(active) else 0)
        time.sleep(max(0, int(width_ms)) / 1000.0)
        self.out(pin, idle)
        if release_high_z:
            self.set_input(pin, gpio_func=True)

    def high(self, pin):
        self.out(pin, LEVEL_HIGH)

    def low(self, pin):
        self.out(pin, LEVEL_LOW)

    def toggle(self, pin):
        self.out(pin, 0 if self.read(pin) else 1)

    def read(self, pin):
        self._ensure_connected()
        status = ctypes.c_ulong(0)
        ret = self._dll.CH910x_GpioGet(
            self._handle,
            ctypes.byref(self._prop),
            ctypes.byref(status),
        )
        self._check(ret, "CH910x_GpioGet")
        return 1 if status.value & self._pin_mask(pin) else 0

    def read_all(self):
        self._ensure_connected()
        status = ctypes.c_ulong(0)
        ret = self._dll.CH910x_GpioGet(
            self._handle,
            ctypes.byref(self._prop),
            ctypes.byref(status),
        )
        self._check(ret, "CH910x_GpioGet")
        return int(status.value)

    def get_config(self, pin):
        self._ensure_connected()
        func_set = ctypes.c_ulong(0)
        dir_out = ctypes.c_ulong(0)
        data_out = ctypes.c_ulong(0)
        ret = self._dll.CH910x_GetGpioConfig(
            self._handle,
            ctypes.byref(self._prop),
            ctypes.byref(func_set),
            ctypes.byref(dir_out),
            ctypes.byref(data_out),
        )
        self._check(ret, "CH910x_GetGpioConfig")
        mask = self._pin_mask(pin)
        return {
            "gpio_func": bool(func_set.value & mask),
            "direction": DIR_OUTPUT if dir_out.value & mask else DIR_INPUT,
            "level": 1 if data_out.value & mask else 0,
        }

    def config_mask(self, enable_mask, func_mask, dir_out_mask):
        self._ensure_connected()
        ret = self._dll.CH910x_GpioConfig(
            self._handle,
            ctypes.byref(self._prop),
            ctypes.c_ulong(enable_mask),
            ctypes.c_ulong(func_mask),
            ctypes.c_ulong(dir_out_mask),
        )
        self._check(ret, "CH910x_GpioConfig")

    def set_mask(self, enable_mask, data_out_mask):
        self._ensure_connected()
        ret = self._dll.CH910x_GpioSet(
            self._handle,
            ctypes.byref(self._prop),
            ctypes.c_ulong(enable_mask),
            ctypes.c_ulong(data_out_mask),
        )
        self._check(ret, "CH910x_GpioSet")

    def _configure_prototypes(self):
        dll = self._dll
        dll.CH343PT_GetChipProperty.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ChipPropertyS)]
        dll.CH343PT_GetChipProperty.restype = ctypes.c_ubyte

        if hasattr(dll, "CH910x_GpioInit"):
            dll.CH910x_GpioInit.argtypes = [wintypes.HANDLE]
            dll.CH910x_GpioInit.restype = ctypes.c_ubyte

        dll.CH910x_GpioConfig.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_ChipPropertyS),
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
        ]
        dll.CH910x_GpioConfig.restype = ctypes.c_ubyte

        dll.CH910x_GpioSet.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_ChipPropertyS),
            ctypes.c_ulong,
            ctypes.c_ulong,
        ]
        dll.CH910x_GpioSet.restype = ctypes.c_ubyte

        dll.CH910x_GpioGet.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_ChipPropertyS),
            ctypes.POINTER(ctypes.c_ulong),
        ]
        dll.CH910x_GpioGet.restype = ctypes.c_ubyte

        dll.CH910x_GetGpioConfig.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_ChipPropertyS),
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_ulong),
        ]
        dll.CH910x_GetGpioConfig.restype = ctypes.c_ubyte

    def _open_port(self, port):
        device_path = f"\\\\.\\{port}"
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        kernel32.CreateFileW.restype = wintypes.HANDLE
        handle = kernel32.CreateFileW(
            device_path,
            GENERIC_READ | GENERIC_WRITE,
            0,
            None,
            OPEN_EXISTING,
            0,
            None,
        )
        if handle is None or handle == INVALID_HANDLE_VALUE:
            err = ctypes.get_last_error()
            raise InstrumentConnectionError(
                f"Failed to open {port} (CreateFileW error {err})"
            )
        return handle

    def _gpio_init(self):
        if not hasattr(self._dll, "CH910x_GpioInit"):
            logger.debug("CH910x_GpioInit not exported by DLL, skipping init")
            return
        ret = self._dll.CH910x_GpioInit(self._handle)
        if ret != CH910x_SUCCESS:
            raise InstrumentConnectionError(
                f"CH910x_GpioInit failed: {self._ret_msg(ret)}"
            )

    def _read_chip_property(self):
        prop = _ChipPropertyS()
        chip_type = self._dll.CH343PT_GetChipProperty(self._handle, ctypes.byref(prop))
        if chip_type == USER_TYPE_UNKNOWN:
            raise InstrumentConnectionError(
                f"{self.port} is not a recognized CH910x device"
            )
        if chip_type not in (USER_TYPE_CH9114F, USER_TYPE_CH9114L, USER_TYPE_CH9114W):
            logger.warning(
                "CH9114F: unexpected chip type 0x%02X on %s, proceeding anyway",
                chip_type,
                self.port,
            )
        if prop.GpioCount == 0:
            raise InstrumentConnectionError(
                f"{self.port} reports 0 GPIO pins (not supported)"
            )
        return prop

    def _pin_mask(self, pin):
        pin = int(pin)
        if pin < 0 or pin > 31:
            raise InstrumentError(f"GPIO pin out of range (0-31): {pin}")
        return 1 << pin

    def _check(self, ret, func_name):
        if ret != CH910x_SUCCESS:
            raise InstrumentError(f"{func_name} failed: {self._ret_msg(ret)}")

    @staticmethod
    def _ret_msg(ret):
        return _RETURN_MESSAGES.get(ret, f"unknown error 0x{ret:02X}")

    def _close_handle(self):
        if self._handle is not None:
            try:
                ctypes.windll.kernel32.CloseHandle(self._handle)
            except Exception as exc:
                logger.warning("CH9114F close handle failed: %s", exc, exc_info=True)
            finally:
                self._handle = None

    def _ensure_connected(self):
        if not self.is_connected() or self._prop is None:
            raise InstrumentConnectionError("CH9114F is not connected")


def _make_set(pin):
    def _setter(self, level=HIGH):
        return self.set_gpio(pin, level)
    _setter.__name__ = f"setGPIO{pin}"
    return _setter


def _make_get(pin):
    def _getter(self):
        return self.get_gpio(pin)
    _getter.__name__ = f"getGPIO{pin}"
    return _getter


def _make_toggle(pin):
    def _toggler(self):
        return self.toggle_gpio(pin)
    _toggler.__name__ = f"toggleGPIO{pin}"
    return _toggler


for _pin in range(CH9114_GPIO_MAX + 1):
    setattr(CH9114F, f"setGPIO{_pin}", _make_set(_pin))
    setattr(CH9114F, f"getGPIO{_pin}", _make_get(_pin))
    setattr(CH9114F, f"toggleGPIO{_pin}", _make_toggle(_pin))
del _pin


def test_toggle_gpio0(port="auto", interval=1.0, pin=0):
    gpio = CH9114F(port)
    if not gpio.connect():
        logger.error("CH9114F connect failed on %s", port)
        return
    try:
        logger.info("identify: %s", gpio.identify())
        gpio.set_output(pin)
        logger.info("Start toggling GPIO%d every %.1fs (Ctrl+C to stop)", pin, interval)
        while True:
            gpio.toggle(pin)
            logger.info("GPIO%d = %s", pin, gpio.read(pin))
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Toggle test stopped by user")
    finally:
        gpio.disconnect()


def demo():
    ch9114f = CH9114F()

    ch9114f.setGPIO0(HIGH)
    logger.info("GPIO0 -> HIGH, read back = %s", ch9114f.getGPIO0())

    ch9114f.setGPIO0(LOW)
    logger.info("GPIO0 -> LOW, read back = %s", ch9114f.getGPIO0())

    logger.info("GPIO0 toggle -> %s", ch9114f.toggleGPIO0())

    ch9114f.set_gpio(1, HIGH)
    logger.info("GPIO1 (generic) = %s", ch9114f.get_gpio(1))

    with CH9114F() as session:
        session.setGPIO2(HIGH)
        session.setGPIO3(LOW)
        logger.info("batch in one session: GPIO2=%s GPIO3=%s",
                    session.read(2), session.read(3))


if __name__ == "__main__":
    demo()

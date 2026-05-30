from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import socket
import struct
import time
from dataclasses import dataclass
from typing import Any, Iterable

try:
    from instruments.chambers.base import ChamberBase
except ModuleNotFoundError:
    class ChamberBase:
        pass

try:
    from log_config import get_logger
except ModuleNotFoundError:
    import logging

    def get_logger(name: str):
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        return logging.getLogger(name)


logger = get_logger(__name__)


EVENT_CLICKDOWN = 0
EVENT_CLICKUP = 1
EVENT_SCRINIT = 2
EVENT_SCRDESTROY = 3
EVENT_DATATRANS = 4
DEFAULT_WT2040_HOST = "192.168.1.66"
DEFAULT_WT2040_PORT = 80


class ChamberConfigError(RuntimeError):
    pass


class ChamberCommandError(RuntimeError):
    pass


@dataclass(frozen=True)
class HmiPart:
    screen: int
    name: str
    type: str
    index: int | None = None
    text: str = ""
    left: int | None = None
    right: int | None = None
    top: int | None = None
    bottom: int | None = None
    hidden: bool = False
    enabled: bool | None = None


@dataclass(frozen=True)
class ChamberControlConfig:
    monitor_screen: int = 114
    temperature_setpoint_part: str = "114_NUM_3"
    temperature_readback_part: str = "114_NUM_25"
    status_title_part: str = "114_TXT_8"
    start_part: str = "114_CmpFS_5"
    running_screen: int = 115
    running_temperature_setpoint_part: str = "115_NUM_7"
    running_temperature_readback_part: str = "115_NUM_24"
    running_status_title_part: str = "115_TXT_11"
    stop_part: str | None = "115_CmpFS_5"
    start_confirm_texts: tuple[str, ...] = ("\u91cd\u65b0\u8fd0\u884c",)
    stop_confirm_texts: tuple[str, ...] = ("\u662f",)
    humidity_setpoint_part: str | None = None
    humidity_readback_part: str | None = None
    menu_screen: int = 1
    monitor_menu_part: str = "1_BS_20"
    numeric_keypad_screen: int = 1000
    numeric_display_part: str = "1000_STR_26"
    numeric_keys: dict[str, str] | None = None

    @classmethod
    def bt107c_default(cls) -> "ChamberControlConfig":
        return cls(
            numeric_keys={
                "0": "1000_KY_3",
                "1": "1000_KY_5",
                "2": "1000_KY_4",
                "3": "1000_KY_1",
                "4": "1000_KY_10",
                "5": "1000_KY_9",
                "6": "1000_KY_6",
                "7": "1000_KY_16",
                "8": "1000_KY_15",
                "9": "1000_KY_11",
                ".": "1000_KY_8",
                "-": "1000_KY_14",
                "backspace": "1000_KY_7",
                "enter": "1000_KY_23",
                "cancel": "1000_KY_2",
            }
        )


def _varint(value: int) -> bytes:
    out = bytearray()
    value &= (1 << 64) - 1
    while value > 0x7F:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def _field_varint(field_no: int, value: int) -> bytes:
    return _varint((field_no << 3) | 0) + _varint(value)


def _field_bytes(field_no: int, value: bytes) -> bytes:
    return _varint((field_no << 3) | 2) + _varint(len(value)) + value


def encode_hmi_event(scrno: int, part_name: str, event_type: int, event_buffer: str = "") -> bytes:
    """Encode proto.hmiproto.hmievent with the same fields used by the HMI page."""
    payload = bytearray()
    payload += _field_varint(1, int(scrno))
    payload += _field_varint(2, int(event_type))
    payload += _field_bytes(9, part_name.encode("utf-8"))
    payload += _field_bytes(10, str(event_buffer).encode("utf-8"))
    return bytes(payload)


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    shift = 0
    value = 0
    while True:
        b = data[pos]
        pos += 1
        value |= (b & 0x7F) << shift
        if not b & 0x80:
            return value, pos
        shift += 7


def _decode_message(data: bytes) -> list[tuple[int, int, Any]]:
    fields: list[tuple[int, int, Any]] = []
    pos = 0
    while pos < len(data):
        key, pos = _read_varint(data, pos)
        field_no = key >> 3
        wire_type = key & 0x07
        if wire_type == 0:
            value, pos = _read_varint(data, pos)
        elif wire_type == 1:
            value = data[pos : pos + 8]
            pos += 8
        elif wire_type == 2:
            length, pos = _read_varint(data, pos)
            value = data[pos : pos + length]
            pos += length
        elif wire_type == 5:
            value = data[pos : pos + 4]
            pos += 4
        else:
            raise ValueError(f"Unsupported protobuf wire type {wire_type}")
        fields.append((field_no, wire_type, value))
    return fields


def _safe_decode_message(data: bytes) -> list[tuple[int, int, Any]] | None:
    try:
        return _decode_message(data)
    except (IndexError, ValueError):
        return None


def _first(fields: list[tuple[int, int, Any]], field_no: int) -> Any | None:
    for no, _, value in fields:
        if no == field_no:
            return value
    return None


def _all(fields: list[tuple[int, int, Any]], field_no: int) -> list[Any]:
    return [value for no, _, value in fields if no == field_no]


def _text(value: Any | None) -> str:
    if not isinstance(value, (bytes, bytearray)):
        return ""
    return bytes(value).decode("utf-8", errors="replace")


def parse_hmi_parts(payload: bytes) -> list[HmiPart]:
    """Extract screen parts from a proto.hmiproto.hmiact frame."""
    socketio = _parse_socketio_event(payload)
    if socketio is not None:
        name, args = socketio
        if name not in {"scrinfo", "updatepart"} or not args:
            return []
        try:
            data = json.loads(args[0])
        except (TypeError, ValueError):
            return []
        return [_parse_json_part(part) for part in data.get("Parts", []) if _parse_json_part(part) is not None]

    act = _safe_decode_message(payload)
    if act is None:
        return []
    parts: list[HmiPart] = []

    for raw_common in _all(act, 4):
        common = _safe_decode_message(raw_common)
        if common is None:
            continue
        enabled = _first(common, 3)
        basic_raw = _first(common, 2)
        if isinstance(basic_raw, (bytes, bytearray)):
            part = _parse_basic(bytes(basic_raw), enabled=bool(enabled) if enabled is not None else None)
            if part:
                parts.append(part)

    for raw_downlist in _all(act, 5):
        downlist = _safe_decode_message(raw_downlist)
        if downlist is None:
            continue
        basic_raw = _first(downlist, 2)
        if isinstance(basic_raw, (bytes, bytearray)):
            part = _parse_basic(bytes(basic_raw))
            if part:
                parts.append(part)

    for raw_custom in _all(act, 6):
        custom = _safe_decode_message(raw_custom)
        if custom is None:
            continue
        basic_raw = _first(custom, 2)
        if isinstance(basic_raw, (bytes, bytearray)):
            part = _parse_basic(bytes(basic_raw))
            if part:
                parts.append(part)

    for raw_slider in _all(act, 7):
        slider = _safe_decode_message(raw_slider)
        if slider is None:
            continue
        basic_raw = _first(slider, 2)
        if isinstance(basic_raw, (bytes, bytearray)):
            part = _parse_basic(bytes(basic_raw))
            if part:
                parts.append(part)

    return parts


def parse_hmi_basic_updates(payload: bytes) -> list[dict[str, Any]]:
    socketio = _parse_socketio_event(payload)
    if socketio is not None:
        name, args = socketio
        if name not in {"scrinfo", "updatepart"} or not args:
            return []
        try:
            data = json.loads(args[0])
        except (TypeError, ValueError):
            return []
        updates: list[dict[str, Any]] = []
        for part in data.get("Parts", []):
            parsed = _parse_json_part(part)
            if parsed is None:
                continue
            updates.append(
                {
                    "screen": parsed.screen,
                    "index": parsed.index,
                    "name": parsed.name,
                    "type": parsed.type,
                    "text": parsed.text,
                    "hidden": parsed.hidden,
                }
            )
        return updates

    act = _safe_decode_message(payload)
    if act is None:
        return []
    event_screen = None
    event_raw = _first(act, 2)
    if isinstance(event_raw, (bytes, bytearray)):
        event = _safe_decode_message(bytes(event_raw))
        if event is not None:
            event_screen = _maybe_int(_first(event, 1))
    updates: list[dict[str, Any]] = []
    for raw_common in _all(act, 4):
        common = _safe_decode_message(raw_common)
        if common is None:
            continue
        basic_raw = _first(common, 2)
        if isinstance(basic_raw, (bytes, bytearray)):
            basic = _safe_decode_message(bytes(basic_raw))
            if basic is None:
                continue
            updates.append(
                {
                    "screen": _maybe_int(_first(basic, 1)) or event_screen,
                    "index": _maybe_int(_first(basic, 2)),
                    "name": _text(_first(basic, 8)),
                    "type": _text(_first(basic, 7)),
                    "text": _text(_first(basic, 10)),
                    "hidden": bool(_first(basic, 9)) if _first(basic, 9) is not None else None,
                }
            )
    return updates


def _parse_basic(payload: bytes, enabled: bool | None = None) -> HmiPart | None:
    basic = _safe_decode_message(payload)
    if basic is None:
        return None
    screen = _first(basic, 1)
    name = _text(_first(basic, 8))
    if screen is None or not name:
        return None
    return HmiPart(
        screen=int(screen),
        name=name,
        type=_text(_first(basic, 7)),
        index=_maybe_int(_first(basic, 2)),
        text=_text(_first(basic, 10)),
        left=_maybe_int(_first(basic, 3)),
        right=_maybe_int(_first(basic, 4)),
        top=_maybe_int(_first(basic, 5)),
        bottom=_maybe_int(_first(basic, 6)),
        hidden=bool(_first(basic, 9)) if _first(basic, 9) is not None else False,
        enabled=enabled,
    )


def _maybe_int(value: Any | None) -> int | None:
    return int(value) if value is not None else None


def _parse_socketio_event(payload: bytes) -> tuple[str, list[Any]] | None:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not text.startswith("5:::"):
        return None
    try:
        event = json.loads(text[4:])
    except ValueError:
        return None
    name = event.get("name")
    args = event.get("args", [])
    if not isinstance(name, str) or not isinstance(args, list):
        return None
    return name, args

def _parse_json_part(raw: dict[str, Any]) -> HmiPart | None:
    screen = raw.get("ScrNo")
    name = raw.get("PartName")
    if screen is None or not name:
        return None
    area = str(raw.get("Area") or "").split()
    left = _maybe_int(area[0]) if len(area) >= 1 else None
    top = _maybe_int(area[1]) if len(area) >= 2 else None
    width = _maybe_int(area[2]) if len(area) >= 3 else None
    height = _maybe_int(area[3]) if len(area) >= 4 else None
    index = _part_index_from_name(str(name))
    return HmiPart(
        screen=int(screen),
        name=str(name),
        type=str(raw.get("PartType") or ""),
        index=index,
        text=str(raw.get("Text") or ""),
        left=left,
        right=(left + width) if left is not None and width is not None else None,
        top=top,
        bottom=(top + height) if top is not None and height is not None else None,
        hidden=str(raw.get("Hide") or "0") == "1",
        enabled=str(raw.get("Enable")) != "0" if raw.get("Enable") is not None else None,
    )


def _part_index_from_name(name: str) -> int | None:
    match = re.match(r"^[A-Za-z]+_(\d+)(?:_\d+)?$", name)
    return int(match.group(1)) if match else None


class MinimalWebSocket:
    """Small Socket.IO 0.9 WebSocket client for the embedded HMI.

    The HMI page uses socket.io.js 0.9.x. That version first requests a
    Socket.IO session id over HTTP, then upgrades to a WebSocket at
    /socket.io/1/websocket/<session-id>.
    """

    def __init__(self, host: str, port: int = 80, path: str = "/", timeout: float = 5.0):
        self.host = host
        self.port = port
        self.path = path
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self.session_id: str | None = None

    def __enter__(self) -> "MinimalWebSocket":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def connect(self) -> None:
        sid = self._socketio_handshake()
        self.session_id = sid
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        host_header = self.host if self.port == 80 else f"{self.host}:{self.port}"
        ws_path = f"/socket.io/1/websocket/{sid}"
        req = (
            f"GET {ws_path} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "User-Agent: Mozilla/5.0\r\n"
            "Origin: http://{host}\r\n"
            "\r\n"
        ).format(host=self.host)
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        sock.sendall(req.encode("ascii"))
        resp = sock.recv(4096)
        if b" 101 " not in resp.split(b"\r\n", 1)[0]:
            raise ConnectionError(
                f"Socket.IO WebSocket handshake failed on {ws_path}: {resp[:200]!r}"
            )
        accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        )
        if accept not in resp:
            raise ConnectionError("WebSocket handshake accept key mismatch")
        self.sock = sock
        frame = self.recv_frame(timeout=2.0)
        if frame is not None and frame[1] != b"1::":
            return

    def _socketio_handshake(self) -> str:
        host_header = self.host if self.port == 80 else f"{self.host}:{self.port}"
        req = (
            f"GET /socket.io/1/?t={int(time.time() * 1000)} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        try:
            sock.sendall(req.encode("ascii"))
            resp = self._read_http_response(sock)
        finally:
            sock.close()
        header, _, body = resp.partition(b"\r\n\r\n")
        if b" 200 " not in header.split(b"\r\n", 1)[0]:
            raise ConnectionError(f"Socket.IO handshake failed: {resp[:200]!r}")
        if b"transfer-encoding: chunked" in header.lower():
            body = self._decode_chunked(body)
        text = body.decode("ascii", errors="replace").strip()
        sid = text.split(":", 1)[0]
        if not sid:
            raise ConnectionError(f"Socket.IO handshake did not return a session id: {text!r}")
        return sid

    def _read_http_response(self, sock: socket.socket) -> bytes:
        sock.settimeout(self.timeout)
        chunks = bytearray()
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks += chunk
        return bytes(chunks)

    def _decode_chunked(self, body: bytes) -> bytes:
        out = bytearray()
        pos = 0
        while pos < len(body):
            line_end = body.find(b"\r\n", pos)
            if line_end < 0:
                break
            size_text = body[pos:line_end].split(b";", 1)[0]
            try:
                size = int(size_text, 16)
            except ValueError:
                break
            pos = line_end + 2
            if size == 0:
                break
            out += body[pos : pos + size]
            pos += size + 2
        return bytes(out)

    def emit_event(self, name: str, args: list[Any]) -> None:
        self.send_text("5:::" + json.dumps({"name": name, "args": args}, separators=(",", ":"), ensure_ascii=False))

    def send_text(self, text: str) -> None:
        self._send_frame(0x81, text.encode("utf-8"))

    def send_binary(self, payload: bytes) -> None:
        self._send_frame(0x82, payload)

    def _send_frame(self, first_byte: int, payload: bytes) -> None:
        if self.sock is None:
            raise RuntimeError("WebSocket is not connected")
        mask = os.urandom(4)
        header = bytearray([first_byte])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header += struct.pack("!H", length)
        else:
            header.append(0x80 | 127)
            header += struct.pack("!Q", length)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header) + mask + masked)

    def recv_frame(self, timeout: float | None = None) -> tuple[int, bytes] | None:
        if self.sock is None:
            raise RuntimeError("WebSocket is not connected")
        self.sock.settimeout(self.timeout if timeout is None else timeout)
        try:
            first = self.sock.recv(2)
        except socket.timeout:
            return None
        if not first:
            return None
        opcode = first[0] & 0x0F
        masked = bool(first[1] & 0x80)
        length = first[1] & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]
        mask = self._read_exact(4) if masked else b""
        payload = self._read_exact(length)
        if masked:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        if opcode == 1 and payload == b"2::":
            self.send_text("2::")
        return opcode, payload

    def _read_exact(self, length: int) -> bytes:
        if self.sock is None:
            raise RuntimeError("WebSocket is not connected")
        chunks = bytearray()
        while len(chunks) < length:
            chunk = self.sock.recv(length - len(chunks))
            if not chunk:
                raise ConnectionError("Socket closed while reading frame")
            chunks += chunk
        return bytes(chunks)

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None


@dataclass
class HMIChamber:
    host: str = "192.168.1.66"
    scrno: int = 7171
    port: int = 80
    path: str = "/"
    delay_s: float = 0.2
    request_screen_on_connect: bool = True

    def __post_init__(self) -> None:
        self.ws = MinimalWebSocket(self.host, self.port, self.path)

    def __enter__(self) -> "HMIChamber":
        self.ws.connect()
        if self.request_screen_on_connect:
            self.request_screen()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self.ws.close()

    def send_event(self, part_name: str, event_type: int, value: str = "", scrno: int | None = None) -> None:
        self.ws.emit_event(
            "sendevent",
            [
                {
                    "ScrNo": scrno or self.scrno,
                    "PartName": part_name,
                    "EventType": event_type,
                    "EventBuffer": value,
                }
            ],
        )
        time.sleep(self.delay_s)

    def request_screen(self, scrno: int | None = None) -> None:
        self.send_event("", EVENT_SCRINIT, "", scrno=scrno)

    def change_screen(self, new_screen: int, old_screen: int = -1) -> None:
        self.ws.emit_event(
            "changescreen",
            [
                {
                    "NewScreenId": new_screen,
                    "OldScreenId": old_screen,
                    "SocketId": self.ws.session_id or "",
                    "EventType": EVENT_SCRINIT,
                }
            ],
        )
        time.sleep(self.delay_s)

    def click(self, part_name: str, scrno: int | None = None) -> None:
        self.send_event(part_name, EVENT_CLICKDOWN, "", scrno=scrno)
        self.send_event(part_name, EVENT_CLICKUP, "", scrno=scrno)
        time.sleep(self.delay_s)

    def click_xy(self, x: int | float, y: int | float, scrno: int | None = None) -> None:
        pos = f"{int(x)},{int(y)}"
        self.send_event("", EVENT_CLICKDOWN, pos, scrno=scrno)
        self.send_event("", EVENT_CLICKUP, pos, scrno=scrno)
        time.sleep(self.delay_s)

    def write_value(self, part_name: str, value: float | int | str, scrno: int | None = None) -> None:
        self.send_event(part_name, EVENT_DATATRANS, str(value), scrno=scrno)

    def run_steps(self, steps: Iterable["ChamberStep"], temp_part: str, hum_part: str | None = None) -> None:
        for step in steps:
            self.write_value(temp_part, step.temperature_c)
            if hum_part is not None and step.humidity_pct is not None:
                self.write_value(hum_part, step.humidity_pct)
            time.sleep(step.hold_s)

    def read_parts(self, scrno: int | None = None, timeout_s: float | None = None) -> list[HmiPart]:
        if scrno is not None:
            self.request_screen(scrno=scrno)
        deadline = time.time() + (self.ws.timeout if timeout_s is None else timeout_s)
        while time.time() < deadline:
            remaining = max(0.05, deadline - time.time())
            frame = self.ws.recv_frame(timeout=min(self.ws.timeout, remaining))
            if frame is None:
                continue
            opcode, payload = frame
            if opcode in (1, 2):
                parts = parse_hmi_parts(payload)
                if parts:
                    return parts
        return []

    def read_part_map(self, scrno: int | None = None, timeout_s: float | None = None) -> dict[str, HmiPart]:
        return {part.name: part for part in self.read_parts(scrno=scrno, timeout_s=timeout_s)}


class Chamber:
    """High-level B-T-107C control API.

    Method names are provided in both Python style and the requested camelCase
    style, so chamber.setTemperature(35) works.
    """

    def __init__(
        self,
        host: str = "192.168.1.66",
        config: ChamberControlConfig | None = None,
        *,
        port: int = 80,
        timeout: float = 5.0,
        delay_s: float = 0.2,
    ):
        self.config = config or ChamberControlConfig.bt107c_default()
        self._part_cache: dict[str, HmiPart] = {}
        self._part_index: dict[tuple[int, int], str] = {}
        self.hmi = HMIChamber(
            host=host,
            scrno=self.config.monitor_screen,
            port=port,
            delay_s=delay_s,
            request_screen_on_connect=False,
        )
        self.hmi.ws.timeout = timeout

    def __enter__(self) -> "Chamber":
        self.hmi.ws.connect()
        self._refresh_parts(timeout_s=self.hmi.ws.timeout)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self.hmi.close()

    def set_temperature(self, value_c: float) -> None:
        self._ensure_control_screen()
        part_name = self._setpoint_part()
        try:
            self._write_numeric(part_name, value_c)
        except ChamberCommandError:
            self._reset_connection()
            self._ensure_control_screen()
            part_name = self._setpoint_part()
            self._write_numeric(part_name, value_c)

    def _reset_connection(self) -> None:
        self.hmi.close()
        self._part_cache.clear()
        self._part_index.clear()
        time.sleep(0.5)
        self.hmi.ws.connect()
        self._refresh_parts(timeout_s=self.hmi.ws.timeout)

    def get_temperature_setpoint(self) -> float:
        self._ensure_control_screen()
        return self._read_float(self._setpoint_part())

    def get_temperature(self) -> float:
        self._ensure_control_screen()
        return self._read_float(self._readback_part())

    def set_humidity(self, value_pct: float) -> None:
        self.hmi.write_value(
            self._require("humidity_setpoint_part"),
            value_pct,
            scrno=self.config.monitor_screen,
        )

    def get_humidity(self) -> float:
        return self._read_float(self._require("humidity_readback_part"))

    def start(self) -> None:
        if self.is_running():
            return
        self._ensure_control_screen()
        part = self._require("start_part")
        self._click_part(part)
        self._click_popup_button(63, self.config.start_confirm_texts, timeout_s=10.0)
        if not self._wait_running(True, timeout_s=20.0):
            raise ChamberCommandError("Start command was sent, but the chamber did not enter running state")

    def stop(self) -> None:
        if not self.is_running():
            return
        self._ensure_control_screen()
        part = self._require("stop_part")
        self._click_part(part)
        self._click_popup_button(64, self.config.stop_confirm_texts, timeout_s=10.0)
        if not self._wait_running(False, timeout_s=20.0):
            raise ChamberCommandError("Stop command was sent, but the chamber still appears to be running")

    def is_running(self) -> bool:
        self._consume_frames(timeout_s=1.0)
        if self.config.running_status_title_part not in self._part_cache and self.config.status_title_part not in self._part_cache:
            self._refresh_parts(timeout_s=1.0)
        return self._is_running_from_cache()

    def read_status(self) -> dict[str, str]:
        self._ensure_monitor_screen()
        parts = self._refresh_parts(timeout_s=0.8)
        return {name: part.text for name, part in parts.items() if part.text}

    def discover_parts(self) -> list[HmiPart]:
        unique: dict[tuple[int, str], HmiPart] = {}
        for part in self._refresh_parts(timeout_s=self.hmi.ws.timeout).values():
            unique[(part.screen, part.name)] = part
        return list(unique.values())

    def _read_float(self, part_name: str) -> float:
        text = self._part_text(part_name)
        return float(text)

    def _part_text(self, part_name: str | None) -> str:
        if not part_name:
            return ""
        cached = self._part_cache.get(part_name)
        if cached is not None:
            return cached.text
        parts = self._refresh_parts(timeout_s=0.8)
        if part_name not in parts:
            raise ChamberConfigError(f"Configured HMI part {part_name!r} was not found")
        return parts[part_name].text

    def _refresh_parts(self, timeout_s: float = 0.8, scrno: int | None = -1) -> dict[str, HmiPart]:
        for part in self.hmi.read_parts(scrno=scrno, timeout_s=timeout_s):
            self._cache_part(part)
        return dict(self._part_cache)

    def _cache_part(self, part: HmiPart) -> None:
        if part.screen in (self.config.monitor_screen, self.config.running_screen):
            other_screen = self.config.running_screen if part.screen == self.config.monitor_screen else self.config.monitor_screen
            for key, cached in list(self._part_cache.items()):
                if cached.screen == other_screen:
                    self._part_cache.pop(key, None)
        self._part_cache[part.name] = part
        compact_name = self._compact_part_name(part)
        if compact_name:
            self._part_cache[compact_name] = part
        if part.index is not None:
            self._part_index[(part.screen, part.index)] = part.name

    def _compact_part_name(self, part: HmiPart) -> str | None:
        match = re.match(r"^([A-Za-z]+)_(\d+)(?:_\d+)?$", part.name)
        if not match:
            return None
        return f"{part.screen}_{match.group(1)}_{match.group(2)}"

    def _ensure_control_screen(self) -> None:
        self._consume_frames(timeout_s=1.0)
        if self.config.temperature_readback_part in self._part_cache:
            return
        if self.config.running_temperature_readback_part in self._part_cache:
            return

        parts = self._refresh_parts(timeout_s=1.0)
        menu_part = parts.get(self.config.monitor_menu_part)
        if menu_part is not None:
            x = ((menu_part.left or 0) + (menu_part.right or 0)) / 2
            y = ((menu_part.top or 0) + (menu_part.bottom or 0)) / 2
            self.hmi.click_xy(x, y, scrno=self.config.menu_screen)
            self._consume_frames(timeout_s=2.0)
            self._refresh_parts(timeout_s=1.0)
        if self.config.temperature_readback_part in self._part_cache:
            return
        if self.config.running_temperature_readback_part in self._part_cache:
            return

        self._refresh_parts(timeout_s=1.5, scrno=self.config.monitor_screen)
        if self.config.temperature_readback_part in self._part_cache:
            return
        if self.config.running_temperature_readback_part in self._part_cache:
            return
        if self.config.monitor_menu_part in self._part_cache:
            self.hmi.click(self.config.monitor_menu_part, scrno=self.config.menu_screen)
            self._wait_for_part(self.config.temperature_readback_part, timeout_s=5.0)
            return
        visible_text = " ".join(
            part.text for part in self._part_cache.values() if part.text and not part.hidden
        )
        if "请输入密码" in visible_text or "请进入系统" in visible_text:
            raise ChamberConfigError(
                "The HMI is currently on the password/login screen. "
                "Unlock the chamber HMI first, then run this script again."
            )
        screens = sorted({part.screen for part in self._part_cache.values()})
        raise ChamberConfigError(f"Could not navigate to the monitor screen; visible screens: {screens}")

    def _ensure_monitor_screen(self) -> None:
        self._ensure_control_screen()

    def _wait_for_part(self, part_name: str, timeout_s: float) -> HmiPart:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            self._consume_frames(timeout_s=0.5)
            if part_name in self._part_cache:
                return self._part_cache[part_name]
        raise ChamberConfigError(f"Timed out waiting for HMI part {part_name!r}")

    def _consume_frames(self, timeout_s: float = 0.5) -> None:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            frame = self.hmi.ws.recv_frame(timeout=max(0.05, min(0.2, deadline - time.time())))
            if not frame:
                continue
            _, payload = frame
            socketio = _parse_socketio_event(payload)
            if socketio is not None and socketio[0] == "hmitoweb" and socketio[1]:
                try:
                    event = json.loads(socketio[1][0])
                except (TypeError, ValueError):
                    event = {}
                pop_screen = event.get("ScrNo")
                if pop_screen is not None:
                    self.hmi.request_screen(int(pop_screen))
            for part in parse_hmi_parts(payload):
                self._cache_part(part)
            for update in parse_hmi_basic_updates(payload):
                index = update.get("index")
                if index is None:
                    continue
                screen = update.get("screen")
                if screen is None:
                    screen = self.config.numeric_keypad_screen if self.config.numeric_display_part in self._part_cache else self.config.monitor_screen
                name = update.get("name") or self._part_index.get((screen, index))
                if not name:
                    continue
                old = self._part_cache.get(name)
                self._cache_part(
                    HmiPart(
                        screen=screen,
                        name=name,
                        type=update.get("type") or (old.type if old else ""),
                        index=index,
                        text=update.get("text") if update.get("text") != "" else (old.text if old else ""),
                        left=old.left if old else None,
                        right=old.right if old else None,
                        top=old.top if old else None,
                        bottom=old.bottom if old else None,
                        hidden=update.get("hidden") if update.get("hidden") is not None else (old.hidden if old else False),
                        enabled=old.enabled if old else None,
                    )
                )

    def _write_numeric(self, part_name: str, value: float | int | str) -> None:
        keys = self.config.numeric_keys or {}
        value_text = self._format_number(value)
        target = self._part_cache.get(part_name)
        target_screen = target.screen if target is not None else self.config.monitor_screen
        if target is not None and target.left is not None and target.right is not None and target.top is not None and target.bottom is not None:
            self._clear_screen_cache(self.config.numeric_keypad_screen)
            self.hmi.click_xy((target.left + target.right) / 2, (target.top + target.bottom) / 2, scrno=target_screen)
        else:
            self._clear_screen_cache(self.config.numeric_keypad_screen)
            self.hmi.click(part_name, scrno=target_screen)
        self._wait_for_part(self.config.numeric_display_part, timeout_s=5.0)

        backspace = self._require_key("backspace")
        for _ in range(10):
            current = self._part_cache.get(self.config.numeric_display_part)
            if current is not None and current.text == "":
                break
            self._click_key(backspace)
            self._wait_for_numeric_update(timeout_s=0.8)

        input_text = value_text
        if input_text.startswith("-"):
            self._click_key(self._require_key("-"))
            self._consume_frames(timeout_s=0.5)
            input_text = input_text[1:]

        for char in input_text:
            self._click_key(self._require_key(char))
            self._wait_for_numeric_update(timeout_s=0.8)

        entered = self._part_cache.get(self.config.numeric_display_part)
        if entered and entered.text and float(entered.text) != float(value_text):
            raise ChamberConfigError(f"Numeric keypad entry failed: expected {value_text}, saw {entered.text}")

        self._click_key(self._require_key("enter"))
        self._clear_screen_cache(self.config.numeric_keypad_screen)
        time.sleep(0.5)
        if not self._wait_numeric_value(part_name, value_text, timeout_s=15.0):
            raise ChamberCommandError(f"Temperature setpoint did not update to {value_text}")
        self._clear_screen_cache(self.config.numeric_keypad_screen)

    def _clear_screen_cache(self, screen: int) -> None:
        for key, part in list(self._part_cache.items()):
            if part.screen == screen:
                self._part_cache.pop(key, None)

    def _wait_numeric_value(self, part_name: str, value_text: str, timeout_s: float) -> bool:
        target_screen = self._screen_from_part_name(part_name)
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            self._consume_frames(timeout_s=0.5)
            self._refresh_parts(timeout_s=0.8, scrno=target_screen)
            current = self._part_cache.get(part_name)
            if current is None:
                continue
            try:
                if float(current.text) == float(value_text):
                    return True
            except ValueError:
                if current.text == value_text:
                    return True
        return False

    def _screen_from_part_name(self, part_name: str) -> int | None:
        match = re.match(r"^(\d+)_", part_name)
        return int(match.group(1)) if match else None

    def _wait_for_numeric_update(self, timeout_s: float) -> str:
        before = self._part_cache.get(self.config.numeric_display_part)
        before_text = before.text if before else None
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            self._consume_frames(timeout_s=0.2)
            current = self._part_cache.get(self.config.numeric_display_part)
            if current is not None and current.text != before_text:
                return current.text
        current = self._part_cache.get(self.config.numeric_display_part)
        return current.text if current else ""

    def _require_key(self, key: str) -> str:
        keys = self.config.numeric_keys or {}
        if key not in keys:
            raise ChamberConfigError(f"Numeric keypad key {key!r} is not configured")
        return keys[key]

    def _click_key(self, part_name: str) -> None:
        part = self._part_cache.get(part_name)
        if part is not None and part.left is not None and part.right is not None and part.top is not None and part.bottom is not None:
            self.hmi.click_xy((part.left + part.right) / 2, (part.top + part.bottom) / 2, scrno=part.screen)
        else:
            self.hmi.click(part_name, scrno=self.config.numeric_keypad_screen)

    def _format_number(self, value: float | int | str) -> str:
        if isinstance(value, str):
            return value
        if float(value).is_integer():
            return str(int(value))
        return str(value)

    def _setpoint_part(self) -> str:
        if self._is_running_from_cache() and self.config.running_temperature_setpoint_part in self._part_cache:
            return self.config.running_temperature_setpoint_part
        return self._require("temperature_setpoint_part")

    def _readback_part(self) -> str:
        if self._is_running_from_cache() and self.config.running_temperature_readback_part in self._part_cache:
            return self.config.running_temperature_readback_part
        return self._require("temperature_readback_part")

    def _is_running_from_cache(self) -> bool:
        status_text = self._cached_text(self.config.running_status_title_part)
        stop_text = self._cached_text(self.config.stop_part)
        stopped_text = self._cached_text(self.config.status_title_part)
        start_text = self._cached_text(self.config.start_part)
        if "运行" in status_text or "停止" in stop_text:
            return True
        if "停止" in stopped_text or "启动" in start_text:
            return False
        if "\u8fd0\u884c" in status_text or "\u505c\u6b62" in stop_text:
            return True
        if "\u505c\u6b62" in stopped_text or "\u542f\u52a8" in start_text:
            return False
        return self.config.running_temperature_readback_part in self._part_cache

    def _cached_text(self, part_name: str | None) -> str:
        if not part_name:
            return ""
        part = self._part_cache.get(part_name)
        return part.text if part is not None else ""

    def _click_confirmation(self, texts: tuple[str, ...], timeout_s: float) -> None:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            self._consume_frames(timeout_s=0.5)
            part = self._find_part_by_text(texts)
            if part is not None:
                self._click_part(part.name)
                self._consume_frames(timeout_s=1.0)
                return
        labels = ", ".join(repr(text) for text in texts)
        raise ChamberCommandError(f"Confirmation button {labels} was not found")

    def _click_popup_button(self, screen: int, texts: tuple[str, ...], timeout_s: float) -> None:
        for key, part in list(self._part_cache.items()):
            if part.screen == screen:
                self._part_cache.pop(key, None)
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            self._consume_frames(timeout_s=0.5)
            for part in list(self._part_cache.values()):
                if part.screen != screen or part.hidden or not part.text:
                    continue
                if any(text in part.text for text in texts):
                    self._click_part(part.name)
                    self._consume_frames(timeout_s=1.0)
                    return
        labels = ", ".join(repr(text) for text in texts)
        raise ChamberCommandError(f"Confirmation button {labels} on screen {screen} was not found")

    def _find_part_by_text(self, texts: tuple[str, ...]) -> HmiPart | None:
        candidates = []
        for part in self._part_cache.values():
            if part.hidden or not part.text:
                continue
            if any(text in part.text for text in texts):
                candidates.append(part)
        if not candidates:
            return None
        candidates.sort(key=lambda part: (part.screen == self.config.monitor_screen, -(part.left or 0)))
        return candidates[0]

    def _wait_running(self, expected: bool, timeout_s: float) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            self._consume_frames(timeout_s=0.8)
            if self._is_running_from_cache() is expected:
                return True
        return False

    def _require(self, field_name: str) -> str:
        value = getattr(self.config, field_name)
        if not value:
            raise ChamberConfigError(
                f"{field_name} is not configured for this chamber screen. "
                "Run discover_parts() or inspect the HMI page, then set it in ChamberControlConfig."
            )
        return value

    def _click_part(self, part_name: str) -> None:
        part = self._part_cache.get(part_name)
        if part is None:
            parts = self._refresh_parts(timeout_s=0.8)
            part = parts.get(part_name)
        if part is None:
            raise ChamberConfigError(f"Configured HMI part {part_name!r} was not found")
        if part.left is not None and part.right is not None and part.top is not None and part.bottom is not None:
            self.hmi.click_xy((part.left + part.right) / 2, (part.top + part.bottom) / 2, scrno=part.screen)
        else:
            self.hmi.click(part.name, scrno=part.screen)

    setTemperature = set_temperature
    getTemperatureSetpoint = get_temperature_setpoint
    getTemperature = get_temperature
    setHumidity = set_humidity
    getHumidity = get_humidity
    readStatus = read_status
    discoverParts = discover_parts
    isRunning = is_running


def _normalize_endpoint(host: str | None, tcp_port: int) -> tuple[str, int]:
    endpoint = (host or DEFAULT_WT2040_HOST).strip()
    if endpoint.count(":") == 1:
        host_part, port_part = endpoint.rsplit(":", 1)
        if host_part and port_part.isdigit():
            return host_part, int(port_part)
    return endpoint or DEFAULT_WT2040_HOST, tcp_port


class WT2040(ChamberBase):
    DEFAULT_HOST = DEFAULT_WT2040_HOST
    DEFAULT_PORT = DEFAULT_WT2040_PORT

    def __init__(
        self,
        host: str = DEFAULT_WT2040_HOST,
        *,
        tcp_port: int = DEFAULT_WT2040_PORT,
        timeout: float = 5.0,
        config: ChamberControlConfig | None = None,
        delay_s: float = 0.2,
    ):
        self.host, self.tcp_port = _normalize_endpoint(host, tcp_port)
        self.timeout = timeout
        self._last_set_temp: float | None = None
        self._driver = Chamber(
            self.host,
            config=config,
            port=self.tcp_port,
            timeout=timeout,
            delay_s=delay_s,
        )
        self._connected = False
        self.connect()

    def connect(self, *args, **kwargs):
        if self.is_connected():
            return True
        try:
            self._driver.hmi.ws.connect()
            self._driver._refresh_parts(timeout_s=self.timeout)
            self._connected = True
            logger.info("WT2040 connected: %s:%d", self.host, self.tcp_port)
            return True
        except Exception as e:
            self._connected = False
            logger.error("WT2040 connect failed: %s", e, exc_info=True)
            raise

    def disconnect(self):
        self.close()

    def close(self) -> None:
        self._driver.close()
        self._connected = False

    def is_connected(self) -> bool:
        return bool(self._connected and self._driver.hmi.ws.sock is not None)

    def identify(self) -> str:
        return f"WT2040 Temperature Chamber ({self.host}:{self.tcp_port})"

    def set_temperature(self, temp_celsius: float):
        self._driver.set_temperature(float(temp_celsius))
        self._last_set_temp = float(temp_celsius)

    def get_current_temp(self):
        value = self._cached_float(self._driver._readback_part())
        if value is not None:
            return value
        return self._driver.get_temperature()

    def get_set_temp(self):
        value = self._cached_float(self._driver._setpoint_part())
        if value is not None:
            return value
        if self._last_set_temp is not None:
            return self._last_set_temp
        return self._driver.get_temperature_setpoint()

    def start(self):
        self._driver.start()

    def stop(self):
        self._driver.stop()

    def is_running(self) -> bool:
        running = self._driver.is_running()
        self._last_known_running_state = running
        self._last_known_running_state_verified = True
        return running

    def set_humidity(self, value_pct: float) -> None:
        self._driver.set_humidity(value_pct)

    def get_humidity(self) -> float:
        return self._driver.get_humidity()

    def read_humidity_pv(self):
        return self.get_humidity()

    def read_temperature_sv(self):
        return self.get_set_temp()

    def _cached_float(self, part_name: str) -> float | None:
        self._refresh_cache_quick()
        part = self._driver._part_cache.get(part_name)
        if part is None or part.text == "":
            return None
        self._last_known_running_state = self._driver._is_running_from_cache()
        try:
            return float(part.text)
        except ValueError:
            logger.debug("WT2040 cached value is not numeric: %s=%s", part_name, part.text)
            return None

    def _refresh_cache_quick(self) -> None:
        if not self.is_connected():
            return
        try:
            self._driver._consume_frames(timeout_s=0.05)
        except Exception:
            logger.debug("WT2040 quick cache refresh failed", exc_info=True)

    setTemperature = set_temperature
    getTemperatureSetpoint = get_set_temp
    getTemperature = get_current_temp
    setHumidity = set_humidity
    getHumidity = get_humidity
    isRunning = is_running


@dataclass(frozen=True)
class ChamberStep:
    temperature_c: float
    hold_s: float
    humidity_pct: float | None = None


def main() -> None:
    import argparse
    import time

    parser = argparse.ArgumentParser(description="Run a WT2040 chamber control verification sequence.")
    parser.add_argument("--host", default="192.168.1.66", help="Chamber HMI IP address")
    parser.add_argument("--port", type=int, default=80, help="Chamber HMI TCP port")
    parser.add_argument("--timeout", type=float, default=5.0, help="Socket timeout in seconds")
    args = parser.parse_args()

    def log_temperatures(chamber: Chamber, label: str) -> None:
        setpoint = chamber.getTemperatureSetpoint()
        actual = chamber.getTemperature()
        running = chamber.isRunning()
        logger.info("%s: setpoint=%.1f C, actual=%.1f C, running=%s", label, setpoint, actual, running)

    with Chamber(args.host, port=args.port, timeout=args.timeout) as chamber:
        logger.info("1. Set chamber to 35 C")
        chamber.setTemperature(35)

        logger.info("2. Wait 1s")
        time.sleep(1)

        logger.info("3. Read setpoint and actual temperature")
        log_temperatures(chamber, "After setting 35 C")

        logger.info("4. Set chamber to 25 C")
        chamber.setTemperature(25)

        logger.info("5. Start chamber")
        chamber.start()

        logger.info("6. Wait 1s")
        time.sleep(1)

        logger.info("7. Read setpoint and actual temperature")
        log_temperatures(chamber, "After start")

        logger.info("8. Stop chamber")
        chamber.stop()

        logger.info("9. Read setpoint and actual temperature")
        log_temperatures(chamber, "After stop")


if __name__ == "__main__":
    main()

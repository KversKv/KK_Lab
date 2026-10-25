# -*- coding: utf-8 -*-
"""pyserial 统一入口：端口枚举 / 参数文本映射 / 打开连接。

UI 层禁止直接 import serial；串口常量与 serial.Serial 构造集中在 core 本模块。
无 Qt 依赖，pytest 可直测。
"""

from collections import namedtuple

import serial
import serial.tools.list_ports

# 轻量端口信息（屏蔽 pyserial ListPortInfo 类型向 UI 泄漏；vid/pid 供 USB 设备过滤）
SerialPortInfo = namedtuple(
    "SerialPortInfo", ["device", "description", "hwid", "vid", "pid"],
    defaults=[None, None],
)

DEFAULT_STOPBITS = serial.STOPBITS_ONE
DEFAULT_PARITY = serial.PARITY_NONE

# (显示文本, pyserial 常量)，供 UI 下拉 data 与映射共用
STOPBITS_CHOICES = [
    ("1", serial.STOPBITS_ONE),
    ("1.5", serial.STOPBITS_ONE_POINT_FIVE),
    ("2", serial.STOPBITS_TWO),
]
PARITY_CHOICES = [
    ("None", serial.PARITY_NONE),
    ("Even", serial.PARITY_EVEN),
    ("Odd", serial.PARITY_ODD),
    ("Mark", serial.PARITY_MARK),
    ("Space", serial.PARITY_SPACE),
]

_STOPBITS_BY_TEXT = dict(STOPBITS_CHOICES)
_PARITY_BY_TEXT = dict(PARITY_CHOICES)
_STOPBITS_TO_TEXT = {v: k for k, v in STOPBITS_CHOICES}
_PARITY_TO_TEXT = {v: k for k, v in PARITY_CHOICES}


def stopbits_from_text(text, default=DEFAULT_STOPBITS):
    """停止位文本（"1"/"1.5"/"2"）→ pyserial 常量；非字符串原样透传。"""
    if not isinstance(text, str):
        return default if text is None else text
    return _STOPBITS_BY_TEXT.get(text.strip(), default)


def parity_from_text(text, default=DEFAULT_PARITY):
    """校验文本（"None"/"Even"/...）→ pyserial 常量；非字符串原样透传。"""
    if not isinstance(text, str):
        return default if text is None else text
    return _PARITY_BY_TEXT.get(text.strip(), default)


def stopbits_to_text(value, default="1"):
    return _STOPBITS_TO_TEXT.get(value, default)


def parity_to_text(value, default="None"):
    return _PARITY_TO_TEXT.get(value, default)


def list_serial_ports():
    """枚举系统串口，返回 [SerialPortInfo(device, description, hwid, vid, pid)]。"""
    return [
        SerialPortInfo(p.device, p.description, p.hwid,
                       getattr(p, "vid", None), getattr(p, "pid", None))
        for p in serial.tools.list_ports.comports()
    ]


def open_serial(port, baudrate, *, bytesize=8, stopbits=None, parity=None,
                xonxoff=False, rtscts=False, timeout=0.1):
    """打开串口（serial.Serial 唯一构造点）。

    stopbits/parity 接受文本（"1"/"None"）或 pyserial 常量，None 用默认值。
    """
    return serial.Serial(
        port=port,
        baudrate=baudrate,
        bytesize=bytesize,
        stopbits=stopbits_from_text(stopbits),
        parity=parity_from_text(parity),
        xonxoff=xonxoff,
        rtscts=rtscts,
        timeout=timeout,
    )

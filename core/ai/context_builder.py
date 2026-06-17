"""ContextBuilder：聚合各 Provider 输出为只读、受裁剪、可脱敏的上下文快照。

职责（AI_Assist.md §11）：
  - 汇总 LogContextProvider / SerialContextProvider 的文本；
  - 日志范围选择（行数上限保护）；
  - 等级过滤（仅保留 >= 指定等级的行）；
  - 脱敏（序列号 / IP / 路径 / token / key 正则掩码）；
  - 超限摘要 + 截断并提示。

本模块纯逻辑，禁 import Qt。脱敏复用 prompt_manager.mask_sensitive 并扩展。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from core.ai.prompt_manager import mask_sensitive
from core.ai.providers.log_provider import LogContextProvider
from core.ai.providers.serial_provider import SerialContextProvider

_LEVEL_ORDER = {
    "DEBUG": 10,
    "INFO": 20,
    "STEP": 20,
    "SYSTEM": 20,
    "WARN": 30,
    "WARNING": 30,
    "ERROR": 40,
    "FAIL": 40,
    "STOP": 40,
    "CRITICAL": 50,
}

_LEVEL_RE = re.compile(r"\[(DEBUG|INFO|STEP|SYSTEM|WARN|WARNING|ERROR|FAIL|STOP|CRITICAL)\]")

_EXTRA_MASK_PATTERNS = [
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "[IP]"),
    (re.compile(r"[A-Za-z]:\\[^\s\"']+"), "[PATH]"),
    (re.compile(r"\bSN[:=]?\s*[A-Za-z0-9\-]{6,}\b", re.IGNORECASE), "[SN]"),
]

_MAX_LINES_HARD_CAP = 1000


@dataclass
class ContextOptions:
    max_app_lines: int = 300
    max_exec_lines: int = 200
    max_rx_lines: int = 200
    min_level: str = "DEBUG"
    enable_masking: bool = True
    char_budget: int = 16000


def _line_level(line: str) -> int:
    m = _LEVEL_RE.search(line)
    if not m:
        return _LEVEL_ORDER["INFO"]
    return _LEVEL_ORDER.get(m.group(1).upper(), _LEVEL_ORDER["INFO"])


def filter_by_level(lines: list[str], min_level: str) -> list[str]:
    threshold = _LEVEL_ORDER.get(min_level.upper(), _LEVEL_ORDER["DEBUG"])
    if threshold <= _LEVEL_ORDER["DEBUG"]:
        return lines
    return [ln for ln in lines if _line_level(ln) >= threshold]


def mask_extra(text: str) -> str:
    if not text:
        return text
    masked = text
    for pattern, repl in _EXTRA_MASK_PATTERNS:
        masked = pattern.sub(repl, masked)
    return masked


def _summarize_truncate(text: str, char_budget: int) -> tuple[str, bool]:
    if char_budget <= 0 or len(text) <= char_budget:
        return text, False
    head = text[: char_budget // 2]
    tail = text[-char_budget // 2 :]
    return head + "\n…（中间已省略，超出长度上限）…\n" + tail, True


class ContextBuilder:
    def __init__(
        self,
        log_provider: LogContextProvider | None = None,
        serial_provider: SerialContextProvider | None = None,
    ):
        self._log = log_provider
        self._serial = serial_provider

    def build(self, options: ContextOptions) -> str:
        sections: list[str] = []
        truncated = False

        if self._serial is not None:
            serial_text = self._build_serial(options)
            if serial_text:
                sections.append(serial_text)

        if self._log is not None:
            log_text = self._build_logs(options)
            if log_text:
                sections.append(log_text)

        body = "\n\n".join(sections)
        if options.enable_masking:
            body = mask_extra(mask_sensitive(body))
        body, truncated = _summarize_truncate(body, options.char_budget)
        if truncated:
            body = "[注意：上下文已超长，已自动摘要并截断]\n" + body
        return body

    def _build_serial(self, options: ContextOptions) -> str:
        status = self._serial.status()
        if not status:
            return ""
        port = status.get("port") or "未配置"
        baud = status.get("baudrate") or "-"
        connected = "已连接" if status.get("connected") else "未连接"
        head = (
            f"[活动串口] 端口={port} 波特率={baud} 状态={connected} "
            f"RX={status.get('rx_bytes', 0)}B TX={status.get('tx_bytes', 0)}B"
        )
        rx_lines = self._serial.recent_rx(min(options.max_rx_lines, _MAX_LINES_HARD_CAP))
        rx_lines = filter_by_level(rx_lines, options.min_level)
        if rx_lines:
            return head + "\n[最近串口接收 %d 行]\n%s" % (
                len(rx_lines),
                "\n".join(rx_lines),
            )
        return head

    def _build_logs(self, options: ContextOptions) -> str:
        parts: list[str] = []
        app = self._log.recent_app_logs(min(options.max_app_lines, _MAX_LINES_HARD_CAP))
        app = filter_by_level(app, options.min_level)
        if app:
            parts.append("[最近软件运行日志 %d 行]\n%s" % (len(app), "\n".join(app)))
        exec_logs = self._log.recent_execution_logs(
            min(options.max_exec_lines, _MAX_LINES_HARD_CAP)
        )
        exec_logs = filter_by_level(exec_logs, options.min_level)
        if exec_logs:
            parts.append(
                "[当前页执行日志 %d 行]\n%s" % (len(exec_logs), "\n".join(exec_logs))
            )
        return "\n\n".join(parts)

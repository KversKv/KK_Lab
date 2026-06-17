"""PolicyStore：白名单（带护栏）读写与求值（AI_AssistNewFeature_V1 §2，F2.1/F2.2）。

落地"白名单 = 必带边界条件"的折衷安全策略，区别于普通 IDE Agent 的无脑放行：
  - auto_approve : 常驻白名单条目（动作名 + 可选护栏条件 when），命中且护栏通过则免确认；
  - session_grants: 会话级白名单（本次会话内存生效，不落盘），用户在确认框勾选写入；
  - blocked      : 黑名单动作名，永远拒绝（优先级最高）。

护栏条件 when 为通用求值器，支持对动作参数做边界判定（详见 _match_when）：
  {"voltage_max": 5.0, "current_max": 1.0}  -> arguments["voltage"] <= 5.0 且 ["current"] <= 1.0
  {"channel_in": [1, 2]}                     -> arguments["channel"] ∈ {1, 2}
  {"enabled_eq": false}                      -> arguments["enabled"] == False

落盘路径：get_user_data_dir("ai")/policy.json（开发态 user_data/ai/，打包后 %APPDATA%/KK_Lab/ai/）。
本模块纯逻辑，禁 import Qt。
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from typing import Any

from ui.resource_path import get_user_data_dir
from log_config import get_logger

logger = get_logger(__name__)

_POLICY_FILENAME = "policy.json"
_POLICY_VERSION = 1

# 护栏后缀 -> 比较语义
_SUFFIX_MAX = "_max"
_SUFFIX_MIN = "_min"
_SUFFIX_IN = "_in"
_SUFFIX_EQ = "_eq"


def _policy_path() -> str:
    return os.path.join(get_user_data_dir("ai"), _POLICY_FILENAME)


@dataclass
class PolicyResult:
    """白名单匹配结果。"""

    matched: bool
    auto_approve: bool
    blocked: bool = False
    reason: str = ""


def _to_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _match_when(when: dict[str, Any], arguments: dict[str, Any]) -> bool:
    """通用护栏求值器：when 全部条件满足才返回 True。

    支持后缀语义（key 去掉后缀即参数名）：
      *_max : 参数值 <= 条件值（数值）；
      *_min : 参数值 >= 条件值（数值）；
      *_in  : 参数值 ∈ 条件列表；
      *_eq  : 参数值 == 条件值；
      其它  : 直接相等比较（参数名 == 条件值）。

    参数缺失即视为不满足（护栏不放行未知边界），保证"必带边界条件"的安全语义。
    """
    if not when:
        return True
    if not isinstance(when, dict):
        return False

    for key, expected in when.items():
        if key.endswith(_SUFFIX_MAX):
            param = key[: -len(_SUFFIX_MAX)]
            actual = _to_number(arguments.get(param))
            bound = _to_number(expected)
            if actual is None or bound is None or actual > bound:
                return False
        elif key.endswith(_SUFFIX_MIN):
            param = key[: -len(_SUFFIX_MIN)]
            actual = _to_number(arguments.get(param))
            bound = _to_number(expected)
            if actual is None or bound is None or actual < bound:
                return False
        elif key.endswith(_SUFFIX_IN):
            param = key[: -len(_SUFFIX_IN)]
            if param not in arguments:
                return False
            choices = expected if isinstance(expected, (list, tuple, set)) else [expected]
            if arguments.get(param) not in choices:
                return False
        elif key.endswith(_SUFFIX_EQ):
            param = key[: -len(_SUFFIX_EQ)]
            if param not in arguments or arguments.get(param) != expected:
                return False
        else:
            if arguments.get(key) != expected:
                return False
    return True


@dataclass
class PolicyStore:
    """白名单存储（常驻 + 会话级），线程安全读写。

    auto_approve  : list[{"action": str, "when": dict}]（常驻，落盘 policy.json）；
    session_grants: list[{"action": str, "when": dict}]（会话级，仅内存）；
    blocked       : list[str]（黑名单动作名，落盘）。
    """

    auto_approve: list[dict[str, Any]] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    session_grants: list[dict[str, Any]] = field(default_factory=list)
    _path: str = field(default="", repr=False, compare=False)
    _lock: threading.Lock = field(
        default_factory=threading.Lock, repr=False, compare=False
    )

    @classmethod
    def load(cls, path: str | None = None) -> "PolicyStore":
        target = path or _policy_path()
        store = cls(_path=target)
        if not os.path.isfile(target):
            return store
        try:
            with open(target, "r", encoding="utf-8") as f:
                raw = json.load(f) or {}
        except (OSError, json.JSONDecodeError):
            logger.error("读取白名单策略失败: %s", target, exc_info=True)
            return store
        approve = raw.get("auto_approve")
        if isinstance(approve, list):
            store.auto_approve = [e for e in approve if isinstance(e, dict) and e.get("action")]
        blocked = raw.get("blocked")
        if isinstance(blocked, list):
            store.blocked = [str(a) for a in blocked if str(a).strip()]
        return store

    def save(self) -> bool:
        """把常驻白名单与黑名单写回 policy.json（不写会话级条目）。"""
        payload = {
            "version": _POLICY_VERSION,
            "auto_approve": list(self.auto_approve),
            "session_grants": [],
            "blocked": list(self.blocked),
        }
        target = self._path or _policy_path()
        try:
            with self._lock:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
            return True
        except OSError:
            logger.error("写入白名单策略失败: %s", target, exc_info=True)
            return False

    def is_blocked(self, name: str) -> bool:
        return name in self.blocked

    def evaluate(self, name: str, arguments: dict[str, Any] | None = None) -> PolicyResult:
        """对一个动作 + 参数求值白名单：黑名单 > 会话级 > 常驻。"""
        args = arguments or {}
        if self.is_blocked(name):
            return PolicyResult(
                matched=True,
                auto_approve=False,
                blocked=True,
                reason="动作在黑名单中，禁止执行。",
            )
        with self._lock:
            session = list(self.session_grants)
            resident = list(self.auto_approve)
        for entry in session:
            if entry.get("action") == name and _match_when(entry.get("when") or {}, args):
                return PolicyResult(
                    matched=True, auto_approve=True, reason="命中会话级白名单（护栏通过）。"
                )
        for entry in resident:
            if entry.get("action") == name and _match_when(entry.get("when") or {}, args):
                return PolicyResult(
                    matched=True, auto_approve=True, reason="命中常驻白名单（护栏通过）。"
                )
        return PolicyResult(matched=False, auto_approve=False)

    def grant_session(self, name: str, when: dict[str, Any] | None = None) -> None:
        """添加会话级白名单（仅内存，不落盘）。"""
        entry = {"action": name, "when": dict(when or {})}
        with self._lock:
            if entry not in self.session_grants:
                self.session_grants.append(entry)
        logger.debug("会话级白名单新增: %s when=%s", name, when or {})

    def grant_resident(self, name: str, when: dict[str, Any] | None = None) -> bool:
        """添加常驻白名单并落盘。"""
        entry = {"action": name, "when": dict(when or {})}
        with self._lock:
            if entry not in self.auto_approve:
                self.auto_approve.append(entry)
        return self.save()

    def clear_session_grants(self) -> None:
        """清空会话级白名单（如新会话开始时）。"""
        with self._lock:
            self.session_grants.clear()

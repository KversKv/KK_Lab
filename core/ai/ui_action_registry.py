"""UIActionSpec + UIActionRegistry（AIAssist_PageScopedControlPlan.md §5b）。

解决「页面上有按钮但没专用接口（如 N6705C 的 Auto Set / Zero / Calibrate / Auto Fit），
AI 偶尔要用」的普适性问题。采用「页面声明式登记具名 UI 动作 + 统一 ui_invoke 触发」，
而非盲扫 Widget 树 + 模拟 click 的 RPA 路径（脆弱、绕过确认/审计、跨线程点击有崩溃风险）。

设计原则（与现有架构一致，不破坏分层）：
  - core 不反向依赖 ui——本模块仅 dataclass + registry，禁 import Qt；
    handler 字段是 UI 注入的 Callable（鸭子类型，不持 Qt 类型依赖）；
  - 页面声明式登记——页面构建控件后一次性 register，handler 直接指向按钮原槽，
    零重复实现、行为与人点完全一致；
  - 白名单制——只有显式 register 的按钮可被 AI 触发；未登记的控件 AI 无任何途径操作；
  - 页面隔离——list_for_page / get 按 page_key 裁剪，禁止跨页派发；
  - 线程安全——register/unregister/list 可能跨页面构建线程与 AI 调度线程并发，
    用 RLock 守护内部 dict（lookup 在 AI 调度主线程，注册在 UI 主线程，仍加锁保险）。

执行链路（§5b.4）：
  AI: ui_invoke(action_id)
    → list_ui_actions handler 经 page_key_getter + registry.list_for_page 渲染可见集
    → ui_invoke handler 经 deps.ui_invoke_callback 委派枢纽：
       校验归属页(page_key 匹配) + enabled_when → PermissionChecker/确认(由 dispatcher)
       → 主线程 Slot 调 spec.handler()（按钮原槽）→ 写 AuditLog + 回灌 {ok,message}
    → 控件状态照常经原有信号/轮询投影刷新 + 执行日志追加 [AI] ...
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable

from log_config import get_logger

logger = get_logger(__name__)

# handler 签名：无参，返回 (ok, message)；复用按钮原 clicked.connect 的槽。
UIActionHandler = Callable[[], "tuple[bool, str]"]
# enabled_when：无参，返回当前是否可触发；不满足→明示不可用，AI 不盲点。
EnabledWhen = Callable[[], bool]


@dataclass
class UIActionSpec:
    """一个可被 AI 经 ui_invoke 触发的具名 UI 动作（声明式白名单条目）。

    Attributes:
        id: 全局唯一，建议 "<page>.<action>"，如 "power_analyser.auto_set"。
        label: 给模型/用户看的可读名，如 "Auto Set"。
        page_key: 归属页面（裁剪 + 防串台），与 _get_current_help_key 返回值对齐。
        handler: 复用按钮已绑定的槽（无参，返回 (ok, message)）；行为与人点完全一致。
        risk: low/medium/high；沿用 PermissionChecker 语义，供确认提示与审计展示。
        confirm: 是否需二次确认（信息性，ui_invoke 动作本身经 dispatcher 统一确认）。
        enabled_when: 不满足→明示不可用，AI 不盲点；None 视为恒可用。
        description: 可选，补充语义供模型判断何时用。
    """

    id: str
    label: str
    page_key: str
    handler: UIActionHandler
    risk: str = "medium"
    confirm: bool = True
    enabled_when: EnabledWhen | None = None
    description: str = ""

    def is_enabled(self) -> bool:
        """返回当前是否可触发（enabled_when 为 None 视为恒可用）。"""
        if self.enabled_when is None:
            return True
        try:
            return bool(self.enabled_when())
        except Exception:  # noqa: BLE001 - 判定异常视为不可用，杜绝盲点
            logger.error("UIAction enabled_when 判定异常: %s", self.id, exc_info=True)
            return False

    def to_view(self) -> dict[str, Any]:
        """渲染给模型的可读描述（list_ui_actions 返回项）。不含 handler 闭包。"""
        return {
            "id": self.id,
            "label": self.label,
            "page_key": self.page_key,
            "risk": self.risk,
            "confirm": self.confirm,
            "enabled": self.is_enabled(),
            "description": self.description,
        }


class UIActionRegistry:
    """UI 动作注册表：按 page_key 注册 / 查找 / 列举（线程安全，禁 Qt）。

    - register(spec)：登记一个 UIActionSpec（id 全局唯一，重复覆盖并告警）；
    - unregister_page(page_key)：清空某页全部登记（页面销毁时调用，防泄漏）；
    - get(page_key, action_id)：精确查找（含 page_key 隔离校验）；
    - list_for_page(page_key, only_enabled=True)：按页列举（默认仅返回 enabled）。
    """

    def __init__(self) -> None:
        self._specs: dict[str, UIActionSpec] = {}
        self._lock = threading.RLock()

    def register(self, spec: UIActionSpec) -> None:
        with self._lock:
            if spec.id in self._specs:
                logger.warning("UIAction 已存在，覆盖注册: %s", spec.id)
            self._specs[spec.id] = spec

    def register_many(self, specs) -> None:
        for spec in specs:
            self.register(spec)

    def unregister_page(self, page_key: str) -> None:
        """清空某页全部登记（页面销毁时调用）。"""
        with self._lock:
            doomed = [sid for sid, s in self._specs.items() if s.page_key == page_key]
            for sid in doomed:
                self._specs.pop(sid, None)

    def get(self, page_key: str, action_id: str) -> UIActionSpec | None:
        """按页 + id 精确查找（page_key 不匹配返回 None，禁止跨页派发）。"""
        with self._lock:
            spec = self._specs.get(action_id)
        if spec is None or spec.page_key != page_key:
            return None
        return spec

    def list_for_page(
        self, page_key: str, only_enabled: bool = True
    ) -> list[UIActionSpec]:
        """按页列举（默认仅返回 enabled，供 list_ui_actions 过滤不可用项）。"""
        with self._lock:
            specs = [s for s in self._specs.values() if s.page_key == page_key]
        if only_enabled:
            specs = [s for s in specs if s.is_enabled()]
        return specs

    def has_page(self, page_key: str) -> bool:
        with self._lock:
            return any(s.page_key == page_key for s in self._specs.values())

"""AIControllablePage 页面契约（AIAssist_PageScopedControlPlan.md §2）。

定义专项页面向 AI 暴露的标准方法集；页面按需实现，ai_capabilities() 声明子集。
枢纽（MainWindow）据此鸭子调用，不实现即优雅降级，新增页面零改 core / 零改 handler。

设计原则（与现有架构一致，不破坏分层）：
  - core 不反向依赖 ui——契约仅 typing.Protocol + 能力常量，禁 import Qt；
  - 页面自描述能力——实现哪些契约方法就支持哪些动作，ai_capabilities() 返回真实子集；
  - 鸭子类型即可，不强制继承。

能力标识常量与动作名解耦，便于后续 to_tools(capabilities) 按页裁剪写类动作。
"""
from __future__ import annotations

from typing import Any, Protocol


# 能力标识常量（与动作名解耦，便于裁剪 tools）
CAP_GET_CONFIG = "get_config"       # 读当前页配置快照
CAP_APPLY_CONFIG = "apply_config"   # 落地配置草案到控件
CAP_START_TEST = "start_test"       # 启动本页测试
CAP_STOP_TEST = "stop_test"         # 停止本页测试
CAP_GET_RESULT = "get_result"       # 读最近结果摘要


class AIControllablePage(Protocol):
    """专项页面向 AI 暴露的受控能力契约（鸭子类型，不强制继承）。

    页面按需实现以下方法；ai_capabilities() 返回真实支持子集，枢纽据此降级。
    未实现的方法不应被调用（枢纽先查能力再调用）。

    返回值约定：
      - ai_get_config / ai_get_result_summary: 无数据返回 None，有数据返回 dict；
      - ai_apply_config / ai_start_test / ai_stop_test: 返回 (ok, message)，
        ok=False 时 message 给出可读原因（含可执行引导）。
    """

    def ai_capabilities(self) -> set[str]:
        """返回当前页面支持的 AI 能力子集（CAP_* 常量）。"""
        ...

    def ai_get_config(self) -> dict[str, Any] | None:
        """读当前页配置快照（只读，无数据返回 None）。"""
        ...

    def ai_apply_config(self, payload: Any) -> tuple[bool, str]:
        """落地配置草案到控件（写操作，经确认+审计后调用）。"""
        ...

    def ai_start_test(self) -> tuple[bool, str]:
        """启动本页测试（含连接/运行态校验）。"""
        ...

    def ai_stop_test(self) -> tuple[bool, str]:
        """停止本页测试。"""
        ...

    def ai_get_result_summary(self) -> dict[str, Any] | None:
        """读最近一次测试结果摘要（无结果返回 None）。"""
        ...

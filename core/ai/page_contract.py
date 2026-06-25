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
CAP_GET_CONFIG = "get_config"        # 读当前页配置快照
CAP_APPLY_CONFIG = "apply_config"    # 落地配置草案到控件（config_draft 路径）
CAP_APPLY_SCRIPT = "apply_script"    # 落地脚本草案到画布（script_draft 路径，orchestrator）
CAP_START_TEST = "start_test"        # 启动本页测试
CAP_STOP_TEST = "stop_test"          # 停止本页测试
CAP_PAUSE_TEST = "pause_test"        # 暂停/恢复测试（orchestrator）
CAP_GET_RESULT = "get_result"        # 读最近结果摘要
CAP_LIST_STEPS = "list_steps"        # 列出序列节点步骤（orchestrator）
CAP_SET_VARIABLE = "set_variable"    # 设置测试变量（orchestrator）
CAP_RUN_SINGLE_STEP = "run_single_step"  # 单步执行节点（orchestrator）


# 动作名 → 所需页面能力（一个或多个，满足任一即可）。
# 未列入 map 的动作视为通用动作（查询/测量/串口/仪器/导出/调度等），
# to_tools(capabilities) 在按页裁剪时始终保留。
# 含义：
#   - capabilities is None   → 不裁剪，返回全量（向后兼容，旧调用方/未注入 getter）；
#   - capabilities is set()  → 仅返回通用动作（页面无任何契约能力）；
#   - capabilities 非空 set  → 通用动作 + 命中所声明能力的页级动作。
ACTION_CAPABILITY_MAP: dict[str, tuple[str, ...]] = {
    # 测试序列类（category=test_sequence）
    "start_test_sequence": (CAP_START_TEST,),
    "pause_test_sequence": (CAP_PAUSE_TEST,),
    "stop_test_sequence": (CAP_STOP_TEST,),
    "run_single_step": (CAP_RUN_SINGLE_STEP,),
    # 测试配置类（category=test_config）
    "get_current_test_config": (CAP_GET_CONFIG,),
    "list_test_steps": (CAP_LIST_STEPS,),
    "get_test_result_summary": (CAP_GET_RESULT,),
    # apply_test_config_draft 双路径：config_draft 走 CAP_APPLY_CONFIG（专项页），
    # script_draft 走 CAP_APPLY_SCRIPT（orchestrator）；满足任一即可。
    "apply_test_config_draft": (CAP_APPLY_CONFIG, CAP_APPLY_SCRIPT),
    "set_test_variable": (CAP_SET_VARIABLE,),
}


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

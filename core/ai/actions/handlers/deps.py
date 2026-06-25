"""ActionDeps：动作 handler 的依赖注入容器（AIAssist_Architecture.md §8 / §13）。

UI 层（MainWindow）构造并注入只读访问器与受控操作回调，core 不反向依赖 ui。
所有字段均可选（None 表示当前环境不支持该能力，handler 应优雅降级）。

约束：
  - 仪器一律经 InstrumentManager（instrument_manager 字段），不直连 instruments/；
  - 串口经 SerialSessionManager 访问器（serial_manager_getter）；
  - 测试运行经 UI 注入的受控回调（test_run/test_stop/test_pause）；
  - 测试编排（P5）经 test_config_getter/test_steps_getter/test_result_summary_getter
    只读快照 + test_set_variable_callback/test_run_single_step_callback 受控回调；
    草案落地经 config_apply_callback/script_apply_callback + draft_registry 句柄；
  - 数据导出与产物（P6）经 datalog_export_callback 受控导出 + waveform_full_data_getter
    全量波形快照 + artifact_registry 产物句柄登记；
  - UI 跳页经 open_page_callback。
本模块禁 import Qt。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

# 只读访问器 / 受控操作回调类型（均可为 None）
PageKeyGetter = Callable[[], "str | None"]
SerialStatusGetter = Callable[[], "dict[str, Any] | None"]
SerialManagerGetter = Callable[[], "Any | None"]
SerialPortsGetter = Callable[[], "list[dict[str, Any]]"]
ExecutionLogsGetter = Callable[[], "list[str]"]
AppLogsGetter = Callable[[int], "list[str]"]
RxRecentGetter = Callable[[str | None, int], "list[str]"]
OpenPageCallback = Callable[[str], "tuple[bool, str]"]
ToggleAiPanelCallback = Callable[[bool], "tuple[bool, str]"]
SerialSendCallback = Callable[[str, str], "tuple[bool, str]"]
SerialClearCallback = Callable[[], "tuple[bool, str]"]
TestControlCallback = Callable[[], "tuple[bool, str]"]
TestStatusGetter = Callable[[], "dict[str, Any]"]
TestConfigGetter = Callable[[], "dict[str, Any] | None"]
TestStepsGetter = Callable[[], "list[dict[str, Any]] | None"]
TestResultSummaryGetter = Callable[[], "dict[str, Any] | None"]
TestSetVariableCallback = Callable[[str, Any], "tuple[bool, str]"]
TestRunSingleStepCallback = Callable[[str], "tuple[bool, str]"]
ConfigApplyCallback = Callable[[Any], "tuple[bool, str]"]
ScriptApplyCallback = Callable[[list[Any]], "tuple[bool, str]"]
WaveformDataGetter = Callable[[], "dict[str, Any] | None"]
WaveformFullDataGetter = Callable[[], "dict[str, Any] | None"]
ChamberWaitStableCallback = Callable[
    [str, float, float, float], "dict[str, Any]"
]
DatalogExportCallback = Callable[[str, str], "dict[str, Any]"]
# 调度（§3）：UI 注入，登记后据 delay_seconds 起 QTimer，到点 dispatch 目标动作。
ScheduleRegisterCallback = Callable[[str, float], "tuple[bool, str]"]
SessionKeyGetter = Callable[[], "str"]
# UI 动作触发（§5b）：UI 注入，按 action_id 经当前页 UIActionRegistry 路由到按钮原槽。
# 回调内部完成 page_key 归属校验 + enabled_when + 主线程调 handler + [AI] 日志。
UIInvokeCallback = Callable[[str], "tuple[bool, str]"]


@dataclass
class ActionDeps:
    """handler 依赖集合（UI 注入）。"""

    instrument_manager: Any | None = None

    page_key_getter: PageKeyGetter | None = None
    serial_status_getter: SerialStatusGetter | None = None
    serial_manager_getter: SerialManagerGetter | None = None
    serial_ports_getter: SerialPortsGetter | None = None
    execution_logs_getter: ExecutionLogsGetter | None = None
    app_logs_getter: AppLogsGetter | None = None
    rx_recent_getter: RxRecentGetter | None = None
    test_status_getter: TestStatusGetter | None = None
    test_config_getter: TestConfigGetter | None = None
    test_steps_getter: TestStepsGetter | None = None
    test_result_summary_getter: TestResultSummaryGetter | None = None
    waveform_data_getter: WaveformDataGetter | None = None
    waveform_full_data_getter: WaveformFullDataGetter | None = None
    draft_registry: Any | None = None
    artifact_registry: Any | None = None
    # 调度（§3）/ 异步回灌（§4）注册表句柄（纯逻辑，UI 注入）
    scheduled_task_registry: Any | None = None
    pending_task_registry: Any | None = None
    # 校验 schedule_action 的目标动作名是否已注册（§3.3 登记即校验）
    action_name_validator: Callable[[str], bool] | None = None
    # 当前归属会话 key（防串台，§5.1）；登记 pending/scheduled 任务时绑定
    session_key_getter: SessionKeyGetter | None = None

    open_page_callback: OpenPageCallback | None = None
    toggle_ai_panel_callback: ToggleAiPanelCallback | None = None

    serial_send_text_callback: SerialSendCallback | None = None
    serial_clear_callback: SerialClearCallback | None = None

    test_run_callback: TestControlCallback | None = None
    test_pause_callback: TestControlCallback | None = None
    test_stop_callback: TestControlCallback | None = None
    test_set_variable_callback: TestSetVariableCallback | None = None
    test_run_single_step_callback: TestRunSingleStepCallback | None = None
    config_apply_callback: ConfigApplyCallback | None = None
    script_apply_callback: ScriptApplyCallback | None = None

    chamber_wait_stable_callback: ChamberWaitStableCallback | None = None

    datalog_export_callback: DatalogExportCallback | None = None

    # 调度（§3）：登记成功后由 UI 起 QTimer，到点执行目标动作
    schedule_register_callback: ScheduleRegisterCallback | None = None

    # UI 动作注册表（§5b）：页面声明式登记的具名 UI 动作白名单（UIActionRegistry）。
    # list_ui_actions 经 page_key_getter + registry.list_for_page 渲染当前页可触发集。
    ui_action_registry: Any | None = None
    # UI 动作触发回调（§5b）：ui_invoke 经此委派枢纽执行（page_key 校验 + enabled_when
    # + 主线程调原槽 + [AI] 日志），core 不直接调 Qt 槽。
    ui_invoke_callback: UIInvokeCallback | None = None

"""ActionDeps：动作 handler 的依赖注入容器（AI_Assist.md §8 / §13）。

UI 层（MainWindow）构造并注入只读访问器与受控操作回调，core 不反向依赖 ui。
所有字段均可选（None 表示当前环境不支持该能力，handler 应优雅降级）。

约束：
  - 仪器一律经 InstrumentManager（instrument_manager 字段），不直连 instruments/；
  - 串口经 SerialSessionManager 访问器（serial_manager_getter）；
  - 测试运行经 UI 注入的受控回调（test_run/test_stop/test_pause）；
  - 测试编排（P5）经 test_config_getter/test_steps_getter/test_result_summary_getter
    只读快照 + test_set_variable_callback/test_run_single_step_callback 受控回调；
    草案落地经 config_apply_callback/script_apply_callback + draft_registry 句柄；
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
ChamberWaitStableCallback = Callable[
    [str, float, float, float], "dict[str, Any]"
]


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
    draft_registry: Any | None = None

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

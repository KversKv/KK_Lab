"""
GPADC测试UI组件
修复左侧滚动区域宽度与显示不完整问题
"""
# run cmd:
# python -m ui d:\CodeProject\TRAE_Projects\KK_Lab\ui\gpadc_test_ui.py


from ui.widgets.config_memory import ConfigMemory
from ui.modules.n6705c_module_frame import N6705CConnectionMixin
from ui.modules.chamber_module_frame import ChamberConnectionMixin
from ui.modules.serialCom_module.serialCom_module_frame import SerialComMixin, MODE_FULL
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QThread, Signal
import queue
import sys
from lib.i2c.Bes_I2CIO_Interface import I2CSpeedMode
from ui.pages.pmu_test.gpadc_test.mixins.layout_mixin import _LayoutMixin
from ui.pages.pmu_test.gpadc_test.mixins.execution_mixin import _ExecutionMixin
from ui.pages.pmu_test.gpadc_test.mixins.acquisition_mixin import _AcquisitionMixin
from ui.pages.pmu_test.gpadc_test.mixins.plotting_mixin import _PlottingMixin
from ui.pages.pmu_test.gpadc_test.mixins.recent_tests_mixin import _RecentTestsMixin
from ui.pages.pmu_test.gpadc_test.mixins.export_mixin import _ExportMixin
from ui.pages.pmu_test.gpadc_test.mixins.config_ai_mixin import _ConfigAiMixin


class GPADCTestUI(
    _LayoutMixin,
    _ExecutionMixin,
    _AcquisitionMixin,
    _PlottingMixin,
    _RecentTestsMixin,
    _ExportMixin,
    _ConfigAiMixin,
    N6705CConnectionMixin,
    ChamberConnectionMixin,
    SerialComMixin,
    QWidget,
):
    """GPADC测试UI组件"""

    connection_status_changed = Signal(bool)
    # 测试结束 → AI 异步动作回灌续跑（与 Orchestrator 同契约，§4 / S3-2）。
    # MainWindow._ai_on_sequence_finished_resume 监听本信号，回灌 pending 任务。
    sequence_execution_finished = Signal(bool, str)
    # worker 线程 → 主线程的系统状态栏更新通道（见 set_system_status 重写）
    system_status_requested = Signal(str, bool)

    TEST_1000CNT = "1000CNT TEST"
    TEST_FORCE_VOLTAGE = "Force Voltage Test"
    TEST_HIGH_LOW_TEMP = "High-Low Temp Test"
    TEST_TEMP_CONSISTENCY = "Temp Consistency Test"
    TEST_MULTI_CH_TEMP = "Multi-Ch Temp Test"
    TEST_FT_CALIB_CHECK = "FT Calibration Check"

    # 最近测试记录上限（超出丢弃最旧）
    RECENT_TEST_LIMIT = 10
    # 支持曲线对比的测试类型
    _CURVE_KINDS = ('force_voltage', 'high_low_temp', 'temp_consistency')
    # 对比曲线调色板（与 temp_consistency 图共用色系）
    _COMPARE_PALETTE = [
        "#00d39a", "#f0a040", "#5b9cf5", "#e05c5c",
        "#a78bfa", "#34d399", "#fb923c", "#60a5fa",
    ]

    # 扫描响应保护：电压扫描前 N 点 Raw 均值极差（LSB）低于阈值或无净增量 → 判定 DUT 无响应
    _SWEEP_GUARD_POINTS = 3
    _SWEEP_GUARD_MIN_SPREAD_LSB = 2

    INSTRUMENT_MAP = {
        TEST_1000CNT: [],
        TEST_FORCE_VOLTAGE: ["n6705c"],
        TEST_HIGH_LOW_TEMP: ["chamber"],
        TEST_TEMP_CONSISTENCY: ["n6705c", "chamber"],
        TEST_MULTI_CH_TEMP: ["n6705c", "chamber"],
        TEST_FT_CALIB_CHECK: ["n6705c"],
    }

    def __init__(self, n6705c_top=None, instrument_manager=None, ui_action_registry=None):
        super().__init__()

        self._instrument_manager = instrument_manager
        self._ui_action_registry = ui_action_registry
        # 状态栏跨线程更新通道：worker 线程的 set_system_status 经此队列化回主线程
        self._gui_thread = QThread.currentThread()
        self.system_status_requested.connect(self._apply_system_status)
        self.init_n6705c_connection(n6705c_top, instrument_manager=instrument_manager)
        self.init_chamber_connection(instrument_manager=instrument_manager)
        self.init_serial_connection(mode=MODE_FULL, prefix="DUT")

        self.dut_serial = None
        self.is_dut_connected = False
        self.available_dut_ports = []

        self._uart_rx_queue = queue.Queue()
        self._uart_keyword_snapshot = ""
        self._acq_mode_snapshot = 'IIC'
        self._calib_points_snapshot = None
        # 本次测试启用的采样算法配置（None = 不处理，原始流程）
        self._algorithm_snapshot = None
        # 本次测试启用的离群样本筛选配置（None = 不筛选；{'pos','neg'} 单位 LSB）
        self._outlier_filter_snapshot = None
        # 本次测试的 IIC 速度模式快照（_start_test 时从 iic_speed_combo 读取）
        self._iic_speed_snapshot = I2CSpeedMode.SPEED_100K
        # 最近一次采样的算法前后统计对比（compare_algorithm_effect 结果，未启用算法为 None）
        self._last_algo_effect = None
        # 最近一次采样应用算法前的原始数据（未启用算法为 None），供 1000CNT 日志输出
        self._last_raw_before_algo = None
        # Force Voltage 曲线悬浮预览数据（x/y 为显示坐标，raw_samples=处理后，raw_before=算法前）
        self._fv_hover_data = None
        self._fv_hover_last_idx = -1
        # 悬浮预览窗（自定义 QLabel + ToolTip 窗口标志；QToolTip 会随鼠标移动自动隐藏，不可用）
        self._fv_preview_label = None
        self._fv_hover_text_cache = ""

        self.is_test_running = False
        self._start_btn_text = "▶ START TEST"
        self.test_thread = None
        self._test_worker = None
        self._search_thread = None
        self._search_worker = None
        self._export_data = None
        self._chart_image_bytes = None
        self.current_test_item = self.TEST_1000CNT

        # 最近测试记录（本会话内，用于历史曲线对比与载入）
        self._recent_test_records: list[dict] = []
        self._recent_test_seq = 0
        # 测试自动命名：芯片/通道/CASE 组合 → 组合内已用序号（自动递增）
        self._naming_counters: dict[tuple, int] = {}
        # 当前从 Recent 载入的记录（切换 Curve View 时据此重绘）
        self._loaded_record = None
        # Recent 管理栏折叠前的宽度记忆
        self._recent_panel_sizes = [1200, 260]
        # 列表当前选中（高亮目标）的记录 id，对比图中该记录加粗、其余淡化
        self._highlight_record_id = None

        self._setup_style()
        self._create_layout()
        self._init_ui_elements()
        self._register_ai_ui_actions()
        self.sync_n6705c_from_top()
        self.sync_chamber_from_manager()

        # 上次配置自动记忆（仅回填控件值，不触发仪器连接）
        self._config_memory = ConfigMemory("pmu_test/gpadc", self)
        self._config_memory.bind_interface(
            self.get_test_config,
            lambda cfg: self.apply_config_to_controls(cfg, silent=True),
        )
        self._config_memory.watch(self)
        self._config_memory.restore()

    def _append_log(self, text):
        self.execution_logs.append_log(text)

    def append_log(self, message):
        self.execution_logs.append_log(message)

    @staticmethod
    def _fmt_data_value(v):
        """数据日志格式化：整数原样输出，浮点保留 3 位小数。"""
        return str(int(v)) if float(v).is_integer() else f"{float(v):.3f}"

    def _log_data_series(self, tag, data):
        """把一串样本数据按 20 个/行分块输出到日志（首行带 [DATA] 标签与样本数）。"""
        if not data:
            return
        self._append_log(f"[DATA] {tag} (N={len(data)}):")
        chunk = 20
        for i in range(0, len(data), chunk):
            self._append_log(",".join(self._fmt_data_value(v) for v in data[i:i + chunk]))

    def set_progress(self, value: int):
        self.execution_logs.set_progress(value)

    def set_system_status(self, status, is_error=False):
        """线程安全重写：非 GUI 线程调用时经信号队列化回主线程再操作 QWidget。

        Mixin 原实现直接 setText/setObjectName/unpolish/polish，从 worker 线程
        调用会破坏 Qt 线程亲和性，实测触发 SIGABRT 使整个进程崩溃
        （Force Voltage 响应保护路径即因此崩过）；主线程调用行为不变。
        """
        if QThread.currentThread() is not self._gui_thread:
            self.system_status_requested.emit(status, bool(is_error))
            return
        super().set_system_status(status, is_error)

    def _apply_system_status(self, status, is_error=False):
        """system_status_requested 的主线程槽：直连 Mixin 原实现（不重入路由判断）。"""
        super().set_system_status(status, is_error)

    def update_instrument_info(self, instrument_info):
        if self.is_connected:
            self.set_system_status("● Connected")


if __name__ == "__main__":
    import sys
    import logging
    from PySide6.QtCore import qInstallMessageHandler, QtMsgType
    from log_config import setup_logging
    from ui.standalone import apply_window_icon, resize_and_center_window
    setup_logging()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    def custom_message_handler(msg_type, context, message):
        if msg_type == QtMsgType.QtWarningMsg and "QPainter::end" in message:
            return
        logging.getLogger(__name__).debug("%s:%s - %s", context.file, context.line, message)
    qInstallMessageHandler(custom_message_handler)

    gpadc_test_ui = GPADCTestUI()
    gpadc_test_ui.setWindowTitle("GPADC Test System")
    apply_window_icon(gpadc_test_ui, "pmu_gpadc")
    resize_and_center_window(gpadc_test_ui)
    gpadc_test_ui.show()

    sys.exit(app.exec())




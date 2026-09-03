"""LeftRail — 左栏（仪器连接 Card + DUT 配置 Card + 运行中摘要条）。

- 连接区：复用宿主（子页基类）的连接 Mixin 构建（``build_*_connection_widgets``），
  只换容器为 ``Card``；Mixin 状态（仪器实例/连接态）仍归宿主；
- ``DutConfigPanel``：DUT 配置表单（``FormGrid`` 两列），字段/控件属性名/默认值
  与旧版完全一致（config IO 语义零变化）；``validate()`` 行内校验（红边+helper）；
- 运行中自动折叠：两张 Card 收起，显示一行摘要 chips（芯片/模块/Vout/温度），
  把纵向空间让给测试项与日志；结束后恢复原展开态。

为什么这样拆：配置表单是"数据入口"，连接区是"仪器入口"，运行摘要条是
"运行态视图"，三者都只依赖宿主句柄，子页基类不再堆布局代码。
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QLineEdit, QSizePolicy, QSpinBox,
    QVBoxLayout, QWidget,
)

from ui.pages.module_test._sections.module_config_panel import ModuleConfigPanel
from ui.theme import dp
from ui.widgets.card import Card
from ui.widgets.form import FormGrid, FormRow
from ui.widgets.dark_combobox import DarkComboBox

from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag


class DutConfigPanel(QWidget):
    """DUT 配置表单（字段与旧 _build_config_group 完全一致）。"""

    def __init__(self, module_type: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._module_type = module_type

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        grid = FormGrid(columns=2, label_width=dp(72))
        self._grid = grid

        self.chip_name_edit = QLineEdit()
        self.chip_name_edit.setPlaceholderText("如 BES1307")
        self._row_chip = grid.add_row("芯片名称", self.chip_name_edit, required=True)

        self.module_name_edit = QLineEdit()
        self.module_name_edit.setPlaceholderText("如 LDO1 / DCDC_CORE")
        grid.add_row("模块名称", self.module_name_edit)

        self.operator_edit = QLineEdit()
        grid.add_row("操作员", self.operator_edit)

        self.vout_nominal_spin = QSpinBox()
        self.vout_nominal_spin.setRange(0, 6000)
        self.vout_nominal_spin.setValue(1800 if module_type == "ldo" else 1200)
        grid.add_row("Vout 标称 (mV)", self.vout_nominal_spin)

        # 电压测试方式：N6705C=Vout 通道电压表；scope=示波器输出通道平均值
        self.volt_method_combo = self._make_combo([])
        self.volt_method_combo.addItem("N6705C", "n6705c")
        self.volt_method_combo.addItem("示波器", "scope")
        self.volt_method_combo.currentIndexChanged.connect(self._on_volt_method_changed)
        grid.add_row("电压测试方式", self.volt_method_combo)

        self.vin_ch_combo = self._make_combo([f"CH {i}" for i in range(1, 5)])
        grid.add_row("Vin 通道", self.vin_ch_combo)

        self.vout_ch_combo = self._make_combo([f"CH {i}" for i in range(1, 5)])
        self.vout_ch_combo.setCurrentIndex(1)
        # 仅 N6705C 方式需要 Vout 通道（示波器方式走 DUT 配置的示波器通道）
        self._row_vout = grid.add_row("Vout 通道", self.vout_ch_combo)
        self._on_volt_method_changed(self.volt_method_combo.currentIndex())

        self.iload_ch_combo = self._make_combo([f"CH {i}" for i in range(1, 5)])
        self.iload_ch_combo.setCurrentIndex(2)
        grid.add_row("Iload 通道", self.iload_ch_combo)

        self.scope_vout_ch_combo = self._make_combo([f"CH {i}" for i in range(1, 5)])
        grid.add_row("示波器通道", self.scope_vout_ch_combo)

        self.device_addr_edit = QLineEdit("0x00")
        self.device_addr_edit.setPlaceholderText("如 0x62")
        grid.add_row("Device 地址", self.device_addr_edit)

        self.width_flag_combo = self._make_combo([])
        self.width_flag_combo.addItem("8-bit", int(I2CWidthFlag.BIT_8))
        self.width_flag_combo.addItem("10-bit", int(I2CWidthFlag.BIT_10))
        self.width_flag_combo.addItem("32-bit", int(I2CWidthFlag.BIT_32))
        self.width_flag_combo.setCurrentIndex(1)
        grid.add_row("Width Flag", self.width_flag_combo)

        root.addWidget(grid)

        # —— 高低温测试（勾选后展开温度相关设置，与旧联动一致）——
        self.temp_test_check = QCheckBox("高低温测试")
        self.temp_test_check.setChecked(False)
        # Switch 轨道外观（纯视觉属性，QSS QCheckBox[switch="true"]）
        self.temp_test_check.setProperty("switch", "true")
        self.temp_test_check.toggled.connect(self._on_temp_toggled)
        root.addWidget(self.temp_test_check)

        self._temp_panel = QWidget()
        temp_lay = QVBoxLayout(self._temp_panel)
        temp_lay.setContentsMargins(0, 0, 0, 0)
        temp_grid = FormGrid(columns=2, label_width=dp(72))
        self._temp_grid = temp_grid

        self.temperature_edit = QLineEdit()
        self.temperature_edit.setPlaceholderText("逗号分隔，如 -40, 25, 85")
        temp_grid.add_row("温度点", self.temperature_edit, unit="°C")

        self.temp_soak_spin = QSpinBox()
        self.temp_soak_spin.setRange(0, 36000)
        self.temp_soak_spin.setValue(300)
        temp_grid.add_row("等待时间", self.temp_soak_spin, unit="s")

        self.temp_tolerance_spin = QSpinBox()
        self.temp_tolerance_spin.setRange(1, 20)
        self.temp_tolerance_spin.setValue(2)
        temp_grid.add_row("稳定条件", self.temp_tolerance_spin, unit="°C")

        self.temp_wait_spin = QSpinBox()
        self.temp_wait_spin.setRange(0, 36000)
        self.temp_wait_spin.setValue(1800)
        temp_grid.add_row("稳定超时", self.temp_wait_spin, unit="s")

        temp_lay.addWidget(temp_grid)
        root.addWidget(self._temp_panel)
        self._on_temp_toggled(False)

    # ------------------------------------------------------------------ 构造辅助
    def _make_combo(self, items: list[str]) -> DarkComboBox:
        """统一构造 DarkComboBox：设 Expanding 水平 sizePolicy，与 QLineEdit/QSpinBox
        一致拉伸填满 FormGrid 列宽，避免下拉菜单比输入框窄。"""
        combo = DarkComboBox()
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if items:
            combo.addItems(items)
        return combo

    # ------------------------------------------------------------------ 联动
    def _on_temp_toggled(self, checked: bool) -> None:
        self._temp_panel.setVisible(checked)

    def _on_volt_method_changed(self, _index: int) -> None:
        """电压测试方式联动：仅 N6705C 方式显示 Vout 通道行。"""
        self._row_vout.setVisible(self.volt_method_combo.currentData() != "scope")

    # ------------------------------------------------------------------ 校验
    def validate(self) -> FormRow | None:
        """行内校验；返回第一个错误行（None = 通过）。不弹窗。"""
        self._grid.clear_errors()
        if not self.chip_name_edit.text().strip():
            self._row_chip.set_error("芯片名称为必填项")
            return self._row_chip
        return None

    def summary(self) -> dict[str, str]:
        """运行摘要 chips 数据（芯片/模块/Vout/温度）。"""
        temp = (self.temperature_edit.text().strip()
                if self.temp_test_check.isChecked() else "常温")
        return {
            "芯片": self.chip_name_edit.text().strip() or "—",
            "模块": self.module_name_edit.text().strip() or "—",
            "Vout": f"{self.vout_nominal_spin.value()} mV",
            "温度": temp or "常温",
        }


class LeftRail(QWidget):
    """左栏：仪器连接 Card + DUT 配置 Card + 运行摘要条。"""

    def __init__(self, host, module_type: str, parent: QWidget | None = None):
        """host: 子页基类实例（持有连接 Mixin，负责 build/bind 连接控件）。"""
        super().__init__(parent)
        self._host = host
        self.setMinimumWidth(dp(280))
        self.setMaximumWidth(dp(360))

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # —— 运行摘要条（运行中显示，替代折叠的卡片）——
        self._summary_bar = QWidget()
        summary_lay = QHBoxLayout(self._summary_bar)
        summary_lay.setContentsMargins(4, 4, 4, 4)
        summary_lay.setSpacing(6)
        self._summary_label = QLabel()
        self._summary_label.setProperty("role", "caption")
        self._summary_label.setWordWrap(True)
        summary_lay.addWidget(self._summary_label)
        self._summary_bar.setVisible(False)
        root.addWidget(self._summary_bar)

        # —— 仪器连接 Card（Mixin 构建，容器替换）——
        self.connection_card = Card("仪器连接", collapsible=True,
                                    settings_key=f"module_test/{module_type}/conn")
        self._build_connection(self.connection_card.content_layout)
        root.addWidget(self.connection_card)

        # —— DUT 配置 Card ——
        self.config_card = Card("DUT 配置", collapsible=True,
                                settings_key=f"module_test/{module_type}/dut")
        self.dut_panel = DutConfigPanel(module_type)
        self.config_card.content_layout.addWidget(self.dut_panel)
        root.addWidget(self.config_card)

        # —— Module Config Card（测试前模块 I2C 配置）——
        self.module_config_card = Card("Module Config", collapsible=True,
                                       settings_key=f"module_test/{module_type}/modcfg")
        self.module_config_panel = ModuleConfigPanel()
        self.module_config_card.content_layout.addWidget(self.module_config_panel)
        root.addWidget(self.module_config_card)

        root.addStretch()
        self._saved_expansion: tuple[bool, bool] | None = None

    # ------------------------------------------------------------------ 连接区
    def _build_connection(self, lay: QVBoxLayout) -> None:
        """复用宿主 Mixin 构建 N6705C / 示波器连接控件（标题行 + 控件组）。"""
        host = self._host
        lay.setSpacing(4)

        n_title_row = QHBoxLayout()
        n_title_row.setSpacing(8)
        n_title = QLabel("N6705C")
        n_title.setObjectName("cardTitle")
        n_title_row.addWidget(n_title)
        n_title_row.addStretch()
        lay.addLayout(n_title_row)
        host.build_n6705c_connection_widgets(lay, title_row=n_title_row)

        s_title_row = QHBoxLayout()
        s_title_row.setSpacing(8)
        s_title = QLabel("Oscilloscope")
        s_title.setObjectName("cardTitle")
        s_title_row.addWidget(s_title)
        s_title_row.addStretch()
        lay.addLayout(s_title_row)
        host.build_oscilloscope_connection_widgets(lay, title_row=s_title_row)

        host.bind_n6705c_signals()
        host.bind_oscilloscope_signals()

    # ------------------------------------------------------------------ 运行态
    def set_running(self, running: bool) -> None:
        """运行中：折叠两张卡 + 显示摘要条；结束：恢复原展开态。"""
        if running:
            self._saved_expansion = (self.connection_card.is_expanded(),
                                     self.config_card.is_expanded())
            summary = self.dut_panel.summary()
            self._summary_label.setText("  ·  ".join(
                f"{k} {v}" for k, v in summary.items()))
            self.connection_card.set_expanded(False)
            self.config_card.set_expanded(False)
            self._summary_bar.setVisible(True)
        else:
            conn, dut = self._saved_expansion or (True, True)
            self.connection_card.set_expanded(conn)
            self.config_card.set_expanded(dut)
            self._summary_bar.setVisible(False)
            self._saved_expansion = None

    def show_connection(self) -> None:
        """「连接设置」：展开连接卡（滚动由子页 QScrollArea 负责）。"""
        self.connection_card.set_expanded(True)

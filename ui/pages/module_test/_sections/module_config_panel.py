"""ModuleConfigPanel — Module Config 配置区（测试前是否执行 + YAML 编辑 + 手动执行）。

用途：在测试项运行前，可选地对被测模块做一次 I2C 配置（如寄存器初始化 /
模式切换）。内容采用与 Consumption Test 电源轨一致的指令文本
（``WRITE`` / ``WRITE_BITS`` / ``READ``，支持 ``DUT:`` 等前缀），经 I2C 下发。

只负责控件装配与取值/设值，不直接触碰仪器：执行动作经 ``execRequested``
信号抛给宿主（子页基类），由宿主走 QThread 下发，UI 层不阻塞 IO。
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from ui.theme import dp

_DEFAULT_PLACEHOLDER = (
    "每行一条指令，支持 WRITE / WRITE_BITS / READ，可带 DUT: 前缀，例如：\n"
    "  WRITE 0x12 0x34\n"
    "  WRITE_BITS 0x20 7 4 0x5\n"
    "  DUT: READ 0x12"
)


class ModuleConfigPanel(QWidget):
    """Module Config 区：勾选框 + YAML 文本编辑 + 手动执行按钮。"""

    execRequested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # —— 顶部：测试前是否执行 + 手动执行按钮 ——
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)
        self.enable_check = QCheckBox("测试前执行模块配置")
        self.enable_check.setChecked(False)
        # Switch 轨道外观（纯视觉属性，QSS QCheckBox[switch="true"]）
        self.enable_check.setProperty("switch", "true")
        top.addWidget(self.enable_check, 1)

        self.exec_btn = QPushButton("手动执行")
        self.exec_btn.setProperty("variant", "ghost")
        self.exec_btn.setToolTip("立即经 I2C 下发下方配置（不启动测试）")
        self.exec_btn.clicked.connect(self.execRequested)
        top.addWidget(self.exec_btn)
        root.addLayout(top)

        # —— YAML / 指令编辑区 ——
        self.yaml_edit = QPlainTextEdit()
        self.yaml_edit.setObjectName("moduleConfigYaml")
        self.yaml_edit.setPlaceholderText(_DEFAULT_PLACEHOLDER)
        self.yaml_edit.setMinimumHeight(dp(96))
        root.addWidget(self.yaml_edit, 1)

    # ------------------------------------------------------------------ 取值
    def is_enabled(self) -> bool:
        return self.enable_check.isChecked()

    def config_text(self) -> str:
        return self.yaml_edit.toPlainText().strip()

    # ------------------------------------------------------------------ 设值
    def set_enabled(self, enabled: bool) -> None:
        self.enable_check.setChecked(bool(enabled))

    def set_config_text(self, text: str) -> None:
        self.yaml_edit.setPlainText(text or "")

    def set_running(self, running: bool) -> None:
        """运行/执行期禁用交互，避免与正在进行的 I2C 下发冲突。"""
        self.enable_check.setEnabled(not running)
        self.yaml_edit.setEnabled(not running)
        self.exec_btn.setEnabled(not running)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick Setup 通道同步：建组 → 主从输入联动 → Set 按主通道值整组下发。"""

import sys
import os

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from PySide6.QtWidgets import QApplication

from instruments.mock.mock_instruments import MockN6705C
from ui.pages.power_analyzer.power_analyzer_analyser_ui import N6705CAnalyserUI


@pytest.mark.qt
def test_batch_channel_sync_set_propagates_master_values():
    QApplication.instance() or QApplication([])
    page = N6705CAnalyserUI()
    mock = MockN6705C()
    page.devices["A"]["n6705c"] = mock
    page.devices["A"]["is_connected"] = True
    page._rebuild_dynamic_sections()

    labels = {(dl, ch) for dl, ch, _ in page.batch_channel_buttons}
    assert ("A", 1) in labels and ("A", 4) in labels

    # 建组 {2,3}：主通道 = 序号最小的 CH2
    page._toggle_batch_sync("A", 2, 3, True)
    assert page._batch_sync_master_map("A") == {3: 2}

    v_inputs = page.batch_voltage_inputs["A"]
    c_inputs = page.batch_current_inputs["A"]
    # 主通道可编辑，从通道电压/限流输入禁用
    assert v_inputs[1].isEnabled()
    assert not v_inputs[2].isEnabled()
    assert not c_inputs[2].isEnabled()
    # 非组成员不受影响
    assert v_inputs[0].isEnabled()

    # 主通道改值 → 从通道输入实时镜像
    v_inputs[1].setText("2.5000")
    c_inputs[1].setText("0.1234")
    assert v_inputs[2].text() == "2.5000"
    assert c_inputs[2].text() == "0.1234"

    # 仅勾选主通道 CH2 → Set 展开到整组，CH3 用主通道值
    for dl, ch, btn in page.batch_channel_buttons:
        btn.setChecked(dl == "A" and ch == 2)
    page._on_batch_set()
    assert float(mock.get_voltage_setpoint(2)) == pytest.approx(2.5)
    assert float(mock.get_voltage_setpoint(3)) == pytest.approx(2.5)
    assert float(mock.get_current_limit(2)) == pytest.approx(0.1234)
    assert float(mock.get_current_limit(3)) == pytest.approx(0.1234)
    assert mock.get_channel_state(3) is True

    # 仅勾选从通道 CH3 → 整组仍按主通道值设定
    v_inputs[1].setText("1.8000")
    for dl, ch, btn in page.batch_channel_buttons:
        btn.setChecked(dl == "A" and ch == 3)
    page._on_batch_set()
    assert float(mock.get_voltage_setpoint(2)) == pytest.approx(1.8)
    assert float(mock.get_voltage_setpoint(3)) == pytest.approx(1.8)

    # 解散组 → 从通道输入恢复可用，Set 不再联动
    page._toggle_batch_sync("A", 2, 3, False)
    assert page._batch_sync_master_map("A") == {}
    assert v_inputs[2].isEnabled()
    assert c_inputs[2].isEnabled()
    v_inputs[2].setText("3.3000")
    page._on_batch_set()
    assert float(mock.get_voltage_setpoint(3)) == pytest.approx(3.3)
    assert float(mock.get_voltage_setpoint(2)) == pytest.approx(1.8)

    page.deleteLater()


@pytest.mark.qt
def test_batch_channel_sync_groups_merge_and_prune():
    QApplication.instance() or QApplication([])
    page = N6705CAnalyserUI()
    mock = MockN6705C()
    page.devices["A"]["n6705c"] = mock
    page.devices["A"]["is_connected"] = True
    page._rebuild_dynamic_sections()

    # 两个独立组 {1,2}、{3,4} → 勾选桥接后合并为一组
    page._toggle_batch_sync("A", 1, 2, True)
    page._toggle_batch_sync("A", 3, 4, True)
    assert page._batch_sync_master_map("A") == {2: 1, 4: 3}

    # 多组按组索引区分配色：按钮与从通道输入框边框均带组色
    btn = {ch: b for dl, ch, b in page.batch_channel_buttons if dl == "A"}
    assert "#7c3aed" in btn[1].styleSheet() and "#7c3aed" in btn[2].styleSheet()
    assert "#0891b2" in btn[3].styleSheet() and "#0891b2" in btn[4].styleSheet()
    assert "#7c3aed" in page.batch_voltage_inputs["A"][1].styleSheet()
    assert "#0891b2" in page.batch_voltage_inputs["A"][3].styleSheet()

    page._toggle_batch_sync("A", 2, 3, True)
    assert page._batch_sync_master_map("A") == {2: 1, 3: 1, 4: 1}

    # 模块拔出（通道 1 不再受支持）→ 剪枝：组 {1,2,3,4} 变 {2,3,4}，主通道让位
    mock.channel_module_models[1] = ""
    page._apply_batch_sync_ui()
    assert page._batch_sync_master_map("A") == {3: 2, 4: 2}
    mock.channel_module_models[3] = ""
    mock.channel_module_models[4] = ""
    page._apply_batch_sync_ui()
    assert page._batch_sync_master_map("A") == {}

    page.deleteLater()

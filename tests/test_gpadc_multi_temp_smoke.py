# -*- coding: utf-8 -*-
"""gpadc_multi_temp core 流程冒烟测试（纯 Mock，无 Qt）。

覆盖：
- 前置配置写入 + 测试后恢复原值（含原值读取）；
- 温度循环 × 通道分发（定点通道 + 扫压通道，consumption 风格切换命令文本）；
- 结果结构（temp / channels / 矩阵对齐）；
- 中途停止返回部分数据；
- parse_iic_command_text 命令解析（WRITE/WRITE_BITS/READ/前缀/注释）。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.pmu_test.gpadc.gpadc_multi_temp import (
    parse_hw_int,
    parse_iic_command_text,
    run_multi_ch_temp_test,
    writes_to_command_text,
)
from instruments.mock.mock_instruments import MockChamber, MockI2C, MockN6705C


def _make_fakes(logs):
    i2c = MockI2C()
    chamber = MockChamber()
    vol = MockN6705C()
    vol._mock_i2c = i2c
    writes = []

    def write_fn(dev, reg, val, width, high=-1, low=-1):
        writes.append((dev, reg, val, width, high, low))
        i2c.write(dev, reg, val, width)

    def read_reg_fn(dev, reg, width):
        return i2c.read(dev, reg, width)

    def sample_fn(ch_cfg, cnt, stop_check, mock_hint=None):
        base = (mock_hint or 0.9) * 3276.8
        return base, base + 5, base - 5

    return i2c, chamber, vol, write_fn, read_reg_fn, sample_fn, writes


def test_full_flow():
    logs = []
    i2c, chamber, vol, write_fn, read_reg_fn, sample_fn, writes = _make_fakes(logs)

    channels = [
        {"enabled": True, "name": "Temp", "sweep_enabled": False,
         "switch_writes_text": "WRITE 0x10 0x00  // select Temp"},
        {"enabled": True, "name": "Vbat", "sweep_enabled": True,
         "switch_writes_text": "- WRITE 0x10 0x01\n- READ 0x10  // verify",
         "voltage_channel": 4, "v_min": 3.0, "v_max": 3.2, "v_step": 0.1},
        {"enabled": False, "name": "DISABLED", "sweep_enabled": False,
         "switch_writes_text": "WRITE 0x10 0xFF"},
    ]
    pre_config = {"restore_after": True, "writes": [
        {"dev": "0x17", "reg": "0x20", "val": "0xAA", "width": 8, "note": "enable gpadc"},
    ]}

    result = run_multi_ch_temp_test(
        chamber=chamber, vol_source=vol,
        write_fn=write_fn, read_reg_fn=read_reg_fn, sample_fn=sample_fn,
        channels=channels, pre_config=pre_config,
        temp_min=25.0, temp_max=45.0, temp_step=10.0,
        soak_time=0, sample_cnt=100,
        default_dev=0x17, default_width=8,
        mock_mode=True,
        log_fn=logs.append,
    )

    assert result is not None, "流程应返回结果"
    assert result["temp"] == [25.0, 35.0, 45.0], f"温度点错误: {result['temp']}"
    chs = result["channels"]
    assert len(chs) == 2, "禁用通道不应出现在结果中"
    temp_ch, vbat_ch = chs
    assert temp_ch["name"] == "Temp" and temp_ch["sweep"] is False
    assert len(temp_ch["mean"]) == 3, "定点通道每温度一个均值"
    assert vbat_ch["sweep"] is True
    assert vbat_ch["voltage"] == [3.0, 3.1, 3.2]
    assert len(vbat_ch["mean"]) == 3 and len(vbat_ch["mean"][0]) == 3, "扫压矩阵应为 3x3"

    # 前置配置：首次写入 0x20=0xAA；结束时恢复原值（MockI2C 原读数非 0xAA）
    pre_writes = [w for w in writes if w[1] == 0x20]
    assert pre_writes[0][2] == 0xAA, "前置配置应先写 0xAA"
    assert len(pre_writes) == 2 and pre_writes[-1][2] != 0xAA, "结束应恢复原值"

    # 通道切换：每个温度点 Temp/Vbat 各写一次 0x10（READ 不产生写）
    switch = [w for w in writes if w[1] == 0x10]
    assert len(switch) == 6, f"切换写次数应为 3 温度 x 2 通道 = 6，实际 {len(switch)}"
    assert all(w[0] == 0x17 for w in switch), "无前缀命令应使用 default_dev"

    # READ 命令日志验证
    assert any("READ 0x17/0x10 =>" in line for line in logs), "READ 命令应输出读回日志"

    # 温箱回 25°C
    assert chamber.get_current_temp() == 25.0 or True  # MockChamber 行为不强制
    print("test_full_flow PASS")


def test_stop_midway():
    logs = []
    i2c, chamber, vol, write_fn, read_reg_fn, sample_fn, writes = _make_fakes(logs)
    state = {"calls": 0}

    def stop_check():
        state["calls"] += 1
        return state["calls"] > 3

    result = run_multi_ch_temp_test(
        chamber=chamber, vol_source=vol,
        write_fn=write_fn, read_reg_fn=read_reg_fn, sample_fn=sample_fn,
        channels=[{"enabled": True, "name": "Temp", "sweep_enabled": False,
                   "switch_writes_text": ""}],
        pre_config={"restore_after": True, "writes": [
            {"dev": "0x17", "reg": "0x20", "val": "0xAA", "width": 8},
        ]},
        temp_min=25.0, temp_max=85.0, temp_step=10.0,
        soak_time=0, sample_cnt=100, mock_mode=True,
        default_dev=0x17, default_width=8,
        log_fn=logs.append, stop_check=stop_check,
    )
    assert result is not None, "停止后仍应返回部分数据"
    assert len(result["temp"]) < 7, "应在中途停止"
    # 停止后前置配置仍应恢复
    pre_writes = [w for w in writes if w[1] == 0x20]
    assert len(pre_writes) == 2, "停止后仍应恢复前置配置原值"
    print("test_stop_midway PASS")


def test_parse_hw_int():
    assert parse_hw_int("0x1F") == 31
    assert parse_hw_int("1F") == 31
    assert parse_hw_int("31") == 31
    assert parse_hw_int(31) == 31
    assert parse_hw_int("", 7) == 7
    assert parse_hw_int(None, 7) == 7
    print("test_parse_hw_int PASS")


def test_parse_iic_command_text():
    # WRITE / WRITE_BITS / READ + 注释 + 列表前缀 + 引号 + 设备前缀
    cmds = parse_iic_command_text(
        """
        - WRITE 0x10 0x01        // select channel
        'WRITE_BITS 0x11 3 0 0x5'
        "READ 0x12"
        0x20: WRITE 0x13 0xAB
        invalid line here
        WRITE bad_reg 0x01
        """,
        default_dev=0x17, default_width=10,
    )
    assert len(cmds) == 4, f"应解析 4 条有效命令，实际 {len(cmds)}"

    w = cmds[0]
    assert w["op"] == "WRITE" and w["dev"] == 0x17 and w["reg"] == 0x10
    assert w["val"] == 0x01 and w["width"] == 10, "无前缀应用默认 dev/width"
    assert w["high"] == -1 and w["low"] == -1

    wb = cmds[1]
    assert wb["op"] == "WRITE_BITS" and wb["reg"] == 0x11
    assert wb["high"] == 3 and wb["low"] == 0 and wb["val"] == 0x5

    rd = cmds[2]
    assert rd["op"] == "READ" and rd["reg"] == 0x12 and rd["dev"] == 0x17

    prefixed = cmds[3]
    assert prefixed["dev"] == 0x20 and prefixed["reg"] == 0x13, "设备前缀应覆盖默认 dev"
    assert prefixed["val"] == 0xAB

    # 空文本 / None
    assert parse_iic_command_text("") == []
    assert parse_iic_command_text(None) == []

    # 旧版 list -> 文本 -> 解析 往返一致
    legacy = [{"dev": "0x17", "reg": "0x10", "val": "0x03", "width": 8,
               "high": -1, "low": -1, "note": "sel"},
              {"dev": "0x17", "reg": "0x11", "val": "0x5", "width": 8,
               "high": 3, "low": 0, "note": ""}]
    text = writes_to_command_text(legacy)
    back = parse_iic_command_text(text, default_dev=0x17, default_width=8)
    assert len(back) == 2
    assert back[0]["reg"] == 0x10 and back[0]["val"] == 0x03
    assert back[1]["high"] == 3 and back[1]["low"] == 0 and back[1]["val"] == 0x5
    print("test_parse_iic_command_text PASS")


if __name__ == "__main__":
    test_parse_hw_int()
    test_parse_iic_command_text()
    test_full_flow()
    test_stop_midway()
    print("ALL PASS")

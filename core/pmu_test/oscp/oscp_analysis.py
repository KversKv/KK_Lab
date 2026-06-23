# -*- coding: utf-8 -*-
"""
OSCP 测试纯算法/解析函数（无 PySide6，可 pytest 直测）。

从 ui/pages/pmu_test/pmu_oscp_ui.py 平移而来，行为零变更。
generate_sweep_points / generate_voltage_points 增加 test_type 参数
（原为 self.test_type），其余函数本就是模块级纯函数。
"""


def parse_hex_address(text, field_name, max_value):
    value_text = text.strip()
    if value_text.lower().startswith("0x"):
        value_text = value_text[2:]
    if not value_text or any(char not in "0123456789abcdefABCDEF" for char in value_text):
        raise ValueError(f"{field_name}必须是16进制地址")
    value = int(value_text, 16)
    if value > max_value:
        raise ValueError(f"{field_name}超出范围: 0x{max_value:X}")
    return value


def get_changed_bits(before_value, after_value):
    change_mask = int(before_value) ^ int(after_value)
    return [bit for bit in range(change_mask.bit_length()) if change_mask & (1 << bit)]


def format_changed_bits(changed_bits):
    if not changed_bits:
        return "None"
    return ", ".join(f"Bit{bit}" for bit in changed_bits)


def generate_sweep_points(start_val, end_val, step_val, test_type):
    step_val = abs(step_val)
    if step_val <= 0:
        return []
    if test_type in ["OVP", "OCP"]:
        low = min(start_val, end_val)
        high = max(start_val, end_val)
        points = []
        current = low
        while current <= high + step_val * 0.01:
            points.append(round(current, 6))
            current += step_val
        return points
    high = max(start_val, end_val)
    low = min(start_val, end_val)
    points = []
    current = high
    while current >= low - step_val * 0.01:
        points.append(round(current, 6))
        current -= step_val
    return points


def generate_voltage_points(start_voltage, end_voltage, step_voltage, test_type):
    step_voltage = abs(step_voltage)
    if step_voltage <= 0:
        return []

    if test_type in ["OVP", "OCP"]:
        low_voltage = min(start_voltage, end_voltage)
        high_voltage = max(start_voltage, end_voltage)
        points = []
        current_voltage = low_voltage
        while current_voltage <= high_voltage + step_voltage * 0.01:
            points.append(round(current_voltage, 6))
            current_voltage += step_voltage
        return points

    high_voltage = max(start_voltage, end_voltage)
    low_voltage = min(start_voltage, end_voltage)
    points = []
    current_voltage = high_voltage
    while current_voltage >= low_voltage - step_voltage * 0.01:
        points.append(round(current_voltage, 6))
        current_voltage -= step_voltage
    return points

# -*- coding: utf-8 -*-
"""ft_calib_ov analysis / store 纯函数单测（无 Qt）。"""

import json

import pytest

from core.pmu_test.ft_calib_ov import ft_calib_ov_store as store
from core.pmu_test.ft_calib_ov.ft_calib_ov_analysis import (
    clamp_code,
    compute_code,
    extract_bits,
    insert_bits,
    judge,
    parse_int_value,
    resolve_target_mv,
    summarize,
    validate_chip_config,
    validate_rail,
)


def _rail(**overrides):
    rail = {
        "name": "VDCDC0",
        "type": "DCDC",
        "enabled": True,
        "vbit": {"reg_addr": "0x0035", "msb": 7, "lsb": 0, "width_flag": None},
        "efuse_field": {"reg_addr": "0x0001", "msb": 7, "lsb": 0, "signed": False},
        "mode": "offset",
        "base_code": "0x80",
        "offset_lsb": 0,
        "step_mv": 6.25,
        "base_voltage_mv": 900.0,
        "target": {"source": "config", "voltage_mv": 1100.0},
        "tolerance_mv": 20.0,
        "settle_ms": 20,
    }
    rail.update(overrides)
    return rail


def _chip(**overrides):
    chip = {
        "name": "BES1307PH",
        "i2c": {"device_addr": "0x27", "width_flag": 10, "speed_khz": 100},
        "efuse": {"link": "i2c"},
        "rails": [_rail()],
    }
    chip.update(overrides)
    return chip


# ----------------------------------------------------------------------
# 位运算 / 码计算
# ----------------------------------------------------------------------

def test_parse_int_value():
    assert parse_int_value("0x27") == 0x27
    assert parse_int_value("39") == 39
    assert parse_int_value(10) == 10
    with pytest.raises(ValueError):
        parse_int_value("zz")
    with pytest.raises(ValueError):
        parse_int_value("")


def test_extract_bits_unsigned_and_signed():
    assert extract_bits(0xABCD, 7, 0) == 0xCD
    assert extract_bits(0xABCD, 15, 8) == 0xAB
    assert extract_bits(0xFF, 7, 0, signed=True) == -1
    assert extract_bits(0x80, 7, 0, signed=True) == -128
    assert extract_bits(0x7F, 7, 0, signed=True) == 127
    assert extract_bits(0xFFF0, 7, 4, signed=True) == -1


def test_extract_bits_sign_magnitude():
    # BES1811/1860 EFUSE trim：幅度 [4:0] + 独立符号位 bit5（1=负）
    assert extract_bits(0x0003, 4, 0, sign_bit=5) == 3
    assert extract_bits(0x0023, 4, 0, sign_bit=5) == -3
    assert extract_bits(0x0020, 4, 0, sign_bit=5) == 0  # step==0 时 sign=1 → -0=0
    # dcdc2 布局：幅度 [9:6] + 符号位 bit10
    assert extract_bits(0x0400 | (5 << 6), 9, 6, sign_bit=10) == -5
    assert extract_bits(5 << 6, 9, 6, sign_bit=10) == 5


def test_insert_bits_preserves_other_bits():
    assert insert_bits(0xAB00, 0xCD, 7, 0) == 0xABCD
    assert insert_bits(0xFFFF, 0x00, 7, 0) == 0xFF00
    assert insert_bits(0x0000, 0x5, 6, 4) == 0x50


def test_compute_code_modes():
    assert compute_code("offset", 0x80, 3, 2) == 0x85
    assert compute_code("offset", 0x80, -3, 0) == 0x7D
    assert compute_code("absolute", 0, 0x55, 1) == 0x56
    with pytest.raises(ValueError):
        compute_code("unknown", 0, 0)


def test_clamp_code():
    assert clamp_code(300, 7, 0) == (255, True)
    assert clamp_code(-2, 7, 0) == (0, True)
    assert clamp_code(100, 7, 0) == (100, False)


def test_resolve_target_mv_sources():
    rail = _rail()
    assert resolve_target_mv(rail, 0x80) == 1100.0
    rail["target"] = {"source": "derived"}
    assert resolve_target_mv(rail, 32) == pytest.approx(900.0 + 32 * 6.25)


def test_judge_boundary_inclusive():
    err, passed = judge(1.120, 1100.0, 20.0)
    assert err == pytest.approx(20.0)
    assert passed
    _, passed = judge(1.1201, 1100.0, 20.0)
    assert not passed
    err, passed = judge(1.1, 1100.0, 20.0)
    assert err == pytest.approx(0.0)
    assert passed


def test_summarize():
    results = [
        {"passed": True, "err_mv": 5.0},
        {"passed": False, "err_mv": -30.0},
    ]
    s = summarize(results)
    assert s["total"] == 2
    assert s["passed"] == 1
    assert s["failed"] == 1
    assert s["max_abs_err_mv"] == 30.0
    assert not s["overall_pass"]
    assert not summarize([])["overall_pass"]


# ----------------------------------------------------------------------
# 校验
# ----------------------------------------------------------------------

def test_validate_rail_ok():
    validate_rail(_rail())
    validate_rail(_rail(mode="absolute"))
    validate_rail(_rail(target={"source": "derived"}))
    validate_rail(_rail(efuse_field={
        "reg_addr": "0x2", "msb": 4, "lsb": 0, "signed": False, "sign_bit": 5,
    }))


@pytest.mark.parametrize("field", [
    {"reg_addr": "0x2", "msb": 4, "lsb": 0, "sign_bit": 3},
    {"reg_addr": "0x2", "msb": 4, "lsb": 0, "sign_bit": 32},
    {"reg_addr": "0x2", "msb": 4, "lsb": 0, "signed": True, "sign_bit": 5},
])
def test_validate_rail_sign_bit_invalid(field):
    with pytest.raises(ValueError):
        validate_rail(_rail(efuse_field=field))


@pytest.mark.parametrize("override", [
    {"name": ""},
    {"type": "BUCK"},
    {"mode": "relative"},
    {"vbit": {"reg_addr": "0x35", "msb": 0, "lsb": 7}},
    {"vbit": {"reg_addr": "zz", "msb": 7, "lsb": 0}},
    {"efuse_field": {"reg_addr": "0x1", "msb": 32, "lsb": 0}},
    {"tolerance_mv": 0},
    {"step_mv": -1},
    {"target": {"source": "config", "voltage_mv": 0}},
    {"target": {"source": "magic"}},
    {"settle_ms": -5},
    {"offset_lsb": 1.5},
])
def test_validate_rail_invalid(override):
    with pytest.raises(ValueError):
        validate_rail(_rail(**override))


def test_validate_chip_config_ok():
    validate_chip_config(_chip())
    validate_chip_config(_chip(efuse={
        "link": "script", "script_filename": "efuse_1307ph.py",
        "chip_name": "1307ph",
    }))


@pytest.mark.parametrize("override", [
    {"name": ""},
    {"i2c": {"device_addr": "0x27", "width_flag": 16, "speed_khz": 100}},
    {"i2c": {"device_addr": "0x27", "width_flag": 10, "speed_khz": 50}},
    {"efuse": {"link": "magic"}},
    {"efuse": {"link": "script"}},
    {"rails": [_rail(), _rail()]},
])
def test_validate_chip_config_invalid(override):
    with pytest.raises(ValueError):
        validate_chip_config(_chip(**override))


def test_validate_chip_script_link_rejects_88_width():
    chip = _chip(
        i2c={"device_addr": "0x27", "width_flag": 88, "speed_khz": 100},
        efuse={"link": "script", "script_filename": "efuse_1307ph.py"},
    )
    with pytest.raises(ValueError):
        validate_chip_config(chip)


# ----------------------------------------------------------------------
# store
# ----------------------------------------------------------------------

@pytest.fixture()
def tmp_library(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "get_user_data_dir", lambda *sub: str(tmp_path))
    return tmp_path


def test_store_roundtrip(tmp_library):
    assert store.load_library() == []
    chips = [_chip()]
    store.save_library(chips)
    loaded = store.load_library()
    assert loaded == chips


def test_store_corrupt_falls_back(tmp_library):
    path = store.library_path()
    with open(path, "w", encoding="utf-8") as f:
        f.write("{not json")
    assert store.load_library() == []


def test_store_bad_structure_falls_back(tmp_library):
    path = store.library_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"schema_version": 1, "chips": "oops"}, f)
    assert store.load_library() == []


def test_merge_import_conflicts():
    existing = [_chip(name="A"), _chip(name="B")]
    incoming = [_chip(name="B"), _chip(name="C")]
    merged, conflicts = store.merge_import(existing, incoming)
    assert conflicts == ["B"]
    assert [c["name"] for c in merged] == ["A", "B", "C"]
    assert merged[1] is incoming[0]


def test_export_import_file(tmp_library):
    chips = [_chip()]
    path = str(tmp_library / "export.json")
    store.export_chips(chips, path)
    assert store.import_library_file(path) == chips
    with pytest.raises(OSError):
        store.import_library_file(str(tmp_library / "missing.json"))


def test_list_efuse_scripts_contains_known():
    scripts = store.list_efuse_scripts()
    assert "EFUSE_SCRIPTS/efuse_1307ph.py" in scripts
    assert "best1811/efuse_scripts/efuse_1811_pmu.py" in scripts
    assert "best1860/efuse_scripts/efuse_1860_pmu.py" in scripts


def test_resolve_efuse_script():
    legacy = store.resolve_efuse_script("efuse_1307ph.py")
    assert legacy.name == "efuse_1307ph.py"
    assert legacy.parent.name == "EFUSE_SCRIPTS"
    assert legacy.is_file()
    pmu = store.resolve_efuse_script("best1811/efuse_scripts/efuse_1811_pmu.py")
    assert pmu.is_file()
    assert pmu.parent.name == "efuse_scripts"
    backslash = store.resolve_efuse_script("best1860\\efuse_scripts\\efuse_1860_pmu.py")
    assert backslash == store.resolve_efuse_script(
        "best1860/efuse_scripts/efuse_1860_pmu.py")


class _FakeEfuseRaw:
    """模拟 1811/1860 PMU efuse 控制器（0x1a8 控制 / 0x1af 结果）。"""

    def __init__(self, phys):
        self.phys = dict(phys)
        self.regs = {}
        self._latched = 0

    def read(self, speed, dev, reg, width):
        if reg == 0x1AF:
            return self.phys.get(self._latched, 0)
        return self.regs.get(reg, 0)

    def write(self, speed, dev, reg, data, width, high_bit=-1, low_bit=-1):
        cur = self.regs.get(reg, 0)
        if high_bit >= 0 and low_bit >= 0:
            mask = ((1 << (high_bit - low_bit + 1)) - 1) << low_bit
            cur = (cur & ~mask) | ((data << low_bit) & mask)
        else:
            cur = data & 0xFFFF
        self.regs[reg] = cur
        if reg == 0x1A8 and (cur & 0x20):
            self._latched = (cur >> 6) & 0x7F


@pytest.mark.parametrize("script_rel", [
    "best1811/efuse_scripts/efuse_1811_pmu.py",
    "best1860/efuse_scripts/efuse_1860_pmu.py",
])
def test_vendor_pmu_script_read_via_caller(script_rel):
    from lib.i2c.efuse_script_caller import EFuseScriptCaller
    from lib.i2c.i2c_interface_x64 import I2CSpeedMode, I2CWidthFlag

    # 字索引 2 → 物理字节 8..11；低 16bit = 0x0023（幅度 3 + 符号位 1）
    raw = _FakeEfuseRaw({8: 0x23, 9: 0x00, 10: 0x00, 11: 0x00})
    path = store.resolve_efuse_script(script_rel)
    caller = EFuseScriptCaller(raw, efuse_scripts_dir=path.parent)
    ok, value = caller.read_efuse(
        0x17, 0x2, I2CWidthFlag.BIT_10, I2CSpeedMode.SPEED_100K,
        path.name, "test",
    )
    assert ok
    assert value == 0x0023
    assert extract_bits(value, 4, 0, sign_bit=5) == -3

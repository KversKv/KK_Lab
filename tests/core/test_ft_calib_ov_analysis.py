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
    assert "efuse_1307ph.py" in scripts

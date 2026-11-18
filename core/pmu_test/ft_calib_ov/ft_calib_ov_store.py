# -*- coding: utf-8 -*-
"""FT Calibration Check - Output Voltage Check 芯片库持久化（无 Qt）。

存储：``user_data/ft_calib_ov_chips/chip_library.json``（schema_version 包装，
tmp + os.replace 原子写，损坏记日志回落空库）。芯片 → 多 rail 的 schema
由 ft_calib_ov_analysis.validate_chip_config 校验。
"""

import json
import os

from log_config import get_logger
from resource_path import get_resource_base, get_user_data_dir

_logger = get_logger(__name__)

_SCHEMA_VERSION = 1
_DIR_NAME = "ft_calib_ov_chips"
_LIBRARY_FILENAME = "chip_library.json"


def library_path() -> str:
    return os.path.join(get_user_data_dir(_DIR_NAME), _LIBRARY_FILENAME)


def _read_payload(path):
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f) or {}
    chips = payload.get("chips")
    if not isinstance(chips, list):
        raise ValueError(f"Invalid chip library structure: {path}")
    return [c for c in chips if isinstance(c, dict)]


def load_library() -> list:
    """读取芯片库；文件不存在 / 损坏时回落空库，不抛异常。"""
    path = library_path()
    if not os.path.isfile(path):
        return []
    try:
        return _read_payload(path)
    except (OSError, json.JSONDecodeError, ValueError):
        _logger.error("读取芯片库失败: %s", path, exc_info=True)
        return []


def _write_payload(path, chips):
    payload = {"schema_version": _SCHEMA_VERSION, "chips": chips}
    tmp_path = path + ".tmp"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except (OSError, TypeError, ValueError):
        _logger.error("写入芯片库失败: %s", path, exc_info=True)
        try:
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        raise


def save_library(chips) -> None:
    _write_payload(library_path(), list(chips))


def export_chips(chips, path) -> None:
    _write_payload(path, list(chips))


def import_library_file(path) -> list:
    """读取外部芯片库 JSON；结构非法抛 ValueError。"""
    return _read_payload(path)


def merge_import(existing, incoming):
    """按 chip.name 合并导入（重名覆盖）。返回 (合并结果, 冲突芯片名列表)。"""
    merged = list(existing)
    index = {str(c.get("name", "")): i for i, c in enumerate(merged)}
    conflicts = []
    for chip in incoming:
        name = str(chip.get("name", ""))
        if name in index:
            conflicts.append(name)
            merged[index[name]] = chip
        else:
            index[name] = len(merged)
            merged.append(chip)
    return merged, conflicts


def list_efuse_scripts() -> list:
    """扫描 EFUSE_SCRIPTS 目录下的厂商脚本文件名（供管理对话框下拉）。"""
    script_dir = os.path.join(get_resource_base(), "lib", "i2c", "config", "EFUSE_SCRIPTS")
    try:
        return sorted(
            name for name in os.listdir(script_dir)
            if name.endswith(".py") and not name.startswith("_")
        )
    except OSError:
        _logger.error("扫描 EFUSE 脚本目录失败: %s", script_dir, exc_info=True)
        return []

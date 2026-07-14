# I2C 模板 / 序列脚本 / 状态 持久化

import os
import json
import copy
import re

from ui.resource_path import get_user_data_dir
from log_config import get_logger

from ui.modules.IIC_Module.i2c_constants import (
    _i2c_template_dir, _infer_reg_bits,
)

logger = get_logger(__name__)

try:
    import yaml as _yaml
except Exception:
    _yaml = None


# ---------------------------------------------------------------------------
# 序列脚本序列化 / 持久化（YAML，commands 为字符串列表）
# ---------------------------------------------------------------------------

def _i2c_sequence_dir():
    return get_user_data_dir("i2c_sequences")


def _seq_filename_for(name):
    """根据脚本名称生成安全的文件名（不含扩展名）。"""
    safe = re.sub(r'[^\w\-.]', '_', name or "sequence").strip('_')
    if not safe:
        safe = "sequence"
    return safe


def _load_all_sequences():
    """扫描序列目录，返回 [(filepath, script_dict), ...]，按名称排序。"""
    if _yaml is None:
        return []
    result = []
    seq_dir = _i2c_sequence_dir()
    if not os.path.isdir(seq_dir):
        return result
    for fn in os.listdir(seq_dir):
        if not (fn.endswith(".yaml") or fn.endswith(".yml")):
            continue
        path = os.path.join(seq_dir, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = _yaml.safe_load(f)
            if isinstance(data, dict):
                data.setdefault("name", "")
                data.setdefault("description", "")
                data.setdefault("template", "")
                cmds = data.get("commands", []) or []
                data["commands"] = [str(c) for c in cmds]
                result.append((path, data))
        except Exception as e:
            logger.error("Load sequence %s failed: %s", fn, e, exc_info=True)
    result.sort(key=lambda x: str(x[1].get("name", x[0])))
    return result


def _save_sequence_file(script_dict):
    """将脚本 dict 写入 YAML 文件，返回文件路径。"""
    if _yaml is None:
        return None
    name = script_dict.get("name", "sequence")
    seq_dir = _i2c_sequence_dir()
    os.makedirs(seq_dir, exist_ok=True)
    filename = _seq_filename_for(name) + ".yaml"
    path = os.path.join(seq_dir, filename)
    out = {
        "name": str(script_dict.get("name", "")),
        "description": str(script_dict.get("description", "")),
        "template": str(script_dict.get("template", "")),
        "commands": [str(c) for c in script_dict.get("commands", [])],
    }
    with open(path, "w", encoding="utf-8") as f:
        _yaml.dump(out, f, allow_unicode=True, default_flow_style=False,
                   sort_keys=False)
    return path


def _delete_sequence_file(path):
    try:
        if path and os.path.isfile(path):
            os.remove(path)
    except Exception as e:
        logger.error("Delete sequence %s failed: %s", path, e, exc_info=True)


def _serialize_script_yaml(script_dict):
    """脚本 dict → YAML 字符串。"""
    if _yaml is None:
        return ""
    out = {
        "name": str(script_dict.get("name", "")),
        "description": str(script_dict.get("description", "")),
        "template": str(script_dict.get("template", "")),
        "commands": [str(c) for c in script_dict.get("commands", [])],
    }
    return _yaml.dump(out, allow_unicode=True, default_flow_style=False,
                      sort_keys=False)


def _parse_script_yaml(text):
    """YAML 字符串 → 脚本 dict，失败抛异常。"""
    if _yaml is None:
        raise RuntimeError("PyYAML 未安装")
    data = _yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("YAML 顶层必须为字典")
    data.setdefault("name", "")
    data.setdefault("description", "")
    data.setdefault("template", "")
    cmds = data.get("commands", []) or []
    data["commands"] = [str(c) for c in cmds]
    return data


# ---------------------------------------------------------------------------
# 模板（Register Map）持久化（JSON，每文件一模板） + I2C 状态持久化
# ---------------------------------------------------------------------------

def _tpl_filename_for(name):
    """根据模板名称生成安全的文件名（不含扩展名）。"""
    safe = re.sub(r'[^\w\-.]', '_', name or "template").strip('_')
    if not safe:
        safe = "template"
    return safe


def _load_all_templates():
    """扫描模板目录，返回 [(filepath, template_dict), ...]，按名称排序。"""
    result = []
    tpl_dir = _i2c_template_dir()
    if not os.path.isdir(tpl_dir):
        return result
    for fn in os.listdir(tpl_dir):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(tpl_dir, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                continue
            data.setdefault("name", "")
            data.setdefault("device_addr", "0x00")
            data.setdefault("speed_mode", 1)
            data.setdefault("data_bits", 16)
            data.setdefault("reg_bits", _infer_reg_bits(data["data_bits"]))
            data.setdefault("registers", [])
            result.append((path, data))
        except Exception as e:
            logger.error("Load template %s failed: %s", fn, e, exc_info=True)
    result.sort(key=lambda x: str(x[1].get("name", x[0])))
    return result


def _save_template_file(template_dict):
    """将模板 dict 写入 JSON 文件，返回文件路径。"""
    name = template_dict.get("name", "template")
    tpl_dir = _i2c_template_dir()
    os.makedirs(tpl_dir, exist_ok=True)
    filename = _tpl_filename_for(name) + ".json"
    path = os.path.join(tpl_dir, filename)
    out = {
        "name": str(template_dict.get("name", "")),
        "device_addr": str(template_dict.get("device_addr", "0x00")),
        "speed_mode": int(template_dict.get("speed_mode", 1)),
        "data_bits": int(template_dict.get("data_bits", 16)),
        "reg_bits": int(template_dict.get("reg_bits", 16)),
        "registers": copy.deepcopy(template_dict.get("registers", [])),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return path


def _i2c_state_path():
    return os.path.join(get_user_data_dir("i2c_state"), "i2c_state.json")


def _load_i2c_state():
    """加载 I2C 模块持久化状态。返回 dict；不存在或损坏时返回空 dict。"""
    path = _i2c_state_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception as e:
        logger.error("Load i2c state failed: %s", e, exc_info=True)
    return {}


def _save_i2c_state(state):
    """保存 I2C 模块持久化状态到 JSON。"""
    try:
        path = _i2c_state_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Save i2c state failed: %s", e, exc_info=True)

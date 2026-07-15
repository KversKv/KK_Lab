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
    """根据集合名称生成安全的文件名（不含扩展名）。"""
    safe = re.sub(r'[^\w\-.]', '_', name or "sequence").strip('_')
    if not safe:
        safe = "sequence"
    return safe


def _normalize_script(s):
    """规范化单个脚本 dict。"""
    return {
        "name": str(s.get("name", "")),
        "description": str(s.get("description", "")),
        "template": str(s.get("template", "")),
        "commands": [str(c) for c in (s.get("commands", []) or [])],
    }


def _normalize_collection(data):
    """把加载的 YAML dict 规范化为集合 dict。

    新格式：顶层含 scripts 列表，{name, description, scripts:[...]}。
    旧格式：顶层无 scripts 键，视为单脚本集合（向后兼容）。
    返回 None 表示数据非法。
    """
    if not isinstance(data, dict):
        return None
    if "scripts" in data:
        scripts = [_normalize_script(s)
                   for s in (data.get("scripts") or []) if isinstance(s, dict)]
        return {
            "name": str(data.get("name", "")),
            "description": str(data.get("description", "")),
            "scripts": scripts,
        }
    # 旧格式：顶层即单脚本
    script = _normalize_script(data)
    coll_name = (str(data.get("template", "")) or str(data.get("name", ""))
                 or "sequence")
    return {
        "name": coll_name,
        "description": "",
        "scripts": [script],
    }


def _load_all_collections():
    """扫描序列目录，返回 [(filepath, collection_dict), ...]，按集合名排序。

    collection_dict: {name, description, scripts:[script_dict, ...]}
    兼容旧单脚本文件。
    """
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
            coll = _normalize_collection(data)
            if coll is None:
                continue
            if not coll.get("name"):
                coll["name"] = _seq_filename_for(os.path.splitext(fn)[0])
            result.append((path, coll))
        except Exception as e:
            logger.error("Load sequence collection %s failed: %s",
                         fn, e, exc_info=True)
    result.sort(key=lambda x: str(x[1].get("name", x[0])))
    return result


def _load_all_sequences():
    """扁平化返回 [(filepath, script_dict), ...]，供 UI 列表使用。

    每个 script_dict 带有内存态字段 _collection / _collection_path，
    标记脚本所属集合（不持久化到 YAML）。
    """
    result = []
    for path, coll in _load_all_collections():
        coll_name = coll.get("name", "")
        for script in coll.get("scripts", []):
            s = dict(script)
            s["_collection"] = coll_name
            s["_collection_path"] = path
            result.append((path, s))
    result.sort(key=lambda x: (str(x[1].get("_collection", "")),
                               str(x[1].get("name", ""))))
    return result


def _save_collection_file(collection_dict):
    """保存整个集合到 <name>.yaml，返回文件路径。"""
    if _yaml is None:
        return None
    name = collection_dict.get("name", "sequence")
    seq_dir = _i2c_sequence_dir()
    os.makedirs(seq_dir, exist_ok=True)
    filename = _seq_filename_for(name) + ".yaml"
    path = os.path.join(seq_dir, filename)
    out = {
        "name": str(collection_dict.get("name", "")),
        "description": str(collection_dict.get("description", "")),
        "scripts": [_normalize_script(s)
                    for s in collection_dict.get("scripts", [])],
    }
    with open(path, "w", encoding="utf-8") as f:
        _yaml.dump(out, f, allow_unicode=True, default_flow_style=False,
                   sort_keys=False)
    return path


def _save_sequence_file(script_dict, collection_name=None):
    """将脚本 upsert 到指定集合文件。

    collection_name 为 None/空时，取 script.template 或 script.name。
    集合文件名 = _seq_filename_for(collection_name) + '.yaml'。
    若集合已存在，按 script.name 替换或追加；不存在则新建。
    返回集合文件路径。
    """
    if _yaml is None:
        return None
    script = _normalize_script(script_dict)
    name = script.get("name", "").strip()
    if collection_name is None or not str(collection_name).strip():
        collection_name = (str(script.get("template", "")) or name
                           or "sequence")
    collection_name = str(collection_name).strip()
    seq_dir = _i2c_sequence_dir()
    filename = _seq_filename_for(collection_name) + ".yaml"
    path = os.path.join(seq_dir, filename)
    coll = {"name": collection_name, "description": "", "scripts": []}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = _yaml.safe_load(f)
            normalized = _normalize_collection(data)
            if normalized is not None:
                coll = normalized
                if not coll.get("name"):
                    coll["name"] = collection_name
        except Exception as e:
            logger.error("Load collection for upsert failed: %s",
                         e, exc_info=True)
    # upsert：按 name 替换或追加
    scripts = coll.get("scripts", [])
    found = False
    for i, s in enumerate(scripts):
        if str(s.get("name", "")) == name:
            scripts[i] = script
            found = True
            break
    if not found:
        scripts.append(script)
    coll["scripts"] = scripts
    return _save_collection_file(coll)


def _delete_sequence_file(filepath, script_name=None):
    """从集合文件移除脚本；集合空则删文件。

    script_name 为 None 时直接删整个文件（向后兼容旧调用）。
    """
    try:
        if not filepath or not os.path.isfile(filepath):
            return
        if script_name is None:
            os.remove(filepath)
            return
        with open(filepath, "r", encoding="utf-8") as f:
            data = _yaml.safe_load(f)
        coll = _normalize_collection(data)
        if coll is None:
            return
        scripts = [s for s in coll.get("scripts", [])
                   if str(s.get("name", "")) != script_name]
        if not scripts:
            os.remove(filepath)
        else:
            coll["scripts"] = scripts
            _save_collection_file(coll)
    except Exception as e:
        logger.error("Delete sequence failed: %s", e, exc_info=True)


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

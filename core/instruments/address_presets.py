"""实验室仪器地址预设读取（resources/instrument_addresses.json 单一事实源）。

地址禁硬编码：驱动层一律强制传参；UI 预填（扫描前默认项）统一经本模块读取，
预设缺失时返回空串，由用户扫描 / 手输。
"""
import json
import os

from log_config import get_logger
from resource_path import get_resource_base

logger = get_logger(__name__)

_cache = None


def _load() -> dict:
    global _cache
    if _cache is None:
        path = os.path.join(get_resource_base(), "resources", "instrument_addresses.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                _cache = json.load(f)
        except (OSError, ValueError) as e:
            logger.warning("仪器地址预设读取失败(%s)，按空预设处理", e)
            _cache = {}
    return _cache


def get_address_preset(group: str, key: str, default: str = "") -> str:
    """读取预设地址，如 get_address_preset("n6705c", "A")；缺失返回 default。"""
    value = _load().get(group, {}).get(key, default)
    return str(value) if value else default

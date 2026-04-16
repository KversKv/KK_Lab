import os
import importlib

_CHIPS_DIR = os.path.dirname(os.path.abspath(__file__))

SUPPORTED_CHIPS = [
    "bes1000",
    "bes1305",
    "bes1305_dcdc",
    "bes1306",
    "bes1306p",
    "bes1307",
    "bes1307p",
    "bes1307ph",
    "bes1307s",
    "bes1400",
    "bes1501",
    "bes1501p",
    "bes1502p",
    "bes1502p_earphone",
    "bes1502p_watch",
    "bes1502x",
    "bes1502x_2600zp",
    "bes1502x_2700h",
    "bes1502x_2700ibp",
    "bes1502x_2700L",
    "bes1503",
    "bes1600",
    "bes1603",
    "bes1605",
    "bes1607",
    "bes1700",
    "bes1702",
    "bes2000",
    "bes2001",
    "bes2002",
    "bes2003",
    "bes2007",
    "bes2009",
    "bes2300",
    "bes2300a",
    "bes2300p",
    "bes3601p",
]


def get_chip_config(chip_name):
    module_name = f"chips.bes_chip_configs.{chip_name}"
    try:
        mod = importlib.import_module(module_name)
        return mod.CHIP_CONFIG
    except (ModuleNotFoundError, AttributeError):
        return None


def get_all_chip_configs():
    configs = {}
    for name in SUPPORTED_CHIPS:
        cfg = get_chip_config(name)
        if cfg:
            configs[name] = cfg
    return configs

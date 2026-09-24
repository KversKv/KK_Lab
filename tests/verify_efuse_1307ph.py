#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 efuse_1307ph.py 在实机 1307ph 上的 eFuse 读取流程

流程:
    1. bes_chip_check() 确认当前连接芯片为 BES1307PH
    2. 通过 EFuseScriptCaller 调用 efuse_1307ph.py 的 read_efuse(0x0001)
    3. 校验返回值是否为预期 0x0003

用法:
    python tests/verify_efuse_1307ph.py
"""

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
I2C_DIR = PROJECT_ROOT / "lib" / "i2c"
sys.path.insert(0, str(I2C_DIR))

from Bes_I2CIO_Interface import I2CSpeedMode, I2CWidthFlag  # noqa: E402
from efuse_script_caller import EFuseScriptCaller  # noqa: E402
from i2c_interface_x64 import I2CInterface  # noqa: E402

logger = logging.getLogger("verify_efuse_1307ph")

EFUSE_OFFSET = 0x0001
EXPECTED_VALUE = 0x0003
EFUSE_DEVICE_ADDR = 0x27
EFUSE_DATA_WIDTH = I2CWidthFlag.BIT_10
EFUSE_SCRIPT = "efuse_1307ph.py"
EFUSE_CHIP_NAME = "1307ph"


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
    )

    # 1. 芯片检测，确认连接的是 1307ph
    i2c = I2CInterface()
    try:
        chip_info = i2c.bes_chip_check()
    except Exception:
        logger.error("芯片检测失败，请确认 I2C 连接与芯片上电状态", exc_info=True)
        return 1

    logger.info(
        "芯片检测: main_die=%s(%s) main_die_pmu=%s pmu=%s warning=%s",
        chip_info["main_die"], chip_info["main_die_version"],
        chip_info["main_die_pmu"], chip_info["pmu"], chip_info["warning"],
    )
    if chip_info["main_die"] != "BES1307PH":
        logger.error("当前 main_die=%s，非 BES1307PH，终止验证", chip_info["main_die"])
        return 1

    # 2. 调用 efuse_1307ph.py 读取 eFuse 偏移 0x0001
    caller = EFuseScriptCaller(i2c.raw)
    success, value = caller.read_efuse(
        EFUSE_DEVICE_ADDR,
        EFUSE_OFFSET,
        EFUSE_DATA_WIDTH,
        I2CSpeedMode.SPEED_100K,
        EFUSE_SCRIPT,
        EFUSE_CHIP_NAME,
    )

    logger.info(
        "read_efuse 返回: success=%s value=%s",
        success, "0x%04X" % value if isinstance(value, int) and value >= 0 else value,
    )
    if not success:
        logger.error("eFuse 脚本调用失败")
        return 1

    # 3. 校验读取值
    if value == EXPECTED_VALUE:
        logger.info(
            "验证通过: eFuse[0x%04X] = 0x%04X，与预期一致", EFUSE_OFFSET, value,
        )
        return 0

    logger.error(
        "验证失败: eFuse[0x%04X] = 0x%04X，预期 0x%04X",
        EFUSE_OFFSET, value if isinstance(value, int) else -1, EXPECTED_VALUE,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from instruments.power.keysight.n6705c import N6705C
from log_config import get_logger, setup_logging

logger = get_logger(__name__)


def main():
    setup_logging(level=logging.INFO)

    resource = os.environ.get("KK_LAB_N6705C_RESOURCE", "").strip()
    if not resource:
        raise ValueError("请先设置 KK_LAB_N6705C_RESOURCE 环境变量")

    channel = 1
    original_mode = None
    visa_library = os.environ.get("KK_LAB_N6705C_VISA_LIBRARY", "").strip() or None
    n6705c = N6705C(resource, visa_library=visa_library)
    try:
        idn = n6705c.instr.query("*IDN?").strip()
        logger.info("已连接: %s", idn)

        original_mode = n6705c.instr.query(
            f"VOLT:SENS:SOUR? (@{channel})"
        ).strip().upper()
        logger.info("CH%d 原始 Sense 模式: %s", channel, original_mode)

        for mode, expected in (("Local", "INT"), ("4 Wire", "EXT")):
            n6705c.set_sense_mode(channel, mode)
            actual = n6705c.instr.query(
                f"VOLT:SENS:SOUR? (@{channel})"
            ).strip().upper()
            if actual != expected:
                raise AssertionError(
                    f"CH{channel} {mode} 模式验证失败: "
                    f"期望 {expected}, 实际 {actual}"
                )
            logger.info(
                "PASS: CH%d set_sense_mode('%s') -> %s",
                channel, mode, actual,
            )
    finally:
        try:
            if original_mode in ("INT", "EXT"):
                n6705c.set_sense_mode(channel, original_mode)
                logger.info("已恢复 CH%d 原始 Sense 模式: %s", channel, original_mode)
        finally:
            n6705c.disconnect()
            logger.info("已断开连接")


if __name__ == "__main__":
    main()

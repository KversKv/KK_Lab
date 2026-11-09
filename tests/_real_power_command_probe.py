#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
from unittest.mock import patch

import debug_config
from instruments.factory import create_power_analyzer
from log_config import get_logger, setup_logging

logger = get_logger("real_power_command_probe")

COMMANDS = (
    ":SYSTem:CHANnel:STATus? (@1,2,3,4,5,6,7,8)",
    ":SYSTem:CHANnel:STATus? (@1)",
    ":SYSTem:CHANnel:STATus? (@4)",
    ":SYSTem:CHANnel:MODel? (@1)",
    "SYSTem:CHANnel:MODel? (@1)",
    "SYST:MOD:SLOT1?",
    "SOUR:CHAN:IDN? 1",
    "SOUR:CHAN:IDN? (@1)",
    "SYST:MOD:INFO? (@1)",
    "SYST:CHAN:INFO? (@1)",
    "SYST:INFO?",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("resource")
    args = parser.parse_args()

    setup_logging(logging.INFO)
    debug_config.DEBUG_MOCK = False
    instance = None
    try:
        with patch(
            "instruments.power.keysight.n6705c.N6705C.refresh_channel_modules",
            return_value={},
        ), patch(
            "instruments.power.itech.it2705.IT2705.refresh_channel_modules",
            return_value={},
        ):
            instance = create_power_analyzer(args.resource, analyzer_type="auto")
        instance.instr.timeout = 2000
        logger.info("COMMAND_PROBE resource=%s", args.resource)
        logger.info("COMMAND_PROBE IDN=%s", instance.instr.query("*IDN?").strip())
        for command in COMMANDS:
            try:
                response = instance.instr.query(command)
                logger.info("COMMAND_PROBE %r -> %r", command, response)
            except Exception as exc:
                logger.info("COMMAND_PROBE %r -> %s", command, exc)
                try:
                    error = instance.instr.query("SYST:ERR?")
                    logger.info("COMMAND_PROBE SYST:ERR? -> %r", error)
                except Exception as error_exc:
                    logger.info("COMMAND_PROBE SYST:ERR? -> %s", error_exc)
    finally:
        if instance is not None:
            instance.disconnect()
            logger.info("COMMAND_PROBE disconnected")


if __name__ == "__main__":
    main()

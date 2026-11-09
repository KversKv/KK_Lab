#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging

import debug_config
from instruments.factory import create_power_analyzer, get_power_analyzer_idn
from log_config import get_logger, setup_logging

logger = get_logger("real_power_module_probe")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("resource")
    args = parser.parse_args()

    setup_logging(logging.INFO)
    debug_config.DEBUG_MOCK = False
    instance = None
    try:
        instance = create_power_analyzer(args.resource, analyzer_type="auto")
        idn = get_power_analyzer_idn(instance)
        models = dict(instance.channel_module_models)
        logger.info("REAL_PROBE resource=%s", args.resource)
        logger.info("REAL_PROBE IDN=%s", idn)
        for channel in instance.VALID_CHANNELS:
            if models.get(channel, ""):
                try:
                    raw = instance.instr.query(f":SYSTem:CHANnel:MODel? (@{channel})")
                except Exception as exc:
                    raw = f"ERROR: {exc}"
                    logger.warning(
                        "REAL_PROBE CH%d raw query failed", channel, exc_info=True
                    )
            else:
                raw = "SKIPPED (no installed module)"
            logger.info(
                "REAL_PROBE CH%d raw=%r normalized=%r supported=%s",
                channel,
                raw,
                models.get(channel, ""),
                instance.is_channel_supported(channel),
            )
        supported = [
            channel for channel in instance.VALID_CHANNELS
            if instance.is_channel_supported(channel)
        ]
        logger.info("REAL_PROBE supported_channels=%s", supported)
    except Exception:
        logger.error("REAL_PROBE failed resource=%s", args.resource, exc_info=True)
        raise
    finally:
        if instance is not None:
            try:
                instance.disconnect()
                logger.info("REAL_PROBE disconnected resource=%s", args.resource)
            except Exception:
                logger.error(
                    "REAL_PROBE disconnect failed resource=%s",
                    args.resource,
                    exc_info=True,
                )


if __name__ == "__main__":
    main()

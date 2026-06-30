"""CMW500 测试用例入口。

运行方式 (项目根目录下)::

    python -m instruments.wirelessConnectivityTester.rohde_schwarz.cmw500

覆盖 BT (BR/EDR) / BLE / LTE (FDD+TDD) / WIFI 四大制式, 包含信令小区配置、
上行 TX 测量、PER / 吞吐量等完整测试流程。
"""

import os
import sys

if __package__ is None or __package__ == "":
    _PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from instruments.wirelessConnectivityTester.rohde_schwarz.cmw500 import CMW500
from log_config import get_logger, setup_logging

logger = get_logger(__name__)

DEFAULT_RESOURCE = "TCPIP0::10.31.31.236::hislip0::INSTR"


def test_base(cmw):
    """基础信息与系统状态。"""
    logger.info("==== [BASE] 基础信息 ====")
    logger.info("已连接: %s", cmw.identify())
    logger.info("固件版本: %s", cmw.get_firmware_version())
    logger.info("已安装选件: %s", cmw.get_options())
    cmw.clear_status()


def test_bt(cmw):
    """BT (BR/EDR) 非信令 TX 测量 + 信令配置演示。"""
    logger.info("==== [BT] BR/EDR 测量 ====")
    cmw.bt_reset()
    cmw.bt_set_rf_input("RF1C", attenuation_db=0.0)

    # —— BR DH1 测量 ——
    cmw.bt_set_demod_mode("BRATe")
    cmw.bt_set_packet_type("DH1")
    cmw.bt_set_payload_length(37)
    cmw.bt_set_pattern("PRBS9")
    cmw.bt_set_channel(0)
    cmw.bt_set_expected_power(0)
    cmw.bt_set_repetition("SINGleshot")
    cmw.bt_set_meas_count(10)
    cmw.bt_init_meval()
    if cmw.wait_for_ready(cmw.BT_MEAS + ":MEValuation", timeout_s=10):
        logger.info("  BR 平均功率: %.3f dBm", cmw.bt_get_average_power_dbm())
        logger.info("  调制结果: %s", cmw.bt_fetch_modulation())

    # —— EDR 2Mbps 测量 ——
    logger.info("[BT] EDR 2Mbps (2DH1)")
    cmw.bt_set_demod_mode("EDRate")
    cmw.bt_set_packet_type("2DH1")
    cmw.bt_set_channel(10)
    cmw.bt_set_repetition("SINGleshot")
    cmw.bt_init_meval()
    if cmw.wait_for_ready(cmw.BT_MEAS + ":MEValuation", timeout_s=10):
        logger.info("  EDR 平均功率: %.3f dBm", cmw.bt_get_average_power_dbm())
        logger.info("  DEVM: %s", cmw.bt_fetch_edr_modulation())

    # —— 信令配置演示 (不实际建链) ——
    logger.info("[BT] 信令配置 (TX 功率 / 测试模式)")
    cmw.bt_set_tx_power(-50)
    cmw.bt_set_test_mode("LOOPback")
    logger.info("  TX 功率: %.1f dBm", cmw.bt_get_tx_power())
    logger.info("  测试模式: %s", cmw.bt_get_test_mode())


def test_ble(cmw):
    """BLE (LE1M / LE2M / LE Coded) 非信令 TX 测量。"""
    logger.info("==== [BLE] 低功耗蓝牙测量 ====")
    cmw.ble_reset()
    cmw.ble_set_rf_input("RF1C", attenuation_db=0.0)

    # —— LE1M ——
    logger.info("[BLE] LE1M, 信道 0")
    cmw.ble_set_phy("LE1M")
    cmw.ble_set_packet_type("RFPHytest")
    cmw.ble_set_payload_length(37)
    cmw.ble_set_pattern("ALL1")
    cmw.ble_set_channel(0)
    cmw.ble_set_expected_power(0)
    cmw.ble_set_repetition("SINGleshot")
    cmw.ble_init_meval()
    if cmw.wait_for_ready(cmw.BLE_MEAS + ":MEValuation", timeout_s=10):
        logger.info("  平均功率: %.3f dBm", cmw.ble_get_average_power_dbm())
        logger.info("  调制结果: %s", cmw.ble_fetch_modulation())
        logger.info("  频率精度: %s", cmw.ble_fetch_freq_accuracy())

    # —— LE Coded (S=8) ——
    logger.info("[BLE] LE Coded (LELR), 信道 10")
    cmw.ble_set_phy("LELR")
    cmw.ble_set_channel(10)
    cmw.ble_set_repetition("SINGleshot")
    cmw.ble_init_meval()
    if cmw.wait_for_ready(cmw.BLE_MEAS + ":MEValuation", timeout_s=10):
        logger.info("  LE Coded 平均功率: %.3f dBm", cmw.ble_get_average_power_dbm())

    # —— 连接参数 / 广播配置演示 ——
    logger.info("[BLE] 连接参数与广播配置")
    cmw.ble_set_connection_interval(30.0)
    cmw.ble_set_connection_latency(0)
    cmw.ble_set_connection_timeout(1000.0)
    cmw.ble_set_advertising_type("ADVIND")
    cmw.ble_set_advertising_interval(100.0)
    logger.info("  连接间隔: %.1f ms", cmw.ble_get_connection_interval())


def test_wifi(cmw):
    """WLAN (11n / 11ac / 11ax) 非信令 TX 测量。"""
    logger.info("==== [WIFI] WLAN 测量 ====")
    cmw.wifi_reset()
    cmw.wifi_set_rf_input("RF1C", attenuation_db=0.0)

    # —— 11n HT20 ——
    logger.info("[WIFI] 11n, BW20, 信道 6")
    cmw.wifi_set_standard("HTOFdm")
    cmw.wifi_set_bandwidth("BW20")
    cmw.wifi_set_mcs(7)
    cmw.wifi_set_spatial_streams(1)
    cmw.wifi_set_guard_interval("GI400")
    cmw.wifi_set_channel(6, "B24G")
    cmw.wifi_set_expected_power(0)
    cmw.wifi_set_repetition("SINGleshot")
    cmw.wifi_set_bursts_count(10)
    cmw.wifi_init_meval()
    if cmw.wait_for_ready(cmw.WIFI_MEAS + ":MEValuation", timeout_s=10):
        logger.info("  平均功率: %.3f dBm", cmw.wifi_get_average_power_dbm())
        logger.info("  EVM: %s", cmw.wifi_fetch_evm())
        logger.info("  频谱模板: %s", cmw.wifi_fetch_spectrum())

    # —— 11ax HE80 ——
    logger.info("[WIFI] 11ax, BW80, 信道 100")
    cmw.wifi_set_standard("HEOFdm")
    cmw.wifi_set_bandwidth("BW80")
    cmw.wifi_set_mcs(9)
    cmw.wifi_set_channel(100, "B5G")
    cmw.wifi_set_repetition("SINGleshot")
    cmw.wifi_init_meval()
    if cmw.wait_for_ready(cmw.WIFI_MEAS + ":MEValuation", timeout_s=10):
        logger.info("  11ax 平均功率: %.3f dBm", cmw.wifi_get_average_power_dbm())
        logger.info("  中心频偏: %s", cmw.wifi_fetch_center_freq_error())
        logger.info("  时钟误差: %s", cmw.wifi_fetch_clock_error())

    # —— 信令 AP 配置演示 ——
    logger.info("[WIFI] 信令 AP 配置")
    cmw.wifi_set_operation_mode("AP")
    cmw.wifi_set_ssid("CMW500_AP")
    cmw.wifi_set_security("WPA2")
    cmw.wifi_set_tx_power(-50)
    logger.info("  模式: %s, SSID: %s", cmw.wifi_get_operation_mode(), cmw.wifi_get_ssid())


def test_lte(cmw):
    """LTE 信令小区配置 (FDD + TDD) + 上行测量。"""
    logger.info("==== [LTE] 信令与上行测量 ====")
    cmw.lte_reset()

    # —— FDD Band1 配置 ——
    logger.info("[LTE] FDD Band1 小区配置")
    cmw.lte_set_duplex_mode("FDD")
    cmw.lte_set_band("OB1")
    cmw.lte_set_dl_channel(100)
    cmw.lte_set_bandwidth("B100")
    cmw.lte_set_cell_id(100)
    cmw.lte_set_dl_power(-80)
    cmw.lte_set_expected_ul_power(23)
    cmw.lte_set_transmission_mode(1)
    cmw.lte_set_ul_modulation("QPSK")
    cmw.lte_set_ul_rb(25, 0)
    cmw.lte_set_imsi("001010000000000")
    logger.info("  双工: %s, 频段: %s", cmw.lte_get_duplex_mode(), cmw.lte_get_band())
    logger.info("  DL EARFCN: %d, PCI: %d", cmw.lte_get_dl_channel(), cmw.lte_get_cell_id())
    logger.info("  小区状态: %s", cmw.lte_cell_state())

    # —— TDD Band38 配置演示 ——
    logger.info("[LTE] TDD Band38 配置演示")
    cmw.lte_set_duplex_mode("TDD")
    cmw.lte_set_band("OB38")
    cmw.lte_set_dl_channel(38950)
    cmw.lte_set_bandwidth("B100")
    cmw.lte_set_tdd_uldl_config(2)
    cmw.lte_set_tdd_special_subframe(7)
    logger.info("  双工: %s", cmw.lte_get_duplex_mode())

    # —— 上行测量 (切回 FDD Band1) ——
    logger.info("[LTE] 上行 TX 测量")
    cmw.lte_set_meas_connector("RF1C")
    cmw.lte_set_meas_frequency(1_950_000_000)
    cmw.lte_set_meas_bandwidth("B100")
    cmw.lte_set_meas_expected_power(23)
    cmw.lte_init_meval()
    if cmw.wait_for_ready(cmw.LTE_MEAS + ":MEValuation", timeout_s=15):
        logger.info("  TX 功率: %s", cmw.lte_fetch_tx_power())
        logger.info("  EVM: %s", cmw.lte_fetch_evm())
        logger.info("  ACLR: %s", cmw.lte_fetch_spectrum())
        logger.info("  SEM: %s", cmw.lte_fetch_spectrum_emask())
        logger.info("  IQ 偏移: %s", cmw.lte_fetch_iq_offset())


def main():
    setup_logging()

    cmw = CMW500(DEFAULT_RESOURCE)
    try:
        test_base(cmw)
        test_bt(cmw)
        test_ble(cmw)
        test_wifi(cmw)
        test_lte(cmw)

        errs = cmw.get_errors()
        logger.info("==== 错误队列: %s ====", errs)
    except Exception:
        logger.error("CMW500 测试用例异常", exc_info=True)
    finally:
        cmw.disconnect()
        logger.info("已断开连接")


if __name__ == "__main__":
    main()

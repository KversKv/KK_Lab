"""CMW270 测试用例入口。

运行方式 (项目根目录下)::

    python -m instruments.wirelessConnectivityTester.rohde_schwarz.cmw270

覆盖 BT (BR/EDR) / BLE / LTE / WIFI 四大制式的非信令 TX 测量与信令配置演示。
"""

import os
import sys

if __package__ is None or __package__ == "":
    _PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from instruments.wirelessConnectivityTester.rohde_schwarz.cmw270 import CMW270
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
    """BT (BR/EDR) 非信令 TX 测量。"""
    logger.info("==== [BT] BR/EDR 测量 ====")
    cmw.bt_reset()
    cmw.bt_set_rf_input("RF1C", attenuation_db=0.0)
    cmw.bt_set_demod_mode("BRATe")
    cmw.bt_set_packet_type("DH1")
    logger.info("  数据包类型: %s", cmw.bt_get_packet_type())
    cmw.bt_set_payload_length(37)
    cmw.bt_set_pattern("PRBS9")
    cmw.bt_set_channel(0)
    logger.info("  中心频率: %.0f Hz", cmw.bt_get_frequency())
    cmw.bt_set_expected_power(0)
    cmw.bt_set_user_margin(0)
    cmw.bt_set_repetition("SINGleshot")
    cmw.bt_set_meas_count(10)
    cmw.bt_init_meval()
    if cmw.wait_for_ready(cmw.BT_MEAS + ":MEValuation", timeout_s=10):
        logger.info("  平均功率: %.3f dBm", cmw.bt_get_average_power_dbm())
        logger.info("  调制结果: %s", cmw.bt_fetch_modulation())
        logger.info("  频偏结果: %s", cmw.bt_fetch_freq_offset())
        logger.info("  20dB 带宽: %s", cmw.bt_fetch_20db_bandwidth())

    # —— EDR 3Mbps 测量 ——
    logger.info("[BT] EDR 3Mbps 测量")
    cmw.bt_set_demod_mode("EDRate")
    cmw.bt_set_packet_type("3DH1")
    cmw.bt_set_repetition("SINGleshot")
    cmw.bt_init_meval()
    if cmw.wait_for_ready(cmw.BT_MEAS + ":MEValuation", timeout_s=10):
        logger.info("  平均功率: %.3f dBm", cmw.bt_get_average_power_dbm())
        logger.info("  EVM (DEVM): %s", cmw.bt_fetch_edr_modulation())


def test_ble(cmw):
    """BLE (LE1M / LE2M) 非信令 TX 测量。"""
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
    cmw.ble_set_meas_count(10)
    cmw.ble_init_meval()
    if cmw.wait_for_ready(cmw.BLE_MEAS + ":MEValuation", timeout_s=10):
        logger.info("  平均功率: %.3f dBm", cmw.ble_get_average_power_dbm())
        logger.info("  调制结果: %s", cmw.ble_fetch_modulation())
        logger.info("  频率精度: %s", cmw.ble_fetch_freq_accuracy())

    # —— LE2M ——
    logger.info("[BLE] LE2M, 信道 19")
    cmw.ble_set_phy("LE2M")
    cmw.ble_set_channel(19)
    cmw.ble_set_repetition("SINGleshot")
    cmw.ble_init_meval()
    if cmw.wait_for_ready(cmw.BLE_MEAS + ":MEValuation", timeout_s=10):
        logger.info("  平均功率: %.3f dBm", cmw.ble_get_average_power_dbm())


def test_wifi(cmw):
    """WLAN (11n / 11ac) 非信令 TX 测量。"""
    logger.info("==== [WIFI] WLAN 测量 ====")
    cmw.wifi_reset()
    cmw.wifi_set_rf_input("RF1C", attenuation_db=0.0)

    # —— 11n HT20 ——
    logger.info("[WIFI] 11n, BW20, 信道 6")
    cmw.wifi_set_standard("HTOFdm")
    cmw.wifi_set_bandwidth("BW20")
    cmw.wifi_set_mcs(0)
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
        logger.info("  频率误差: %s", cmw.wifi_fetch_center_freq_error())
        logger.info("  频谱模板: %s", cmw.wifi_fetch_spectrum())

    # —— 11ac VHT80 ——
    logger.info("[WIFI] 11ac, BW80, 信道 36")
    cmw.wifi_set_standard("VHTOfdm")
    cmw.wifi_set_bandwidth("BW80")
    cmw.wifi_set_mcs(7)
    cmw.wifi_set_channel(36, "B5G")
    cmw.wifi_set_repetition("SINGleshot")
    cmw.wifi_init_meval()
    if cmw.wait_for_ready(cmw.WIFI_MEAS + ":MEValuation", timeout_s=10):
        logger.info("  平均功率: %.3f dBm", cmw.wifi_get_average_power_dbm())
        logger.info("  频谱平坦度: %s", cmw.wifi_fetch_spectrum_flatness())


def test_lte(cmw):
    """LTE 信令小区配置 + 上行测量。"""
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
    logger.info("  双工模式: %s", cmw.lte_get_duplex_mode())
    logger.info("  频段: %s, DL EARFCN: %d", cmw.lte_get_band(), cmw.lte_get_dl_channel())
    logger.info("  小区状态: %s", cmw.lte_cell_state())

    # —— 上行测量 (Standalone) ——
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
        logger.info("  频率误差: %s", cmw.lte_fetch_freq_error())


def main():
    setup_logging()

    cmw = CMW270(DEFAULT_RESOURCE)
    try:
        test_base(cmw)
        test_bt(cmw)
        test_ble(cmw)
        test_wifi(cmw)
        test_lte(cmw)

        errs = cmw.get_errors()
        logger.info("==== 错误队列: %s ====", errs)
    except Exception:
        logger.error("CMW270 测试用例异常", exc_info=True)
    finally:
        cmw.disconnect()
        logger.info("已断开连接")


if __name__ == "__main__":
    main()

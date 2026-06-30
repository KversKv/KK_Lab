"""CMW 低功耗蓝牙 (Bluetooth LE) 测量与信令指令 Mixin。"""

from log_config import get_logger

logger = get_logger(__name__)


class BluetoothLEMixin:
    """Bluetooth Low Energy (LE 1M / LE 2M / LE Coded) 信令与非信令测量。

    依赖宿主类提供 write / query / query_float / query_int / query_values /
    init_measurement / fetch / read 等基础 IO 方法 (见 CMWBase)。
    """

    BLE_MEAS = "BLUetooth:MEASurement"
    BLE_SIGN = "BLUetooth:SIGNaling"

    # =========================
    # 通用配置 / 复位
    # =========================

    def ble_reset(self):
        """复位 BLE 测量与信令状态。"""
        self.write(f"SOURce:{self.BLE_SIGN}:STATe OFF")
        self.write(f"ABORt:{self.BLE_MEAS}:MEValuation")

    def ble_set_phy(self, phy="LE1M"):
        """物理层: LE1M / LE2M / LELR (LE Coded)。"""
        self.write(f"CONFigure:{self.BLE_MEAS}:MEValuation:PHY {phy}")

    def ble_get_phy(self):
        return self.query(f"CONFigure:{self.BLE_MEAS}:MEValuation:PHY?").strip()

    def ble_set_packet_type(self, packet_type="RFPHytest"):
        """LE 数据包类型: RFPHytest / ADVertiser。"""
        self.write(f"CONFigure:{self.BLE_MEAS}:MEValuation:PATTern {packet_type}")

    def ble_get_packet_type(self):
        return self.query(f"CONFigure:{self.BLE_MEAS}:MEValuation:PATTern?").strip()

    def ble_set_payload_length(self, length):
        """设置有效载荷长度 (0~255 字节)。"""
        self.write(f"CONFigure:{self.BLE_MEAS}:MEValuation:PLENgth {int(length)}")

    def ble_get_payload_length(self):
        return self.query_int(f"CONFigure:{self.BLE_MEAS}:MEValuation:PLENgth?")

    def ble_set_pattern(self, pattern="ALL1"):
        """有效载荷数据模式: ALL0 / ALL1 / P11 / P44 / PRBS9 / F0 / FF 等。"""
        self.write(f"CONFigure:{self.BLE_MEAS}:MEValuation:PDPattern {pattern}")

    def ble_get_pattern(self):
        return self.query(f"CONFigure:{self.BLE_MEAS}:MEValuation:PDPattern?").strip()

    def ble_set_trigger(self, source="IFPower"):
        """设置测量触发源: IFPower / FreeRun / Baseband。"""
        self.write(f"TRIGger:{self.BLE_MEAS}:MEValuation:SOURce {source}")

    def ble_set_trigger_level(self, level_dbm=-20):
        self.write(f"TRIGger:{self.BLE_MEAS}:MEValuation:LEVel {level_dbm}")

    # =========================
    # RF 设置
    # =========================

    def ble_set_rf_input(self, connector="RF1C", attenuation_db=0.0):
        """设置 RF 输入连接器与外部衰减。"""
        self.write(f"CONFigure:{self.BLE_MEAS}:RFSettings:CONNector {connector}")
        self.write(f"CONFigure:{self.BLE_MEAS}:RFSettings:EATTenuation {attenuation_db}")

    def ble_get_rf_connector(self):
        return self.query(f"CONFigure:{self.BLE_MEAS}:RFSettings:CONNector?").strip()

    def ble_set_frequency(self, freq_hz):
        """直接设置中心频率 (Hz)。"""
        self.write(f"CONFigure:{self.BLE_MEAS}:RFSettings:FREQuency {freq_hz}")

    def ble_get_frequency(self):
        return self.query_float(f"CONFigure:{self.BLE_MEAS}:RFSettings:FREQuency?")

    @staticmethod
    def ble_channel_to_freq_hz(channel):
        """BLE 信道 (0~39) 转中心频率 (Hz)。

        信道 0~12:  2402 + 2*k   MHz (k=channel)
        信道 13~38: 2426 + 2*(k-13) MHz
        信道 39:    2480 MHz
        """
        ch = int(channel)
        if ch == 39:
            return 2_480_000_000
        if ch <= 12:
            return int((2402 + 2 * ch) * 1_000_000)
        return int((2426 + 2 * (ch - 13)) * 1_000_000)

    def ble_set_channel(self, channel):
        """设置 LE 信道 (0~39)。"""
        self.write(f"CONFigure:{self.BLE_MEAS}:RFSettings:CHANnel {int(channel)}")

    def ble_get_channel(self):
        return self.query_int(f"CONFigure:{self.BLE_MEAS}:RFSettings:CHANnel?")

    def ble_set_expected_power(self, power_dbm):
        """设置期望输入功率 (dBm)。"""
        self.write(f"CONFigure:{self.BLE_MEAS}:RFSettings:ENPMode MANual")
        self.write(f"CONFigure:{self.BLE_MEAS}:RFSettings:ENPower {power_dbm}")

    def ble_get_expected_power(self):
        return self.query_float(f"CONFigure:{self.BLE_MEAS}:RFSettings:ENPower?")

    def ble_set_expected_power_auto(self, auto=True):
        """使能/关闭期望功率自动估算。"""
        state = "ON" if auto else "OFF"
        self.write(f"CONFigure:{self.BLE_MEAS}:RFSettings:RFEPower:AUTO {state}")

    def ble_set_user_margin(self, margin_db=0.0):
        """设置用户余量 (dB)。"""
        self.write(f"CONFigure:{self.BLE_MEAS}:RFSettings:UMARgin {margin_db}")

    def ble_get_user_margin(self):
        return self.query_float(f"CONFigure:{self.BLE_MEAS}:RFSettings:UMARgin?")

    # =========================
    # 测量控制
    # =========================

    def ble_set_repetition(self, mode="SINGleshot"):
        """重复模式: SINGleshot / CONTinuous。"""
        self.write(f"CONFigure:{self.BLE_MEAS}:MEValuation:REPetition {mode}")

    def ble_get_repetition(self):
        return self.query(f"CONFigure:{self.BLE_MEAS}:MEValuation:REPetition?").strip()

    def ble_set_meas_count(self, count):
        """设置单次测量的样本数。"""
        self.write(f"CONFigure:{self.BLE_MEAS}:MEValuation:SCOunt:RFPM {int(count)}")

    def ble_get_meas_count(self):
        return self.query_int(f"CONFigure:{self.BLE_MEAS}:MEValuation:SCOunt:RFPM?")

    def ble_init_meval(self):
        """启动 MEValuation 多项测量。"""
        self.init_measurement(f"{self.BLE_MEAS}:MEValuation")

    def ble_abort_meval(self):
        self.write(f"ABORt:{self.BLE_MEAS}:MEValuation")

    def ble_stop_meval(self):
        self.write(f"STOP:{self.BLE_MEAS}:MEValuation")

    def ble_meval_state(self):
        return self.query(f"FETCh:{self.BLE_MEAS}:MEValuation:STATe?").strip()

    # =========================
    # TX 测量结果
    # =========================

    def ble_fetch_power(self):
        """返回功率结果列表 (平均/峰值)。"""
        return self.fetch(f"{self.BLE_MEAS}:MEValuation:POWer:AVERage")

    def ble_read_power(self):
        return self.read(f"{self.BLE_MEAS}:MEValuation:POWer:AVERage")

    def ble_fetch_peak_power(self):
        return self.fetch(f"{self.BLE_MEAS}:MEValuation:POWer:PEAK")

    def ble_fetch_modulation(self):
        """LE 调制结果 (Δf1avg / Δf2avg / Δf2/Δf1 / 频偏)。"""
        return self.fetch(f"{self.BLE_MEAS}:MEValuation:MODulation:AVERage")

    def ble_fetch_freq_accuracy(self):
        """频率精度 / 初始频偏 / 最大漂移结果。"""
        return self.fetch(f"{self.BLE_MEAS}:MEValuation:SACP:AVERage")

    def ble_fetch_spectrum_acp(self):
        """邻道功率 (ACP) 结果。"""
        return self.fetch(f"{self.BLE_MEAS}:MEValuation:SPECtrum:AVERage")

    def ble_fetch_20db_bandwidth(self):
        """20dB 带宽测量结果。"""
        return self.fetch(f"{self.BLE_MEAS}:MEValuation:IBWBandwidth:AVERage")

    def ble_get_average_power_dbm(self):
        """便捷接口: 返回平均功率 (dBm)。"""
        results = self.ble_read_power()
        for v in results:
            if isinstance(v, float):
                return v
        return None

    # =========================
    # 信令模式 / 连接参数
    # =========================

    def ble_signaling_on(self):
        """打开 BLE 信令。"""
        self.write(f"SOURce:{self.BLE_SIGN}:STATe ON")

    def ble_signaling_off(self):
        self.write(f"SOURce:{self.BLE_SIGN}:STATe OFF")

    def ble_signaling_state(self):
        return self.query(f"SOURce:{self.BLE_SIGN}:STATe?").strip()

    def ble_set_tx_power(self, power_dbm):
        """设置仪器发射功率 (用于 DUT 接收测试)。"""
        self.write(f"CONFigure:{self.BLE_SIGN}:RFSettings:LEVel {power_dbm}")

    def ble_get_tx_power(self):
        return self.query_float(f"CONFigure:{self.BLE_SIGN}:RFSettings:LEVel?")

    def ble_set_dut_address(self, address):
        """设置 DUT 蓝牙地址 (XX:XX:XX:XX:XX:XX)。"""
        self.write(f"CONFigure:{self.BLE_SIGN}:CONNection:BDADdress:DUT '{address}'")

    def ble_get_dut_address(self):
        return self.query(f"CONFigure:{self.BLE_SIGN}:CONNection:BDADdress:DUT?").strip().strip('"')

    def ble_connect_dut(self, address=None):
        """发起与 DUT 的信令连接。"""
        if address:
            self.ble_set_dut_address(address)
        self.write(f"CALL:{self.BLE_SIGN}:ACTion CONNect")

    def ble_disconnect_dut(self):
        self.write(f"CALL:{self.BLE_SIGN}:ACTion DISConnect")

    def ble_get_connection_state(self):
        """返回连接状态: OFF / CONN / ADV 等。"""
        return self.query(f"FETCh:{self.BLE_SIGN}:CONNection:STATe?").strip()

    def ble_abort_call(self):
        self.write(f"CALL:{self.BLE_SIGN}:ACTion ABORt")

    # —— 连接参数 (Connection Parameters) ——
    def ble_set_connection_interval(self, interval_ms):
        """设置连接间隔 (ms), 取值 7.5~4000 ms。"""
        self.write(f"CONFigure:{self.BLE_SIGN}:CONNection:INTerval {interval_ms}")

    def ble_get_connection_interval(self):
        return self.query_float(f"CONFigure:{self.BLE_SIGN}:CONNection:INTerval?")

    def ble_set_connection_latency(self, latency):
        """设置连接延迟 (Slave Latency, 单位: 连接事件数)。"""
        self.write(f"CONFigure:{self.BLE_SIGN}:CONNection:LATency {int(latency)}")

    def ble_get_connection_latency(self):
        return self.query_int(f"CONFigure:{self.BLE_SIGN}:CONNection:LATency?")

    def ble_set_connection_timeout(self, timeout_ms):
        """设置连接超时 (ms)。"""
        self.write(f"CONFigure:{self.BLE_SIGN}:CONNection:TIMeout {timeout_ms}")

    def ble_get_connection_timeout(self):
        return self.query_float(f"CONFigure:{self.BLE_SIGN}:CONNection:TIMeout?")

    # —— PHY 更新 ——
    def ble_set_phy_update(self, phy="LE1M"):
        """发起 PHY 更新流程: LE1M / LE2M / LELR。"""
        self.write(f"CONFigure:{self.BLE_SIGN}:CONNection:PHY {phy}")

    def ble_get_phy_update(self):
        return self.query(f"CONFigure:{self.BLE_SIGN}:CONNection:PHY?").strip()

    # —— 广播 (Advertising) 配置 ——
    def ble_set_advertising_type(self, adv_type="ADVIND"):
        """广播类型: ADVIND / ADEVIND / ADVNONCONN / SCANRSP。"""
        self.write(f"CONFigure:{self.BLE_SIGN}:ADVertising:TYPe {adv_type}")

    def ble_set_advertising_interval(self, interval_ms):
        """设置广播间隔 (ms)。"""
        self.write(f"CONFigure:{self.BLE_SIGN}:ADVertising:INTerval {interval_ms}")

    def ble_set_advertising_channel(self, channels="37,38,39"):
        """设置广播信道 (37/38/39)。"""
        self.write(f"CONFigure:{self.BLE_SIGN}:ADVertising:CHANnel {channels}")

    # =========================
    # Direct Test Mode (DTM) / RX 质量
    # =========================

    def ble_set_per_packets(self, packet_count):
        """设置 RX 测试发包数量。"""
        self.write(f"CONFigure:{self.BLE_SIGN}:RXQuality:PACKets {int(packet_count)}")

    def ble_get_per_packets(self):
        return self.query_int(f"CONFigure:{self.BLE_SIGN}:RXQuality:PACKets?")

    def ble_set_per_phy(self, phy="LE1M"):
        """设置 RX 测试物理层: LE1M / LE2M / LELR。"""
        self.write(f"CONFigure:{self.BLE_SIGN}:RXQuality:PHY {phy}")

    def ble_init_per(self):
        """启动 PER 测量。"""
        self.init_measurement(f"{self.BLE_SIGN}:RXQuality:PER")

    def ble_abort_per(self):
        self.write(f"ABORt:{self.BLE_SIGN}:RXQuality:PER")

    def ble_fetch_per(self):
        """返回 PER 测量结果 (误包率 %, 收到包数等)。"""
        return self.fetch(f"{self.BLE_SIGN}:RXQuality:PER")

    def ble_get_per_percent(self):
        """便捷接口: 返回 PER 百分比。"""
        results = self.ble_fetch_per()
        for v in results:
            if isinstance(v, float):
                return v
        return None

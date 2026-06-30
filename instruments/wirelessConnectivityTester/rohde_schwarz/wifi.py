"""CMW WLAN (Wi-Fi 802.11 a/b/g/n/ac/ax) 测量与信令指令 Mixin。"""

from log_config import get_logger

logger = get_logger(__name__)


class WifiMixin:
    """WLAN 信令 (AP/Station 模拟) 与非信令 TX/RX 测量。

    依赖宿主类提供 write / query / query_float / query_int / query_values /
    init_measurement / fetch / read 等基础 IO 方法 (见 CMWBase)。
    """

    WIFI_MEAS = "WLAN:MEASurement"
    WIFI_SIGN = "WLAN:SIGNaling"

    # =========================
    # 通用配置 / 复位
    # =========================

    def wifi_reset(self):
        """复位 WLAN 测量与信令状态。"""
        self.write(f"SOURce:{self.WIFI_SIGN}:STATe OFF")
        self.write(f"ABORt:{self.WIFI_MEAS}:MEValuation")

    def wifi_set_standard(self, standard="NSTD"):
        """物理层标准: DSSS(11b)/LOFDm(11a/g)/HTOFdm(11n)/VHTOfdm(11ac)/HEOFdm(11ax)。"""
        self.write(f"CONFigure:{self.WIFI_MEAS}:ISIGnal:STANdard {standard}")

    def wifi_get_standard(self):
        return self.query(f"CONFigure:{self.WIFI_MEAS}:ISIGnal:STANdard?").strip()

    def wifi_set_bandwidth(self, bandwidth="BW20"):
        """信道带宽: BW05 / BW10 / BW20 / BW40 / BW80 / BW160。"""
        self.write(f"CONFigure:{self.WIFI_MEAS}:ISIGnal:BWIDth {bandwidth}")

    def wifi_get_bandwidth(self):
        return self.query(f"CONFigure:{self.WIFI_MEAS}:ISIGnal:BWIDth?").strip()

    def wifi_set_mcs(self, mcs):
        """设置 MCS 索引 (0~9 for HT; 0~9 for VHT single stream)。"""
        self.write(f"CONFigure:{self.WIFI_MEAS}:ISIGnal:MCS {int(mcs)}")

    def wifi_get_mcs(self):
        return self.query_int(f"CONFigure:{self.WIFI_MEAS}:ISIGnal:MCS?")

    def wifi_set_spatial_streams(self, streams=1):
        """设置空间流数 (1~8, 适用于 11n/11ac/11ax)。"""
        self.write(f"CONFigure:{self.WIFI_MEAS}:ISIGnal:SSCount {int(streams)}")

    def wifi_set_guard_interval(self, gi="GI400"):
        """保护间隔: GI400 (短) / GI800 (长)。"""
        self.write(f"CONFigure:{self.WIFI_MEAS}:ISIGnal:GUARdinterval {gi}")

    def wifi_set_bursts_count(self, count):
        """设置测量样本数 (调制测量)。"""
        self.write(f"CONFigure:{self.WIFI_MEAS}:MEValuation:SCOunt:MODulation {int(count)}")

    def wifi_set_power_count(self, count):
        """设置功率测量样本数。"""
        self.write(f"CONFigure:{self.WIFI_MEAS}:MEValuation:SCOunt:POWer {int(count)}")

    def wifi_set_trigger(self, source="IFPower"):
        """设置测量触发源: IFPower / FreeRun。"""
        self.write(f"TRIGger:{self.WIFI_MEAS}:MEValuation:SOURce {source}")

    def wifi_set_trigger_level(self, level_dbm=-20):
        self.write(f"TRIGger:{self.WIFI_MEAS}:MEValuation:LEVel {level_dbm}")

    # =========================
    # RF 设置
    # =========================

    def wifi_set_rf_input(self, connector="RF1C", attenuation_db=0.0):
        """设置 RF 输入连接器与外部衰减。"""
        self.write(f"CONFigure:{self.WIFI_MEAS}:RFSettings:CONNector {connector}")
        self.write(f"CONFigure:{self.WIFI_MEAS}:RFSettings:EATTenuation {attenuation_db}")

    def wifi_get_rf_connector(self):
        return self.query(f"CONFigure:{self.WIFI_MEAS}:RFSettings:CONNector?").strip()

    def wifi_set_frequency(self, freq_hz):
        """直接设置中心频率 (Hz)。"""
        self.write(f"CONFigure:{self.WIFI_MEAS}:RFSettings:FREQuency {freq_hz}")

    def wifi_get_frequency(self):
        return self.query_float(f"CONFigure:{self.WIFI_MEAS}:RFSettings:FREQuency?")

    @staticmethod
    def wifi_channel_to_freq_hz(channel, band="B24G"):
        """Wi-Fi 信道号转中心频率 (Hz)。

        B24G: 信道 1~14, f = 2412 + (ch-1)*5 MHz (ch14=2484)
        B5G : 信道 36~165, f = 5000 + ch*5 MHz
        """
        ch = int(channel)
        if band.upper() == "B24G":
            if ch == 14:
                return 2_484_000_000
            return int((2412 + (ch - 1) * 5) * 1_000_000)
        # B5G / B6G
        return int((5000 + ch * 5) * 1_000_000)

    def wifi_set_channel(self, channel, band="B24G"):
        """设置 Wi-Fi 信道号 (band: B24G 2.4GHz / B5G 5GHz / B6G 6GHz)。"""
        self.write(f"CONFigure:{self.WIFI_MEAS}:RFSettings:CHANnel {int(channel)},{band}")

    def wifi_get_channel(self):
        return self.query(f"CONFigure:{self.WIFI_MEAS}:RFSettings:CHANnel?").strip()

    def wifi_set_expected_power(self, power_dbm):
        """设置期望输入功率 (dBm)。"""
        self.write(f"CONFigure:{self.WIFI_MEAS}:RFSettings:ENPMode MANual")
        self.write(f"CONFigure:{self.WIFI_MEAS}:RFSettings:ENPower {power_dbm}")

    def wifi_get_expected_power(self):
        return self.query_float(f"CONFigure:{self.WIFI_MEAS}:RFSettings:ENPower?")

    def wifi_set_expected_power_auto(self, auto=True):
        """使能/关闭期望功率自动估算。"""
        state = "ON" if auto else "OFF"
        self.write(f"CONFigure:{self.WIFI_MEAS}:RFSettings:RFEPower:AUTO {state}")

    def wifi_set_user_margin(self, margin_db=0.0):
        """设置用户余量 (dB)。"""
        self.write(f"CONFigure:{self.WIFI_MEAS}:RFSettings:UMARgin {margin_db}")

    def wifi_get_user_margin(self):
        return self.query_float(f"CONFigure:{self.WIFI_MEAS}:RFSettings:UMARgin?")

    # =========================
    # 测量控制
    # =========================

    def wifi_set_repetition(self, mode="SINGleshot"):
        """重复模式: SINGleshot / CONTinuous。"""
        self.write(f"CONFigure:{self.WIFI_MEAS}:MEValuation:REPetition {mode}")

    def wifi_get_repetition(self):
        return self.query(f"CONFigure:{self.WIFI_MEAS}:MEValuation:REPetition?").strip()

    def wifi_init_meval(self):
        """启动 MEValuation 多项测量。"""
        self.init_measurement(f"{self.WIFI_MEAS}:MEValuation")

    def wifi_abort_meval(self):
        self.write(f"ABORt:{self.WIFI_MEAS}:MEValuation")

    def wifi_stop_meval(self):
        self.write(f"STOP:{self.WIFI_MEAS}:MEValuation")

    def wifi_meval_state(self):
        return self.query(f"FETCh:{self.WIFI_MEAS}:MEValuation:STATe?").strip()

    # =========================
    # TX 测量结果
    # =========================

    def wifi_fetch_power(self):
        """返回功率测量结果 (峰值/平均功率)。"""
        return self.fetch(f"{self.WIFI_MEAS}:MEValuation:POWer:AVERage")

    def wifi_read_power(self):
        return self.read(f"{self.WIFI_MEAS}:MEValuation:POWer:AVERage")

    def wifi_fetch_peak_power(self):
        """返回峰值功率结果。"""
        return self.fetch(f"{self.WIFI_MEAS}:MEValuation:POWer:PEAK")

    def wifi_fetch_modulation(self):
        """返回调制测量结果 (EVM / 频偏 / 时钟偏差等)。"""
        return self.fetch(f"{self.WIFI_MEAS}:MEValuation:MODulation:AVERage:ALL")

    def wifi_fetch_evm(self):
        """返回 EVM 结果 (RMS / Peak / 95%)。"""
        return self.fetch(f"{self.WIFI_MEAS}:MEValuation:MODulation:EVMagnitude:AVERage")

    def wifi_fetch_center_freq_error(self):
        """返回中心频率误差 (Hz)。"""
        return self.fetch(f"{self.WIFI_MEAS}:MEValuation:MODulation:FERRor:AVERage")

    def wifi_fetch_clock_error(self):
        """返回符号时钟误差 (ppm)。"""
        return self.fetch(f"{self.WIFI_MEAS}:MEValuation:MODulation:CERRor:AVERage")

    def wifi_fetch_iq_offset(self):
        """返回 IQ 偏移结果 (dB)。"""
        return self.fetch(f"{self.WIFI_MEAS}:MEValuation:MODulation:IQOffset:AVERage")

    def wifi_fetch_spectrum(self):
        """频谱模板结果 (Spectral Mask)。"""
        return self.fetch(f"{self.WIFI_MEAS}:MEValuation:TSMask:AVERage")

    def wifi_fetch_spectrum_flatness(self):
        """频谱平坦度结果。"""
        return self.fetch(f"{self.WIFI_MEAS}:MEValuation:FLATness:AVERage")

    def wifi_get_average_power_dbm(self):
        """便捷接口: 返回平均功率 (dBm)。"""
        results = self.wifi_read_power()
        for v in results:
            if isinstance(v, float):
                return v
        return None

    # =========================
    # 信令 (AP/Station) 模式
    # =========================

    def wifi_signaling_on(self):
        """打开 WLAN 信令 (作为 AP / Station)。"""
        self.write(f"SOURce:{self.WIFI_SIGN}:STATe ON")

    def wifi_signaling_off(self):
        self.write(f"SOURce:{self.WIFI_SIGN}:STATe OFF")

    def wifi_signaling_state(self):
        return self.query(f"SOURce:{self.WIFI_SIGN}:STATe?").strip()

    def wifi_set_operation_mode(self, mode="AP"):
        """信令工作模式: AP / STATion。"""
        self.write(f"CONFigure:{self.WIFI_SIGN}:DUT:MODE {mode}")

    def wifi_get_operation_mode(self):
        return self.query(f"CONFigure:{self.WIFI_SIGN}:DUT:MODE?").strip()

    def wifi_set_ssid(self, ssid):
        """设置 SSID (信令 AP 模式)。"""
        self.write(f"CONFigure:{self.WIFI_SIGN}:CONNection:SSID '{ssid}'")

    def wifi_get_ssid(self):
        return self.query(f"CONFigure:{self.WIFI_SIGN}:CONNection:SSID?").strip().strip('"')

    def wifi_set_signaling_standard(self, standard="NSTD"):
        """设置信令物理层标准。"""
        self.write(f"CONFigure:{self.WIFI_SIGN}:RFSettings:STANdard {standard}")

    def wifi_set_signaling_channel(self, channel, band="B24G"):
        """设置信令信道号与频段。"""
        self.write(f"CONFigure:{self.WIFI_SIGN}:RFSettings:CHANnel {int(channel)},{band}")

    def wifi_set_signaling_bandwidth(self, bw="BW20"):
        """设置信令信道带宽。"""
        self.write(f"CONFigure:{self.WIFI_SIGN}:RFSettings:BWIDth {bw}")

    def wifi_set_tx_power(self, power_dbm):
        """设置仪器下行 (TX) 功率 (dBm), 用于 DUT 接收测试。"""
        self.write(f"CONFigure:{self.WIFI_SIGN}:RFSettings:LEVel {power_dbm}")

    def wifi_get_tx_power(self):
        return self.query_float(f"CONFigure:{self.WIFI_SIGN}:RFSettings:LEVel?")

    def wifi_set_security(self, security="OPEN"):
        """设置安全模式: OPEN / WPA2 / WPA3。"""
        self.write(f"CONFigure:{self.WIFI_SIGN}:SECurity:MODE {security}")

    def wifi_set_passphrase(self, passphrase):
        """设置 WPA2/WPA3 密钥。"""
        self.write(f"CONFigure:{self.WIFI_SIGN}:SECurity:PASSphrase '{passphrase}'")

    def wifi_connect_dut(self):
        """发起与 DUT 的关联 (信令)。"""
        self.write(f"CALL:{self.WIFI_SIGN}:ACTion CONNect")

    def wifi_disconnect_dut(self):
        self.write(f"CALL:{self.WIFI_SIGN}:ACTion DISConnect")

    def wifi_abort_call(self):
        self.write(f"CALL:{self.WIFI_SIGN}:ACTion ABORt")

    def wifi_get_connection_state(self):
        """返回连接状态: OFF / ASSociated / CONNecting 等。"""
        return self.query(f"SENSe:{self.WIFI_SIGN}:CONNection:STATus?").strip()

    # =========================
    # RX 测量 (PER / 吞吐量)
    # =========================

    def wifi_set_per_packets(self, packet_count):
        """设置 PER 测试发包数量。"""
        self.write(f"CONFigure:{self.WIFI_SIGN}:PER:PACKets {int(packet_count)}")

    def wifi_get_per_packets(self):
        return self.query_int(f"CONFigure:{self.WIFI_SIGN}:PER:PACKets?")

    def wifi_init_per(self):
        """启动 PER 测量。"""
        self.init_measurement(f"{self.WIFI_SIGN}:PER")

    def wifi_abort_per(self):
        self.write(f"ABORt:{self.WIFI_SIGN}:PER")

    def wifi_fetch_per(self):
        """返回 PER 测量结果 (误包率 %, 收到包数, 丢失包数)。"""
        return self.fetch(f"{self.WIFI_SIGN}:PER")

    def wifi_get_per_percent(self):
        """便捷接口: 返回 PER 百分比。"""
        results = self.wifi_fetch_per()
        for v in results:
            if isinstance(v, float):
                return v
        return None

    def wifi_init_throughput(self):
        """启动吞吐量测量。"""
        self.init_measurement(f"{self.WIFI_SIGN}:TPUT")

    def wifi_abort_throughput(self):
        self.write(f"ABORt:{self.WIFI_SIGN}:TPUT")

    def wifi_fetch_throughput(self):
        """返回吞吐量结果 (DL/UL Mbps)。"""
        return self.fetch(f"{self.WIFI_SIGN}:TPUT")

    # =========================
    # Ping (数据连通性验证)
    # =========================

    def wifi_set_ping_target(self, target="127.0.0.1"):
        """设置 Ping 目标地址。"""
        self.write(f"CONFigure:{self.WIFI_SIGN}:PING:IPADdress '{target}'")

    def wifi_set_ping_count(self, count=4):
        self.write(f"CONFigure:{self.WIFI_SIGN}:PING:REPeats {int(count)}")

    def wifi_init_ping(self):
        self.write(f"INITiate:{self.WIFI_SIGN}:PING")

    def wifi_fetch_ping(self):
        """返回 Ping 结果 (发送/接收/丢失/平均时延)。"""
        return self.fetch(f"{self.WIFI_SIGN}:PING")

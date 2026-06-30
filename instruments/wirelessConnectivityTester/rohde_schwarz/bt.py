"""CMW 蓝牙 (Classic BR/EDR) 测量与信令指令 Mixin。"""

from log_config import get_logger

logger = get_logger(__name__)


class BluetoothMixin:
    """Bluetooth Classic (BR/EDR) 信令与非信令测量。

    依赖宿主类提供 write / query / query_float / query_int / query_values /
    init_measurement / fetch / read 等基础 IO 方法 (见 CMWBase)。
    """

    BT_MEAS = "BLUetooth:MEASurement"
    BT_SIGN = "BLUetooth:SIGNaling"

    # =========================
    # 通用配置 / 复位
    # =========================

    def bt_reset(self):
        """复位蓝牙测量与信令状态。"""
        self.write(f"SOURce:{self.BT_SIGN}:STATe OFF")
        self.write(f"ABORt:{self.BT_MEAS}:MEValuation")

    def bt_set_demod_mode(self, mode="BRATe"):
        """设置解调模式 (制式): AUTO / BRATe (BR) / EDRate (EDR) / LENergy (BLE)。

        真机实测节点: CONFigure:BLUetooth:MEASurement:ISIGnal:DMODe。
        """
        self.write(f"CONFigure:{self.BT_MEAS}:ISIGnal:DMODe {mode}")

    def bt_get_demod_mode(self):
        return self.query(f"CONFigure:{self.BT_MEAS}:ISIGnal:DMODe?").strip()

    def bt_set_burst_type(self, burst_type="BR"):
        """突发类型 (等同制式选择), 映射到 ISIGnal:DMODe。"""
        mapping = {"BR": "BRATe", "EDR": "EDRate", "LE": "LENergy"}
        self.bt_set_demod_mode(mapping.get(burst_type, burst_type))

    def bt_set_packet_type(self, packet_type="DH1"):
        """设置蓝牙数据包类型 (BR/EDR)。

        常见取值:
          BR  : DH1 / DH3 / DH5
          EDR : 2DH1 / 2DH3 / 2DH5 (2 Mbps) / 3DH1 / 3DH3 / 3DH5 (3 Mbps)
        """
        logger.debug("BT set_packet_type: %s", packet_type)
        self.write(f"CONFigure:{self.BT_MEAS}:MEValuation:STYPe {packet_type}")

    def bt_get_packet_type(self):
        return self.query(f"CONFigure:{self.BT_MEAS}:MEValuation:STYPe?").strip()

    def bt_set_payload_length(self, length):
        """设置有效载荷长度 (字节)。"""
        self.write(f"CONFigure:{self.BT_MEAS}:MEValuation:PLENgth {int(length)}")

    def bt_get_payload_length(self):
        return self.query_int(f"CONFigure:{self.BT_MEAS}:MEValuation:PLENgth?")

    def bt_set_pattern(self, pattern="PRBS9"):
        """设置有效载荷数据模式: PRBS9 / ALL0 / ALL1 / P11 / P44 / F0 / FF 等。"""
        self.write(f"CONFigure:{self.BT_MEAS}:MEValuation:PDPattern {pattern}")

    def bt_get_pattern(self):
        return self.query(f"CONFigure:{self.BT_MEAS}:MEValuation:PDPattern?").strip()

    def bt_set_trigger(self, source="IFPower"):
        """设置测量触发源: IFPower / FreeRun / Baseband。"""
        self.write(f"TRIGger:{self.BT_MEAS}:MEValuation:SOURce {source}")

    def bt_set_trigger_level(self, level_dbm=-20):
        self.write(f"TRIGger:{self.BT_MEAS}:MEValuation:LEVel {level_dbm}")

    # =========================
    # RF 输入/输出
    # =========================

    def bt_set_rf_input(self, connector="RF1C", attenuation_db=0.0):
        """设置 RF 输入连接器与外部衰减。"""
        self.write(f"CONFigure:{self.BT_MEAS}:RFSettings:CONNector {connector}")
        self.write(f"CONFigure:{self.BT_MEAS}:RFSettings:EATTenuation {attenuation_db}")

    def bt_get_rf_connector(self):
        return self.query(f"CONFigure:{self.BT_MEAS}:RFSettings:CONNector?").strip()

    def bt_set_frequency(self, freq_hz):
        """直接设置中心频率 (Hz)。"""
        self.write(f"CONFigure:{self.BT_MEAS}:RFSettings:FREQuency {freq_hz}")

    def bt_get_frequency(self):
        return self.query_float(f"CONFigure:{self.BT_MEAS}:RFSettings:FREQuency?")

    @staticmethod
    def bt_channel_to_freq_hz(channel):
        """蓝牙 BR/EDR 信道 (0~78) 转中心频率 (Hz): f = 2402 + k MHz。"""
        return int((2402 + int(channel)) * 1_000_000)

    def bt_set_channel(self, channel):
        """设置蓝牙信道 (0~78)。

        该固件 BLUetooth:MEASurement 无 RFSettings:CHANnel 节点 (实测 -113),
        故换算为中心频率经 RFSettings:FREQuency 设置。
        """
        self.bt_set_frequency(self.bt_channel_to_freq_hz(channel))

    def bt_set_expected_power(self, power_dbm):
        """设置期望输入功率 (dBm)。

        该固件无 RFSettings:ENPMode 节点 (实测 -113), 直接写 ENPower。
        """
        self.write(f"CONFigure:{self.BT_MEAS}:RFSettings:ENPower {power_dbm}")

    def bt_get_expected_power(self):
        return self.query_float(f"CONFigure:{self.BT_MEAS}:RFSettings:ENPower?")

    def bt_set_expected_power_auto(self, auto=True):
        """使能/关闭期望功率自动估算。"""
        state = "ON" if auto else "OFF"
        self.write(f"CONFigure:{self.BT_MEAS}:RFSettings:RFEPower:AUTO {state}")

    def bt_set_user_margin(self, margin_db=0.0):
        """设置用户余量 (dB), 用于功率测量的动态范围调整。"""
        self.write(f"CONFigure:{self.BT_MEAS}:RFSettings:UMARgin {margin_db}")

    def bt_get_user_margin(self):
        return self.query_float(f"CONFigure:{self.BT_MEAS}:RFSettings:UMARgin?")

    # =========================
    # 测量控制
    # =========================

    def bt_set_repetition(self, mode="SINGleshot"):
        """重复模式: SINGleshot / CONTinuous。"""
        self.write(f"CONFigure:{self.BT_MEAS}:MEValuation:REPetition {mode}")

    def bt_get_repetition(self):
        return self.query(f"CONFigure:{self.BT_MEAS}:MEValuation:REPetition?").strip()

    def bt_set_meas_count(self, count):
        """设置单次测量的样本数 (SINGleshot 模式下生效)。"""
        self.write(f"CONFigure:{self.BT_MEAS}:MEValuation:SCOunt:RFPM {int(count)}")

    def bt_get_meas_count(self):
        return self.query_int(f"CONFigure:{self.BT_MEAS}:MEValuation:SCOunt:RFPM?")

    def bt_init_meval(self):
        """启动 MEValuation 多项测量。"""
        self.init_measurement(f"{self.BT_MEAS}:MEValuation")

    def bt_abort_meval(self):
        self.write(f"ABORt:{self.BT_MEAS}:MEValuation")

    def bt_stop_meval(self):
        self.write(f"STOP:{self.BT_MEAS}:MEValuation")

    def bt_meval_state(self):
        return self.query(f"FETCh:{self.BT_MEAS}:MEValuation:STATe?").strip()

    # =========================
    # TX 测量结果
    # =========================

    def bt_fetch_power(self):
        """返回功率测量结果列表 (平均/峰值/最大/最小)。"""
        return self.fetch(f"{self.BT_MEAS}:MEValuation:POWer:AVERage")

    def bt_read_power(self):
        return self.read(f"{self.BT_MEAS}:MEValuation:POWer:AVERage")

    def bt_fetch_peak_power(self):
        """返回峰值功率结果。"""
        return self.fetch(f"{self.BT_MEAS}:MEValuation:POWer:PEAK")

    def bt_fetch_modulation(self):
        """返回 BR 调制结果 (Δf1avg / Δf2avg / Δf2/Δf1 / 频偏等)。"""
        return self.fetch(f"{self.BT_MEAS}:MEValuation:MODulation:AVERage")

    def bt_fetch_edr_modulation(self):
        """EDR 调制结果 (DEVM RMS/Peak/99%)。"""
        return self.fetch(f"{self.BT_MEAS}:MEValuation:MODulation:EDRate:AVERage")

    def bt_fetch_freq_offset(self):
        """返回频率精度 / 频偏结果。"""
        return self.fetch(f"{self.BT_MEAS}:MEValuation:SACP:AVERage")

    def bt_fetch_spectrum_acp(self):
        """返回邻道功率 (ACP) 结果列表。"""
        return self.fetch(f"{self.BT_MEAS}:MEValuation:SPECtrum:AVERage")

    def bt_fetch_20db_bandwidth(self):
        """返回 20dB 带宽测量结果。"""
        return self.fetch(f"{self.BT_MEAS}:MEValuation:IBWBandwidth:AVERage")

    def bt_get_average_power_dbm(self):
        """便捷接口: 返回平均功率 (dBm)。"""
        results = self.bt_read_power()
        for v in results:
            if isinstance(v, float):
                return v
        return None

    # =========================
    # 信令模式 (BR/EDR)
    # =========================

    def bt_signaling_on(self):
        """打开蓝牙信令 (作为测试仪与 DUT 建链)。"""
        self.write(f"SOURce:{self.BT_SIGN}:STATe ON")

    def bt_signaling_off(self):
        self.write(f"SOURce:{self.BT_SIGN}:STATe OFF")

    def bt_signaling_state(self):
        return self.query(f"SOURce:{self.BT_SIGN}:STATe?").strip()

    def bt_set_tx_power(self, power_dbm):
        """设置仪器下行 (TX) 功率 (dBm), 用于 DUT 接收测试。"""
        self.write(f"CONFigure:{self.BT_SIGN}:RFSettings:LEVel {power_dbm}")

    def bt_get_tx_power(self):
        return self.query_float(f"CONFigure:{self.BT_SIGN}:RFSettings:LEVel?")

    def bt_set_test_mode(self, mode="LOOPback"):
        """信令测试模式: LOOPback / TXTest / RXTest。"""
        self.write(f"CONFigure:{self.BT_SIGN}:RXQuality:TMODe {mode}")

    def bt_get_test_mode(self):
        return self.query(f"CONFigure:{self.BT_SIGN}:RXQuality:TMODe?").strip()

    def bt_set_dut_bd_address(self, bd_address):
        """设置 DUT 蓝牙地址 (XX:XX:XX:XX:XX:XX)。"""
        self.write(f"CONFigure:{self.BT_SIGN}:CONNection:BDADdress:DUT '{bd_address}'")

    def bt_get_dut_bd_address(self):
        return self.query(f"CONFigure:{self.BT_SIGN}:CONNection:BDADdress:DUT?").strip().strip('"')

    def bt_connect_dut(self, bd_address=None):
        """发起与 DUT 的信令连接。"""
        if bd_address:
            self.bt_set_dut_bd_address(bd_address)
        self.write(f"CALL:{self.BT_SIGN}:ACTion CONNect")

    def bt_disconnect_dut(self):
        self.write(f"CALL:{self.BT_SIGN}:ACTion DISConnect")

    def bt_get_connection_state(self):
        """返回连接状态: OFF / CONN / PAGing / INQuiring 等。"""
        return self.query(f"FETCh:{self.BT_SIGN}:CONNection:STATe?").strip()

    def bt_inquiry(self):
        """发起 Inquiry 查询周边蓝牙设备。"""
        self.write(f"CALL:{self.BT_SIGN}:ACTion INQuiry")

    def bt_page(self):
        """发起 Page 寻呼指定 DUT。"""
        self.write(f"CALL:{self.BT_SIGN}:ACTion PAGE")

    def bt_abort_call(self):
        """中止当前的 Inquiry/Page/Connect 动作。"""
        self.write(f"CALL:{self.BT_SIGN}:ACTion ABORt")

    def bt_set_page_scan(self, enabled=True):
        """设置 DUT 是否可被寻呼 (写入 DUT 寄存器, 需信令链路)。"""
        state = "ON" if enabled else "OFF"
        self.write(f"CONFigure:{self.BT_SIGN}:CONNection:PSCHannel {state}")

    def bt_set_inquiry_scan(self, enabled=True):
        state = "ON" if enabled else "OFF"
        self.write(f"CONFigure:{self.BT_SIGN}:CONNection:ISCHannel {state}")

    # =========================
    # RX 质量 / PER (接收灵敏度)
    # =========================

    def bt_set_per_packets(self, packet_count):
        """设置 RX 测试发包数量。"""
        self.write(f"CONFigure:{self.BT_SIGN}:RXQuality:PACKets {int(packet_count)}")

    def bt_get_per_packets(self):
        return self.query_int(f"CONFigure:{self.BT_SIGN}:RXQuality:PACKets?")

    def bt_set_per_payload_length(self, length):
        self.write(f"CONFigure:{self.BT_SIGN}:RXQuality:PLENgth {int(length)}")

    def bt_init_per(self):
        """启动 PER 测量。"""
        self.init_measurement(f"{self.BT_SIGN}:RXQuality:PER")

    def bt_abort_per(self):
        self.write(f"ABORt:{self.BT_SIGN}:RXQuality:PER")

    def bt_fetch_per(self):
        """返回 PER 测量结果 (误包率 %, 收到包数, 丢失包数等)。"""
        return self.fetch(f"{self.BT_SIGN}:RXQuality:PER")

    def bt_get_per_percent(self):
        """便捷接口: 返回 PER 百分比。"""
        results = self.bt_fetch_per()
        for v in results:
            if isinstance(v, float):
                return v
        return None

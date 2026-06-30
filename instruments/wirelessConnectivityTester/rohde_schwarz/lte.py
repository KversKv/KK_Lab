"""CMW LTE FDD/TDD 信令与测量指令 Mixin。"""

from log_config import get_logger

logger = get_logger(__name__)


class LTEMixin:
    """LTE 信令 (eNB 模拟) 与上行测量。

    依赖宿主类提供 write / query / query_float / query_int / query_values /
    init_measurement / fetch / read 等基础 IO 方法 (见 CMWBase)。
    """

    LTE_SIGN = "LTE:SIGNaling"
    LTE_MEAS = "LTE:MEASurement"

    # =========================
    # 信令通用配置 / 复位
    # =========================

    def lte_reset(self):
        """复位 LTE 信令小区与测量。"""
        self.write(f"SOURce:{self.LTE_SIGN}:CELL:STATe OFF")
        self.write(f"ABORt:{self.LTE_MEAS}:MEValuation")

    def lte_set_duplex_mode(self, mode="FDD"):
        """双工模式: FDD / TDD。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:DMODe {mode}")

    def lte_get_duplex_mode(self):
        return self.query(f"CONFigure:{self.LTE_SIGN}:DMODe?").strip()

    def lte_set_band(self, band):
        """设置工作频段, 例如 OB1 / OB3 / OB7 / OB38 / OB40 / OB41 等。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:PCC:BAND {band}")

    def lte_get_band(self):
        return self.query(f"CONFigure:{self.LTE_SIGN}:PCC:BAND?").strip()

    def lte_set_dl_channel(self, earfcn):
        """设置下行 EARFCN。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:RFSettings:PCC:CHANnel:DL {int(earfcn)}")

    def lte_get_dl_channel(self):
        return self.query_int(f"CONFigure:{self.LTE_SIGN}:RFSettings:PCC:CHANnel:DL?")

    def lte_set_ul_channel(self, earfcn):
        """设置上行 EARFCN (FDD 可由 DL 自动推算, TDD 需手动设置)。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:RFSettings:PCC:CHANnel:UL {int(earfcn)}")

    def lte_get_ul_channel(self):
        return self.query_int(f"CONFigure:{self.LTE_SIGN}:RFSettings:PCC:CHANnel:UL?")

    def lte_set_bandwidth(self, bw="B100"):
        """带宽: B014(1.4M)/B030(3M)/B050(5M)/B100(10M)/B150(15M)/B200(20M)。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:PCC:BANDwidth:DL {bw}")
        self.write(f"CONFigure:{self.LTE_SIGN}:PCC:BANDwidth:UL {bw}")

    def lte_get_dl_bandwidth(self):
        return self.query(f"CONFigure:{self.LTE_SIGN}:PCC:BANDwidth:DL?").strip()

    def lte_get_ul_bandwidth(self):
        return self.query(f"CONFigure:{self.LTE_SIGN}:PCC:BANDwidth:UL?").strip()

    # —— TDD 专用配置 ——
    def lte_set_tdd_uldl_config(self, config=0):
        """TDD 上下行配置 (0~6), 决定子帧分配。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:CELL:TDD:ASSubframe {int(config)}")

    def lte_set_tdd_special_subframe(self, ss_config=7):
        """TDD 特殊子帧配置 (0~9), 决定 DwPTS/GP/UpPTS 长度。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:CELL:TDD:SSUBframe {int(ss_config)}")

    # =========================
    # RF 设置
    # =========================

    def lte_set_rf_connector(self, output="RF1C", input_conn="RF1C"):
        """设置 RF 输入/输出连接器。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:RFSettings:PCC:CONNector:BB {output}")
        self.write(f"ROUTe:{self.LTE_SIGN}:RFSettings:PCC:CONNector:RX {input_conn}")

    def lte_set_dl_power(self, power_dbm):
        """设置下行 RS EPRE 功率 (dBm)。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:DL:PCC:RSEPre:LEVel {power_dbm}")

    def lte_get_dl_power(self):
        return self.query_float(f"CONFigure:{self.LTE_SIGN}:DL:PCC:RSEPre:LEVel?")

    def lte_set_expected_ul_power(self, power_dbm):
        """设置期望上行 PUSCH 功率 (dBm)。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:UL:PCC:PUSCh:EPPPusch {power_dbm}")

    def lte_get_expected_ul_power(self):
        return self.query_float(f"CONFigure:{self.LTE_SIGN}:UL:PCC:PUSCh:EPPPusch?")

    def lte_set_external_attenuation(self, output_db=0.0, input_db=0.0):
        """设置外部衰减 (输出/输入, dB)。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:RFSettings:PCC:EATTenuation:OUTPut {output_db}")
        self.write(f"CONFigure:{self.LTE_SIGN}:RFSettings:PCC:EATTenuation:INPut {input_db}")

    # =========================
    # 小区控制 / 连接
    # =========================

    def lte_cell_on(self):
        """打开小区 (发射下行信号)。"""
        self.write(f"SOURce:{self.LTE_SIGN}:CELL:STATe ON")

    def lte_cell_off(self):
        self.write(f"SOURce:{self.LTE_SIGN}:CELL:STATe OFF")

    def lte_cell_state(self):
        """返回小区状态: OFF / ADJ / ON 等。"""
        return self.query(f"SOURce:{self.LTE_SIGN}:CELL:STATe:ALL?").strip()

    def lte_get_connection_state(self):
        """返回 UE 连接状态: OFF/ON/SINFo/REG/RRC/ATT/CEST 等。"""
        return self.query(f"SENSe:{self.LTE_SIGN}:RRCState?").strip()

    def lte_connect_ue(self):
        """发起 PS 切换连接 (RRC 建立 + 附着)。"""
        self.write(f"CALL:{self.LTE_SIGN}:PSWitched:ACTion CONNect")

    def lte_disconnect_ue(self):
        self.write(f"CALL:{self.LTE_SIGN}:PSWitched:ACTion DISConnect")

    def lte_attach_ue(self):
        """发起仅附着 (不建立 RRC)。"""
        self.write(f"CALL:{self.LTE_SIGN}:ATTach:ACTion CONNect")

    def lte_detach_ue(self):
        self.write(f"CALL:{self.LTE_SIGN}:ATTach:ACTion DISConnect")

    def lte_abort_call(self):
        self.write(f"CALL:{self.LTE_SIGN}:PSWitched:ACTion ABORt")

    def lte_get_cell_id(self):
        """返回小区物理 ID (PCI)。"""
        return self.query_int(f"CONFigure:{self.LTE_SIGN}:CELL:PID?")

    def lte_set_cell_id(self, pci):
        """设置小区物理 ID (0~503)。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:CELL:PID {int(pci)}")

    # —— UE 标识 ——
    def lte_set_imsi(self, imsi):
        """设置期望 UE 的 IMSI。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:UESetting:IMSI '{imsi}'")

    def lte_get_imsi(self):
        return self.query(f"CONFigure:{self.LTE_SIGN}:UESetting:IMSI?").strip().strip('"')

    def lte_set_imei(self, imei):
        self.write(f"CONFigure:{self.LTE_SIGN}:UESetting:IMEI '{imei}'")

    def lte_get_imei(self):
        return self.query(f"CONFigure:{self.LTE_SIGN}:UESetting:IMEI?").strip().strip('"')

    # =========================
    # RRC / 调度配置
    # =========================

    def lte_set_scheduling_type(self, sched="RMC"):
        """调度类型: RMC / UDCHannels / UDTTibased。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:CONNection:STYPe {sched}")

    def lte_set_ul_rb(self, num_rb, start_rb=0):
        """设置上行 RB 数量与起始位置。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:CONNection:PCC:RMC:UL {num_rb},{start_rb}")

    def lte_set_dl_rb(self, num_rb, start_rb=0):
        """设置下行 RB 数量与起始位置。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:CONNection:PCC:RMC:DL {num_rb},{start_rb}")

    def lte_set_ul_modulation(self, modulation="QPSK"):
        """上行调制: QPSK / Q16AM / Q64AM / Q256AM。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:CONNection:PCC:UL:MODulation {modulation}")

    def lte_set_dl_modulation(self, modulation="QPSK"):
        """下行调制: QPSK / Q16AM / Q64AM / Q256AM。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:CONNection:PCC:DL:MODulation {modulation}")

    def lte_set_transmission_mode(self, tm=1):
        """设置传输模式 TM1~TM9 (1=SISO, 2=TxDiversity, 3=OLCL, 4=CLCL, 9=TM9)。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:CONNection:TMODel {int(tm)}")

    def lte_get_transmission_mode(self):
        return self.query_int(f"CONFigure:{self.LTE_SIGN}:CONNection:TMODel?")

    def lte_set_mimo(self, antenna_config="1x1"):
        """设置 MIMO 天线配置: 1x1 / 2x2 / 4x4。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:CONNection:ANTenna {antenna_config}")

    def lte_set_ul_tpc(self, tpc_step_db=0):
        """设置上行 TPC (发射功率控制) 步进 (dB)。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:UL:PCC:PUSCh:TPC:STEP {tpc_step_db}")

    # =========================
    # 上行测量 (TX Power / Modulation / Spectrum)
    # =========================

    def lte_set_meas_connector(self, connector="RF1C"):
        """设置测量场景与连接器 (Standalone 模式)。"""
        self.write(f"ROUTe:{self.LTE_MEAS}:SCENario:SALone {connector},RX1")

    def lte_set_meas_frequency(self, freq_hz):
        """设置测量频率 (Hz, 非信令场景)。"""
        self.write(f"CONFigure:{self.LTE_MEAS}:RFSettings:FREQuency {freq_hz}")

    def lte_set_meas_bandwidth(self, bw="B100"):
        """设置测量带宽。"""
        self.write(f"CONFigure:{self.LTE_MEAS}:RFSettings:BWIDth {bw}")

    def lte_set_meas_expected_power(self, power_dbm):
        self.write(f"CONFigure:{self.LTE_MEAS}:RFSettings:ENPower {power_dbm}")

    def lte_init_meval(self):
        """启动 MEValuation 多项测量。"""
        self.init_measurement(f"{self.LTE_MEAS}:MEValuation")

    def lte_abort_meval(self):
        self.write(f"ABORt:{self.LTE_MEAS}:MEValuation")

    def lte_stop_meval(self):
        self.write(f"STOP:{self.LTE_MEAS}:MEValuation")

    def lte_meval_state(self):
        return self.query(f"FETCh:{self.LTE_MEAS}:MEValuation:STATe?").strip()

    def lte_fetch_tx_power(self):
        """返回上行 TX 功率测量结果列表 (PMONitor)。"""
        return self.fetch(f"{self.LTE_MEAS}:MEValuation:PMONitor:AVERage")

    def lte_fetch_modulation(self):
        """返回调制测量结果 (EVM / 频偏 / IQ 偏移等)。"""
        return self.fetch(f"{self.LTE_MEAS}:MEValuation:MODulation:AVERage")

    def lte_fetch_evm(self):
        """返回 EVM 结果 (RMS / Peak / 95%)。"""
        return self.fetch(f"{self.LTE_MEAS}:MEValuation:MODulation:EVMagnitude:AVERage")

    def lte_fetch_spectrum(self):
        """返回频谱发射结果 (ACLR / SEM)。"""
        return self.fetch(f"{self.LTE_MEAS}:MEValuation:ACLR:AVERage")

    def lte_fetch_spectrum_emask(self):
        """返回频谱发射掩码 (SEM) 结果。"""
        return self.fetch(f"{self.LTE_MEAS}:MEValuation:SEMask:AVERage")

    def lte_fetch_iq_offset(self):
        """返回 IQ 偏移结果。"""
        return self.fetch(f"{self.LTE_MEAS}:MEValuation:MODulation:IQOffset:AVERage")

    def lte_fetch_freq_error(self):
        """返回频率误差 (Hz)。"""
        return self.fetch(f"{self.LTE_MEAS}:MEValuation:MODulation:FERRor:AVERage")

    # =========================
    # 吞吐量 / BLER
    # =========================

    def lte_init_throughput(self):
        """启动 BLER / 吞吐量测量。"""
        self.init_measurement(f"{self.LTE_SIGN}:EBLer")

    def lte_abort_throughput(self):
        self.write(f"ABORt:{self.LTE_SIGN}:EBLer")

    def lte_fetch_bler(self):
        """返回 BLER / 吞吐量结果 (PCC)。"""
        return self.fetch(f"{self.LTE_SIGN}:EBLer:PCC")

    def lte_fetch_ul_throughput(self):
        """返回上行吞吐量 (Mbps)。"""
        return self.fetch(f"{self.LTE_SIGN}:EBLer:PCC:UL")

    def lte_fetch_dl_throughput(self):
        """返回下行吞吐量 (Mbps)。"""
        return self.fetch(f"{self.LTE_SIGN}:EBLer:PCC:DL")

    # =========================
    # Ping (数据连通性验证)
    # =========================

    def lte_set_ping_target(self, target="127.0.0.1"):
        """设置 Ping 目标地址。"""
        self.write(f"CONFigure:{self.LTE_SIGN}:PING:IPADdress '{target}'")

    def lte_set_ping_count(self, count=4):
        self.write(f"CONFigure:{self.LTE_SIGN}:PING:REPeats {int(count)}")

    def lte_init_ping(self):
        self.write(f"INITiate:{self.LTE_SIGN}:PING")

    def lte_fetch_ping(self):
        """返回 Ping 结果 (发送/接收/丢失/平均时延)。"""
        return self.fetch(f"{self.LTE_SIGN}:PING")

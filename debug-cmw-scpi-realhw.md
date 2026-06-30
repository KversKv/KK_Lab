# Debug Session: cmw-scpi-realhw

Status: [OPEN]
Target: 真机 R&S CMW (TCPIP0::10.31.31.236::hislip0::INSTR, 固件 4.0.250)
Goal: 逐条核对 BT/BLE/LTE/WIFI 的 SCPI 指令路径, 使 cmw270/__main__.py 全流程跑通 (无 VISA 超时 / SYST:ERR? 干净)。

## 已确认 (Confirmed)
- ModuleNotFoundError 已修复 (__main__.py sys.path 4 层 bootstrap)。
- *IDN? 正常: Rohde&Schwarz,CMW,1201.0002k75/100420,4.0.250
- SYSTem:BASE:VERSion? 在该固件不支持 -> get_firmware_version 已加 *IDN? 回退。
- *OPT? 正常 (返回大量选件)。

## 当前症状 (Symptom)
- 进入 BT 配置 "[BT] 配置信道 0, DH1 数据包" 后, 某条 query 读超时 (VI_ERROR_TMO)。

## 假设 (Hypotheses)
- H1: bt_init_meval 后 wait_for_ready 轮询的状态查询路径在该固件不被识别 -> 读超时。
- H2: BT 配置命令 (bt_set_channel/packet_type 等) 使用了写命令, 但其中夹带了一条 query 路径错误。
- H3: 该 CMW 未装 BT 测量选件, 相关子系统不响应。
- H4: 命令路径大小写/缩写与该固件 SCPI 语法不符 (如 BLUetooth:MEAS vs :SIGN)。
- H5: 测量需先 INIT 再等 *OPC, 直接 FETCh 在未 ready 时阻塞读超时。

## 取证策略
- 用诊断脚本: 每发一条 SCPI 后立即 SYST:ERR? (不阻塞), 定位首个报错指令, 而非等读超时。
- write 类命令不会读超时; 只有 query 会。先把所有 query 改为"发命令+查错"模式核对。

## 取证结果 (Evidence, 来自 _probe_scpi.py)
真机大量返回 -113 "Undefined header", 但部分命令成功, 规律:
- 成功: ...:RFSettings:ENPower / ...:MEValuation:REPetition / INITiate:...:MEValuation
        / FETCh:BLUetooth:MEASurement:MEValuation:STATe? (RUN/OFF)
        / FETCh:WLAN:MEASurement:MEValuation:STATe? (RDY)
- 失败(-113): ...:RFSettings:CHANnel, ...:MEValuation:PTYPe, ...:RFSettings:ENPMode,
        BLE INPut:LENERgy, WLAN:MEASurement:STANdard, LTE:MEASurement:DMODe/BAND,
        FETCh:LTE:MEASurement:STATe? (LTE MEAS 子系统整体不识别)

### 结论
- H1 部分成立: STATe? 路径 BT/WLAN 实际是支持的 (不是超时根因); LTE:MEAS 不支持才超时。
- 核心根因(H4 成立): 大量 CONFigure 子节点 header 与该固件语法不符 -> -113。
  多数失败命令缺少 R&S CMW 必需的 ":SIGNaling<i>:" / ":MEASurement<i>:" **数字后缀** (如 :MEASurement1:),
  以及个别节点名错误 (CHANnel/PTYPe/STANdard 等需挂在正确父节点)。
- *OPT? 含 KM... / KS... 选件, 但需逐条确认装机的测量应用。

## 修复记录 (Fixes)
真机 (固件 4.0.250) 实测可用 vs 不可用节点映射:

BT/BLE (BLUetooth:MEASurement):
- 可用: RFSettings:FREQuency / RFSettings:UMARgin / RFSettings:EATTenuation /
        RFSettings:ENPower / MEValuation:REPetition / ISIGnal:DMODe (值 AUTO/BRATe/EDRate/LENergy) /
        ISIGnal:LENergy:PHY (LE1M/LE2M/...) / INITiate:...:MEValuation /
        FETCh:...:MEValuation:STATe? (RUN/OFF/RDY)
- 不可用(-113): RFSettings:CHANnel / MEValuation:PTYPe / MEValuation:STYPe /
        RFSettings:ENPMode / ISIGnal:BRATe:PTYPe / ISIGnal:STANdard / ISIGnal:INPut:LENERgy
- 结论: 用 RFSettings:FREQuency 替代 CHANnel; 用 ISIGnal:DMODe 选制式(BR/EDR/LE);
        BLE PHY 用 ISIGnal:LENergy:PHY。删除/改造不存在的 PTYPe/ENPMode/STANdard 节点。

WLAN (WLAN:MEASurement):
- 可用: ISIGnal:STANdard (HTOFdm->回读 HTOF) / RFSettings:FREQuency /
        ISIGnal:BWIDth (BW20MHz->回读 BW20) / RFSettings:ENPower / RFSettings:UMARgin /
        FETCh:...:MEValuation:STATe? (RDY)
- 不可用(-113): ISIGnal:BANDwidth / ISIGnal:CBANdwidth / RFSettings:CHANnel / MEASurement:STANdard(无后缀直挂)
- 结论: 带宽用 ISIGnal:BWIDth (非 BANDwidth); 标准用 ISIGnal:STANdard; 信道用 RFSettings:FREQuency。

LTE:
- LTE:MEASurement 与 LTE:SIGNaling 全部 -113 + 读超时 => 该机未装 LTE 选件。
- 结论: 驱动保留 LTE 代码, 但 main 测试用例对 LTE 做"选件缺失"容错跳过, 不阻塞。

## 验证 (Verification)
- 待: 按映射修正 bt/ble/lte/wifi mixin 及 main, 重跑 __main__ 对比 (无 -113 / 无超时)。

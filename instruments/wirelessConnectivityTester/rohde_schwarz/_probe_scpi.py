"""临时真机探针: 逐条发送各制式 SCPI 并紧跟 SYST:ERR? 取证。

非业务代码, 调试取证用, 完成后删除。
运行: python instruments/wirelessConnectivityTester/rohde_schwarz/_probe_scpi.py
"""

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pyvisa

RES = "TCPIP0::10.31.31.236::hislip0::INSTR"

# 每个制式取 main 中会触发的关键指令 (write 类), 末尾各放一条 STATe? query
PROBE = {
    "BASE": [
        ("Q", "*IDN?"),
        ("W", "*CLS"),
    ],
    # 第二轮: 验证 :MEASurement:CHANnel 失败命令加数字后缀 / 校正节点
    "BT_CANDIDATES": [
        ("W", "CONFigure:BLUetooth:MEASurement:RFSettings:CHANnel:BRATe 0"),
        ("W", "CONFigure:BLUetooth:MEASurement:RFSettings:FREQuency 2402000000"),
        ("W", "CONFigure:BLUetooth:MEASurement:MEValuation:STYPe DH1"),
        ("W", "CONFigure:BLUetooth:MEASurement:ISIGnal:BRATe:PTYPe DH1"),
        ("W", "CONFigure:BLUetooth:MEASurement:RFSettings:UMARgin 0"),
        ("W", "CONFigure:BLUetooth:MEASurement:RFSettings:ENPMode AUTO"),
        ("W", "CONFigure:BLUetooth:MEASurement:RFSettings:EATTenuation 0"),
    ],
    "WIFI_CANDIDATES": [
        ("W", "CONFigure:WLAN:MEASurement:ISIGnal:STANdard HTOFdm"),
        ("W", "CONFigure:WLAN:MEASurement:RFSettings:FREQuency 2437000000"),
        ("W", "CONFigure:WLAN:MEASurement:ISIGnal:BANDwidth BW20MHz"),
    ],
    "BT_DMODE_QUERY": [
        ("Q", "CONFigure:BLUetooth:MEASurement:ISIGnal:DMODe?"),
        ("Q", "CONFigure:BLUetooth:MEASurement:ISIGnal:BRATe:PTYPe?"),
        ("Q", "CONFigure:BLUetooth:MEASurement:ISIGnal:LENergy:PHY?"),
        ("Q", "CONFigure:BLUetooth:MEASurement:ISIGnal:STANdard?"),
        ("Q", "CONFigure:WLAN:MEASurement:ISIGnal:STANdard?"),
        ("Q", "CONFigure:WLAN:MEASurement:ISIGnal:BWIDth?"),
    ],
    "OPT_FULL": [
        ("QFULL", "*OPT?"),
    ],
}


def main():
    rm = pyvisa.ResourceManager()
    instr = rm.open_resource(RES)
    instr.timeout = 4000  # 4s, 让不识别的 query 快速超时
    instr.read_termination = "\n"
    instr.write_termination = "\n"
    try:
        for group, cmds in PROBE.items():
            print(f"\n===== {group} =====", flush=True)
            for kind, cmd in cmds:
                try:
                    if kind == "Q":
                        resp = instr.query(cmd).strip()
                        print(f"[Q ] {cmd} -> {resp[:80]}", flush=True)
                    elif kind == "QFULL":
                        resp = instr.query(cmd).strip()
                        print(f"[QF] {cmd} ->\n{resp}", flush=True)
                    else:
                        instr.write(cmd)
                        print(f"[W ] {cmd}", flush=True)
                except Exception as e:  # noqa: BLE001 调试脚本
                    print(f"[!!] {cmd} -> EXC {type(e).__name__}: {e}", flush=True)
                    try:
                        instr.clear()
                    except Exception:
                        pass
                # 紧跟查错
                try:
                    err = instr.query("SYSTem:ERRor?").strip()
                    if not err.startswith("0,") and "No error" not in err:
                        print(f"     ERR: {err}", flush=True)
                except Exception as e:  # noqa: BLE001
                    print(f"     ERR-query EXC {type(e).__name__}: {e}", flush=True)
                    try:
                        instr.clear()
                    except Exception:
                        pass
    finally:
        instr.close()
        rm.close()


if __name__ == "__main__":
    main()

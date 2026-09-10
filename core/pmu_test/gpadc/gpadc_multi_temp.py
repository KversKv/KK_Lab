# -*- coding: utf-8 -*-
"""GPADC 多通道高低温联合测试流程（纯 Python，无 Qt 依赖）。

设计目标：一轮温循内完成所有 GPADC 高低温相关测试——
- 单温度点内按通道分发：逐通道执行 IIC 切换写序列后采样；
- 通道可配电压扫描（N6705C 扫压，语义同 Temp Consistency）或定点采样；
- 前置配置在测试开始前执行一次，可选测试结束后恢复原值；
- 结果按通道分类输出，日志分层打印。

与 UI 的解耦方式：所有副作用（写寄存器 / 读寄存器 / 采样 / 日志 / 状态）
均经回调注入，UI 侧在 worker 线程中调用本函数。
"""

from __future__ import annotations

import time

from instruments.chambers import TemperatureStabilizer
from log_config import get_logger

logger = get_logger(__name__)


def parse_hw_int(value, default=0):
    """解析十六进制 / 十进制字符串或 int 为 int。

    支持 '0x1F' / '1F' / '31' / 31；空串 / None 回退 default。
    """
    if value is None:
        return default
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return default
    try:
        return int(text, 0)
    except ValueError:
        try:
            return int(text, 16)
        except ValueError:
            return default


def _norm_write(op) -> dict:
    """规范化一条 IIC 写操作（容忍字符串 / 缺失字段）。"""
    return {
        "op": str(op.get("op") or "WRITE").upper(),
        "dev": parse_hw_int(op.get("dev")),
        "reg": parse_hw_int(op.get("reg")),
        "val": parse_hw_int(op.get("val")),
        "width": int(op.get("width") or 8),
        "high": int(op.get("high", -1) if op.get("high") is not None else -1),
        "low": int(op.get("low", -1) if op.get("low") is not None else -1),
        "note": str(op.get("note") or ""),
    }


def parse_iic_command_text(text, default_dev=0, default_width=8) -> list[dict]:
    """解析 consumption_test 同款 YAML 风格 IIC 命令文本为写操作列表。

    语法（每行一条，容忍 `-` 列表前缀 / 首尾引号 / `//` 注释）：
        WRITE <reg> <value>                  整寄存器写
        WRITE_BITS <reg> <msb> <lsb> <value> 位写
        READ <reg>                           读回（日志验证用）
        [0x17:] WRITE ...                    可选十六进制设备地址前缀；
                                             无前缀时用 default_dev / default_width

    数值均支持 0x 十六进制 / 十进制。无法识别的行静默跳过（与 consumption 一致）。
    """
    commands = []
    for raw_line in str(text or "").strip().splitlines():
        line = raw_line.strip()
        if line.startswith("-"):
            line = line[1:].strip()
        if line.startswith("'") or line.startswith('"'):
            line = line[1:]
        if line.endswith("'") or line.endswith('"'):
            line = line[:-1]
        line = line.strip()

        comment_idx = line.find("//")
        if comment_idx >= 0:
            line = line[:comment_idx].strip()
        if not line:
            continue

        upper = line.upper()
        if not any(kw in upper for kw in ("WRITE_BITS", "WRITE", "READ")):
            continue

        dev = default_dev
        if ":" in line:
            prefix, rest = line.split(":", 1)
            rest_upper = rest.strip().upper()
            if any(kw in rest_upper for kw in ("WRITE_BITS", "WRITE", "READ")):
                try:
                    dev = int(prefix.strip(), 0)
                    line = rest.strip()
                except ValueError:
                    pass

        parts = line.split()
        if len(parts) < 2:
            continue
        op = parts[0].upper()
        try:
            if op == "WRITE_BITS" and len(parts) >= 5:
                commands.append(_norm_write({
                    "op": "WRITE_BITS", "dev": dev,
                    "reg": int(parts[1], 0), "high": int(parts[2], 0),
                    "low": int(parts[3], 0), "val": int(parts[4], 0),
                    "width": default_width,
                }))
            elif op == "WRITE" and len(parts) >= 3:
                commands.append(_norm_write({
                    "op": "WRITE", "dev": dev,
                    "reg": int(parts[1], 0), "val": int(parts[2], 0),
                    "width": default_width,
                }))
            elif op == "READ" and len(parts) >= 2:
                commands.append(_norm_write({
                    "op": "READ", "dev": dev,
                    "reg": int(parts[1], 0), "width": default_width,
                }))
        except ValueError:
            continue
    return commands


def writes_to_command_text(writes) -> str:
    """旧版 dict 写序列（表格格式）转命令文本（加载旧配置时兼容用）。"""
    lines = []
    for op in writes or []:
        w = _norm_write(op)
        dev_prefix = f"0x{w['dev']:02X}: " if w["dev"] else ""
        if w["high"] >= 0 and w["low"] >= 0:
            line = f"{dev_prefix}WRITE_BITS 0x{w['reg']:X} {w['high']} {w['low']} 0x{w['val']:X}"
        else:
            line = f"{dev_prefix}WRITE 0x{w['reg']:X} 0x{w['val']:X}"
        if w["note"]:
            line += f"  // {w['note']}"
        lines.append(line)
    return "\n".join(lines)


def _fmt_write(w) -> str:
    if w.get("op") == "READ":
        text = f"0x{w['dev']:02X}/0x{w['reg']:02X} READ ({w['width']}-bit)"
    else:
        text = f"0x{w['dev']:02X}/0x{w['reg']:02X}=0x{w['val']:X} ({w['width']}-bit)"
        if w["high"] >= 0 and w["low"] >= 0:
            text += f" [bit {w['high']}:{w['low']}]"
    if w["note"]:
        text += f"  # {w['note']}"
    return text


def _exec_write_op(w, write_fn, read_reg_fn, log_fn, tag):
    """执行一条规范化操作：WRITE/WRITE_BITS 走 write_fn，READ 走 read_reg_fn 并日志回读值。"""
    if w.get("op") == "READ":
        val = read_reg_fn(w["dev"], w["reg"], w["width"])
        log_fn(f"{tag} READ 0x{w['dev']:02X}/0x{w['reg']:02X} => 0x{int(val):X}")
    else:
        write_fn(w["dev"], w["reg"], w["val"], w["width"], w["high"], w["low"])
        log_fn(f"{tag} {_fmt_write(w)}")


def _build_voltage_points(v_min, v_max, v_step) -> list[float]:
    points = []
    v = float(v_min)
    v_max = float(v_max)
    v_step = float(v_step)
    if v_step <= 0:
        return [round(v, 6)]
    while v <= v_max + v_step * 0.001:
        points.append(round(v, 6))
        v = round(v + v_step, 6)
    return points


def _resolve_switch_writes(ch, default_dev, default_width) -> list[dict]:
    """通道切换写序列：优先解析 switch_writes_text（consumption 风格命令文本），
    向后兼容旧版 switch_writes dict 列表。"""
    text = ch.get("switch_writes_text")
    if isinstance(text, str) and text.strip():
        return parse_iic_command_text(text, default_dev, default_width)
    return [_norm_write(w) for w in (ch.get("switch_writes") or [])]


def run_multi_ch_temp_test(
    *,
    chamber,
    vol_source=None,
    write_fn,
    read_reg_fn,
    sample_fn,
    channels,
    pre_config=None,
    temp_min=0.0,
    temp_max=100.0,
    temp_step=10.0,
    soak_time=180,
    sample_cnt=1000,
    default_dev=0,
    default_width=8,
    mock_mode=False,
    log_fn=None,
    status_fn=None,
    stop_check=None,
    progress_callback=None,
):
    """执行多通道高低温联合测试。

    参数（全部关键字）：
        chamber: 温箱实例（set_temperature/start/get_current_temp）。
        vol_source: N6705C 实例；任一启用通道开启电压扫描时必需。
        write_fn(dev, reg, val, width, high, low): IIC 写（high/low>=0 时位写）。
        read_reg_fn(dev, reg, width): IIC 原始读（前置配置恢复原值 / READ 命令用）。
        sample_fn(channel_cfg, sample_cnt, stop_check, mock_hint): 采样一次，
            返回 (avg, max, min)；mock_hint 仅供 Mock 联动电压（扫压点或温度/100）。
        channels: 通道配置列表（enabled/name/sweep_enabled/switch_writes_text/
            read_dev/read_reg/read_width/voltage_channel/v_min/v_max/v_step）。
            switch_writes_text 为 consumption 风格命令文本（parse_iic_command_text）；
            向后兼容旧版 switch_writes dict 列表。
        pre_config: {"restore_after": bool, "writes": [write op, ...]}。
        default_dev / default_width: 命令文本无前缀时使用的页面全局设备地址/位宽。
        mock_mode: True 时跳过稳温/均温/扫压延时。

    返回：{"temp": [...], "sample_cnt": int,
           "channels": [{"name", "sweep", "voltage"|None,
                         "mean": [...], "min": [...], "max": [...]} ...]}；
          失败返回 None（用户停止时返回已采集的部分数据）。
    """

    def _log(msg):
        if log_fn is not None:
            log_fn(msg)

    def _status(msg, is_error=False):
        if status_fn is not None:
            status_fn(msg, is_error)

    def _stopped():
        return bool(stop_check and stop_check())

    enabled = [c for c in (channels or []) if c.get("enabled", True)]
    if not enabled:
        _log("[ERROR] 无已启用的通道，测试中止")
        _status("错误: 无已启用通道", True)
        return None
    if chamber is None:
        _log("[ERROR] Chamber not connected")
        _status("错误: 温箱未连接", True)
        return None

    # 通道计划：预规范化切换写序列与电压扫描点
    ch_plans = []
    for idx, ch in enumerate(enabled):
        sweep = bool(ch.get("sweep_enabled"))
        vpts = (
            _build_voltage_points(ch.get("v_min", 0.1), ch.get("v_max", 1.8), ch.get("v_step", 0.05))
            if sweep else []
        )
        ch_plans.append({
            "cfg": ch,
            "name": str(ch.get("name") or f"CH{idx + 1}"),
            "sweep": sweep,
            "vpts": vpts,
            "writes": _resolve_switch_writes(ch, default_dev, default_width),
        })

    if any(p["sweep"] for p in ch_plans) and vol_source is None:
        _log("[ERROR] 存在启用电压扫描的通道，但 N6705C 未连接，测试中止")
        _status("错误: N6705C未连接", True)
        return None

    try:
        # ---------- 前置配置（测试开始前执行一次） ----------
        originals = []
        pre = pre_config or {}
        pre_writes = [_norm_write(w) for w in (pre.get("writes") or [])]
        if pre_writes:
            restore = bool(pre.get("restore_after", True))
            _log("===== 前置配置 IIC 写入 =====")
            for w in pre_writes:
                if _stopped():
                    _log("[INFO] Multi-Ch temp test stopped by user.")
                    return None
                if restore:
                    try:
                        orig = read_reg_fn(w["dev"], w["reg"], w["width"])
                        originals.append((w, orig))
                    except Exception as e:  # noqa: BLE001
                        logger.warning("前置配置读原值失败: %s", e, exc_info=True)
                        originals.append((w, None))
                        _log(f"[WARN] 前置配置读原值失败 {w['dev']:#04x}/{w['reg']:#04x}: {e}")
                _exec_write_op(w, write_fn, read_reg_fn, _log, "[PRE]")

        # ---------- 进度总量 ----------
        total_temp_points = max(1, int(round((temp_max - temp_min) / temp_step)) + 1)
        per_temp_steps = sum(len(p["vpts"]) if p["sweep"] else 1 for p in ch_plans)
        total_steps = max(1, total_temp_points * per_temp_steps)
        completed_steps = 0

        temp_list = []
        results = [{
            "name": p["name"],
            "sweep": p["sweep"],
            "voltage": list(p["vpts"]) if p["sweep"] else None,
            "mean": [], "min": [], "max": [],
        } for p in ch_plans]

        settle_time = 0.0 if mock_mode else 0.5
        step_time = 0.0 if mock_mode else 0.2

        current_temp = temp_min
        point_idx = 0
        try:
            while current_temp <= temp_max + 0.001:
                if _stopped():
                    _log("[INFO] Multi-Ch temp test stopped by user.")
                    break

                chamber.set_temperature(current_temp)
                _status(f"设置温箱温度到 {current_temp:.1f}°C")

                if mock_mode:
                    _log(f"[DEBUG] Temp set to {current_temp:.1f}°C (instant)")
                else:
                    if point_idx == 0:
                        try:
                            chamber.start()
                            _log("[INFO] Chamber started (constant-temp run command sent)")
                        except Exception as e:  # noqa: BLE001
                            logger.warning("Chamber start 命令失败: %s", e, exc_info=True)
                            _log(f"[WARN] Chamber start command failed: {e}")

                    stabilizer = TemperatureStabilizer(
                        chamber, log_fn=_log, stop_check=stop_check,
                    )
                    st = stabilizer.wait_for_stable(current_temp)
                    if st.reason == "stopped":
                        _log("[INFO] Multi-Ch temp test stopped by user.")
                        break
                    actual_str = "N/A" if st.actual is None else f"{st.actual:.2f}"
                    _log(
                        f"[INFO] Temperature {st.reason}: target={current_temp:.1f}, "
                        f"actual={actual_str}, waited {st.waited_s:.0f}s, polls={st.poll_count}"
                    )

                    _status(f"DUT温度均衡中: {current_temp:.1f}°C")
                    for _ in range(int(soak_time)):
                        if _stopped():
                            break
                        time.sleep(1)
                    if _stopped():
                        _log("[INFO] Multi-Ch temp test stopped by user.")
                        break

                _log(f"===== T={current_temp:.1f}°C 通道分发测试 =====")
                temp_list.append(current_temp)

                for ci, plan in enumerate(ch_plans):
                    if _stopped():
                        break
                    name = plan["name"]
                    ch_cfg = plan["cfg"]

                    for w in plan["writes"]:
                        _exec_write_op(w, write_fn, read_reg_fn, _log, f"[CH {name}] SWITCH")

                    if plan["sweep"]:
                        vch = int(ch_cfg.get("voltage_channel") or 1)
                        vol_source.set_voltage(vch, plan["vpts"][0])
                        time.sleep(settle_time)
                        mean_row, min_row, max_row = [], [], []
                        for vpt in plan["vpts"]:
                            if _stopped():
                                break
                            vol_source.set_voltage(vch, vpt)
                            time.sleep(step_time)
                            avg, mx, mn = sample_fn(ch_cfg, sample_cnt, stop_check, vpt)
                            mean_row.append(avg)
                            min_row.append(mn)
                            max_row.append(mx)
                            completed_steps += 1
                            if progress_callback:
                                progress_callback(int(completed_steps * 100 / total_steps))
                        results[ci]["mean"].append(mean_row)
                        results[ci]["min"].append(min_row)
                        results[ci]["max"].append(max_row)
                        _log(f"[CH {name}] T={current_temp:.1f}°C  voltage sweep done ({len(mean_row)} points)")
                    else:
                        avg, mx, mn = sample_fn(ch_cfg, sample_cnt, stop_check, current_temp / 100.0)
                        results[ci]["mean"].append(avg)
                        results[ci]["min"].append(mn)
                        results[ci]["max"].append(mx)
                        completed_steps += 1
                        if progress_callback:
                            progress_callback(int(completed_steps * 100 / total_steps))
                        _log(f"[CH {name}] T={current_temp:.1f}°C, avg={avg:.3f}, min={mn}, max={mx}")

                if _stopped():
                    _log("[INFO] Multi-Ch temp test stopped by user.")
                    break
                current_temp = round(current_temp + temp_step, 6)
                point_idx += 1
        finally:
            # 温箱回室温 + 前置配置恢复原值（停止 / 异常均兜底）
            try:
                chamber.set_temperature(25.0)
            except Exception as e:  # noqa: BLE001
                logger.warning("温箱回设 25°C 失败: %s", e, exc_info=True)
                _log(f"[WARN] 温箱回设 25°C 失败: {e}")
            for w, orig in reversed(originals):
                if orig is None:
                    continue
                try:
                    write_fn(w["dev"], w["reg"], int(orig), w["width"], -1, -1)
                    _log(f"[PRE] RESTORE 0x{w['dev']:02X}/0x{w['reg']:02X}=0x{int(orig):X}")
                except Exception as e:  # noqa: BLE001
                    logger.warning("前置配置恢复失败: %s", e, exc_info=True)
                    _log(f"[WARN] 前置配置恢复失败 0x{w['dev']:02X}/0x{w['reg']:02X}: {e}")

        # ---------- 结果分类输出 ----------
        _log("===== MULTI-CH TEMP TEST 结果分类输出 =====")
        for res in results:
            name = res["name"]
            if res["sweep"]:
                vol_header = "  ".join(f"{v:.3f}" for v in (res["voltage"] or []))
                for tag, matrix in (("Mean", res["mean"]), ("Min", res["min"]), ("Max", res["max"])):
                    _log(f"--- [CH {name}] {tag} (Temp x Voltage) ---")
                    _log("Temp\\Voltage  " + vol_header)
                    for i, t in enumerate(temp_list):
                        if i < len(matrix):
                            _log(f"T={t:.1f}  " + "  ".join(f"{x:.1f}" for x in matrix[i]))
            else:
                _log(f"--- [CH {name}] 定点采样 (Temp, Mean, Min, Max) ---")
                for i, t in enumerate(temp_list):
                    if i < len(res["mean"]):
                        _log(f"{t:.2f}, {res['mean'][i]:.3f}, {res['min'][i]}, {res['max'][i]}")

        return {
            "temp": temp_list,
            "sample_cnt": sample_cnt,
            "channels": results,
        }

    except Exception as e:  # noqa: BLE001
        _log(f"[ERROR] {e}")
        logger.error("多通道高低温测试执行错误: %s", e, exc_info=True)
        _status(f"错误: {e}", True)
        return None

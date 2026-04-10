import struct
import re


def parse_csv_text(csv_text, curr_channels, volt_channels, ulabel, sample_period_s):
    actual_interval = None
    match = re.search(r'Sample interval:\s*([\d.eE+\-]+)', csv_text)
    if match:
        actual_interval = float(match.group(1))

    if actual_interval is not None:
        sample_period_s = actual_interval
        print(f"[Datalog] Using sample interval from CSV: {sample_period_s}")

    lines = csv_text.splitlines()
    print(f"[Datalog] Total CSV lines: {len(lines)}")

    ordered_cols = []
    all_chs = sorted(set(curr_channels) | set(volt_channels))
    for ch in all_chs:
        if ch in volt_channels:
            ordered_cols.append(("volt", ch))
        if ch in curr_channels:
            ordered_cols.append(("curr", ch))

    col_data = {i: [] for i in range(len(ordered_cols))}

    for line in lines:
        if not line.strip() or "," not in line:
            continue
        parts = line.split(",")
        try:
            float(parts[0])
        except (ValueError, IndexError):
            continue
        for col_idx in range(len(ordered_cols)):
            try:
                col_data[col_idx].append(float(parts[1 + col_idx]))
            except (ValueError, IndexError):
                pass

    all_data = {}
    for col_idx, (meas_type, ch) in enumerate(ordered_cols):
        suffix = "I" if meas_type == "curr" else "V"
        label = f"{ulabel} CH{ch} {suffix}".strip()
        values = col_data[col_idx]
        print(f"[Datalog] {label}: {len(values)} points")
        if values:
            values = [v * 1000.0 for v in values]
            t = [i * sample_period_s for i in range(len(values))]
            all_data[label] = {"time": t, "values": values}

    return all_data


def parse_dlog_binary(raw_data, curr_channels, volt_channels, ulabel, sample_period_s):
    all_data = {}
    try:
        xml_header = raw_data[:min(len(raw_data), 8192)].decode('ascii', errors='replace')

        tint_match = re.search(r'<tint>([\d.eE+\-]+)</tint>', xml_header)
        if tint_match:
            sample_period_s = float(tint_match.group(1))
            print(f"[Datalog] dlog tint (sample interval): {sample_period_s}")

        dlog_curr_chs = []
        dlog_volt_chs = []
        for m in re.finditer(r'<channel id="(\d+)">(.*?)</channel>', xml_header, re.DOTALL):
            ch_id = int(m.group(1))
            ch_xml = m.group(2)
            sc = re.search(r'<sense_curr>(\d+)</sense_curr>', ch_xml)
            sv = re.search(r'<sense_volt>(\d+)</sense_volt>', ch_xml)
            if sc and sc.group(1) == '1':
                dlog_curr_chs.append(ch_id)
            if sv and sv.group(1) == '1':
                dlog_volt_chs.append(ch_id)

        dlog_col_order = []
        all_ch_ids = sorted(set(dlog_curr_chs + dlog_volt_chs))
        for ch in all_ch_ids:
            if ch in dlog_volt_chs:
                dlog_col_order.append(("volt", ch))
            if ch in dlog_curr_chs:
                dlog_col_order.append(("curr", ch))

        num_traces = len(dlog_col_order)
        if num_traces == 0:
            print("[Datalog] No active traces found in dlog XML header")
            return None

        close_tag = b'</dlog>'
        tag_pos = raw_data.find(close_tag)
        if tag_pos < 0:
            print("[Datalog] Could not find </dlog> tag in dlog file")
            return None

        data_offset = tag_pos + len(close_tag) + 9

        if data_offset + num_traces * 4 > len(raw_data):
            print(f"[Datalog] dlog file too small for data at offset {data_offset}")
            return None

        print(f"[Datalog] dlog data_offset: {data_offset}, traces: {num_traces}")

        data_section = raw_data[data_offset:]
        float_count = len(data_section) // 4
        num_samples = float_count // num_traces

        print(f"[Datalog] dlog: {float_count} floats, {num_samples} samples, {num_traces} traces")

        values_all = struct.unpack_from(f'>{float_count}f', data_section, 0)

        requested = []
        all_req_chs = sorted(set(curr_channels) | set(volt_channels))
        for ch in all_req_chs:
            if ch in volt_channels:
                requested.append(("volt", ch))
            if ch in curr_channels:
                requested.append(("curr", ch))

        for meas_type, ch in requested:
            try:
                col_idx = dlog_col_order.index((meas_type, ch))
            except ValueError:
                continue

            values = [values_all[i * num_traces + col_idx] * 1000.0
                      for i in range(num_samples)]

            suffix = "I" if meas_type == "curr" else "V"
            label = f"{ulabel} CH{ch} {suffix}".strip()
            print(f"[Datalog] {label}: {len(values)} points (from dlog)")
            if values:
                t = [i * sample_period_s for i in range(len(values))]
                all_data[label] = {"time": t, "values": values}

        return all_data
    except Exception as e:
        print(f"[Datalog] dlog parse error: {e}")
        import traceback
        traceback.print_exc()
        return None


def compute_power_channels(all_data, power_chs_a, power_chs_b):
    for i, active in enumerate(power_chs_a):
        if active:
            ch = i + 1
            calc_power_for_ch(all_data, ch, "")
    for i, active in enumerate(power_chs_b):
        if active:
            ch = i + 1
            calc_power_for_ch(all_data, ch, "B")


def calc_power_for_ch(all_data, ch, unit_prefix):
    prefix = f"{unit_prefix} " if unit_prefix else ""
    v_label = f"{prefix}CH{ch} V".strip()
    i_label = f"{prefix}CH{ch} I".strip()
    p_label = f"{prefix}CH{ch} P".strip()
    if v_label in all_data and i_label in all_data:
        v_vals = all_data[v_label]["values"]
        i_vals = all_data[i_label]["values"]
        t = all_data[v_label]["time"]
        p_vals = [v * i / 1000.0 for v, i in zip(v_vals, i_vals)]
        all_data[p_label] = {"time": t, "values": p_vals}


def import_csv_file(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        return None

    header = lines[0].strip().split(",")
    if len(header) < 2:
        return None

    channel_names = [h.strip() for h in header[1:]]

    all_data = {}
    for name in channel_names:
        all_data[name] = {"time": [], "values": []}

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 2:
            continue

        try:
            t = float(parts[0])
        except ValueError:
            continue

        for col_idx, name in enumerate(channel_names):
            try:
                val = float(parts[1 + col_idx])
            except (ValueError, IndexError):
                val = 0.0
            all_data[name]["time"].append(t)
            all_data[name]["values"].append(val)

    empty_keys = [k for k, v in all_data.items() if not v["time"]]
    for k in empty_keys:
        del all_data[k]

    if not all_data:
        return None

    return all_data


def _parse_dlog_raw(raw_data):
    xml_header = raw_data[:min(len(raw_data), 8192)].decode('ascii', errors='replace')

    sample_period_s = 0.001
    tint_match = re.search(r'<tint>([\d.eE+\-]+)</tint>', xml_header)
    if tint_match:
        sample_period_s = float(tint_match.group(1))

    dlog_col_order = []
    for m in re.finditer(r'<channel id="(\d+)">(.*?)</channel>', xml_header, re.DOTALL):
        ch_id = int(m.group(1))
        ch_xml = m.group(2)
        sc = re.search(r'<sense_curr>(\d+)</sense_curr>', ch_xml)
        sv = re.search(r'<sense_volt>(\d+)</sense_volt>', ch_xml)
        if sv and sv.group(1) == '1':
            dlog_col_order.append(("volt", ch_id))
        if sc and sc.group(1) == '1':
            dlog_col_order.append(("curr", ch_id))

    num_traces = len(dlog_col_order)
    if num_traces == 0:
        return None, None

    close_tag = b'</dlog>'
    tag_pos = raw_data.find(close_tag)
    if tag_pos < 0:
        return None, None

    return sample_period_s, dlog_col_order


def import_edlg_file(path):
    import zipfile
    from xml.etree import ElementTree

    with zipfile.ZipFile(path, 'r') as zf:
        mdlg_name = None
        dlog_name = None
        for name in zf.namelist():
            if name.endswith('.mdlg'):
                mdlg_name = name
            elif name.endswith('.dlog'):
                dlog_name = name

        if not dlog_name:
            return None, None

        trace_names = []
        if mdlg_name:
            mdlg_xml = zf.read(mdlg_name).decode('utf-8', errors='replace')
            root = ElementTree.fromstring(mdlg_xml)
            for trace_el in root.findall('.//TraceSettings/Frames/Frame/Trace'):
                name_el = trace_el.find('Name')
                if name_el is not None and name_el.text:
                    trace_names.append(name_el.text.strip())

        raw_data = zf.read(dlog_name)

    xml_header = raw_data[:min(len(raw_data), 8192)].decode('ascii', errors='replace')

    sample_period_s = 0.001
    tint_match = re.search(r'<tint>([\d.eE+\-]+)</tint>', xml_header)
    if tint_match:
        sample_period_s = float(tint_match.group(1))

    dlog_col_order = []
    for m in re.finditer(r'<channel id="(\d+)">(.*?)</channel>', xml_header, re.DOTALL):
        ch_id = int(m.group(1))
        ch_xml = m.group(2)
        sc = re.search(r'<sense_curr>(\d+)</sense_curr>', ch_xml)
        sv = re.search(r'<sense_volt>(\d+)</sense_volt>', ch_xml)
        if sv and sv.group(1) == '1':
            dlog_col_order.append(("volt", ch_id))
        if sc and sc.group(1) == '1':
            dlog_col_order.append(("curr", ch_id))

    num_traces = len(dlog_col_order)
    if num_traces == 0:
        return None, None

    close_tag = b'</dlog>'
    tag_pos = raw_data.find(close_tag)
    if tag_pos < 0:
        return None, None

    data_start = tag_pos + len(close_tag)
    while data_start < len(raw_data) and raw_data[data_start:data_start+1] in (b'\r', b'\n'):
        data_start += 1
    data_start += 8

    if data_start + num_traces * 4 > len(raw_data):
        return None, None

    data_section = raw_data[data_start:]
    float_count = len(data_section) // 4
    num_samples = float_count // num_traces

    values_all = struct.unpack_from(f'>{float_count}f', data_section, 0)

    has_power = any(n.endswith('-P1') or n.endswith('-P2') or n.endswith('-P3') or n.endswith('-P4')
                    for n in trace_names)

    all_data = {}
    for col_idx, (meas_type, ch) in enumerate(dlog_col_order):
        values = [values_all[i * num_traces + col_idx] * 1000.0
                  for i in range(num_samples)]
        suffix = "I" if meas_type == "curr" else "V"
        label = f"CH{ch} {suffix}"
        if values:
            t = [i * sample_period_s for i in range(len(values))]
            all_data[label] = {"time": t, "values": values}

    if has_power:
        for ch_id in sorted(set(c for _, c in dlog_col_order)):
            v_label = f"CH{ch_id} V"
            i_label = f"CH{ch_id} I"
            if v_label in all_data and i_label in all_data:
                v_vals = all_data[v_label]["values"]
                i_vals = all_data[i_label]["values"]
                t = all_data[v_label]["time"]
                p_vals = [v * i / 1000.0 for v, i in zip(v_vals, i_vals)]
                all_data[f"CH{ch_id} P"] = {"time": t, "values": p_vals}

    if not all_data:
        return None, None

    return all_data, raw_data


def import_dlog_file(path):
    with open(path, "rb") as f:
        raw_data = f.read()

    xml_header = raw_data[:min(len(raw_data), 8192)].decode('ascii', errors='replace')

    sample_period_s = 0.001
    tint_match = re.search(r'<tint>([\d.eE+\-]+)</tint>', xml_header)
    if tint_match:
        sample_period_s = float(tint_match.group(1))

    dlog_col_order = []
    for m in re.finditer(r'<channel id="(\d+)">(.*?)</channel>', xml_header, re.DOTALL):
        ch_id = int(m.group(1))
        ch_xml = m.group(2)
        sc = re.search(r'<sense_curr>(\d+)</sense_curr>', ch_xml)
        sv = re.search(r'<sense_volt>(\d+)</sense_volt>', ch_xml)
        if sv and sv.group(1) == '1':
            dlog_col_order.append(("volt", ch_id))
        if sc and sc.group(1) == '1':
            dlog_col_order.append(("curr", ch_id))

    num_traces = len(dlog_col_order)
    if num_traces == 0:
        return None, None

    close_tag = b'</dlog>'
    tag_pos = raw_data.find(close_tag)
    if tag_pos < 0:
        return None, None

    data_offset = tag_pos + len(close_tag) + 9
    if data_offset + num_traces * 4 > len(raw_data):
        return None, None

    data_section = raw_data[data_offset:]
    float_count = len(data_section) // 4
    num_samples = float_count // num_traces

    values_all = struct.unpack_from(f'>{float_count}f', data_section, 0)

    all_data = {}
    for col_idx, (meas_type, ch) in enumerate(dlog_col_order):
        values = [values_all[i * num_traces + col_idx] * 1000.0
                  for i in range(num_samples)]
        suffix = "I" if meas_type == "curr" else "V"
        label = f"CH{ch} {suffix}"
        if values:
            t = [i * sample_period_s for i in range(len(values))]
            all_data[label] = {"time": t, "values": values}

    for ch_id in sorted(set(c for _, c in dlog_col_order)):
        v_label = f"CH{ch_id} V"
        i_label = f"CH{ch_id} I"
        if v_label in all_data and i_label in all_data:
            v_vals = all_data[v_label]["values"]
            i_vals = all_data[i_label]["values"]
            t = all_data[v_label]["time"]
            p_vals = [v * i / 1000.0 for v, i in zip(v_vals, i_vals)]
            all_data[f"CH{ch_id} P"] = {"time": t, "values": p_vals}

    if not all_data:
        return None, None

    return all_data, raw_data

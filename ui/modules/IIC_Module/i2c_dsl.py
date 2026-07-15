# I2C 序列脚本 DSL 解析（变量 / 循环 / 条件 / 批量读取）

from PySide6.QtGui import QColor, QFont

from ui.modules.IIC_Module.i2c_constants import (
    _fmt_hex, _reg_addr_bits, _data_bits, _hex_digits,
)


def _strip_dsl_line(raw):
    """剥离注释与列表标记，返回净指令文本；空行返回 ''。"""
    # 行内注释 // 或 # （# 必须在行首或前面是空白才视为整行注释，行内 # 也剥）
    line = raw
    # 整行注释
    stripped = line.strip()
    if stripped.startswith("#") or stripped.startswith("//"):
        return ""
    # 行内 // 注释
    if "//" in line:
        line = line.split("//", 1)[0]
    line = line.strip()
    # 去掉前导 "- " 列表标记
    if line.startswith("-"):
        line = line[1:].strip()
    return line


def _parse_dsl_line(raw):
    """解析一行 DSL，返回指令 dict；空行/注释返回 None。

    数值解析规则（在执行时按 default_base 解析，这里只保留 token 字符串）：
      地址/寄存器相关参数 → 默认十六进制
      步长/延时/循环次数/位号 → 默认十进制
      0x 前缀 → 强制十六进制
      $ 前缀 → 变量
    """
    line = _strip_dsl_line(raw)
    if not line:
        return None
    parts = line.split()
    op = parts[0].upper()
    if op == "WRITE" and len(parts) >= 3:
        return {"type": "WRITE", "addr": parts[1], "value": parts[2]}
    if op == "READ":
        # READ addr  或  READ addr TO $var
        if len(parts) >= 4 and parts[2].upper() == "TO":
            var = parts[3]
            if var.startswith("$"):
                var = var[1:]
            return {"type": "READ", "addr": parts[1], "to": var}
        if len(parts) >= 2:
            return {"type": "READ", "addr": parts[1], "to": None}
        return None
    if op == "WRITE_BITS" and len(parts) >= 5:
        return {"type": "WRITE_BITS", "addr": parts[1],
                "high": parts[2], "low": parts[3], "value": parts[4]}
    if op == "DELAY" and len(parts) >= 2:
        return {"type": "DELAY", "ms": parts[1]}
    if op == "READ_RANGE" and len(parts) >= 3:
        cmd = {"type": "READ_RANGE", "start": parts[1], "stop": parts[2]}
        if len(parts) >= 4:
            cmd["step"] = parts[3]
        if len(parts) >= 5:
            cmd["delay"] = parts[4]
        return cmd
    if op == "LOOP" and len(parts) >= 2:
        return {"type": "LOOP", "count_expr": parts[1]}
    if op == "END_LOOP":
        return {"type": "END_LOOP"}
    if op == "IF" and len(parts) >= 2:
        # IF 后面全部为条件表达式
        cond = line[len(parts[0]):].strip()
        return {"type": "IF", "condition": cond}
    if op == "END_IF":
        return {"type": "END_IF"}
    # 无法识别 → 原样保留为注释型指令
    return {"type": "UNKNOWN", "raw": line}


def _build_ast(command_lines):
    """将 DSL 字符串列表解析为嵌套 AST。

    返回 (nodes, error_msg)。error_msg 非空表示语法错误。
    节点类型：
      ("CMD", parsed_dict)
      ("LOOP", count_expr, [body_nodes])
      ("IF", condition_str, [body_nodes])
    """
    parsed = []
    for raw in command_lines:
        p = _parse_dsl_line(raw)
        if p is not None:
            parsed.append(p)

    def parse_block(start, end_tokens):
        """返回 (nodes, end_index, error_msg)。"""
        nodes = []
        i = start
        while i < len(parsed):
            p = parsed[i]
            op = p["type"]
            if op in end_tokens:
                return nodes, i, None
            if op == "LOOP":
                body, end_i, err = parse_block(i + 1, {"END_LOOP"})
                if err:
                    return nodes, end_i, err
                if end_i >= len(parsed):
                    return nodes, len(parsed), "LOOP 缺少 END_LOOP"
                nodes.append(("LOOP", p["count_expr"], body))
                i = end_i + 1
            elif op == "IF":
                body, end_i, err = parse_block(i + 1, {"END_IF"})
                if err:
                    return nodes, end_i, err
                if end_i >= len(parsed):
                    return nodes, len(parsed), "IF 缺少 END_IF"
                nodes.append(("IF", p["condition"], body))
                i = end_i + 1
            elif op in ("END_LOOP", "END_IF"):
                # 多余的结束符
                return nodes, i, None
            else:
                nodes.append(("CMD", p))
                i += 1
        return nodes, i, None

    nodes, _end, err = parse_block(0, set())
    return nodes, err


# ---- 表达式 / 条件求值 ----

_SEQ_COND_OPS = ["==", "!=", ">=", "<=", ">", "<", "&", "|", "^"]


def _resolve_token(token, default_base, variables):
    """解析单个 token 为 int。

    - $var → 变量值（不存在为 0）
    - 0x 前缀 → 十六进制
    - 否则按 default_base 解析（16=十六进制默认, 10=十进制默认）
    """
    if token is None:
        return 0
    t = str(token).strip()
    if not t:
        return 0
    if t.startswith("$"):
        return int(variables.get(t[1:], 0))
    if t.lower().startswith("0x"):
        return int(t, 16)
    return int(t, default_base)


def _eval_expr(i2c, dev, width, expr, variables, emit, data_bits=16):
    """求值表达式，返回 int。

    支持：
      $var              → 变量值
      READ <addr>       → 执行读取，返回结果
      <number>          → 字面量（默认十六进制）
    """
    e = expr.strip()
    if not e:
        return 0
    if e.startswith("$"):
        return int(variables.get(e[1:], 0))
    up = e.upper()
    if up.startswith("READ "):
        # READ <addr>
        sub = _parse_dsl_line(e)
        if sub and sub.get("type") == "READ":
            addr = _resolve_token(sub["addr"], 16, variables)
            val = i2c.read(dev, addr, width)
            emit("    (IF-READ addr={0} => {1})".format(
                _fmt_hex(addr, _reg_addr_bits(width)),
                _fmt_hex(val, data_bits)))
            return val
        return 0
    # 字面量，默认十六进制
    return _resolve_token(e, 16, variables)


def _eval_condition(i2c, dev, width, cond_str, variables, emit, data_bits=16):
    """求值 IF 条件，返回 bool。"""
    cond = cond_str.strip()
    # 查找操作符（先查双字符）
    op_found = None
    left_str = cond
    right_str = ""
    for op in _SEQ_COND_OPS:
        # 用空格或直接连接都要匹配，找最早出现
        idx = _find_operator(cond, op)
        if idx >= 0:
            op_found = op
            left_str = cond[:idx].strip()
            right_str = cond[idx + len(op):].strip()
            break
    if op_found is None:
        # 无操作符：非零即真
        val = _eval_expr(i2c, dev, width, cond, variables, emit, data_bits)
        return val != 0
    left = _eval_expr(i2c, dev, width, left_str, variables, emit, data_bits)
    right = _eval_expr(i2c, dev, width, right_str, variables, emit, data_bits)
    if op_found == "==":
        return left == right
    if op_found == "!=":
        return left != right
    if op_found == ">":
        return left > right
    if op_found == "<":
        return left < right
    if op_found == ">=":
        return left >= right
    if op_found == "<=":
        return left <= right
    if op_found == "&":
        return (left & right) != 0
    if op_found == "|":
        return (left | right) != 0
    if op_found == "^":
        return (left ^ right) != 0
    return False


def _find_operator(text, op):
    """在 text 中查找操作符 op 的位置，避免拆散 0x 等；返回 -1 表示未找到。

    优先匹配带空格包围的形式；若无空格也接受。需保证双字符操作符先于单字符。
    """
    # 先找带空格的 " op "
    spaced = " {0} ".format(op)
    idx = text.find(spaced)
    if idx >= 0:
        return idx + 1
    # 再找无空格的（但避免匹配到 0x 中的字符等：& | ^ 不会出现在数字里，> < 也安全）
    idx = text.find(op)
    if idx >= 0:
        return idx
    return -1


# ---------------------------------------------------------------------------
# 序列脚本表格显示解析
# ---------------------------------------------------------------------------

_SEQ_ACTION_COLORS = {
    "W":  "#60a5fa",
    "R":  "#34d399",
    "WR": "#f59e0b",
    "LOOP":      "#a78bfa",
    "END_LOOP":  "#64748b",
    "IF":        "#a78bfa",
    "END_IF":    "#64748b",
    "DELAY":     "#2dd4bf",
    "READ_RANGE":"#22d3ee",
    "UNKNOWN":   "#94a3b8",
}


def _seq_action_color(action):
    return QColor(_SEQ_ACTION_COLORS.get(action, "#94a3b8"))


def _seq_bold_font():
    f = QFont()
    f.setBold(True)
    return f


def _seq_italic_font():
    f = QFont()
    f.setItalic(True)
    return f


def _parse_dsl_for_display(raw_line):
    """解析一行 DSL 用于表格显示，返回 display dict。

    返回字段：
      action: "W"/"R"/"WR" 或控制指令名 或 None
      addr, msb, lsb, value: 各列文本
      desc: 行内注释文本（仅支持 // 注释符；# 是 YAML 原生注释，
            PyYAML 加载时已丢弃，不会到达此处）
      is_comment: True 表示整行注释（需跨全部列显示）
      is_control: True 表示逻辑/控制指令（需跨前4列显示）
      full_text: 跨列显示时的完整文本（已剥除前导 "- " 列表标记）
    """
    line = raw_line or ""
    desc = ""
    code = line
    if "//" in code:
        code, desc = code.split("//", 1)
        desc = desc.strip()
    code = code.strip()
    if code.startswith("-"):
        code = code[1:].strip()
    # 整行 // 注释（剥后已空）：full_text 只显示注释内容，剥掉前导 "- //"
    if not code and "//" in line:
        full = line.strip()
        # 剥掉前导 "- " 列表标记
        if full.startswith("- "):
            full = full[2:].strip()
        elif full.startswith("-"):
            full = full[1:].strip()
        # 剥掉行首 "// " 注释符，只保留描述文本
        if full.startswith("//"):
            full = full[2:].lstrip()
        return {
            "action": None, "addr": "", "msb": "", "lsb": "",
            "value": "", "desc": "",
            "is_comment": True, "is_control": False,
            "full_text": full,
        }

    if not code:
        return {
            "action": None, "addr": "", "msb": "", "lsb": "",
            "value": "", "desc": "",
            "is_comment": True, "is_control": False,
            "full_text": line.strip(),
        }

    parts = code.split()
    op = parts[0].upper() if parts else ""

    if op == "WRITE" and len(parts) >= 3:
        return {
            "action": "W", "addr": parts[1], "msb": "", "lsb": "",
            "value": parts[2], "desc": desc,
            "is_comment": False, "is_control": False, "full_text": "",
        }
    if op == "READ":
        addr = parts[1] if len(parts) >= 2 else ""
        return {
            "action": "R", "addr": addr, "msb": "", "lsb": "",
            "value": "", "desc": desc,
            "is_comment": False, "is_control": False, "full_text": "",
        }
    if op == "WRITE_BITS" and len(parts) >= 5:
        return {
            "action": "WR", "addr": parts[1], "msb": parts[2],
            "lsb": parts[3], "value": parts[4], "desc": desc,
            "is_comment": False, "is_control": False, "full_text": "",
        }
    if op in ("DELAY", "LOOP", "END_LOOP", "IF", "END_IF", "READ_RANGE"):
        return {
            "action": op, "addr": "", "msb": "", "lsb": "",
            "value": "", "desc": desc,
            "is_comment": False, "is_control": True,
            "full_text": code,
        }
    return {
        "action": "UNKNOWN", "addr": "", "msb": "", "lsb": "",
        "value": "", "desc": desc,
        "is_comment": False, "is_control": True,
        "full_text": code,
    }


_SEQ_CMD_TYPES = ["WRITE", "READ", "WRITE_BITS", "DELAY", "READ_RANGE",
                  "LOOP", "END_LOOP", "IF", "END_IF"]

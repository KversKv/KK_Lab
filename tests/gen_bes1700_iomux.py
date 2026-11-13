#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BES1700 iomux 表 → chips/gpio_configs/bes1700.json func_sel.functions 注入。

从 Temp_Docs/docs/bes1700_IOMUX.xlsx 的 BES2800BP-JE6 sheet 提取每脚
Function 1~9 复用功能名（源表 Function N → sel 位域值 N，sel=0 保留未用置 null，
空单元格 = 该值未用，写为 null），合并写回 bes1700.json 的 func_sel.functions
（键 GPIO_P{G}_{P}，其余字段原样保留）。
xlsx "Pin name" 列为扁平命名 GPIO{G}{P}（如 GPIO117 = Group11 Pin7）；
GPIO32~37 物理无 iomux，源表未收录。
"""

import json
import os
import re

import openpyxl

XLSX_PATH = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "Temp_Docs", "docs", "bes1700_IOMUX.xlsx")
JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "chips", "gpio_configs", "bes1700.json")

PIN_NAME_COL = 1            # "Pin name" 列（GPIO{G}{P} 扁平命名）
FUNC_FIRST_COL = 4          # Function 1 列，其后 Function N 连续排布
FUNC_COUNT = 9              # Function 1 ~ Function 9 → sel 位域值 1~9


def extract_functions(xlsx_path):
    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    ws = wb["BES2800BP-JE6"]
    rows = list(ws.iter_rows(values_only=True))
    functions = {}
    for row in rows[1:]:
        port = row[PIN_NAME_COL] if len(row) > PIN_NAME_COL else None
        if port is None or not str(port).strip():
            continue
        m = re.fullmatch(r"GPIO(\d+)(\d)", str(port).strip().upper())
        if not m:
            raise SystemExit("Pin name 格式异常: {0!r}".format(port))
        key = "GPIO_P{0}_{1}".format(int(m.group(1)), int(m.group(2)))
        # sel=0 保留未用：列表首位补 null，Function N 置于 index N
        names = [None]
        for n in range(FUNC_COUNT):
            col = FUNC_FIRST_COL + n
            value = row[col] if col < len(row) else None
            text = str(value).strip() if value is not None else ""
            names.append(text or None)
        functions[key] = names
    return functions


def main():
    functions = extract_functions(XLSX_PATH)
    if not functions:
        raise SystemExit("xlsx 未提取到任何 GPIO 行")
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    fsel = cfg.get("func_sel") or {}
    # 重建字段顺序：functions 紧随 groups，comment 收尾
    ordered = {}
    for key in ("base", "bits_per_gpio", "gpio_value", "groups"):
        if key in fsel:
            ordered[key] = fsel[key]
    ordered["functions"] = functions
    for key, value in fsel.items():
        if key not in ordered and key != "functions":
            ordered[key] = value
    cfg["func_sel"] = ordered
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(" injected {0} ports into {1}".format(len(functions), JSON_PATH))


if __name__ == "__main__":
    main()

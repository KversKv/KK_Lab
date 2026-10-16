#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BEST3601P iomux 表 → chips/gpio_configs/best3601p.json func_sel.functions 注入。

从 Temp/bes3601P_iomux.xlsx 的 iomux sheet 提取每脚 Func_0~Func_8 复用功能名
（列 index = func_sel 位域值，空单元格 = 该值未用，写为 null），
合并写回 best3601p.json 的 func_sel.functions（键 GPIO_P{G}_{P}，其余字段原样保留）。
"""

import json
import os
import re

import openpyxl

XLSX_PATH = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "Temp", "bes3601P_iomux.xlsx")
JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "chips", "gpio_configs", "best3601p.json")

GPIO_PORT_COL = 3           # GPIO_PORT 列（GPIO_P{G}_{P}）
FUNC_FIRST_COL = 4          # Func_0 列，其后每个 Func_N 间隔一列 dir
FUNC_COUNT = 9              # Func_0 ~ Func_8


def extract_functions(xlsx_path):
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb["iomux"]
    rows = list(ws.iter_rows(values_only=True))
    functions = {}
    for row in rows[1:]:
        port = row[GPIO_PORT_COL]
        if port is None or not re.fullmatch(r"GPIO_P\d+_\d+",
                                            str(port).strip()):
            continue
        names = []
        for n in range(FUNC_COUNT):
            col = FUNC_FIRST_COL + 2 * n
            value = row[col] if col < len(row) else None
            text = str(value).strip() if value is not None else ""
            names.append(text or None)
        functions[str(port).strip()] = names
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

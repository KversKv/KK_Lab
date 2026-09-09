"""Module Test 单项结果保存 / 聚合导出（final 汇总报告）。

用途：某一项 Fail 后只勾选重测该项，逐项「保存结果」落盘；最后从已保存
结果中挑选若干项聚合生成一份完整报告，避免每次全量重测。

目录约定（均在 ``Results/`` 下，已 gitignore）::

    Results/module_test/{module_type}/saved/{item_key}/{YYYYMMDD_HHMMSS}/
        result.json     # 元信息 + ItemResult 序列化（资产路径相对本目录）
        {item_key}.csv  # 资产按「原运行输出目录相对路径」结构化落盘
        screenshots/... # （如 screenshots/foo.png），与正常输出目录布局一致
    Results/module_test/{module_type}/final/{芯片}_{模块}_{条件}_{时间戳}/
        {item_key}.csv / screenshots/...   # 原始文件按原布局聚合还原
        report.html / report.pdf / XLSX/...

聚合导出走与正常运行一致的 ``save_html_report``（含单项 XLSX、可选 PDF），
保证汇总报告与单次运行报告版式完全一致。
"""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
from datetime import datetime
from typing import Any

from PySide6.QtCore import QObject, Signal

from core.module_test.report import save_html_report
from core.module_test.result_model import ItemResult, ModuleTestResult
from log_config import get_logger

logger = get_logger(__name__)

_SCHEMA_VERSION = 1
_ENTRY_JSON = "result.json"
_INVALID_DIR_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')


# ---------------------------------------------------------------------- 路径
def saved_root(module_type: str) -> str:
    """已保存单项结果根目录。"""
    return os.path.join("Results", "module_test", module_type, "saved")


def final_root(module_type: str) -> str:
    """聚合导出（final）根目录。"""
    return os.path.join("Results", "module_test", module_type, "final")


def _safe_dir_part(text: str) -> str:
    """清洗用户输入为合法目录名片段（与 _runner_base 同规则）。"""
    return _INVALID_DIR_CHARS.sub("_", text.strip()).strip(" .")


# ---------------------------------------------------------------------- 保存
def _rel_to_out_dir(src: str, out_dir_root: str | None) -> str:
    """资产路径 → 相对原运行输出目录的路径（JSON/落盘统一用 '/'）。

    不在输出目录内（或无法计算）时退化为文件名（落在条目根）。
    """
    if out_dir_root:
        try:
            rel = os.path.relpath(src, out_dir_root)
        except ValueError:  # 跨盘符
            rel = ""
        if rel and not rel.startswith(".."):
            return rel.replace(os.sep, "/")
    return os.path.basename(src)


def _copy_asset(src: str | None, entry_dir: str, out_dir_root: str | None,
                copied: dict[str, str]) -> str | None:
    """把资产文件按原输出目录相对布局拷入条目目录，返回相对条目目录路径。

    ``copied`` 按源绝对路径去重（waveform_png 常与 screenshots[0] 同文件）。
    """
    if not src or not os.path.isfile(src):
        return None
    key = os.path.normcase(os.path.abspath(src))
    if key in copied:
        return copied[key]
    rel = _rel_to_out_dir(src, out_dir_root)
    dst = os.path.join(entry_dir, rel)
    os.makedirs(os.path.dirname(dst) or entry_dir, exist_ok=True)
    try:
        shutil.copy2(src, dst)
    except OSError:
        logger.error("复制结果资产失败: %s -> %s", src, dst, exc_info=True)
        return None
    copied[key] = rel
    return rel


def save_item_result(module_type: str, item: ItemResult,
                     source: ModuleTestResult) -> str:
    """把单个测试项结果（含 CSV/截图等资产）落盘，返回条目目录。

    ``source`` 为产生该结果的本次运行汇总（提供芯片/模块/测试条件/仪器等
    元信息）。资产按「原运行输出目录相对路径」结构化落盘（如
    ``{item_key}.csv`` 在条目根、``screenshots/`` 逐点截图），JSON 中存
    相对条目目录路径，加载/导出时再解析还原。
    """
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(saved_root(module_type), _safe_dir_part(item.item_key))
    entry_dir = os.path.join(base, stamp)
    n = 2
    while os.path.exists(entry_dir):  # 同秒重复保存兜底
        entry_dir = os.path.join(base, f"{stamp}_{n}")
        n += 1
    os.makedirs(entry_dir, exist_ok=True)

    out_dir_root = (source.summary or {}).get("output_dir") or None
    copied: dict[str, str] = {}
    measured = copy.deepcopy(item.measured)
    if isinstance(measured, dict):
        shots = measured.get("screenshots")
        if isinstance(shots, list):
            for s in shots:
                if isinstance(s, dict) and s.get("png"):
                    s["png"] = _copy_asset(str(s["png"]), entry_dir,
                                           out_dir_root, copied)
    raw_csv = _copy_asset(item.raw_csv_path, entry_dir, out_dir_root, copied)
    waveform = _copy_asset(item.waveform_png, entry_dir, out_dir_root, copied)

    payload = {
        "version": _SCHEMA_VERSION,
        "module_type": module_type,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "meta": {
            "chip_name": source.chip_name,
            "module_name": source.module_name,
            "test_condition": source.test_condition,
            "operator": source.operator,
            "temperature": source.temperature,
            "instruments": list(source.instruments or []),
        },
        "item": {
            "item_key": item.item_key,
            "name": item.name,
            "unit": item.unit,
            "passed": item.passed,
            "measured": measured,
            "raw_csv_path": raw_csv,
            "waveform_png": waveform,
            "notes": item.notes,
            "ts": item.ts,
            "duration_s": item.duration_s,
        },
    }
    json_path = os.path.join(entry_dir, _ENTRY_JSON)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    logger.info("测试项结果已保存: %s", json_path)
    return entry_dir


# ---------------------------------------------------------------------- 读取
def _resolve(entry_dir: str, rel: str | None) -> str | None:
    """相对条目目录的资产路径 → 绝对路径。"""
    if not rel:
        return None
    return os.path.normpath(os.path.join(entry_dir, rel))


def _read_entry(entry_dir: str) -> dict[str, Any] | None:
    """读取单个已保存条目（result.json）；损坏返回 None。"""
    json_path = os.path.join(entry_dir, _ENTRY_JSON)
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        logger.error("读取已保存结果失败: %s", json_path, exc_info=True)
        return None
    if not isinstance(data, dict) or not isinstance(data.get("item"), dict):
        return None
    return data


def _entry_to_item(entry_dir: str, data: dict[str, Any]) -> ItemResult:
    """反序列化 ItemResult（资产相对路径解析回绝对路径）。"""
    d = data["item"]
    measured = d.get("measured")
    if isinstance(measured, dict):
        shots = measured.get("screenshots")
        if isinstance(shots, list):
            for s in shots:
                if isinstance(s, dict) and s.get("png"):
                    s["png"] = _resolve(entry_dir, str(s["png"]))
    return ItemResult(
        item_key=str(d.get("item_key", "")),
        name=str(d.get("name", "")),
        unit=str(d.get("unit", "")),
        passed=d.get("passed"),
        measured=measured,
        raw_csv_path=_resolve(entry_dir, d.get("raw_csv_path")),
        waveform_png=_resolve(entry_dir, d.get("waveform_png")),
        notes=str(d.get("notes", "")),
        ts=str(d.get("ts", "")),
        duration_s=d.get("duration_s"),
    )


def list_saved_results(module_type: str) -> list[dict[str, Any]]:
    """扫描已保存条目（按保存时间倒序），供导出选择弹窗展示。

    每条：``{dir, item_key, name, passed, verdict, saved_at, chip_name,
    module_name, test_condition}``；损坏条目跳过。
    """
    root = saved_root(module_type)
    entries: list[dict[str, Any]] = []
    if not os.path.isdir(root):
        return entries
    for item_dir in sorted(os.listdir(root)):
        item_path = os.path.join(root, item_dir)
        if not os.path.isdir(item_path):
            continue
        for stamp in sorted(os.listdir(item_path), reverse=True):
            entry_dir = os.path.join(item_path, stamp)
            if not os.path.isdir(entry_dir):
                continue
            data = _read_entry(entry_dir)
            if data is None:
                continue
            d = data["item"]
            meta = data.get("meta") or {}
            passed = d.get("passed")
            entries.append({
                "dir": entry_dir,
                "item_key": str(d.get("item_key", "")),
                "name": str(d.get("name", "")),
                "passed": passed,
                "verdict": ("PASS" if passed is True
                            else "FAIL" if passed is False else "N/A"),
                "saved_at": str(data.get("saved_at", "")),
                "chip_name": str(meta.get("chip_name", "")),
                "module_name": str(meta.get("module_name", "")),
                "test_condition": str(meta.get("test_condition", "")),
            })
    entries.sort(key=lambda e: e["saved_at"], reverse=True)
    return entries


# ---------------------------------------------------------------------- 聚合导出
def _copy_into_out_dir(src: str | None, entry_dir: str, out_dir: str,
                       copied: dict[str, str]) -> str | None:
    """把条目内资产按原相对布局复制进聚合输出目录，返回新绝对路径。

    同一测试项的多次保存被同时勾选时相对路径相同，后拷的加条目时间戳前缀
    防覆盖；``copied`` 按源绝对路径去重。
    """
    if not src or not os.path.isfile(src):
        return None
    key = os.path.normcase(os.path.abspath(src))
    if key in copied:
        return copied[key]
    rel = os.path.relpath(src, entry_dir)
    if rel.startswith(".."):  # 兜底：不在条目目录内时按文件名落根
        rel = os.path.basename(src)
    dst = os.path.normpath(os.path.join(out_dir, rel))
    if os.path.exists(dst):
        stem, ext = os.path.splitext(os.path.basename(dst))
        dst = os.path.join(os.path.dirname(dst),
                           f"{os.path.basename(entry_dir)}_{stem}{ext}")
    os.makedirs(os.path.dirname(dst) or out_dir, exist_ok=True)
    try:
        shutil.copy2(src, dst)
    except OSError:
        logger.error("复制资产到聚合目录失败: %s -> %s", src, dst,
                     exc_info=True)
        return None
    copied[key] = dst
    return dst


def _materialize_item(entry_dir: str, data: dict[str, Any], out_dir: str,
                      copied: dict[str, str]) -> ItemResult:
    """反序列化 ItemResult，并把资产按原布局还原进聚合输出目录、重指路径。"""
    item = _entry_to_item(entry_dir, data)
    for attr in ("raw_csv_path", "waveform_png"):
        new = _copy_into_out_dir(getattr(item, attr), entry_dir, out_dir,
                                 copied)
        if new:
            setattr(item, attr, new)
    measured = item.measured
    if isinstance(measured, dict):
        shots = measured.get("screenshots")
        if isinstance(shots, list):
            for s in shots:
                if isinstance(s, dict) and s.get("png"):
                    new = _copy_into_out_dir(str(s["png"]), entry_dir,
                                             out_dir, copied)
                    if new:
                        s["png"] = new
    return item


def export_saved_results(module_type: str,
                         entry_dirs: list[str]) -> tuple[str, str | None, str]:
    """把选中的已保存条目聚合为一份完整报告，导出到 ``final/`` 目录。

    原始文件（``{item_key}.csv``、``screenshots/`` 等）按正常运行输出目录
    布局还原进聚合目录，保证与直接生成的报告目录内容一致。
    返回 ``(html_path, pdf_path, out_dir)``；``entry_dirs`` 顺序即报告项顺序。
    """
    pairs: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for entry_dir in entry_dirs:
        data = _read_entry(entry_dir)
        if data is None:
            continue
        meta = dict(data.get("meta") or {})
        meta["saved_at"] = str(data.get("saved_at", ""))
        pairs.append((entry_dir, data, meta))
    if not pairs:
        raise ValueError("未选择有效的已保存结果")

    # 元信息取选中条目中保存时间最新的一份（芯片/模块/条件/仪器以最新为准）
    base_meta = max((m for _, _, m in pairs), key=lambda m: m.get("saved_at", ""))
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parts = [p for p in (
        _safe_dir_part(str(base_meta.get("chip_name", ""))),
        _safe_dir_part(str(base_meta.get("module_name", ""))),
        _safe_dir_part(str(base_meta.get("test_condition", ""))),
    ) if p]
    parts.append(stamp)
    out_dir = os.path.join(final_root(module_type), "_".join(parts))
    os.makedirs(out_dir, exist_ok=True)

    copied: dict[str, str] = {}
    items = [_materialize_item(d, data, out_dir, copied)
             for d, data, _ in pairs]
    result = ModuleTestResult(
        module_type=module_type,
        chip_name=str(base_meta.get("chip_name", "")),
        module_name=str(base_meta.get("module_name", "")),
        test_condition=str(base_meta.get("test_condition", "")),
        operator=str(base_meta.get("operator", "")),
        temperature=str(base_meta.get("temperature", "")),
        instruments=list(base_meta.get("instruments") or []),
        items=items,
    )
    ts_list = [it.ts for it in items if it.ts]
    result.started_at = min(ts_list) if ts_list else ""
    result.finished_at = max(ts_list) if ts_list else ""
    result.build_summary()

    html_path, pdf_path = save_html_report(result, out_dir)
    logger.info("已保存结果聚合报告已生成: %s", html_path)
    return html_path, pdf_path, out_dir


class SavedResultsExportWorker(QObject):
    """聚合导出后台 Worker（QObject + moveToThread，避免 PDF 无头打印阻塞 UI）。

    Signals:
        log(str): 日志行。
        finished(bool, str, str): (是否成功, 消息/输出目录, 报告 HTML 路径)。
    """

    log = Signal(str)
    finished = Signal(bool, str, str)

    def __init__(self, module_type: str, entry_dirs: list[str], parent=None):
        super().__init__(parent)
        self._module_type = module_type
        self._entry_dirs = list(entry_dirs)

    def run(self) -> None:
        try:
            html_path, pdf_path, out_dir = export_saved_results(
                self._module_type, self._entry_dirs)
        except Exception:  # noqa: BLE001 - 导出失败回 UI 提示
            logger.error("聚合导出已保存结果失败", exc_info=True)
            self.finished.emit(False, "导出失败，详见日志", "")
            return
        self.log.emit(f"[EXPORT] 汇总报告已生成: {html_path}")
        if pdf_path:
            self.log.emit(f"[EXPORT] PDF 报告已生成: {pdf_path}")
        self.finished.emit(True, out_dir, html_path)

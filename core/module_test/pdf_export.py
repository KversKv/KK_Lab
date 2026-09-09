"""Module Test 报告 PDF 导出（系统 Edge/Chrome 无头打印）。

HTML 报告为纯 JS 渲染的单文件（数据 = REPORT_DATA JSON），非浏览器排版引擎
（weasyprint / reportlab 等）无法复用其图表与表格渲染；故 PDF 导出走系统已装
Chromium 内核浏览器 headless --print-to-pdf。调用方传入打印变体 HTML
（report._to_print_variant：@media print 提为基础版式 + 版心锁 180mm +
boot 同步全量渲染），页面 load 前即渲染完成，不依赖 headless 下触发不可靠的
beforeprint 事件，也无需 --virtual-time-budget（其与新 headless 组合在部分
Chromium 版本会挂起）。

纯 subprocess 实现无 Qt；未找到浏览器或打印失败抛 RuntimeError，
由调用方（report.save_html_report）best-effort 降级（WARN 不阻断）。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from log_config import get_logger

logger = get_logger(__name__)

# Edge 优先（Win10/11 系统自带），Chrome 兜底
_BROWSER_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)
_TIMEOUT_S = 180          # 单次打印超时（含浏览器冷启动）


def find_browser() -> str | None:
    """定位可用 Chromium 内核浏览器（Edge 优先，Win10/11 系统自带）。"""
    for exe in ("msedge", "chrome"):
        found = shutil.which(exe)
        if found:
            return found
    for path in _BROWSER_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None


def _print_once(browser: str, html_path: str, pdf_path: str,
                headless_flag: str) -> bool:
    """执行一次无头打印，返回是否产出非空 PDF。"""
    cmd = [
        browser,
        headless_flag,
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",  # 旧版 Chromium 别名，未知开关会被忽略
        f"--print-to-pdf={pdf_path}",
        Path(html_path).resolve().as_uri(),  # 中文路径需 percent-encode
    ]
    with tempfile.TemporaryDirectory(prefix="kk_lab_pdf_") as profile:
        # 独立临时 profile：避免与已打开的 Edge/Chrome 用户配置锁冲突
        cmd.append(f"--user-data-dir={profile}")
        try:
            proc = subprocess.run(
                cmd, capture_output=True, timeout=_TIMEOUT_S,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired:
            logger.warning("PDF 导出超时（%ss，%s）: %s",
                           _TIMEOUT_S, headless_flag, html_path)
            return False
        except OSError:
            logger.warning("PDF 导出启动浏览器失败: %s", browser, exc_info=True)
            return False
    if os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 1024:
        return True
    err = (proc.stderr or b"").decode("utf-8", "replace").strip()
    logger.warning("PDF 导出未产出有效文件（%s），stderr: %s",
                   headless_flag, err[-500:] or "<empty>")
    return False


def export_pdf_from_html(html_path: str, pdf_path: str,
                         html_text: str | None = None) -> str:
    """把单文件 HTML 报告打印为 PDF，成功返回 pdf_path。

    ``html_text`` 提供时（打印变体，见 report._to_print_variant）先落临时
    文件再打印（数据全内联无相对资源依赖），结束后删除。

    Raises:
        RuntimeError: 未找到浏览器 / 两次尝试（new headless 与旧 headless）
            均未产出有效 PDF。
    """
    browser = find_browser()
    if not browser:
        raise RuntimeError("未找到 Edge/Chrome 浏览器，无法导出 PDF 报告")
    # 相对路径会被 Chromium 解析到临时 user-data-dir 下（随后被清理），必须绝对化
    pdf_path = os.path.abspath(pdf_path)
    logger.info("PDF 导出浏览器: %s", browser)
    if os.path.isfile(pdf_path):
        os.remove(pdf_path)
    tmp_path = None
    src = html_path
    if html_text is not None:
        fd, tmp_path = tempfile.mkstemp(suffix=".html", prefix="kk_lab_rpt_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html_text)
        src = tmp_path
    try:
        for headless_flag in ("--headless=new", "--headless"):
            if _print_once(browser, src, pdf_path, headless_flag):
                logger.info("PDF 报告已生成: %s（浏览器: %s）", pdf_path, browser)
                return pdf_path
            if os.path.isfile(pdf_path):
                os.remove(pdf_path)  # 清掉无效产物再重试
        raise RuntimeError(f"PDF 导出失败（浏览器: {browser}）: {pdf_path}")
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:  # noqa: BLE001 - 临时文件清理失败不影响结果
                pass

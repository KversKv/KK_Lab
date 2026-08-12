# -*- coding: utf-8 -*-
# 临时工具：从 PDF 数据手册提取文本（调试用，见 AGENTS.md 规则11）
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "_pdfdeps"))

from pypdf import PdfReader  # noqa: E402


def extract(pdf_path, out_path):
    reader = PdfReader(pdf_path)
    parts = []
    for i, page in enumerate(reader.pages):
        parts.append(f"\n===== PAGE {i + 1} =====\n")
        try:
            parts.append(page.extract_text() or "")
        except Exception as e:  # noqa: BLE001
            parts.append(f"<extract error: {e}>")
    text = "\n".join(parts)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"{os.path.basename(pdf_path)} -> {out_path} ({len(text)} chars)")


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    extract(os.path.join(base, "DS_AWP37702_EN_V1.1.pdf"),
            os.path.join(base, "awp37702.txt"))
    extract(os.path.join(base, "DS_AWP37701Z_EN_V1.2.pdf"),
            os.path.join(base, "awp37701z.txt"))

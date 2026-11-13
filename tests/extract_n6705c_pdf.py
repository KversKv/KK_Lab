"""Extract Keysight N6705C Programmer's Reference Guide (PDF) to structured Markdown.

Font-based line classification (KeysightSansLight sizes 20/15/13/11 = headings,
CourierNewPSMT = SCPI code, 10/9/8pt = body), plus x-coordinate table
reconstruction for "Parameters" and "SCPI Command / Description" tables.
"""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

PDF_PATH = Path(r"d:\CodeProject\TRAE_Projects\KK_Lab\Temp_Docs\N6705C_编程指南.pdf")
OUT_DIR = Path(r"d:\CodeProject\TRAE_Projects\KK_Lab\instruments\power\keysight\n6705c_programming_guide")

TOP_CUT = 55.0   # drop page header zone
BOT_CUT = 740.0  # drop page footer zone

CHAPTER_FILES = {
    1: "01_introduction",
    2: "02_scpi_language",
    4: "04_quick_reference",
    5: "05_programming_examples",
    6: "06_error_messages",
}

PARAM_HDR = re.compile(r"^Name\s+Type\s+Range\s+of\s+Values\s+Default\s+Value$", re.I)
QUICK_HDR = re.compile(r"^SCPI\s+Command(\s+\([^)]*\))?\s+Description$", re.I)
BIT_HDR = re.compile(r"^Bit\s+Number\s+Decimal(\s+Value)?\s+Definition$", re.I)
RANGE_SEC_HDR = re.compile(r"^Range\s+in\s+seconds\s+Resolution$", re.I)
INTRO_HDR = re.compile(r"^(.*?)\s+(?:Commands|Subsystem)\s+Introduction$")
CHAPTER_NUM = re.compile(r"^(\d)\s+\S")
TOC_DOTS = re.compile(r"\.{5,}")
SENTENCE_END = tuple('.!?"\'')
PAREN_END = ")"  # weak ending: joins only across tight line gaps
FORCE_NEW_PARA = [
    re.compile(r"^NOTE\b"),
    re.compile(r"^[-•▪◦]\s"),
    re.compile(r"^\*\w"),                      # *RST, *IDN? ...
    re.compile(r"^-?\d{1,3},\s"),              # SCPI error codes
    re.compile(r"^\(?\d{1,2}[\).]\s"),         # numbered list
    re.compile(r"^\[*[A-Za-z]+:\[?[A-Za-z]"),   # SCPI subsystem command
]


def extract_lines(page):
    words = page.extract_words(extra_attrs=["size", "fontname"], x_tolerance=2, y_tolerance=2)
    words = [w for w in words if TOP_CUT < w["top"] < BOT_CUT]
    words.sort(key=lambda w: (round(w["top"], 1), w["x0"]))
    grouped = []
    for w in words:
        if grouped and abs(grouped[-1][0]["top"] - w["top"]) < 2.5:
            grouped[-1].append(w)
        else:
            grouped.append([w])
    lines = []
    for ws in grouped:
        ws.sort(key=lambda w: w["x0"])
        lines.append({
            "text": " ".join(w["text"] for w in ws),
            "size": max(w["size"] for w in ws),
            "x0": min(w["x0"] for w in ws),
            "code": all("Courier" in w["fontname"] for w in ws),
            "top": ws[0]["top"],
            "words": ws,
        })
    return lines


def classify(line):
    if line["code"]:
        return "code"
    s = line["size"]
    if s >= 18:
        return "h1"
    if s >= 14:
        return "h2"
    if s >= 12.5:
        return "h3"
    if s >= 10.8:
        return "h4"
    return "body"


def esc(text):
    text = text.replace("\\", "\\\\")
    for a, b in (("*", "\\*"), ("<", "\\<"), (">", "\\>")):
        text = text.replace(a, b)
    return text


def esc_cell(text):
    return esc(text).replace("|", "\\|")


LOWER_RUN = re.compile(r"[a-z]+ [a-z]+ [a-z]+")


def looks_like_cmd(text):
    """Body-font line inside a Syntax box that is actually a SCPI command."""
    if text.endswith(".") or len(text) > 120:
        return False
    if not re.match(r"^[*A-Za-z][\w:\[\]]*", text):
        return False
    return not LOWER_RUN.search(text)


class Builder:
    def __init__(self):
        self.out = []
        self.para_open = False
        self.code_open = False
        self.table = None  # {"cols_x": [...], "header": [...]}
        self.prev_body = None  # {"text","x0","top","size"}
        self.in_syntax = False  # current section is a Syntax box

    def _blank(self):
        if self.out and self.out[-1] != "":
            self.out.append("")

    def _close_para(self):
        self.para_open = False
        self.prev_body = None

    def _close_code(self):
        if self.code_open:
            self.out.append("```")
            self.out.append("")
            self.code_open = False

    def _close_table(self):
        self.table = None

    def add_heading(self, level, text):
        self._close_code()
        self._close_table()
        self._close_para()
        self._blank()
        self.out.append("#" * level + " " + esc(text))
        self.out.append("")
        self.in_syntax = text.strip().lower() in ("syntax", "query syntax")

    def add_code(self, text):
        self._close_para()
        self._close_table()
        if not self.code_open:
            self._blank()
            self.out.append("```")
            self.code_open = True
        self.out.append(text)

    def _split_row(self, words, cols_x, tol=8):
        cells = [[] for _ in cols_x]
        for w in words:
            for i in range(len(cols_x) - 1, -1, -1):
                if w["x0"] >= cols_x[i] - tol:
                    cells[i].append(w["text"])
                    break
            else:
                cells[0].append(w["text"])
        return [" ".join(c) for c in cells]

    def _start_table(self, line, header_names, key_words, bit_mode=False):
        self._close_para()
        self._close_code()
        cols_x = []
        for kw in key_words:
            for w in line["words"]:
                if w["text"].lower() == kw:
                    cols_x.append(w["x0"])
                    break
        if len(cols_x) != len(key_words):
            return False
        self._blank()
        self.out.append("| " + " | ".join(header_names) + " |")
        self.out.append("|" + "---|" * len(header_names))
        # bit tables: "Value" may be a second header line to skip
        skip_value = bit_mode and "value" not in line["text"].lower()
        self.table = {"cols_x": cols_x, "rows": 0, "bit": bit_mode, "skip_value": skip_value}
        return True

    @staticmethod
    def _near(x, targets, tol=10):
        return any(abs(x - t) <= tol for t in targets)

    def _add_table_line(self, line):
        """Add a line to the open table. Return False if it is prose after the table."""
        if self.table["skip_value"]:
            self.table["skip_value"] = False
            if line["text"].strip() == "Value":
                return True  # second header line of a bit table
        cols_x = self.table["cols_x"]
        cells = self._split_row(line["words"], cols_x)
        if self.table["bit"]:
            row_start = bool(cells[0]) and bool(cells[1]) and self._near(line["x0"], cols_x[:1])
        else:
            row_start = bool(cells[0])
        if row_start:
            self.out.append("| " + " | ".join(esc_cell(c) for c in cells) + " |")
            self.table["rows"] += 1
            return True
        # wrapped cell fragments start near a column; anything else is prose
        if not self._near(line["x0"], cols_x):
            return False
        if not self.table["bit"]:
            used = sum(1 for c in cells if c)
            if self.table["rows"] == 0 or used >= 3 or (used >= 2 and len(line["words"]) > 8):
                return False  # dense full-width prose below the table
        elif self.table["rows"] == 0:
            return False
        prev = self.out[-1]
        prev_cells = [c.strip() for c in re.split(r"(?<!\\)\|", prev.strip())[1:-1]]
        for i, c in enumerate(cells):
            if c and i < len(prev_cells):
                sep = "" if prev_cells[i].endswith("-") else " "
                prev_cells[i] = (prev_cells[i] + sep + esc_cell(c)).strip()
        self.out[-1] = "| " + " | ".join(prev_cells) + " |"
        return True

    def add_body(self, line, force_note=False):
        text = line["text"]
        if self.code_open:
            self._close_code()
        # table header detection first: a repeated header starts a new table
        if PARAM_HDR.match(text):
            if self._start_table(line, ["Name", "Type", "Range of Values", "Default Value"],
                                 ["name", "type", "range", "default"]):
                return
        elif QUICK_HDR.match(text):
            if self._start_table(line, ["SCPI Command", "Description"],
                                 ["scpi", "description"]):
                return
        elif BIT_HDR.match(text):
            if self._start_table(line, ["Bit Number", "Decimal Value", "Definition"],
                                 ["bit", "decimal", "definition"], bit_mode=True):
                return
        elif RANGE_SEC_HDR.match(text):
            if self._start_table(line, ["Range in seconds", "Resolution"],
                                 ["range", "resolution"]):
                return
        if self.table is not None:
            if self._add_table_line(line):
                return
            self._close_table()  # fall through: prose below the table
        if force_note:
            note_text = re.sub(r"^NOTE\s*", "", text)
            # NOTE label floats mid-paragraph: previous line is part of the same note
            if (
                self.para_open
                and self.prev_body is not None
                and not self.prev_body["text"].endswith(SENTENCE_END)
                and abs(line["x0"] - self.prev_body["x0"]) < 12
            ):
                prev_text = self.out.pop()
                if not prev_text.startswith("> **NOTE** "):
                    prev_text = "> **NOTE** " + prev_text
                self.out.append(prev_text + " " + esc(note_text))
            else:
                self._blank()
                self.out.append("> **NOTE** " + esc(note_text))
            self.para_open = True
            self.prev_body = line
            return
        # paragraph reflow
        join = False
        if self.para_open and self.prev_body is not None:
            prev = self.prev_body
            gap = line["top"] - (prev["top"] + prev["size"])
            prev_words = prev["text"].split()
            prev_last = prev_words[-1] if prev_words else ""
            # prev line clearly ends mid-sentence -> always join
            mid_sentence = (
                bool(prev_last)
                and prev_last[0].islower()
                and not prev["text"].endswith(SENTENCE_END)
            )
            force_ok = mid_sentence or not any(p.match(text) for p in FORCE_NEW_PARA)
            tight = gap < 5  # wrapped line of the same paragraph (any indent)
            if prev["text"].endswith(SENTENCE_END):
                join = False
            elif prev["text"].endswith(PAREN_END):
                join = tight and force_ok  # ")": join only across tight gaps
            else:
                join = force_ok and (
                    tight or (abs(line["x0"] - prev["x0"]) < 10 and gap < 17)
                )
        if join:
            sep = "" if self.out[-1].endswith("-") else " "
            self.out[-1] += sep + esc(text)
        else:
            self._blank()
            m = re.match(r"^NOTE\s+(.*)$", text)
            if m:
                self.out.append("> **NOTE** " + esc(m.group(1)))
            else:
                self.out.append(esc(text))
        self.para_open = True
        self.prev_body = line

    def finish(self):
        self._close_code()
        while self.out and self.out[-1] == "":
            self.out.pop()
        return "\n".join(self.out) + "\n"


def main():
    pdf = pdfplumber.open(str(PDF_PATH))
    raw = []
    for pi in range(4, len(pdf.pages)):  # skip cover / legal / contents
        raw.extend(extract_lines(pdf.pages[pi]))
    raw = [ln for ln in raw if not TOC_DOTS.search(ln["text"])]

    # merge consecutive h1 lines (chapter titles wrap over two lines)
    items = []
    for ln in raw:
        cls = classify(ln)
        if items and cls == items[-1][0] and cls == "h1":
            items[-1][1]["text"] += " " + ln["text"]
            continue
        items.append((cls, ln))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = {}   # fname -> (title, Builder)
    order = []
    cur = None
    chapter = 0
    pending_note = False

    def start_file(name, title):
        nonlocal cur
        cur = Builder()
        files[name] = (title, cur)
        order.append(name)
        cur.add_heading(1, title)

    for cls, ln in items:
        text = ln["text"]
        if cls == "h1":
            m = CHAPTER_NUM.match(text)
            chapter = int(m.group(1)) if m else chapter
            if chapter != 3:  # chapter 3 files start at each subsystem intro
                start_file(CHAPTER_FILES.get(chapter, f"0{chapter}_chapter"), text)
            continue
        if chapter == 6 and cls == "h2" and text.strip().lower() == "index":
            break  # trailing index section references PDF page numbers; useless in md
        if cur is None:
            continue
        if cls == "h4" and text.strip() == "NOTE":
            pending_note = True  # floating NOTE label inside a note box
            continue
        if cls == "h4" and text.strip().startswith("NOTE "):
            cur.add_body(ln, force_note=True)  # NOTE label with inline content
            continue
        if chapter == 3 and cls == "h2":
            mi = INTRO_HDR.match(text)
            if mi:
                slug = re.sub(r"[^a-z0-9]+", "_", mi.group(1).lower()).strip("_")
                start_file(f"03_{slug}", text)
            else:
                cur.add_heading(2, text)
            continue
        if cls == "h2":
            cur.add_heading(2, text)
        elif cls == "h3":
            cur.add_heading(2 if chapter == 3 else 3, text)
        elif cls == "h4":
            cur.add_heading(3 if chapter == 3 else 4, text)
        elif cls == "code" or (
            cls == "body"
            and cur.in_syntax
            and looks_like_cmd(text)
        ):
            cur.add_code(text)
            pending_note = False
        else:
            cur.add_body(ln, force_note=pending_note)
            pending_note = False

    for name in order:
        title, b = files[name]
        (OUT_DIR / f"{name}.md").write_text(b.finish(), encoding="utf-8")

    readme = ["# Keysight N6705C DC Power Analyzer - Programmer's Reference Guide", "",
              "Extracted from `N6705C_编程指南.pdf` (Keysight Technologies 2006-2015).", "",
              "## Contents", ""]
    for name in order:
        title, _ = files[name]
        readme.append(f"- [{title}]({name}.md)")
    (OUT_DIR / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")

    for name in order:
        p = OUT_DIR / f"{name}.md"
        print(f"{p.name}: {p.stat().st_size} bytes")


if __name__ == "__main__":
    main()

"""HTML report builder for Orchestrator runs."""

from __future__ import annotations

import html
import json
from typing import Any, Dict, Iterable, List


def build_html_report(
    *,
    manifest: Dict[str, Any],
    records: Iterable[Dict[str, Any]],
    logs: Iterable[str] | None = None,
    title: str = "Orchestrator Report",
) -> str:
    rows = list(records)
    log_lines = list(logs or [])
    fields: List[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

    header_cells = "".join(f"<th>{html.escape(name)}</th>" for name in fields)
    body_rows = []
    for row in rows:
        cells = "".join(html.escape(str(row.get(name, ""))) for name in fields)
        body_rows.append("<tr>" + "".join(
            f"<td>{html.escape(str(row.get(name, '')))}</td>" for name in fields
        ) + "</tr>")
    table = (
        "<table><thead><tr>" + header_cells + "</tr></thead><tbody>"
        + "\n".join(body_rows)
        + "</tbody></table>"
    ) if fields else "<p>No records.</p>"

    manifest_json = html.escape(json.dumps(manifest, ensure_ascii=False, indent=2, default=str))
    logs_html = "\n".join(html.escape(line) for line in log_lines[-500:])

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #172033; }}
    h1 {{ margin: 0 0 16px; font-size: 22px; }}
    h2 {{ margin-top: 24px; font-size: 16px; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 12px; }}
    th, td {{ border: 1px solid #d6deeb; padding: 6px 8px; text-align: left; }}
    th {{ background: #edf2fb; }}
    pre {{ background: #f7f9fc; border: 1px solid #d6deeb; padding: 12px; overflow: auto; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <h2>Manifest</h2>
  <pre>{manifest_json}</pre>
  <h2>Results</h2>
  {table}
  <h2>Logs</h2>
  <pre>{logs_html}</pre>
</body>
</html>
"""

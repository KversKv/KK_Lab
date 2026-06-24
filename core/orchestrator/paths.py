"""Path helpers for Orchestrator user data."""

from __future__ import annotations

import json
import os
from typing import Any, Iterable, List


def project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_primary_template_dir() -> str:
    return os.path.join(project_root(), "userdata", "orchestrator_templates")


def get_legacy_template_dir() -> str:
    return os.path.join(project_root(), "ui", "pages", "orchestrator", "templates")


def get_template_dirs() -> List[str]:
    dirs = [get_primary_template_dir(), get_legacy_template_dir()]
    seen: set[str] = set()
    result: List[str] = []
    for path in dirs:
        normalized = os.path.normcase(os.path.abspath(path))
        if normalized in seen or not os.path.isdir(path):
            continue
        seen.add(normalized)
        result.append(path)
    return result


def iter_template_files() -> Iterable[str]:
    for folder in get_template_dirs():
        for name in sorted(os.listdir(folder)):
            if name.lower().endswith(".json"):
                yield os.path.join(folder, name)


def resolve_template_path(name_or_path: str) -> str:
    if os.path.isabs(name_or_path) and os.path.isfile(name_or_path):
        return name_or_path
    if os.path.isfile(name_or_path):
        return os.path.abspath(name_or_path)

    name = os.path.basename(name_or_path)
    for folder in get_template_dirs():
        candidate = os.path.join(folder, name)
        if os.path.isfile(candidate):
            return candidate
    return os.path.join(get_primary_template_dir(), name)


def get_recent_sequences_path() -> str:
    return os.path.join(project_root(), "userdata", "orchestrator_recent.json")


def load_recent_sequences(limit: int = 10) -> List[str]:
    path = get_recent_sequences_path()
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data: Any = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        text = str(item)
        if text and os.path.isfile(text):
            result.append(text)
        if len(result) >= limit:
            break
    return result


def record_recent_sequence(path: str, limit: int = 10) -> None:
    if not path:
        return
    abs_path = os.path.abspath(path)
    existing = load_recent_sequences(limit=limit * 2)
    normalized = os.path.normcase(abs_path)
    entries = [abs_path]
    entries.extend(
        item for item in existing
        if os.path.normcase(os.path.abspath(item)) != normalized
    )
    entries = entries[:limit]
    target = get_recent_sequences_path()
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

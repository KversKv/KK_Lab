"""One-shot script: scan chips/bes_chip_configs/main_chips/*.py, read
CHIP_CONFIG['power_distribution'], and emit one YAML per chip into
chips/bes_chip_configs/main_chip_configs/<chip>.yaml.

Behavior:
- Non-empty power_distribution: migrate its key/value pairs as top-level YAML
  keys. Each entry's value may be either:
    * a plain list of commands -> emitted as a YAML list
    * a list whose first element is a bare label like 'Voltage_low:' -> the
      label is stripped and the rest are emitted as the command list
- Empty power_distribution ({}): emit a sample template with two commented
  config blocks showing the expected format.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed in current interpreter:", sys.executable)
    sys.exit(1)


ROOT = Path(__file__).resolve().parent.parent
MAIN_CHIPS_DIR = ROOT / "chips" / "bes_chip_configs" / "main_chips"
OUT_DIR = ROOT / "chips" / "bes_chip_configs" / "main_chip_configs"


def load_chip_config(py_file: Path):
    spec = importlib.util.spec_from_file_location(py_file.stem, str(py_file))
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        print(f"[WARN] Failed to load {py_file.name}: {e}")
        return None
    return getattr(mod, "CHIP_CONFIG", None)


def normalize_power_distribution(pd: dict) -> dict:
    """Clean up the entries so the YAML output is tidy."""
    cleaned: dict = {}
    for name, items in pd.items():
        if not isinstance(items, list):
            # Scalar or dict -> preserve as-is under the key.
            cleaned[name] = items
            continue

        new_items: list = []
        for it in items:
            if not isinstance(it, str):
                new_items.append(it)
                continue
            stripped = it.strip()
            # Skip a bare YAML-style label such as "Voltage_low:" or "foo:"
            if stripped.endswith(":") and " " not in stripped:
                continue
            # Strip a leading "- " that came from a serialized YAML dump.
            if stripped.startswith("- "):
                stripped = stripped[2:].lstrip()
            new_items.append(stripped)
        cleaned[name] = new_items
    return cleaned


SAMPLE_TEMPLATE = """\
# 示例配置,供参考。请按实际芯片寄存器需要修改或新增顶层 key。
# 下拉菜单中的 Config 条目就是本文件顶层 key。
# 支持的指令:
#   READ <addr>
#   WRITE <addr> <value>
#   WRITE_BITS <addr> <high_bit> <low_bit> <value>
#   DELAY <ms>
#   // 以 // 开头的行为注释(随 WRITE_BITS 一起存放)

voltage_low:
  - // 示例:降低所有电压轨
  - WRITE_BITS 0x0130 10 10 0x1
  - WRITE_BITS 0x0140 10 10 0x1
  - WRITE_BITS 0x0150 10 10 0x1

voltage_default:
  - // 示例:恢复默认电压
  - WRITE_BITS 0x0130 10 10 0x0
  - WRITE_BITS 0x0140 10 10 0x0
  - WRITE_BITS 0x0150 10 10 0x0
"""


def dump_yaml(data: dict) -> str:
    """Dump with key order preserved and lists as block style."""
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=200,
    )


def main() -> int:
    if not MAIN_CHIPS_DIR.is_dir():
        print(f"[ERROR] source dir not found: {MAIN_CHIPS_DIR}")
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    migrated = 0
    templated = 0
    skipped = 0

    for py_file in sorted(MAIN_CHIPS_DIR.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        chip_name = py_file.stem
        out_path = OUT_DIR / f"{chip_name}.yaml"
        if out_path.exists():
            print(f"[SKIP ] {chip_name}.yaml already exists")
            skipped += 1
            continue

        cfg = load_chip_config(py_file)
        pd = (cfg or {}).get("power_distribution") or {}

        if isinstance(pd, dict) and pd:
            cleaned = normalize_power_distribution(pd)
            header = (
                f"# {chip_name} power_distribution 配置\n"
                f"# 由 scripts/_gen_chip_yaml.py 从 {py_file.name} 自动迁移生成。\n"
                f"# 顶层 key 即下拉菜单中的 Config 条目。\n\n"
            )
            out_path.write_text(header + dump_yaml(cleaned), encoding="utf-8")
            print(f"[MIGR ] {chip_name}.yaml  ({len(cleaned)} configs)")
            migrated += 1
        else:
            header = (
                f"# {chip_name} power_distribution 配置(模板)\n"
                f"# 源 {py_file.name} 中的 power_distribution 为空,下列内容为示例模板。\n"
                f"# 请按实际寄存器配置修改或删除后再使用。\n\n"
            )
            out_path.write_text(header + SAMPLE_TEMPLATE, encoding="utf-8")
            print(f"[SAMPL] {chip_name}.yaml  (sample template)")
            templated += 1

    print(
        f"\nDone. migrated={migrated}, samples={templated}, skipped_existing={skipped}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

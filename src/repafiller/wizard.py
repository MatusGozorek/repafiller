"""
Template wizard  –  repa-filler --wizard <name>
Creates templates/<name>.json by prompting day-by-day.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# ── input helpers ────────────────────────────────────────────────────────────

def _ask(prompt: str) -> str:
    """Prompt and return stripped input; Ctrl-C exits gracefully."""
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        print("\nWizard cancelled.")
        sys.exit(0)


def _ask_int(prompt: str, *, min_val: int = 0) -> int:
    while True:
        raw = _ask(prompt)
        if raw.isdigit() and int(raw) >= min_val:
            return int(raw)
        print(f"  Please enter a whole number >= {min_val}.")


def _parse_class_input(raw: str) -> tuple[str, str] | None:
    """
    Accept any of:
        ENG 3   |   ENG,3   |   ENG;3   |   ENG, 3
    Returns (class_name_upper, time_str) or None if unparseable.
    """
    parts = re.split(r"[;\s]+", raw.strip(), maxsplit=1)
    if len(parts) != 2:
        return None
    name, time_raw = parts[0].strip().upper(), parts[1].strip()
    if not name or not re.match(r"^\d+([.,]\d+)?$", time_raw):
        return None
    return name, time_raw.replace(",", ".")

# ── wizard core ──────────────────────────────────────────────────────────────

def run_wizard(template_name: str, templates_dir: Path) -> None:
    templates_dir.mkdir(parents=True, exist_ok=True)
    out_path = templates_dir / f"{template_name}.json"

    if out_path.exists():
        ans = _ask(f"  '{out_path.name}' already exists. Overwrite? [y/N] ")
        if ans.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    print(f"\n=== Template wizard: {template_name} ===")
    print("For each class enter:  CLASS_NAME LENGTH   (e.g. 'ENG 3' or 'PaS,2')")
    print("Enter 0 classes to mark a day as free.\n")

    template: list[dict] = []

    for day in DAYS:
        print(f"── {day} ──")
        count = _ask_int(f"  How many classes? ", min_val=0)

        for i in range(1, count + 1):
            while True:
                raw = _ask(f"  Class {i} (name length): ")
                parsed = _parse_class_input(raw)
                if parsed:
                    class_name, time_str = parsed
                    template.append({
                        "day": day,
                        "class": class_name,
                        "time": time_str,
                        "description": ""   # filled later from inventory
                    })
                    break
                print("  Bad format – try e.g. 'ENG 3' or 'PaS,2'")
        print()

    # ── preview ──────────────────────────────────────────────────────────────
    print("── Preview ──")
    if not template:
        print("  (no classes added)")
    else:
        current_day = None
        for entry in template:
            if entry["day"] != current_day:
                current_day = entry["day"]
                print(f"  {current_day}:")
            print(f"    {entry['class']:8s}  {entry['time']} hr(s)")

    print()
    ans = _ask("Save template? [Y/n] ")
    if ans.lower() == "n":
        print("Discarded.")
        sys.exit(0)

    out_path.write_text(json.dumps(template, indent=2))
    print(f"  ✓ Saved to {out_path}")
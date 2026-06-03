"""
builder.py  –  repafiller
Takes a template (list of day/class/time entries) + inventory + a per-subject
counter, fills in descriptions using Option A (simple counter per subject),
and returns a finished JSON payload ready to POST.
"""
from __future__ import annotations

import json
import random
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path


# ── description resolver ─────────────────────────────────────────────────────

def _next_description(
    subject: str,
    inventory: dict[str, list[str]],
    counters: dict[str, int],
) -> str:
    """
    Return the next unused description for `subject`.
    Mutates `counters` in place.

    - If the subject is not in inventory at all  → warning, returns ""
    - If the subject has run out of descriptions  → warning, returns a random
      one from the same pool (wraps around)
    """
    pool = inventory.get(subject)

    if not pool:
        warnings.warn(
            f"Subject '{subject}' not found in inventory.txt – description left blank.",
            stacklevel=2,
        )
        return ""

    idx = counters.get(subject, 0)

    if idx >= len(pool):
        warnings.warn(
            f"Subject '{subject}' ran out of descriptions "
            f"(used all {len(pool)}). Reusing a random one.",
            stacklevel=2,
        )
        chosen = random.choice(pool)
        # do NOT advance the counter – keeps warning on every future call
        return chosen

    counters[subject] = idx + 1
    return pool[idx]


# ── date formatter ───────────────────────────────────────────────────────────

def _format_date(d) -> str:
    """
    Convert a date/datetime to the site's expected UTC string.
    The site stores days as UTC 22:00 of the *previous* calendar day
    (i.e. local midnight CET = UTC-2 offset used in your original script).
    """
    from datetime import date as date_type
    if isinstance(d, date_type) and not isinstance(d, datetime):
        d = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    dt = d.astimezone(timezone.utc) - timedelta(hours=2)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


# ── single-day payload builder ───────────────────────────────────────────────

def build_payload(
    date,                          # datetime.date for the target day
    template: list[dict],          # entries from e.g. week_a.json
    inventory: dict[str, list[str]],
    counters: dict[str, int],      # shared across the whole month run
    place: int = 2,
    status: int = 1,
    day_name: str | None = None,   # e.g. "Monday" – filters template entries
) -> dict:
    """
    Build one attendance payload for `date`.

    `day_name` should be the weekday name ("Monday" … "Friday").
    Only template entries matching that day are included.
    If day_name is None, ALL template entries are used (useful for testing).
    """
    if day_name is None:
        entries = template
    else:
        entries = [e for e in template if e.get("day") == day_name]

    content = []
    for entry in entries:
        subject = entry["class"]
        desc = _next_description(subject, inventory, counters)
        content.append({
            "description": desc,
            "time": str(entry["time"]),   # keep as string to match site format
            "class": subject,
        })

    return {
        "place":   place,
        "date":    _format_date(date),
        "content": content,
        "status":  status,
    }


# ── template loader ──────────────────────────────────────────────────────────

def load_template(path: Path) -> list[dict]:
    """Load a template JSON file and return its list of entries."""
    with path.open() as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Template {path.name} must be a JSON array.")
    return data


# ── quick smoke-test (python builder.py) ────────────────────────────────────

if __name__ == "__main__":
    from datetime import date
    from repafiller.parser import load_inventory

    # fake template – replace with load_template(Path("templates/week_a.json"))
    fake_template = [
        {"day": "Monday",    "class": "E", "time": "1", "description": ""},
        {"day": "Wednesday", "class": "E", "time": "2", "description": ""},
        {"day": "Friday",    "class": "E", "time": "1", "description": ""},
    ]

    inv      = load_inventory()
    counters: dict[str, int] = {}

    # simulate 3 days
    test_days = [
        (date(2026, 6, 2),  "Monday"),
        (date(2026, 6, 4),  "Wednesday"),
        (date(2026, 6, 6),  "Friday"),
    ]

    for d, day_name in test_days:
        payload = build_payload(d, fake_template, inv, counters, day_name=day_name)
        print(json.dumps(payload, indent=2))
        print()
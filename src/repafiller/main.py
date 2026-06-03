"""
repafiller  –  main entry point

Usage examples:
  repafiller --wizard week_a
  repafiller -m june -f week_a,week_b,week_c
  repafiller -m june -f week_a,week_b,week_c -l 25,26
  repafiller -m june -f week_a,week_b,week_c --dry-run
  repafiller -m june --submit
  repafiller -m june --submit -l 25,26
  repafiller -m june --submit --dry-run
"""
from __future__ import annotations

import argparse
import calendar
import json
import sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

# ── paths ─────────────────────────────────────────────────────────────────────

BASE_DIR      = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = BASE_DIR / "templates"

# ── month helpers ─────────────────────────────────────────────────────────────

MONTH_NAMES = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}

def _parse_month(raw: str) -> tuple[int, int]:
    raw = raw.strip().lower()
    if raw.isdigit():
        m = int(raw)
    else:
        m = MONTH_NAMES.get(raw)
    if not m or not (1 <= m <= 12):
        print(f"Error: '{raw}' is not a valid month.", file=sys.stderr)
        sys.exit(1)
    return date.today().year, m

def _weekdays_in_month(year: int, month: int) -> list[date]:
    _, days_in_month = calendar.monthrange(year, month)
    return [
        date(year, month, d)
        for d in range(1, days_in_month + 1)
        if date(year, month, d).weekday() < 5
    ]

def _parse_leave(raw: str, year: int, month: int) -> set[int]:
    _, days_in_month = calendar.monthrange(year, month)
    leave = set()
    for part in raw.split(","):
        part = part.strip()
        if not part.isdigit():
            print(f"Error: leave day '{part}' is not a number.", file=sys.stderr)
            sys.exit(1)
        d = int(part)
        if not (1 <= d <= days_in_month):
            print(
                f"Error: day {d} is out of range for "
                f"{calendar.month_name[month]} {year} (1–{days_in_month}).",
                file=sys.stderr,
            )
            sys.exit(1)
        leave.add(d)
    return leave

def _date_matches(entry_date_str: str, d: date) -> bool:
    """
    Compare an ISO date string from the API against a local date.
    The API stores dates as UTC 22:00 of the previous day, so we
    add 2 hours back to recover the intended local date.
    """
    try:
        dt = datetime.fromisoformat(entry_date_str.replace("Z", "+00:00"))
        local = (dt + timedelta(hours=2)).date()
        return local == d
    except Exception:
        return False

# ── save mode ─────────────────────────────────────────────────────────────────

def run_save(args: argparse.Namespace) -> None:
    from repafiller.builder import build_payload, load_template
    from repafiller.parser  import load_inventory
    from repafiller.config  import Config
    from repafiller.sender  import send_payload
    from itertools import groupby

    cfg = Config()

    # validate templates
    template_names = [t.strip() for t in args.files.split(",")]
    templates: list[list[dict]] = []
    for name in template_names:
        path = TEMPLATES_DIR / f"{name}.json"
        if not path.exists():
            print(f"Error: template '{path}' not found.", file=sys.stderr)
            sys.exit(1)
        templates.append(load_template(path))

    year, month   = _parse_month(args.month)
    leave_days    = _parse_leave(args.leave, year, month) if args.leave else set()
    weekdays      = _weekdays_in_month(year, month)

    # group into calendar weeks and round-robin templates
    weeks_grouped: list[list[date]] = [
        list(days)
        for _, days in groupby(weekdays, key=lambda d: d.isocalendar()[1])
    ]

    inventory = load_inventory()
    counters: dict[str, int] = {}

    mode = "DRY RUN" if args.dry_run else "SAVE"
    print(f"\n{'─'*50}")
    print(f"  repafiller  [{mode}]")
    print(f"  Month    : {calendar.month_name[month]} {year}")
    print(f"  Templates: {' → '.join(template_names)} (repeating)")
    print(f"  Leave    : {sorted(leave_days) or 'none'}")
    print(f"{'─'*50}\n")

    total = ok = skipped = 0

    for week_idx, week_days in enumerate(weeks_grouped):
        template = templates[week_idx % len(templates)]
        t_name   = template_names[week_idx % len(template_names)]
        print(f"  Week {week_idx + 1}  [{t_name}]")

        for d in week_days:
            day_name = d.strftime("%A")

            if d.day in leave_days:
                print(f"    {d}  {day_name:<10}  LEAVE – skipped")
                skipped += 1
                continue

            total += 1
            payload = build_payload(
                d, template, inventory, counters,
                place=cfg.place, status=cfg.status, day_name=day_name,
            )

            preview = json.dumps(payload)[:90]
            print(f"    {d}  {day_name:<10}  {preview}...")

            if not args.dry_run:
                ok += send_payload(payload, cfg)
            else:
                ok += 1
        print()

    print(f"{'─'*50}")
    print(f"  Done: {ok}/{total} saved,  {skipped} leave days skipped.")
    print(f"{'─'*50}\n")

# ── submit mode ───────────────────────────────────────────────────────────────

def run_submit(args: argparse.Namespace) -> None:
    from repafiller.config import Config
    from repafiller.sender import send_payload, fetch_attendance

    cfg = Config()

    year, month = _parse_month(args.month)
    leave_days  = _parse_leave(args.leave, year, month) if args.leave else set()
    weekdays    = _weekdays_in_month(year, month)

    mode = "DRY RUN" if args.dry_run else "SUBMIT"
    print(f"\n{'─'*50}")
    print(f"  repafiller  [{mode}]")
    print(f"  Month    : {calendar.month_name[month]} {year}")
    print(f"  Leave    : {sorted(leave_days) or 'none'}")
    print(f"{'─'*50}\n")

    # fetch existing entries from the server
    if not args.dry_run:
        print("  Fetching existing attendance from server...")
        existing = fetch_attendance(cfg)
        if not existing:
            print("  No entries found or fetch failed. Nothing to submit.")
            return
    else:
        existing = []

    total = ok = skipped = missing = 0

    for d in weekdays:
        day_name = d.strftime("%A")

        if d.day in leave_days:
            print(f"    {d}  {day_name:<10}  LEAVE – skipped")
            skipped += 1
            continue

        # find matching entry from server
        entry = next(
            (e for e in existing if _date_matches(e.get("date", ""), d)),
            None,
        )

        if args.dry_run:
            print(f"    {d}  {day_name:<10}  would submit (skipping fetch in dry-run)")
            ok += 1
            total += 1
            continue

        if not entry:
            print(f"    {d}  {day_name:<10}  ✗ not found on server – skipping")
            missing += 1
            total += 1
            continue

        total += 1

        # re-POST same entry with status 2
        payload = {
            "place":   entry["place"],
            "date":    entry["date"],
            "content": entry["content"],
            "status":  2,
        }

        preview = json.dumps(payload)[:90]
        print(f"    {d}  {day_name:<10}  {preview}...")
        ok += send_payload(payload, cfg)

    print(f"\n{'─'*50}")
    if missing:
        print(f"  Warning: {missing} day(s) had no saved entry on the server.")
    print(f"  Done: {ok}/{total} submitted,  {skipped} leave days skipped.")
    print(f"{'─'*50}\n")

# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="repafiller",
        description="Attendance filler for milankoys.sk",
    )

    parser.add_argument(
        "--wizard", metavar="TEMPLATE_NAME",
        help="Launch interactive template builder  (e.g. --wizard week_a)",
    )
    parser.add_argument("-m", "--month",  metavar="MONTH",
        help="Target month, e.g. june or 6")
    parser.add_argument("-f", "--files",  metavar="TEMPLATES",
        help="Comma-separated template names in week order  (e.g. week_a,week_b)")
    parser.add_argument("-l", "--leave",  metavar="DAYS",
        help="Comma-separated day numbers to skip  (e.g. 25,26)")
    parser.add_argument("--submit", action="store_true",
        help="Submit saved entries for the month (fetches from server, no -f needed)")
    parser.add_argument("--dry-run", action="store_true",
        help="Preview without sending anything")

    args = parser.parse_args()

    # wizard
    if args.wizard:
        from repafiller.wizard import run_wizard
        run_wizard(args.wizard, TEMPLATES_DIR)
        return

    # submit mode — no -f required
    if args.submit:
        if not args.month:
            print("Error: --submit requires -m/--month.", file=sys.stderr)
            sys.exit(1)
        run_submit(args)
        return

    # save mode
    if not args.month or not args.files:
        parser.print_help()
        sys.exit(0)

    run_save(args)


if __name__ == "__main__":
    main()
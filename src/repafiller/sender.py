"""
sender.py  –  repafiller
POSTs a single payload and fetches existing attendance from the API.
"""
from __future__ import annotations

import urllib3
import requests
from repafiller.config import Config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _headers(cfg: Config) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": cfg.token,
    }


def send_payload(payload: dict, cfg: Config) -> bool:
    """POST one payload. Returns True on success, False on failure."""
    try:
        r = requests.post(
            cfg.api_url, json=payload, headers=_headers(cfg),
            verify=False, timeout=10,
        )
        if r.ok:
            print(f"       ✓ {r.status_code}")
            return True
        else:
            print(f"       ✗ {r.status_code}: {r.text[:120]}")
            return False
    except Exception as e:
        print(f"       ✗ Error: {e}")
        return False


def fetch_attendance(cfg: Config) -> list[dict]:
    """
    GET /attendance and return the list of existing entries.
    Each entry looks like:
      {"place": 2, "date": "2026-06-01T...", "content": [...], "status": 1}
    Returns empty list on failure.
    """
    try:
        r = requests.get(
            cfg.api_url, headers=_headers(cfg),
            verify=False, timeout=10,
        )
        if r.ok:
            return r.json()
        else:
            print(f"  ✗ Failed to fetch attendance: {r.status_code}: {r.text[:120]}")
            return []
    except Exception as e:
        print(f"  ✗ Error fetching attendance: {e}")
        return []
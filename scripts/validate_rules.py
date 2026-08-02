#!/usr/bin/env python3
"""Validate DepositDay web/data state rule JSON for schema + coverage.

Reproducible checks (no network):
  python scripts/validate_rules.py

Exit 0 on success; non-zero on any failure.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data"
STATES = DATA / "states"
LIVE = ("CA", "TX", "FL", "NY", "PA")
REQUIRED_RULE_KEYS = {
    "state_code",
    "state_name",
    "program",
    "version",
    "effective_from",
    "updated_at",
    "status",
    "summary",
    "notes",
    "citations",
    "input_hint",
    "input",
}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def cover_ranges(ranges: list[dict]) -> None:
    covered = set()
    for r in ranges:
        if r["from"] > r["to"]:
            fail(f"range from>to: {r}")
        for n in range(r["from"], r["to"] + 1):
            if n in covered:
                fail(f"overlapping range at {n}: {r}")
            covered.add(n)
            if not 1 <= r["day_of_month"] <= 31:
                fail(f"bad day_of_month in {r}")
    missing = [i for i in range(100) if i not in covered]
    if missing:
        fail(f"ranges miss codes: {missing[:10]}...")


def validate_rule(rule: dict, state_code: str) -> None:
    missing = REQUIRED_RULE_KEYS - set(rule)
    if missing:
        fail(f"{state_code}: rule missing keys {missing}")
    if rule["state_code"] != state_code:
        fail(f"{state_code}: state_code mismatch")
    if not rule["citations"]:
        fail(f"{state_code}: citations empty")
    for c in rule["citations"]:
        for k in ("title", "url", "publisher", "retrieved_at"):
            if k not in c or not c[k]:
                fail(f"{state_code}: citation missing {k}")
        if not str(c["url"]).startswith("http"):
            fail(f"{state_code}: citation url not http(s)")

    kind = rule["input"]["kind"]
    if kind in ("case_last_digit", "edg_last_digit", "business_day_last_digit"):
        mapping = rule.get("mapping") or {}
        digits = set(mapping.keys())
        if digits != {str(i) for i in range(10)}:
            fail(f"{state_code}: mapping must cover digits 0-9, got {sorted(digits)}")
    elif kind in (
        "edg_last_two_digits_ranges",
        "fl_digits_98_ranges",
        "case_last_two_digits_ranges",
    ):
        cover_ranges(rule["ranges"])
    else:
        fail(f"{state_code}: unknown kind {kind}")


def main() -> None:
    index = load(DATA / "index.json")
    if tuple(index.get("live_states", [])) != LIVE:
        fail(f"index.live_states expected {LIVE}, got {index.get('live_states')}")

    for code in LIVE:
        path = STATES / f"{code.lower()}.json"
        if not path.exists():
            fail(f"missing {path}")
        bundle = load(path)
        if bundle["state_code"] != code:
            fail(f"{path}: state_code")
        if bundle["status"] != "live":
            fail(f"{path}: status not live")
        default = bundle["default_rule_id"]
        if default not in bundle["rules"]:
            fail(f"{path}: default_rule_id missing")
        for rid, rule in bundle["rules"].items():
            validate_rule(rule, code)
            print(f"OK  {code}/{rid}")

    federal = load(DATA / "federal" / "calendar.json")
    if not federal.get("programs") or not federal.get("federal_holidays"):
        fail("federal calendar incomplete")
    print(f"OK  federal v{federal['version']} programs={len(federal['programs'])}")

    de = load(DATA / "direct-express.json")
    if not de.get("official_links"):
        fail("direct-express missing official_links")
    print(f"OK  direct-express v{de['version']}")

    # Spot checks matching vitest fixtures
    ca = load(STATES / "ca.json")
    assert ca["rules"]["calfresh_case_last_digit"]["mapping"]["6"] == 6
    assert ca["rules"]["calfresh_case_last_digit"]["mapping"]["0"] == 10
    tx = load(STATES / "tx.json")
    post = tx["rules"]["snap_edg_post_2020"]["ranges"]
    hit = next(r for r in post if r["from"] <= 42 <= r["to"])
    assert hit["day_of_month"] == 28
    print("OK  spot checks CA/TX")
    print("ALL PASSED")


if __name__ == "__main__":
    main()

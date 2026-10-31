#!/usr/bin/env python3
"""Metric canary: re-run the pinned MetricFlow query and compare it to approved.csv.

approved.csv holds the answer for settled periods that was reconciled against an
independent query on the source tables before it was pinned. This script re-runs
the same `mf query` (described in canary.json), rounds it the same way, and
compares the two row by row.

Run from anywhere, with the project's environment active:

    python canary/check_metrics.py          # compare
    python canary/check_metrics.py --pin    # write approved.csv once, after reconciling

Exit codes:
    0  every row matches approved.csv
    1  at least one row differs, is missing, or is new (each one is printed)
    2  the check could not run (mf or dbt failed, approved.csv missing or malformed)

--pin refuses to overwrite an existing approved.csv. To re-pin, reconcile the new
numbers against independent SQL on the source tables first, delete approved.csv
yourself, then pin again, so a moved number cannot be approved by accident.
"""

from __future__ import annotations

import argparse
import csv
import json
from decimal import InvalidOperation
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

CANARY_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CANARY_DIR.parent
APPROVED_CSV = CANARY_DIR / "approved.csv"
CONFIG_JSON = CANARY_DIR / "canary.json"


class CanaryError(Exception):
    """The check could not run, so it neither passed nor failed."""


def load_config() -> dict:
    if not CONFIG_JSON.exists():
        raise CanaryError(f"{CONFIG_JSON} not found.")
    try:
        cfg = json.loads(CONFIG_JSON.read_text())
    except json.JSONDecodeError as err:
        raise CanaryError(f"{CONFIG_JSON.name} is not valid JSON: {err}") from err
    missing = {"metrics", "group_by", "start_time", "end_time"} - set(cfg)
    if missing:
        raise CanaryError(f"{CONFIG_JSON.name} is missing {sorted(missing)}.")
    cfg.setdefault("decimals", 2)
    return cfg


try:
    CONFIG = load_config()
except CanaryError as err:
    print(f"CANARY ERROR: {err}", file=sys.stderr)
    sys.exit(2)

GROUP_BY = CONFIG["group_by"]
METRICS = list(CONFIG["metrics"])
COLUMNS = [GROUP_BY, *METRICS]
QUANTUM = Decimal(1).scaleb(-int(CONFIG["decimals"]))

MF_QUERY_ARGS = [
    "query",
    "--metrics", ",".join(METRICS),
    "--group-by", GROUP_BY,
    "--start-time", CONFIG["start_time"],
    "--end-time", CONFIG["end_time"],
    "--order", GROUP_BY,
    "--quiet",
]


def find_tool(name: str) -> str:
    """Prefer the executable next to this interpreter (the project .venv), then PATH."""
    candidate = Path(sys.executable).parent / name
    if candidate.exists():
        return str(candidate)
    found = shutil.which(name)
    if found is None:
        raise CanaryError(f"`{name}` not found. Activate the project's .venv first.")
    return found


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise CanaryError(
            f"`{' '.join(cmd)}` exited with {result.returncode}:\n{result.stdout}{result.stderr}"
        )


def run_mf_query() -> list[dict[str, str]]:
    # mf reads target/semantic_manifest.json and never re-parses the YAML, so parse
    # first. Otherwise an edited metric definition is checked against a stale manifest.
    run([find_tool("dbt"), "parse", "--quiet"])
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "mf_query.csv"
        run([find_tool("mf"), *MF_QUERY_ARGS, "--csv", str(out)])
        if not out.exists():
            # mf exits 0 and writes no CSV when the query returns no rows. Treat that
            # as an empty result so every pinned row is reported as missing.
            return []
        with out.open(newline="") as f:
            return list(csv.DictReader(f))


def to_period(value: str) -> str:
    # mf writes "2026-08-01 00:00:00"; keep the date so a timestamp format change
    # in a MetricFlow upgrade does not read as a moved number. Non-date group-by
    # values pass through unchanged.
    try:
        return datetime.fromisoformat(value.strip()).date().isoformat()
    except ValueError:
        return value.strip()


def round_value(value: str | None) -> str:
    # A null metric stays empty, so a later change between null and a number shows up.
    # Warehouse float sums can differ in the last bits between runs; rounding to
    # the configured decimals absorbs that.
    if value is None or value.strip() == "":
        return ""
    return str(Decimal(value.strip()).quantize(QUANTUM, rounding=ROUND_HALF_UP))


def normalize(rows: list[dict[str, str]], source: str) -> list[dict[str, str]]:
    """Order by the group-by value and round every metric, as strings."""
    if rows and set(COLUMNS) - set(rows[0]):
        raise CanaryError(f"{source} has columns {list(rows[0])}, expected {COLUMNS}.")
    try:
        out = [{GROUP_BY: to_period(r[GROUP_BY]), **{m: round_value(r[m]) for m in METRICS}} for r in rows]
    except (InvalidOperation, AttributeError, KeyError, TypeError) as err:
        raise CanaryError(f"{source} has a missing or non-numeric value: {err!r}") from err
    keys = [r[GROUP_BY] for r in out]
    if len(keys) != len(set(keys)):
        raise CanaryError(f"{source} has more than one row for the same {GROUP_BY}.")
    return sorted(out, key=lambda r: r[GROUP_BY])


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_approved() -> list[dict[str, str]]:
    if not APPROVED_CSV.exists():
        raise CanaryError(f"{APPROVED_CSV} not found. Nothing to compare against.")
    with APPROVED_CSV.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise CanaryError(
                f"{APPROVED_CSV.name} header is {reader.fieldnames}, expected {COLUMNS}. "
                "It does not match the query this script runs."
            )
        return normalize(list(reader), APPROVED_CSV.name)


def describe(row: dict[str, str] | None) -> str:
    if row is None:
        return "(no row)"
    return ", ".join(f"{m}={row[m] or 'null'}" for m in METRICS)


def compare(expected: list[dict[str, str]], actual: list[dict[str, str]]) -> int:
    """Print every row that differs and return how many did."""
    exp = {r[GROUP_BY]: r for r in expected}
    act = {r[GROUP_BY]: r for r in actual}
    mismatches = 0
    for key in sorted(exp.keys() | act.keys()):
        e, a = exp.get(key), act.get(key)
        if e == a:
            continue
        mismatches += 1
        if e is None or a is None:
            differs = "whole row (missing from the new run)" if a is None else "whole row (not in approved.csv)"
        else:
            differs = ", ".join(m for m in METRICS if e[m] != a[m])
        print(f"MISMATCH {GROUP_BY}={key}")
        print(f"  expected: {describe(e)}")
        print(f"  actual:   {describe(a)}")
        print(f"  differs:  {differs}")
    return mismatches


def pin() -> int:
    if APPROVED_CSV.exists():
        print(f"CANARY ERROR: {APPROVED_CSV.name} already exists; delete it yourself to re-pin.", file=sys.stderr)
        return 2
    try:
        rows = normalize(run_mf_query(), "mf query output")
    except CanaryError as err:
        print(f"CANARY ERROR: {err}", file=sys.stderr)
        return 2
    if not rows:
        print("CANARY ERROR: mf query returned no rows; nothing to pin.", file=sys.stderr)
        return 2
    write_csv(rows, APPROVED_CSV)
    print(f"Pinned {len(rows)} rows to {APPROVED_CSV.name}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare pinned MetricFlow results to approved.csv.")
    parser.add_argument("--pin", action="store_true", help="write approved.csv once, after reconciling")
    if parser.parse_args().pin:
        return pin()
    try:
        expected = read_approved()
        actual = normalize(run_mf_query(), "mf query output")
    except CanaryError as err:
        print(f"CANARY ERROR: {err}", file=sys.stderr)
        return 2

    mismatches = compare(expected, actual)
    total = len({r[GROUP_BY] for r in expected} | {r[GROUP_BY] for r in actual})
    if mismatches:
        print(f"Canary FAILED: {mismatches} of {total} rows differ from {APPROVED_CSV.name}.")
        return 1
    print(f"Canary passed: all {total} rows match {APPROVED_CSV.name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

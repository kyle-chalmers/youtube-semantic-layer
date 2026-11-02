#!/usr/bin/env python3
"""Weekly channel report: run the mf queries in report.json and append the results to BigQuery.

Every number comes from `mf query`, so the report uses the same metric definitions as the
canary and the agents. The report week is the latest 7 days that every metric in the report
has data for, compared with the 7 days before. Rows are marked provisional because YouTube
can still restate days for about five weeks.

    python report/weekly_report.py             # query and append to BigQuery
    python report/weekly_report.py --dry-run   # query and print the rows, load nothing

Output never prints metric values except in --dry-run, so a run log on a public repo shows
only counts. Exit codes: 0 loaded (or printed), 2 the report could not be built or loaded.

Environment: GCP_PROJECT_ID (default: the credentials' project) and REPORT_DATASET
(default: dbt_semantic_layer) choose where the table lives.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

REPORT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = REPORT_DIR.parent
CONFIG_JSON = REPORT_DIR / "report.json"
LOOKBACK_DAYS = 45

RunQuery = Callable[..., list[dict[str, str]]]


class ReportError(Exception):
    """The report could not be built or loaded."""


def find_tool(name: str) -> str:
    """Prefer the executable next to this interpreter (the project .venv), then PATH."""
    candidate = Path(sys.executable).parent / name
    if candidate.exists():
        return str(candidate)
    found = shutil.which(name)
    if found is None:
        raise ReportError(f"`{name}` not found. Activate the project's .venv first.")
    return found


def run_mf_query(metrics: list[str], group_by: list[str], start: date, end: date,
                 order: str | None = None, limit: int | None = None) -> list[dict[str, str]]:
    cmd = [find_tool("mf"), "query", "--metrics", ",".join(metrics),
           "--start-time", start.isoformat(), "--end-time", end.isoformat(), "--quiet"]
    if group_by:
        cmd += ["--group-by", ",".join(group_by)]
    if order:
        cmd += ["--order", order]
    if limit:
        cmd += ["--limit", str(limit)]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "mf_query.csv"
        result = subprocess.run([*cmd, "--csv", str(out)], cwd=PROJECT_ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            raise ReportError(f"mf query for {','.join(metrics)} exited with {result.returncode}:\n{result.stderr}")
        if not out.exists():  # mf exits 0 and writes no CSV when the query returns no rows
            return []
        with out.open(newline="") as f:
            return list(csv.DictReader(f))


def choose_window(latest_days: dict[str, date]) -> tuple[tuple[date, date], tuple[date, date]]:
    """The current week ends on the earliest of each metric's latest day; the prior week precedes it."""
    end = min(latest_days.values())
    start = end - timedelta(days=6)
    return (start, end), (start - timedelta(days=7), start - timedelta(days=1))


def _day(value: str) -> date:
    return date.fromisoformat(value[:10])


def find_window(config: dict, run_query: RunQuery, today: date) -> tuple[tuple[date, date], tuple[date, date]]:
    metrics = sorted({m for s in config["sections"] for m in s["metrics"]})
    daily = run_query(metrics, ["metric_time__day"], today - timedelta(days=LOOKBACK_DAYS), today)
    days_with_data = {m: {_day(r["metric_time__day"]) for r in daily if r.get(m) not in (None, "")} for m in metrics}

    missing = [m for m, days in days_with_data.items() if not days]
    if missing:
        raise ReportError(f"no data in the last {LOOKBACK_DAYS} days for {', '.join(missing)}")

    current, prior = choose_window({m: max(days) for m, days in days_with_data.items()})
    for label, (start, end) in (("current", current), ("prior", prior)):
        week = {start + timedelta(d) for d in range(7)}
        short = [f"{m} ({len(week & days)} of 7 days)" for m, days in days_with_data.items() if len(week & days) < 7]
        if short:
            raise ReportError(f"{label} week {start} to {end} is incomplete: {', '.join(short)}")
    return current, prior


def section_rows(section: dict, rows: list[dict[str, str]], period: str, week: tuple[date, date],
                 run_id: str, generated_at: str) -> list[dict]:
    group_by = section["group_by"]
    key = group_by[0] if group_by else None
    label = group_by[1] if len(group_by) > 1 else key
    out = []
    for row in rows:
        for metric in section["metrics"]:
            value = row.get(metric)
            out.append({
                "run_id": run_id,
                "generated_at": generated_at,
                "period": period,
                "week_start": week[0].isoformat(),
                "week_end": week[1].isoformat(),
                "section": section["name"],
                "metric": metric,
                "dimension_name": key,
                "dimension_value": row.get(key) if key else None,
                "dimension_label": row.get(label) if label else None,
                "value": float(value) if value not in (None, "") else None,
                "data_status": "provisional",
            })
    return out


def generate(config: dict, run_query: RunQuery, today: date, run_id: str, now: datetime) -> list[dict]:
    current, prior = find_window(config, run_query, today)
    rows = []
    for period, week in (("current", current), ("prior", prior)):
        for section in config["sections"]:
            result = run_query(section["metrics"], section["group_by"], week[0], week[1],
                               order=section.get("order"), limit=section.get("limit"))
            if not result:
                raise ReportError(f"section {section['name']} returned no rows for the {period} week")
            rows += section_rows(section, result, period, week, run_id, now.isoformat())
    return rows


SCHEMA = [
    ("run_id", "STRING"), ("generated_at", "TIMESTAMP"), ("period", "STRING"), ("week_start", "DATE"),
    ("week_end", "DATE"), ("section", "STRING"), ("metric", "STRING"), ("dimension_name", "STRING"),
    ("dimension_value", "STRING"), ("dimension_label", "STRING"), ("value", "FLOAT64"), ("data_status", "STRING"),
]


def load_to_bigquery(rows: list[dict], table: str) -> None:
    from google.cloud import bigquery  # installed with dbt-bigquery

    client = bigquery.Client(project=os.environ.get("GCP_PROJECT_ID") or None)
    dataset = os.environ.get("REPORT_DATASET", "dbt_semantic_layer")
    job = client.load_table_from_json(
        rows,
        f"{client.project}.{dataset}.{table}",
        job_config=bigquery.LoadJobConfig(
            schema=[bigquery.SchemaField(name, kind) for name, kind in SCHEMA],
            write_disposition="WRITE_APPEND",
            create_disposition="CREATE_IF_NEEDED",
        ),
    )
    job.result()


def main(argv: list[str] | None = None, run_query: RunQuery = run_mf_query,
         loader: Callable | None = None, config: dict | None = None, today: date | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the weekly channel report from mf query output.")
    parser.add_argument("--dry-run", action="store_true", help="print the rows instead of loading them")
    args = parser.parse_args(argv)

    try:
        config = config or json.loads(CONFIG_JSON.read_text())
        run_id = str(uuid.uuid4())
        rows = generate(config, run_query, today or date.today(), run_id, datetime.now(timezone.utc))
        if args.dry_run:
            for row in rows:
                print(json.dumps(row))
            return 0
        (loader or (lambda r: load_to_bigquery(r, config["table"])))(rows)
    except (OSError, json.JSONDecodeError, ReportError) as err:
        print(f"REPORT ERROR: {err}", file=sys.stderr)
        return 2
    except Exception as err:  # BigQuery client errors; their messages carry no metric values
        print(f"REPORT ERROR: load failed: {type(err).__name__}: {err}", file=sys.stderr)
        return 2

    weeks = sorted({(r["week_start"], r["week_end"]) for r in rows})
    print(f"Report {run_id}: loaded {len(rows)} rows for weeks {weeks} into {config['table']}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

---
name: metricflow-canary
description: >-
  Build a metric canary for a dbt project that uses MetricFlow: reconcile chosen metrics for settled
  periods against an independent query on the source tables, pin the agreed answer in
  canary/approved.csv, and add a check script that re-runs mf query and fails with the rows that
  moved. Works on any warehouse MetricFlow supports. Use when someone wants to test dbt metrics,
  catch a metric whose number changed, "set up a canary", "pin these numbers", or check a semantic
  layer after a model change.
---

# MetricFlow canary

`mf validate-configs` proves a metric parses, resolves and runs. It never checks a value. This
skill pins an answer someone has verified and fails loudly when that answer moves, using only
`mf query` and the warehouse's own SQL, so it works on Snowflake, BigQuery, Databricks, Redshift
or Postgres.

## Hard rules

1. **Never pin a number that was not reconciled.** Every value in `approved.csv` must match an
   independent query on the source tables (not on the dbt models the metric reads). If any value
   differs, stop, show both numbers, and pin nothing.
2. **Never pin a period that is still settling.** Ask how late data arrives, or measure it
   (`references/settled-periods.md`). Default when nobody knows: only months that closed at least
   14 days ago.
3. **Never change metric YAML, models, or an existing approved.csv.** A moved number is the owner's
   call. Re-pinning means reconciling again first.
4. Show every SQL query and `mf` command as a code block before running it.

## Workflow

1. **Inputs.** Confirm, in one message, the metrics to pin, the grain (default
   `metric_time__month`), the settled periods, the source tables for the independent query, and the
   warehouse CLI to run it with (`bq`, `snow`, `databricks`, `psql`). Read `models/semantic/` to get
   each metric's real definition.
2. **Reconcile.** Run `mf query --metrics <m1,m2> --group-by <grain> --start-time <start>
   --end-time <end> --order <grain> --csv <tmp>` and write one independent SQL query that computes
   the same numbers straight from the source tables. Compare at the canary's precision. Report a
   short table of both. Stop on any mismatch. How to write the independent query:
   `references/reconcile.md`.
3. **Pin.** Copy `scripts/check_metrics.py` into `canary/`, write `canary/canary.json` (format
   below), then run `python canary/check_metrics.py --pin` once to write `canary/approved.csv` from
   the reconciled query. `--pin` refuses to overwrite an existing approved.csv.
4. **Check.** Run `python canary/check_metrics.py`. It must exit 0. Show the output.
5. **Schedule (only if asked).** The check queries whatever tables the last `dbt build` left in
   the warehouse, so run it right after your normal build, in the same target (for example
   `dbt build && python canary/check_metrics.py`). It needs warehouse credentials wherever it
   runs. Exit code 1 means a number moved, 2 means the check could not run.

`canary/canary.json`:

```json
{
  "metrics": ["avg_view_duration_seconds", "total_seconds_watched", "total_views"],
  "group_by": "metric_time__month",
  "start_time": "2026-08-01",
  "end_time": "2026-09-30",
  "decimals": 2
}
```

## Limits to state when you finish

- A baseline that was wrong from the start stays wrong; the reconciliation is the guard.
- It does not cover periods newer than the pinned range.
- It does not notice a change in what a metric means if the numbers for the pinned range stay the
  same.

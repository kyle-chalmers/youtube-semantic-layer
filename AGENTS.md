# YouTube Semantic Layer

IMPORTANT: Everything in this repo is public-facing, so do not place any sensitive info here and make sure to distinguish between what should be internal-facing info (e.g. secrets, PII, recording guides/scripts), and public-facing info (instructions, how-to guides, actual code utilized). If there is information the assistant needs across sessions but should not be published, put it in the `.internal/` folder which is ignored by git per the `.gitignore`.

## Project overview
Governed metrics on YouTube Analytics data with dbt Core and MetricFlow on BigQuery, a canary that checks metric values stay correct over time, and a way for AI agents to answer data questions through those metrics.

Intended users: data professionals and analytics engineers.

## Answering data questions: metrics first
When asked anything about the channel's numbers (views, watch time, subscribers, impressions, CTR, traffic sources, devices, audience, top videos):

1. Use the `query-metrics` skill. Claude Code loads it from `.claude/skills/query-metrics/`; Codex loads the same files through the `.agents/skills/query-metrics` symlink. Any other agent: read `.claude/skills/query-metrics/SKILL.md`.
2. Find the metric in `docs/metrics.md` or with `mf list metrics`; find its dimensions with `mf list dimensions --metrics <metric>`.
3. Answer with `mf query`. Check the metric's **Data starts** date against the period asked about.
4. Use raw SQL only when no metric covers the question, and say so in the answer.

## Stack
- dbt Core 1.12 with the BigQuery adapter (`profiles.yml` in the project root, oauth via application-default credentials)
- MetricFlow 0.213 (`mf` CLI), legacy YAML spec with measures
- Python 3.12 in `.venv`

## Commands
- Activate: `source .venv/bin/activate`
- Build models: `dbt build`
- Validate metrics: `mf validate-configs`
- Query: `mf query --metrics <metric> --group-by metric_time__month --start-time YYYY-MM-DD --end-time YYYY-MM-DD`
- Regenerate the glossary after changing metric YAML: `dbt parse && python scripts/build_glossary.py`
- Tests: `python -m pytest tests/python`
- Ad hoc SQL: `bq query --use_legacy_sql=false '<sql>'`

## Data notes
- Reporting API tables are the canonical source from 2026-08-06 (`var reporting_complete_from`). For earlier periods use the `analytics_*` metrics (Analytics API, from 2025-10-16).
- `total_views` is real views. Average view duration divides watch time by engaged views, as YouTube does. Never reconstruct views from watch time and average view duration: that gives engaged views.
- `video_metadata` has one row per video per snapshot date; `stg_video_metadata` keeps the latest snapshot.
- Reporting reissues a day's report for up to about 36 days, and the weekly Analytics refresh rewrites days 6 to 35 days old, so a month is final about five weeks after it closes. `canary/sql/settled_months.sql` shows the Analytics window.

## Working principles
- Print SQL as a formatted code block before running it.
- When checking a metric, compare it against a query written directly on the source tables, not on the dbt models.
- Explain non-obvious modeling choices in one or two sentences.
- Do not change files unless asked.

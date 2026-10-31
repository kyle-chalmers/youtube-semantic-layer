# YouTube Semantic Layer

## Project overview
This project builds governed metrics on YouTube Analytics data with dbt Core and MetricFlow on BigQuery, and checks that metric values stay correct over time.

Intended users: data professionals and analytics engineers.

## Stack
- dbt Core 1.12 with the BigQuery adapter (`profiles.yml` in the project root, oauth via application-default credentials)
- MetricFlow 0.213 (`mf` CLI), legacy YAML spec with measures
- Python 3.12 in `.venv`

## Commands
- Activate: `source .venv/bin/activate`
- Build models: `dbt build`
- Validate metrics: `mf validate-configs`
- Query: `mf query --metrics <metric> --group-by metric_time__month --start-time YYYY-MM-DD --end-time YYYY-MM-DD`
- Ad hoc SQL: `bq query --use_legacy_sql=false '<sql>'`

## Data notes
- `video_metadata` has one row per video per snapshot date; always use `stg_video_metadata`, which keeps the latest snapshot.
- Views are reconstructed in staging as minutes watched * 60 / average view duration.
- Recent days are restated by weekly refreshes; treat a month as settled about two weeks after it closes.

## Working principles
- Print SQL as a formatted code block before running it.
- When checking a metric, compare it against a query written directly on the source tables, not on the dbt models.
- Explain non-obvious modeling choices in one or two sentences.
- Do not change files unless asked.

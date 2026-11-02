# YouTube Semantic Layer

A dbt Core + MetricFlow semantic layer on YouTube Analytics data in BigQuery, plus a metric canary: a pinned, independently reconciled answer that fails loudly when a metric's number moves.

Everything here is open source. [MetricFlow](https://github.com/dbt-labs/metricflow) has been Apache 2.0 since version 0.209.0, and dbt lists Snowflake, BigQuery, Databricks, Redshift and Postgres as [supported platforms](https://docs.getdbt.com/docs/build/about-metricflow), so the metric definitions move to another warehouse by swapping the dbt adapter (the staging SQL uses BigQuery syntax and needs a small rewrite).

Video walkthrough: [Kyle Chalmers Data Plus AI on YouTube](https://www.youtube.com/@kylechalmersdataai)

## Why a canary

`mf validate-configs` checks that the YAML parses, references resolve and the SQL runs against the warehouse. It never checks a value ([dbt docs](https://docs.getdbt.com/docs/build/validation)). dbt data tests can assert aggregates on models; the canary instead pins what MetricFlow itself returns for each metric. A metric can pass every tier and still answer the wrong question, and a later change to a model can move a number without failing anything. The canary compares the numbers themselves.

![What each check catches when the model changes](./images/semantic-layer-dbt-diagrams-01.png)

## Data

The source tables come from the [youtube-bigquery-pipeline](https://github.com/kyle-chalmers/youtube-bigquery-pipeline) project. Two YouTube APIs feed it, and each metric reads from exactly one source:

| Source | Tables modeled | Grain | Coverage | Used for |
|---|---|---|---|---|
| Reporting API | `reporting_channel_combined_a3` | video, Pacific day, subscribed status, country, traffic source, device, OS, playback location | 2026-08-06 on | views, engaged views, watch time, average view duration |
| Reporting API | `reporting_channel_basic_a3` | video, day, subscribed status, country (plus channel-level rows with no video) | 2026-08-06 on | likes, comments, shares, subscribers |
| Reporting API | `reporting_channel_reach_combined_a1` | video, day, traffic source, detail, device, OS | 2026-08-06 on | impressions, impressions CTR |
| Reporting API | `traffic_source_a3`, `demographics_a1`, `cards_a1`, `end_screens_a1`, `sharing_service_a1` | per report | 2026-08-06 on | traffic detail, demographic estimates, cards, end screens, shares by service |
| Analytics API | `daily_video_analytics`, `daily_traffic_sources` | video, day (and traffic source) | 2025-10-16 on | `analytics_*` history metrics |
| Data API | `daily_video_stats`, `video_metadata` | video, snapshot date | 2026-02-17 on | lifetime counters, the video dimension |

Every fact joins one `videos` dimension, so any metric can be grouped by `video__title` or `video__video_type`. `models/semantic/` holds 37 metrics; each one's description says what it means, which table it reads, when its data starts, and whether it adds up.

Things that trip people up:

- **Views versus engaged views.** YouTube computes average view duration over *engaged* views, so watch time divided by average view duration gives roughly engaged views, not views (less than half of all views on a Shorts-heavy channel). `total_views` reads views straight from the Reporting API, and `avg_view_duration_seconds` divides watch time by engaged views.
- **Impressions cover six surfaces only** (search, suggested, browse, channel page and two playlist surfaces). Never divide views by impressions; use `impressions_ctr`.
- **Channel-level rows.** About a third of subscribers gained are not tied to a video. They count in channel totals; filter `attribution = 'video'` to rank videos.
- **Demographics are estimates.** YouTube only gives each age and gender group's share of a video-day's logged-in views.
- **Recent days move.** Reporting reissues a day's report for up to about five weeks, and the pipeline rewrites Analytics days 6 to 35 days old every week.

Using your own data: point `models/staging/_sources.yml` at your own pipeline's tables, or keep only the models you have sources for.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate   # or: uv venv .venv
pip install -r requirements.txt
gcloud auth application-default login
cp profiles.yml.example profiles.yml                  # set your project; keep the dataset in the same location as your source
dbt build
mf validate-configs
```

Query a metric:

```bash
mf query --metrics total_views,impressions_ctr --group-by metric_time__month,video__video_type --start-time 2026-09-01 --end-time 2026-09-30
```

## Agents on the semantic layer, without the dbt platform

The usual way to give an AI agent a dbt Semantic Layer is the dbt MCP server. Its Semantic Layer tools (`list_metrics`, `query_metrics` and the rest) need a dbt platform host, token and production environment ID, and they switch themselves off without them ([dbt docs](https://docs.getdbt.com/docs/dbt-ai/setup-local-mcp), checked 2026-11-02). On dbt Core there is a simpler route: MetricFlow's own CLI already lists metrics, lists dimensions and runs queries, and coding agents are good at CLIs.

Three pieces make an agent use it reliably:

| Piece | File | What it does |
|---|---|---|
| Rule | `AGENTS.md` (Claude Code reads it through `CLAUDE.md`) | Data questions go through metrics first; raw SQL only when no metric covers the question, and the answer says so. |
| Skill | `.claude/skills/query-metrics/SKILL.md` (Codex loads it through the `.agents/skills/query-metrics` symlink) | The steps (`mf list metrics`, `mf list dimensions`, `mf query`), how to check a metric's coverage date, and a table of the questions that go wrong with the query that gets them right. |
| Glossary | `docs/metrics.md`, generated by `scripts/build_glossary.py` | Every metric's meaning, formula, source table, first complete date and the exact `--group-by` names. Generated from the semantic manifest, so it cannot drift; `--check` fails when it is stale. |

Try it: open this repo in Claude Code or Codex and ask "What was my impressions CTR by traffic source over the last 28 days?" or "Which videos gained the most subscribers in October?". The agent should answer with `mf query` and mention the caveats in the metric descriptions (six impression surfaces only; channel-level subscribers; recent days still settling).

What this does not give you: a hosted API, BI tool integrations, caching or access control. Those are dbt platform features. A small MCP server that wraps `mf` would let agents without shell access use the same metrics; it is not built here.

## Metric canary skill

`.claude/skills/metricflow-canary` is a Claude Code skill that builds the canary for any dbt project with MetricFlow: it reconciles chosen metrics against an independent query on the source tables, pins settled periods in `canary/approved.csv`, and adds `canary/check_metrics.py` (exit 0 when everything matches, 1 when a number moved, 2 when the check could not run). Open this repo in Claude Code, or copy the folder into your own project's `.claude/skills/`, and ask for a metric canary.

## Project layout

```
seeds/reporting_codes.csv   code to name lookup for Reporting API dimensions
models/
  staging/     one view per source table; Reporting tables start at var reporting_complete_from
  marts/       dim_videos plus one fact per report, each with a unique row_key
  semantic/    semantic models and metrics, one file per group (traffic, activity, reach, audience, engagement, lifetime, analytics_history)
tests/         singular data tests (code lookup, demographic shares, CTR range); tests/python for the scripts
scripts/build_glossary.py   writes docs/metrics.md from the semantic manifest
docs/metrics.md             the metric glossary agents read
AGENTS.md, .claude/skills/query-metrics/   the rule and skill that point agents at mf
canary/
  canary.json        which metrics, grain and months the canary pins
  approved.csv       the reconciled answer for the pinned months
  check_metrics.py   re-runs mf query and compares it to approved.csv
  sql/               settled_months.sql, plus reconcile_core.sql and reconcile_extended.sql (independent checks on the source tables)
.claude/skills/metricflow-canary/   the Claude Code skill that builds the canary
```

## Run the canary

```bash
dbt build
python canary/check_metrics.py   # exit 0: every number matches; 1: a number moved; 2: the check could not run
```

## Settled months

YouTube revises recent days, and the pipeline's weekly refresh rewrites the last 35 days. `canary/sql/settled_months.sql` shows how far back each refresh reached. Pin only months that no refresh can rewrite again: on this data, about five weeks after the month closes.

## What the canary does not cover

- A baseline that was wrong from the start. Reconcile against independent SQL before pinning anything.
- Months still settling.
- A change in what a metric means that nobody writes down.
- The hosted dbt Semantic Layer APIs and BI integrations require the dbt platform. Nothing in this project does.

## References

- [MetricFlow commands](https://docs.getdbt.com/docs/build/metricflow-commands)
- [Ratio metrics](https://docs.getdbt.com/docs/build/ratio)
- [Open-sourcing MetricFlow](https://www.getdbt.com/blog/open-source-metricflow-governed-metrics)
- [dbt Discourse: testing strategies for the dbt Semantic Layer](https://discourse.getdbt.com/t/testing-strategies-for-dbt-semantic-layer/19811)

## License

MIT

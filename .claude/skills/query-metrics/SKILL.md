---
name: query-metrics
description: Answer questions about the YouTube channel's numbers (views, watch time, subscribers, impressions, CTR, traffic sources, devices, audience, cards, end screens, top videos) through the dbt MetricFlow semantic layer with the mf CLI, before any raw SQL. Use whenever someone asks a data question about the channel in this repo, such as "CTR by traffic source last 28 days" or "which videos gained the most subscribers in October".
---

# Query metrics

The metrics in `models/semantic/` are the governed definitions of the channel's numbers. Answering
through them means every agent gets the same number for the same question. This works on dbt Core
with the open-source MetricFlow CLI; no dbt platform account is needed.

## Steps

1. **Activate and check the manifest.** `source .venv/bin/activate`. `mf` reads
   `target/semantic_manifest.json`; if `models/semantic/` changed since the last build, run
   `dbt parse` first.
2. **Pick the metric.** Read `docs/metrics.md` (meaning, formula, source, **Data starts**, valid
   group-bys) or run `mf list metrics`. Prefer the plain metric (`total_views`) over a narrow one
   (`traffic_detail_views`, `shares_by_service`) unless the question needs that narrow dimension.
3. **Pick dimensions.** `mf list dimensions --metrics <metric>`, or the **Group by** line in the
   glossary. Use the exact prefixed name, for example `video_traffic_day__traffic_source`.
4. **Check the period.** If the question starts before the metric's **Data starts** date, the
   answer is a partial total. Say so, or switch to the `analytics_*` metric for earlier history.
   Anything in the last five weeks can still change; label it provisional.
5. **Query.**
   ```bash
   mf query --metrics <m1>,<m2> --group-by metric_time__month,<dimension> \
     --start-time YYYY-MM-DD --end-time YYYY-MM-DD [--order -<m1>] [--limit 10] \
     [--where "{{ Dimension('<entity>__<dim>') }} = 'value'"]
   ```
   Add `--explain` to show the SQL MetricFlow generates.
6. **Answer** with the numbers, the metric names used, the period, and any caveat from the
   metric's description. If no metric fits, say that, then use SQL on the source tables.

## Pitfalls and the right query

| Question shape | Wrong | Right |
|---|---|---|
| Rank videos by subscribers | grouping `subscribers_gained` by `video__title` alone shows a blank title holding about a third of gains | add `--where "{{ Dimension('video_activity_day__attribution') }} = 'video'"` |
| Click-through rate | `total_views / total_impressions` (impressions exist on only six surfaces) | `impressions_ctr` (a fraction: 0.056 = 5.6%) |
| Views and CTR by traffic source | one query: each fact has its own traffic source dimension | two queries: `total_views` by `video_traffic_day__traffic_source`, `impressions_ctr` by `video_reach_day__traffic_source` |
| Average of a rate | averaging daily `avg_view_duration_seconds` or `impressions_ctr` | query the ratio metric at the grain you need; MetricFlow recomputes it from totals |
| Audience share by age | treating `estimated_demographic_views` as exact, or adding it across queries with different filters | group by `video_demographic_day__age_group`, then divide each row by the total of all rows; call it an estimate |
| Views before August 2026 | `total_views` for June (returns nothing or a partial month) | `analytics_views` |
| Lifetime counts | adding `lifetime_views` across days | `lifetime_views` takes the latest snapshot in each period by itself; compare periods, never sum them |

## Worked examples

**CTR by traffic source, last 28 days** (dates are examples; use the 28 days before the latest
loaded day):
```bash
mf query --metrics impressions_ctr,total_impressions --group-by video_reach_day__traffic_source \
  --start-time 2026-10-04 --end-time 2026-10-31 --order -total_impressions
```
Report CTR as a percentage, mention that it covers the six impression surfaces only, and that the
last days are provisional.

**Videos with the most subscribers gained in October:**
```bash
mf query --metrics subscribers_gained --group-by video__title \
  --start-time 2026-10-01 --end-time 2026-10-31 --order -subscribers_gained --limit 10 \
  --where "{{ Dimension('video_activity_day__attribution') }} = 'video'"
```
Then state how many October gains were channel-level (run once without the filter) and that
October is not final until early December.

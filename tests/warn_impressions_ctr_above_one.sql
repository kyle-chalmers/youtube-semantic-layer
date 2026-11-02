-- impressions_ctr is a fraction, so values above 1 are suspect source rows. Warn, not fail:
-- YouTube occasionally reports them (one row of 2.0 in September 2026).
{{ config(severity='warn') }}
select report_date, video_id, traffic_source, impressions, impressions_ctr
from {{ ref('fct_video_reach_days') }}
where impressions_ctr > 1

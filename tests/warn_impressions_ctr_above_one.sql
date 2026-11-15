-- impressions_ctr is a fraction, so values above 1 are suspect source rows. Warn, not fail:
-- YouTube reports them on rows with only a few impressions (about 14 rows a month).
{{ config(severity='warn') }}
select report_date, video_id, traffic_source, impressions, impressions_ctr
from {{ ref('fct_video_reach_days') }}
where impressions_ctr > 1

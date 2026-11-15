-- Engagement and subscriber activity per Pacific day, video, subscribed status and country.
-- Views and watch time live in fct_video_traffic_days, which totals exactly to the same source
-- from September 2026 (stg_reporting_channel_combined notes the August 2026 differences).
select
    {{ row_key(['report_date', 'video_id', 'live_or_on_demand', 'subscribed_status', 'country_code']) }} as row_key,
    *
from {{ ref('stg_reporting_channel_basic') }}

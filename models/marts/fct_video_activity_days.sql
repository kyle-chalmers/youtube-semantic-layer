-- Engagement and subscriber activity per Pacific day, video, subscribed status and country.
-- Views and watch time live in fct_video_traffic_days, which totals exactly to the same source.
select
    {{ row_key(['report_date', 'video_id', 'subscribed_status', 'country_code']) }} as row_key,
    *
from {{ ref('stg_reporting_channel_basic') }}

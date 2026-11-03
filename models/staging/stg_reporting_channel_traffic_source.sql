-- One row per Pacific day, video, subscribed status, country, traffic source and detail.
-- traffic_source_detail is the search term, referring video or site; YouTube leaves it
-- null when the volume is too small to report.
select
    report_date,
    video_id,
    subscribed_status,
    country_code,
    traffic_source_type,
    traffic_source_detail,
    views,
    engaged_views,
    watch_time_minutes
from {{ source('youtube', 'reporting_channel_traffic_source_a3') }}
where {{ reporting_window() }}

-- One row per video per activity day from the Analytics API.
-- This table has no views column. Views come from stg_daily_traffic_sources; dividing
-- watch time by average view duration gives roughly engaged views, not views.
select
    video_id,
    activity_date,
    estimated_minutes_watched,
    average_view_duration_seconds,
    subscribers_gained,
    subscribers_lost,
    shares
from {{ source('youtube', 'daily_video_analytics') }}

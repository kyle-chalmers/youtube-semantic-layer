-- One row per video per activity day per Analytics traffic source. Unlike
-- daily_video_analytics, this table holds true views.
select
    activity_date,
    video_id,
    traffic_source_type,
    views,
    estimated_minutes_watched
from {{ source('youtube', 'daily_traffic_sources') }}

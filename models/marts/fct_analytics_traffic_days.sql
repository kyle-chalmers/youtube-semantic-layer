-- Analytics API history: views per video per activity day per traffic source, back to 2025-10-16.
select
    {{ row_key(['activity_date', 'video_id', 'traffic_source_type']) }} as row_key,
    activity_date,
    video_id,
    traffic_source_type as analytics_traffic_source,
    views,
    estimated_minutes_watched
from {{ ref('stg_daily_traffic_sources') }}

-- One row per video per activity day.
-- The source stores minutes watched and average view duration but not views,
-- so views are reconstructed as minutes watched * 60 / average view duration.
-- Days with an average view duration of 0 get null views.
select
    video_id,
    activity_date,
    estimated_minutes_watched,
    estimated_minutes_watched * 60 as seconds_watched,
    average_view_duration_seconds,
    safe_divide(estimated_minutes_watched * 60, nullif(average_view_duration_seconds, 0)) as views,
    subscribers_gained,
    subscribers_lost,
    shares
from {{ source('youtube', 'daily_video_analytics') }}

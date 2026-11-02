-- Analytics API history: one row per video per activity day, back to 2025-10-16.
-- Minutes are truncated to whole minutes per row, so totals run about 2% below Reporting.
select
    {{ row_key(['activity_date', 'video_id']) }} as row_key,
    video_id,
    activity_date,
    estimated_minutes_watched,
    subscribers_gained,
    subscribers_lost,
    shares
from {{ ref('stg_daily_video_analytics') }}

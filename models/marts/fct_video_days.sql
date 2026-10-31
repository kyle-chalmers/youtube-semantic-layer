-- One row per video per activity day, with the video's type attached.
select
    a.video_id,
    a.activity_date,
    m.video_type,
    a.estimated_minutes_watched,
    a.seconds_watched,
    a.average_view_duration_seconds,
    a.views,
    a.subscribers_gained,
    a.subscribers_lost,
    a.shares
from {{ ref('stg_daily_video_analytics') }} as a
left join {{ ref('stg_video_metadata') }} as m
    using (video_id)

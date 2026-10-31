-- video_metadata keeps one row per video per snapshot date.
-- Keep only the latest snapshot so joins stay one row per video.
select
    video_id,
    title,
    published_at,
    duration_seconds,
    video_type
from {{ source('youtube', 'video_metadata') }}
qualify row_number() over (partition by video_id order by snapshot_date desc) = 1

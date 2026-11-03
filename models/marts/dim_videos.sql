-- One row per video, from the latest metadata snapshot.
select
    video_id,
    title,
    video_type,
    published_at,
    date(published_at, 'America/Los_Angeles') as published_date,
    duration_seconds
from {{ ref('stg_video_metadata') }}

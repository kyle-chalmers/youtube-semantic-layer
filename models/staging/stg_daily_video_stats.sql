-- One row per video per snapshot date. The counts are lifetime running totals, so they
-- add up across videos but never across days.
select
    snapshot_date,
    video_id,
    view_count,
    like_count,
    comment_count
from {{ source('youtube', 'daily_video_stats') }}

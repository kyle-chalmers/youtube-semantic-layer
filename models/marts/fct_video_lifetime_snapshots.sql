-- Lifetime view, like and comment counts per video per snapshot date (Data API).
select
    {{ row_key(['snapshot_date', 'video_id']) }} as row_key,
    *
from {{ ref('stg_daily_video_stats') }}

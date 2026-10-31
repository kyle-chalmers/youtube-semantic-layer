-- How many rows each weekly refresh changed for one month, comparing the archived
-- copy of each row with the current table. A month is settled once refreshes stop
-- changing it. Replace the project and dataset with your own.
with cur as (
    select video_id, activity_date, estimated_minutes_watched as minutes
    from `your-gcp-project-id.youtube_analytics.daily_video_analytics`
    where activity_date between '2026-09-01' and '2026-09-30'
),
arc as (
    select video_id, activity_date, archived_at, estimated_minutes_watched as minutes
    from `your-gcp-project-id.youtube_analytics.daily_video_analytics_refresh_archive`
    where activity_date between '2026-09-01' and '2026-09-30'
)
select
    date(arc.archived_at) as refresh_date,
    count(*) as rows_compared,
    countif(abs(arc.minutes - cur.minutes) > 0.01) as rows_changed
from arc
join cur using (video_id, activity_date)
group by refresh_date
order by refresh_date

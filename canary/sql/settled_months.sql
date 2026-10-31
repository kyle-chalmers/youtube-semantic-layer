-- How far back each weekly refresh rewrote the analytics table.
-- A month is final once a refresh has run more than that many days after its last day.
-- Replace the project and dataset with your own.
select
    refresh_run_id,
    date(min(archived_at)) as refreshed_on,
    min(activity_date) as oldest_day_rewritten,
    max(activity_date) as newest_day_rewritten,
    date_diff(date(min(archived_at)), min(activity_date), day) as days_back
from `your-gcp-project-id.youtube_analytics.daily_video_analytics_refresh_archive`
group by refresh_run_id
order by refreshed_on desc

-- Independent check of the core metrics for one month, written on the source tables
-- (not the dbt models). Compare with:
--   mf query --metrics total_views,total_engaged_views,total_seconds_watched,total_minutes_watched,avg_view_duration_seconds,total_likes,total_dislikes,total_comments,total_shares,subscribers_gained,subscribers_lost,playlist_adds,playlist_removes --group-by metric_time__month --start-time 2026-09-01 --end-time 2026-09-30
-- and, for video-attributed subscribers, add --where "{{ Dimension('video_activity_day__attribution') }} = 'video'".
-- Replace the project and dataset with your own.
with combined as (
    select
        sum(views) as total_views,
        sum(engaged_views) as total_engaged_views,
        sum(watch_time_minutes) * 60 as total_seconds_watched,
        sum(watch_time_minutes) as total_minutes_watched
    from `your-gcp-project-id.youtube_analytics.reporting_channel_combined_a3`
    where report_date between '2026-09-01' and '2026-09-30'
),

basic as (
    select
        sum(likes) as total_likes,
        sum(dislikes) as total_dislikes,
        sum(comments) as total_comments,
        sum(shares) as total_shares,
        sum(subscribers_gained) as subscribers_gained,
        sum(subscribers_lost) as subscribers_lost,
        sum(videos_added_to_playlists) as playlist_adds,
        sum(videos_removed_from_playlists) as playlist_removes,
        sum(if(video_id is not null, subscribers_gained, 0)) as video_subscribers_gained
    from `your-gcp-project-id.youtube_analytics.reporting_channel_basic_a3`
    where report_date between '2026-09-01' and '2026-09-30'
)

select
    combined.*,
    combined.total_seconds_watched / combined.total_engaged_views as avg_view_duration_seconds,
    basic.*
from combined cross join basic

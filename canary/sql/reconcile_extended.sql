-- Independent check of every non-core metric for September 2026, on the source tables.
-- Compare with mf query --metrics <metric> --group-by metric_time__month --start-time 2026-09-01 --end-time 2026-09-30.
-- lifetime_* use the latest snapshot in the month. Replace the project and dataset with your own.
declare start_date date default '2026-09-01';
declare end_date date default '2026-09-30';

with traffic_detail as (
    select sum(views) as traffic_detail_views
    from `your-gcp-project-id.youtube_analytics.reporting_channel_traffic_source_a3`
    where report_date between start_date and end_date
),

reach as (
    select
        sum(video_thumbnail_impressions) as total_impressions,
        sum(video_thumbnail_impressions * video_thumbnail_impressions_ctr) as impression_clicks,
        safe_divide(sum(video_thumbnail_impressions * video_thumbnail_impressions_ctr), sum(video_thumbnail_impressions)) as impressions_ctr
    from `your-gcp-project-id.youtube_analytics.reporting_channel_reach_combined_a1`
    where report_date between start_date and end_date
),

video_day_views as (
    select report_date, video_id, sum(views) as v
    from `your-gcp-project-id.youtube_analytics.reporting_channel_combined_a3`
    where report_date between start_date and end_date and video_id is not null
    group by 1, 2
),

demographics as (
    select sum(coalesce(v.v, 0) * d.views_percentage / 100) as estimated_demographic_views
    from `your-gcp-project-id.youtube_analytics.reporting_channel_demographics_a1` as d
    left join video_day_views as v using (report_date, video_id)
    where d.report_date between start_date and end_date
),

cards as (
    select sum(card_impressions) as card_impressions, sum(card_clicks) as card_clicks,
           sum(card_teaser_impressions) as card_teaser_impressions, sum(card_teaser_clicks) as card_teaser_clicks
    from `your-gcp-project-id.youtube_analytics.reporting_channel_cards_a1`
    where report_date between start_date and end_date
),

end_screens as (
    select sum(end_screen_element_impressions) as end_screen_impressions, sum(end_screen_element_clicks) as end_screen_clicks
    from `your-gcp-project-id.youtube_analytics.reporting_channel_end_screens_a1`
    where report_date between start_date and end_date
),

sharing as (
    select sum(shares) as shares_by_service
    from `your-gcp-project-id.youtube_analytics.reporting_channel_sharing_service_a1`
    where report_date between start_date and end_date
),

lifetime as (
    select sum(view_count) as lifetime_views, sum(like_count) as lifetime_likes, sum(comment_count) as lifetime_comments
    from `your-gcp-project-id.youtube_analytics.daily_video_stats`
    where snapshot_date = (
        select max(snapshot_date) from `your-gcp-project-id.youtube_analytics.daily_video_stats`
        where snapshot_date between start_date and end_date
    )
),

analytics as (
    select sum(estimated_minutes_watched) as analytics_minutes_watched, sum(subscribers_gained) as analytics_subscribers_gained,
           sum(subscribers_lost) as analytics_subscribers_lost, sum(shares) as analytics_shares
    from `your-gcp-project-id.youtube_analytics.daily_video_analytics`
    where activity_date between start_date and end_date
),

analytics_traffic as (
    select sum(views) as analytics_views
    from `your-gcp-project-id.youtube_analytics.daily_traffic_sources`
    where activity_date between start_date and end_date
)

select *
from traffic_detail, reach, demographics, cards, end_screens, sharing, lifetime, analytics, analytics_traffic

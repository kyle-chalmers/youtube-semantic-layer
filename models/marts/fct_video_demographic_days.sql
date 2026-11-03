-- Estimated views by age group and gender per Pacific day and video.
-- YouTube only gives each row's share of the video-day's logged-in views, so the estimate
-- applies that share to the video-day's total views (summed over every country, subscribed
-- status and traffic dimension in the combined table). Video-days without demographics are absent.
with video_day_views as (
    select report_date, video_id, sum(views) as video_day_views
    from {{ ref('stg_reporting_channel_combined') }}
    where video_id is not null
    group by report_date, video_id
)

select
    {{ row_key(['d.report_date', 'd.video_id', 'd.subscribed_status', 'd.country_code', 'd.age_group',
                'd.gender']) }} as row_key,
    d.report_date,
    d.video_id,
    d.subscribed_status,
    d.country_code,
    d.age_group,
    d.gender,
    d.views_percentage,
    coalesce(v.video_day_views, 0) * d.views_percentage / 100 as estimated_views
from {{ ref('stg_reporting_channel_demographics') }} as d
left join video_day_views as v
    using (report_date, video_id)

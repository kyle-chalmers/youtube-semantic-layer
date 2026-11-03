-- One row per Pacific day, video, subscribed status, country, age group and gender.
-- views_percentage is a share of that video-day's logged-in views and sums to 100 per video per day.
select
    report_date,
    video_id,
    subscribed_status,
    country_code,
    age_group,
    gender,
    views_percentage
from {{ source('youtube', 'reporting_channel_demographics_a1') }}
where {{ reporting_window() }}

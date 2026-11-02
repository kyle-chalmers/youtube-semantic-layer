-- One row per Pacific day, video, subscribed status, country and sharing service.
select
    report_date,
    video_id,
    subscribed_status,
    country_code,
    sharing_service,
    shares
from {{ source('youtube', 'reporting_channel_sharing_service_a1') }}
where {{ reporting_window() }}

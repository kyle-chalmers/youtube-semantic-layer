-- One row per Pacific day, video, subscribed status, country, playback location,
-- traffic source, device and operating system. From September 2026 views, engaged views and
-- watch time here total exactly to the basic table. In August 2026 they differ on 7 days: basic
-- reports 30 more views, and the traffic source table 4 fewer. This table carries every slicing dimension.
select
    report_date,
    video_id,
    if(video_id is null, 'channel', 'video') as attribution,
    live_or_on_demand,
    subscribed_status,
    country_code,
    playback_location_type,
    traffic_source_type,
    device_type,
    operating_system,
    views,
    engaged_views,
    watch_time_minutes
from {{ source('youtube', 'reporting_channel_combined_a3') }}
where {{ reporting_window() }}

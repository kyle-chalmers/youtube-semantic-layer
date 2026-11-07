-- Views, engaged views and watch time per Pacific day, video, subscribed status, country,
-- traffic source, device, operating system and playback location, with code names attached.
select
    {{ row_key(['report_date', 'video_id', 'subscribed_status', 'country_code', 'playback_location_type',
                'traffic_source_type', 'device_type', 'operating_system']) }} as row_key,
    report_date,
    video_id,
    attribution,
    subscribed_status,
    country_code,
    {{ code_name('traffic_source_type', 'traffic_source_type') }} as traffic_source,
    {{ code_name('device_type', 'device_type') }} as device_type,
    {{ code_name('operating_system', 'operating_system') }} as operating_system,
    {{ code_name('playback_location_type', 'playback_location_type') }} as playback_location,
    views,
    engaged_views,
    watch_time_minutes
from {{ ref('stg_reporting_channel_combined') }}
where video_id in (select video_id from {{ ref('dim_videos') }} where video_type = 'full_length')

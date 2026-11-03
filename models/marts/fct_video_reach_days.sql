-- Thumbnail impressions and clicks per Pacific day, video, traffic source, detail, OS and device.
-- Impressions exist only on six YouTube surfaces (search, suggested, browse, channel page and two
-- playlist surfaces), so they never line up with total views.
select
    {{ row_key(['report_date', 'video_id', 'traffic_source_type', 'traffic_source_detail',
                'operating_system', 'device_type']) }} as row_key,
    report_date,
    video_id,
    {{ code_name('traffic_source_type', 'traffic_source_type') }} as traffic_source,
    traffic_source_detail,
    {{ code_name('device_type', 'device_type') }} as device_type,
    {{ code_name('operating_system', 'operating_system') }} as operating_system,
    impressions,
    impression_clicks,
    impressions_ctr
from {{ ref('stg_reporting_channel_reach') }}

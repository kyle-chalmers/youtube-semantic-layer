-- One row per Pacific day, video, traffic source, detail, operating system and device.
-- video_thumbnail_impressions_ctr is stored as a fraction (0.056 = 5.6%), so clicks are
-- impressions * ctr with no division by 100.
select
    report_date,
    video_id,
    traffic_source_type,
    traffic_source_detail,
    operating_system,
    device_type,
    video_thumbnail_impressions as impressions,
    video_thumbnail_impressions * video_thumbnail_impressions_ctr as impression_clicks,
    video_thumbnail_impressions_ctr as impressions_ctr
from {{ source('youtube', 'reporting_channel_reach_combined_a1') }}
where {{ reporting_window() }}

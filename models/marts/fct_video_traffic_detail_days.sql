-- Views per Pacific day, video, traffic source and traffic source detail (search term,
-- referring video or site). Use only when the detail itself is the question.
select
    {{ row_key(['report_date', 'video_id', 'subscribed_status', 'country_code', 'traffic_source_type',
                'traffic_source_detail']) }} as row_key,
    report_date,
    video_id,
    {{ code_name('traffic_source_type', 'traffic_source_type') }} as traffic_source,
    traffic_source_detail,
    views,
    watch_time_minutes
from {{ ref('stg_reporting_channel_traffic_source') }}

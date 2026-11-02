-- Shares per Pacific day, video, subscribed status, country and sharing service.
select
    {{ row_key(['report_date', 'video_id', 'subscribed_status', 'country_code', 'sharing_service']) }} as row_key,
    report_date,
    video_id,
    subscribed_status,
    country_code,
    {{ code_name('sharing_service', 'sharing_service') }} as sharing_service,
    shares
from {{ ref('stg_reporting_channel_sharing_service') }}

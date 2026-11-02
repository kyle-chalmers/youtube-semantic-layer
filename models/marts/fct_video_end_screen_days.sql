-- End screen element impressions and clicks per Pacific day, video, subscribed status, country and element.
select
    {{ row_key(['report_date', 'video_id', 'subscribed_status', 'country_code', 'end_screen_element_type',
                'end_screen_element_id']) }} as row_key,
    report_date,
    video_id,
    subscribed_status,
    country_code,
    {{ code_name('end_screen_element_type', 'end_screen_element_type') }} as end_screen_element_type,
    end_screen_element_id,
    end_screen_element_impressions,
    end_screen_element_clicks
from {{ ref('stg_reporting_channel_end_screens') }}

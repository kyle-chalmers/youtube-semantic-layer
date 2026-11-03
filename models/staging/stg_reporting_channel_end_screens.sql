-- One row per Pacific day, video, subscribed status, country and end screen element.
select
    report_date,
    video_id,
    subscribed_status,
    country_code,
    end_screen_element_type,
    end_screen_element_id,
    end_screen_element_impressions,
    end_screen_element_clicks
from {{ source('youtube', 'reporting_channel_end_screens_a1') }}
where {{ reporting_window() }}

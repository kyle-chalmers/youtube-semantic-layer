-- One row per Pacific day, video, subscribed status, country and card.
select
    report_date,
    video_id,
    subscribed_status,
    country_code,
    card_type,
    card_id,
    card_impressions,
    card_clicks,
    card_teaser_impressions,
    card_teaser_clicks
from {{ source('youtube', 'reporting_channel_cards_a1') }}
where {{ reporting_window() }}

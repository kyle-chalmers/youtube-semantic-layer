-- Card and card teaser impressions and clicks per Pacific day, video, subscribed status, country and card.
select
    {{ row_key(['report_date', 'video_id', 'subscribed_status', 'country_code', 'card_type', 'card_id']) }} as row_key,
    report_date,
    video_id,
    subscribed_status,
    country_code,
    {{ code_name('card_type', 'card_type') }} as card_type,
    card_id,
    card_impressions,
    card_clicks,
    card_teaser_impressions,
    card_teaser_clicks
from {{ ref('stg_reporting_channel_cards') }}

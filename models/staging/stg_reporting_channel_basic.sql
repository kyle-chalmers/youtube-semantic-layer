-- One row per Pacific day, video, subscribed status and country.
-- Rows with no video_id are channel-level activity (mostly subscribers gained on the channel page);
-- they are kept so channel totals match YouTube Studio and labeled by attribution.
select
    report_date,
    video_id,
    if(video_id is null, 'channel', 'video') as attribution,
    subscribed_status,
    country_code,
    likes,
    dislikes,
    comments,
    shares,
    subscribers_gained,
    subscribers_lost,
    videos_added_to_playlists,
    videos_removed_from_playlists
from {{ source('youtube', 'reporting_channel_basic_a3') }}
where {{ reporting_window() }}

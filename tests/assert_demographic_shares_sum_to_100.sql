-- The demographic estimate assumes views_percentage sums to 100 per video per day.
-- Any video-day that does not breaks the estimate.
select report_date, video_id, sum(views_percentage) as total_percentage
from {{ ref('stg_reporting_channel_demographics') }}
group by report_date, video_id
having abs(sum(views_percentage) - 100) > 0.5

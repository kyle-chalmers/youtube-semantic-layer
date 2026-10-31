select date_day
from unnest(generate_date_array('2024-01-01', '2030-12-31')) as date_day

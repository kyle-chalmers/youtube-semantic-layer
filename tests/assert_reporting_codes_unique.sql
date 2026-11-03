-- Each code appears once per dimension, so name lookups return one row.
select dimension, code, count(*) as n
from {{ ref('reporting_codes') }}
group by dimension, code
having count(*) > 1

{# Name for a Reporting API code, from the reporting_codes seed. Unknown codes show as "Code <n>". #}
{% macro code_name(dimension, column) %}
    coalesce(
        (select name from {{ ref('reporting_codes') }} where dimension = '{{ dimension }}' and code = {{ column }}),
        concat('Code ', {{ column }})
    )
{% endmacro %}

{# Stable key for one row of a fact table: a hash of its grain columns. #}
{% macro row_key(columns) %}
    to_hex(md5(to_json_string(struct({{ columns | join(', ') }}))))
{% endmacro %}

{# Reporting API rows on or after the first date every Reporting table covers. #}
{% macro reporting_window(date_column='report_date') %}
    {{ date_column }} >= date('{{ var("reporting_complete_from") }}')
{% endmacro %}

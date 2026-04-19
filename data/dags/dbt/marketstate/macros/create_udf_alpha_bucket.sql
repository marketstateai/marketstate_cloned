{% macro create_udf_alpha_bucket() %}
  {% set sql %}
    create or replace function `general-428410.udfs.alpha_bucket`(sym string)
    returns int64
    as (
      case
        when sym is null then null
        when regexp_contains(upper(substr(sym, 1, 1)), r'[A-Z]') then
          ascii(upper(substr(sym, 1, 1))) - ascii('A') + 1
        else null
      end
    )
  {% endset %}

  {{ run_query(sql) }}
{% endmacro %}

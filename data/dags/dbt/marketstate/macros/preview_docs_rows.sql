{% macro preview_docs_rows(
    relation_name,
    schema,
    database=None,
    limit=5,
    sample_percent=1,
    partition_filter=None,
    use_partition_filter=False
  )
%}
  {% set resolved_database = database or target.database or target.project %}
  {% set relation = adapter.get_relation(database=resolved_database, schema=schema, identifier=relation_name) %}
  {% if relation is none %}
    {% do exceptions.raise_compiler_error("relation not found: " ~ (resolved_database or "") ~ "." ~ schema ~ "." ~ relation_name) %}
  {% endif %}

  {% if use_partition_filter and partition_filter %}
    {% set sql %}
      select *
      from {{ relation }}
      where {{ partition_filter }}
      order by rand()
      limit {{ limit }}
    {% endset %}
  {% else %}
    {% set sql %}
      select *
      from {{ relation }} tablesample system ({{ sample_percent }} percent)
      order by rand()
      limit {{ limit }}
    {% endset %}
  {% endif %}

  {% set results = run_query(sql) %}
  {% if execute %}
    {% set rows = [] %}
    {% for row in results %}
      {% set row_dict = {} %}
      {% for column in results.columns %}
        {% set column_name = column.name %}
        {% set value = row[column_name] %}
        {% if value is none %}
          {% do row_dict.update({column_name: value}) %}
        {% else %}
          {% do row_dict.update({column_name: value | string}) %}
        {% endif %}
      {% endfor %}
      {% do rows.append(row_dict) %}
    {% endfor %}
    {{ log("DOCS_PREVIEW_JSON=" ~ (rows | tojson), info=True) }}
  {% endif %}
{% endmacro %}

{{
  config(
    materialized = "table"
  )
}}

-- Vanilla date dimension (no source inputs).
-- Default range: from 2000-01-01 through 10 years into the future.
-- Override range via vars if desired:
--   dbt run -s dim_date --vars '{dim_date_start: "2000-01-01", dim_date_end: "2036-12-31"}'
WITH params AS (
  SELECT
    DATE("{{ var('dim_date_start', '2000-01-01') }}") AS start_date,
    DATE(
      COALESCE(
        NULLIF("{{ var('dim_date_end', '') }}", ''),
        FORMAT_DATE('%F', DATE_ADD(CURRENT_DATE(), INTERVAL 10 YEAR))
      )
    ) AS end_date
),
spine AS (
  SELECT d AS date
  FROM params, UNNEST(GENERATE_DATE_ARRAY(start_date, end_date)) AS d
)

SELECT
  CAST(FORMAT_DATE("%Y%m%d", date) AS INT64) AS date_key,
  date,
  EXTRACT(YEAR FROM date) AS year,
  EXTRACT(MONTH FROM date) AS month,
  EXTRACT(QUARTER FROM date) AS quarter,
  EXTRACT(DAY FROM date) AS day,
  EXTRACT(DAYOFWEEK FROM date) AS day_of_week
FROM spine

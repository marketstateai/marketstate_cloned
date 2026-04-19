{{
  config(
    materialized = "table"
  )
}}

-- Country-level fiscal periods (heuristic).
-- NOTE: Corporate fiscal years vary by company; this is intended for country/macro reporting.
--
-- Default range: 2000-01-01 through CURRENT_DATE() + 10 years.
-- Override range via vars if desired:
--   dbt run -s stg_country_financial_periods --vars '{period_start: "2000-01-01", period_end: "2036-12-31"}'
WITH params AS (
  SELECT
    DATE("{{ var('period_start', '2000-01-01') }}") AS start_date,
    DATE(
      COALESCE(
        NULLIF("{{ var('period_end', '') }}", ''),
        FORMAT_DATE('%F', DATE_ADD(CURRENT_DATE(), INTERVAL 10 YEAR))
      )
    ) AS end_date
),

-- All ISO-3166-1 alpha-2 countries/territories (hardcoded).
-- `fy_end_month` = fiscal year end month number (1-12). Default: 12 unless overridden.
country_codes AS (
  SELECT country_code
  FROM UNNEST([
    "AD","AE","AF","AG","AI","AL","AM","AO","AQ","AR","AS","AT","AU","AW","AX","AZ",
    "BA","BB","BD","BE","BF","BG","BH","BI","BJ","BL","BM","BN","BO","BQ","BR","BS","BT","BV","BW","BY","BZ",
    "CA","CC","CD","CF","CG","CH","CI","CK","CL","CM","CN","CO","CR","CU","CV","CW","CX","CY","CZ",
    "DE","DJ","DK","DM","DO","DZ",
    "EC","EE","EG","EH","ER","ES","ET",
    "FI","FJ","FK","FM","FO","FR",
    "GA","GB","GD","GE","GF","GG","GH","GI","GL","GM","GN","GP","GQ","GR","GS","GT","GU","GW","GY",
    "HK","HM","HN","HR","HT","HU",
    "ID","IE","IL","IM","IN","IO","IQ","IR","IS","IT",
    "JE","JM","JO","JP",
    "KE","KG","KH","KI","KM","KN","KP","KR","KW","KY","KZ",
    "LA","LB","LC","LI","LK","LR","LS","LT","LU","LV","LY",
    "MA","MC","MD","ME","MF","MG","MH","MK","ML","MM","MN","MO","MP","MQ","MR","MS","MT","MU","MV","MW","MX","MY","MZ",
    "NA","NC","NE","NF","NG","NI","NL","NO","NP","NR","NU","NZ",
    "OM",
    "PA","PE","PF","PG","PH","PK","PL","PM","PN","PR","PS","PT","PW","PY",
    "QA",
    "RE","RO","RS","RU","RW",
    "SA","SB","SC","SD","SE","SG","SH","SI","SJ","SK","SL","SM","SN","SO","SR","SS","ST","SV","SX","SY","SZ",
    "TC","TD","TF","TG","TH","TJ","TK","TL","TM","TN","TO","TR","TT","TV","TW","TZ",
    "UA","UG","UM","US","UY","UZ",
    "VA","VC","VE","VG","VI","VN","VU",
    "WF","WS",
    "YE","YT",
    "ZA","ZM","ZW"
  ]) AS country_code
),

fy_overrides AS (
  SELECT * FROM UNNEST([
    STRUCT("US" AS country_code, 9 AS fy_end_month),   -- US federal FY ends Sep
    STRUCT("JP" AS country_code, 3 AS fy_end_month),
    STRUCT("IN" AS country_code, 3 AS fy_end_month),
    STRUCT("GB" AS country_code, 3 AS fy_end_month),
    STRUCT("CA" AS country_code, 3 AS fy_end_month),
    STRUCT("AU" AS country_code, 6 AS fy_end_month),
    STRUCT("NZ" AS country_code, 6 AS fy_end_month)
  ])
),

countries AS (
  SELECT
    cc.country_code,
    COALESCE(o.fy_end_month, 12) AS fy_end_month
  FROM country_codes cc
  LEFT JOIN fy_overrides o
    ON cc.country_code = o.country_code
),

months AS (
  SELECT
    m AS month_start
  FROM params, UNNEST(GENERATE_DATE_ARRAY(start_date, end_date, INTERVAL 1 MONTH)) AS m
),

month_ends AS (
  SELECT
    c.country_code,
    c.fy_end_month,
    LAST_DAY(m.month_start, MONTH) AS period_end_date,
    EXTRACT(MONTH FROM LAST_DAY(m.month_start, MONTH)) AS end_month
  FROM months m
  CROSS JOIN countries c
),

fiscal_quarter_ends AS (
  SELECT
    country_code,
    fy_end_month,
    period_end_date,
    -- offset of this month-end from fiscal year end month (0,3,6,9 are quarter ends)
    MOD(end_month - fy_end_month + 12, 12) AS moff
  FROM month_ends
  WHERE MOD(end_month - fy_end_month + 12, 12) IN (0, 3, 6, 9)
),

periods AS (
  SELECT
    country_code,
    "quarterly" AS period_type,
    period_end_date,
    -- Fiscal year is the year in which the fiscal year ends.
    EXTRACT(YEAR FROM period_end_date) + IF(EXTRACT(MONTH FROM period_end_date) > fy_end_month, 1, 0) AS fiscal_year,
    CAST(4 - (moff / 3) AS INT64) AS fiscal_quarter
  FROM fiscal_quarter_ends

  UNION ALL

  SELECT
    country_code,
    "annual" AS period_type,
    period_end_date,
    EXTRACT(YEAR FROM period_end_date) AS fiscal_year,
    4 AS fiscal_quarter
  FROM fiscal_quarter_ends
  WHERE moff = 0
)

SELECT
  TO_HEX(MD5(CONCAT(country_code, "|", period_type, "|", CAST(period_end_date AS STRING)))) AS period_sk,
  country_code,
  period_type,
  period_end_date,
  CAST(FORMAT_DATE("%Y%m%d", period_end_date) AS INT64) AS period_end_date_key,
  fiscal_year,
  fiscal_quarter,
  FORMAT("%s_%s_FY%dQ%d", country_code, period_type, fiscal_year, fiscal_quarter) AS period_label
FROM periods

{{
  config(
    materialized = "table",
    schema = "int_prod"
  )
}}

-- Listing = (symbol on an exchange). This is the stable join key for daily price facts.
-- We intentionally model listings off the stock snapshot + exchanges MIC metadata.

WITH stocks AS (
  SELECT
    yf_symbol,
    market_identifier_code,
    exchange_currency,
    company_currency,
    capture_date
  FROM {{ ref('stg_stocks') }}
  WHERE TRUE
    AND yf_symbol IS NOT NULL
    AND market_identifier_code IS NOT NULL
),

exchanges AS (
  SELECT
    market_identifier_code,
    exchange_name,
    country,
    currency AS exchange_currency
  FROM {{ ref('exchanges') }}
  WHERE market_identifier_code IS NOT NULL
),

deduped AS (
  SELECT
    stocks.yf_symbol,
    stocks.market_identifier_code,
    COALESCE(stocks.exchange_currency, exchanges.exchange_currency) AS exchange_currency,
    stocks.company_currency,
    exchanges.exchange_name,
    exchanges.country,
    MAX(stocks.capture_date) AS last_seen_capture_date
  FROM stocks
  LEFT JOIN exchanges
    ON stocks.market_identifier_code = exchanges.market_identifier_code
  GROUP BY
    yf_symbol,
    market_identifier_code,
    exchange_currency,
    company_currency,
    exchange_name,
    country
)

SELECT
  TO_HEX(MD5(CONCAT(CAST(market_identifier_code AS STRING), "|", CAST(yf_symbol AS STRING)))) AS listing_sk,
  CAST(market_identifier_code AS STRING) AS market_identifier_code,
  CAST(yf_symbol AS STRING) AS yf_symbol,
  CAST(exchange_name AS STRING) AS exchange_name,
  CAST(country AS STRING) AS country,
  CAST(exchange_currency AS STRING) AS exchange_currency,
  CAST(company_currency AS STRING) AS company_currency,
  CAST(last_seen_capture_date AS DATE) AS last_seen_capture_date
FROM deduped

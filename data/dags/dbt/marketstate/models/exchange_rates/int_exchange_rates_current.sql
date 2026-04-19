WITH EXCHANGE_RATES AS (
    SELECT
        exchange_rate_sk,
        currency,
        date,
        rate
    FROM {{ ref('stg_exchange_rates_current') }}
),

CURRENCY_MAPPING AS (
    SELECT
        currency,
        currency_name
    FROM {{ ref('stg_currency_mapping') }}
),

FINAL_CTE AS (
    SELECT
        EXCHANGE_RATES.exchange_rate_sk,
        EXCHANGE_RATES.currency,
        EXCHANGE_RATES.date,
        CURRENCY_MAPPING.currency_name,
        EXCHANGE_RATES.rate
    FROM EXCHANGE_RATES
    LEFT JOIN CURRENCY_MAPPING
        ON EXCHANGE_RATES.currency = CURRENCY_MAPPING.currency
)

SELECT
    CAST(exchange_rate_sk AS STRING) AS exchange_rate_sk,
    CAST(currency AS STRING) AS currency,
    CAST(date AS DATE) AS date,
    CAST(currency_name AS STRING) AS currency_name,
    CAST(rate AS FLOAT64) AS rate
FROM FINAL_CTE

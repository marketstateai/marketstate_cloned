WITH EXCHANGE_RATES AS (
    SELECT
        UPPER(currency) AS currency,
        rate,
        date
    FROM {{ source('raw', 'exchange_rates') }}
),

DEDUPED_RATES AS (
    SELECT
        EXCHANGE_RATES.currency,
        EXCHANGE_RATES.rate,
        EXCHANGE_RATES.date
    FROM EXCHANGE_RATES
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY EXCHANGE_RATES.currency, EXCHANGE_RATES.date
        ORDER BY EXCHANGE_RATES.date DESC
    ) = 1
),

FINAL_CTE AS (
    SELECT
        TO_HEX(
            MD5(
                CONCAT(
                    CAST(DEDUPED_RATES.currency AS STRING),
                    '|',
                    CAST(DEDUPED_RATES.date AS STRING)
                )
            )
        ) AS exchange_rate_sk,
        DEDUPED_RATES.currency,
        DEDUPED_RATES.date,
        ROUND(CAST(DEDUPED_RATES.rate AS FLOAT64), 3) AS rate
    FROM DEDUPED_RATES
)

SELECT
    CAST(exchange_rate_sk AS STRING) AS exchange_rate_sk,   -- Surrogate key
    CAST(currency AS STRING) AS currency,                   -- Primary key
    CAST(date AS DATE) AS date,                             -- Primary key
    CAST(rate AS FLOAT64) AS rate
FROM FINAL_CTE

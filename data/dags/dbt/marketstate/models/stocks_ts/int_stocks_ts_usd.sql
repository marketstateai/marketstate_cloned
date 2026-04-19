WITH SER AS (
    -- This is already deduped
    SELECT
        yf_symbol,                                  -- Primary Key
        currency
    FROM {{ ref('int_symbol_exchange_rates') }}
),

ERC AS (
    -- This is already deduped
    SELECT
        currency,                                   -- Primary key
        date,                                       -- Primary key
        SAFE_CAST(rate AS FLOAT64) AS rate
    FROM {{ ref('stg_exchange_rates_current') }}
),

STS AS (
    -- This is already deduped
    SELECT
        stocks_ts_sk,                               -- Primary key
        exchange_symbol,
        yf_symbol,
        capture_date AS date,
        current_price,
        market_cap,
        volume
    FROM {{ ref('stg_stocks_ts_cleansed') }}
),

FINAL_CTE AS (
    SELECT
        stocks_ts_sk,
        sts.exchange_symbol,
        sts.yf_symbol,
        sts.date,
        SAFE_CAST(ROUND(SAFE_DIVIDE(sts.market_cap, NULLIF(rate, 0)), 0) AS INT64)
            AS market_cap_usd,
        ROUND(SAFE_DIVIDE(sts.current_price, NULLIF(rate, 0)), 2) AS current_price_usd,
        ROUND(SAFE_DIVIDE(sts.volume, NULLIF(rate, 0)), 0) AS volume_usd,
        sts.volume,
        ser.currency
    FROM STS
    LEFT JOIN SER
        ON sts.yf_symbol = ser.yf_symbol
    LEFT JOIN ERC
        ON erc.currency = ser.currency
        AND sts.date = erc.date
)

-- We need to know the stock symbol, the exchange (not all symbols are unique), and the date because it's timeseries
-- We considered breaking up exchange_symbol into exchange and the already existing symbol, but we can easily parse the exchange out of exchange_symbol, it's really this that is the primary key, no symbol
-- As it is, we must carry exchange_symbol and yf_symbol through together
SELECT
    CAST(stocks_ts_sk AS STRING) AS stocks_ts_sk,           -- Surrogate key
    CAST(exchange_symbol AS STRING) AS exchange_symbol,     -- Primary key
    CAST(yf_symbol AS STRING) AS yf_symbol,                 -- Primary key
    CAST(date AS DATE) AS date,                             -- Primary key
    CAST(market_cap_usd AS INT64) AS market_cap_usd,
    CAST(current_price_usd AS FLOAT64) AS current_price_usd,
    CAST(volume_usd AS FLOAT64) AS volume_usd,
    CAST(volume AS INT64) AS volume,
    CAST(currency AS STRING) AS currency
FROM FINAL_CTE
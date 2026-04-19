-- Builds a symbol-to-exchange/currency lookup for downstream exchange-rate mapping.
-- Primary key: symbol_exchange_rate_sk is a stable hash of yf_symbol to keep one row per symbol.
-- Excludes rows missing market_identifier_code and de-duplicates to one exchange per MIC and one MIC per symbol.
WITH EXCHANGES AS (
    SELECT DISTINCT
        market_identifier_code,
        exchange_name,
        currency
    FROM {{ source('raw', 'exchanges') }}
    WHERE 
        market_identifier_code IS NOT NULL
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY market_identifier_code
        ORDER BY exchange_name, currency
    ) = 1
),

STOCKS AS (
    SELECT DISTINCT
        yf_symbol,
        market_identifier_code
    FROM {{ source('raw', 'stocks') }}
    -- We have thousands of stock symbols / companies, but many only have these datapoints and no others, including market_identifier_code
    -- We also exclude records where yf_symbol is not available, since it's the primary key
    WHERE 
        market_identifier_code IS NOT NULL
        and yf_symbol IS NOT NULL
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY yf_symbol
        ORDER BY market_identifier_code
    ) = 1
),

FINAL_CTE AS (
    SELECT
        TO_HEX(
            MD5(
                CAST(STOCKS.yf_symbol AS STRING)
            )
        ) AS symbol_exchange_rate_sk,
        STOCKS.yf_symbol,
        EXCHANGES.exchange_name,
        EXCHANGES.currency
    FROM STOCKS
    LEFT JOIN EXCHANGES
        ON STOCKS.market_identifier_code = EXCHANGES.market_identifier_code
)

SELECT
    CAST(symbol_exchange_rate_sk AS STRING) AS symbol_exchange_rate_sk,
    CAST(yf_symbol AS STRING) AS yf_symbol, -- Primary 
    CAST(exchange_name AS STRING) AS exchange_name,
    CAST(currency AS STRING) AS currency
FROM FINAL_CTE

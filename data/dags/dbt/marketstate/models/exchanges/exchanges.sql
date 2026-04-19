WITH exchanges AS (
    SELECT
        exchange_name,
        country,
        market_identifier_code,
        currency,
        stock_count,
        url,
        capture_date,
        exchange_abbreviation,
        exchange_name_local_language,
        trade_accessibility
    FROM {{ source('raw', 'exchanges') }}
),

deduped_exchanges AS (
    SELECT
        exchange_name,
        country,
        market_identifier_code,
        currency,
        stock_count,
        url,
        capture_date,
        exchange_abbreviation,
        exchange_name_local_language,
        trade_accessibility
    FROM exchanges
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY market_identifier_code
        ORDER BY capture_date DESC, exchange_name
    ) = 1
)

SELECT
    exchange_name,
    country,
    market_identifier_code,
    currency,
    stock_count,
    url,
    capture_date,
    exchange_abbreviation,
    exchange_name_local_language,
    trade_accessibility
FROM deduped_exchanges

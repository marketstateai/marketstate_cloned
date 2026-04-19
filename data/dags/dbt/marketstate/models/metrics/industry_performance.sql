WITH SER AS (
    -- This is already deduped
    SELECT
        stocks_ts_sk,                                  -- Primary Key
        exchange_symbol,
        yf_symbol,
        date,
        market_cap_usd
    FROM `general-428410`.`int_prod`.`int_stocks_ts_usd`
)

SELECT *
FROM SER
WHERE date = CURRENT_DATE()
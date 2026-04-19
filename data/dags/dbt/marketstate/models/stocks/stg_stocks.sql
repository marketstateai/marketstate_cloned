WITH CLEANED_DATA AS (
    SELECT
        yf_symbol,
        capture_date,
        NULLIF(NULLIF(address1, 'nan'), '') AS address1,
        NULLIF(NULLIF(address2, 'nan'), '') AS address2,
        NULLIF(NULLIF(city, 'nan'), '') AS city,
        NULLIF(NULLIF(zip, 'nan'), '') AS zip,
        NULLIF(NULLIF(country, 'nan'), '') AS country,
        company_name,
        CAST(NULL AS STRING) AS primary_symbol,
        NULLIF(NULLIF(long_name, 'nan'), '') AS long_name,
        NULLIF(NULLIF(short_name, 'nan'), '') AS short_name,
        NULLIF(NULLIF(website, 'nan'), '') AS website,
        NULLIF(NULLIF(phone, 'nan'), '') AS phone,
        NULLIF(NULLIF(company_officers, 'nan'), '') AS company_officers,
        NULLIF(NULLIF(sector, 'nan'), '') AS sector,
        NULLIF(NULLIF(industry, 'nan'), '') AS industry,
        NULLIF(NULLIF(long_business_summary, 'nan'), '') AS long_business_summary,
        NULLIF(NULLIF(exchange, 'nan'), '') AS exchange,
        NULLIF(NULLIF(financial_currency, 'nan'), '') AS financial_currency,
        NULLIF(NULLIF(currency, 'nan'), '') AS currency,
        NULLIF(NULLIF(five_year_avg_dividend_yield, 'nan'), '') AS five_year_avg_dividend_yield,
        NULLIF(NULLIF(full_time_employees, 'nan'), '') AS full_time_employees,
        NULLIF(NULLIF(shares_outstanding, 'nan'), '') AS shares_outstanding,
        NULLIF(NULLIF(last_dividend_value, 'nan'), '') AS last_dividend_value,
        NULLIF(NULLIF(last_dividend_date, 'nan'), '') AS last_dividend_date,
        NULLIF(NULLIF(last_fiscal_year_end, 'nan'), '') AS last_fiscal_year_end,
        NULLIF(NULLIF(first_trade_date_epoch_utc, 'nan'), '') AS first_trade_date_epoch_utc,
        NULLIF(NULLIF(quote_type, 'nan'), '') AS quote_type,
        NULLIF(NULLIF(market_identifier_code, 'nan'), '') AS market_identifier_code
    FROM {{ source('raw', 'stocks') }}
    WHERE quote_type = 'EQUITY'
),

FORMATTED AS (
    SELECT
        yf_symbol,
        primary_symbol,
        capture_date,
        CONCAT(address1, ', ', address2, ', ', city, ', ', zip) AS address,
        country AS company_country,
        company_name,
        website,
        company_officers,
        sector,
        industry,
        long_business_summary,
        exchange,
        UPPER(financial_currency) AS company_currency,
        UPPER(currency) AS exchange_currency,
        five_year_avg_dividend_yield,
        CAST(CAST(full_time_employees AS FLOAT64) AS INT64) AS full_time_employees,
        CAST(CAST(shares_outstanding AS FLOAT64) AS INT64) AS shares_outstanding,
        CAST(last_dividend_value AS FLOAT64) AS last_dividend_value,
        DATE(
            TIMESTAMP_SECONDS(CAST(CAST(last_dividend_date AS FLOAT64) AS INT64))
        ) AS last_dividend_date,
        DATE(
            TIMESTAMP_SECONDS(CAST(CAST(last_fiscal_year_end AS FLOAT64) AS INT64))
        ) AS last_fiscal_year_end_date,
        DATE(
            TIMESTAMP_SECONDS(CAST(CAST(first_trade_date_epoch_utc AS FLOAT64) AS INT64))
        ) AS first_trade_date,
        market_identifier_code
    FROM CLEANED_DATA
),

FINAL_CTE AS (
    SELECT
        TO_HEX(
            MD5(
                CONCAT(
                    CAST(capture_date AS STRING),
                    '|',
                    CAST(yf_symbol AS STRING),
                    '|',
                    CAST(company_name AS STRING)
                )
            )
        ) AS stg_stocks_sk,
        primary_symbol,
        capture_date,
        yf_symbol,
        company_name,
        address,
        company_country,
        website,
        company_officers,
        sector,
        industry,
        long_business_summary,
        exchange,
        company_currency,
        exchange_currency,
        five_year_avg_dividend_yield,
        full_time_employees,
        shares_outstanding,
        last_dividend_value,
        last_dividend_date,
        last_fiscal_year_end_date,
        first_trade_date,
        market_identifier_code
    FROM FORMATTED
)

SELECT
    CAST(stg_stocks_sk AS STRING) AS stg_stocks_sk,
    CAST(capture_date AS DATE) AS capture_date,
    CAST(yf_symbol AS STRING) AS yf_symbol,
    CAST(primary_symbol AS STRING) AS primary_symbol,
    CAST(company_name AS STRING) AS company_name,
    CAST(address AS STRING) AS address,
    CAST(company_country AS STRING) AS company_country,
    CAST(website AS STRING) AS website,
    CAST(company_officers AS STRING) AS company_officers,
    CAST(sector AS STRING) AS sector,
    CAST(industry AS STRING) AS industry,
    CAST(long_business_summary AS STRING) AS long_business_summary,
    CAST(exchange AS STRING) AS exchange,
    CAST(company_currency AS STRING) AS company_currency,
    CAST(exchange_currency AS STRING) AS exchange_currency,
    CAST(five_year_avg_dividend_yield AS STRING) AS five_year_avg_dividend_yield,
    CAST(full_time_employees AS INT64) AS full_time_employees,
    CAST(shares_outstanding AS INT64) AS shares_outstanding,
    CAST(last_dividend_value AS FLOAT64) AS last_dividend_value,
    CAST(last_dividend_date AS DATE) AS last_dividend_date,
    CAST(last_fiscal_year_end_date AS DATE) AS last_fiscal_year_end_date,
    CAST(first_trade_date AS DATE) AS first_trade_date,
    CAST(market_identifier_code AS STRING) AS market_identifier_code
FROM FINAL_CTE

WITH BASE AS (
    SELECT
        -- Keep raw PK/partition columns to avoid breaking partition pruning; tests enforce null safety.
        SAFE_CAST(exchange_symbol AS STRING) AS exchange_symbol,
        SAFE_CAST(yf_symbol AS STRING) AS yf_symbol,
        SAFE_CAST(capture_date AS DATE) AS capture_date,
        COALESCE(
            SAFE_CAST(NULLIF(NULLIF(CAST(market_cap AS STRING), 'nan'), 'null') AS INT64),
            SAFE_CAST(SAFE_CAST(NULLIF(NULLIF(CAST(market_cap AS STRING), 'nan'), 'null') AS FLOAT64) AS INT64)
        ) AS market_cap,
        COALESCE(
            SAFE_CAST(NULLIF(NULLIF(CAST(current_price AS STRING), 'nan'), 'null') AS INT64),
            SAFE_CAST(SAFE_CAST(NULLIF(NULLIF(CAST(current_price AS STRING), 'nan'), 'null') AS FLOAT64) AS INT64)
        ) AS current_price,
        COALESCE(
            SAFE_CAST(NULLIF(NULLIF(CAST(volume AS STRING), 'nan'), 'null') AS INT64),
            SAFE_CAST(SAFE_CAST(NULLIF(NULLIF(CAST(volume AS STRING), 'nan'), 'null') AS FLOAT64) AS INT64)
        ) AS volume,
        -- SAFE_CAST(open AS STRING) AS open,
        -- SAFE_CAST(beta AS STRING) AS beta,
        -- SAFE_CAST(forward_pe AS STRING) AS forward_pe,
        -- SAFE_CAST(audit_risk AS STRING) AS audit_risk,
        -- SAFE_CAST(board_risk AS STRING) AS board_risk,
        -- SAFE_CAST(compensation_risk AS STRING) AS compensation_risk,
        -- SAFE_CAST(share_holder_rights_risk AS STRING) AS share_holder_rights_risk,
        -- SAFE_CAST(overall_risk AS STRING) AS overall_risk,
        -- SAFE_CAST(governance_epoch_date AS STRING) AS governance_epoch_date,
        -- SAFE_CAST(compensation_as_of_epoch_date AS STRING) AS compensation_as_of_epoch_date,
        -- SAFE_CAST(max_age AS STRING) AS max_age,
        -- SAFE_CAST(previous_close AS STRING) AS previous_close,
        -- SAFE_CAST(day_low AS STRING) AS day_low,
        -- SAFE_CAST(day_high AS STRING) AS day_high,
        -- SAFE_CAST(regular_market_previous_close AS STRING) AS regular_market_previous_close,
        -- SAFE_CAST(regular_market_open AS STRING) AS regular_market_open,
        -- SAFE_CAST(regular_market_day_low AS STRING) AS regular_market_day_low,
        -- SAFE_CAST(regular_market_day_high AS STRING) AS regular_market_day_high,
        -- SAFE_CAST(regular_market_volume AS STRING) AS regular_market_volume,
        -- SAFE_CAST(average_volume AS STRING) AS average_volume,
        -- SAFE_CAST(average_volume_10_days AS STRING) AS average_volume_10_days,
        -- SAFE_CAST(average_daily_volume_10_day AS STRING) AS average_daily_volume_10_day,
        -- SAFE_CAST(bid AS STRING) AS bid,
        -- SAFE_CAST(ask AS STRING) AS ask,
        -- SAFE_CAST(bid_size AS STRING) AS bid_size,
        -- SAFE_CAST(ask_size AS STRING) AS ask_size,
        -- SAFE_CAST(fifty_two_week_low AS STRING) AS fifty_two_week_low,
        -- SAFE_CAST(fifty_two_week_high AS STRING) AS fifty_two_week_high,
        -- SAFE_CAST(fifty_day_average AS STRING) AS fifty_day_average,
        -- SAFE_CAST(two_hundred_day_average AS STRING) AS two_hundred_day_average,
        -- SAFE_CAST(enterprise_value AS STRING) AS enterprise_value,
        -- SAFE_CAST(float_shares AS STRING) AS float_shares,
        -- SAFE_CAST(shares_outstanding AS STRING) AS shares_outstanding,
        -- SAFE_CAST(shares_short AS STRING) AS shares_short,
        -- SAFE_CAST(shares_short_prior_month AS STRING) AS shares_short_prior_month,
        -- SAFE_CAST(shares_short_previous_month_date AS STRING) AS shares_short_previous_month_date,
        -- SAFE_CAST(date_short_interest AS STRING) AS date_short_interest,
        -- SAFE_CAST(shares_percent_shares_out AS STRING) AS shares_percent_shares_out,
        -- SAFE_CAST(held_percent_insiders AS STRING) AS held_percent_insiders,
        -- SAFE_CAST(held_percent_institutions AS STRING) AS held_percent_institutions,
        -- SAFE_CAST(short_ratio AS STRING) AS short_ratio,
        -- SAFE_CAST(short_percent_of_float AS STRING) AS short_percent_of_float,
        -- SAFE_CAST(implied_shares_outstanding AS STRING) AS implied_shares_outstanding,
        -- SAFE_CAST(book_value AS STRING) AS book_value,
        -- SAFE_CAST(price_to_book AS STRING) AS price_to_book,
        -- SAFE_CAST(net_income_to_common AS STRING) AS net_income_to_common,
        -- SAFE_CAST(trailing_eps AS STRING) AS trailing_eps,
        -- SAFE_CAST(forward_eps AS STRING) AS forward_eps,
        -- SAFE_CAST(peg_ratio AS STRING) AS peg_ratio,
        -- SAFE_CAST(enterprise_to_ebitda AS STRING) AS enterprise_to_ebitda,
        -- SAFE_CAST(fifty_two_week_change AS STRING) AS fifty_two_week_change,
        -- SAFE_CAST(sand_p_52_week_change AS STRING) AS sand_p_52_week_change,
        -- SAFE_CAST(target_high_price AS STRING) AS target_high_price,
        -- SAFE_CAST(target_low_price AS STRING) AS target_low_price,
        -- SAFE_CAST(target_mean_price AS STRING) AS target_mean_price,
        -- SAFE_CAST(target_median_price AS STRING) AS target_median_price,
        -- SAFE_CAST(recommendation_mean AS STRING) AS recommendation_mean,
        -- SAFE_CAST(recommendation_key AS STRING) AS recommendation_key,
        -- SAFE_CAST(number_of_analyst_opinions AS STRING) AS number_of_analyst_opinions,
        -- SAFE_CAST(total_cash AS STRING) AS total_cash,
        -- SAFE_CAST(total_cash_per_share AS STRING) AS total_cash_per_share,
        -- SAFE_CAST(ebitda AS STRING) AS ebitda,
        -- SAFE_CAST(total_debt AS STRING) AS total_debt,
        -- SAFE_CAST(quick_ratio AS STRING) AS quick_ratio,
        -- SAFE_CAST(current_ratio AS STRING) AS current_ratio,
        -- SAFE_CAST(debt_to_equity AS STRING) AS debt_to_equity,
        -- SAFE_CAST(return_on_assets AS STRING) AS return_on_assets,
        -- SAFE_CAST(return_on_equity AS STRING) AS return_on_equity,
        -- SAFE_CAST(free_cashflow AS STRING) AS free_cashflow,
        -- SAFE_CAST(operating_cashflow AS STRING) AS operating_cashflow,
        -- SAFE_CAST(trailing_peg_ratio AS STRING) AS trailing_peg_ratio
    FROM {{ source('raw', 'yf_stocks_ts') }}
    WHERE exchange_symbol IS NOT NULL
      AND capture_date IS NOT NULL
)

SELECT
    TO_HEX(
        MD5(
            CONCAT(
                exchange_symbol,
                '|',
                capture_date
            )
        )
    ) AS stocks_ts_sk,              -- Surrogate key
    exchange_symbol,                -- Primary key
    yf_symbol,                      -- Intentionally excluded from primary key to reduce redundancy
    capture_date,                   -- Primary key
    market_cap,
    current_price,
    volume
FROM BASE
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY exchange_symbol, capture_date
    ORDER BY capture_date DESC
) = 1

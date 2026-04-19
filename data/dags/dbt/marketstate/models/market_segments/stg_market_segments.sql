WITH raw AS (
    SELECT
        market_segment,
        MAX(description) AS market_segment_description,

        -- Mean (avg) with safe cast
        ROUND(AVG(CASE
            WHEN SAFE_CAST(year AS INT64) = 2025
                THEN SAFE_CAST(market_size_billions_usd AS FLOAT64)
        END), 2) AS market_size_2025_busd_mean,
        ROUND(AVG(CASE
            WHEN SAFE_CAST(year AS INT64) = 2030
                THEN SAFE_CAST(market_size_billions_usd AS FLOAT64)
        END), 2) AS market_size_2030_busd_mean,

        -- Median
        ROUND(APPROX_QUANTILES(CASE
            WHEN SAFE_CAST(year AS INT64) = 2025
                THEN SAFE_CAST(market_size_billions_usd AS FLOAT64)
        END, 2)[OFFSET(1
        )], 2) AS market_size_2025_busd_median,
        ROUND(APPROX_QUANTILES(CASE
            WHEN SAFE_CAST(year AS INT64) = 2030
                THEN SAFE_CAST(market_size_billions_usd AS FLOAT64)
        END, 2)[OFFSET(1
        )], 2) AS market_size_2030_busd_median,

        -- Stddevs
        ROUND(STDDEV(CASE
            WHEN SAFE_CAST(year AS INT64) = 2025
                THEN SAFE_CAST(market_size_billions_usd AS FLOAT64)
        END), 2) AS market_size_2025_busd_std,
        ROUND(STDDEV(CASE
            WHEN SAFE_CAST(year AS INT64) = 2030
                THEN SAFE_CAST(market_size_billions_usd AS FLOAT64)
        END), 2) AS market_size_2030_busd_std,

        -- Counts
        COUNT(CASE
            WHEN SAFE_CAST(year AS INT64) = 2025
                THEN SAFE_CAST(market_size_billions_usd AS FLOAT64)
        END) AS market_size_2025_busd_estimates_count,
        COUNT(CASE
            WHEN SAFE_CAST(year AS INT64) = 2030
                THEN SAFE_CAST(market_size_billions_usd AS FLOAT64)
        END) AS market_size_2030_busd_estimates_count,

        -- Sources
        STRING_AGG(DISTINCT CASE
            WHEN SAFE_CAST(year AS INT64) IN (2025, 2030)
                THEN source_url
        END, ', ') AS sources
    FROM
        {{ source('raw', 'market_segments') }}
    GROUP BY
        market_segment
)

SELECT
    market_segment,
    market_segment_description,

    -- CAGR based on means
    market_size_2025_busd_mean,

    -- CAGR based on medians
    market_size_2030_busd_mean,

    -- Means
    market_size_2025_busd_median,
    market_size_2030_busd_median,

    -- Medians
    market_size_2025_busd_std,
    market_size_2030_busd_std,

    -- Stddevs
    market_size_2025_busd_estimates_count,
    market_size_2030_busd_estimates_count,

    -- Counts
    sources,
    ROUND(
        POW(market_size_2030_busd_mean / market_size_2025_busd_mean, 1 / 5) - 1,
        4
    )
    * 100 AS estimated_yearly_cagr_mean,

    -- Sources
    ROUND(
        POW(market_size_2030_busd_median / market_size_2025_busd_median, 1 / 5)
        - 1,
        4
    )
    * 100 AS estimated_yearly_cagr_median
FROM
    raw
WHERE
    market_size_2025_busd_mean IS NOT NULL
    AND market_size_2030_busd_mean IS NOT NULL

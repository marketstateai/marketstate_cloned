WITH RAW_GICS AS (
    SELECT
        SAFE_CAST(sector_code AS INT64) AS sector_code,
        CAST(sector AS STRING) AS sector,
        SAFE_CAST(industry_group_code AS INT64) AS industry_group_code,
        CAST(industry_group AS STRING) AS industry_group,
        SAFE_CAST(industry_code AS INT64) AS industry_code,
        CAST(industry AS STRING) AS industry,
        SAFE_CAST(sub_industry_code AS INT64) AS sub_industry_code,
        CAST(sub_industry AS STRING) AS sub_industry,
        CAST(description AS STRING) AS description
    FROM {{ source('raw', 'gics') }}
),

FINAL_CTE AS (
    SELECT
        TO_HEX(
            MD5(
                CONCAT(
                    CAST(sector_code AS STRING),
                    '|',
                    CAST(industry_group_code AS STRING),
                    '|',
                    CAST(industry_code AS STRING),
                    '|',
                    CAST(sub_industry_code AS STRING)
                )
            )
        ) AS gics_sk,
        sector_code,
        sector,
        industry_group_code,
        industry_group,
        industry_code,
        industry,
        sub_industry_code,
        sub_industry,
        description
    FROM RAW_GICS
)

SELECT
    CAST(gics_sk AS STRING) AS gics_sk,
    CAST(sector_code AS INT64) AS sector_code,
    CAST(sector AS STRING) AS sector,
    CAST(industry_group_code AS INT64) AS industry_group_code,
    CAST(industry_group AS STRING) AS industry_group,
    CAST(industry_code AS INT64) AS industry_code,
    CAST(industry AS STRING) AS industry,
    CAST(sub_industry_code AS INT64) AS sub_industry_code,
    CAST(sub_industry AS STRING) AS sub_industry,
    CAST(description AS STRING) AS description
FROM FINAL_CTE

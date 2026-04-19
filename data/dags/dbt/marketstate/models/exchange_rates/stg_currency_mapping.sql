WITH CURRENCY_MAPPING AS (
    SELECT
        UPPER(currency) AS currency,
        currency_name
    FROM {{ source('raw', 'currency_mapping') }}
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY UPPER(currency)
        ORDER BY currency_name
    ) = 1
),

FINAL_CTE AS (
    SELECT
        TO_HEX(
            MD5(
                CAST(currency AS STRING)
            )
        ) AS currency_mapping_sk,
        currency,
        currency_name
    FROM CURRENCY_MAPPING
)

SELECT
    CAST(currency_mapping_sk AS STRING) AS currency_mapping_sk,
    CAST(currency AS STRING) AS currency,
    CAST(currency_name AS STRING) AS currency_name
FROM FINAL_CTE

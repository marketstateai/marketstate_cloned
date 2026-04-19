{{ config(materialized="materialized_view") }}

WITH COMPANIES AS (
    SELECT 
        company_name, -- primary key
        website,
        phone,
        address1,
        address2,
        city,
        zip,
        country_of_origin,
        financial_currency,
        sector,
        industry,
        primary_market,
        market_share,
        wikipedia_url,
        business_summary,
        main_market_segments,
        geo_markets,
        products,
        business_summary_int
    FROM
        {{ source('raw', 'src_companies') }}
)

SELECT 
    company_name, -- primary key
    business_summary,
    website,
    concat(address1, ', ', address2) as address,
    city,
    zip,
    country_of_origin,
    financial_currency,
    sector,
    industry,
    wikipedia_url
FROM 
    COMPANIES

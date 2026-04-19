with symbol_exchange_rates as (
    select
        yf_symbol,
        exchange_name,
        currency
    from {{ ref('int_symbol_exchange_rates') }}
),

base as (
    select
        date(Date) as date, --pk
        yfSymbol as yf_symbol, --pk
        periodType as period, --pk
        companyName as company_name,
        `Total Revenue` as total_revenue_usd,
        `Cost Of Revenue` as cost_of_revenue_usd,
        `Gross Profit` as gross_profit_usd,
        round(SAFE_DIVIDE(`Gross Profit`, `Total Revenue`), 3) as profit_margin,
        alphaBucket as alpha_bucket,
        processingDate as processing_date
    from 
        {{ source('raw', 'income_statements') }}
),

ttm_rows as (
    select
        date,
        yf_symbol,
        'ttm' as period,
        company_name,
        sum(total_revenue_usd) over w as total_revenue_usd,
        sum(cost_of_revenue_usd) over w as cost_of_revenue_usd,
        sum(gross_profit_usd) over w as gross_profit_usd,
        round(
            SAFE_DIVIDE(
                sum(gross_profit_usd) over w,
                sum(total_revenue_usd) over w
            ),
            3
        ) as profit_margin,
        alpha_bucket
    from base
    where period = 'quarterly'
    qualify
        count(*) over w = 4
        and row_number() over (partition by yf_symbol order by date desc) = 1
    window w as (
        partition by yf_symbol
        order by date
        rows between 3 preceding and current row
    )
),

final_cte as (
    select
        to_hex(
            md5(
                concat(
                    cast(base.date as string),
                    '|',
                    cast(base.yf_symbol as string),
                    '|',
                    cast(period as string)
                )
            )
        ) as income_statement_sk,
        cast(base.date as date) as date,
        cast(base.yf_symbol as string) as yf_symbol,
        cast(period as string) as period,
        cast(company_name as string) as company_name,
        cast(total_revenue_usd as float64) as total_revenue_usd,
        cast(cost_of_revenue_usd as float64) as cost_of_revenue_usd,
        cast(gross_profit_usd as float64) as gross_profit_usd,
        cast(profit_margin as float64) as profit_margin,
        cast(alpha_bucket as string) as alpha_bucket,
        cast(symbol_exchange_rates.exchange_name as string) as exchange_name,
        cast(symbol_exchange_rates.currency as string) as currency
    from base
    left join symbol_exchange_rates
        on base.yf_symbol = symbol_exchange_rates.yf_symbol

    union all

    select
        to_hex(
            md5(
                concat(
                    cast(ttm_rows.date as string),
                    '|',
                    cast(ttm_rows.yf_symbol as string),
                    '|',
                    cast(period as string)
                )
            )
        ) as income_statement_sk,
        cast(ttm_rows.date as date) as date,
        cast(ttm_rows.yf_symbol as string) as yf_symbol,
        cast(period as string) as period,
        cast(company_name as string) as company_name,
        cast(total_revenue_usd as float64) as total_revenue_usd,
        cast(cost_of_revenue_usd as float64) as cost_of_revenue_usd,
        cast(gross_profit_usd as float64) as gross_profit_usd,
        cast(profit_margin as float64) as profit_margin,
        cast(alpha_bucket as string) as alpha_bucket,
        cast(symbol_exchange_rates.exchange_name as string) as exchange_name,
        cast(symbol_exchange_rates.currency as string) as currency
    from ttm_rows
    left join symbol_exchange_rates
        on ttm_rows.yf_symbol = symbol_exchange_rates.yf_symbol
)

select
    income_statement_sk,
    date,
    yf_symbol,
    period,
    company_name,
    total_revenue_usd,
    cost_of_revenue_usd,
    gross_profit_usd,
    profit_margin,
    alpha_bucket,
    exchange_name,
    currency
from final_cte

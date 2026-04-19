with income_statement_records as (
    select
        *
    from 
        {{ ref('income_statements_all_periods') }}
    where 
        period in ('ttm', 'annual')
    qualify
        row_number() over (
            partition by income_statement_sk
            order by income_statement_sk
        ) = 1
),

metrics_base as (
    select
        yf_symbol,
        date,
        period,
        profit_margin
    from income_statement_records
    where period in ('ttm', 'annual')
      and profit_margin is not null
),

annual_ranked as (
    select
        yf_symbol,
        date,
        period,
        profit_margin,
        row_number() over (partition by yf_symbol order by date desc) as rn_annual
    from metrics_base
    where period = 'annual'
),

annual_filtered as (
    select
        yf_symbol,
        date,
        period,
        profit_margin
    from annual_ranked
    where rn_annual <= 4
),

ttm_latest as (
    select
        yf_symbol,
        date,
        period,
        profit_margin
    from (
        select
            yf_symbol,
            date,
            period,
            profit_margin,
            row_number() over (partition by yf_symbol order by date desc) as rn_ttm
        from metrics_base
        where period = 'ttm'
    )
    where rn_ttm = 1
),

combined as (
    select * from annual_filtered
    union all
    select * from ttm_latest
),

ordered as (
    select
        yf_symbol,
        date,
        profit_margin,
        row_number() over (partition by yf_symbol order by date) - 1 as t
    from combined
),

weighted as (
    select
        *,
        1 as w
    from ordered
),

stats as (
    select
        *,
        sum(w * t) over (partition by yf_symbol) / sum(w) over (partition by yf_symbol) as mean_t,
        sum(w * profit_margin) over (partition by yf_symbol) / sum(w) over (partition by yf_symbol) as mean_y
    from weighted
),

metrics as (
    select
        yf_symbol,
        round(avg(profit_margin), 3) as avg_profit_margin,
        round(stddev_samp(profit_margin), 3) as std_profit_margin,
        sum(w * (t - mean_t) * (profit_margin - mean_y))
            / nullif(sum(w * pow(t - mean_t, 2)), 0) as profit_margin_trend
    from stats
    group by
        yf_symbol
),

timeseries as (
    select
        yf_symbol,
        market_cap_usd,
        current_price_usd,
        volume,
        volume_usd,
        date
    from 
        {{ ref('int_stocks_ts_usd') }}
)

select
    income_statement_records.date as income_statement_date,
    income_statement_records.company_name,
    income_statement_records.yf_symbol,
    income_statement_records.period,
    income_statement_records.total_revenue_usd,
    income_statement_records.cost_of_revenue_usd,
    income_statement_records.gross_profit_usd,
    income_statement_records.profit_margin,
    income_statement_records.alpha_bucket,
    income_statement_records.exchange_name,
    income_statement_records.currency,
    metrics.avg_profit_margin,
    metrics.std_profit_margin,
    metrics.profit_margin_trend,

    timeseries.market_cap_usd,
    timeseries.current_price_usd,
    timeseries.volume,
    timeseries.volume_usd,
    timeseries.date as stock_date
from income_statement_records
left join metrics
    on income_statement_records.yf_symbol = metrics.yf_symbol
left join timeseries
    on income_statement_records.yf_symbol = timeseries.yf_symbol

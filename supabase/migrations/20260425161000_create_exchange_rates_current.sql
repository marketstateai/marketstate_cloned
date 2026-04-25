create table if not exists public.exchange_rates_current (
  exchange_rate_sk text not null,
  currency text not null,
  date date not null,
  currency_name text,
  rate numeric(20, 3) not null,
  replicated_at timestamptz not null default now(),
  primary key (exchange_rate_sk),
  unique (currency, date)
);

create index if not exists exchange_rates_current_date_idx
  on public.exchange_rates_current (date desc);

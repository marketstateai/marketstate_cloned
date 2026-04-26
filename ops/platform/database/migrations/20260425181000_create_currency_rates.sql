create table if not exists public.currency_rates (
  currency text not null,
  date date not null,
  rate numeric(30, 10) not null,
  created_at timestamptz not null default now(),
  primary key (currency, date)
);

create index if not exists currency_rates_date_idx
  on public.currency_rates (date desc);

alter table public.currency_rates enable row level security;

drop policy if exists currency_rates_select_authenticated on public.currency_rates;
create policy currency_rates_select_authenticated
  on public.currency_rates
  for select
  to authenticated
  using (true);

drop policy if exists currency_rates_insert_authenticated on public.currency_rates;
create policy currency_rates_insert_authenticated
  on public.currency_rates
  for insert
  to authenticated
  with check (true);

drop policy if exists currency_rates_update_authenticated on public.currency_rates;
create policy currency_rates_update_authenticated
  on public.currency_rates
  for update
  to authenticated
  using (true)
  with check (true);

drop policy if exists currency_rates_delete_authenticated on public.currency_rates;
create policy currency_rates_delete_authenticated
  on public.currency_rates
  for delete
  to authenticated
  using (true);

do $$
begin
  if exists (
    select 1
    from information_schema.tables
    where table_schema = 'public'
      and table_name = 'exchange_rates_current'
  ) then
    if exists (
      select 1
      from information_schema.columns
      where table_schema = 'public'
        and table_name = 'exchange_rates_current'
        and column_name = 'date'
    ) then
      insert into public.currency_rates (currency, date, rate)
      select
        currency,
        date,
        rate::numeric(30, 10)
      from public.exchange_rates_current
      on conflict (currency, date) do update
      set rate = excluded.rate;
    elsif exists (
      select 1
      from information_schema.columns
      where table_schema = 'public'
        and table_name = 'exchange_rates_current'
        and column_name = 'rate_date'
    ) then
      insert into public.currency_rates (currency, date, rate)
      select
        currency,
        rate_date,
        rate::numeric(30, 10)
      from public.exchange_rates_current
      on conflict (currency, date) do update
      set rate = excluded.rate;
    end if;
  end if;
end $$;

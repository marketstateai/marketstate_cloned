begin;

create extension if not exists pgcrypto;

create table if not exists public.ms_profiles (
  id uuid primary key default gen_random_uuid(),
  auth_user_id uuid unique references auth.users (id) on delete set null,
  email text not null unique,
  display_name text not null,
  risk_profile text not null default 'balanced',
  created_at timestamptz not null default now()
);

create table if not exists public.ms_portfolio_snapshots (
  id bigserial primary key,
  user_id uuid not null references public.ms_profiles (id) on delete cascade,
  as_of_date date not null default current_date,
  total_value numeric(14, 2) not null,
  cash_balance numeric(14, 2) not null,
  day_pnl numeric(14, 2) not null,
  total_return_pct numeric(7, 3) not null,
  created_at timestamptz not null default now(),
  unique (user_id, as_of_date)
);

create table if not exists public.ms_holdings (
  id bigserial primary key,
  user_id uuid not null references public.ms_profiles (id) on delete cascade,
  symbol text not null,
  company_name text not null,
  quantity numeric(18, 4) not null check (quantity >= 0),
  price numeric(14, 2) not null check (price >= 0),
  change_pct numeric(7, 3) not null,
  created_at timestamptz not null default now(),
  unique (user_id, symbol)
);

create table if not exists public.ms_watchlist (
  id bigserial primary key,
  user_id uuid not null references public.ms_profiles (id) on delete cascade,
  symbol text not null,
  price numeric(14, 2) not null check (price >= 0),
  change_pct numeric(7, 3) not null,
  created_at timestamptz not null default now(),
  unique (user_id, symbol)
);

create table if not exists public.ms_activity_log (
  id bigserial primary key,
  user_id uuid not null references public.ms_profiles (id) on delete cascade,
  activity_text text not null,
  activity_time timestamptz not null,
  created_at timestamptz not null default now(),
  unique (user_id, activity_text, activity_time)
);

create index if not exists idx_ms_snapshots_user_date
  on public.ms_portfolio_snapshots (user_id, as_of_date desc);
create index if not exists idx_ms_holdings_user
  on public.ms_holdings (user_id);
create index if not exists idx_ms_watchlist_user
  on public.ms_watchlist (user_id);
create index if not exists idx_ms_activity_user_time
  on public.ms_activity_log (user_id, activity_time desc);

alter table public.ms_profiles enable row level security;
alter table public.ms_portfolio_snapshots enable row level security;
alter table public.ms_holdings enable row level security;
alter table public.ms_watchlist enable row level security;
alter table public.ms_activity_log enable row level security;

drop policy if exists "ms_profiles_public_read_demo" on public.ms_profiles;
create policy "ms_profiles_public_read_demo"
on public.ms_profiles
for select
using (true);

drop policy if exists "ms_portfolio_public_read_demo" on public.ms_portfolio_snapshots;
create policy "ms_portfolio_public_read_demo"
on public.ms_portfolio_snapshots
for select
using (true);

drop policy if exists "ms_holdings_public_read_demo" on public.ms_holdings;
create policy "ms_holdings_public_read_demo"
on public.ms_holdings
for select
using (true);

drop policy if exists "ms_watchlist_public_read_demo" on public.ms_watchlist;
create policy "ms_watchlist_public_read_demo"
on public.ms_watchlist
for select
using (true);

drop policy if exists "ms_activity_public_read_demo" on public.ms_activity_log;
create policy "ms_activity_public_read_demo"
on public.ms_activity_log
for select
using (true);

grant select on public.ms_profiles to anon, authenticated;
grant select on public.ms_portfolio_snapshots to anon, authenticated;
grant select on public.ms_holdings to anon, authenticated;
grant select on public.ms_watchlist to anon, authenticated;
grant select on public.ms_activity_log to anon, authenticated;

insert into public.ms_profiles (
  id,
  email,
  display_name,
  risk_profile
) values (
  '11111111-1111-1111-1111-111111111111',
  'demo@marketstate.ai',
  'Demo Investor',
  'balanced'
)
on conflict (email) do update
set
  display_name = excluded.display_name,
  risk_profile = excluded.risk_profile;

insert into public.ms_portfolio_snapshots (
  user_id,
  as_of_date,
  total_value,
  cash_balance,
  day_pnl,
  total_return_pct
) values (
  '11111111-1111-1111-1111-111111111111',
  current_date,
  128430.74,
  14220.12,
  758.45,
  1.84
)
on conflict (user_id, as_of_date) do update
set
  total_value = excluded.total_value,
  cash_balance = excluded.cash_balance,
  day_pnl = excluded.day_pnl,
  total_return_pct = excluded.total_return_pct;

insert into public.ms_holdings (
  user_id,
  symbol,
  company_name,
  quantity,
  price,
  change_pct
) values
  ('11111111-1111-1111-1111-111111111111', 'AAPL', 'Apple Inc.', 42, 196.21, 0.92),
  ('11111111-1111-1111-1111-111111111111', 'MSFT', 'Microsoft', 28, 431.05, 1.22),
  ('11111111-1111-1111-1111-111111111111', 'NVDA', 'NVIDIA', 19, 967.88, 2.14),
  ('11111111-1111-1111-1111-111111111111', 'TSLA', 'Tesla', 16, 183.61, -0.74)
on conflict (user_id, symbol) do update
set
  company_name = excluded.company_name,
  quantity = excluded.quantity,
  price = excluded.price,
  change_pct = excluded.change_pct;

insert into public.ms_watchlist (
  user_id,
  symbol,
  price,
  change_pct
) values
  ('11111111-1111-1111-1111-111111111111', 'AMZN', 184.20, 0.55),
  ('11111111-1111-1111-1111-111111111111', 'META', 503.76, -1.11),
  ('11111111-1111-1111-1111-111111111111', 'GOOGL', 176.82, 0.27)
on conflict (user_id, symbol) do update
set
  price = excluded.price,
  change_pct = excluded.change_pct;

insert into public.ms_activity_log (
  user_id,
  activity_text,
  activity_time
) values
  ('11111111-1111-1111-1111-111111111111', 'Bought 5 NVDA @ $955.10', '2026-04-25 09:42:00+00'),
  ('11111111-1111-1111-1111-111111111111', 'Sold 3 TSLA @ $188.45', '2026-04-25 08:17:00+00'),
  ('11111111-1111-1111-1111-111111111111', 'Dividend posted: MSFT', '2026-04-24 16:10:00+00')
on conflict (user_id, activity_text, activity_time) do nothing;

create or replace function public.ms_get_portal_payload(p_email text default 'demo@marketstate.ai')
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_payload jsonb;
begin
  select id
  into v_user_id
  from public.ms_profiles
  where email = p_email;

  if v_user_id is null then
    raise exception 'No profile found for %', p_email;
  end if;

  select jsonb_build_object(
    'profile', (
      select row_to_json(p)
      from (
        select id, email, display_name, risk_profile, created_at
        from public.ms_profiles
        where id = v_user_id
      ) p
    ),
    'snapshot', (
      select row_to_json(s)
      from (
        select as_of_date, total_value, cash_balance, day_pnl, total_return_pct
        from public.ms_portfolio_snapshots
        where user_id = v_user_id
        order by as_of_date desc
        limit 1
      ) s
    ),
    'holdings', (
      select coalesce(jsonb_agg(h order by h.symbol), '[]'::jsonb)
      from (
        select symbol, company_name, quantity, price, change_pct
        from public.ms_holdings
        where user_id = v_user_id
      ) h
    ),
    'watchlist', (
      select coalesce(jsonb_agg(w order by w.symbol), '[]'::jsonb)
      from (
        select symbol, price, change_pct
        from public.ms_watchlist
        where user_id = v_user_id
      ) w
    ),
    'activity', (
      select coalesce(jsonb_agg(a order by a.activity_time desc), '[]'::jsonb)
      from (
        select activity_text, activity_time
        from public.ms_activity_log
        where user_id = v_user_id
        order by activity_time desc
        limit 10
      ) a
    )
  )
  into v_payload;

  return v_payload;
end;
$$;

grant execute on function public.ms_get_portal_payload(text) to anon, authenticated;

commit;

do $$
begin
  if to_regclass('public.currency_rates') is not null then
    drop policy if exists "currency_rates_delete_authenticated" on public.currency_rates;
    drop policy if exists "currency_rates_insert_authenticated" on public.currency_rates;
    drop policy if exists "currency_rates_select_authenticated" on public.currency_rates;
    drop policy if exists "currency_rates_update_authenticated" on public.currency_rates;

    revoke delete on table public.currency_rates from anon;
    revoke insert on table public.currency_rates from anon;
    revoke references on table public.currency_rates from anon;
    revoke select on table public.currency_rates from anon;
    revoke trigger on table public.currency_rates from anon;
    revoke truncate on table public.currency_rates from anon;
    revoke update on table public.currency_rates from anon;

    revoke delete on table public.currency_rates from authenticated;
    revoke insert on table public.currency_rates from authenticated;
    revoke references on table public.currency_rates from authenticated;
    revoke select on table public.currency_rates from authenticated;
    revoke trigger on table public.currency_rates from authenticated;
    revoke truncate on table public.currency_rates from authenticated;
    revoke update on table public.currency_rates from authenticated;

    revoke delete on table public.currency_rates from service_role;
    revoke insert on table public.currency_rates from service_role;
    revoke references on table public.currency_rates from service_role;
    revoke select on table public.currency_rates from service_role;
    revoke trigger on table public.currency_rates from service_role;
    revoke truncate on table public.currency_rates from service_role;
    revoke update on table public.currency_rates from service_role;

    alter table public.currency_rates drop constraint if exists currency_rates_pkey;

    drop index if exists public.currency_rates_date_idx;
    drop index if exists public.currency_rates_pkey;

    drop table public.currency_rates;
  end if;
end $$;
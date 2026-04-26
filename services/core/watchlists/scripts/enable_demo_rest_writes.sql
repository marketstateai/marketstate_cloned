begin;

-- Demo-only write access for quick REST method testing.
-- Do NOT use these open policies in production.

alter table public.ms_watchlist enable row level security;

drop policy if exists "ms_watchlist_public_insert_demo" on public.ms_watchlist;
create policy "ms_watchlist_public_insert_demo"
on public.ms_watchlist
for insert
to anon, authenticated
with check (true);

drop policy if exists "ms_watchlist_public_update_demo" on public.ms_watchlist;
create policy "ms_watchlist_public_update_demo"
on public.ms_watchlist
for update
to anon, authenticated
using (true)
with check (true);

grant insert, update on public.ms_watchlist to anon, authenticated;
grant usage, select on sequence public.ms_watchlist_id_seq to anon, authenticated;

commit;

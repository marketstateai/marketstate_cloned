create table if not exists public.orama_user_backups (
  user_id uuid primary key references auth.users (id) on delete cascade,
  state jsonb not null default '{}'::jsonb,
  state_version integer not null default 1,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

comment on table public.orama_user_backups is
  'Canonical per-user Orama backup blob used to hydrate and restore the full planning workspace.';

comment on column public.orama_user_backups.state is
  'Full Orama application state as JSON.';

comment on column public.orama_user_backups.state_version is
  'Schema version for the stored Orama state blob.';

create or replace function public.set_orama_user_backups_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

drop trigger if exists set_orama_user_backups_updated_at on public.orama_user_backups;

create trigger set_orama_user_backups_updated_at
before update on public.orama_user_backups
for each row
execute function public.set_orama_user_backups_updated_at();

alter table public.orama_user_backups enable row level security;

drop policy if exists orama_user_backups_select_own on public.orama_user_backups;
create policy orama_user_backups_select_own
  on public.orama_user_backups
  for select
  to authenticated
  using (auth.uid() = user_id);

drop policy if exists orama_user_backups_insert_own on public.orama_user_backups;
create policy orama_user_backups_insert_own
  on public.orama_user_backups
  for insert
  to authenticated
  with check (auth.uid() = user_id);

drop policy if exists orama_user_backups_update_own on public.orama_user_backups;
create policy orama_user_backups_update_own
  on public.orama_user_backups
  for update
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists orama_user_backups_delete_own on public.orama_user_backups;
create policy orama_user_backups_delete_own
  on public.orama_user_backups
  for delete
  to authenticated
  using (auth.uid() = user_id);

create index if not exists orama_user_backups_updated_at_idx
  on public.orama_user_backups (updated_at desc);

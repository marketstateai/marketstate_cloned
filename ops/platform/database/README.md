# Database Platform

Canonical home for shared database lifecycle assets:

- `migrations/`: ordered schema migrations
- `seed.sql`: base seed data used by local reset/bootstrap flows

These files are provider-neutral at the architecture level, even if a specific
adapter such as Supabase consumes them.

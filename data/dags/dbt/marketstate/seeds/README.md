# Seeds

This directory contains dbt seed data used by the `marketstate` project.

## currency_mapping

- File: `currency_mapping.csv`
- Purpose: Map lowercase currency codes to canonical currency names.
- Used by: `exchange_rates` model joins to attach readable currency names.

## How to load seeds

From the repo root:

```bash
dbt seed --project-dir dags/dbt/marketstate --select currency_mapping
```

To load all seeds:

```bash
dbt seed --project-dir dags/dbt/marketstate
```

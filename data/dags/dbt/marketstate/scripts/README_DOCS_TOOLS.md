# Docs tools

Utilities for updating docs previews and profile summaries.

## Files
- `update_docs_assets.rb`: Updates preview rows + profile summary in one run.
- `patch_dbt_docs_html.py`: Applies CSS/HTML patch to `target/index.html`.
- `docs_preview_config.json`: Global CSS for docs tables.

## Usage

Run from the repo root.

Optional flags:
- `--debug`: Passes `--debug` to dbt for both preview and profile operations.

### Model (view) example

Use this for models like `stg_companies` (views):

```
  ./dags/dbt/marketstate/scripts/update_docs_assets.rb \
  --docs-file dags/dbt/marketstate/models/companies/docs/src_companies.md \
  --project-dir dags/dbt/marketstate \
  --relation src_companies \
  --schema src_prod \
  --partition-filter null \
  --profile-relation src_companies \
  --profile-schema src_prod \
  --schema-file dags/dbt/marketstate/models/companies/config_companies.yml \
  --source raw \
  --source-table src_companies
```

### Source (table) example

Use this for sources like `raw.src_companies` (base tables):

```
./dags/dbt/marketstate/scripts/update_docs_assets.rb \
  --docs-file dags/dbt/marketstate/models/companies/docs/stg_companies.md \
  --project-dir dags/dbt/marketstate \
  --relation stg_companies \
  --schema stg_prod \
  --partition-filter null \
  --profile-relation stg_companies \
  --profile-schema stg_prod \
  --schema-file dags/dbt/marketstate/models/companies/config_companies.yml
```

### Source (table) example with partition filter

Use this for sources partitioned by date (last 10 days):

```
./dags/dbt/marketstate/scripts/update_docs_assets.rb \
  --docs-file dags/dbt/marketstate/models/stocks_ts/docs/yf_stocks_ts.md \
  --project-dir dags/dbt/marketstate \
  --relation yf_stocks_ts \
  --schema src_prod \
  --partition-filter "capture_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 10 DAY)" \
  --profile-relation yf_stocks_ts \
  --profile-schema src_prod \
  --schema-file dags/dbt/marketstate/models/stocks_ts/config_stocks_ts.yml \
  --source raw \
  --source-table yf_stocks_ts
```

Then rebuild docs and apply CSS:

```
dbt docs generate --project-dir dags/dbt/marketstate
colibri generate
python3 dags/dbt/marketstate/scripts/patch_dbt_docs_html.py
```

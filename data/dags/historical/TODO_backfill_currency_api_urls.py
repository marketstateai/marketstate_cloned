"""
One-off backfill script to load USD FX rates from the historical JSDelivr
currency API into BigQuery.

What it does:
- Iterates daily dates from a start date to today (or an explicit end date).
- Builds the dated API URL for each day, e.g.:
  https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@2024.3.2/v1/currencies/usd.json
- Fetches the JSON and extracts `usd` (or the configured base currency) rates.
- If a dated URL 404s, it retries using the previous day's URL and still tags
  the data with the target date.
- Appends all rows into a single DataFrame and writes to BigQuery in one load job.

Required environment:
- `GOOGLE_APPLICATION_CREDENTIALS` must point to a service account JSON
  with BigQuery write permissions for the target table.
- Network access to jsdelivr.net.

Example usage:
  python marketstate/scripts/backfill_currency_api_urls.py \
    --table-id dev.exchange_rates \
    --project general-428410 \
    --base-currency usd \
    --start-date 2024-03-02 \
    --end-date 2024-12-31 \
    --write-disposition WRITE_APPEND
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
import time
from google.cloud import bigquery
from marketstate.marketstate_data.src.bigquery_utils import load_dataframe_to_bigquery


URL_TEMPLATE = (
    "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{version}/v1/currencies/{base}.json"
)


def _parse_date(value: str) -> date:
    try:
        parts = value.split("-")
        if len(parts) != 3:
            raise ValueError
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception as exc:
        raise argparse.ArgumentTypeError(
            "Dates must be in YYYY-MM-DD format"
        ) from exc


def _build_dates(start_date: date, end_date: date) -> list[date]:
    dates: list[date] = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def _url_for_date(target_date: date, base_currency: str) -> str:
    version = f"{target_date.year}.{target_date.month}.{target_date.day}"
    return URL_TEMPLATE.format(version=version, base=base_currency)


def _fetch_rates(
    target_date: date, base_currency: str
) -> tuple[date, pd.DataFrame, str]:
    url = _url_for_date(target_date, base_currency)
    response = requests.get(url, timeout=10)
    if response.status_code == 404:
        fallback_date = target_date - timedelta(days=1)
        fallback_url = _url_for_date(fallback_date, base_currency)
        response = requests.get(fallback_url, timeout=10)
        if response.status_code == 404:
            return target_date, pd.DataFrame(), fallback_url
    response.raise_for_status()
    data = response.json()
    rates = data.get(base_currency, {})
    rows = [
        {"currency": key, "rate": value, "date": target_date}
        for key, value in rates.items()
    ]
    return target_date, pd.DataFrame(rows), url


def _normalize_table_id(table_id: str, project: str | None) -> str:
    dot_count = table_id.count(".")
    if dot_count == 2:
        return table_id
    if dot_count == 1:
        if not project:
            raise ValueError("Project is required when table_id is dataset.table")
        return f"{project}.{table_id}"
    raise ValueError("table_id must be dataset.table or project.dataset.table")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--table-id",
        required=True,
        help="Target table ID: dataset.table or project.dataset.table",
    )
    parser.add_argument(
        "--start-date",
        type=_parse_date,
        default=_parse_date("2024-03-02"),
        help="Start date (YYYY-MM-DD). Default: 2024-03-02",
    )
    parser.add_argument(
        "--end-date",
        type=_parse_date,
        default=date.today(),
        help="End date (YYYY-MM-DD). Default: today (UTC)",
    )
    parser.add_argument(
        "--project",
        default=os.environ.get("GCP_PROJECT_ID"),
        help="GCP project ID (used if table-id omits project).",
    )
    parser.add_argument(
        "--base-currency",
        default="usd",
        help="Base currency code used in the API URL. Default: usd",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=6,
        help="Number of concurrent requests. Default: 6",
    )
    parser.add_argument(
        "--write-disposition",
        default="WRITE_TRUNCATE",
        choices=["WRITE_TRUNCATE", "WRITE_APPEND"],
        help="BigQuery write disposition. Default: WRITE_TRUNCATE",
    )
    args = parser.parse_args()

    if args.end_date < args.start_date:
        raise ValueError("end-date must be >= start-date")

    table_id = _normalize_table_id(args.table_id, args.project)
    base_currency = args.base_currency.lower()
    dates = _build_dates(args.start_date, args.end_date)

    ddl = f"""
    CREATE TABLE IF NOT EXISTS `{table_id}` (
      currency STRING,
      date DATE,
      rate FLOAT64
    )
    PARTITION BY date
    """
    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("currency", "STRING"),
            bigquery.SchemaField("rate", "FLOAT"),
        ],
        write_disposition=args.write_disposition,
    )
    all_frames: list[pd.DataFrame] = []
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_map = {
            executor.submit(_fetch_rates, target_date, base_currency): target_date
            for target_date in dates
        }
        for future in as_completed(future_map):
            target_date = future_map[future]
            try:
                date_value, df, url = future.result()
            except requests.RequestException as exc:
                url = _url_for_date(target_date, base_currency)
                print(f"Skipping {target_date} ({url}): {exc}")
                time.sleep(0.25)
                continue
            if df.empty:
                print(f"Skipping {target_date} (no data): {url}")
                continue
            print(f"Loaded {len(df)} rows for {date_value} from {url}")
            all_frames.append(df)

    if not all_frames:
        print("No rows fetched; nothing to write.")
        return

    combined = pd.concat(all_frames, ignore_index=True)
    load_dataframe_to_bigquery(
        combined,
        table_id=table_id,
        project=args.project,
        write_disposition=args.write_disposition,
        ddl=ddl,
        schema=job_config.schema,
        empty_message="No rows fetched; nothing to write.",
    )


if __name__ == "__main__":
    main()

"""
## MarketState YF Stocks DAG

Daily DAG that pulls unprocessed Yahoo Finance symbols from BigQuery, fetches
ticker details via yfinance, normalizes them to the yf_stocks_ts schema,
and appends results in batches.

Key behavior:
- Queries stocks for distinct market_identifier_code/yf_symbol
- Skips market_identifier_code already processed today in yf_stocks_ts
- Throttles yfinance calls (0.5 seconds)
- Ensures expected columns exist and are strings (except capture_date)
- Appends results to {project_id}.src_{env}.yf_stocks_ts

Required Airflow Variables:
- BQ_SECRET_RESOURCE: Secret Manager resource for BigQuery SA
"""

from __future__ import annotations

import os

os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
os.environ.setdefault("GRPC_TRACE", "")
os.environ.setdefault("ABSL_LOGGING_MIN_SEVERITY", "2")
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("GLOG_logtostderr", "0")
os.environ.setdefault("GLOG_stderrthreshold", "2")

import gc
import logging
import re
import time
import urllib.parse
from datetime import datetime
from functools import lru_cache
from typing import Any

import pandas as pd
import pendulum
import yfinance as yf
from airflow.sdk import dag, get_current_context, task

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BQ_SECRET_RESOURCE_VAR = "BQ_SECRET_RESOURCE"
DEFAULT_BQ_SECRET_RESOURCE = "projects/318171260121/secrets/bigquery"
ORCHESTRATOR_LOGS_TABLE_VAR = "ORCHESTRATOR_LOGS_TABLE_ID"
ORCHESTRATOR_LOGS_IGNORE_ERRORS_VAR = "ORCHESTRATOR_LOGS_IGNORE_ERRORS"

target = f"src_{os.getenv('TARGET', 'dev')}"
logger.info(f"Target: {target}")

STOCKS_TABLE = f"{target}.stocks"
STOCKS_TS_TABLE = f"{target}.yf_stocks_ts"
TARGET_TABLE_SUFFIX = f"{target}.yf_stocks_ts"

BATCH_SIZE = 100

STOCKS_DETAILED_COLUMNS = [
    "market_identifier_code",
    "yf_symbol",
    "capture_date",
    "market_cap",
    "current_price",
    "open",
    "beta",
    "forward_pe",
    "volume",
    "audit_risk",
    "board_risk",
    "compensation_risk",
    "share_holder_rights_risk",
    "overall_risk",
    "governance_epoch_date",
    "compensation_as_of_epoch_date",
    "max_age",
    "previous_close",
    "day_low",
    "day_high",
    "regular_market_previous_close",
    "regular_market_open",
    "regular_market_day_low",
    "regular_market_day_high",
    "regular_market_volume",
    "average_volume",
    "average_volume_10_days",
    "average_daily_volume_10_day",
    "bid",
    "ask",
    "bid_size",
    "ask_size",
    "fifty_two_week_low",
    "fifty_two_week_high",
    "fifty_day_average",
    "two_hundred_day_average",
    "enterprise_value",
    "float_shares",
    "shares_outstanding",
    "shares_short",
    "shares_short_prior_month",
    "shares_short_previous_month_date",
    "date_short_interest",
    "shares_percent_shares_out",
    "held_percent_insiders",
    "held_percent_institutions",
    "short_ratio",
    "short_percent_of_float",
    "implied_shares_outstanding",
    "book_value",
    "price_to_book",
    "net_income_to_common",
    "trailing_eps",
    "forward_eps",
    "peg_ratio",
    "enterprise_to_ebitda",
    "fifty_two_week_change",
    "sand_p_52_week_change",
    "target_high_price",
    "target_low_price",
    "target_mean_price",
    "target_median_price",
    "recommendation_mean",
    "recommendation_key",
    "number_of_analyst_opinions",
    "total_cash",
    "total_cash_per_share",
    "ebitda",
    "total_debt",
    "quick_ratio",
    "current_ratio",
    "debt_to_equity",
    "return_on_assets",
    "return_on_equity",
    "free_cashflow",
    "operating_cashflow",
    "trailing_peg_ratio",
]

@lru_cache(maxsize=1)
def _secret_helper():
    from marketstate.marketstate_data.dags._lib.utils import SecretManagerHelper

    return SecretManagerHelper()


def _import_bigquery():
    from google.cloud import bigquery

    return bigquery


def _import_bq_exceptions():
    from google.api_core.exceptions import BadRequest, GoogleAPICallError

    return BadRequest, GoogleAPICallError


def _import_service_account():
    from google.oauth2 import service_account

    return service_account


@lru_cache(maxsize=1)
def _orchestrator():
    from marketstate.marketstate_data.src.orchestrator import OrchestratorConfig, OrchestratorLogger

    return OrchestratorLogger(
        OrchestratorConfig(source="get_stock_data"),
        secret_helper=_secret_helper(),
    )


def _query_with_logging(
    client: Any, sql: str, *, label: str
) -> Any:
    BadRequest, GoogleAPICallError = _import_bq_exceptions()
    try:
        job = client.query(sql)
        logger.info("BQ query started [%s] job_id=%s", label, job.job_id)
        results = job.result()
        logger.info("BQ query finished [%s] job_id=%s", label, job.job_id)
        return results
    except BadRequest as exc:
        logger.exception("BQ query failed [%s] (BadRequest): %s", label, exc)
        raise
    except GoogleAPICallError as exc:
        logger.exception("BQ query failed [%s] (APICallError): %s", label, exc)
        raise


def _yf_throttle_seconds() -> float:
    value = os.getenv("YF_THROTTLE_SECONDS", "0.5").strip()
    try:
        return max(float(value), 0.0)
    except ValueError:
        return 0.5


def _yf_retries() -> int:
    # Default to a single attempt; yfinance 404s are common for invalid symbols and
    # retries just add noise and slow the DAG down.
    value = os.getenv("YF_RETRIES", "0").strip()
    try:
        return max(int(value), 0)
    except ValueError:
        return 0


def _to_snake_case(value: str) -> str:
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"([A-Za-z])([0-9])", r"\1_\2", value)
    value = re.sub(r"([0-9])([A-Za-z])", r"\1_\2", value)
    return value.lower()


def _get_symbols(client: Any) -> pd.DataFrame:
    query = f"""
        SELECT
            market_identifier_code,
            yf_symbol,
            capture_date
        FROM
            {STOCKS_TABLE}
        WHERE 
            skip != TRUE
        QUALIFY
            ROW_NUMBER() OVER (
                PARTITION BY market_identifier_code, yf_symbol
                ORDER BY capture_date DESC
            ) = 1
        ORDER BY
            capture_date DESC
    """
    results = _query_with_logging(client, query, label="get_symbols")
    df = results.to_dataframe()
    logger.info("BQ get_symbols returned %s rows", len(df))
    return df


def _get_processed_keys_for_today(
    client: Any, target_table: str
) -> set[tuple[str, str]]:
    query = f"""
        SELECT
            yf_symbol,
            market_identifier_code
        FROM
            {target_table}
        WHERE
            DATE(capture_date) = CURRENT_DATE()
    """
    results = _query_with_logging(client, query, label="get_processed_keys_for_today")
    keys = {(row.yf_symbol, row.market_identifier_code) for row in results}
    logger.info("BQ processed keys for today: %s", len(keys))
    return keys


def _count_processed_today(client: Any, target_table: str) -> int:
    query = f"""
        SELECT
            COUNT(DISTINCT yf_symbol) AS processed_count
        FROM
            {target_table}
        WHERE
            DATE(capture_date) = CURRENT_DATE()
    """
    results = list(_query_with_logging(client, query, label="count_processed_today"))
    if not results:
        return 0
    return int(results[0].processed_count or 0)


def _stocks_detailed_blank() -> pd.DataFrame:
    return pd.DataFrame(columns=STOCKS_DETAILED_COLUMNS)


def _get_symbol_info(df: pd.DataFrame) -> list[dict]:
    processed_symbols: list[dict] = []

    for i, row in df.iterrows():
        yf_symbol = row.get("yf_symbol")
        market_identifier_code = row.get("market_identifier_code")
        if not yf_symbol or not market_identifier_code:
            logger.warning("Missing symbol data in row: %s", row.to_dict())
            continue

        try:
            ticker_info = yf.Ticker(urllib.parse.quote(str(yf_symbol))).info
            normalized = {_to_snake_case(key): value for key, value in ticker_info.items()}
            normalized["market_identifier_code"] = market_identifier_code
            normalized["yf_symbol"] = yf_symbol
            normalized["capture_date"] = datetime.now().strftime("%Y-%m-%d")
            processed_symbols.append(normalized)
        except Exception as exc:
            logger.warning("Failed to fetch info for %s: %s", yf_symbol, exc)
    return processed_symbols


def _process_info(
    stocks_detailed_blank: pd.DataFrame, successful_symbols_list: list[dict]
) -> pd.DataFrame:
    if not successful_symbols_list:
        return stocks_detailed_blank.copy()

    processed_symbols = pd.DataFrame(successful_symbols_list)
    for col in stocks_detailed_blank.columns:
        if col not in processed_symbols.columns:
            processed_symbols[col] = ""

    if "capture_date" in processed_symbols.columns:
        processed_symbols["capture_date"] = pd.to_datetime(
            processed_symbols["capture_date"], errors="coerce"
        ).dt.date

    for col in processed_symbols.columns:
        if col != "capture_date":
            processed_symbols[col] = processed_symbols[col].astype(str)

    processed_symbols = processed_symbols[stocks_detailed_blank.columns]
    processed_symbols.fillna("", inplace=True)
    return processed_symbols


def _update_stock_get_info(
    stocks_detailed_updated: pd.DataFrame,
    target_table: str,
    project_id: str,
    credentials,
) -> None:
    try:
        if stocks_detailed_updated.empty:
            return
        from pandas_gbq import to_gbq

        logger.info(
            "Uploading %s rows x %s cols to %s",
            len(stocks_detailed_updated),
            len(stocks_detailed_updated.columns),
            target_table,
        )
        to_gbq(
            dataframe=stocks_detailed_updated,
            destination_table=target_table,
            project_id=project_id,
            if_exists="append",
            credentials=credentials,
            progress_bar=False,
        )
    except Exception as exc:
        logger.warning("Upload to BigQuery failed: %s", exc)
        # Keep the batch loop moving; failures are logged.
        return


@dag(
    dag_id="get_yf",
    start_date=pendulum.today(),
    schedule="0 8 * * *",
    catchup=False,
    doc_md=__doc__,
    default_args={
        "owner": "MarketState",
        "retries": 2,
    },
    tags=["yfinance"],
)
def get_yf():
    @task(show_return_value_in_logs=False)
    def fetch_symbols() -> list[dict]:
        secret_helper = _secret_helper()
        secret_resource = secret_helper.get_secret_resource(
            BQ_SECRET_RESOURCE_VAR, DEFAULT_BQ_SECRET_RESOURCE
        )
        bq_sa = secret_helper.fetch_service_account_json(secret_resource)
        if not isinstance(bq_sa, dict):
            raise ValueError("BigQuery secret payload is not a JSON object")
        project_id = bq_sa.get("project_id")
        if not project_id:
            raise ValueError("BigQuery secret payload missing project_id")
        service_account = _import_service_account()
        bigquery = _import_bigquery()
        credentials = service_account.Credentials.from_service_account_info(bq_sa)
        client = bigquery.Client(credentials=credentials, project=project_id)
        all_symbols = _get_symbols(client)
        if all_symbols.empty:
            logger.info("No symbols returned from source table for today.")
            return []
        outstanding = len(all_symbols)
        logger.info(
            "Outstanding symbols to process today (pre-dedupe): %s",
            outstanding,
        )
        return all_symbols.to_dict(orient="records")

    @task
    def process_batches(symbols: list[dict]) -> None:
        if not symbols:
            logger.info("No symbols to process in batches.")
            return

        secret_helper = _secret_helper()
        secret_resource = secret_helper.get_secret_resource(
            BQ_SECRET_RESOURCE_VAR, DEFAULT_BQ_SECRET_RESOURCE
        )
        bq_sa = secret_helper.fetch_service_account_json(secret_resource)
        if not isinstance(bq_sa, dict):
            raise ValueError("BigQuery secret payload is not a JSON object")
        project_id = bq_sa.get("project_id")
        if not project_id:
            raise ValueError("BigQuery secret payload missing project_id")

        service_account = _import_service_account()
        bigquery = _import_bigquery()
        credentials = service_account.Credentials.from_service_account_info(bq_sa)

        stocks_detailed_blank = _stocks_detailed_blank()
        all_symbols = pd.DataFrame(symbols)

        num_batches = (len(all_symbols) + BATCH_SIZE - 1) // BATCH_SIZE
        target_table = f"{project_id}.{TARGET_TABLE_SUFFIX}"
        client = bigquery.Client(credentials=credentials, project=project_id)
        processed_keys = _get_processed_keys_for_today(client, target_table)
        total_source = len(all_symbols)
        if processed_keys:
            keep_mask = ~all_symbols.apply(
                lambda row: (row.get("yf_symbol"), row.get("market_identifier_code"))
                in processed_keys,
                axis=1,
            )
            all_symbols = all_symbols[keep_mask]
        processed_today = _count_processed_today(client, target_table)
        logger.info(
            "Symbols total (base): %s | Processed today: %s | Remaining to process: %s",
            total_source,
            processed_today,
            len(all_symbols),
        )
        if all_symbols.empty:
            logger.info("No new symbols to process for today.")
            return
        num_batches = (len(all_symbols) + BATCH_SIZE - 1) // BATCH_SIZE

        total_start = time.monotonic()
        for start in range(0, len(all_symbols), BATCH_SIZE):
            batch_number = start // BATCH_SIZE + 1
            batch = all_symbols.iloc[start : start + BATCH_SIZE]
            logger.info(
                "Starting batch %s/%s with %s symbols.",
                batch_number,
                num_batches,
                len(batch),
            )

            batch_start = time.monotonic()
            successful_symbols_list = _get_symbol_info(batch)
            stocks_detailed_updated = _process_info(
                stocks_detailed_blank, successful_symbols_list
            )
            try:
                _update_stock_get_info(
                    stocks_detailed_updated=stocks_detailed_updated,
                    target_table=target_table,
                    project_id=project_id,
                    credentials=credentials,
                )
            except Exception as exc:
                logger.warning("Batch %s failed: %s", batch_number, exc)
                # Continue with remaining batches.
                continue
            batch_elapsed = time.monotonic() - batch_start
            elapsed = time.monotonic() - total_start
            avg_batch_time = elapsed / batch_number
            expected_total = avg_batch_time * num_batches
            remaining = max(expected_total - elapsed, 0.0)
            logger.info(
                "Batch %s/%s completed in %.2fs (%.2fh). Avg %.2fs (%.2fh). "
                "ETA %.2fs (%.2fh) total est %.2fs (%.2fh).",
                batch_number,
                num_batches,
                batch_elapsed,
                batch_elapsed / 3600.0,
                avg_batch_time,
                avg_batch_time / 3600.0,
                remaining,
                remaining / 3600.0,
                expected_total,
                expected_total / 3600.0,
            )
            del batch, successful_symbols_list, stocks_detailed_updated
            gc.collect()

    @task(trigger_rule="all_done")
    def write_orchestrator_log() -> None:
        """
        Append a single status row to the orchestrator logs table in BigQuery.

        Table default: general-428410.src_prod.orchestrator_logs
        Override via Airflow Variable ORCHESTRATOR_LOGS_TABLE_ID.
        """
        orchestrator = _orchestrator()
        context = get_current_context()
        dag_run = context.get("dag_run")
        task_states = orchestrator.task_states_from_dag_run(
            dag_run,
            ["fetch_symbols", "process_batches"],
        )
        state = orchestrator.state_from_task_states(task_states)
        orchestrator.write_from_airflow_context(
            state=state,
            notes={
                "strategy": "task_states",
                "task_states": task_states,
                "notes": "fetch_symbols, process_batches",
            },
        )

    symbols = fetch_symbols()
    batch_task = process_batches(symbols)
    log_task = write_orchestrator_log()
    batch_task >> log_task


get_yf()

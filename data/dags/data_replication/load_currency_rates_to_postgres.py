"""
Load currency data from BigQuery into Postgres via truncate-load.
Uses batched COPY with verbose progress logging.
"""

from __future__ import annotations

import io
import logging
import os
import re
import time

import pandas as pd
import pendulum
from airflow.sdk import dag, task
from google.cloud import bigquery
from google.oauth2 import service_account
from sqlalchemy import create_engine

try:
    from marketstate.marketstate_data.dags._lib.utils import SecretManagerHelper
except ModuleNotFoundError:
    # Airflow DAG bundle runtime usually mounts `dags/` directly on PYTHONPATH.
    from _lib.utils import SecretManagerHelper

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SOURCE_TABLE = "general-428410.stg_prod.exchange_rates_current"
TARGET_SCHEMA = f"src_{os.getenv('TARGET', 'dev')}"
TARGET_TABLE = "currency_rates"

BQ_SECRET_RESOURCE_VAR = "BQ_SECRET_RESOURCE"
BQ_SECRET_RESOURCE_DEFAULT = "projects/318171260121/secrets/bigquery"
POSTGRES_SECRET_RESOURCE_VAR = "POSTGRES_SECRET_RESOURCE"
POSTGRES_SECRET_RESOURCE_DEFAULT = "projects/318171260121/secrets/postgres"

BATCH_SIZE = max(int(os.getenv("CURRENCY_PG_BATCH_SIZE", "10000")), 1)
SOURCE_LIMIT_RAW = os.getenv("CURRENCY_SOURCE_LIMIT", "").strip()
SOURCE_LIMIT = int(SOURCE_LIMIT_RAW) if SOURCE_LIMIT_RAW else None

helper = SecretManagerHelper()


def _is_cloudsql_instance_name(value: str) -> bool:
    return bool(re.fullmatch(r"[^:\s]+:[^:\s]+:[^:\s]+", value))


def _safe_ident(value: str, label: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Unsafe {label}: {value!r}")
    return value


def _get_bq_client() -> bigquery.Client:
    bq_secret = helper.get_secret_resource(BQ_SECRET_RESOURCE_VAR, BQ_SECRET_RESOURCE_DEFAULT)
    bq_sa = helper.fetch_service_account_json(bq_secret)

    project_id = str(bq_sa.get("project_id", "")).strip()
    if not project_id:
        raise ValueError("BigQuery service account secret is missing `project_id`.")

    credentials = service_account.Credentials.from_service_account_info(bq_sa)
    logger.info("Creating BigQuery client for project: %s", project_id)
    return bigquery.Client(credentials=credentials, project=project_id)


def _read_source_df(client: bigquery.Client) -> pd.DataFrame:
    sql = f"""
        SELECT
          currency,
          CAST(rate AS FLOAT64) AS rate,
          DATE(date) AS rate_date
        FROM `{SOURCE_TABLE}`
        WHERE currency IS NOT NULL
          AND rate IS NOT NULL
          AND date IS NOT NULL
    """
    if SOURCE_LIMIT is not None and SOURCE_LIMIT > 0:
        sql += f"\nLIMIT {SOURCE_LIMIT}"
        logger.info("Applying source LIMIT=%s", SOURCE_LIMIT)

    logger.info("Reading BigQuery source table: %s", SOURCE_TABLE)
    t0 = time.monotonic()
    rows = list(client.query(sql).result())
    logger.info("BigQuery returned %s rows in %.2fs", len(rows), time.monotonic() - t0)

    df = pd.DataFrame(
        [
            {
                "currency": r["currency"],
                "rate": r["rate"],
                "rate_date": r["rate_date"],
            }
            for r in rows
        ]
    )

    if not df.empty:
        logger.info("BigQuery head:\n%s", df.head(10).to_string(index=False))
    return df


def _get_postgres_config() -> dict[str, str]:
    pg_secret = helper.get_secret_resource(
        POSTGRES_SECRET_RESOURCE_VAR, POSTGRES_SECRET_RESOURCE_DEFAULT
    )
    pg = helper.fetch_service_account_json(pg_secret)

    required = ["POSTGRES_ADMIN", "POSTGRES_PASSWORD", "POSTGRES_HOST"]
    missing = [k for k in required if not str(pg.get(k, "")).strip()]
    if missing:
        raise ValueError(f"{POSTGRES_SECRET_RESOURCE_VAR} secret is missing required key(s): {missing}")

    cfg = {
        "host": str(pg["POSTGRES_HOST"]).strip(),
        "user": str(pg["POSTGRES_ADMIN"]).strip(),
        "password": str(pg["POSTGRES_PASSWORD"]).strip(),
        "db": str(pg.get("POSTGRES_DB", "marketstate")).strip() or "marketstate",
    }
    logger.info("Postgres config parsed: host=%s db=%s user=%s", cfg["host"], cfg["db"], cfg["user"])
    return cfg


def _build_pg_engine(pg: dict[str, str]):
    if _is_cloudsql_instance_name(pg["host"]):
        from google.cloud.sql.connector import Connector

        logger.info("Using Cloud SQL connector mode")
        connector = Connector(refresh_strategy="lazy")
        engine = create_engine(
            "postgresql+pg8000://",
            creator=lambda: connector.connect(
                pg["host"],
                "pg8000",
                user=pg["user"],
                password=pg["password"],
                db=pg["db"],
            ),
            pool_pre_ping=True,
        )
        return engine, connector, "cloudsql_connector"

    import pg8000

    logger.info("Using direct TCP mode")
    engine = create_engine(
        "postgresql+pg8000://",
        creator=lambda: pg8000.connect(
            host=pg["host"],
            port=5432,
            user=pg["user"],
            password=pg["password"],
            database=pg["db"],
        ),
        pool_pre_ping=True,
    )
    return engine, None, "tcp"


def _truncate_load(engine, schema: str, table: str, df: pd.DataFrame, batch_size: int) -> None:
    logger.info("Starting Postgres truncate-load into %s.%s", schema, table)
    t0 = time.monotonic()

    raw = engine.raw_connection()
    try:
        cur = raw.cursor()
        cur.execute("SELECT CURRENT_DATABASE(), CURRENT_USER, NOW()")
        db, user_name, server_time = cur.fetchone()
        logger.info("Connected to Postgres: db=%s user=%s server_time=%s", db, user_name, server_time)

        cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        cur.execute(
            f'''
            CREATE TABLE IF NOT EXISTS "{schema}"."{table}" (
              currency TEXT NOT NULL,
              rate DOUBLE PRECISION NOT NULL,
              date DATE NOT NULL,
              loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            '''
        )
        cur.execute(f'TRUNCATE TABLE "{schema}"."{table}"')
        logger.info("Truncated %s.%s", schema, table)

        if df.empty:
            logger.info("Dataframe is empty; nothing to insert")
            raw.commit()
            return

        df_for_copy = df[["currency", "rate", "rate_date"]].copy()
        total = len(df_for_copy)
        copy_sql = f'COPY "{schema}"."{table}" (currency, rate, date) FROM STDIN WITH (FORMAT CSV)'
        logger.info("Starting batched COPY load: total_rows=%s batch_size=%s", total, batch_size)

        copy_t0 = time.monotonic()
        copied = 0
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch_df = df_for_copy.iloc[start:end]
            csv_buf = io.StringIO()
            batch_df.to_csv(csv_buf, index=False, header=False)
            csv_buf.seek(0)
            cur.execute(copy_sql, stream=csv_buf)
            copied += len(batch_df)
            logger.info(
                "COPY batch loaded %s/%s rows (%.1f%%) in %.2fs",
                copied,
                total,
                (copied / total) * 100.0,
                time.monotonic() - copy_t0,
            )

        cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
        count = cur.fetchone()[0]
        logger.info("Post-load row count in %s.%s = %s", schema, table, count)

        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()

    logger.info("Postgres truncate-load completed in %.2fs", time.monotonic() - t0)


@dag(
    dag_id="load_currency_rates_to_postgres",
    start_date=pendulum.today(),
    schedule="0 9 * * *",
    catchup=False,
    default_args={"owner": "MarketState", "retries": 0},
    tags=["currency", "postgres"],
)
def load_currency_rates_to_postgres():
    @task
    def run() -> dict[str, str | int]:
        schema = _safe_ident(TARGET_SCHEMA, "target_schema")
        table = _safe_ident(TARGET_TABLE, "target_table")

        bq_client = _get_bq_client()
        df = _read_source_df(bq_client)

        pg_cfg = _get_postgres_config()
        engine, connector, mode = _build_pg_engine(pg_cfg)
        try:
            _truncate_load(engine, schema, table, df, BATCH_SIZE)
        finally:
            if connector is not None:
                connector.close()
                logger.info("Closed Cloud SQL connector")

        return {
            "mode": mode,
            "source_table": SOURCE_TABLE,
            "target_table": f"{schema}.{table}",
            "rows_loaded": int(len(df)),
            "batch_size": BATCH_SIZE,
        }

    run()


load_currency_rates_to_postgres()

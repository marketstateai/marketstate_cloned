#!/usr/bin/env python3
"""Replicate BigQuery exchange rates into Supabase Postgres."""

from __future__ import annotations

import base64
import io
import json
import os
import time
from urllib.parse import quote, unquote, urlparse

import pandas as pd
import pg8000
from google.cloud import bigquery
from google.oauth2 import service_account


# Environment-backed configuration.
SOURCE_TABLE = os.getenv(
    "BQ_SOURCE_TABLE",
    "general-428410.stg_prod.exchange_rates_current",
)
TARGET_TABLE = os.getenv("SUPABASE_TARGET_TABLE", "exchange_rates_current")
BQ_SECRET_RESOURCE_VAR = "BQ_SECRET_RESOURCE"
BQ_SECRET_RESOURCE_DEFAULT = "projects/318171260121/secrets/bigquery"
BATCH_SIZE = max(int(os.getenv("SUPABASE_BATCH_SIZE", "10000")), 1)
SOURCE_LIMIT_RAW = os.getenv("BQ_SOURCE_LIMIT", "").strip()
SOURCE_LIMIT = int(SOURCE_LIMIT_RAW) if SOURCE_LIMIT_RAW else None


class SecretManagerHelper:
    SECRET_MANAGER_CREDENTIALS_ENV = "GOOGLE_SECRET_MANAGER_CREDENTIALS"
    SECRET_MANAGER_CREDENTIALS_B64_ENV = "GOOGLE_SECRET_MANAGER_CREDENTIALS_B64"
    DEFAULT_SECRET_MANAGER_CREDENTIALS = "/usr/local/airflow/.dbt/gcp-secrets.json"

    def _load_service_account_info(self, value: str) -> dict[str, object]:
        # Load service-account info from file path, JSON string, or base64 JSON.
        if os.path.isfile(value):
            with open(value, "r", encoding="utf-8") as handle:
                return json.load(handle)

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

        decoded = base64.b64decode(value).decode("utf-8")
        return json.loads(decoded)

    def _get_secret_manager_credentials(self):
        # Load credentials for reading Secret Manager.
        from google.oauth2 import service_account as google_service_account

        raw = os.getenv(self.SECRET_MANAGER_CREDENTIALS_ENV) or os.getenv(
            self.SECRET_MANAGER_CREDENTIALS_B64_ENV
        )
        if raw:
            info = self._load_service_account_info(raw)
            return google_service_account.Credentials.from_service_account_info(info)

        explicit_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if (
            explicit_path
            and os.path.isfile(explicit_path)
            and os.access(explicit_path, os.R_OK)
        ):
            return google_service_account.Credentials.from_service_account_file(
                explicit_path
            )

        if os.path.isfile(self.DEFAULT_SECRET_MANAGER_CREDENTIALS) and os.access(
            self.DEFAULT_SECRET_MANAGER_CREDENTIALS, os.R_OK
        ):
            return google_service_account.Credentials.from_service_account_file(
                self.DEFAULT_SECRET_MANAGER_CREDENTIALS
            )

        return None

    def fetch_service_account_json(self, secret_resource: str) -> dict[str, object]:
        # Fetch service-account JSON from Google Secret Manager.
        from google.cloud.secretmanager import SecretManagerServiceClient

        credentials = self._get_secret_manager_credentials()
        if credentials:
            client = SecretManagerServiceClient(credentials=credentials)
        else:
            client = SecretManagerServiceClient()

        response = client.access_secret_version(
            request={"name": f"{secret_resource}/versions/latest"}
        )
        return json.loads(response.payload.data.decode("utf-8"))


helper = SecretManagerHelper()


def _get_bq_client() -> bigquery.Client:
    # Prefer BigQuery credentials from Secret Manager.
    secret_resource = os.getenv(BQ_SECRET_RESOURCE_VAR, "").strip()
    secret_resource = secret_resource or BQ_SECRET_RESOURCE_DEFAULT

    try:
        bq_sa = helper.fetch_service_account_json(secret_resource)
        project_id = str(bq_sa.get("project_id", "")).strip()

        if not project_id:
            raise ValueError("BigQuery service account secret is missing `project_id`.")

        credentials = service_account.Credentials.from_service_account_info(bq_sa)

        print(f"Using BigQuery credentials from Secret Manager: {secret_resource}")
        return bigquery.Client(credentials=credentials, project=project_id)

    except Exception as exc:
        print(f"Secret Manager BigQuery auth unavailable, falling back to local creds: {exc}")

    # Fall back to explicit local BigQuery credentials.
    service_account_json = os.getenv("BQ_SERVICE_ACCOUNT_JSON", "").strip()
    service_account_file = os.getenv("BQ_SERVICE_ACCOUNT_FILE", "").strip()
    project_override = os.getenv("BQ_PROJECT", "").strip() or None

    if service_account_json:
        info = json.loads(service_account_json)
        credentials = service_account.Credentials.from_service_account_info(info)
        return bigquery.Client(
            credentials=credentials,
            project=project_override or info.get("project_id"),
        )

    if service_account_file:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file
        )
        return bigquery.Client(project=project_override, credentials=credentials)

    return bigquery.Client(project=project_override)


def _read_source_df(client: bigquery.Client) -> pd.DataFrame:
    # Query the source exchange-rate table.
    sql = f"""
        SELECT
          UPPER(currency) AS currency,
          CAST(rate AS FLOAT64) AS rate,
          DATE(date) AS date
        FROM `{SOURCE_TABLE}`
        WHERE currency IS NOT NULL
          AND rate IS NOT NULL
          AND date IS NOT NULL
    """

    if SOURCE_LIMIT is not None and SOURCE_LIMIT > 0:
        sql += f"\nLIMIT {SOURCE_LIMIT}"

    started_at = time.monotonic()
    rows = list(client.query(sql).result())

    print(
        f"Fetched {len(rows):,} rows from BigQuery in "
        f"{time.monotonic() - started_at:.2f}s"
    )

    df = pd.DataFrame(
        [
            {
                "currency": row["currency"],
                "rate": row["rate"],
                "date": row["date"],
            }
            for row in rows
        ]
    )

    if df.empty:
        print("Source query returned no rows.")
        return df

    # Normalize source data.
    df["currency"] = df["currency"].astype(str).str.upper().str.strip()
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

    df = df.dropna(subset=["currency", "rate", "date"])
    df = df.drop_duplicates(subset=["currency", "date"], keep="last")
    df = df.sort_values(["date", "currency"]).reset_index(drop=True)

    print(df.head())
    return df


def _get_required_env(name: str) -> str:
    # Retrieve a required environment variable.
    value = os.getenv(name, "").strip()

    if not value:
        raise ValueError(f"Missing required environment variable: {name}")

    return value


def _get_supabase_project_ref() -> str:
    # Derive project ref from SUPABASE_URL.
    supabase_url = _get_required_env("SUPABASE_URL")
    parsed_supabase_url = urlparse(supabase_url)
    supabase_host = parsed_supabase_url.hostname

    if not supabase_host or not supabase_host.endswith(".supabase.co"):
        raise ValueError(
            f"Invalid SUPABASE_URL: {supabase_url}. "
            "Expected format: https://<project-ref>.supabase.co"
        )

    return supabase_host.removesuffix(".supabase.co")


def _build_supabase_pooler_url_from_env() -> str:
    # Build Supabase Session Pooler URL from stored env vars.
    project_ref = _get_supabase_project_ref()
    password = _get_required_env("SUPABASE_POSTGRES_PASSWORD")
    region = _get_required_env("SUPABASE_POOLER_REGION")

    encoded_password = quote(password, safe="")
    pooler_host = f"aws-0-{region}.pooler.supabase.com"

    return (
        f"postgresql://postgres.{project_ref}:{encoded_password}"
        f"@{pooler_host}:5432/postgres"
    )


def _get_supabase_database_url() -> str:
    # Prefer the Supabase Session Pooler URL built from stored vars.
    database_url = _build_supabase_pooler_url_from_env()

    # Support placeholder-style URLs if manually overridden later.
    password_override = os.getenv("SUPABASE_POSTGRES_PASSWORD", "").strip()
    if password_override and "YOUR_PASSWORD" in database_url:
        encoded_password = quote(password_override, safe="")
        database_url = database_url.replace("YOUR_PASSWORD", encoded_password, 1)

    return database_url


def _get_pg_connection() -> pg8000.dbapi.Connection:
    # Open a pg8000 connection to Supabase through the Session Pooler.
    database_url = _get_supabase_database_url()
    parsed = urlparse(database_url)

    if not parsed.hostname or not parsed.username or parsed.password is None:
        raise ValueError("Supabase Postgres URL is missing host, user, or password.")

    database_name = (parsed.path or "/postgres").lstrip("/") or "postgres"

    # Decode URL-encoded credentials before passing them to pg8000.
    username = unquote(parsed.username)
    password = unquote(parsed.password)

    print(f"Connecting to Supabase Postgres host: {parsed.hostname}")
    print(f"Connecting to Supabase Postgres user: {username}")

    return pg8000.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=username,
        password=password,
        database=database_name,
        ssl_context=True,
    )


def _truncate_and_load(
    connection: pg8000.dbapi.Connection,
    table: str,
    df: pd.DataFrame,
    batch_size: int,
) -> None:
    # Refresh the target Supabase table through a temporary staging table.
    if df.empty:
        raise ValueError("Refusing to truncate/load because source DataFrame is empty.")

    cursor = connection.cursor()

    try:
        cursor.execute("DROP TABLE IF EXISTS exchange_rates_stage")
        cursor.execute(
            """
            CREATE TEMP TABLE exchange_rates_stage (
              currency TEXT NOT NULL,
              rate DOUBLE PRECISION NOT NULL,
              date DATE NOT NULL
            ) ON COMMIT DROP
            """
        )

        total = len(df)
        copied = 0
        started_at = time.monotonic()

        copy_sql = (
            "COPY exchange_rates_stage (currency, rate, date) "
            "FROM STDIN WITH (FORMAT CSV)"
        )

        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch_df = df.iloc[start:end][["currency", "rate", "date"]]

            csv_buf = io.StringIO()
            batch_df.to_csv(csv_buf, index=False, header=False)
            csv_buf.seek(0)

            cursor.execute(copy_sql, stream=csv_buf)

            copied += len(batch_df)
            print(
                f"Copied {copied:,}/{total:,} rows into temp stage "
                f"({time.monotonic() - started_at:.2f}s)"
            )


        cursor.execute(
            f"""
            ALTER TABLE public."{table}"
            ALTER COLUMN rate TYPE DOUBLE PRECISION
            USING rate::DOUBLE PRECISION
            """
        )

        cursor.execute(f'TRUNCATE TABLE public."{table}"')

        cursor.execute(
            f"""
            INSERT INTO public."{table}" (
              exchange_rate_sk,
              currency,
              rate,
              date
            )
            SELECT
              md5(currency || '|' || date::TEXT) AS exchange_rate_sk,
              currency,
              rate,
              date
            FROM exchange_rates_stage
            """
        )


        connection.commit()

        cursor.execute(f'SELECT COUNT(*) FROM public."{table}"')
        row_count = cursor.fetchone()[0]

        print(f"Supabase refresh committed: {row_count:,} rows in public.{table}")

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()


def main() -> None:
    # Read from BigQuery.
    bq_client = _get_bq_client()
    df = _read_source_df(bq_client)

    # Write to Supabase.
    connection = _get_pg_connection()
    try:
        _truncate_and_load(connection, TARGET_TABLE, df, BATCH_SIZE)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
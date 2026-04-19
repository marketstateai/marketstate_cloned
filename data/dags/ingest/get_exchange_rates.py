DAG_DOC = """
## MarketState FX Rates DAG

Daily DAG that pulls historical USD FX rates from the JSDelivr currency API,
writes a Parquet snapshot to GCS, and loads recent snapshots into BigQuery.

Key behavior:
- Uses the run date (`ds`) to build the API version URL:
  https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@YYYY.MM.DD/v1/currencies/usd.json
- Writes one Parquet file per day in GCS:
  usd_fx_snapshot_YYYYMMDD.parquet
- Adds a `date` column to the Parquet data (used for partitioning in BigQuery).
- Loads the latest 3 Parquet files and only inserts dates not yet in the table.

Backfill:
- `catchup=False` is enabled so Astronomer backfill will materialize historical runs.
- Use the UI backfill range to populate historical dates.

Required Airflow Variables:
- USD_FX_TABLE_ID: dataset.table or project.dataset.table
- GCS_RAW_DATA: target bucket name
- BQ_SECRET_RESOURCE: Secret Manager resource for BigQuery SA
- GCS_SECRET_RESOURCE: Secret Manager resource for GCS SA
"""

import os

os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
os.environ.setdefault("GRPC_TRACE", "")
os.environ.setdefault("ABSL_LOGGING_MIN_SEVERITY", "2")
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("GLOG_logtostderr", "0")
os.environ.setdefault("GLOG_stderrthreshold", "2")

from airflow.sdk import Asset, Variable, dag, get_current_context, task
from google.cloud import bigquery, storage
from google.api_core.exceptions import NotFound
from google.oauth2 import service_account
import pyarrow as pa
import pyarrow.parquet as pq
import pendulum
import requests
import pandas as pd
import logging

from marketstate.marketstate_data.src.orchestrator import OrchestratorConfig, OrchestratorLogger

from marketstate.marketstate_data.dags._lib.utils import SecretManagerHelper


logger = logging.getLogger(__name__)

target = f"src_{os.getenv('TARGET', 'dev')}"
logger.info("Target: %s", target)

TABLE_ID_VAR = "USD_FX_TABLE_ID"
GCS_BUCKET_VAR = "GCS_RAW_DATA"
GCS_OBJECT_PREFIX = "usd_fx_snapshot_"


URL_TEMPLATE = (
    "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{version}/v1/currencies/usd.json"
)
BQ_SECRET_RESOURCE_VAR = "BQ_SECRET_RESOURCE"
GCS_SECRET_RESOURCE_VAR = "GCS_SECRET_RESOURCE"
ORCHESTRATOR_LOGS_TABLE_VAR = "ORCHESTRATOR_LOGS_TABLE_ID"
ORCHESTRATOR_LOGS_IGNORE_ERRORS_VAR = "ORCHESTRATOR_LOGS_IGNORE_ERRORS"

secret_helper = SecretManagerHelper()

orchestrator = OrchestratorLogger(
    OrchestratorConfig(source="get_exchange_rate"),
    secret_helper=secret_helper,
)


def _latest_parquet_gcs_uris(
        bucket_name: str, 
        prefix: str, 
        credentials, 
        project_id: str, 
        limit: int = 3
        ) -> list[tuple[str, str]]:
    """
    Return up to `limit` most recent Parquet objects in GCS for a prefix.

    Objects are expected to follow `{prefix}YYYYMMDD.parquet`. The date is parsed
    from the filename (not object metadata) and returned alongside the GCS URI.
    """
    storage_client = storage.Client(credentials=credentials, project=project_id)
    blobs = storage_client.list_blobs(bucket_name, prefix=prefix)
    dated_blobs = []
    for blob in blobs:
        if not blob.name.endswith(".parquet"):
            continue
        name = blob.name
        if not name.startswith(prefix):
            continue
        date_str = name[len(prefix) : -len(".parquet")]
        try:
            date_value = pendulum.from_format(date_str, "YYYYMMDD").to_date_string()
        except Exception:
            continue
        dated_blobs.append((date_value, name))

    if not dated_blobs:
        raise FileNotFoundError(
            f"No Parquet objects found in gs://{bucket_name}/{prefix}*"
        )
    dated_blobs.sort(key=lambda item: item[0], reverse=True)
    latest = dated_blobs[:limit]
    return [(date_value, f"gs://{bucket_name}/{name}") for date_value, name in latest]


def _date_str_from_ds(ds: str) -> str:
    return ds.replace("-", "")


def _version_from_ds(ds: str) -> str:
    date_value = pendulum.from_format(ds, "YYYY-MM-DD")
    return f"{date_value.year}.{date_value.month}.{date_value.day}"


@dag(
    dag_id="get_exchange_rate",
    start_date=pendulum.today(),
    schedule="0 8 * * *",
    catchup=False,
    doc_md=DAG_DOC,
    default_args={
        "owner": "MarketState",
        "retries": 2,
    },
    tags=["currency"],
)
def get_exchange_rate():
    @task(outlets=[Asset("usd_fx_snapshot")], show_return_value_in_logs=False)
    def fetch_and_convert_to_dataframe(ds: str) -> list[dict]:
        """
        Fetches live USD FX data, converts it to a DataFrame,
        and returns rows for downstream processing.
        """
        try:
            version = _version_from_ds(ds)
            url = URL_TEMPLATE.format(version=version)
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()

            currency_data = [
                {"currency": key, "rate": value}
                for key, value in data["usd"].items()
            ]

            df = pd.DataFrame(currency_data)

            logger.info("Total currencies found: %s", len(df))

            return currency_data

        except requests.exceptions.RequestException as e:
            logger.error("Error fetching data: %s", e)
            raise

        except KeyError:
            logger.error("Unexpected data structure in the response")
            raise

    @task(show_return_value_in_logs=False, do_xcom_push=False)
    def write_to_gcs(rows: list[dict], ds: str) -> str:
        """
        Uploads Parquet content to GCS using a service account from Secret Manager.
        """
        try:
            df = pd.DataFrame(rows)
            bucket_name = Variable.get(GCS_BUCKET_VAR, "raw_data_marketstate")
            gcs_secret = secret_helper.get_secret_resource(
                GCS_SECRET_RESOURCE_VAR, "projects/318171260121/secrets/storage"
            )
            gcs_sa = secret_helper.fetch_service_account_json(gcs_secret)
            logger.info(
                "GCS SA identity: %s (project_id=%s)",
                gcs_sa.get("client_email"),
                gcs_sa.get("project_id"),
            )
            date_str = _date_str_from_ds(ds)
            date_value = pendulum.from_format(date_str, "YYYYMMDD").date()
            df["date"] = date_value
            object_name = f"{GCS_OBJECT_PREFIX}{date_str}.parquet"
            gcs_credentials = service_account.Credentials.from_service_account_info(
                gcs_sa
            )
            gcs_project_id = gcs_sa.get("project_id")
            storage_client = storage.Client(
                credentials=gcs_credentials, project=gcs_project_id
            )
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            with blob.open("wb") as f:
                schema = pa.schema(
                    [
                        ("currency", pa.string()),
                        ("rate", pa.float64()),
                        ("date", pa.date32()),
                    ]
                )
                table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
                pq.write_table(table, f)
            gcs_uri = f"gs://{bucket_name}/{object_name}"
            logger.info("Uploaded Parquet to %s", gcs_uri)
            return gcs_uri

        except Exception as e:
            logger.error("Error writing to GCS: %s", e)
            raise

    @task
    def load_to_bigquery() -> None:
        """
        Loads rows into BigQuery from a GCS Parquet object.
        """
        try:
            table_id = Variable.get(TABLE_ID_VAR, f"{target}.exchange_rates")

            bq_secret = secret_helper.get_secret_resource(
                BQ_SECRET_RESOURCE_VAR, "projects/318171260121/secrets/bigquery"
            )
            bq_sa = secret_helper.fetch_service_account_json(bq_secret)
            project_id = bq_sa.get("project_id")

            if table_id.count(".") == 1:
                table_id = f"{project_id}.{table_id}"
            elif table_id.count(".") != 2:
                raise ValueError(
                    f"{TABLE_ID_VAR} must be dataset.table or project.dataset.table"
                )

            write_disposition = bigquery.WriteDisposition.WRITE_APPEND

            bucket_name = Variable.get(GCS_BUCKET_VAR, "raw_data_marketstate")
            gcs_secret = secret_helper.get_secret_resource(
                GCS_SECRET_RESOURCE_VAR, "projects/318171260121/secrets/storage"
            )
            gcs_sa = secret_helper.fetch_service_account_json(gcs_secret)
            gcs_credentials = service_account.Credentials.from_service_account_info(
                gcs_sa
            )
            gcs_project_id = gcs_sa.get("project_id")
            latest_uris = _latest_parquet_gcs_uris(
                bucket_name, GCS_OBJECT_PREFIX, gcs_credentials, gcs_project_id
            )

            logger.info("Latest URIs (sample): %s", latest_uris[:10])

            bq_credentials = service_account.Credentials.from_service_account_info(
                bq_sa
            )
            client = bigquery.Client(credentials=bq_credentials, project=project_id)
            ddl = f"""
            CREATE TABLE IF NOT EXISTS `{table_id}` (
              currency STRING,
              rate FLOAT64,
              date DATE
            )
            PARTITION BY date
            """
            client.query(ddl).result()
            for date_value, gcs_uri in latest_uris:
                exists_query = (
                    f"SELECT 1 FROM `{table_id}` "
                    f"WHERE date = DATE('{date_value}') LIMIT 1"
                )
                try:
                    exists = list(client.query(exists_query).result())
                    if exists:
                        logger.info(
                            "Skipping %s; %s already loaded", gcs_uri, date_value
                        )
                        continue
                except NotFound:
                    logger.info("Table %s not found; will create on load", table_id)

                job_config = bigquery.LoadJobConfig(
                    write_disposition=write_disposition,
                    source_format=bigquery.SourceFormat.PARQUET,
                    autodetect=True,
                    schema_update_options=[
                        bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION
                    ],
                )
                load_job = client.load_table_from_uri(
                    gcs_uri, table_id, job_config=job_config
                )
                load_job.result()
                logger.info("Loaded data from %s into %s", gcs_uri, table_id)

        except Exception as e:
            logger.error(f"Error writing to BigQuery: {e}")
            raise

    @task(trigger_rule="all_done")
    def write_orchestrator_log() -> None:
        """
        Append a single status row to the orchestrator logs table in BigQuery.

        Table default: general-428410.src_prod.orchestrator_logs
        Override via Airflow Variable ORCHESTRATOR_LOGS_TABLE_ID.
        """
        context = get_current_context()
        snapshot = orchestrator.prev_success_snapshot(context)
        ds = str(snapshot.get("ds") or "").strip()
        state = orchestrator.state_from_prev_success(
            ds=ds,
            prev_end_date_success=context.get("prev_end_date_success"),
        )
        task_states = orchestrator.task_states_from_dag_run(
            context.get("dag_run"),
            ["fetch_and_convert_to_dataframe", "write_to_gcs", "load_to_bigquery"],
        )
        orchestrator.write_from_airflow_context(
            state=state,
            notes={
                "strategy": "prev_success",
                "task_states": task_states,
                **snapshot,
            },
        )

    rows = fetch_and_convert_to_dataframe(ds="{{ ds }}")
    gcs_task = write_to_gcs(rows, ds="{{ ds }}")
    load_task = load_to_bigquery()
    log_task = write_orchestrator_log()
    gcs_task >> load_task >> log_task


get_exchange_rate()

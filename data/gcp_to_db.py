#!/usr/bin/env python3
"""
BigQuery -> local parquet -> Unity Catalog volume -> managed Delta table (Databricks way)

Uses:
- BigQuery (via your existing GCP helper)
- Databricks SDK Files API to upload parquet to a UC Volume
- Databricks SQL Statement Execution API to create/replace a managed Delta table

Env vars required:
- DATABRICKS_HOST
- DATABRICKS_TOKEN

Optional:
- DATABRICKS_WAREHOUSE_ID
  If not set, the script will automatically choose a SQL warehouse (prefers a RUNNING one).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import sql as dbsql

# Section header comments
# make marketstate imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Section header comments
# source query from BigQuery
QUERY = """
SELECT *
FROM `general-428410.src_prod.yf_stocks_ts`
""".strip()


# Section header comments
# helper for your existing GCP wrapper
def _secret_manager_service_account(session) -> dict:
    candidate = getattr(session, "secret_manager_path", None)
    if isinstance(candidate, dict):
        return candidate
    return session.GOOGLE_SECRET_MANAGER_CREDENTIALS


# Section header comments
# fetch rows from BigQuery using your existing template
def bq_to_rows(query: str, *, limit: int | None = None, job_project: str | None = None) -> list[dict[str, Any]]:
    from marketstate.src.gcp_functions import GCP

    session = GCP()
    if job_project:
        session.project_id = job_project

    bq_creds = session.get_credentials_from_secret_manager(
        secret_id="bigquery",
        version_id=1,
        secret_manager_service_account=_secret_manager_service_account(session),
    )

    df = session.bq_to_df(credentials=bq_creds, query=query)
    if limit is not None:
        df = df.head(limit)

    return df.to_dict(orient="records")


# Section header comments
# choose a SQL warehouse automatically if env var is not provided
def get_warehouse_id(w: WorkspaceClient) -> str:
    env_id = os.environ.get("DATABRICKS_WAREHOUSE_ID")
    if env_id:
        print(f"Using warehouse from env: {env_id}")
        return env_id

    warehouses = list(w.warehouses.list())

    if not warehouses:
        raise RuntimeError(
            "No SQL warehouses found in this workspace. Create one in Databricks SQL first."
        )

    # prefer a running warehouse
    for wh in warehouses:
        state = str(getattr(wh, "state", "")).upper()
        if "RUNNING" in state:
            print(f"Using running warehouse: {wh.name} ({wh.id})")
            return wh.id

    # fallback to first warehouse (Databricks may auto-start it)
    wh = warehouses[0]
    print(f"Using warehouse: {wh.name} ({wh.id})")
    return wh.id


# Section header comments
# run SQL on a Databricks SQL warehouse and wait for completion
def execute_sql(
    w: WorkspaceClient,
    warehouse_id: str,
    sql_text: str,
    timeout_seconds: int = 900,
):
    resp = w.statement_execution.execute_statement(
        statement=sql_text,
        warehouse_id=warehouse_id,
        wait_timeout="50s",
        disposition=dbsql.Disposition.INLINE,
        format=dbsql.Format.JSON_ARRAY,
    )

    statement_id = resp.statement_id
    status = resp.status.state if resp.status else None

    start = time.time()
    while status in ("PENDING", "RUNNING"):
        if time.time() - start > timeout_seconds:
            raise TimeoutError(
                f"SQL statement timed out after {timeout_seconds}s "
                f"(statement_id={statement_id})"
            )
        time.sleep(2)
        resp = w.statement_execution.get_statement(statement_id=statement_id)
        status = resp.status.state if resp.status else None

    if status != "SUCCEEDED":
        err = resp.status.error if resp.status else None
        raise RuntimeError(f"SQL failed: {status} | {err}")

    return resp


# Section header comments
# print available warehouses (optional debug helper)
def print_warehouses(w: WorkspaceClient) -> None:
    print("\nAvailable SQL warehouses:")
    for wh in w.warehouses.list():
        print(f"  name={wh.name} | id={wh.id} | state={wh.state}")


# Section header comments
# main
def main() -> None:
    # Databricks client
    w = WorkspaceClient(
        host=os.environ["DATABRICKS_HOST"],
        token=os.environ["DATABRICKS_TOKEN"],
    )

    # Pick a warehouse automatically (or use env override)
    warehouse_id = get_warehouse_id(w)

    # Local staging path
    local_dir = Path("/Users/gabrielzenkner/projects/marketstate/data")
    local_dir.mkdir(parents=True, exist_ok=True)
    local_parquet = local_dir / "yf_stocks_ts_new_from_bigquery.parquet"

    # Databricks UC volume staging path (volume must already exist)
    volume_parquet = "/Volumes/dev/bronze/files/yf_stocks_ts_new/yf_stocks_ts_new_from_bigquery.parquet"

    # Final managed Delta table
    target_table = "dev.bronze.yf_stocks_ts_new"

    # Section header comments
    # extract from BigQuery
    rows = bq_to_rows(QUERY, limit=None, job_project="general-428410")
    if not rows:
        print("No rows returned from BigQuery.")
        return

    print(f"Fetched {len(rows):,} rows from BigQuery")

    # Section header comments
    # write local parquet (good staging/interchange format)
    pdf = pd.DataFrame(rows)
    pdf.to_parquet(local_parquet, index=False)
    print(f"Wrote local parquet: {local_parquet}")

    # Section header comments
    # upload parquet to Unity Catalog volume
    # upload_from is the recommended SDK method for local file paths
    w.files.upload_from(
        file_path=volume_parquet,
        source_path=str(local_parquet),
        overwrite=True,
    )
    print(f"Uploaded to volume: {volume_parquet}")

    # Section header comments
    # create or replace managed Delta table from staged parquet
    # CTAS reads parquet from the volume and writes a managed Delta table
    sql_text = f"""
    CREATE OR REPLACE TABLE {target_table}
    USING DELTA
    AS
    SELECT *
    FROM parquet.`{volume_parquet}`
    """
    execute_sql(w, warehouse_id, sql_text)
    print(f"Created/updated Delta table: {target_table}")

    # Section header comments
    # verify row count
    verify_sql = f"SELECT COUNT(*) AS row_count FROM {target_table}"
    verify_resp = execute_sql(w, warehouse_id, verify_sql)

    result = getattr(verify_resp, "result", None)
    if result and getattr(result, "data_array", None):
        print("Row count:", result.data_array[0][0])
    else:
        print("Verification query succeeded (no inline result payload returned).")


if __name__ == "__main__":
    main()
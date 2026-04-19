"""Shared BigQuery helpers."""

from __future__ import annotations

import pandas as pd
from google.cloud import bigquery


def load_dataframe_to_bigquery(
    df: pd.DataFrame,
    table_id: str,
    project: str | None,
    write_disposition: str,
    ddl: str,
    schema: list[bigquery.SchemaField],
    empty_message: str,
    credentials=None,
) -> None:
    if df.empty:
        print(empty_message)
        return
    client = bigquery.Client(project=project, credentials=credentials)
    client.query(ddl.format(table_id=table_id)).result()
    job_config = bigquery.LoadJobConfig(
        write_disposition=write_disposition,
        schema=schema,
    )
    load_job = client.load_table_from_dataframe(
        df, table_id, job_config=job_config
    )
    load_job.result()
    print(f"Wrote {len(df)} rows to BigQuery table {table_id}.")

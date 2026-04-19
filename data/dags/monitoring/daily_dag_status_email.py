"""
Daily Airflow DAG that emails a concise status summary for today.

Configuration:
- `DAG_STATUS_EMAIL_TO`: comma-separated recipients (Airflow Variable preferred)
- `DAG_STATUS_EMAIL_SUBJECT_PREFIX`: optional subject prefix (Airflow Variable preferred)
- `ORCHESTRATOR_LOGS_TABLE_ID`: fully-qualified BigQuery table id
  (defaults to `general-428410.src_prod.orchestrator_logs`)

This DAG is intentionally simple:
1) Run a BigQuery query to fetch today's latest status per DAG.
2) Send an email with the results.
"""

from __future__ import annotations

import html
import json
import os
import smtplib
from datetime import date
from email.message import EmailMessage

import pendulum
from airflow.sdk import Variable, dag, get_current_context, task
from google.cloud import bigquery
from google.oauth2 import service_account

from marketstate.marketstate_data.dags._lib.utils import SecretManagerHelper


BQ_SECRET_RESOURCE_VAR = "BQ_SECRET_RESOURCE"
DEFAULT_BQ_SECRET_RESOURCE = "projects/318171260121/secrets/bigquery"
ORCHESTRATOR_LOGS_TABLE_VAR = "ORCHESTRATOR_LOGS_TABLE_ID"
DEFAULT_ORCHESTRATOR_LOGS_TABLE_ID = "general-428410.src_prod.orchestrator_logs"

secret_helper = SecretManagerHelper()


def _get_recipients() -> list[str]:
    value = Variable.get("DAG_STATUS_EMAIL_TO", os.getenv("DAG_STATUS_EMAIL_TO", ""))
    # recipients = [addr.strip() for addr in (value or "").split(",") if addr.strip()]
    recipients = ['gabriel.zenkner@gmail.com']
    if not recipients:
        raise ValueError(
            "Missing recipients: set Airflow Variable DAG_STATUS_EMAIL_TO or env var DAG_STATUS_EMAIL_TO."
        )
    return recipients


def _subject_prefix() -> str:
    value = Variable.get(
        "DAG_STATUS_EMAIL_SUBJECT_PREFIX",
        os.getenv("DAG_STATUS_EMAIL_SUBJECT_PREFIX", "MarketState"),
    )
    value = (value or "").strip()
    return value or "MarketState"


def _brevo_api_token() -> str:
    value = Variable.get("BREVO_API_TOKEN", os.getenv("BREVO_API_TOKEN", ""))
    value = (value or "").strip()
    if not value:
        raise ValueError("Missing Brevo SMTP token: set BREVO_API_TOKEN (Airflow Variable or env var).")
    return value


def _send_with_brevo_smtp(
    *,
    to_addrs: list[str],
    subject: str,
    text: str,
    html_content: str | None = None,
) -> None:
    """
    Send email via Brevo SMTP.

    This mirrors `/Users/gabrielzenkner/projects/test_email.py` (verified/tested).
    """
    smtp_host = "smtp-relay.brevo.com"
    smtp_port = 587
    smtp_login = "a36933001@smtp-brevo.com"
    smtp_password = _brevo_api_token()

    from_email = Variable.get("BREVO_FROM_EMAIL", os.getenv("BREVO_FROM_EMAIL", "gabriel.zenkner@gmail.com")).strip()
    from_name = Variable.get("BREVO_FROM_NAME", os.getenv("BREVO_FROM_NAME", "Gabriel")).strip()

    if not to_addrs:
        raise ValueError("No recipients provided.")

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_login, smtp_password)

        for to_addr in to_addrs:
            msg = EmailMessage()
            msg["To"] = to_addr
            msg["From"] = f"{from_name} <{from_email}>" if from_name else from_email
            msg["Subject"] = subject
            msg.set_content(text)
            if html_content:
                msg.add_alternative(html_content, subtype="html")
            server.send_message(msg)


def _get_bigquery_client() -> tuple[bigquery.Client, str]:
    secret_resource = secret_helper.get_secret_resource(
        BQ_SECRET_RESOURCE_VAR, DEFAULT_BQ_SECRET_RESOURCE
    )
    bq_sa = secret_helper.fetch_service_account_json(secret_resource)
    if not isinstance(bq_sa, dict):
        raise ValueError("BigQuery secret payload is not a JSON object")
    project_id = bq_sa.get("project_id")
    if not project_id:
        raise ValueError("BigQuery secret payload missing project_id")
    credentials = service_account.Credentials.from_service_account_info(bq_sa)
    return bigquery.Client(credentials=credentials, project=project_id), project_id


def _run_date_from_context() -> date:
    context = get_current_context()
    logical_date = context.get("logical_date") or context.get("execution_date")
    if logical_date:
        try:
            return pendulum.instance(logical_date).date()
        except Exception:
            pass
    return pendulum.now("UTC").date()


def _default_daily_status_sql(table_id: str) -> str:
    # Latest state per dag_id for the given run_date (UTC), based on orchestrator logs.
    return f"""
    WITH base AS (
      SELECT
        dag_id,
        state,
        log_ts,
        source
      FROM `{table_id}`
      WHERE DATE(logical_date) = @run_date
    ),
    ranked AS (
      SELECT
        dag_id,
        state,
        log_ts,
        source,
        ROW_NUMBER() OVER (PARTITION BY dag_id ORDER BY log_ts DESC) AS rn
      FROM base
    )
    SELECT
      dag_id,
      state,
      log_ts,
      source
    FROM ranked
    WHERE rn = 1
    ORDER BY dag_id
    """


@dag(
    dag_id="daily_dag_status_email",
    start_date=pendulum.datetime(2026, 2, 25, tz="UTC"),
    schedule="0 9 * * *",
    catchup=False,
    default_args={"owner": "MarketState", "retries": 0},
    tags=["monitoring", "email"],
)
def daily_dag_status_email():
    @task
    def run_query() -> dict:
        def jsonify(value: object) -> object:
            if value is None:
                return None
            iso = getattr(value, "isoformat", None)
            if callable(iso):
                try:
                    return iso()
                except Exception:
                    pass
            if isinstance(value, (str, int, float, bool)):
                return value
            return str(value)

        run_date = _run_date_from_context()
        table_id = Variable.get(
            ORCHESTRATOR_LOGS_TABLE_VAR,
            os.getenv(ORCHESTRATOR_LOGS_TABLE_VAR, DEFAULT_ORCHESTRATOR_LOGS_TABLE_ID),
        )
        if str(table_id).count(".") != 2:
            raise ValueError(
                f"{ORCHESTRATOR_LOGS_TABLE_VAR} must be fully-qualified project.dataset.table"
            )

        sql = Variable.get("DAG_STATUS_BQ_SQL", os.getenv("DAG_STATUS_BQ_SQL", "")).strip()
        if sql:
            # Allow overriding the query (optionally referencing {table_id}).
            sql = sql.format(table_id=table_id)
        else:
            sql = _default_daily_status_sql(table_id)

        client, _project_id = _get_bigquery_client()
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("run_date", "DATE", run_date),
            ]
        )
        rows = client.query(sql, job_config=job_config).result()
        results = [{k: jsonify(v) for k, v in dict(row.items()).items()} for row in rows]
        print(
            "daily_dag_status_email query results:",
            json.dumps(
                {
                    "run_date": run_date.isoformat(),
                    "table_id": str(table_id),
                    "row_count": len(results),
                    "rows": results,
                },
                indent=2,
                sort_keys=True,
            ),
        )
        return {"run_date": run_date.isoformat(), "table_id": str(table_id), "rows": results}

    @task
    def send_email_report(payload: dict) -> None:
        recipients = _get_recipients()
        run_date = str(payload.get("run_date") or "")
        table_id = str(payload.get("table_id") or "")
        rows = list(payload.get("rows") or [])

        state_counts: dict[str, int] = {}
        failing: list[dict] = []
        for row in rows:
            state = str(row.get("state") or "none").lower()
            state_counts[state] = state_counts.get(state, 0) + 1
            if state not in {"success"}:
                failing.append(row)

        counts_str = ", ".join(f"{k}={v}" for k, v in sorted(state_counts.items())) or "no_rows=1"
        subject = f"{_subject_prefix()} | Daily status | {run_date} | {counts_str}"
        text_body = (
            f"Daily DAG status (UTC date): {run_date}\n"
            f"Source table: {table_id}\n"
            f"Counts: {counts_str}\n"
            f"Rows: {len(rows)}\n"
        )

        def td(value: object) -> str:
            return f"<td>{html.escape('' if value is None else str(value))}</td>"

        failing_list = (
            "<ul>"
            + "".join(f"<li>{html.escape(str(r.get('dag_id') or ''))}: {html.escape(str(r.get('state') or ''))}</li>" for r in failing)
            + "</ul>"
            if failing
            else "<p><b>All DAGs successful (based on query results).</b></p>"
        )

        table_rows = "\n".join(
            "<tr>"
            + td(r.get("dag_id"))
            + td(r.get("state"))
            + td(r.get("log_ts"))
            + td(r.get("source"))
            + "</tr>"
            for r in rows
        )
        table_body = (
            table_rows
            if table_rows
            else '<tr><td colspan="4"><i>No rows returned for this date.</i></td></tr>'
        )

        html_body = f"""
        <h3>Daily DAG status</h3>
        <p><b>Date (UTC):</b> {html.escape(run_date)}</p>
        <p><b>Source table:</b> {html.escape(table_id)}</p>
        <p><b>Counts:</b> {html.escape(counts_str)}</p>
        <h4>Non-success</h4>
        {failing_list}
        <h4>Latest per DAG</h4>
        <table border="1" cellpadding="4" cellspacing="0">
          <thead>
            <tr>
              <th>DAG</th>
              <th>State</th>
              <th>Log TS</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {table_body}
          </tbody>
        </table>
        """

        _send_with_brevo_smtp(
            to_addrs=recipients,
            subject=subject,
            text=text_body,
            html_content=html_body,
        )

    send_email_report(run_query())


daily_dag_status_email()

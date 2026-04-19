"""Orchestrator log writer for Airflow DAGs.

This module centralizes the logic used by DAGs to append a single "orchestrator"
row into BigQuery (e.g. `general-428410.src_prod.orchestrator_logs`).

Design goals:
- Extensible: pluggable state derivation and flexible notes payloads.
- Safe: best-effort serialization that avoids triggering Airflow Variable accessors.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

import pendulum

try:  # Optional: only available in Airflow runtime.
    from airflow.sdk import Variable, get_current_context
except Exception:  # pragma: no cover
    Variable = None  # type: ignore[assignment]
    get_current_context = None  # type: ignore[assignment]

try:  # Optional: available when running inside the Airflow dags folder.
    from _lib.utils import SecretManagerHelper
except Exception:  # pragma: no cover
    SecretManagerHelper = None  # type: ignore[assignment]


@dataclass(frozen=True)
class OrchestratorConfig:
    source: str
    bq_secret_resource_var: str = "BQ_SECRET_RESOURCE"
    bq_secret_resource_default: str = "projects/318171260121/secrets/bigquery"
    logs_table_var: str = "ORCHESTRATOR_LOGS_TABLE_ID"
    logs_table_default: str = "general-428410.src_prod.orchestrator_logs"
    ignore_errors_var: str = "ORCHESTRATOR_LOGS_IGNORE_ERRORS"


class OrchestratorLogger:
    def __init__(self, config: OrchestratorConfig, *, secret_helper: Any | None = None) -> None:
        self.config = config
        if secret_helper is not None:
            self._secret_helper = secret_helper
        else:
            if SecretManagerHelper is None:  # pragma: no cover
                raise RuntimeError("SecretManagerHelper is not available in this runtime.")
            self._secret_helper = SecretManagerHelper()

    # -------------------------
    # Public: state derivation
    # -------------------------
    def state_from_task_states(self, task_states: Mapping[str, str]) -> str:
        values = [str(v).strip().lower() for v in task_states.values()]
        if any(v in {"failed", "upstream_failed"} for v in values):
            return "failed"
        if values and all(v == "success" for v in values):
            return "success"
        if any(v in {"queued", "scheduled", "running", "deferred", "none"} for v in values):
            return "running"
        if values and all(v in {"success", "skipped"} for v in values) and any(v == "skipped" for v in values):
            return "skipped"
        return "unknown"

    def task_states_from_dag_run(self, dag_run: Any, task_ids: list[str]) -> dict[str, str]:
        states: dict[str, str] = {}
        for task_id in task_ids:
            try:
                ti = dag_run.get_task_instance(task_id) if dag_run else None
                states[task_id] = str(getattr(ti, "state", None) or "none")
            except Exception:
                states[task_id] = "unknown"
        return states

    def state_from_prev_success(self, *, ds: str, prev_end_date_success: Any) -> str:
        """
        Robust daily success signal based on Airflow-provided "previous successful run" fields.

        Note: this is NOT the current run's final state; it's intended for dashboards that
        want to know whether there has been a successful run for a given `ds` value.
        """
        prev_ds = None
        if prev_end_date_success:
            try:
                prev_ds = pendulum.instance(prev_end_date_success).to_date_string()
            except Exception:
                prev_ds = str(prev_end_date_success)[:10]

        if prev_end_date_success is None:
            return "no_prior_success"
        if prev_ds == ds:
            return "success"
        return "no_success_for_ds"

    def prev_success_snapshot(self, context: Mapping[str, Any]) -> dict[str, Any]:
        ds = str(context.get("ds") or "").strip()
        prev_data_interval_start_success = context.get("prev_data_interval_start_success")
        prev_data_interval_end_success = context.get("prev_data_interval_end_success")
        prev_start_date_success = context.get("prev_start_date_success")
        prev_end_date_success = context.get("prev_end_date_success")
        return {
            "ds": ds,
            "prev_data_interval_start_success": self._to_iso(prev_data_interval_start_success),
            "prev_data_interval_end_success": self._to_iso(prev_data_interval_end_success),
            "prev_start_date_success": self._to_iso(prev_start_date_success),
            "prev_end_date_success": self._to_iso(prev_end_date_success),
        }

    # -------------------------
    # Public: write log row
    # -------------------------
    def write_from_airflow_context(self, *, state: str, notes: Mapping[str, Any] | str | None = None) -> None:
        if get_current_context is None or Variable is None:  # pragma: no cover
            raise RuntimeError("Airflow context/Variable accessors are not available.")
        try:
            from google.cloud import bigquery
            from google.oauth2 import service_account
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("google-cloud-bigquery is not available.") from exc

        context = get_current_context()
        ti = context["ti"]
        dag_run = context.get("dag_run")

        table_id = Variable.get(
            self.config.logs_table_var,
            os.getenv(self.config.logs_table_var, self.config.logs_table_default),
        )
        if str(table_id).count(".") != 2:
            raise ValueError(f"{self.config.logs_table_var} must be fully-qualified project.dataset.table")

        ignore_errors_raw = Variable.get(
            self.config.ignore_errors_var,
            os.getenv(self.config.ignore_errors_var, "0"),
        )
        ignore_errors = str(ignore_errors_raw).strip().lower() in {"1", "true", "yes", "y", "on"}

        bq_secret = self._secret_helper.get_secret_resource(
            self.config.bq_secret_resource_var, self.config.bq_secret_resource_default
        )
        bq_sa = self._secret_helper.fetch_service_account_json(bq_secret)
        if not isinstance(bq_sa, dict):
            raise ValueError("BigQuery secret payload is not a JSON object")
        project_id = bq_sa.get("project_id")
        if not project_id:
            raise ValueError("BigQuery secret payload missing project_id")

        credentials = service_account.Credentials.from_service_account_info(bq_sa)
        client = bigquery.Client(credentials=credentials, project=project_id)

        logical_date = context.get("logical_date") or context.get("execution_date")
        start_ts = getattr(ti, "start_date", None)
        end_ts = getattr(ti, "end_date", None)
        duration_sec = None
        if start_ts and end_ts:
            try:
                duration_sec = int((end_ts - start_ts).total_seconds())
            except Exception:
                duration_sec = None

        notes_str: str | None
        if notes is None:
            notes_str = None
        elif isinstance(notes, str):
            notes_str = notes
        else:
            notes_str = json.dumps(self._safe_serialize(notes), sort_keys=True)

        row = {
            "log_id": uuid.uuid4().hex,
            "log_ts": datetime.now(timezone.utc).isoformat(),
            "dag_id": context["dag"].dag_id,
            "task_id": context["task"].task_id,
            "run_id": context.get("run_id") or (getattr(dag_run, "run_id", None) if dag_run else None),
            "map_index": int(getattr(ti, "map_index", -1) or -1),
            "try_number": int(getattr(ti, "try_number", 0) or 0),
            "state": str(state),
            "logical_date": self._to_iso(logical_date),
            "start_ts": self._to_iso(start_ts),
            "end_ts": self._to_iso(end_ts),
            "duration_sec": duration_sec,
            "hostname": getattr(ti, "hostname", None),
            "queue": getattr(ti, "queue", None),
            "pool": getattr(ti, "pool", None),
            "source": self.config.source,
            "notes": notes_str,
        }

        errors = client.insert_rows_json(str(table_id), [row])
        if errors:
            message = f"BigQuery insert_rows_json returned errors: {errors}"
            if ignore_errors:
                return
            raise RuntimeError(message)

    # -------------------------
    # Internal helpers
    # -------------------------
    def _to_iso(self, value: Any) -> str | None:
        if value is None:
            return None
        try:
            iso = object.__getattribute__(value, "isoformat")
        except Exception:
            iso = None
        if callable(iso):
            try:
                return iso()
            except Exception:
                return str(value)
        return str(value)

    def _safe_serialize(self, obj: Any, *, depth: int = 5, max_items: int = 200) -> Any:
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        if depth <= 0:
            return str(obj)
        if isinstance(obj, dict):
            out: dict[str, Any] = {}
            for i, (k, v) in enumerate(obj.items()):
                if i >= max_items:
                    out["__truncated__"] = True
                    break
                key = str(k)
                if any(s in key.lower() for s in ("password", "passwd", "secret", "token", "key", "credential")):
                    out[key] = "***REDACTED***"
                else:
                    out[key] = self._safe_serialize(v, depth=depth - 1, max_items=max_items)
            return out
        if isinstance(obj, (list, tuple, set)):
            items = list(obj)
            trimmed = items[:max_items]
            out_list = [self._safe_serialize(v, depth=depth - 1, max_items=max_items) for v in trimmed]
            if len(items) > max_items:
                out_list.append({"__truncated__": True, "__original_len__": len(items)})
            return out_list
        # Avoid triggering Airflow context accessors (e.g. var.value.foo).
        return str(obj)

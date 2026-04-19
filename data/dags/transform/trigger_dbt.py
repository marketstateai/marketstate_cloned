import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from airflow.sdk import dag, task
from google.oauth2 import service_account
from pendulum import datetime

from marketstate.marketstate_data.dags._lib.utils import SecretManagerHelper
logger = logging.getLogger(__name__)

BQ_SECRET_RESOURCE_VAR = "BQ_SECRET_RESOURCE"

secret_helper = SecretManagerHelper()


@dag(
    dag_id="trigger_dbt",
    start_date=datetime(2025, 4, 22),
    schedule=None,
    catchup=False,
    default_args={"owner": "MarketState", "retries": 2},
    tags=["marketstate", "dbt"],
)
def marketstate_dbt_run():
    def ensure_profiles() -> Path:
        project_root = Path(__file__).resolve().parent
        dbt_profiles_dir = Path("/usr/local/airflow/.dbt")
        repo_profiles_path = project_root.parent / ".dbt" / "profiles.yml"
        dbt_profiles_dir.mkdir(parents=True, exist_ok=True)
        profiles_path = dbt_profiles_dir / "profiles.yml"
        if repo_profiles_path.exists():
            if repo_profiles_path.resolve() != profiles_path.resolve():
                shutil.copyfile(repo_profiles_path, profiles_path)
        elif not profiles_path.exists():
            raise FileNotFoundError(
                f"Missing profiles.yml at {repo_profiles_path} or {profiles_path}"
            )
        return dbt_profiles_dir

    def write_bq_keyfile() -> tuple[dict, Path, tempfile.TemporaryDirectory]:
        secret_resource = secret_helper.get_secret_resource(
            BQ_SECRET_RESOURCE_VAR, "projects/318171260121/secrets/bigquery"
        )
        bq_sa = secret_helper.fetch_service_account_json(secret_resource)
        if not isinstance(bq_sa, dict):
            raise ValueError("BigQuery secret payload is not a JSON object")
        if not bq_sa.get("client_email") or not bq_sa.get("private_key"):
            raise ValueError("BigQuery secret payload missing required fields")

        keyfile_contents = json.dumps(bq_sa, indent=2)
        if not keyfile_contents.strip():
            raise ValueError("BigQuery keyfile payload is empty")
        tmp_dir = tempfile.TemporaryDirectory(prefix="dbt-bq-")
        keyfile_path = Path(tmp_dir.name) / "bigquery-creds.json"
        with keyfile_path.open("w", encoding="utf-8") as f:
            f.write(keyfile_contents)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(keyfile_path, 0o600)
        keyfile_size = keyfile_path.stat().st_size
        if keyfile_size == 0:
            tmp_dir.cleanup()
            raise ValueError(f"BigQuery keyfile write failed: {keyfile_path}")
        logger.info("DBT keyfile written (%s bytes)", keyfile_size)
        if not keyfile_path.exists():
            tmp_dir.cleanup()
            raise FileNotFoundError(f"Missing BigQuery keyfile at {keyfile_path}")
        if not os.access(keyfile_path, os.R_OK):
            tmp_dir.cleanup()
            raise PermissionError(f"BigQuery keyfile not readable: {keyfile_path}")
        logger.info(
            "DBT keyfile identity: %s (project_id=%s)",
            bq_sa.get("client_email"),
            bq_sa.get("project_id"),
        )
        return bq_sa, keyfile_path, tmp_dir

    def discover_models(dbt_project_dir: Path) -> list[str]:
        models_dir = dbt_project_dir / "models"
        if not models_dir.exists():
            raise FileNotFoundError(f"Missing dbt models directory: {models_dir}")
        model_files = sorted(path for path in models_dir.rglob("*.sql") if path.is_file())
        model_names = [path.stem for path in model_files]
        if not model_names:
            raise ValueError(f"No dbt model files found under {models_dir}")
        duplicates = {name for name in model_names if model_names.count(name) > 1}
        if duplicates:
            raise ValueError(f"Duplicate dbt model names found: {sorted(duplicates)}")
        return model_names

    def model_task_id(model_name: str) -> str:
        sanitized = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in model_name)
        return f"{sanitized}_build"

    @task
    def run_model(model_name: str) -> None:
        project_root = Path(__file__).resolve().parent
        dbt_project_dir = project_root.parent / "dbt" / "marketstate"
        dbt_profiles_dir = ensure_profiles()
        _, keyfile_path, tmp_dir = write_bq_keyfile()
        try:
            run_cmd = [
                "dbt",
                "build",
                "--project-dir",
                str(dbt_project_dir),
                "--profiles-dir",
                str(dbt_profiles_dir),
                "--target",
                "prod",
                "--target-path",
                "/tmp/dbt-target",
                "--select",
                model_name,
            ]
            env = os.environ.copy()
            env["DBT_BQ_KEYFILE"] = str(keyfile_path)
            logger.info("Running model %s: %s", model_name, " ".join(run_cmd))
            subprocess.run(run_cmd, check=True, env=env)
        finally:
            tmp_dir.cleanup()

    project_root = Path(__file__).resolve().parent
    dbt_project_dir = project_root.parent / "dbt" / "marketstate"
    for model_name in discover_models(dbt_project_dir):
        run_model.override(task_id=model_task_id(model_name))(model_name=model_name)


marketstate_dbt_run()

import base64
import json
import os

from airflow.sdk import Variable


class SecretManagerHelper:
    SECRET_MANAGER_CREDENTIALS_ENV = "GOOGLE_SECRET_MANAGER_CREDENTIALS"
    SECRET_MANAGER_CREDENTIALS_B64_ENV = "GOOGLE_SECRET_MANAGER_CREDENTIALS_B64"
    DEFAULT_SECRET_MANAGER_CREDENTIALS = "/usr/local/airflow/.dbt/gcp-secrets.json"

    def _load_service_account_info(self, value: str) -> dict:
        if os.path.isfile(value):
            with open(value, "r", encoding="utf-8") as handle:
                return json.load(handle)
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
        try:
            decoded = base64.b64decode(value).decode("utf-8")
            return json.loads(decoded)
        except Exception as exc:
            raise ValueError(
                "Secret manager credentials must be JSON, base64-encoded JSON, or a JSON file path."
            ) from exc

    def _get_secret_manager_credentials(self):
        from google.oauth2 import service_account

        raw = os.getenv(self.SECRET_MANAGER_CREDENTIALS_ENV) or os.getenv(
            self.SECRET_MANAGER_CREDENTIALS_B64_ENV
        )
        if raw:
            info = self._load_service_account_info(raw)
            return service_account.Credentials.from_service_account_info(info)
        explicit_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if (
            explicit_path
            and os.path.isfile(explicit_path)
            and os.access(explicit_path, os.R_OK)
        ):
            return service_account.Credentials.from_service_account_file(explicit_path)
        if os.path.isfile(self.DEFAULT_SECRET_MANAGER_CREDENTIALS) and os.access(
            self.DEFAULT_SECRET_MANAGER_CREDENTIALS, os.R_OK
        ):
            return service_account.Credentials.from_service_account_file(
                self.DEFAULT_SECRET_MANAGER_CREDENTIALS
            )
        return None

    def fetch_service_account_json(self, secret_resource: str) -> dict:
        from google.cloud import secretmanager

        credentials = self._get_secret_manager_credentials()
        if credentials:
            client = secretmanager.SecretManagerServiceClient(credentials=credentials)
        else:
            client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(
            request={"name": f"{secret_resource}/versions/latest"}
        )
        return json.loads(response.payload.data.decode("utf-8"))

    def get_secret_resource(self, var_name: str, default_value: str) -> str:
        value = Variable.get(var_name, default_value)
        if not value:
            raise ValueError(f"Airflow Variable {var_name} is empty")
        return value

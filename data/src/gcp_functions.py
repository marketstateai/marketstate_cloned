from google.oauth2 import service_account
from google.cloud.bigquery import Client
from google.cloud import secretmanager, storage

import os
from json import loads, load

from pandas import DataFrame

import os
import json

import os
import json
import base64
from google.oauth2 import service_account
from google.cloud import secretmanager


class GCP:
    def __init__(self):
        self.GOOGLE_SECRET_MANAGER_CREDENTIALS = self._get_credentials_value()
        self.project_id = self.GOOGLE_SECRET_MANAGER_CREDENTIALS.get("project_id")
        self.default_zone = "us-central1-a"

    def _get_credentials_value(self):
        value = os.getenv("GOOGLE_SECRET_MANAGER_CREDENTIALS")
        # print(value)
        if not value:
            raise EnvironmentError(
                "Environment variable 'GOOGLE_SECRET_MANAGER_CREDENTIALS' is not set. "
                "Please set it to either the raw JSON string or base64-encoded JSON for your credentials."
            )

        value = value.strip()

        # If it's a file path, load it directly.
        if os.path.isfile(value):
            with open(value, "r") as f:
                return json.load(f)

        # If it's a quoted JSON string, strip the wrapping quotes.
        if (value[0] == value[-1]) and value[0] in ("'", '"'):
            value = value[1:-1].strip()

        # Try plain JSON first
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass  # fall back to base64

        # Try Python literal dict (single quotes)
        try:
            import ast
            literal = ast.literal_eval(value)
            if isinstance(literal, dict):
                return literal
        except Exception:
            pass

        # Try base64-decoding
        try:
            decoded = base64.b64decode(value).decode("utf-8")
            return json.loads(decoded)
        except Exception as e:
            raise ValueError(
                "Environment variable 'GOOGLE_SECRET_MANAGER_CREDENTIALS' is not valid JSON "
                "or valid base64-encoded JSON."
            ) from e

    def get_credentials_from_secret_manager(self, secret_id, version_id, secret_manager_service_account):
        # Auth to Secret Manager with GCP credentials
        credentials = service_account.Credentials.from_service_account_info(secret_manager_service_account)
        client = secretmanager.SecretManagerServiceClient(credentials=credentials)
        name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version_id}"

        response = client.access_secret_version(name=name)
        secret_data = response.payload.data.decode("utf-8")

        # Try to parse JSON
        try:
            secret_dict = json.loads(secret_data)
        except json.JSONDecodeError:
            # If it’s not JSON, just return raw string
            return secret_data

        # Detect if it's a service account JSON
        if all(k in secret_dict for k in ["client_email", "token_uri", "private_key"]):
            return service_account.Credentials.from_service_account_info(secret_dict)

        # Otherwise, it's probably app creds like Postgres
        return secret_dict


    def bq_to_df(self, credentials: str, query: str) -> DataFrame:
        client = Client(credentials=credentials, project=self.project_id)
        query_job = client.query(query)
        results = query_job.result()
        return results.to_dataframe()


    def df_to_bq(self, df: DataFrame, table_id: str, credentials: str, if_exists="append"):
        from pandas_gbq import to_gbq
        to_gbq(df, table_id, project_id=self.project_id, if_exists=if_exists, credentials=credentials)


    def upload_file_to_bucket(self, bucket_name, source_file_name, destination_blob_name, credentials=None):
        """
        Uploads a file to the specified Google Cloud Storage bucket using the provided credentials.
        
        Args:
            bucket_name (str): Name of the GCS bucket.
            source_file_name (str): Local path to the file to be uploaded.
            destination_blob_name (str): The desired object name in the bucket.
            credentials (google.auth.credentials.Credentials, optional): Credentials for authentication.
        """
        try:
            # If credentials are provided, use them when creating the storage client.
            if credentials:
                storage_client = storage.Client(credentials=credentials)
            else:
                storage_client = storage.Client()
                
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_filename(source_file_name)
            print(f"File '{source_file_name}' uploaded to '{bucket_name}/{destination_blob_name}'.")
        except Exception as e:
            print(f"Error uploading file: {e}")


    def get_bq_commands():
        cmc = """
                CREATE OR REPLACE EXTERNAL TABLE `propane-dogfish-418716.coinmarketcap.coinmarketcap_external`
                OPTIONS (
                    format ="PARQUET",
                    uris = ['gs://coin_market_cap/coinMarketCapDaily_*.parquet']
                    );

                SELECT 
                    substr(pk, 1, 10) AS extraction_date,
                    REGEXP_EXTRACT(pk, r'page-(\d+)-') AS page_number,
                    REGEXP_EXTRACT(pk, r'idx-(\d+)') AS idx,
                    *
                FROM `propane-dogfish-418716.coinmarketcap.coinmarketcap_external`
            """
        
        indexes = """
                    CREATE OR REPLACE EXTERNAL TABLE `propane-dogfish-418716.coinmarketcap.coinmarketcap_external`
                    OPTIONS (
                        format ="PARQUET",
                        uris = ['gs://coin_market_cap/coinMarketCapDaily_*.parquet']
                        );


                    SELECT 
                        substr(pk, 1, 10) AS extraction_date,
                        REGEXP_EXTRACT(pk, r'page-(\d+)-') AS page_number,
                        REGEXP_EXTRACT(pk, r'idx-(\d+)') AS idx,
                        *
                    FROM `propane-dogfish-418716.coinmarketcap.coinmarketcap_external`
                    """

        return {'indexes': indexes, 'cmc':cmc}

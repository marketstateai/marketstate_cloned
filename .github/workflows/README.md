# Workflow Index

- `ci-currency-api.yml`: PR/main CI for `services/core/apis/currency-api` (lint, tests, Docker build).
- `currency-deploy.yml`: Manual production deploy of currency API as a Cloud Function (Gen2), including Artifact Registry repository management for build images.
- `test-data-dags.yml`: PR tests for Airflow DAG code in `data/`.
- `deploy-airflow-vm.yml`: Manual Airflow VM provisioning/deploy workflow.

Naming convention:
- `ci-*`: continuous integration checks.
- `test-*`: targeted test workflows.
- `deploy-*`: release/provision workflows.

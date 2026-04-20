#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TFVARS_FILE="$SCRIPT_DIR/terraform.tfvars"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
SOURCE_DIR="${SOURCE_DIR_OVERRIDE:-$REPO_ROOT/services/core/apis/currency-api}"

if [[ ! -f "$TFVARS_FILE" ]]; then
  echo "Missing terraform.tfvars at $TFVARS_FILE"
  exit 1
fi

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Missing source directory: $SOURCE_DIR"
  exit 1
fi

read_tfvar() {
  local key="$1"
  awk -F'=' -v k="$key" '$1 ~ "^"k"[[:space:]]*$" {gsub(/^[ \t\"]+|[ \t\"]+$/, "", $2); print $2}' "$TFVARS_FILE" | tail -n 1
}

PROJECT_ID="$(read_tfvar project_id)"
REGION="$(read_tfvar region)"
REPO_NAME="$(read_tfvar artifact_repo_name)"
SERVICE_NAME="$(read_tfvar service_name)"

if [[ -z "$PROJECT_ID" || -z "$REGION" || -z "$REPO_NAME" || -z "$SERVICE_NAME" ]]; then
  echo "project_id, region, artifact_repo_name, and service_name must be set in terraform.tfvars"
  exit 1
fi

TIMESTAMP_TAG="$(date +%Y%m%d-%H%M%S)"
IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE_NAME}:${TIMESTAMP_TAG}"

gcloud services enable artifactregistry.googleapis.com cloudbuild.googleapis.com run.googleapis.com --project "$PROJECT_ID"

if ! gcloud artifacts repositories describe "$REPO_NAME" --location "$REGION" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPO_NAME" \
    --repository-format=docker \
    --location "$REGION" \
    --project "$PROJECT_ID" \
    --description="Docker repo for currency-api"
fi

gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

gcloud builds submit "$SOURCE_DIR" --tag "$IMAGE_URL" --project "$PROJECT_ID"

echo "$IMAGE_URL"

# Terraform Basics: Currency API on GCP (Container)

This folder is self-contained and deploys your Dockerized API with Terraform.

## Why Cloud Run, not Cloud Functions, for this image

You asked for Cloud Functions, but for an arbitrary prebuilt Docker image, the direct serverless target is Cloud Run. Cloud Functions Gen2 is source-driven; Cloud Run is image-driven.

## What this creates

- Artifact Registry Docker repository
- Cloud Run service (public)
- Required APIs (`run`, `artifactregistry`, `cloudbuild`)

## Inputs

`terraform.tfvars` is already set for your project:

- `project_id = "general-428410"`
- region/service/repo defaults

## Deploy (fast path)

```bash
cd /Users/gabrielzenkner/projects/marketstate/ops/infra/terraform/gcp/currency-api-cloudrun
gcloud auth application-default login
gcloud auth login
./deploy.sh
```

`deploy.sh` does:
1. Build and push image from `/Users/gabrielzenkner/projects/marketstate/services/core/apis/currency-api`
2. `terraform init/validate/plan/apply`
3. Print `service_url`

Optional: override API source directory when needed:

```bash
SOURCE_DIR_OVERRIDE=/absolute/path/to/api ./deploy.sh
```

## Terraform essentials

```bash
terraform init
terraform plan -var-file=terraform.tfvars -var-file=terraform.tfvars.runtime
terraform apply -var-file=terraform.tfvars -var-file=terraform.tfvars.runtime
terraform output service_url
```

## Tear down

```bash
./destroy.sh
```

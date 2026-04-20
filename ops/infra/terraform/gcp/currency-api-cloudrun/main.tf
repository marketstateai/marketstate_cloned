terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com"
  ])

  project = var.project_id
  service = each.value

  disable_on_destroy = false
}

data "google_artifact_registry_repository" "api_repo" {
  location      = var.region
  repository_id = var.artifact_repo_name

  depends_on = [google_project_service.required_apis]
}

resource "google_cloud_run_v2_service" "currency_api" {
  name     = var.service_name
  location = var.region

  template {
    containers {
      image = var.image_url

      ports {
        container_port = var.container_port
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
  }

  depends_on = [
    google_project_service.required_apis,
    data.google_artifact_registry_repository.api_repo
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.currency_api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

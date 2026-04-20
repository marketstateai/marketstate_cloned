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

resource "google_cloud_run_v2_service" "currency_api" {
  name     = var.service_name
  location = var.region

  template {
    containers {
      image = var.image_url

      ports {
        container_port = var.container_port
      }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.currency_api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

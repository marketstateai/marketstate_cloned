variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "currency-api"
}

variable "artifact_repo_name" {
  description = "Artifact Registry Docker repo name"
  type        = string
  default     = "currency-api-repo"
}

variable "image_url" {
  description = "Full container image URL, including tag"
  type        = string
}

variable "container_port" {
  description = "Container port exposed by the app"
  type        = number
  default     = 8000
}

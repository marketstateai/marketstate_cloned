output "service_name" {
  value = google_cloud_run_v2_service.currency_api.name
}

output "service_url" {
  value = google_cloud_run_v2_service.currency_api.uri
}

output "artifact_repo" {
  value = data.google_artifact_registry_repository.api_repo.name
}

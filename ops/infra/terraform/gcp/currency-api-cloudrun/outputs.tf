output "service_name" {
  value = google_cloud_run_v2_service.currency_api.name
}

output "service_url" {
  value = google_cloud_run_v2_service.currency_api.uri
}

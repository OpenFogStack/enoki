output "cloud_ip" {
  value = google_compute_instance.enoki-cloud.network_interface.0.access_config.0.nat_ip
}

output "edge_ip" {
  value = google_compute_instance.enoki-edge.network_interface.0.access_config.0.nat_ip
}

output "edge2_ip" {
  value = var.second_edge_host ? google_compute_instance.enoki-edge2[0].network_interface.0.access_config.0.nat_ip : ""
}

output "client_ip" {
  value = google_compute_instance.enoki-client.network_interface.0.access_config.0.nat_ip
}

output "cloud_name" {
  value = format("%s.%s.%s", google_compute_instance.enoki-cloud.name, local.zone, var.gcp_project)
}

output "edge_name" {
  value = format("%s.%s.%s", google_compute_instance.enoki-edge.name, local.zone, var.gcp_project)
}

output "edge2_name" {
  value = var.second_edge_host ? format("%s.%s.%s", google_compute_instance.enoki-edge2[0].name, local.zone, var.gcp_project) : ""
}

output "client_name" {
  value = format("%s.%s.%s", google_compute_instance.enoki-client.name, local.zone, var.gcp_project)
}

output "client_id" {
  value = google_compute_instance.enoki-client.name
}

output "edge_id" {
  value = google_compute_instance.enoki-edge.name
}

output "edge2_id" {
  value = var.second_edge_host ? google_compute_instance.enoki-edge2[0].name : ""
}

output "cloud_id" {
  value = google_compute_instance.enoki-cloud.name
}

output "zone" {
  value = local.zone
}

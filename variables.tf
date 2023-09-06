variable "gcp_project" {
  default = "INSERT YOUR GCP PROJECT ID HERE"
}

variable "gcp_region" {
  default = "europe-west9"
}

variable "gcp_zone" {
  default = "a"
}

variable "cloud_host_type" {
  default = "n2-standard-4"
}

variable "edge_host_type" {
  default = "n2-standard-2"
}

variable "client_host_type" {
  default = "n2-standard-2"
}

# change this only if you know what you're doing!
variable "image_family" {
  default = "debian-11"
}

variable "image_project" {
  default = "debian-cloud"
}

variable "boot_disk_size_gb" {
  default = 20
}

variable "second_edge_host" {
  default = false
}

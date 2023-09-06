provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

# the zone variable must be within the region
# hence this weird setup
locals {
  zone = "${var.gcp_region}-${var.gcp_zone}"
}

# this data item gives us the latest available image
data "google_compute_image" "host-image" {
  family  = var.image_family
  project = var.image_project
}

# we want our instances to be able to talk to each other directly
# hence we add them all to a dedicated network
resource "google_compute_network" "enoki-network" {
  name                    = "enoki-network"
  description             = "connections between hosts"
  auto_create_subnetworks = false
}

# within our network, we need a subnet for this region that has the correct
# IP address range
resource "google_compute_subnetwork" "enoki-subnet" {
  name          = "enoki-subnetwork"
  ip_cidr_range = "192.168.10.0/24"
  region        = var.gcp_region
  network       = google_compute_network.enoki-network.id
}

# # we need to explicitly enable communication between instances in that network
# # as google cloud doesn't add any rules by default
# resource "google_compute_firewall" "enoki-net-firewall-internal" {
#   name          = "enoki-net-firewall-internal"
#   description   = "This firewall allows internal communication in the network."
#   direction     = "INGRESS"
#   network       = google_compute_network.enoki-network.id
#   source_ranges = ["${google_compute_subnetwork.enoki-subnet.ip_cidr_range}"]

#   allow {
#     protocol = "all"
#   }
# }

# we also need to enable ssh ingress to our machines
resource "google_compute_firewall" "enoki-net-firewall-ssh" {
  name          = "enoki-net-firewall-ssh"
  description   = "This firewall allows ssh connections to our instances."
  network       = google_compute_network.enoki-network.id
  direction     = "INGRESS"
  source_ranges = ["0.0.0.0/0"]

  allow {
    protocol = "tcp"
    # ports:
    ## 22: ssh
    ## 2379: etcd
    ## 8000: tinyfaas rproxy http
    ## 8080: tinyfaas manager
    ## 9001: fred
    ## 5555: fred peering
    ports = ["22", "2379", "8000", "8080", "9001", "5555"]
  }
}

# the cloud instance runs Ubuntu 22.04 and has Docker installed
resource "google_compute_instance" "enoki-cloud" {
  name         = "enoki-cloud"
  machine_type = var.cloud_host_type
  zone         = local.zone

  boot_disk {

    initialize_params {
      image = data.google_compute_image.host-image.self_link
      size  = var.boot_disk_size_gb
    }
  }

  # adapter for internal network
  network_interface {
    subnetwork = google_compute_subnetwork.enoki-subnet.self_link
    network_ip = "192.168.10.2"
    # put this empty block in to get a public IP
    access_config {
    }
  }

  service_account {
    scopes = ["cloud-platform"]
  }
}

# the edge instance runs Ubuntu 22.04 and has Docker installed
resource "google_compute_instance" "enoki-edge" {
  name         = "enoki-edge"
  machine_type = var.edge_host_type
  zone         = local.zone

  boot_disk {

    initialize_params {
      image = data.google_compute_image.host-image.self_link
      size  = var.boot_disk_size_gb
    }
  }

  # adapter for internal network
  network_interface {
    subnetwork = google_compute_subnetwork.enoki-subnet.self_link
    network_ip = "192.168.10.3"
    # put this empty block in to get a public IP
    access_config {
    }
  }

  service_account {
    scopes = ["cloud-platform"]
  }
}

resource "google_compute_instance" "enoki-edge2" {
  name         = "enoki-edge2"
  machine_type = var.edge_host_type
  zone         = local.zone

  # only create this instance if the variable is set to true
  count = var.second_edge_host ? 1 : 0

  boot_disk {

    initialize_params {
      image = data.google_compute_image.host-image.self_link
      size  = var.boot_disk_size_gb
    }
  }

  # adapter for internal network
  network_interface {
    subnetwork = google_compute_subnetwork.enoki-subnet.self_link
    network_ip = "192.168.10.5"
    # put this empty block in to get a public IP
    access_config {
    }
  }

  service_account {
    scopes = ["cloud-platform"]
  }
}

# the edge instance runs Ubuntu 22.04 and has nothing installed
resource "google_compute_instance" "enoki-client" {
  name         = "enoki-client"
  machine_type = var.client_host_type
  zone         = local.zone

  boot_disk {

    initialize_params {
      image = data.google_compute_image.host-image.self_link
      size  = var.boot_disk_size_gb
    }
  }

  # adapter for internal network
  network_interface {
    subnetwork = google_compute_subnetwork.enoki-subnet.self_link
    network_ip = "192.168.10.4"
    # put this empty block in to get a public IP
    access_config {
    }
  }

  service_account {
    scopes = ["cloud-platform"]
  }
}

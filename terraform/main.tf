provider "google" {
  project = "project-b1dc10c3-bdd6-4c36-b35"
  region  = "europe-west1"
  zone    = "europe-west1-b"
}

resource "google_compute_network" "default" {
  name                             = "default"
  project                          = "project-b1dc10c3-bdd6-4c36-b35"
  auto_create_subnetworks          = true
  description                      = "Default network for the project"
  routing_mode                     = "REGIONAL"
  delete_default_routes_on_create  = false
}

resource "google_compute_instance" "aiot_master" {
  name         = "aiot-master"
  project      = "project-b1dc10c3-bdd6-4c36-b35"
  zone         = "europe-west1-b"
  machine_type = "e2-standard-8"
  tags         = ["k8s-master"]

  boot_disk {
    auto_delete = true
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 100
      type  = "pd-ssd"
    }
  }

  network_interface {
    network    = google_compute_network.default.self_link
    network_ip = "10.132.0.6"
    access_config {}
  }

  service_account {
    email = "305678698065-compute@developer.gserviceaccount.com"
    scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring.write",
      "https://www.googleapis.com/auth/pubsub",
      "https://www.googleapis.com/auth/service.management.readonly",
      "https://www.googleapis.com/auth/servicecontrol",
      "https://www.googleapis.com/auth/trace.append",
    ]
  }

  shielded_instance_config {
    enable_integrity_monitoring = true
    enable_secure_boot          = false
    enable_vtpm                 = true
  }

  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
    preemptible         = false
  }
}

resource "google_compute_instance" "aiot_worker_01" {
  name         = "aiot-worker-01"
  project      = "project-b1dc10c3-bdd6-4c36-b35"
  zone         = "europe-west1-b"
  machine_type = "e2-standard-2"
  tags         = ["k8s-worker"]

  boot_disk {
    auto_delete = true
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 100
      type  = "pd-ssd"
    }
  }

  network_interface {
    network    = google_compute_network.default.self_link
    network_ip = "10.132.0.7"
    access_config {}
  }

  service_account {
    email = "305678698065-compute@developer.gserviceaccount.com"
    scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring.write",
      "https://www.googleapis.com/auth/pubsub",
      "https://www.googleapis.com/auth/service.management.readonly",
      "https://www.googleapis.com/auth/servicecontrol",
      "https://www.googleapis.com/auth/trace.append",
    ]
  }

  shielded_instance_config {
    enable_integrity_monitoring = true
    enable_secure_boot          = false
    enable_vtpm                 = true
  }

  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
    preemptible         = false
  }
}

resource "google_compute_instance" "aiot_worker_02" {
  name         = "aiot-worker-02"
  project      = "project-b1dc10c3-bdd6-4c36-b35"
  zone         = "europe-west1-b"
  machine_type = "e2-standard-2"
  tags         = ["k8s-worker"]

  boot_disk {
    auto_delete = true
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 100
      type  = "pd-standard"
    }
  }

  network_interface {
    network    = google_compute_network.default.self_link
    network_ip = "10.132.0.9"
    access_config {}
  }

  service_account {
    email = "305678698065-compute@developer.gserviceaccount.com"
    scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring.write",
      "https://www.googleapis.com/auth/pubsub",
      "https://www.googleapis.com/auth/service.management.readonly",
      "https://www.googleapis.com/auth/servicecontrol",
      "https://www.googleapis.com/auth/trace.append",
    ]
  }

  shielded_instance_config {
    enable_integrity_monitoring = true
    enable_secure_boot          = false
    enable_vtpm                 = true
  }

  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
    preemptible         = false
  }
}

resource "google_compute_firewall" "aiot_cloudbeaver" {
  name          = "aiot-cloudbeaver"
  project       = "project-b1dc10c3-bdd6-4c36-b35"
  network       = google_compute_network.default.self_link
  direction     = "INGRESS"
  priority      = 1000
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["aiot"]

  allow {
    protocol = "tcp"
    ports    = ["31978"]
  }
}

resource "google_compute_firewall" "allow_all_k8s_internal" {
  name          = "allow-all-k8s-internal"
  project       = "project-b1dc10c3-bdd6-4c36-b35"
  network       = google_compute_network.default.self_link
  direction     = "INGRESS"
  priority      = 100
  description   = "Allow all traffic between K8s nodes - test env"
  source_ranges = ["10.132.0.0/20"]

  allow {
    protocol = "all"
  }
}

resource "google_compute_firewall" "allow_signoz_nodeport" {
  name          = "allow-signoz-nodeport"
  project       = "project-b1dc10c3-bdd6-4c36-b35"
  network       = google_compute_network.default.self_link
  direction     = "INGRESS"
  priority      = 1000
  source_ranges = ["0.0.0.0/0"]

  allow {
    protocol = "tcp"
    ports    = ["30255"]
  }
}

resource "google_compute_firewall" "default_allow_icmp" {
  name          = "default-allow-icmp"
  project       = "project-b1dc10c3-bdd6-4c36-b35"
  network       = google_compute_network.default.self_link
  direction     = "INGRESS"
  priority      = 65534
  description   = "Allow ICMP from anywhere"
  source_ranges = ["0.0.0.0/0"]

  allow {
    protocol = "icmp"
  }
}

resource "google_compute_firewall" "default_allow_internal" {
  name          = "default-allow-internal"
  project       = "project-b1dc10c3-bdd6-4c36-b35"
  network       = google_compute_network.default.self_link
  direction     = "INGRESS"
  priority      = 65534
  description   = "Allow internal traffic on the default network"
  source_ranges = ["10.128.0.0/9"]

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }
}

resource "google_compute_firewall" "default_allow_rdp" {
  name          = "default-allow-rdp"
  project       = "project-b1dc10c3-bdd6-4c36-b35"
  network       = google_compute_network.default.self_link
  direction     = "INGRESS"
  priority      = 65534
  description   = "Allow RDP from anywhere"
  source_ranges = ["0.0.0.0/0"]

  allow {
    protocol = "tcp"
    ports    = ["3389"]
  }
}

resource "google_compute_firewall" "default_allow_ssh" {
  name          = "default-allow-ssh"
  project       = "project-b1dc10c3-bdd6-4c36-b35"
  network       = google_compute_network.default.self_link
  direction     = "INGRESS"
  priority      = 65534
  description   = "Allow SSH from anywhere"
  source_ranges = ["0.0.0.0/0"]

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

resource "google_compute_firewall" "k8s_external" {
  name          = "k8s-external"
  project       = "project-b1dc10c3-bdd6-4c36-b35"
  network       = google_compute_network.default.self_link
  direction     = "INGRESS"
  priority      = 1000
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["k8s-master", "k8s-worker"]

  allow {
    protocol = "tcp"
    ports    = ["30000-32767"]
  }

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  allow {
    protocol = "tcp"
    ports    = ["6443"]
  }

  allow {
    protocol = "tcp"
    ports    = ["80"]
  }
}

resource "google_compute_firewall" "k8s_internal" {
  name        = "k8s-internal"
  project     = "project-b1dc10c3-bdd6-4c36-b35"
  network     = google_compute_network.default.self_link
  direction   = "INGRESS"
  priority    = 1000
  source_tags = ["k8s-master", "k8s-worker"]
  target_tags = ["k8s-master", "k8s-worker"]

  allow {
    protocol = "icmp"
  }

  allow {
    protocol = "tcp"
  }

  allow {
    protocol = "udp"
  }
}

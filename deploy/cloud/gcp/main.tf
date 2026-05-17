terraform {
  required_providers {
    google = { source = "hashicorp/google" }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_cloud_run_service" "osint" {
  name     = "osint-framework"
  location = var.region

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/osint-framework:latest"
        env {
          name  = "DATABASE_URL"
          value = var.database_url
        }
        ports { container_port = 8000 }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_cloud_run_service_iam_member" "all_users" {
  service  = google_cloud_run_service.osint.name
  location = google_cloud_run_service.osint.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
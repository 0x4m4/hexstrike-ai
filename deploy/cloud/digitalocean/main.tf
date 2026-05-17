terraform {
  required_providers {
    digitalocean = { source = "digitalocean/digitalocean" }
  }
}

provider "digitalocean" { token = var.do_token }

resource "digitalocean_app" "osint" {
  name   = "osint-framework"
  region = var.region

  spec {
    service {
      name               = "osint-framework"
      instance_limit     = 1
      instance_size_slug = "basic-xxs"
      
      image {
        registry_type = "DOCKERHUB"
        repository    = "osint-framework"
        tag           = "latest"
      }
      
      http_port = 8000
      
      env {
        key   = "DATABASE_URL"
        value = var.database_url
      }
    }
  }
}
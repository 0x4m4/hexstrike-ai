terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
  }
}

provider "azurerm" { features = {} }

resource "azurerm_resource_group" "osint" {
  name     = "osint-framework-rg"
  location = var.location
}

resource "azurerm_container_app" "osint" {
  name                = "osint-framework"
  resource_group_name = azurerm_resource_group.osint.name
  location           = var.location
  ingress_external_enabled = true
  
  container {
    image   = "osint-framework:latest"
    name    = "osint-framework"
    env {
      name  = "DATABASE_URL"
      value = var.database_url
    }
    ports { port = 8000 }
  }
}
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs"
  type        = list(string)
}

variable "database_url" {
  description = "Database URL"
  type        = string
  default     = "sqlite+aiosqlite:///app/data/osint.db"
}
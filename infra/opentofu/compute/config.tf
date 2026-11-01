terraform {
  required_version = ">= 1.11.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
  backend "local" {}
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
  default_tags {
    tags = {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "OpenTofu"
    }
  }
}

variable "account_id" {
  type    = string
  default = "222234418877"
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "account_id requiere 12 digitos."
  }
}
variable "region" {
  type    = string
  default = "us-east-2"
}
variable "project" {
  type    = string
  default = "asistencia"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,29}$", var.project))
    error_message = "Nombre de proyecto invalido."
  }
}
variable "environment" {
  type    = string
  default = "cloudinit-opentofu"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,29}$", var.environment))
    error_message = "Nombre de entorno invalido."
  }
}
locals {
  suffix = "${var.project}-${var.environment}"
}

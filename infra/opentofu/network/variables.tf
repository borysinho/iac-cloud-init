variable "ssh_source_cidr" {
  type        = string
  description = "IP publica administrativa actual con mascara /32."
  validation {
    condition     = can(cidrnetmask(var.ssh_source_cidr)) && endswith(var.ssh_source_cidr, "/32")
    error_message = "SSH requiere una IPv4 /32."
  }
}
variable "web_source_cidr" {
  type        = string
  default     = "0.0.0.0/0"
  description = "HTTP publico, conservando la configuracion de CloudFormation."
  validation {
    condition     = can(cidrnetmask(var.web_source_cidr))
    error_message = "Se requiere un CIDR IPv4 valido."
  }
}
variable "availability_zone" {
  type        = string
  default     = null
  description = "AZ opcional; por defecto la primera disponible."
}

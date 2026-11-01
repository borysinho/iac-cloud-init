variable "network_state_path" {
  type        = string
  default     = null
  description = "Estado local de network; por defecto ../network/terraform.tfstate."
}
variable "ssh_public_key_path" {
  type        = string
  default     = "~/globomatics-ec2.pub"
  description = "Ruta de la clave PUBLICA OpenSSH."
  validation {
    condition     = can(regex("^ssh-(ed25519|rsa) [A-Za-z0-9+/]+={0,3}( [^\\r\\n]+)?$", trimspace(file(pathexpand(var.ssh_public_key_path)))))
    error_message = "El archivo debe existir y contener una clave publica OpenSSH."
  }
}
variable "app_revision" {
  type    = string
  default = "9e4d440276547607498f8aa3342c6234bb030f45"
  validation {
    condition     = can(regex("^[a-f0-9]{40}$", var.app_revision))
    error_message = "app_revision debe ser un commit publicado de 40 caracteres."
  }
}
variable "ami_parameter" {
  type    = string
  default = "/aws/service/canonical/ubuntu/server/noble/stable/current/amd64/hvm/ebs-gp3/ami-id"
}

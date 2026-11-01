data "terraform_remote_state" "network" {
  backend = "local"
  config = {
    path = var.network_state_path == null ? abspath("${path.module}/../network/terraform.tfstate") : abspath(pathexpand(var.network_state_path))
  }
}
data "aws_ssm_parameter" "ami" {
  name = var.ami_parameter
}
locals {
  network = data.terraform_remote_state.network.outputs.deployment
  # file + replace evita interpretar ${...} de Bash/Python como sintaxis de OpenTofu.
  cloud_init_source = file("${path.module}/../../cloud-init.yaml")
  app_archive_url   = "https://github.com/borysinho/iac-cloud-init/archive/${var.app_revision}.tar.gz"
  common_user_data  = replace(local.cloud_init_source, "__APP_ARCHIVE_URL__", local.app_archive_url)
}
resource "aws_key_pair" "app" {
  key_name_prefix = "key-${local.suffix}-"
  public_key      = trimspace(file(pathexpand(var.ssh_public_key_path)))
  tags            = { Name = "key-${local.suffix}" }
}
resource "aws_instance" "client" {
  ami                         = nonsensitive(data.aws_ssm_parameter.ami.value)
  instance_type               = "t3.micro"
  key_name                    = aws_key_pair.app.key_name
  subnet_id                   = local.network.public_subnet_id
  private_ip                  = "10.42.1.10"
  associate_public_ip_address = true
  vpc_security_group_ids      = [local.network.client_security_group_id]
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }
  credit_specification { cpu_credits = "standard" }
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 12
    encrypted             = true
    delete_on_termination = true
  }
  user_data                   = replace(local.common_user_data, "__FRONTEND_ORIGIN__", "http://127.0.0.1")
  user_data_replace_on_change = false
  tags                        = { Name = "ec2-cliente-${local.suffix}", Role = "client" }
  lifecycle {
    precondition {
      condition     = local.network.ready && local.network.account_id == var.account_id && local.network.region == var.region && local.network.project == var.project && local.network.environment == var.environment
      error_message = "Completar network y conservar cuenta, region, proyecto y entorno iguales en ambas configuraciones."
    }
    precondition {
      condition     = length(regexall("__APP_ARCHIVE_URL__", local.cloud_init_source)) == 1 && length(regexall("__FRONTEND_ORIGIN__", local.cloud_init_source)) == 1 && startswith(local.cloud_init_source, "#cloud-config\n")
      error_message = "La fuente cloud-init requiere una unica entrada para URL y origen."
    }
    precondition {
      condition     = length(base64encode(local.common_user_data)) / 4 * 3 + 1024 <= 16384
      error_message = "UserData requiere espacio para las entradas resueltas bajo el limite EC2 de 16 KiB."
    }
  }
}
resource "aws_instance" "backend" {
  ami                         = nonsensitive(data.aws_ssm_parameter.ami.value)
  instance_type               = "t3.micro"
  key_name                    = aws_key_pair.app.key_name
  subnet_id                   = local.network.private_subnet_id
  private_ip                  = "10.42.2.20"
  associate_public_ip_address = false
  vpc_security_group_ids      = [local.network.backend_security_group_id]
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }
  credit_specification { cpu_credits = "standard" }
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    encrypted             = true
    delete_on_termination = true
  }
  user_data                   = replace(local.common_user_data, "__FRONTEND_ORIGIN__", "http://${aws_instance.client.public_ip}")
  user_data_replace_on_change = false
  tags                        = { Name = "ec2-backend-${local.suffix}", Role = "backend" }
}

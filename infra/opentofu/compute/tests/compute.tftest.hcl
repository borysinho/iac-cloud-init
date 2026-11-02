mock_provider "aws" {
  mock_data "aws_ssm_parameter" {
    defaults = { value = "ami-test" }
  }
}
override_data {
  target = data.terraform_remote_state.network
  values = {
    outputs = {
      deployment = {
        ready                     = true
        account_id                = "222234418877"
        region                    = "us-east-2"
        project                   = "asistencia"
        environment               = "cloudinit-opentofu"
        public_subnet_id          = "subnet-public"
        private_subnet_id         = "subnet-private"
        client_security_group_id  = "sg-client"
        backend_security_group_id = "sg-backend"
      }
    }
  }
}
override_resource {
  target = aws_instance.client
  values = { public_ip = "203.0.113.10" }
}
variables {
  ssh_public_key_path = "tests/key.pub"
}
run "compute_equivalence" {
  command = apply
  assert {
    condition     = aws_instance.client.private_ip == "10.42.1.10" && aws_instance.backend.private_ip == "10.42.2.20" && aws_instance.client.associate_public_ip_address && !aws_instance.backend.associate_public_ip_address
    error_message = "Dos EC2 con IPs y exposicion equivalentes."
  }
  assert {
    condition     = aws_instance.client.metadata_options[0].http_tokens == "required" && aws_instance.backend.metadata_options[0].http_tokens == "required" && aws_instance.client.credit_specification[0].cpu_credits == "standard" && aws_instance.backend.credit_specification[0].cpu_credits == "standard"
    error_message = "IMDSv2 y CPU standard obligatorios."
  }
  assert {
    condition     = aws_instance.client.root_block_device[0].encrypted && aws_instance.backend.root_block_device[0].encrypted && aws_instance.client.root_block_device[0].volume_size == 12 && aws_instance.backend.root_block_device[0].volume_size == 20
    error_message = "Discos cifrados y tamanos equivalentes."
  }
  assert {
    condition     = aws_instance.client.user_data == replace(replace(file("${path.module}/../../cloud-init.yaml"), "__APP_ARCHIVE_URL__", local.app_archive_url), "__FRONTEND_ORIGIN__", "https://127.0.0.1") && aws_instance.backend.user_data == replace(replace(file("${path.module}/../../cloud-init.yaml"), "__APP_ARCHIVE_URL__", local.app_archive_url), "__FRONTEND_ORIGIN__", "https://203.0.113.10")
    error_message = "Usar exactamente la fuente comun con sus dos entradas resueltas."
  }
  assert {
    condition     = !aws_instance.client.user_data_replace_on_change && !aws_instance.backend.user_data_replace_on_change && output.deployment.url == "https://203.0.113.10"
    error_message = "No reemplazar automaticamente las EC2 por cambios de UserData."
  }
}
run "reject_invalid_revision" {
  command = plan
  variables { app_revision = "main" }
  expect_failures = [var.app_revision]
}
run "reject_wrong_network_account" {
  command = plan
  variables { account_id = "123456789012" }
  expect_failures = [aws_instance.client]
}

mock_provider "aws" {
  mock_data "aws_availability_zones" {
    defaults = { names = ["us-east-2a"] }
  }
}
variables {
  ssh_source_cidr = "181.188.164.3/32"
}
run "network_equivalence" {
  command = apply
  assert {
    condition     = aws_vpc.main.cidr_block == "10.42.0.0/16" && aws_vpc.main.enable_dns_support && aws_vpc.main.enable_dns_hostnames
    error_message = "La VPC debe conservar rangos y DNS."
  }
  assert {
    condition     = aws_subnet.public.cidr_block == "10.42.1.0/24" && aws_subnet.private.cidr_block == "10.42.2.0/24" && aws_subnet.public.availability_zone == aws_subnet.private.availability_zone && !aws_subnet.private.map_public_ip_on_launch
    error_message = "Subredes en una AZ y backend privado."
  }
  assert {
    condition     = one([for rule in aws_security_group.client.ingress : rule if rule.from_port == 80]).cidr_blocks == tolist(["0.0.0.0/0"]) && one([for rule in aws_security_group.client.ingress : rule if rule.from_port == 22]).cidr_blocks == tolist(["181.188.164.3/32"])
    error_message = "HTTP publico y SSH limitado."
  }
  assert {
    condition     = toset([for rule in aws_security_group.backend.ingress : rule.from_port]) == toset([22, 8090]) && alltrue([for rule in aws_security_group.backend.ingress : contains(rule.security_groups, aws_security_group.client.id) && try(length(rule.cidr_blocks), 0) == 0])
    error_message = "Backend solo desde el grupo cliente; MySQL no debe exponerse."
  }
  assert {
    condition     = aws_nat_gateway.main.connectivity_type == "public" && aws_eip.nat.domain == "vpc" && aws_route.private.nat_gateway_id == aws_nat_gateway.main.id && output.deployment.ready
    error_message = "NAT administrado y salida privada preparados."
  }
}
run "reject_open_ssh" {
  command = plan
  variables { ssh_source_cidr = "0.0.0.0/0" }
  expect_failures = [var.ssh_source_cidr]
}

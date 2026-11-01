data "aws_availability_zones" "available" {
  state = "available"
}
locals {
  az = coalesce(var.availability_zone, data.aws_availability_zones.available.names[0])
}
resource "aws_vpc" "main" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "vpc-${local.suffix}" }
}
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.42.1.0/24"
  availability_zone       = local.az
  map_public_ip_on_launch = false
  tags                    = { Name = "subnet-publica-${local.suffix}" }
}
resource "aws_subnet" "private" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.42.2.0/24"
  availability_zone       = local.az
  map_public_ip_on_launch = false
  tags                    = { Name = "subnet-privada-${local.suffix}" }
}
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "igw-${local.suffix}" }
}
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "rtb-publica-${local.suffix}" }
}
resource "aws_route" "public" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "rtb-privada-${local.suffix}" }
}
resource "aws_route_table_association" "private" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private.id
}
resource "aws_eip" "nat" {
  domain     = "vpc"
  tags       = { Name = "eip-nat-${local.suffix}" }
  depends_on = [aws_internet_gateway.main]
}
resource "aws_nat_gateway" "main" {
  allocation_id     = aws_eip.nat.id
  subnet_id         = aws_subnet.public.id
  connectivity_type = "public"
  tags              = { Name = "nat-${local.suffix}" }
  depends_on        = [aws_route.public, aws_route_table_association.public]
}
resource "aws_route" "private" {
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main.id
}
resource "aws_security_group" "client" {
  name_prefix = "cliente-${local.suffix}-"
  description = "Cliente HTTP y bastion SSH"
  vpc_id      = aws_vpc.main.id
  ingress {
    protocol    = "tcp"
    from_port   = 22
    to_port     = 22
    cidr_blocks = [var.ssh_source_cidr]
  }
  ingress {
    protocol    = "tcp"
    from_port   = 80
    to_port     = 80
    cidr_blocks = [var.web_source_cidr]
  }
  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "secgrp-cliente-${local.suffix}" }
}
resource "aws_security_group" "backend" {
  name_prefix = "backend-${local.suffix}-"
  description = "API y SSH solo desde cliente; MySQL local"
  vpc_id      = aws_vpc.main.id
  dynamic "ingress" {
    for_each = toset([22, 8090])
    content {
      protocol        = "tcp"
      from_port       = ingress.value
      to_port         = ingress.value
      security_groups = [aws_security_group.client.id]
    }
  }
  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "secgrp-backend-${local.suffix}" }
}

output "deployment" {
  description = "Contrato consumido por compute tras completar la red."
  value = {
    account_id                = var.account_id
    region                    = var.region
    project                   = var.project
    environment               = var.environment
    vpc_id                    = aws_vpc.main.id
    public_subnet_id          = aws_subnet.public.id
    private_subnet_id         = aws_subnet.private.id
    client_security_group_id  = aws_security_group.client.id
    backend_security_group_id = aws_security_group.backend.id
    nat_gateway_id            = aws_nat_gateway.main.id
    ready                     = true
  }
  depends_on = [aws_route.public, aws_route.private, aws_route_table_association.public, aws_route_table_association.private]
}

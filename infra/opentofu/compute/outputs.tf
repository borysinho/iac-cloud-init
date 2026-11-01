output "deployment" {
  value = {
    client_instance_id  = aws_instance.client.id
    backend_instance_id = aws_instance.backend.id
    client_public_ip    = aws_instance.client.public_ip
    backend_private_ip  = aws_instance.backend.private_ip
    url                 = "http://${aws_instance.client.public_ip}"
    app_revision        = var.app_revision
    client_ssh          = "ssh -i ~/globomatics-ec2 ubuntu@${aws_instance.client.public_ip}"
    backend_ssh         = "ssh -i ~/globomatics-ec2 -o \"ProxyCommand=ssh -i ~/globomatics-ec2 -W %h:%p ubuntu@${aws_instance.client.public_ip}\" ubuntu@10.42.2.20"
  }
}

# Infraestructura

- `cloudformation/`: dos pilas de red y cómputo, archivos Git Sync y políticas IAM; consultar su README.
- `opentofu/`: reservado para los siguientes pasos.
- `pulumi/`: reservado para los siguientes pasos.
- `cloud-init.yaml`: fuente única de configuración de servidores para las tres herramientas; instalación de servicios y despliegue de la aplicación según la IP privada, sobre Ubuntu 24.04; resolver URL del código y origen del cliente.

La aplicación permanece separada en `../app/`. No se han desplegado recursos en AWS.

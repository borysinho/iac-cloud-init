# Infraestructura

- `cloudformation/`: dos pilas de red y cómputo, archivos Git Sync y políticas IAM; consultar su README.
- `opentofu/`: reservado para los siguientes pasos.
- `pulumi/`: reservado para los siguientes pasos.
- `cloud-init.yaml`: fuente única de configuración de servidores para las tres herramientas; instalación de Nginx o Node.js/MySQL según la IP privada, sobre Ubuntu 24.04.

La aplicación permanece separada en `../app/`. No se han desplegado recursos en AWS.

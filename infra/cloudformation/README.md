# CloudFormation: aplicación de asistencia

Solo dos pilas, sin pila raíz ni pilas anidadas:

- `network.yaml`: VPC, subred pública para cliente, subred privada para backend, Internet Gateway, rutas y dos grupos de seguridad.
- `compute.yaml`: dos EC2 `t3.micro` y una clave SSH pública importada.

| Servidor | IP privada | Función |
|---|---|---|
| Cliente | 10.42.1.10 | Nginx: archivos estáticos y proxy `/api`; también permite SSH al backend |
| Backend | 10.42.2.20 | Node.js y MySQL local, según la aplicación existente |

El cliente recibe IP pública dinámica. HTTP se permite desde `WebSourceCidr` y SSH desde `SshSourceCidr`. El backend admite SSH y API 8090 únicamente desde el grupo del cliente. MySQL no tiene puertos de entrada de red. Ambos discos raíz están cifrados e IMDSv2 es obligatorio. Los discos raíz se eliminan al eliminar las instancias; respaldar MySQL antes de reemplazar o borrar el backend.

## Cloud-init compartido

La única fuente es [`../cloud-init.yaml`](../cloud-init.yaml), también para las futuras implementaciones OpenTofu y Pulumi. Por ahora configura zona horaria y acceso SSH; **la instalación de Nginx, Node.js, MySQL y la aplicación queda para el siguiente paso**.

CloudFormation no lee archivos vecinos del repositorio. Desde la raíz de `cloud-init/`, ejecuta:

```bash
python3 infra/cloudformation/scripts/sync-cloud-init.py
python3 infra/cloudformation/scripts/sync-cloud-init.py --check
```

El script incorpora exactamente los mismos bytes en Base64 en `UserData` de ambas EC2. Publica juntos el archivo compartido y `compute.yaml` regenerado: Git Sync vigila la plantilla y el archivo de despliegue. OpenTofu y Pulumi deberán leer la misma fuente directamente.

El backend conserva la subred privada sin Internet de la práctica anterior. Para instalar los servicios en el siguiente paso se necesitarán paquetes offline, una AMI preparada o adaptar explícitamente la salida de red. No se ha añadido NAT. Actualizar UserData no vuelve a ejecutar automáticamente todos los módulos de primer arranque de cloud-init en una instancia existente.

## Git Sync

Los dos archivos de `deployments/` ya están preparados para seleccionar **I am providing my own file in my repository** y evitar depender de su generación automática. AWS puede seguir utilizando PR durante el flujo; revisa cualquier PR antes de fusionarlo.

1. En `deployments/network-lab.yaml`, sustituye los CIDR documentales `192.0.2.1/32` por tu IP/red autorizada. No uses SSH abierto a Internet.
2. En `deployments/compute-lab.yaml`, reemplaza `REEMPLAZAR_POR_CLAVE_PUBLICA_OPENSSH` por la clave **pública** completa.
3. Las rutas suponen que `cloud-init/` es la raíz del repositorio. Si está dentro de otro repositorio, antepón su ruta a `template-file-path` y a las rutas que introduces en la consola.
4. Publica los archivos en la rama elegida. Crea primero `asistencia-cloudinit-network`, con archivo de despliegue `infra/cloudformation/deployments/network-lab.yaml` y plantilla `infra/cloudformation/network.yaml`.
5. Espera `CREATE_COMPLETE`. Crea `asistencia-cloudinit-compute` con archivo de despliegue `infra/cloudformation/deployments/compute-lab.yaml` y plantilla `infra/cloudformation/compute.yaml`.
6. Para ambas pilas selecciona el rol de ejecución descrito en `iam/README.md`. El rol Git Sync es independiente.

`NetworkStackName` debe coincidir con el nombre de la pila de red. Cómputo importa sus salidas por nombre; no se reutilizan IDs anteriores. Ambas pilas deben estar en la misma cuenta y región. Eliminar primero cómputo y después red. Antes de modificar exportaciones existentes, comprobar sus consumidores con `aws cloudformation list-imports --export-name NOMBRE`.

## Validación

```bash
python3 infra/cloudformation/scripts/sync-cloud-init.py --check
cfn-lint infra/cloudformation/network.yaml infra/cloudformation/compute.yaml
```

Confirmar la AMI pública SSM en la región y revisar el change set antes de aplicar. Esta preparación no crea recursos ni configura IAM en AWS.

Referencias: [Git Sync](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/git-sync-create-stack-from-repository-source-code.html), [UserData EC2](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-ec2-instance.html).

# CloudFormation: aplicación de asistencia

Para realizar el despliegue desde cero, sigue la [guía paso a paso](GUIA-PASO-A-PASO.md). Para las EC2 que ya creaste, utiliza [despliegue de la aplicación y actualización de instancias existentes](DESPLIEGUE-APLICACION.md).

Solo dos pilas, sin pila raíz ni pilas anidadas:

- `network.yaml`: VPC, subred pública para cliente, subred privada para backend, Internet Gateway, NAT Gateway con Elastic IP, rutas y dos grupos de seguridad.
- `compute.yaml`: dos EC2 `t3.micro` con créditos CPU en modo `standard`, Ubuntu Server 24.04 LTS amd64 y una clave SSH pública importada.

| Servidor | IP privada | Función |
|---|---|---|
| Cliente | 10.42.1.10 | Nginx: archivos estáticos y proxy `/api`; también permite SSH al backend |
| Backend | 10.42.2.20 | Node.js y MySQL local, según la aplicación existente |

El cliente recibe IP pública dinámica. HTTP se permite desde `WebSourceCidr` y SSH desde `SshSourceCidr`. El backend admite SSH y API 8090 únicamente desde el grupo del cliente. MySQL no tiene puertos de entrada de red. Ambos discos raíz están cifrados e IMDSv2 es obligatorio. Los discos raíz se eliminan al eliminar las instancias; respaldar MySQL antes de reemplazar o borrar el backend.

## Cloud-init compartido

La única fuente es [`../cloud-init.yaml`](../cloud-init.yaml), también para las futuras implementaciones OpenTofu y Pulumi. Instala Nginx en el cliente y Node.js 24 con npm y MySQL en el backend. Detecta la función por la IP privada: `10.42.1.10` o `10.42.2.20`. Una IP desconocida produce un error antes de instalar paquetes. Las futuras configuraciones OpenTofu y Pulumi deben conservar ese mapa o actualizarlo en la fuente común.

MySQL se configura con escucha en `127.0.0.1` para sus puertos SQL y X Protocol. El administrador local utiliza autenticación por socket (`sudo mysql`). Se habilitan Nginx y MySQL al arrancar. También se descarga la aplicación desde un commit del repositorio público, se crea su base y usuario SQL, se generan credenciales locales, se inicializan tablas y administrador y se habilita el servicio `asistencia`. El cliente recibe los cuatro archivos estáticos y la configuración del proxy. Consulta `DESPLIEGUE-APLICACION.md` para entrar y aplicar el cambio a instancias existentes.

CloudFormation no lee archivos vecinos del repositorio. Desde la raíz de `cloud-init/`, ejecuta:

```bash
python3 infra/cloudformation/scripts/sync-cloud-init.py
python3 infra/cloudformation/scripts/sync-cloud-init.py --check
```

El script incorpora la misma plantilla común en `UserData` de ambas EC2; resuelve la URL del commit `AppRevision` y el origen HTTP del cliente mediante funciones de CloudFormation. No hay secretos en UserData. Publica juntos el archivo compartido y `compute.yaml` regenerado: Git Sync vigila la plantilla y el archivo de despliegue. OpenTofu y Pulumi deberán leer la misma fuente y resolver sus dos entradas de despliegue.

El backend permanece sin IP pública. Su nueva ruta de salida usa un NAT Gateway en la subred pública para descargar paquetes de Ubuntu y NodeSource. El NAT y su Elastic IP tienen costo mientras existan. Los creditos aplicables pueden cubrir ese consumo; no se ha comprobado el plan ni el saldo de esta cuenta, por lo que no se garantiza ausencia de cobros a la tarjeta. Antes de desplegar, revisar Billing → Credits y el tipo de plan. No se agregan entradas al grupo de seguridad del backend. Se mantienen exactamente dos pilas y dos EC2.

La AMI cambia de Amazon Linux a Ubuntu 24.04 para instalar MySQL desde los repositorios de Ubuntu. Node.js 24 se obtiene del repositorio firmado de NodeSource. La clave SSH pública es la misma, pero el usuario SSH ahora es `ubuntu`. El dispositivo raíz declarado es `/dev/sda1`, correspondiente a esta AMI.

## Git Sync

Los dos archivos de `deployments/` ya están preparados para seleccionar **I am providing my own file in my repository** y evitar depender de su generación automática. AWS puede seguir utilizando PR durante el flujo; revisa cualquier PR antes de fusionarlo.

1. En `deployments/network-lab.yaml`, sustituye los CIDR documentales `192.0.2.1/32` por tu IP/red autorizada. No uses SSH abierto a Internet.
2. En `deployments/compute-lab.yaml`, reemplaza `REEMPLAZAR_POR_CLAVE_PUBLICA_OPENSSH` por la clave **pública** completa.
3. Las rutas suponen que `cloud-init/` es la raíz del repositorio. Si está dentro de otro repositorio, antepón su ruta a `template-file-path` y a las rutas que introduces en la consola.
4. Publica los archivos en la rama elegida. Crea primero `asistencia-cloudinit-network`, con archivo de despliegue `infra/cloudformation/deployments/network-lab.yaml` y plantilla `infra/cloudformation/network.yaml`.
5. Espera `CREATE_COMPLETE`. Crea `asistencia-cloudinit-compute` con archivo de despliegue `infra/cloudformation/deployments/compute-lab.yaml` y plantilla `infra/cloudformation/compute.yaml`.
6. En el campo IAM de la seccion del repositorio, crea/selecciona el rol **Git Sync**. Despues, en **Configure stack options → Permissions**, selecciona `asistencia-cloudinit-execution`. Son campos y roles diferentes; consulta `iam/README.md`.

`NetworkStackName` debe coincidir con el nombre de la pila de red. Cómputo importa sus salidas por nombre; no se reutilizan IDs anteriores. Ambas pilas deben estar en la misma cuenta y región. Eliminar primero cómputo y después red. Antes de modificar exportaciones existentes, comprobar sus consumidores con `aws cloudformation list-imports --export-name NOMBRE`.

## Aplicar este paso

1. Actualiza en IAM la política insertada del rol con `iam/execution-policy.json`: incluye NAT/EIP y lectura del parámetro de AMI Ubuntu. Publicar el JSON en Git no actualiza IAM.
2. Regenera `compute.yaml` con el script de sincronización y publica ambos archivos junto con las plantillas y los archivos de despliegue. Conserva tu clave pública y CIDR personalizados.
3. Aplica primero red y espera `UPDATE_COMPLETE` o `CREATE_COMPLETE`; NAT y ruta privada deben estar disponibles antes de crear las instancias.
4. Después aplica cómputo. **Cambiar la AMI reemplaza las EC2**, cuyos discos raíz se eliminan: respalda MySQL si el backend ya contiene datos. No es una actualización en sitio del sistema operativo.
5. Espera el resultado de cloud-init en cada servidor. `CREATE_COMPLETE` de CloudFormation no garantiza que haya terminado la instalación: esta plantilla no añade señales de finalización de cloud-init al stack.

```bash
# En ambos servidores, mediante SSH como ubuntu.
sudo cloud-init status --wait --long
sudo tail -n 100 /var/log/cloud-init-output.log

# Cliente
systemctl is-enabled nginx
systemctl is-active nginx
curl -I http://127.0.0.1

# Backend (SSH a traves del cliente)
node --version
npm --version
systemctl is-enabled mysql
systemctl is-active mysql
sudo mysqladmin --protocol=socket ping
sudo mysql -e "SELECT @@bind_address, @@mysqlx_bind_address;"
sudo ss -lntp | grep -E ':(3306|33060)\b'
```

Esperado: Nginx activo en el cliente, Node `v24.x`, MySQL activo y escuchando solo en localhost. Nginx debe servir la pantalla de asistencia y `/api/me` debe devolver 401 sin token. El servicio `asistencia` debe estar activo en el backend. Si cloud-init falla, revisar el registro antes de reintentar. El instalador conserva los datos de MySQL; no borra ni reinicializa la base.

Actualizar UserData no vuelve a ejecutar automáticamente todos los módulos de primer arranque en instancias existentes. Este paso se ejecuta automáticamente al crear las nuevas instancias Ubuntu. Para comprobar un servidor ya inicializado se usan los comandos anteriores, no se presupone que reiniciar lo reconfigure.

## Validación

```bash
python3 infra/cloudformation/scripts/sync-cloud-init.py --check
python3 infra/cloudformation/tests/test_bootstrap.py
cfn-lint infra/cloudformation/network.yaml infra/cloudformation/compute.yaml
```

Se comprobó localmente la sintaxis YAML/JSON, referencias, tamaño de plantillas, coincidencia del UserData y las ramas del instalador con comandos simulados (incluidos errores de IP y APT). No se ejecutó una instalación real en EC2. `cloud-init schema`, `cfn-lint` y `cfn-guard` no están instalados en el entorno de trabajo: su validación de esquema y seguridad/compliance queda pendiente.

Confirmar la AMI pública SSM en la región y revisar el change set antes de aplicar. Esta preparación no crea recursos ni configura IAM en AWS.

Referencias: [Git Sync](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/git-sync-create-stack-from-repository-source-code.html), [UserData EC2](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-ec2-instance.html).

Fuentes de instalación: [AMI Ubuntu en CloudFormation](https://documentation.ubuntu.com/aws/aws-how-to/instances/build-cloudformation-templates/), [MySQL en Ubuntu](https://ubuntu.com/server/docs/databases-mysql/), [NodeSource 24](https://github.com/nodesource/distributions/blob/master/scripts/deb/setup_24.x), [NAT Gateway](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ec2-natgateway.html).

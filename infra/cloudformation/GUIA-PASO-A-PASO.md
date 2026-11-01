# Guía paso a paso: CloudFormation y cloud-init

Esta guía despliega lo implementado hasta ahora: infraestructura y servicios del sistema. Al terminar habrá un cliente con Nginx y un backend con Node.js 24, npm y MySQL. **La aplicación de asistencia todavía no estará publicada**: copiar su código, crear su base de datos y sus credenciales, configurar el proxy y habilitar la API son el siguiente paso.

Se crean exactamente dos pilas:

| Pila | Plantilla | Contenido |
|---|---|---|
| `asistencia-cloudinit-network` | `network.yaml` | VPC, subredes, grupos de seguridad, Internet Gateway, NAT Gateway y Elastic IP |
| `asistencia-cloudinit-compute` | `compute.yaml` | Dos EC2 Ubuntu 24.04, discos raíz y clave SSH pública importada |

El cliente utiliza `10.42.1.10` y recibe una IP pública dinámica. El backend utiliza `10.42.2.20`, sin IP pública. El backend descarga los paquetes a través del NAT Gateway administrado; ninguna EC2 actúa como NAT.

## 1. Confirmar cuenta, región y créditos

1. En la consola AWS, verifica que estás en la cuenta donde harás el laboratorio.
2. Selecciona **US East (Ohio), `us-east-2`**, para las dos pilas y la conexión del repositorio.
3. En **Billing and Cost Management**, comprueba el tipo de plan, el saldo, los servicios cubiertos y la fecha de vencimiento de los créditos.
4. No presupongas que NAT Gateway es gratuito: tiene cargos por tiempo y procesamiento; su IPv4 pública también puede generar consumo. Los créditos aplicables pueden cubrirlos. En un plan de pago, lo que no cubran los créditos puede cobrarse a la tarjeta.

Las políticas de `iam/` están preparadas para la cuenta **`222234418877`** y la región **`us-east-2`**. Si el destino es otro, cambia esos valores en `execution-policy.json` y el ARN de `pass-role-policy.json` antes de usarlos. No cambies los ARN de AMI y parámetros públicos para insertar tu cuenta: algunos utilizan el campo de cuenta vacío deliberadamente.

## 2. Preparar los archivos locales y la clave SSH

Abre una terminal **en tu computadora** y entra en la carpeta del laboratorio:

```bash
cd '/home/borysquiroga/Documentos/docs/Diplomado/Módulo 2/cloud-init'
```

Todos los comandos locales siguientes parten de esa carpeta, salvo indicación contraria.

Comprueba que tienes Python 3, Git y OpenSSH. Para este laboratorio puedes reutilizar una clave pública propia. Si todavía no tienes la clave `~/globomatics-ec2`, créala con:

```bash
ssh-keygen -t ed25519 -f "$HOME/globomatics-ec2" -C asistencia-cloudinit
```

No ejecutes ese comando sobre una clave existente para sobrescribirla. Conserva la clave privada en tu equipo; usa su contraseña de protección cuando SSH la solicite.

Muestra únicamente la **pública** para copiarla al archivo de despliegue:

```bash
cat "$HOME/globomatics-ec2.pub"
```

La línea empieza con `ssh-ed25519`. La privada no se publica en Git, no se pega en CloudFormation y no se copia a los servidores.

## 3. Completar los parámetros de red

Edita [`deployments/network-lab.yaml`](deployments/network-lab.yaml):

| Parámetro | Qué colocar |
|---|---|
| `Project` | Conservar `asistencia` |
| `Environment` | Conservar `cloudinit` |
| `SshSourceCidr` | Tu IP pública administrativa con `/32` |
| `WebSourceCidr` | IP pública o red autorizada para abrir Nginx por HTTP |

Por ejemplo, para acceder por SSH y por navegador desde tu equipo, ambos CIDR pueden contener tu IP pública seguida de `/32`. Obtén esa IP desde tu conexión actual; no uses la IP privada de tu computadora. Los valores incluidos, `192.0.2.1/32`, son documentales y **deben reemplazarse**.

Si tu IP pública cambia, actualiza los CIDR en el archivo y publica el cambio en la rama sincronizada. Mantén SSH limitado a tu IP o a una red administrativa controlada.

## 4. Completar los parámetros de cómputo

Edita [`deployments/compute-lab.yaml`](deployments/compute-lab.yaml):

| Parámetro | Qué colocar |
|---|---|
| `Project` | `asistencia` |
| `Environment` | `cloudinit` |
| `NetworkStackName` | `asistencia-cloudinit-network` |
| `SshPublicKey` | Línea pública OpenSSH completa, en lugar del marcador |
| `LatestAmiId` | Conservar el parámetro público de Ubuntu 24.04 incluido |

Puedes escribir la clave pública en una sola línea entre comillas. No dejes el texto `REEMPLAZAR_POR_CLAVE_PUBLICA_OPENSSH`, porque no cumple la validación del parámetro.

No pegues IDs de VPC, subredes ni grupos de seguridad. `compute.yaml` obtiene esos recursos de las exportaciones de la pila de red. Conserva las IP privadas del laboratorio: el archivo compartido cloud-init las usa para decidir qué servicios instalar.

## 5. Preparar UserData y revisar las rutas del repositorio

Desde `cloud-init/`, ejecuta:

```bash
python3 infra/cloudformation/scripts/sync-cloud-init.py
python3 infra/cloudformation/scripts/sync-cloud-init.py --check
```

El segundo comando debe confirmar que ambas EC2 contienen exactamente el archivo compartido. El script solo incorpora `infra/cloud-init.yaml` en `compute.yaml`; no accede a AWS.

Las rutas de `template-file-path` suponen que **`cloud-init/` es la raíz del repositorio Git**. Verifica la raíz real con:

```bash
git rev-parse --show-toplevel
```

Si publicas esta carpeta dentro de otro repositorio, ajusta las rutas para que partan de su raíz. Por ejemplo, si el laboratorio está en `cloud-init/` dentro de ese repositorio, la ruta de plantilla será `cloud-init/infra/cloudformation/network.yaml`, y la ruta de despliegue que introducirás en AWS también llevará ese prefijo.

Si ya tienes `cfn-lint` disponible, comprueba las plantillas:

```bash
cfn-lint infra/cloudformation/network.yaml infra/cloudformation/compute.yaml
```

## 6. Crear el rol de ejecución de CloudFormation

En la consola **IAM**:

1. Abre **Roles → Create role**.
2. Selecciona una política de confianza personalizada y pega el contenido de [`iam/cloudformation-trust.json`](iam/cloudformation-trust.json).
3. Crea el rol con nombre **`asistencia-cloudinit-execution`**.
4. En ese rol, abre **Permissions → Add permissions → Create inline policy**.
5. En el editor JSON pega [`iam/execution-policy.json`](iam/execution-policy.json).
6. Guarda la política con nombre **`asistencia-cloudinit-resources`**.
7. Guarda el ARN del rol para reconocerlo al configurar las pilas.

Si el rol ya existe, revisa su confianza y actualiza la política insertada en lugar de crear un duplicado. La versión actual incluye los permisos de NAT Gateway, Elastic IP y el parámetro de AMI Ubuntu.

La identidad que entrega el rol a CloudFormation necesita el permiso limitado de [`iam/pass-role-policy.json`](iam/pass-role-policy.json). Si hace falta, un administrador debe incorporarlo a esa identidad. No se adjunta al propio rol de ejecución y no sustituye los permisos de consola ni los de Git Sync.

## 7. Publicar y conectar el repositorio

1. Publica las plantillas, los dos archivos de `deployments/`, las políticas IAM, el script y `infra/cloud-init.yaml` en tu repositorio remoto.
2. Verifica en el proveedor Git que esos archivos existen en la rama que conectarás a AWS. Los archivos que solo están en tu equipo no estarán disponibles para Git Sync.
3. En **AWS CodeConnections**, crea o completa la conexión con tu proveedor Git y autoriza el repositorio. Comprueba que quede disponible; una conexión pendiente de autorización no sirve para sincronizar.

Hay dos funciones IAM distintas:

| Rol | Función |
|---|---|
| `asistencia-cloudinit-execution` | Crear y administrar EC2, red y NAT mediante CloudFormation |
| Rol de Git Sync | Sincronizar el repositorio y gestionar los cambios de la pila |

Para Git Sync puedes dejar que el asistente genere su rol. El rol generado para una pila puede necesitar cambios para utilizarse en otra; lo más directo es dejar que el asistente configure uno para cada pila. Si se requiere pasar el rol de ejecución, revisa también el permiso limitado `iam:PassRole`. No reemplaces la confianza del rol Git Sync por `cloudformation-trust.json`: tienen principales de servicio diferentes.

## 8. Crear primero la pila de red

En **CloudFormation**, región `us-east-2`:

1. Abre **Create stack → With new resources (standard)** y selecciona **Sync from Git**.
2. Usa el nombre **`asistencia-cloudinit-network`**.
3. Para el archivo de despliegue, selecciona **I am providing my own file in my repository**.
4. Selecciona conexión, repositorio y rama.
5. Introduce las rutas de la tabla siguiente, ajustadas a la raíz de tu repositorio.
6. Configura el rol Git Sync. En las opciones de ejecución del stack, selecciona **`asistencia-cloudinit-execution`**.
7. Revisa parámetros y envía la creación. Si AWS abre un PR necesario para completar el flujo, revísalo y fusiónalo en la rama conectada.

| Campo | Ruta si `cloud-init/` es la raíz del repositorio |
|---|---|
| Deployment file path | `infra/cloudformation/deployments/network-lab.yaml` |
| Template file path | `infra/cloudformation/network.yaml` |

Espera **`CREATE_COMPLETE`**. Si falla, revisa **Events** y **Git sync** antes de crear cómputo. En **Resources**, confirma que el NAT Gateway esté disponible y que la ruta privada `0.0.0.0/0` apunte a ese NAT.

En **Outputs**, deben aparecer `VpcId`, `PublicSubnetId`, `PrivateSubnetId`, `ClientSecurityGroupId` y `BackendSecurityGroupId`. No tienes que copiarlos al otro archivo: se importan por nombre de pila.

## 9. Crear la pila de cómputo

Repite el asistente Git Sync con estos valores:

| Campo | Valor |
|---|---|
| Stack name | `asistencia-cloudinit-compute` |
| Deployment file path | `infra/cloudformation/deployments/compute-lab.yaml` |
| Template file path | `infra/cloudformation/compute.yaml` |
| Rol de ejecución | `asistencia-cloudinit-execution` |
| `NetworkStackName` | `asistencia-cloudinit-network` |

Usa la misma cuenta, región y rama que para red. Revisa cualquier PR que genere AWS y espera **`CREATE_COMPLETE`**.

En **Outputs**, localiza `ClientPublicIp`, `ClientInstanceId`, `BackendInstanceId`, `BackendPrivateIp` y los comandos SSH. El backend debe conservar `10.42.2.20` y no tener IP pública.

## 10. Comprobar el cliente y cloud-init

En tu computadora, define la IP obtenida de `ClientPublicIp`:

```bash
CLIENT_PUBLIC=REEMPLAZAR_POR_IP_PUBLICA_DEL_CLIENTE
ssh -i "$HOME/globomatics-ec2" "ubuntu@$CLIENT_PUBLIC"
```

En la primera conexión, comprueba la huella del servidor antes de aceptarla. En el **cliente** ejecuta:

```bash
sudo cloud-init status --wait --long
sudo tail -n 100 /var/log/cloud-init-output.log
systemctl is-enabled nginx
systemctl is-active nginx
sudo nginx -t
curl -I http://127.0.0.1
```

Debes ver cloud-init finalizado sin errores, Nginx habilitado y activo, configuración válida y respuesta HTTP. Desde tu navegador abre `http://IP_PUBLICA_DEL_CLIENTE`: por ahora verás la página predeterminada de Nginx. Tu IP debe estar autorizada por `WebSourceCidr`.

`CREATE_COMPLETE` indica que CloudFormation terminó de crear la infraestructura. No garantiza que cloud-init haya terminado: esta plantilla no incluye señales para que la pila espere la instalación.

## 11. Comprobar el backend y la salida por NAT

Desde **otra terminal de tu computadora**, usando la misma variable `CLIENT_PUBLIC`, conecta a través del cliente:

```bash
ssh -i "$HOME/globomatics-ec2" \
  -o "ProxyCommand=ssh -i $HOME/globomatics-ec2 -W %h:%p ubuntu@$CLIENT_PUBLIC" \
  ubuntu@10.42.2.20
```

La clave privada permanece en tu equipo. El usuario es `ubuntu` en ambas máquinas.

En el **backend** ejecuta:

```bash
sudo cloud-init status --wait --long
sudo tail -n 100 /var/log/cloud-init-output.log
node --version
npm --version
systemctl is-enabled mysql
systemctl is-active mysql
sudo mysqladmin --protocol=socket ping
sudo mysql -e "SELECT VERSION(), @@bind_address, @@mysqlx_bind_address;"
sudo ss -lntp | grep -E ':(3306|33060)\b'
curl -I --connect-timeout 10 --max-time 30 https://deb.nodesource.com/
```

Resultado esperado: Node `v24.x`, npm instalado, MySQL habilitado y activo, respuesta `mysqld is alive` y escucha SQL/X Protocol solo en `127.0.0.1`. La petición HTTPS debe recibir respuesta; confirma que el backend llega al exterior mediante el NAT. No uses `ping` como única comprobación de Internet, porque el destino puede bloquear ICMP.

No debe existir todavía una API activa en el puerto 8090: el código de la aplicación aún no se ha desplegado.

## 12. Actualizaciones posteriores

- Para modificar recursos, edita la plantilla o el archivo de despliegue y publica el cambio en la rama conectada. Revisa el change set o PR y el estado de la sincronización.
- Si cambias `infra/cloud-init.yaml`, ejecuta de nuevo `sync-cloud-init.py` y publica también `compute.yaml`. Git Sync no observa el archivo compartido directamente.
- Cambiar UserData no ejecuta automáticamente toda la configuración de primer arranque en servidores existentes. Revisa la estrategia de actualización antes de esperar una reinstalación.
- Cambiar la AMI reemplaza las EC2. Sus discos raíz se eliminan con ellas: respalda cualquier base existente antes de aplicar ese cambio.
- Las políticas IAM creadas manualmente se actualizan manualmente; publicar sus JSON no modifica los roles.

## 13. Problemas frecuentes

| Síntoma | Qué revisar |
|---|---|
| AWS no encuentra un archivo | Ruta desde la raíz del repositorio, rama correcta y archivo publicado |
| Git Sync no avanza | Estado de la conexión, autorización del repositorio, rol Git Sync y PR pendiente |
| Error `PassRole` o `AccessDenied` | Identidad que entrega el rol, permisos del rol de ejecución, cuenta/región, SCP y límites de permisos |
| Exportación de red no encontrada | Red en `CREATE_COMPLETE`, nombre exacto de `NetworkStackName`, misma cuenta/región |
| SSH al cliente no conecta | IP pública vigente, `SshSourceCidr`, clave y usuario `ubuntu` |
| SSH al backend no conecta | ProxyCommand desde tu equipo, cliente disponible y grupo de seguridad asociado al backend |
| Cloud-init falla al descargar paquetes | NAT disponible, ruta privada hacia NAT, ruta pública hacia Internet Gateway, DNS y salidas permitidas |
| Navegador no abre Nginx | `WebSourceCidr`, IP pública, puerto 80, estado de Nginx y resultado de cloud-init |
| Aparece la bienvenida de Nginx | Es el resultado esperado en este paso; falta desplegar la aplicación |
| Cambié cloud-init y no se ejecutó otra vez | Plantilla regenerada y comportamiento de módulos de primer arranque |

Para investigar errores de arranque, consulta también `sudo less /var/log/cloud-init.log`. Si cloud-init informa errores, conserva los registros y corrige la causa antes de repetir la instalación; no borres el estado de cloud-init ni la base de datos para forzar un reintento.

## 14. Retirar el laboratorio cuando termines

Si decides eliminarlo, respalda primero cualquier dato que hayas creado. Retira la sincronización de Git de las pilas desde sus opciones de Git Sync para que el repositorio no solicite nuevas actualizaciones durante la retirada. Después elimina **cómputo y luego red**, esperando a que termine cada operación. Las exportaciones de red no se pueden eliminar mientras cómputo las utilice.

Detener las EC2 no detiene la facturación del NAT Gateway. Al eliminar red, verifica que el NAT y la Elastic IP administrados por esa pila también se hayan eliminado. No elimines recursos de otra práctica.

## Comprobación final

- [ ] Dos pilas completadas en la misma cuenta y región.
- [ ] NAT Gateway disponible; backend sin IP pública.
- [ ] Cloud-init finalizado sin errores en las dos EC2.
- [ ] Nginx habilitado, activo y accesible desde la red autorizada.
- [ ] Node.js 24 y npm disponibles en el backend.
- [ ] MySQL habilitado, activo y restringido a localhost.
- [ ] Repositorio sin claves privadas ni credenciales reales.

Esta guía describe el procedimiento; no acredita un despliegue ejecutado ni una instalación real comprobada en AWS.

## Referencias

- [Crear una pila con Git Sync y archivos existentes](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/git-sync-create-stack-from-repository-source-code.html).
- [Roles y requisitos de Git Sync](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/git-sync-prereq.html).
- [Rol de servicio de CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-iam-servicerole.html).
- [UserData y ejecución al primer arranque](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html).
- [Precios de Amazon VPC y NAT Gateway](https://aws.amazon.com/vpc/pricing/).
- [Créditos y planes de AWS Free Tier](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier.html).

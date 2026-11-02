# Asistencia con OpenTofu y cloud-init

Despliegue activo comprobado: **https://18.119.120.80/**. Consulta [la verificación real y la retirada de Pulumi](VERIFICACION-AWS.md).

La configuración actual incluye [HTTPS con certificado autofirmado](../HTTPS.md), redirección de HTTP a HTTPS y origen HTTPS en el backend. Este cambio actualiza los ejemplos HTTP de las etapas previas.

Misma configuración del laboratorio actual, con dos configuraciones raíz y estados independientes:

```text
opentofu/
├── network/    VPC, subredes, grupos, rutas, Internet Gateway y NAT Gateway
└── compute/    Dos EC2 y clave SSH pública; consume las salidas de network
```

Se mantienen HTTP público, NAT Gateway administrado, Ubuntu 24.04, cliente `10.42.1.10`, backend privado `10.42.2.20` y el despliegue de la aplicación desde el repositorio público. La única fuente de configuración es `../cloud-init.yaml`, compartida con CloudFormation y Pulumi.

Esta implementación crea recursos **independientes**: no importa ni modifica los existentes de CloudFormation o Pulumi. Si despliegas las tres implementaciones simultáneamente, se acumula su consumo, incluidos NAT Gateway y direcciones públicas. Revisa el plan y los créditos antes de aplicar; no se garantiza ausencia de cargos a la tarjeta.

## Arquitectura

| Elemento | Configuración |
|---|---|
| VPC | `10.42.0.0/16`, DNS habilitado |
| Subred pública | `10.42.1.0/24`, cliente y NAT Gateway |
| Subred privada | `10.42.2.0/24`, backend y ruta por NAT |
| Cliente | `t3.micro`, IPv4 pública dinámica, Nginx y archivos estáticos |
| Backend | `t3.micro`, sin IPv4 pública, Node.js 24, npm, MySQL y API systemd |
| Seguridad | SSH administrativo `/32`; HTTP 80 público; SSH/API 8090 del backend solo desde grupo cliente |
| Discos | gp3 cifrados, 12 GiB cliente y 20 GiB backend; eliminados con las EC2 |
| Metadatos/CPU | IMDSv2 obligatorio y créditos CPU `standard` |

Ambas subredes utilizan la misma AZ. No se expone MySQL a la red. Ninguna EC2 actúa como NAT.

## 1. Requisitos y credenciales

Necesitas OpenTofu 1.11 o superior, AWS CLI, OpenSSH y credenciales AWS temporales válidas con permisos para crear los recursos EC2/VPC del laboratorio. El proveedor restringe la cuenta a `account_id` y la región a `region`; los ejemplos utilizan `222234418877` y `us-east-2`.

```bash
aws sts get-caller-identity
tofu version
cd '/home/borysquiroga/Documentos/docs/Diplomado/Módulo 2/cloud-init/infra/opentofu'
```

Si utilizas un perfil, configura `AWS_PROFILE` antes de ejecutar OpenTofu. No se usa el rol de ejecución de CloudFormation ni el rol Git Sync. Sus políticas de recursos sirven como referencia, pero no modifiques la confianza de esos roles para usar OpenTofu.

### Adaptador de la sesión AWS actual

Para la ejecución real se utiliza `scripts/aws-session.py`. Obtiene credenciales temporales mediante AWS CLI y las entrega solo en memoria al proceso OpenTofu; no las imprime ni las guarda en archivos. Esto permite utilizar la sesión de `aws login` existente con el proveedor AWS.

```bash
python3 scripts/aws-session.py tofu -chdir=network plan
python3 scripts/aws-session.py tofu -chdir=compute plan
```

Si utilizas un perfil diferente, añade `--profile NOMBRE` antes de `tofu`. El adaptador trabaja desde esta carpeta y no modifica la configuración global de AWS.

## 2. Estado local separado

Cada carpeta usa el backend `local` y guarda su propio `terraform.tfstate`. No se crea un bucket de estado ni una tercera configuración. Se incluye un `.terraform.lock.hcl` por carpeta para fijar el proveedor AWS; estos lockfiles se deben versionar.

El estado y sus copias pueden contener información de infraestructura; consérvalos en una ubicación protegida y con respaldo, fuera de Git. El `.gitignore` del laboratorio ya excluye estados, planes, `.terraform/` y `*.tfvars`. No borres el estado mientras existan recursos administrados.

`compute` lee el archivo de estado de `network` mediante `terraform_remote_state`. Por defecto usa `../network/terraform.tfstate`; puedes indicar otra ruta absoluta con `network_state_path`. La lectura permite acceder al estado completo, no solo a las salidas: protege los permisos del archivo. Esta guía utiliza únicamente el workspace `default`; no mezcles rutas de otros workspaces o prácticas.

## 3. Crear primero la red

```bash
cp network/terraform.tfvars.example network/terraform.tfvars
```

Edita `network/terraform.tfvars`:

- Confirma cuenta, región, proyecto y entorno.
- Actualiza `ssh_source_cidr` a tu IP pública actual `/32`. El ejemplo conserva la última IP de CloudFormation, `181.188.164.3/32`; no se presupone que sea permanente.
- Mantén `web_source_cidr = "0.0.0.0/0"` para conservar tu página pública.
- Opcionalmente fija `availability_zone`; si no se indica, se elige la primera disponible.

```bash
tofu -chdir=network init
tofu -chdir=network validate
python3 scripts/aws-session.py tofu -chdir=network plan -out=network.tfplan
python3 scripts/aws-session.py tofu -chdir=network apply network.tfplan
python3 scripts/aws-session.py tofu -chdir=network output -json deployment
```

Revisa el plan antes de aplicar. Espera que termine la red; su salida debe mostrar `ready: true`, IDs de subredes, grupos y NAT. El contrato se publica después de completar las rutas y asociaciones.

## 4. Crear cómputo

```bash
cp compute/terraform.tfvars.example compute/terraform.tfvars
```

Edita `compute/terraform.tfvars`:

- Cuenta, región, proyecto y entorno deben coincidir con `network`.
- `ssh_public_key_path` debe apuntar a tu **clave pública**, nunca a la privada. Se expande `~/`.
- `app_revision` debe ser un commit publicado de 40 caracteres del repositorio público `borysinho/iac-cloud-init`. El valor inicial reproduce la revisión de CloudFormation y Pulumi.
- Conserva el parámetro público de AMI Ubuntu 24.04; cambiar distribución requiere adaptar el archivo común.

```bash
tofu -chdir=compute init
tofu -chdir=compute validate
python3 scripts/aws-session.py tofu -chdir=compute plan -out=compute.tfplan
python3 scripts/aws-session.py tofu -chdir=compute apply compute.tfplan
python3 scripts/aws-session.py tofu -chdir=compute output -json deployment
```

No introduzcas IDs de CloudFormation ni de Pulumi. Cómputo obtiene sus IDs del estado de red y verifica que corresponde a la misma cuenta, región, proyecto y entorno.

Las salidas incluyen `url`, `client_public_ip`, los IDs de EC2 y comandos SSH. El nombre de la clave pública importada tiene un prefijo y sufijo generado para evitar colisiones entre implementaciones.

## 5. Mismo cloud-init, sin copiarlo

El programa utiliza `file("${path.module}/../../cloud-init.yaml")` y sustituye exclusivamente:

- `__APP_ARCHIVE_URL__`: URL del commit publicado configurado.
- `__FRONTEND_ORIGIN__`: origen HTTP de la IP pública del cliente para el backend; localhost para la entrada no utilizada del cliente.

Se utiliza `replace`, no `templatefile`, para conservar literalmente las expresiones `${...}` de Bash y Python que ya contiene el archivo común. No es necesario regenerar plantillas ni usar el script `sync-cloud-init.py`. `aws_instance.user_data` recibe texto y el proveedor lo codifica para EC2.

El archivo compartido instala los servicios, descarga los archivos, configura el proxy de Nginx, inicializa el esquema y crea el servicio `asistencia`. Genera contraseñas en el backend y las guarda en `/opt/asistencia/.env.backend`, protegido. No se escriben contraseñas de aplicación en variables, UserData ni salidas de OpenTofu.

La salida de `tofu apply` indica que los recursos se crearon; no espera automáticamente a que termine cloud-init. Conecta por SSH como `ubuntu` usando los comandos exportados y comprueba en ambos servidores:

```bash
sudo cloud-init status --wait --long
sudo tail -n 100 /var/log/cloud-init-output.log
```

En el cliente:

```bash
sudo nginx -t
systemctl is-active nginx
curl --cacert /etc/ssl/certs/asistencia.crt -I https://127.0.0.1/
curl --cacert /etc/ssl/certs/asistencia.crt -i https://127.0.0.1/api/me
```

Esperado: página HTTP 200 y `/api/me` HTTP 401 sin sesión. En el backend, a través del cliente:

```bash
systemctl is-active mysql asistencia
node --version
npm --version
sudo mysql -e 'SHOW TABLES FROM uagrm_asistencia;'
sudo ss -lntp | grep -E ':(3306|33060)\b'
sudo grep -E '^ADMIN_(USER|PASSWORD)=' /opt/asistencia/.env.backend
```

El último comando muestra la cuenta inicial en tu terminal privada: no publiques su salida. Abre la URL exportada e ingresa con esa cuenta. MySQL debe escuchar solo en localhost. Si tu red intercepta HTTP con FortiGuard, ese bloqueo es independiente del grupo de seguridad, como se observó en la verificación de CloudFormation.

## 6. Cambios posteriores

Planifica y aplica red primero si cambias recursos que necesita cómputo. Después planifica cómputo. La referencia al estado **no impide** destruir red mientras existan consumidores: debes respetar el orden entre configuraciones.

`user_data_replace_on_change = false` conserva el comportamiento de las otras implementaciones: modificar el archivo común o el commit no garantiza que cloud-init vuelva a desplegar la aplicación en las EC2 existentes. Revisa el plan, posibles reinicios y la estrategia de actualización. El aplicador descrito en `../cloudformation/DESPLIEGUE-APLICACION.md` también funciona sobre estas EC2 Ubuntu si exportas el mismo commit y la IP pública actual; ese aplicador no depende del servicio CloudFormation.

Cambiar AMI puede reemplazar instancias y borrar sus discos raíz. Respalda MySQL antes de reemplazar o eliminar el backend. Si se detiene/inicia el cliente y cambia su IP pública, debe actualizarse el origen permitido del backend. No se añade una Elastic IP al cliente.

## 7. Pruebas locales sin AWS

Después de inicializar proveedores:

```bash
tofu fmt -recursive -check
tofu -chdir=network validate
tofu -chdir=compute validate
tofu -chdir=network test
tofu -chdir=compute test
```

Las pruebas incluyen mocks del proveedor AWS y sustituyen la lectura del estado de red; **no ejecutan operaciones reales en AWS**. Su `command = apply` se aplica exclusivamente a recursos simulados. La clave en `compute/tests/key.pub` es una fixture pública de prueba, no sirve para conectarse a un servidor.

Se comprueban red, NAT, reglas de acceso, IPs, discos, IMDSv2, CPU, origen del cliente, renderizado exacto del cloud-init común y rechazo de configuraciones inválidas. Las pruebas no acreditan cuotas, permisos, disponibilidad de AMI ni el arranque real de servicios.

## 8. Retirar solo los recursos OpenTofu

Cuando decidas retirar este laboratorio, respalda los datos y ejecuta **primero cómputo y después red**, revisando ambas operaciones:

```bash
python3 scripts/aws-session.py tofu -chdir=compute plan -destroy
python3 scripts/aws-session.py tofu -chdir=compute destroy
python3 scripts/aws-session.py tofu -chdir=network plan -destroy
python3 scripts/aws-session.py tofu -chdir=network destroy
```

Conserva los estados hasta comprobar que la retirada terminó. Verifica que se hayan eliminado NAT y su Elastic IP. Detener las EC2 no elimina esos recursos ni su consumo. No elimines recursos de CloudFormation o Pulumi para completar esta guía.

Referencias: [backend local](https://opentofu.org/docs/language/settings/backends/local/), [estado remoto](https://opentofu.org/docs/language/state/remote-state-data/), [pruebas con mocks](https://opentofu.org/docs/cli/commands/test/).

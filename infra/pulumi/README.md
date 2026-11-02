# Asistencia con Pulumi y cloud-init

La configuración actual incluye [HTTPS con certificado autofirmado](../HTTPS.md), redirección de HTTP a HTTPS y origen HTTPS en el backend. La ejecución real y la URL vigente están en [VERIFICACION-AWS.md](VERIFICACION-AWS.md). Este cambio actualiza los ejemplos HTTP de las etapas previas.

Implementación equivalente a CloudFormation, con **dos stacks del proyecto `asistencia-cloudinit`**: `network` y `compute`. El valor `layer` determina qué recursos crea cada uno. `compute` consume las salidas de `network` mediante `StackReference`.

Se conserva la configuración actual del laboratorio, incluida tu modificación de HTTP público:

| Recurso | Configuración |
|---|---|
| Red | VPC `10.42.0.0/16`, subred pública `10.42.1.0/24`, privada `10.42.2.0/24`, misma AZ |
| Internet | Internet Gateway, NAT Gateway administrado y Elastic IP del NAT |
| Cliente | Ubuntu 24.04, `t3.micro`, `10.42.1.10`, IPv4 pública dinámica, Nginx |
| Backend | Ubuntu 24.04, `t3.micro`, `10.42.2.20`, sin IP pública, Node.js 24 y MySQL local |
| Acceso | HTTPS 443 y redirección HTTP 80 desde `0.0.0.0/0`; SSH administrativo `/32`; backend 22/8090 solo desde grupo cliente |
| Discos | gp3 cifrados, 12 GiB cliente y 20 GiB backend; se eliminan con las EC2 |
| Instancias | IMDSv2 obligatorio, créditos CPU `standard` |
| Aplicación | Mismo repositorio público y commit, credenciales generadas localmente y servicio systemd |

**Esta implementación crea recursos nuevos.** No importa, modifica ni elimina la infraestructura existente de CloudFormation. Los mismos CIDR pueden existir en VPC independientes, pero ejecutar ambos laboratorios duplica sus recursos y consumo, incluido NAT. Antes de aplicar revisa créditos, plan y `python3 scripts/aws-session.py pulumi preview`. No se garantiza que los créditos cubran todos los cargos.

Los archivos de CloudFormation, tus modificaciones locales y `infra/cloud-init.yaml` se conservan sin cambios. La retirada de los recursos AWS no elimina esas plantillas locales. El entorno predeterminado de esta implementación es `cloudinit-pulumi` para distinguir sus etiquetas. No se añade una tercera EC2 ni se utiliza una EC2 como NAT.

## 1. Herramientas y autenticación

Necesitas Node.js 22 o superior, npm, Pulumi CLI y credenciales AWS temporales válidas con permisos para crear los recursos EC2/VPC del laboratorio. Si utilizas un perfil, configura `AWS_PROFILE` antes de ejecutar Pulumi. Comprueba la identidad:

```bash
aws sts get-caller-identity
```

El proveedor restringe la cuenta a `accountId` (predeterminado `222234418877`) y la región a `aws:region` (`us-east-2`). Cambia la configuración si tu destino es distinto. Pulumi utiliza la identidad autenticada; **no utiliza el rol `asistencia-cloudinit-execution` ni roles Git Sync**. La política de permisos de recursos documentada en `../cloudformation/iam/` sirve como referencia de operaciones, pero su rol de confianza es específico de CloudFormation; no cambies esa confianza para ejecutar Pulumi.

Desde esta carpeta:

```bash
cd '/home/borysquiroga/Documentos/docs/Diplomado/Módulo 2/cloud-init/infra/pulumi'
npm ci
npm run check
npm test
```

Se incluye `package-lock.json`. Las pruebas usan mocks de Pulumi: no crean recursos ni requieren credenciales AWS.

## 2. Backend de estado utilizado en este laboratorio

La ejecución real utiliza el backend local `.pulumi/state` dentro de esta carpeta, con dos estados separados y el directorio de herramientas en `.pulumi/home`. No requiere Pulumi Cloud ni un bucket S3. `scripts/aws-session.py` exporta las credenciales temporales de AWS CLI directamente al proceso Pulumi, sin imprimirlas ni guardarlas en archivos, y configura ese backend.

Usa el adaptador para administrar estos stacks:

```bash
python3 scripts/aws-session.py pulumi stack ls
python3 scripts/aws-session.py pulumi stack select network
```

El archivo `.pulumi/passphrase` protege el estado; se genera solo para un backend nuevo sin estado existente. Guarda una copia segura de ese archivo y de `.pulumi/state`, fuera de Git. No pierdas ni regeneres la contraseña de un estado existente. Los archivos `Pulumi.network.yaml` y `Pulumi.compute.yaml` contienen la configuración local y están excluidos de Git.

En este backend la referencia completa de red es `organization/asistencia-cloudinit/network`. Si decides migrar a otro backend, haz una migración de estado explícita antes de aplicar; cambiar de backend sin migrar puede provocar un segundo despliegue. No uses los estados de otras prácticas.

## 3. Stack de red

```bash
python3 scripts/aws-session.py pulumi stack init network
cp Pulumi.network.yaml.example Pulumi.network.yaml
```

Edita `Pulumi.network.yaml` y comprueba:

- `accountId` y `aws:region` corresponden a tu cuenta y región.
- `sshSourceCidr` contiene tu IP pública actual seguida de `/32`. El ejemplo conserva `181.188.164.3/32`, que está en tu configuración de CloudFormation; no se presupone que esa IP sea permanente.
- `webSourceCidr` conserva `0.0.0.0/0` para la página pública.
- `project` y `environment` serán iguales en los dos stacks.

El programa elige la primera AZ disponible. Si necesitas fijarla, configura `availabilityZone`, por ejemplo `us-east-2a`, antes de crear la red.

```bash
python3 scripts/aws-session.py pulumi preview
python3 scripts/aws-session.py pulumi up
python3 scripts/aws-session.py pulumi stack output deployment --json
```

Espera que termine la actualización. La salida `deployment` debe contener `ready: true`, IDs de VPC, subredes, grupos y NAT. Su estado indica que Pulumi terminó los recursos, no una comprobación HTTP de la aplicación.

## 4. Stack de cómputo

```bash
python3 scripts/aws-session.py pulumi stack init compute
cp Pulumi.compute.yaml.example Pulumi.compute.yaml
```

Edita `Pulumi.compute.yaml`:

- En `networkStack`, utiliza `organization/asistencia-cloudinit/network` con el backend local. Si migras a Pulumi Cloud, usa la organización correspondiente a ese backend.
- En `sshPublicKeyPath`, indica la ruta de tu clave **pública** OpenSSH; nunca la privada. El programa expande `~/`.
- Conserva `appRevision` si quieres el mismo código de CloudFormation, o usa otro commit de 40 caracteres que ya esté publicado y contenga `app/`.
- Conserva el parámetro público Ubuntu 24.04. No cambies a otra distribución sin adaptar el archivo compartido.

El programa verifica que ambos stacks coincidan en cuenta, región, proyecto y entorno. También exige que `network` esté completado. No copies IDs de recursos ni uses los de CloudFormation.

```bash
python3 scripts/aws-session.py pulumi preview
python3 scripts/aws-session.py pulumi up
python3 scripts/aws-session.py pulumi stack output deployment --json
```

La salida incluye `url`, `clientPublicIp`, IDs de ambas EC2 y comandos `clientSsh` y `backendSsh`. La clave se importa con un nombre generado por Pulumi para evitar colisiones con CloudFormation.

## 5. Cloud-init y la aplicación

`src/cloud-init.ts` **lee directamente `../cloud-init.yaml`**, la misma fuente de CloudFormation. Solo resuelve:

- `__APP_ARCHIVE_URL__`: URL del commit público configurado.
- `__FRONTEND_ORIGIN__`: `https://IP_PUBLICA_CLIENTE` para el backend. En el cliente se usa localhost porque esa entrada no interviene en su despliegue.

No se genera ni guarda una segunda copia de cloud-init y no se ejecuta `sync-cloud-init.py`: ese adaptador es propio de CloudFormation. Pulumi entrega el texto resuelto a `Instance.userData`; el proveedor realiza la codificación Base64.

El backend depende de la IP pública del cliente. Al primer arranque, el archivo común instala servicios, descarga y copia los archivos, configura Nginx y su proxy, crea la base/usuario SQL, genera contraseñas protegidas y habilita `asistencia`. No se publican contraseñas en las salidas ni en el estado Pulumi.

Pulumi no espera automáticamente a que termine cloud-init. Después de `python3 scripts/aws-session.py pulumi up`, conecta por SSH usando las salidas y ejecuta en ambos:

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

Esperado: página HTTP 200 y `/api/me` HTTP 401 sin token. En el backend, mediante el bastión:

```bash
systemctl is-active mysql asistencia
node --version
npm --version
sudo mysql -e 'SHOW TABLES FROM uagrm_asistencia;'
sudo ss -lntp | grep -E ':(3306|33060)\b'
sudo grep -E '^ADMIN_(USER|PASSWORD)=' /opt/asistencia/.env.backend
```

El último comando muestra la cuenta inicial en tu terminal privada; no publiques su salida. Abre la URL exportada e inicia sesión. MySQL debe escuchar únicamente en localhost. Si tu red intercepta HTTP mediante FortiGuard, el bloqueo puede ser independiente de AWS, como se documentó en la verificación de CloudFormation; no se cambian los filtros del visitante.

## 6. Cambios y actualizaciones

Selecciona el stack correcto antes de cada operación:

```bash
python3 scripts/aws-session.py pulumi stack select network
python3 scripts/aws-session.py pulumi preview
# Para aplicar un cambio de red revisado: python3 scripts/aws-session.py pulumi up
python3 scripts/aws-session.py pulumi stack select compute
python3 scripts/aws-session.py pulumi preview
```

`userDataReplaceOnChange` está deshabilitado para mantener el comportamiento de la configuración actual: cambiar el archivo común o `appRevision` no implica que cloud-init vuelva a desplegar el código en instancias existentes. Revisa los cambios de UserData, posibles reinicios y la estrategia de actualización; no presupongas una instalación automática después del primer arranque. La guía `../cloudformation/DESPLIEGUE-APLICACION.md` describe el aplicador para las EC2 Ubuntu existentes; sus comandos pueden adaptarse a las IP y al commit exportados por Pulumi. Ese aplicador no depende del servicio CloudFormation.

Cambiar AMI puede reemplazar las EC2 y eliminar sus discos raíz. Respalda MySQL antes de reemplazar o eliminar el backend. Detener/iniciar el cliente puede cambiar su IP pública y requerir actualizar `FRONTEND_ORIGINS` del backend. Mantén la red y NAT completados antes de crear o actualizar cómputo.

## 7. Retirar solo este laboratorio

Cuando decidas eliminar los recursos **de Pulumi**, respalda los datos y ejecuta primero `python3 scripts/aws-session.py pulumi destroy` en `compute`; después, en `network`. Un StackReference no impide automáticamente destruir la red mientras existan consumidores: respeta este orden. Confirma que también se eliminaron NAT y su EIP; detener las EC2 no elimina el NAT ni su consumo.

No ejecutes esos comandos sobre stacks de otra práctica ni elimines recursos de CloudFormation para completar esta guía.

## Validación y límites

Las pruebas locales verifican la red, HTTP público, SSH limitado, aislamiento del backend, NAT, cifrado, IMDSv2, créditos CPU y que el UserData sea exactamente el archivo común con solo sus dos entradas resueltas. También se comprueba TypeScript. Los mocks no acreditan disponibilidad de AMI, permisos, cuotas ni un despliegue real.

Referencias: [StackReference](https://www.pulumi.com/docs/iac/concepts/stacks/), [EC2 Instance](https://www.pulumi.com/registry/packages/aws/api-docs/ec2/instance/), [NAT Gateway](https://www.pulumi.com/registry/packages/aws/api-docs/ec2/natgateway/).

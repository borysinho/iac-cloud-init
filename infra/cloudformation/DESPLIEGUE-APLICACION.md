# Desplegar la aplicación con cloud-init

Actualización: la fuente común ahora configura [HTTPS con certificado autofirmado](../HTTPS.md). Los comandos de etapas HTTP anteriores deben usar HTTPS y el certificado público como confianza explícita; el origen del backend ahora empieza con `https://`.

El archivo común `../cloud-init.yaml` ahora instala servicios y copia la aplicación desde el repositorio público `borysinho/iac-cloud-init`. Mantiene las dos pilas, dos servidores y el NAT Gateway existente. No requiere nuevos roles, buckets ni credenciales de Git.

## Qué instala

| Equipo | Archivos y configuración |
|---|---|
| Cliente `10.42.1.10` | Los cuatro archivos de `app/public/` en `/var/www/asistencia`; configuración Nginx en `/etc/nginx/conf.d/asistencia.conf`; proxy `/api/` a `http://10.42.2.20:8090` |
| Backend `10.42.2.20` | `src/`, `scripts/`, `database/`, unidad systemd y archivos npm en `/opt/asistencia`; dependencias con `npm ci --omit=dev`; esquema y administrador; servicio `asistencia` habilitado |

Se retira el sitio predeterminado de Nginx. MySQL sigue escuchando en localhost. El instalador crea la base `uagrm_asistencia` y un usuario SQL exclusivo. Las contraseñas de base y administración se generan en el backend con aleatoriedad criptográfica y se guardan en `/opt/asistencia/.env.backend`, con propietario `root:asistencia` y modo `640`. No se incluyen en Git, UserData ni registros.

## Entradas de despliegue

`AppRevision`, en `deployments/compute-lab.yaml`, selecciona un **commit publicado** del repositorio, de 40 caracteres hexadecimales. El valor inicial corresponde a la revisión de la aplicación que ya estaba en este laboratorio. Su carpeta `app/` debe contener el código, lockfile, SQL y las configuraciones de Nginx/systemd. Una revisión local sin publicar o un repositorio privado impedirá descargar el archivo.

El archivo común tiene dos entradas neutrales: `__APP_ARCHIVE_URL__` y `__FRONTEND_ORIGIN__`. Las tres herramientas deben partir de esta misma fuente y resolver esas entradas. El adaptador CloudFormation utiliza `Fn::Join` y `Fn::Base64`: compone la URL del commit y entrega al backend el origen `http://IP_PUBLICA_CLIENTE`, obtenido de la EC2 cliente. El cliente no se referencia a sí mismo en UserData; su entrada de origen no se utiliza.

No se modifican los controles CORS de la aplicación ni se oculta el origen real de las peticiones. Si posteriormente agregas dominio/HTTPS, actualiza el origen permitido del backend junto con Nginx.

## Instancias nuevas

1. Conserva los CIDR y la clave pública ya configurados en `deployments/`.
2. Revisa `AppRevision` y publica los archivos actualizados en la rama Git Sync.
3. Antes de publicar `compute.yaml`, regénéralo desde la raíz de `cloud-init/`:

   ```bash
   python3 infra/cloudformation/scripts/sync-cloud-init.py
   python3 infra/cloudformation/scripts/sync-cloud-init.py --check
   ```

4. Con la pila de red completada, crea cómputo. En el primer arranque se ejecutan instalación y despliegue.
5. Comprueba cloud-init y los servicios como se indica al final de este documento. `CREATE_COMPLETE` todavía no espera a que termine cloud-init.

## Tus EC2 ya están creadas: aplicar sin reemplazarlas

Actualizar UserData no vuelve a ejecutar automáticamente los módulos del primer arranque. Para estas instancias se prepara el mismo documento resuelto y se aplican **solo sus tres archivos de bootstrap**, ejecutando después el instalador. No se limpia el estado de cloud-init ni se reinstala el sistema operativo.

1. Publica los cambios en la rama sincronizada y deja que termine la actualización de cómputo. Revisa su change set: si solicita reemplazar una EC2, revisa la causa antes de aplicarlo. El cambio de UserData puede detener/iniciar las EC2 y cambiar la IP pública del cliente.
2. Obtén la IP pública **actual** del cliente en Outputs. En tu equipo local, desde `cloud-init/`, define:

   ```bash
   CLIENT_PUBLIC=REEMPLAZAR_POR_IP_PUBLICA_ACTUAL
   SSH_KEY="$HOME/globomatics-ec2"
   python3 infra/cloudformation/scripts/sync-cloud-init.py \
     --render-dir /tmp/asistencia-update \
     --client-public-ip "$CLIENT_PUBLIC"
   ```

   El exportador usa el `AppRevision` predeterminado de `compute.yaml`. Si modificaste ese parámetro en el archivo de despliegue, añade `--revision COMMIT_PUBLICADO` con el mismo valor que tenga la pila.

3. Copia el archivo del cliente y el aplicador:

   ```bash
   scp -i "$SSH_KEY" \
     /tmp/asistencia-update/client-cloud-init.yaml \
     infra/cloudformation/scripts/apply-cloud-init-update.py \
     "ubuntu@$CLIENT_PUBLIC:/tmp/"
   ssh -t -i "$SSH_KEY" "ubuntu@$CLIENT_PUBLIC" \
     'sudo python3 /tmp/apply-cloud-init-update.py /tmp/client-cloud-init.yaml'
   ```

4. Copia y aplica en el backend a través del cliente. Ejecuta desde la misma terminal local:

   ```bash
   scp -i "$SSH_KEY" \
     -o "ProxyCommand=ssh -i $SSH_KEY -W %h:%p ubuntu@$CLIENT_PUBLIC" \
     /tmp/asistencia-update/backend-cloud-init.yaml \
     infra/cloudformation/scripts/apply-cloud-init-update.py \
     ubuntu@10.42.2.20:/tmp/
   ssh -t -i "$SSH_KEY" \
     -o "ProxyCommand=ssh -i $SSH_KEY -W %h:%p ubuntu@$CLIENT_PUBLIC" \
     ubuntu@10.42.2.20 \
     'sudo python3 /tmp/apply-cloud-init-update.py /tmp/backend-cloud-init.yaml'
   ```

El aplicador requiere Ubuntu 24.04 con cloud-init y su dependencia Python YAML, ya presentes en la AMI utilizada. Espera a que termine cloud-init y se detiene si ese arranque tiene errores; resuelve primero la causa indicada en los registros. No lo ejecutes con sudo en tu computadora.

Al repetir el despliegue se conservan las contraseñas guardadas. El inicializador crea tablas faltantes sin borrar la base y conserva la contraseña del administrador existente; no realiza migraciones de columnas. Reinstalar dependencias y reiniciar la API puede interrumpir solicitudes y elimina las sesiones en memoria. Respaldar la base antes de actualizar código en uso.

## Comprobar y entrar

En el cliente:

```bash
sudo nginx -t
systemctl is-active nginx
curl -I http://127.0.0.1/
curl -i --max-time 10 http://127.0.0.1/api/me
```

`/` debe responder HTTP 200 y mostrar asistencia, no la bienvenida de Nginx. `/api/me` debe responder **401** sin token: confirma que el proxy llega a la API.

En el backend:

```bash
systemctl is-active mysql asistencia
sudo journalctl -u asistencia -n 50 --no-pager
sudo mysql -e 'SHOW TABLES FROM uagrm_asistencia;'
```

Para consultar tu cuenta inicial, desde una sesión SSH al **backend**:

```bash
sudo grep -E '^ADMIN_(USER|PASSWORD)=' /opt/asistencia/.env.backend
```

Ese comando muestra la contraseña en tu terminal; no publiques su salida. Abre `http://IP_PUBLICA_CLIENTE` desde una IP autorizada en `WebSourceCidr` e ingresa con esas credenciales. Después crea un módulo e importa estudiantes y fechas siguiendo `app/README.md`. HTTP queda limitado al laboratorio; HTTPS y dominio no están configurados en esta etapa.

Si el cliente cambia de IP pública, vuelve a exportar los documentos con la nueva IP y aplica la actualización al backend para actualizar `FRONTEND_ORIGINS`; reinicia el servicio mediante el instalador. No necesitas regenerar las contraseñas.

## Si falla

| Síntoma | Revisar |
|---|---|
| Descarga HTTP 404 | Repositorio público, commit publicado y `AppRevision` correcto |
| Instalación npm falla | NAT, DNS, registro npm, espacio y log de cloud-init |
| Nginx muestra bienvenida | Actualización del cliente y eliminación de su sitio predeterminado |
| HTTP 502 | Servicio `asistencia`, escucha en `10.42.2.20:8090`, configuración del proxy y grupos de seguridad |
| HTTP 403 al iniciar sesión | IP actual del cliente y `FRONTEND_ORIGINS` del backend |
| No acepta una nueva contraseña tras actualizar | El administrador existente conserva su hash; cambiar el entorno no cambia su contraseña |

Validación local:

```bash
python3 infra/cloudformation/scripts/sync-cloud-init.py --check
python3 infra/cloudformation/tests/test_bootstrap.py
```

Las pruebas verifican renderizado, tamaño, sintaxis Bash, copia de archivos, proxy y conservación de credenciales con servicios simulados. No acreditan una instalación real de MySQL/Node/Nginx ni un despliegue en AWS. La validación con cfn-lint/cfn-guard sigue pendiente porque no están instalados en el entorno de trabajo.

Referencias: [Fn::Join](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/intrinsic-function-reference-join.html), [UserData y actualizaciones EC2](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ec2-instance.html).

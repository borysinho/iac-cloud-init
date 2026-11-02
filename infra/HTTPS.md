# HTTPS con certificado autofirmado

El archivo compartido `cloud-init.yaml` configura ahora HTTPS para las tres herramientas. El cliente genera localmente un certificado autofirmado con OpenSSL; su SAN contiene la IP pública obtenida mediante IMDSv2, `10.42.1.10` y `127.0.0.1`. Se utiliza TLS 1.2/1.3 y se conserva el proxy interno hacia `http://10.42.2.20:8090`.

- HTTP 80 permanece abierto y devuelve una redirección 301 hacia HTTPS.
- HTTPS 443 utiliza el mismo CIDR web público configurado en cada herramienta.
- SSH y los accesos del backend no se amplían.
- El backend utiliza `FRONTEND_ORIGINS=https://IP_PUBLICA_CLIENTE`.
- No se crean balanceadores, dominios ni recursos ACM.

## Certificado y confianza

El navegador mostrará una advertencia porque el certificado no está firmado por una autoridad pública. La confianza debe establecerse expresamente en el equipo/navegador que lo utiliza, conforme a sus políticas. No se ha modificado el almacén de confianza del equipo local ni se han cambiado filtros de red.

En el cliente:

| Archivo | Uso y permisos |
|---|---|
| `/etc/ssl/certs/asistencia.crt` | Certificado público, modo `644` |
| `/etc/ssl/private/asistencia.key` | Clave privada, `root:root`, modo `600`; no copiar ni publicar |

El certificado tiene una validez inicial de 365 días. Al repetir el despliegue del cliente se conserva si coincide con la IP actual y quedan más de 30 días; en caso contrario se regenera. No hay un servicio de renovación periódica. Si cambia la IP pública, regenerar el certificado y actualizar el origen del backend.

Consulta sus datos sin mostrar la clave privada:

```bash
sudo openssl x509 -in /etc/ssl/certs/asistencia.crt \
  -noout -subject -issuer -dates -ext subjectAltName -fingerprint -sha256
```

## Comprobación en el cliente

```bash
sudo nginx -t
curl -I http://127.0.0.1/
curl --cacert /etc/ssl/certs/asistencia.crt -I https://127.0.0.1/
curl --cacert /etc/ssl/certs/asistencia.crt -i https://127.0.0.1/api/me
```

Esperado: HTTP 301, HTTPS 200 y API 401 sin sesión. `--cacert` permite verificar explícitamente el certificado y el nombre/IP; no deshabilita la validación TLS.

Para probar desde otra máquina, obtén **solo el certificado público** mediante SSH autenticado y utilízalo con `curl --cacert RUTA_CERTIFICADO https://IP_PUBLICA/`. No copies la clave privada.

## Instancias existentes

Actualizar UserData no ejecuta automáticamente los módulos de primer arranque. En la ejecución real de Pulumi se actualizaron los archivos de bootstrap y se aplicó únicamente la parte TLS al cliente; en el backend se cambió el origen y se reinició la API. Se conservaron MySQL y sus contraseñas.

El aplicador operativo está en `pulumi/scripts/enable-https-existing.py`; recibe un JSON resuelto con `role`, `origin` y los tres `write_files` del archivo compartido, comprueba la IP privada del equipo y no ejecuta la instalación completa de la aplicación. Debe ejecutarse con sudo en la EC2 correspondiente. Los payloads de esta ejecución están excluidos de Git en `pulumi/.pulumi/migration/`.

La actualización de UserData reinició las EC2 sin reemplazarlas y cambió la IP pública del cliente. El resultado y la URL vigente se encuentran en [la verificación vigente de OpenTofu](opentofu/VERIFICACION-AWS.md). Las instrucciones HTTP de etapas anteriores deben interpretarse junto a este cambio: el acceso final de la aplicación es HTTPS.

Referencias: [HTTPS en Nginx](https://nginx.org/en/docs/http/configuring_https_servers.html), [certificados OpenSSL y SAN](https://docs.openssl.org/3.4/man1/openssl-req/).

# Verificación real en AWS · 1 de noviembre de 2026

Cuenta: `222234418877`. Región: `us-east-2`.

## Causa encontrada

Las pilas recreadas solo contenían `GitSyncSetupWaitCondition`, sin red ni EC2. La sincronización Git todavía mostraba como exitosa una ejecución anterior a la creación de las nuevas pilas. No se encontraron errores AccessDenied en ellas; el rol de ejecución ya tenía los permisos requeridos.

## Reparación aplicada

- Se revisaron y ejecutaron change sets sobre las dos pilas existentes, primero red y luego cómputo.
- Solo se agregaron los recursos del laboratorio y se retiraron sus marcadores vacíos. No se ampliaron permisos IAM ni se modificaron recursos de otras prácticas.
- Se restablecieron las vinculaciones Git Sync con su misma rama, roles y archivos.
- El NAT Gateway administrado quedó disponible; ninguna EC2 realiza NAT.
- Ambas instancias ejecutaron automáticamente el cloud-init completo, sin copiar archivos ni configurar servicios manualmente después del arranque.

| Recurso | Identificador |
|---|---|
| Pila de red | `asistencia-cloudinit-network` · `UPDATE_COMPLETE` |
| Pila de cómputo | `asistencia-cloudinit-compute` · `UPDATE_COMPLETE` |
| VPC | `vpc-0247c3424f5b4dbf3` |
| NAT Gateway | `nat-06bb5cae58e8bd193` |
| Cliente | `i-0c65d74feace79264` · `10.42.1.10` |
| Backend | `i-0f803766347a90499` · `10.42.2.20` |
| IP pública del cliente | `18.191.31.68` |

La dirección pública puede cambiar si se detiene/inicia el cliente. No se añadió una Elastic IP al cliente.

## Pruebas realizadas

- Cloud-init cliente y backend: `done`, sin errores ni errores recuperables.
- Nginx: activo y configuración válida.
- Página y archivos estáticos: HTTP 200.
- IP pública consultada desde AWS: HTTP 200.
- Proxy `/api/me`: HTTP 401 sin sesión, como corresponde.
- Login del administrador y consulta del dashboard: HTTP 200.
- Generación y descarga de la plantilla Excel: HTTP 200 y archivo ZIP/XLSX válido.
- La sesión de prueba se cerró; no se crearon módulos ni asistencias.
- Las credenciales se leyeron únicamente dentro del backend para la prueba y no se imprimieron.

## Bloqueo ajeno a AWS

Desde la conexión local, las peticiones HTTP a la IP pública fueron interceptadas por **FortiGuard Intrusion Prevention**, con HTTP 403 y el mensaje **Access Blocked**, categoría **Unrated**. La respuesta no procede de Nginx. Se debe solicitar al administrador de esa red que permita `http://18.191.31.68/`. No se desactivó ni se eludió el filtro.

## GitHub

El remoto estaba configurado por HTTPS, lo que explica la solicitud de autenticación. Se probó SSH con la llave disponible `~/.ssh/id_ed25519`, pero GitHub rechazó su clave pública. No se encontró otra llave de GitHub en las carpetas del proyecto; las encontradas del Módulo 1 corresponden a EC2.

No se publicaron cambios nuevos en GitHub desde esta reparación. La aplicación se descargó del commit público configurado en `AppRevision`. El remoto local se conserva por HTTPS hasta disponer de la llave correcta o completar su autenticación. La nueva explicación de recreación de pilas está en `GUIA-PASO-A-PASO.md`.

## Acceso desde cualquier IPv4 comprobado

Se verificaron nuevamente las reglas activas: `sg-01445212d5fba368f` permite TCP 80 desde `0.0.0.0/0`; la ACL de la subred permite entrada y salida IPv4. Nginx escucha en el puerto 80 sin listas `allow`/`deny`, UFW está inactivo y la IP pública responde HTTP 200 desde AWS. SSH conserva su origen administrativo `/32`.

`WebSourceCidr` también queda con valor predeterminado `0.0.0.0/0` en la plantilla local, además del archivo de despliegue. No fue necesario ampliar reglas activas en AWS. El despliegue utiliza IPv4; no tiene configurado acceso IPv6. Los filtros de la red del visitante, como FortiGuard, pueden seguir bloqueando la URL independientemente del acceso público en AWS.

# Migración real de Pulumi a OpenTofu · 1 de noviembre de 2026

Cuenta `222234418877`, región `us-east-2`. Se retiró la infraestructura de Pulumi y se creó la configuración equivalente con OpenTofu. La aplicación quedó funcionando por HTTPS, con certificado autofirmado generado automáticamente por el mismo cloud-init compartido.

URL vigente: **https://18.119.120.80/**

## Retirada completa de Pulumi

Se revisaron los inventarios y las vistas previas de eliminación de los stacks `compute` y `network`. Se ejecutó primero `pulumi destroy` en cómputo y después en red.

| Recurso anterior | Resultado comprobado |
|---|---|
| Cliente `i-0d828424ce73927db` | `terminated` |
| Backend `i-068f1e1ed9752eb29` | `terminated` |
| NAT `nat-095a25f90ba1fb48f` | `deleted` |
| Elastic IP `eipalloc-0e22463fe0c4a2db4` | Liberada, sin asignación en la cuenta |
| VPC `vpc-02527ca1694b96b9f` | Eliminada |
| Clave pública, subredes, rutas y grupos de Pulumi | Eliminados por la operación de retirada |

Se conservaron los archivos del proyecto, la clave SSH privada local y los registros locales de historial/configuración de Pulumi; esos registros no son recursos activos en AWS. No se retiraron recursos de otras prácticas ni se modificaron los roles IAM manuales. La base anterior se eliminó con el disco raíz del backend; no hubo migración de datos.

## Infraestructura OpenTofu creada

Se inicializaron dos estados locales independientes. Se aplicó el plan guardado de red antes de planificar y aplicar cómputo.

| Elemento | Identificador o configuración |
|---|---|
| Red | `network/`, 14 recursos creados |
| Cómputo | `compute/`, 3 recursos creados |
| VPC | `vpc-0824ccc6dd737decb` |
| Subred pública | `subnet-004c08291789301e4` |
| Subred privada | `subnet-0276524db21fbfa79` |
| NAT Gateway | `nat-0d83b6e308b7514e8`, disponible |
| Elastic IP del NAT | `eipalloc-0117ecc55f52fa8cd` |
| Cliente | `i-08bc59223e8c3b6ab` · `10.42.1.10` |
| Backend | `i-0de5fecce22589148` · `10.42.2.20`, sin IP pública |
| Grupo cliente | `sg-019f5865bf90def4c` |
| Grupo backend | `sg-0b655b95fcea76096` |
| Clave pública importada | `key-asistencia-cloudinit-opentofu-2d0e37d3dd6f6b363ec4783a05` |
| Revisión de aplicación | `9e4d440276547607498f8aa3342c6234bb030f45` |
| URL | **https://18.119.120.80/** |

Se verificaron directamente en AWS los dos servidores `t3.micro`, sus IPs y subredes, ausencia de IP pública en el backend, IMDSv2, créditos CPU `standard`, discos gp3 cifrados de 12/20 GiB, reglas de seguridad y ruta privada por NAT. HTTP/HTTPS permanecen públicos; SSH administrativo conserva `181.188.164.3/32`, confirmado como la IP pública actual al desplegar. El backend recibe SSH y API 8090 únicamente desde el grupo cliente.

Se comparó el UserData entregado a ambas EC2 con `infra/cloud-init.yaml`, resolviendo exclusivamente la URL del código y el origen HTTPS. No se creó una copia alternativa de cloud-init.

## Arranque y servicios

- Cliente: cloud-init `done`, sin errores ni errores recuperables; Nginx activo y configuración válida.
- Backend: cloud-init `done`, sin errores ni errores recuperables; MySQL y `asistencia` activos.
- Node.js `v24.22.2` y npm `11.19.1` instalados.
- MySQL escucha solo en `127.0.0.1:3306` y `127.0.0.1:33060`; la API en `10.42.2.20:8090`.
- `.env.backend`: propietario `root:asistencia`, modo `640`.
- Clave privada TLS: `root:root`, modo `600`, conservada únicamente en el cliente.

La aplicación, el proxy, la base y el certificado se configuraron automáticamente durante el primer arranque. Después del despliegue solo se consultaron estados, se obtuvo el certificado público para validación y se ejecutaron pruebas funcionales; no fue necesario copiar manualmente la aplicación ni configurar servicios en las EC2.

## Pruebas funcionales HTTPS

Las pruebas se ejecutaron desde AWS, con el certificado público como confianza explícita y validando su cadena e IP. No se deshabilitó la verificación TLS ni se realizaron análisis del firewall de la red local.

| Comprobación | Resultado |
|---|---|
| Página `/` | HTTP 200 sobre HTTPS |
| `/app.js`, `/styles.css`, `/config.js` | HTTP 200 sobre HTTPS |
| `/api/me` sin sesión | HTTP 401 |
| Login administrativo y dashboard | HTTP 200 |
| Plantilla de estudiantes | HTTP 200, archivo ZIP/XLSX válido |
| Cierre de la sesión | HTTP 200 |

No se crearon módulos, estudiantes ni asistencias de prueba. Las credenciales se leyeron solo dentro del backend y no se imprimieron ni se copiaron fuera de él. La prueba cubre página, recursos estáticos, proxy y API; no incluye una prueba visual interactiva en navegador.

## Certificado autofirmado

El certificado incluye SAN para `18.119.120.80`, `10.42.1.10` y `127.0.0.1`, con validez inicial de 365 días. Su huella pública SHA-256 es:

```text
2D:9C:04:DE:15:4A:E3:0F:11:44:E9:89:9B:1C:A9:20:8C:9C:F2:A3:9A:8E:64:AC:13:E8:07:D6:DB:20:95:B9
```

El navegador mostrará una advertencia hasta que confíes expresamente en este nuevo certificado. No se modificó el almacén de confianza local. La clave privada anterior de Pulumi no se reutilizó: desapareció con su cliente. Consulta [HTTPS](../HTTPS.md) para rutas, verificación y renovación.

## Estado y comprobación final

Se ejecutó `tofu plan -detailed-exitcode` en ambos directorios tras el despliegue. Ambos terminaron con código `0`: **No changes. Your infrastructure matches the configuration.** No quedaron cambios pendientes.

Los estados son `network/terraform.tfstate` y `compute/terraform.tfstate`. Estados, planes y configuración local tienen modo `600` y están excluidos de Git. El adaptador `scripts/aws-session.py` entrega credenciales temporales a OpenTofu solo en memoria y establece `umask 077` para los archivos nuevos.

Desde `infra/opentofu/` puedes consultar el despliegue:

```bash
python3 scripts/aws-session.py tofu -chdir=network output -json deployment
python3 scripts/aws-session.py tofu -chdir=compute output -json deployment
python3 scripts/aws-session.py tofu -chdir=network plan
python3 scripts/aws-session.py tofu -chdir=compute plan
```

Se conservaron los estados previos exportados de Pulumi y las evidencias operativas en `tmp/migration/`, excluido de Git. Respalda de forma segura los estados activos de OpenTofu: perderlos no elimina los recursos AWS.

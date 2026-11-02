# Migración real de CloudFormation a Pulumi · 1 de noviembre de 2026

**Actualización:** la infraestructura descrita en esta verificación fue retirada después, por solicitud del usuario. El despliegue activo ahora utiliza [OpenTofu](../opentofu/VERIFICACION-AWS.md). Este documento conserva la evidencia histórica de Pulumi.

Cuenta `222234418877`, región `us-east-2`. Se ejecutó la retirada solicitada, se crearon los dos stacks de Pulumi y se comprobó la aplicación. Después se añadió HTTPS con certificado autofirmado, sin crear una EC2 NAT ni otros servicios de terminación TLS.

## Retirada de CloudFormation

Se inventariaron las dos pilas y se comprobó que sus exportaciones no tuvieran consumidores ajenos al laboratorio. Se retiraron exclusivamente sus dos vinculaciones Git Sync. Se eliminaron primero `asistencia-cloudinit-compute` y luego `asistencia-cloudinit-network`, esperando su finalización.

Comprobación posterior:

| Recurso anterior | Resultado |
|---|---|
| Las dos pilas CloudFormation | Sin pilas activas con esos nombres |
| EC2 `i-0c65d74feace79264` e `i-0f803766347a90499` | `terminated` |
| NAT `nat-06bb5cae58e8bd193` | `deleted` |
| Elastic IP `3.138.240.11` | Sin asignación en la cuenta |
| VPC `vpc-0247c3424f5b4dbf3` | Eliminada |
| Clave pública AWS `key-asistencia-cloudinit-compute` | Eliminada; la clave privada local se conserva |

No se eliminaron las plantillas locales, los roles IAM manuales ni la conexión Git compartida. La base alojada en el disco raíz del backend anterior se eliminó con esa instancia; el despliegue de Pulumi inicializó una base nueva, no migró datos.

## Recursos de Pulumi

| Elemento | Identificador o configuración |
|---|---|
| Proyecto | `asistencia-cloudinit` |
| Estados | `network` y `compute` |
| VPC | `vpc-02527ca1694b96b9f` |
| Subred pública | `subnet-05909388e8e1cad39` |
| Subred privada | `subnet-00118ffdaa374f0b6` |
| NAT Gateway | `nat-095a25f90ba1fb48f`, disponible |
| Cliente | `i-0d828424ce73927db` · `10.42.1.10` |
| Backend | `i-068f1e1ed9752eb29` · `10.42.2.20`, sin IP pública |
| Grupo del cliente | `sg-04acafca15a59df11` |
| Grupo del backend | `sg-01ac6beae63557fd8` |
| Revisión de la aplicación | `9e4d440276547607498f8aa3342c6234bb030f45` |
| URL vigente | **https://3.16.81.1/** |

El cliente tuvo inicialmente `3.144.9.198`; la actualización de UserData para HTTPS lo detuvo/inició y cambió su IP pública. Ambas EC2 conservan los mismos IDs y discos tras esa actualización.

Se verificaron en AWS las IPs, subredes, grupos, HTTP/HTTPS público, SSH administrativo `/32`, API solo desde grupo cliente, discos gp3 cifrados de 12/20 GiB, IMDSv2, CPU `standard`, NAT disponible y ruta privada hacia NAT. Se comparó el UserData de ambas EC2 con la fuente común y sus dos entradas resueltas.

## Servicios y pruebas funcionales

Cloud-init terminó en las dos instancias con `status: done`, `errors: []` y sin errores recuperables. Nginx validó su configuración. MySQL y `asistencia` quedaron activos; MySQL escucha únicamente en `127.0.0.1:3306` y `127.0.0.1:33060`. El archivo `.env.backend` mantiene propietario `root:asistencia` y modo `640`.

Se comprobó primero HTTP y después HTTPS. La prueba final HTTPS se ejecutó desde AWS, confiando explícitamente en el certificado público y manteniendo la verificación TLS de cadena e IP:

| Prueba | Resultado |
|---|---|
| Página `/` y archivos JS/CSS/config | HTTP 200 sobre HTTPS |
| `/api/me` sin token | HTTP 401 |
| Login administrativo y dashboard | HTTP 200 |
| Plantilla de estudiantes | HTTP 200, ZIP/XLSX válido |
| Cierre de sesión | HTTP 200 |
| HTTP del cliente | Redirección 301 a HTTPS |

No se crearon módulos, estudiantes ni asistencias de prueba. Las credenciales se leyeron solo dentro del backend y no se imprimieron ni se guardaron fuera de la instancia. No se instaló un navegador remoto ni se realizó una prueba visual interactiva: la comprobación cubre página, archivos estáticos, proxy y operaciones funcionales de API.

## Certificado autofirmado

Se generó y quedó en el cliente. Su clave privada no se copió fuera de él y tiene modo `600`, propietario `root:root`. El certificado incluye las IPs `3.16.81.1`, `10.42.1.10` y `127.0.0.1`, con validez de un año.

Huella SHA-256 del certificado público:

```text
2A:FD:48:E5:50:52:10:5C:01:35:92:F1:32:FB:FA:3A:39:D4:3F:B3:F0:76:95:B4:18:58:0F:AB:2C:A6:4E:15
```

El navegador mostrará una advertencia de confianza hasta que el usuario confíe expresamente en el certificado. No se modificaron el firewall ni el almacén de certificados del equipo local. Consulta [HTTPS](../HTTPS.md) para las rutas del certificado, comprobaciones y renovación.

## Estado y operación posterior

El backend utilizado es local, en `infra/pulumi/.pulumi/state`. El adaptador `scripts/aws-session.py` usa credenciales temporales de AWS CLI en memoria y la configuración local del laboratorio. Para revisar o administrar los stacks:

```bash
python3 scripts/aws-session.py pulumi stack ls
python3 scripts/aws-session.py pulumi preview --stack network
python3 scripts/aws-session.py pulumi preview --stack compute
```

Los archivos de configuración local, estado, planes, contraseña de cifrado y evidencias operativas quedan excluidos de Git. Respalda de forma segura `.pulumi/state` y `.pulumi/passphrase`. La documentación y los scripts no contienen contraseñas ni claves privadas.

## Comprobación final de estado

Se ejecutó `pulumi preview --expect-no-changes` mediante el adaptador en ambos stacks: `network` terminó con 16 elementos sin cambios y `compute` con 5 elementos sin cambios. No quedaron operaciones pendientes. También pasaron la comprobación TypeScript, las pruebas de Pulumi con mocks, las pruebas del bootstrap HTTPS y las cinco pruebas de OpenTofu con mocks. Las configuraciones CloudFormation y OpenTofu se actualizaron localmente para mantener el HTTPS del mismo archivo compartido; no se volvieron a desplegar recursos de esas herramientas.

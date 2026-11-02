# Infraestructura

Las tres implementaciones utilizan `cloud-init.yaml` como fuente única para instalar los servicios y desplegar la aplicación con HTTPS autofirmado.

- `cloudformation/`: dos pilas de red y cómputo, plantillas y guías; infraestructura AWS retirada tras su validación.
- `pulumi/`: dos stacks equivalentes; infraestructura AWS retirada después de su validación.
- `opentofu/`: dos configuraciones y estados independientes; **despliegue activo**.
- `HTTPS.md`: certificado, confianza y renovación.

La aplicación permanece separada en `../app/`. Estado vigente, recursos y pruebas: [verificación de OpenTofu](opentofu/VERIFICACION-AWS.md).

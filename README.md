# Control de asistencia con cloud-init

Base del laboratorio para configurar servidores con cloud-init, manteniendo la aplicación y la infraestructura separadas.

```text
cloud-init/
├── app/
│   ├── database/             Esquema SQL
│   ├── deploy/               Nginx y unidad systemd de la aplicación
│   ├── docs/                 Documentación y material de referencia
│   ├── public/               Cliente web estático
│   ├── scripts/              Inicialización de la base de datos
│   ├── src/                  Backend Node.js
│   ├── tests/                Pruebas existentes
│   ├── .env.backend.example  Plantilla de configuración
│   ├── package.json
│   ├── package-lock.json
│   └── README.md
└── infra/
    ├── opentofu/
    ├── pulumi/
    └── cloudformation/
```

## Paso 1: estructura y aplicación

Se copió la aplicación de la carpeta hermana `asistencia/`, conservando código, dependencias declaradas y su archivo de bloqueo, esquema, pruebas, documentación y archivos de despliegue. La copia mantiene el comportamiento de la aplicación original.

Se excluyeron `asistencia/infra/`, el historial Git, las credenciales y configuraciones locales (`.env.backend`, `.env.frontend`, `.aws/`), las dependencias instaladas (`node_modules/`), archivos del editor, temporales y resultados generados (`tmp/`, `out/`). La carpeta vacía `frontend/` tampoco se necesita: el cliente está en `public/`.

Los archivos de `app/deploy/` pertenecen a la aplicación: definen cómo ejecutarla con systemd y servirla con Nginx. La creación de recursos se mantendrá en `infra/`.

Consulta [la documentación de la aplicación](app/README.md) para sus requisitos y funcionamiento. Ejecuta sus comandos npm desde `app/`. La guía manual de AWS copiada en `app/docs/` es una referencia histórica del laboratorio anterior.

## Paso 2: infraestructura CloudFormation

Se prepararon dos pilas y los archivos de Git Sync y del rol IAM en [infra/cloudformation/](infra/cloudformation/README.md). El único `infra/cloud-init.yaml` se incorpora a las dos EC2 mediante un script de sincronización. Por ahora aplica configuración base; la instalación de servicios y el despliegue de la aplicación quedan para los siguientes pasos. OpenTofu y Pulumi permanecen pendientes. No se han creado recursos en AWS.

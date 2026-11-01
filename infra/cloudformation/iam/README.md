# Rol de ejecución de las dos pilas

Configuración manual en IAM, fuera de las dos pilas. Nombre sugerido: `asistencia-cloudinit-execution`.

1. Crea un rol con entidad de confianza de servicio CloudFormation. En el editor de confianza usa `cloudformation-trust.json`.
2. Agrega una política insertada llamada `asistencia-cloudinit-resources` con `execution-policy.json`.
3. Selecciona este mismo rol en las opciones de ejecución de las pilas de red y cómputo.

La política conserva los permisos de la práctica anterior: ciclo de vida EC2, red, etiquetas, importación de claves públicas y resolución del parámetro público de AMI. Está delimitada a **cuenta `222234418877` y región `us-east-2`**. Reemplaza esos valores en las políticas si el destino cambia. El ARN del parámetro público SSM y los ARN de imágenes y snapshots usan cuenta vacía deliberadamente.

Las consultas EC2 requieren `Resource: "*"`; las escrituras se limitan a tipos de recursos de esa cuenta y región, con IDs aún desconocidos. Este alcance permite administrar otros recursos de esos tipos en el destino: no constituye aislamiento por pila. No concede AdministratorAccess, creación de roles/perfiles IAM ni NAT. No hay rol adjunto a EC2 ni permisos de acceso a AWS desde cloud-init. El cifrado usa la configuración EBS predeterminada; una CMK propia requerirá adaptar permisos KMS.

`pass-role-policy.json` es una política complementaria para la identidad que entrega el rol a CloudFormation (y, si corresponde, el rol Git Sync). Autoriza únicamente ese ARN y el servicio CloudFormation. **No se adjunta al rol de ejecución**. No reemplaza los permisos propios de Git Sync/CodeConnections: configura su rol mediante el asistente de AWS y revisa el resultado. La conexión al proveedor Git debe estar autorizada.

La confianza solo permite `cloudformation.amazonaws.com`, conforme al modelo documentado de rol de servicio CloudFormation. No se agregan condiciones SourceArn/SourceAccount sin confirmar que ese flujo las proporcione. Protege quién puede pasar el rol y operar las pilas: CloudFormation conserva el rol asociado a ellas.

Editar estos JSON o publicarlos en Git no actualiza IAM automáticamente. No se ha creado el rol ni se ha ejecutado IAM Access Analyzer o un despliegue real. Los límites de permisos, SCP y cuotas de la cuenta también deben permitir las operaciones.

Referencias: [rol de servicio](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-iam-servicerole.html), [permisos para pasar un rol](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_passrole.html), [requisitos Git Sync](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/git-sync-prereq.html).

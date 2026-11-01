import { readFileSync } from "node:fs";
import { resolve } from "node:path";
// Fuente unica compartida con CloudFormation y la futura configuracion OpenTofu.
export function renderCloudInit(revision: string, origin: string): string {
    if (!/^[a-f0-9]{40}$/.test(revision))
        throw new Error("appRevision debe ser un commit publicado de 40 caracteres");
    if (!/^http:\/\/(?:\d{1,3}\.){3}\d{1,3}$/.test(origin))
        throw new Error("Origen HTTP IPv4 invalido");
    let data = readFileSync(resolve(__dirname, "../../cloud-init.yaml"), "utf8");
    if (!data.startsWith("#cloud-config\n"))
        throw new Error("Formato cloud-init invalido");
    const values = { __APP_ARCHIVE_URL__: `https://github.com/borysinho/iac-cloud-init/archive/${revision}.tar.gz`, __FRONTEND_ORIGIN__: origin };
    for (const [token, value] of Object.entries(values)) {
        if (data.split(token).length !== 2)
            throw new Error(`Se esperaba una entrada ${token}`);
        data = data.replace(token, value);
    }
    if (Buffer.byteLength(data, "utf8") > 16384)
        throw new Error("UserData supera 16 KiB");
    return data; // Instance.userData recibe texto; el proveedor codifica Base64.
}

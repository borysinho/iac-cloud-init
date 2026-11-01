import * as aws from "@pulumi/aws";
import * as pulumi from "@pulumi/pulumi";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { isIPv4 } from "node:net";
import { join } from "node:path";
export const config = new pulumi.Config();
export const layer = config.require("layer");
if (!["network", "compute"].includes(layer))
    throw new Error("layer debe ser network o compute");
export const project = config.get("project") ?? "asistencia";
export const environment = config.get("environment") ?? "cloudinit-pulumi";
for (const value of [project, environment])
    if (!/^[a-z][a-z0-9-]{0,29}$/.test(value))
        throw new Error("Nombre de proyecto/entorno invalido");
export const accountId = config.get("accountId") ?? "222234418877";
if (!/^\d{12}$/.test(accountId))
    throw new Error("accountId debe tener 12 digitos");
export const region = (new pulumi.Config("aws").get("region") ?? "us-east-2") as aws.Region;
export const provider = new aws.Provider("aws", { region, allowedAccountIds: [accountId], defaultTags: { tags: { Project: project, Environment: environment, ManagedBy: "Pulumi" } } });
export const options = { provider };
export const tags = (name: string) => ({ Name: `${name}-${project}-${environment}` });
export function ipv4Cidr(value: string, administrative = false): string {
    const [address, mask, extra] = value.split("/");
    if (!isIPv4(address) || !/^(\d|[12]\d|3[0-2])$/.test(mask ?? "") || extra !== undefined || (administrative && mask !== "32"))
        throw new Error(administrative ? "sshSourceCidr requiere IPv4 /32" : "CIDR IPv4 invalido");
    return value;
}
export function publicKey(): string {
    const path = config.require("sshPublicKeyPath");
    const value = readFileSync(path.startsWith("~/") ? join(homedir(), path.slice(2)) : path, "utf8").trim();
    if (!/^ssh-(ed25519|rsa) [A-Za-z0-9+/]+={0,3}( [^\r\n]+)?$/.test(value))
        throw new Error("Se requiere la clave publica OpenSSH");
    return value;
}

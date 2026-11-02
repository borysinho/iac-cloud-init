import * as aws from "@pulumi/aws";
import * as pulumi from "@pulumi/pulumi";
import { accountId, config, environment, options, project, publicKey, region, tags } from "./config";
import { renderCloudInit } from "./cloud-init";
export function createCompute() {
    const network = new pulumi.StackReference(config.require("networkStack"));
    const deployment = network.requireOutput("deployment").apply(value => {
        if (!value || value.ready !== true)
            throw new Error("Completar network antes de compute");
        for (const [key, expected] of Object.entries({ accountId, region, project, environment }))
            if (value[key] !== expected)
                throw new Error(`Los stacks deben coincidir en ${key}`);
        return value as Record<string, string>;
    });
    const revision = config.get("appRevision") ?? "9e4d440276547607498f8aa3342c6234bb030f45";
    const ami = aws.ssm.getParameterOutput({ name: config.get("amiParameter") ?? "/aws/service/canonical/ubuntu/server/noble/stable/current/amd64/hvm/ebs-gp3/ami-id" }, options).value;
    const key = new aws.ec2.KeyPair("key", { publicKey: publicKey(), tags: tags("key") }, options);
    const base = { ami, instanceType: "t3.micro", keyName: key.keyName, metadataOptions: { httpEndpoint: "enabled", httpTokens: "required" }, creditSpecification: { cpuCredits: "standard" }, userDataReplaceOnChange: false };
    const client = new aws.ec2.Instance("client", {
        ...base, subnetId: deployment.publicSubnetId, privateIp: "10.42.1.10", associatePublicIpAddress: true, vpcSecurityGroupIds: [deployment.clientSecurityGroupId],
        rootBlockDevice: { volumeType: "gp3", volumeSize: 12, encrypted: true, deleteOnTermination: true },
        userData: renderCloudInit(revision, "https://127.0.0.1"), tags: { ...tags("ec2-cliente"), Role: "client" },
    }, options);
    const backend = new aws.ec2.Instance("backend", {
        ...base, subnetId: deployment.privateSubnetId, privateIp: "10.42.2.20", associatePublicIpAddress: false, vpcSecurityGroupIds: [deployment.backendSecurityGroupId],
        rootBlockDevice: { volumeType: "gp3", volumeSize: 20, encrypted: true, deleteOnTermination: true },
        userData: client.publicIp.apply(ip => renderCloudInit(revision, `https://${ip}`)), tags: { ...tags("ec2-backend"), Role: "backend" },
    }, options);
    return { clientInstanceId: client.id, backendInstanceId: backend.id, clientPublicIp: client.publicIp, backendPrivateIp: backend.privateIp,
        url: pulumi.interpolate `https://${client.publicIp}`, appRevision: revision,
        clientSsh: pulumi.interpolate `ssh -i ~/globomatics-ec2 ubuntu@${client.publicIp}`,
        backendSsh: pulumi.interpolate `ssh -i ~/globomatics-ec2 -o "ProxyCommand=ssh -i ~/globomatics-ec2 -W %h:%p ubuntu@${client.publicIp}" ubuntu@10.42.2.20` };
}

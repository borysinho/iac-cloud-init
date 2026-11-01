import * as aws from "@pulumi/aws";
import * as pulumi from "@pulumi/pulumi";
import { accountId, config, environment, ipv4Cidr, options, project, region, tags } from "./config";
export function createNetwork() {
    const ssh = ipv4Cidr(config.require("sshSourceCidr"), true);
    const web = ipv4Cidr(config.get("webSourceCidr") ?? "0.0.0.0/0");
    const az = config.get("availabilityZone") ?? aws.getAvailabilityZonesOutput({ state: "available" }, options).names.apply(names => names[0]);
    const vpc = new aws.ec2.Vpc("vpc", { cidrBlock: "10.42.0.0/16", enableDnsSupport: true, enableDnsHostnames: true, tags: tags("vpc") }, options);
    const publicSubnet = new aws.ec2.Subnet("public-subnet", { vpcId: vpc.id, cidrBlock: "10.42.1.0/24", availabilityZone: az, mapPublicIpOnLaunch: false, tags: tags("subnet-publica") }, options);
    const privateSubnet = new aws.ec2.Subnet("private-subnet", { vpcId: vpc.id, cidrBlock: "10.42.2.0/24", availabilityZone: az, mapPublicIpOnLaunch: false, tags: tags("subnet-privada") }, options);
    const igw = new aws.ec2.InternetGateway("internet-gateway", { vpcId: vpc.id, tags: tags("igw") }, options);
    const publicTable = new aws.ec2.RouteTable("public-routes", { vpcId: vpc.id, tags: tags("rtb-publica") }, options);
    const publicRoute = new aws.ec2.Route("public-default-route", { routeTableId: publicTable.id, destinationCidrBlock: "0.0.0.0/0", gatewayId: igw.id }, options);
    const publicAssociation = new aws.ec2.RouteTableAssociation("public-association", { subnetId: publicSubnet.id, routeTableId: publicTable.id }, options);
    const privateTable = new aws.ec2.RouteTable("private-routes", { vpcId: vpc.id, tags: tags("rtb-privada") }, options);
    const privateAssociation = new aws.ec2.RouteTableAssociation("private-association", { subnetId: privateSubnet.id, routeTableId: privateTable.id }, options);
    const eip = new aws.ec2.Eip("nat-eip", { domain: "vpc", tags: tags("eip-nat") }, { ...options, dependsOn: [igw] });
    const nat = new aws.ec2.NatGateway("nat", { allocationId: eip.id, subnetId: publicSubnet.id, connectivityType: "public", tags: tags("nat") }, { ...options, dependsOn: [publicRoute, publicAssociation] });
    const privateRoute = new aws.ec2.Route("private-default-route", { routeTableId: privateTable.id, destinationCidrBlock: "0.0.0.0/0", natGatewayId: nat.id }, options);
    const egress = [{ protocol: "-1", fromPort: 0, toPort: 0, cidrBlocks: ["0.0.0.0/0"] }];
    const clientGroup = new aws.ec2.SecurityGroup("client-security", {
        vpcId: vpc.id, description: "Cliente HTTP y bastion SSH", tags: tags("secgrp-cliente"), egress,
        ingress: [{ protocol: "tcp", fromPort: 22, toPort: 22, cidrBlocks: [ssh] }, { protocol: "tcp", fromPort: 80, toPort: 80, cidrBlocks: [web] }],
    }, options);
    const backendGroup = new aws.ec2.SecurityGroup("backend-security", {
        vpcId: vpc.id, description: "API y SSH desde cliente; MySQL local", tags: tags("secgrp-backend"), egress,
        ingress: [22, 8090].map(port => ({ protocol: "tcp", fromPort: port, toPort: port, securityGroups: [clientGroup.id] })),
    }, options);
    return { accountId, region, project, environment, vpcId: vpc.id, publicSubnetId: publicSubnet.id, privateSubnetId: privateSubnet.id,
        clientSecurityGroupId: clientGroup.id, backendSecurityGroupId: backendGroup.id, natGatewayId: nat.id,
        ready: pulumi.all([publicRoute.id, privateRoute.id, publicAssociation.id, privateAssociation.id]).apply(() => true) };
}

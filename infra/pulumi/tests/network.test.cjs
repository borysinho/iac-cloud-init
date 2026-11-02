const assert = require('node:assert/strict');
const {test} = require('node:test');
const pulumi = require('@pulumi/pulumi');
process.env.PULUMI_CONFIG = JSON.stringify({'asistencia-cloudinit:layer':'network','asistencia-cloudinit:sshSourceCidr':'181.188.164.3/32'});
const resources=[];
pulumi.runtime.setMocks({
 newResource(args) { resources.push(args); return {id:args.name+'-id',state:args.inputs}; },
 call(args) { if(args.token==='aws:index/getAvailabilityZones:getAvailabilityZones')return {names:['us-east-2a']};throw new Error(args.token); },
},'asistencia-cloudinit','network',false);
test('red equivalente con HTTP publico, backend aislado y NAT administrado',async()=>{
 const infra=await pulumi.runtime.runInPulumiStack(async()=>require('../index.ts'));
 const out=await new Promise(resolve=>pulumi.output(infra.deployment).apply(resolve));
 const of=type=>resources.filter(r=>r.type===type).map(r=>r.inputs);
 assert.equal(out.ready,true);
 assert.equal(of('aws:ec2/vpc:Vpc')[0].cidrBlock,'10.42.0.0/16');
 assert.deepEqual(of('aws:ec2/subnet:Subnet').map(s=>s.cidrBlock).sort(),['10.42.1.0/24','10.42.2.0/24']);
 assert.ok(of('aws:ec2/subnet:Subnet').every(s=>s.availabilityZone==='us-east-2a'&&!s.mapPublicIpOnLaunch));
 const [client,backend]=of('aws:ec2/securityGroup:SecurityGroup');
 assert.equal(client.ingress.find(r=>r.fromPort===80).cidrBlocks[0],'0.0.0.0/0');
 assert.equal(client.ingress.find(r=>r.fromPort===443).cidrBlocks[0],'0.0.0.0/0');
 assert.equal(client.ingress.find(r=>r.fromPort===22).cidrBlocks[0],'181.188.164.3/32');
 assert.deepEqual(backend.ingress.map(r=>r.fromPort),[22,8090]);
 assert.ok(backend.ingress.every(r=>r.securityGroups[0]==='client-security-id'&&!r.cidrBlocks?.length));
 assert.equal(of('aws:ec2/natGateway:NatGateway').length,1);
 assert.equal(of('aws:ec2/eip:Eip')[0].domain,'vpc');
 assert.equal(of('aws:ec2/route:Route').find(r=>r.natGatewayId).natGatewayId,'nat-id');
 assert.equal(of('aws:ec2/instance:Instance').length,0);
 assert.throws(()=>require('../src/config.ts').ipv4Cidr('0.0.0.0/0',true));
});

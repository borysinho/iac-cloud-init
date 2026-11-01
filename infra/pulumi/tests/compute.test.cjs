const assert = require('node:assert/strict');
const {test,after} = require('node:test');
const {mkdtempSync,writeFileSync,rmSync,readFileSync} = require('node:fs');
const {tmpdir} = require('node:os');
const {join,resolve} = require('node:path');
const pulumi = require('@pulumi/pulumi');
const temporary=mkdtempSync(join(tmpdir(),'pulumi-cloudinit-'));
const key=join(temporary,'key.pub');writeFileSync(key,'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestOnly test\n');
process.env.PULUMI_CONFIG=JSON.stringify({'asistencia-cloudinit:layer':'compute','asistencia-cloudinit:networkStack':'org/asistencia-cloudinit/network','asistencia-cloudinit:sshPublicKeyPath':key});
const resources=[];
pulumi.runtime.setMocks({
 newResource(args) {
  resources.push(args);
  if(args.type==='pulumi:pulumi:StackReference')return {id:args.name,state:{...args.inputs,outputs:{deployment:{ready:true,accountId:'222234418877',region:'us-east-2',project:'asistencia',environment:'cloudinit-pulumi',vpcId:'vpc-test',publicSubnetId:'subnet-public',privateSubnetId:'subnet-private',clientSecurityGroupId:'sg-client',backendSecurityGroupId:'sg-backend'}},secretOutputNames:[]}};
  return {id:args.name+'-id',state:{...args.inputs,...(args.type==='aws:ec2/instance:Instance'&&args.name==='client'?{publicIp:'203.0.113.10'}:{})}};
 },
 call(args) { if(args.token==='aws:ssm/getParameter:getParameter'){assert.match(args.inputs.name,/canonical\/ubuntu\/server\/noble/);return {value:'ami-test'};}throw new Error(args.token); },
},'asistencia-cloudinit','compute',false);
after(()=>rmSync(temporary,{recursive:true,force:true}));
test('dos EC2 y el mismo cloud-init, con origen del cliente resuelto para backend',async()=>{
 const infra=await pulumi.runtime.runInPulumiStack(async()=>require('../index.ts'));
 const out=await new Promise(resolve=>pulumi.output(infra.deployment).apply(resolve));
 assert.equal(out.url,'http://203.0.113.10');
 const instances=resources.filter(r=>r.type==='aws:ec2/instance:Instance').map(r=>r.inputs);
 assert.equal(instances.length,2);
 const source=readFileSync(resolve(__dirname,'../../cloud-init.yaml'),'utf8');
 for(const instance of instances){
  const client=instance.privateIp==='10.42.1.10';
  assert.equal(instance.subnetId,client?'subnet-public':'subnet-private');
  assert.equal(instance.associatePublicIpAddress,client);
  assert.equal(instance.ami,'ami-test');assert.equal(instance.instanceType,'t3.micro');
  assert.equal(instance.metadataOptions.httpTokens,'required');assert.equal(instance.creditSpecification.cpuCredits,'standard');
  assert.equal(instance.rootBlockDevice.encrypted,true);assert.equal(instance.rootBlockDevice.volumeSize,client?12:20);
  const expected=source.replace('__APP_ARCHIVE_URL__','https://github.com/borysinho/iac-cloud-init/archive/9e4d440276547607498f8aa3342c6234bb030f45.tar.gz').replace('__FRONTEND_ORIGIN__',client?'http://127.0.0.1':'http://203.0.113.10');
  assert.equal(instance.userData,expected);assert.ok(Buffer.byteLength(instance.userData)<16384);
  assert.equal(instance.userDataReplaceOnChange,false);
 }
 assert.equal(resources.filter(r=>r.type==='aws:ec2/vpc:Vpc').length,0);
 const {renderCloudInit}=require('../src/cloud-init.ts');
 assert.throws(()=>renderCloudInit('main','http://203.0.113.10'));
 assert.throws(()=>renderCloudInit('a'.repeat(40),"http://example.test'"));
});

#!/usr/bin/env python3
"""Ejecuta Pulumi con credenciales AWS temporales en memoria y estado local del laboratorio."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--profile', default=os.environ.get('AWS_PROFILE', 'default'))
parser.add_argument('command', nargs=argparse.REMAINDER)
args = parser.parse_args()
if not args.command:
    parser.error('Falta el comando')
credentials = subprocess.run(['aws','configure','export-credentials','--profile',args.profile,'--format','process'],capture_output=True,text=True)
if credentials.returncode:
    sys.stderr.write(credentials.stderr)
    raise SystemExit(credentials.returncode)
value = json.loads(credentials.stdout)
env = os.environ.copy()
env.update(AWS_ACCESS_KEY_ID=value['AccessKeyId'], AWS_SECRET_ACCESS_KEY=value['SecretAccessKey'])
if value.get('SessionToken'):
    env['AWS_SESSION_TOKEN'] = value['SessionToken']
else:
    env.pop('AWS_SESSION_TOKEN',None)
env.pop('AWS_PROFILE',None)
env.setdefault('AWS_REGION','us-east-2')
env.setdefault('AWS_DEFAULT_REGION','us-east-2')
root = Path(__file__).resolve().parents[1]
local = root/'.pulumi'
local.mkdir(mode=0o700,exist_ok=True)
for name in ('home','state'):
    (local/name).mkdir(mode=0o700,exist_ok=True)
password = local/'passphrase'
if not password.exists():
    if any((local/'state').rglob('*.json')):
        raise SystemExit('Ya existe estado: restaurar la passphrase original; no generar otra')
    fd = os.open(password,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w') as f:
        f.write(secrets.token_urlsafe(48)+'\n')
env.setdefault('PULUMI_CONFIG_PASSPHRASE_FILE',str(password))
env.setdefault('PULUMI_HOME',str(local/'home'))
env.setdefault('PULUMI_BACKEND_URL',(local/'state').as_uri())
raise SystemExit(subprocess.run(args.command,env=env,cwd=root).returncode)

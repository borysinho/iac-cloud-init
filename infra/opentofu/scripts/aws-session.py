#!/usr/bin/env python3
"""Ejecuta OpenTofu con credenciales temporales de AWS CLI solo en memoria."""
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
os.umask(0o077)  # Estados y planes nuevos accesibles solo por su propietario.
raise SystemExit(subprocess.run(args.command,env=env,cwd=root).returncode)

#!/usr/bin/env python3
"""Inserta los mismos bytes de infra/cloud-init.yaml en cada EC2, sin dependencias."""
import argparse
import base64
from pathlib import Path
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check', action='store_true', help='Falla si compute.yaml requiere regenerarse')
args = parser.parse_args()
cf = Path(__file__).resolve().parents[1]
payload = (cf.parent / 'cloud-init.yaml').read_bytes()
if not payload.startswith(b'#cloud-config\n'):
    raise SystemExit('Se esperaba un documento #cloud-config')
if len(payload) > 16384:
    raise SystemExit('UserData supera el limite EC2 de 16 KiB sin codificar')
encoded = base64.b64encode(payload).decode('ascii')
template = cf / 'compute.yaml'
before = template.read_text()
after, count = re.subn(
    r'      # BEGIN SHARED CLOUD INIT\n.*?      # END SHARED CLOUD INIT',
    '      # BEGIN SHARED CLOUD INIT\n      UserData: "' + encoded + '"\n      # END SHARED CLOUD INIT',
    before, flags=re.S,
)
if count != 2:
    raise SystemExit(f'Se esperaban dos EC2; se encontraron {count} bloques')
if args.check:
    if before != after:
        raise SystemExit('Ejecuta scripts/sync-cloud-init.py y publica compute.yaml actualizado')
    print('Las dos EC2 contienen exactamente el cloud-init.yaml compartido')
else:
    template.write_text(after)
    print('compute.yaml actualizado desde infra/cloud-init.yaml')

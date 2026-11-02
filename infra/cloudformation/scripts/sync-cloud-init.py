#!/usr/bin/env python3
"""Incorpora la plantilla cloud-init comun y sus dos entradas de despliegue."""
import argparse
import ipaddress
import json
from pathlib import Path
import re

TOKENS = re.compile(r'(__APP_ARCHIVE_URL__|__FRONTEND_ORIGIN__)')
ARCHIVE_PREFIX = 'https://github.com/borysinho/iac-cloud-init/archive/'


def fragments(payload, values):
    return [values.get(part, part) for part in TOKENS.split(payload) if part]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--render-dir', type=Path, help='Exportar cloud-init resuelto para actualizar EC2 existentes')
    parser.add_argument('--client-public-ip', help='IP publica actual del cliente, necesaria para --render-dir')
    parser.add_argument('--revision', help='Commit publicado de 40 caracteres; predeterminado: AppRevision de compute.yaml')
    args = parser.parse_args()
    cf = Path(__file__).resolve().parents[1]
    payload = (cf.parent / 'cloud-init.yaml').read_text()
    template = cf / 'compute.yaml'
    before = template.read_text()
    if not payload.startswith('#cloud-config\n'):
        raise SystemExit('Se esperaba #cloud-config')
    for token in ('__APP_ARCHIVE_URL__', '__FRONTEND_ORIGIN__'):
        if payload.count(token) != 1:
            raise SystemExit(f'Se esperaba exactamente una entrada {token}')
    # Las referencias actuales producen valores muy inferiores a esta reserva.
    if len(payload.encode()) + 1024 > 16384:
        raise SystemExit('UserData excederia 16 KiB con las entradas resueltas')
    if args.render_dir:
        if not args.client_public_ip:
            parser.error('--render-dir requiere --client-public-ip')
        address = str(ipaddress.IPv4Address(args.client_public_ip))
        revision = args.revision or re.search(r'  AppRevision:\n    Type: String\n    Default: ([a-f0-9]{40})', before).group(1)
        if not re.fullmatch('[a-f0-9]{40}', revision):
            parser.error('--revision debe ser un commit de 40 caracteres hexadecimales')
        resolved = ''.join(fragments(payload, {'__APP_ARCHIVE_URL__': ARCHIVE_PREFIX + revision + '.tar.gz', '__FRONTEND_ORIGIN__': 'https://' + address}))
        args.render_dir.mkdir(parents=True, exist_ok=True)
        for role in ('client', 'backend'):
            (args.render_dir / f'{role}-cloud-init.yaml').write_text(resolved)
        print('Cloud-init resuelto exportado; no se ha enviado a AWS')
        return
    index = 0

    def replace_block(match):
        nonlocal index
        origin = 'https://127.0.0.1' if index == 0 else {'Fn::Join': ['', ['https://', {'Fn::GetAtt': ['GlobomaticsClient', 'PublicIp']}]]}
        values = {'__APP_ARCHIVE_URL__': {'Fn::Join': ['', [ARCHIVE_PREFIX, {'Ref': 'AppRevision'}, '.tar.gz']]}, '__FRONTEND_ORIGIN__': origin}
        data = {'Fn::Base64': {'Fn::Join': ['', fragments(payload, values)]}}
        index += 1
        return '      # BEGIN SHARED CLOUD INIT\n      UserData: ' + json.dumps(data, ensure_ascii=False) + '\n      # END SHARED CLOUD INIT'

    after = re.sub(r'      # BEGIN SHARED CLOUD INIT\n.*?      # END SHARED CLOUD INIT', replace_block, before, flags=re.S)
    if index != 2:
        raise SystemExit(f'Se esperaban dos EC2; se encontraron {index}')
    if len(after.encode()) > 51200:
        raise SystemExit('La plantilla excede el limite inline de 51200 bytes')
    if args.check:
        if before != after:
            raise SystemExit('Ejecuta sync-cloud-init.py y publica compute.yaml actualizado')
        print('Ambas EC2 utilizan la plantilla comun con sus entradas de despliegue')
    else:
        template.write_text(after)
        print('compute.yaml actualizado desde infra/cloud-init.yaml')


if __name__ == '__main__':
    main()

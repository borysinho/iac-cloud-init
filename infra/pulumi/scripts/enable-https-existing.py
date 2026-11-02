#!/usr/bin/env python3
"""En una EC2 existente, actualizar bootstrap y habilitar HTTPS sin reinstalar la aplicacion."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urlsplit

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('payload', type=Path)
args = parser.parse_args()
if os.geteuid() != 0:
    raise SystemExit('Ejecutar con sudo en la EC2, no en el equipo local')
data = json.loads(args.payload.read_text())
role = data['role']
origin = data['origin']
url = urlsplit(origin)
if url.scheme != 'https' or url.path or url.query or url.fragment or url.port is not None:
    raise SystemExit('Se requiere un origen HTTPS sin puerto ni ruta')
ipaddress.IPv4Address(url.hostname)
expected = {'client': '10.42.1.10', 'backend': '10.42.2.20'}
if role not in expected:
    raise SystemExit('Rol no reconocido')
addresses = subprocess.check_output(['hostname','-I'],text=True).split()
if expected[role] not in addresses:
    raise SystemExit('El payload no corresponde a esta instancia')
allowed = {'/etc/asistencia-bootstrap.env': 0o600, '/usr/local/sbin/asistencia-install-services': 0o750, '/usr/local/sbin/asistencia-deploy': 0o750}
entries = data['files']
if len(entries) != len(allowed) or {entry['path'] for entry in entries} != set(allowed):
    raise SystemExit('Archivos de bootstrap inesperados')
for entry in entries:
    if '__APP_ARCHIVE_URL__' in entry['content'] or '__FRONTEND_ORIGIN__' in entry['content']:
        raise SystemExit('El payload contiene entradas sin resolver')
for entry in entries:
    path = Path(entry['path'])
    fd, temporary = tempfile.mkstemp(prefix='.asistencia-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:
            stream.write(entry['content'])
        os.chmod(temporary,allowed[str(path)])
        os.replace(temporary,path)
    finally:
        Path(temporary).unlink(missing_ok=True)
if role == 'client':
    deploy = next(entry['content'] for entry in entries if entry['path'].endswith('/asistencia-deploy'))
    begin = deploy.index('    # Certificado local:')
    end = deploy.index('    # Ubuntu incluye',begin)
    tls = deploy[begin:end]
    if 'listen 443 ssl;' in Path('/etc/nginx/conf.d/asistencia.conf').read_text():
        # Mantener idempotencia si se repite tras un fallo: no duplicar el redirect.
        begin = tls.index("    python3 - <<'TLS'\n")
        end = tls.index('\nTLS\n',begin) + len('\nTLS\n')
        tls = tls[:begin]+tls[end:]
    subprocess.run(['bash'],input='set -euo pipefail\n'+tls+'\nnginx -t\nsystemctl reload nginx\ncurl --fail --silent --show-error --cacert /etc/ssl/certs/asistencia.crt https://127.0.0.1/ -o /dev/null\n',text=True,check=True)
else:
    path = Path('/opt/asistencia/.env.backend')
    stat = path.stat()
    lines = path.read_text().splitlines()
    lines = [line for line in lines if not line.startswith('FRONTEND_ORIGINS=')]
    lines.append('FRONTEND_ORIGINS='+origin)
    fd,temporary = tempfile.mkstemp(prefix='.env-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:
            stream.write('\n'.join(lines)+'\n')
        os.chown(temporary,stat.st_uid,stat.st_gid)
        os.chmod(temporary,stat.st_mode & 0o777)
        os.replace(temporary,path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    subprocess.run(['systemctl','restart','asistencia'],check=True)
print(json.dumps({'role':role,'origin':origin,'https_configured':True}))

#!/usr/bin/env python3
"""Aplicar los archivos del bootstrap resuelto y ejecutar el instalador en una EC2 Ubuntu existente."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import yaml  # Ubuntu lo incluye como dependencia de cloud-init.

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('file', type=Path)
args = parser.parse_args()
if os.geteuid() != 0:
    raise SystemExit('Ejecutar con sudo en la EC2, no en el equipo local')
payload = args.file.read_text()
if '__APP_ARCHIVE_URL__' in payload or '__FRONTEND_ORIGIN__' in payload:
    raise SystemExit('Primero exportar el archivo con sync-cloud-init.py --render-dir')
data = yaml.safe_load(payload)
allowed = {'/etc/asistencia-bootstrap.env': 0o600, '/usr/local/sbin/asistencia-install-services': 0o750, '/usr/local/sbin/asistencia-deploy': 0o750}
entries = data.get('write_files', [])
if len(entries) != len(allowed) or {entry['path'] for entry in entries} != set(allowed):
    raise SystemExit('El documento no contiene exactamente los archivos esperados')
subprocess.run(['cloud-init', 'status', '--wait'], check=True)
for entry in entries:
    path = Path(entry['path'])
    # Sustitucion atomica; no se escribe .env.backend ni estado de cloud-init.
    fd, temporary = tempfile.mkstemp(prefix='.asistencia-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(entry['content'])
        os.chmod(temporary, allowed[str(path)])
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
subprocess.run(['/usr/local/sbin/asistencia-install-services'], check=True)

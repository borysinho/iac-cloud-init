"""Validacion local del renderizado y despliegue; sin instalar servicios ni acceder a AWS."""
from pathlib import Path
import base64
import importlib.util
import json
import os
import subprocess
import tarfile
import tempfile
import unittest
import yaml

CF = Path(__file__).resolve().parents[1]
ROOT = CF.parents[1]
CONFIG = yaml.safe_load((ROOT / 'infra/cloud-init.yaml').read_text())
DEPLOY = next(x['content'] for x in CONFIG['write_files'] if x['path'].endswith('/asistencia-deploy'))

class Loader(yaml.SafeLoader):
    pass

def intrinsic(loader, tag, node):
    return {tag: loader.construct_scalar(node) if isinstance(node, yaml.ScalarNode) else loader.construct_sequence(node)}
Loader.add_multi_constructor('!', intrinsic)

class BootstrapTests(unittest.TestCase):
    def test_templates_and_shell(self):
        subprocess.run(['python3', str(CF/'scripts/sync-cloud-init.py'), '--check'], check=True, capture_output=True)
        for entry in CONFIG['write_files']:
            if entry['content'].startswith('#!/bin/bash'):
                subprocess.run(['bash', '-n'], input=entry['content'], text=True, check=True)
        template = yaml.load((CF/'compute.yaml').read_text(), Loader=Loader)
        def evaluate(x):
            if isinstance(x, str): return x
            if 'Ref' in x: return '9e4d440276547607498f8aa3342c6234bb030f45'
            if 'Fn::GetAtt' in x:
                self.assertEqual(x['Fn::GetAtt'], ['GlobomaticsClient','PublicIp'])
                return '203.0.113.10'
            delimiter, parts = x['Fn::Join']
            return delimiter.join(evaluate(v) for v in parts)
        for name in ('GlobomaticsClient','GlobomaticsBackend'):
            data = template['Resources'][name]['Properties']['UserData']['Fn::Base64']
            rendered = evaluate(data)
            self.assertLess(len(rendered.encode()), 16384)
            self.assertNotIn('__APP_ARCHIVE_URL__', rendered)
            self.assertNotIn('__FRONTEND_ORIGIN__', rendered)
            self.assertIn('https://github.com/borysinho/iac-cloud-init/archive/9e4d440', rendered)
            if name == 'GlobomaticsClient':
                self.assertNotIn('203.0.113.10', rendered)  # Evitar referencia del cliente a si mismo.
        self.assertLess((CF/'compute.yaml').stat().st_size,51200)

    def test_deploy_both_roles_and_preserve_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); bins=folder/'bin';bins.mkdir()
            for directory in ('etc/nginx/conf.d','etc/nginx/sites-enabled','etc/systemd/system','etc/ssl/private','etc/ssl/certs','opt','var/www'):
                (folder/directory).mkdir(parents=True)
            archive=folder/'source.tar.gz'
            with tarfile.open(archive,'w:gz') as tar:
                tar.add(ROOT/'app',arcname='snapshot/app')
            (folder/'etc/asistencia-bootstrap.env').write_text("APP_ARCHIVE_URL=https://example.test/app.tar.gz\nFRONTEND_ORIGIN=https://203.0.113.10\n")
            script=DEPLOY.replace("install -d -o root -g asistencia", "install -d")
            for original in ('/etc/','/opt/','/var/www/'):
                script=script.replace(original,str(folder / original.lstrip('/'))+'/')
            file=folder/'deploy';file.write_text(script)
            stub='''#!/bin/bash
command=${0##*/}
echo "$command $*" >> "$MOCK_LOG"
case "$command" in
 ip) echo "2: ens5 inet $MOCK_IP/24 brd 10.42.255.255 scope global ens5";;
 curl)
   if [[ "$*" == *latest/api/token* ]]; then printf mock-token
   elif [[ "$*" == *latest/meta-data/public-ipv4* ]]; then printf 203.0.113.10
   elif [[ "$*" == *--write-out* ]]; then printf 401
   elif [[ "$*" == *example.test* ]]; then cp "$MOCK_ARCHIVE" "${@: -1}"; fi;;
 mysql) cat >> "$MOCK_SQL";;
esac
'''
            for command in ('ip','curl','systemctl','nginx','useradd','chown','npm','mysql','sleep'):
                path=bins/command;path.write_text(stub);path.chmod(0o755)
            env={**os.environ,'PATH':str(bins)+':'+os.environ['PATH'],'MOCK_LOG':str(folder/'commands'),'MOCK_SQL':str(folder/'sql'),'MOCK_ARCHIVE':str(archive)}
            def run(ip):
                result=subprocess.run(['bash',str(file)],env={**env,'MOCK_IP':ip},capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
            run('10.42.1.10')
            self.assertEqual((folder/'var/www/asistencia/app.js').read_bytes(),(ROOT/'app/public/app.js').read_bytes())
            nginx=(folder/'etc/nginx/conf.d/asistencia.conf').read_text()
            self.assertIn('proxy_pass http://10.42.2.20:8090;',nginx)
            self.assertIn('listen 443 ssl;',nginx)
            self.assertIn('return 301 https://$host$request_uri;',nginx)
            subprocess.run(['openssl','x509','-in',str(folder/'etc/ssl/certs/asistencia.crt'),'-noout','-checkip','203.0.113.10'],check=True,capture_output=True)
            self.assertFalse((folder/'var/www/asistencia/.env.backend').exists())
            run('10.42.2.20')
            path=folder/'opt/asistencia/.env.backend';first=path.read_text()
            self.assertIn('FRONTEND_ORIGINS=https://203.0.113.10',first)
            self.assertIn('CREATE DATABASE IF NOT EXISTS', (folder/'sql').read_text())
            self.assertIn('Requires=mysql.service',(folder/'etc/systemd/system/asistencia.service').read_text())
            run('10.42.2.20')
            self.assertEqual(first,path.read_text())
            self.assertIn('npm run db:init',(folder/'commands').read_text())
            self.assertNotIn('ADMIN_PASSWORD=',(folder/'commands').read_text())

if __name__ == '__main__':
    unittest.main()

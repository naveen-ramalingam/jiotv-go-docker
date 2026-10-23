#!/usr/bin/env python3
"""Exercise a real container using disposable volumes and a loopback-only port."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import ssl
import subprocess
import tempfile
import time
from urllib.request import urlopen
import uuid
import xml.etree.ElementTree as ET


def docker(*args, check=True):
    return subprocess.run(['docker', *args], check=check, text=True, capture_output=True)


def wait_page(url, context, deadline):
    while time.monotonic() < deadline:
        try:
            with urlopen(url, context=context, timeout=5) as response:
                if response.status == 200 and b'JioTV Go' in response.read():
                    return
        except (OSError, ValueError):
            pass
        time.sleep(1)
    raise RuntimeError('Container HTTPS page did not become ready')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    parser.add_argument('--enable-epg', action='store_true')
    args = parser.parse_args()
    name = 'jiotv-smoke-' + uuid.uuid4().hex[:12]
    data, tls = name + '-data', name + '-tls'
    try:
        version = docker('run', '--rm', '--label', 'com.centurylinklabs.watchtower.enable=false',
                         args.image, '--version').stdout
        expected = json.loads(Path('upstream.lock.json').read_text())['version']
        assert expected in version, 'Image executable version mismatch'
        docker('run', '--detach', '--name', name, '--init', '--read-only',
               '--tmpfs', '/tmp:rw,noexec,nosuid,size=32m', '--cap-drop', 'ALL',
               '--cap-add', 'CHOWN', '--cap-add', 'SETUID', '--cap-add', 'SETGID',
               '--cap-add', 'DAC_OVERRIDE', '--cap-add', 'FOWNER',
               '--security-opt', 'no-new-privileges:true',
               '--label', 'com.centurylinklabs.watchtower.enable=false',
               '--publish', '127.0.0.1::5002', '--volume', data + ':/data',
               '--volume', tls + ':/tls', '--env', 'JIOTV_EPG=' + str(args.enable_epg).lower(),
               args.image)
        port = docker('port', name, '5002/tcp').stdout.strip().rsplit(':', 1)[1]
        with tempfile.TemporaryDirectory(prefix='jiotv-cert-check-') as temporary:
            cert = Path(temporary) / 'server.crt'
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                result = docker('cp', name + ':/tls/server.crt', str(cert), check=False)
                if result.returncode == 0:
                    break
                time.sleep(1)
            context = ssl.create_default_context(cafile=str(cert))
            url = f'https://127.0.0.1:{port}'
            wait_page(url + '/', context, deadline)
            docker('exec', name, '/usr/local/bin/healthcheck.sh')
            process = docker('exec', name, 'sh', '-c', 'cat /proc/$(pidof jiotv_go)/status').stdout
            uid = next(line.split()[1] for line in process.splitlines() if line.startswith('Uid:'))
            caps = next(line.split()[1] for line in process.splitlines() if line.startswith('CapEff:'))
            assert uid == '10001' and int(caps, 16) == 0, 'Application must run unprivileged'
            with urlopen(url + '/playlist.m3u?q=high&c=split', context=context, timeout=30) as response:
                assert response.read().startswith(b'#EXTM3U'), 'Playlist is not M3U'
            if args.enable_epg:
                while time.monotonic() < deadline:
                    try:
                        with urlopen(url + '/epg.xml.gz', context=context, timeout=15) as response:
                            root = ET.fromstring(gzip.decompress(response.read()))
                        assert root.tag == 'tv' and root.findall('programme')
                        print('Container EPG validated:', len(root.findall('programme')), 'programmes')
                        break
                    except OSError:
                        time.sleep(2)
                else:
                    raise RuntimeError('Enabled EPG was not generated')
            original_cert = hashlib.sha256(cert.read_bytes()).hexdigest()
            docker('exec', '--user', '10001:10001', name, 'sh', '-c',
                   "printf 'persistent-state-check' > /data/smoke-marker")
            docker('restart', name)
            wait_page(url + '/', context, time.monotonic() + 120)
            docker('cp', name + ':/tls/server.crt', str(cert))
            assert hashlib.sha256(cert.read_bytes()).hexdigest() == original_cert
            assert docker('exec', '--user', '10001:10001', name,
                          'cat', '/data/smoke-marker').stdout == 'persistent-state-check'
            print('Passed: executable version, trusted HTTPS, M3U, UID 10001, zero capabilities, persistent data and TLS')
    except BaseException:
        print(docker('logs', '--tail', '40', name, check=False).stdout)
        raise
    finally:
        docker('rm', '--force', name, check=False)
        docker('volume', 'rm', data, tls, check=False)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import tarfile
from release_utils import semver

version = Path('VERSION').read_text().strip()
semver(version)
tag = 'v' + version
lock = json.loads(Path('upstream.lock.json').read_text())
image = 'ghcr.io/naveen-ramalingam/jiotv-go-docker'
digest = os.environ['IMAGE_DIGEST']
if not digest.startswith('sha256:') or len(digest) != 71:
    raise SystemExit('Missing image digest from successful GitHub build')
dist = Path('dist')
dist.mkdir(exist_ok=True)
notes = f'''Docker packaging release {tag}, built by GitHub Actions.

- Image: `{image}:{version}`
- Moving stable tag: `{image}:latest`
- Immutable image reference: `{image}@{digest}`
- Platforms: `linux/amd64`, `linux/arm64`
- Upstream JioTV Go: [{lock["version"]}]({lock["release_url"]})
- DRM and EPG enabled; HTTPS and persistent data/TLS volumes included.
- Credentials and certificates are created at runtime and are not included in the image.

The image is public and can be pulled without a GitHub sign-in or registry token.
See [README.md](https://github.com/naveen-ramalingam/jiotv-go-docker#readme) for deployment, TiviMate playlists, backups, and migration.
'''
(dist / 'release-notes.md').write_text(notes)
(dist / 'image-digest.txt').write_text(f'{image}@{digest}\n')
bundle = dist / f'jiotv-go-docker-{tag}.tar.gz'
with tarfile.open(bundle, 'w:gz') as archive:
    for name in ('compose.yaml', '.env.example', 'README.md', 'VERSION', 'upstream.lock.json',
                 'LICENSE.upstream', 'NOTICE.md'):
        archive.add(name, arcname=name)
exists = subprocess.run(['gh', 'release', 'view', tag], capture_output=True).returncode == 0
if not exists:
    subprocess.run(['gh', 'release', 'create', tag, '--verify-tag', '--title', tag,
                    '--notes-file', str(dist / 'release-notes.md')], check=True)
subprocess.run(['gh', 'release', 'upload', tag, '--clobber', str(bundle),
                str(dist / 'image-digest.txt'), 'upstream.lock.json'], check=True)
print(f'Published {tag}: {image}:{version}')

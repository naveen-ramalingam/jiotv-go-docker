#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
from release_utils import semver, validate_lock

version = Path('VERSION').read_text().strip()
semver(version)
lock = validate_lock(json.loads(Path('upstream.lock.json').read_text()))
tag = 'v' + version
requested = os.environ.get('RELEASE_TAG', '')
if requested and requested != tag:
    raise SystemExit('Release tag does not match VERSION')
if os.environ.get('REQUIRE_TAG') == '1':
    tagged = subprocess.run(['git', 'rev-parse', f'{tag}^{{commit}}'], check=True,
                            capture_output=True, text=True).stdout.strip()
    current = subprocess.run(['git', 'rev-parse', 'HEAD'], check=True,
                             capture_output=True, text=True).stdout.strip()
    if tagged != current:
        raise SystemExit('VERSION tag must already exist and point to the checked-out commit')
values = dict(version=version, tag=tag, upstream=lock['version'],
              image='ghcr.io/naveen-ramalingam/jiotv-go-docker')
output = os.environ.get('GITHUB_OUTPUT')
if output:
    with open(output, 'a') as target:
        for name, value in values.items():
            target.write(f'{name}={value}\n')
print(json.dumps(values, indent=2))

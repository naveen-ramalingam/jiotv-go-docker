#!/usr/bin/env python3
"""Download a locked upstream executable; no authentication or credentials needed."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from release_utils import validate_lock


def verify_binary(path, asset, arch):
    if path.stat().st_size != asset['size']:
        raise ValueError('Downloaded executable size mismatch')
    if hashlib.sha256(path.read_bytes()).hexdigest() != asset['sha256']:
        raise ValueError('Downloaded executable SHA-256 mismatch')
    with path.open('rb') as source:
        header = source.read(20)
    machine = {'amd64': 62, 'arm64': 183}[arch]
    if (len(header) < 20 or header[:6] != b'\x7fELF\x02\x01'
            or struct.unpack('<H', header[18:20])[0] != machine):
        raise ValueError('Downloaded executable architecture mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arch', choices=['amd64', 'arm64'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--lock', type=Path, default=Path('upstream.lock.json'))
    args = parser.parse_args()
    lock = validate_lock(json.loads(args.lock.read_text()))
    asset = lock['assets'][args.arch]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    request = Request(asset['url'], headers={'User-Agent': 'jiotv-go-private-container-build'})
    try:
        with urlopen(request, timeout=90) as response, args.output.open('wb') as target:
            final = urlsplit(response.url)
            if final.scheme != 'https' or final.hostname not in {
                    'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}:
                raise ValueError('Unexpected download redirect')
            total = 0
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > asset['size']:
                    raise ValueError('Executable exceeds the locked size')
                target.write(block)
        verify_binary(args.output, asset, args.arch)
        args.output.chmod(0o755)
        print(f'Verified upstream {lock["version"]} for {args.arch}')
    except BaseException:
        args.output.unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    main()

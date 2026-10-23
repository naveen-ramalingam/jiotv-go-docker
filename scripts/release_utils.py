"""Validation shared by the image build and upstream release automation."""
import re
from urllib.parse import unquote, urlsplit


def semver(value):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', value)
    if not match:
        raise ValueError('Expected a stable MAJOR.MINOR.PATCH version')
    return tuple(map(int, match.groups()))


def validate_lock(lock):
    tag = lock['version']
    semver(tag)
    for arch in ('amd64', 'arm64'):
        asset = lock['assets'][arch]
        parsed = urlsplit(asset['url'])
        expected = f'/jiotv-go/jiotv_go/releases/download/{tag}/jiotv_go-linux-{arch}'
        if (parsed.scheme != 'https' or parsed.hostname != 'github.com'
                or parsed.username or parsed.password or parsed.port not in (None, 443)
                or parsed.query or parsed.fragment
                or unquote(parsed.path).lower() != expected.lower()):
            raise ValueError('Binary URL must identify the official repository, release, and architecture')
        if not re.fullmatch(r'[a-f0-9]{64}', asset['sha256']):
            raise ValueError('Missing or invalid release SHA-256')
        if not isinstance(asset['size'], int) or not 0 < asset['size'] <= 128 * 1024 * 1024:
            raise ValueError('Unexpected executable size')
    return lock


def release_to_lock(release):
    if release.get('draft') is not False or release.get('prerelease') is not False:
        raise ValueError('Drafts and prereleases are not published automatically')
    tag = release['tag_name']
    semver(tag)
    result = dict(version=tag, source='https://github.com/JioTV-Go/jiotv_go',
                  release_url=release['html_url'], assets={})
    for arch in ('amd64', 'arm64'):
        matches = [a for a in release['assets'] if a['name'] == f'jiotv_go-linux-{arch}']
        if len(matches) != 1:
            raise ValueError(f'Expected one official {arch} executable')
        asset = matches[0]
        if not asset.get('digest', '').startswith('sha256:'):
            raise ValueError('Official GitHub asset checksum is required')
        result['assets'][arch] = dict(url=asset['browser_download_url'],
                                     sha256=asset['digest'][7:].lower(), size=asset['size'])
    return validate_lock(result)

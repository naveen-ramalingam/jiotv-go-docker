import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fetch_binary import verify_binary
from release_utils import release_to_lock, semver, validate_lock


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads((ROOT / 'upstream.lock.json').read_text())

    def test_committed_assets_are_official_and_pinned(self):
        self.assertEqual(validate_lock(self.lock), self.lock)
        self.assertEqual(set(self.lock['assets']), {'amd64', 'arm64'})

    def test_stable_version_order(self):
        self.assertGreater(semver('v3.23.0'), semver('v3.22.9'))
        for value in ('v3.23.0-beta', 'latest', '3.2', '../../etc/passwd'):
            with self.assertRaises(ValueError):
                semver(value)

    def test_credentials_query_and_other_hosts_are_rejected(self):
        for url in ('http://github.com/a', 'https://example.com/a',
                    self.lock['assets']['arm64']['url'] + '?token=fixture',
                    self.lock['assets']['arm64']['url'].replace('https://', 'https://user:fixture@')):
            changed = copy.deepcopy(self.lock)
            changed['assets']['arm64']['url'] = url
            with self.assertRaises(ValueError):
                validate_lock(changed)

    def test_checksum_is_required_for_both_architectures(self):
        for arch in ('arm64', 'amd64'):
            changed = copy.deepcopy(self.lock)
            changed['assets'][arch]['sha256'] = ''
            with self.assertRaises(ValueError):
                validate_lock(changed)

    def test_release_rejects_prerelease_and_missing_architecture(self):
        release = dict(tag_name=self.lock['version'], html_url=self.lock['release_url'],
                       draft=False, prerelease=False, assets=[])
        for arch, asset in self.lock['assets'].items():
            release['assets'].append(dict(name='jiotv_go-linux-' + arch,
                                         digest='sha256:' + asset['sha256'], size=asset['size'],
                                         browser_download_url=asset['url']))
        self.assertEqual(release_to_lock(release), self.lock)
        release['prerelease'] = True
        with self.assertRaises(ValueError):
            release_to_lock(release)
        release['prerelease'] = False
        release['assets'].pop()
        with self.assertRaises(ValueError):
            release_to_lock(release)

    def test_actual_binary_hash_size_and_architecture(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'executable'
            for arch, machine in [('amd64', 62), ('arm64', 183)]:
                content = bytearray(24)
                content[:6] = b'\x7fELF\x02\x01'
                content[18:20] = machine.to_bytes(2, 'little')
                path.write_bytes(content)
                asset = dict(size=len(content), sha256=hashlib.sha256(content).hexdigest())
                verify_binary(path, asset, arch)
                with self.assertRaisesRegex(ValueError, 'SHA-256'):
                    verify_binary(path, dict(asset, sha256='0' * 64), arch)
                with self.assertRaisesRegex(ValueError, 'size'):
                    verify_binary(path, dict(asset, size=len(content) + 1), arch)
                with self.assertRaisesRegex(ValueError, 'architecture'):
                    verify_binary(path, asset, 'arm64' if arch == 'amd64' else 'amd64')


if __name__ == '__main__':
    unittest.main()

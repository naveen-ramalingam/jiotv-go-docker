#!/usr/bin/env python3
"""Update the source lock, create a version tag, and dispatch the GitHub build."""
import json
import os
from pathlib import Path
import subprocess
from release_utils import release_to_lock, semver, validate_lock


def run(*args, capture=False):
    return subprocess.run(args, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def main():
    current = validate_lock(json.loads(Path('upstream.lock.json').read_text()))
    release = json.loads(run('gh', 'api', 'repos/JioTV-Go/jiotv_go/releases/latest', capture=True))
    latest = release_to_lock(release)
    if semver(latest['version']) <= semver(current['version']):
        print(f'Upstream is unchanged: {current["version"]}; no commit, tag, or image rebuild')
        return
    major, minor, patch = semver(Path('VERSION').read_text().strip())
    version = f'{major}.{minor}.{patch + 1}'
    tag = 'v' + version
    run('gh', 'auth', 'setup-git')
    existing = subprocess.run(['git', 'ls-remote', '--exit-code', '--tags', 'origin', f'refs/tags/{tag}'],
                              capture_output=True, text=True)
    if existing.returncode != 2:
        raise RuntimeError('Next packaging tag already exists or tag lookup failed')
    Path('upstream.lock.json').write_text(json.dumps(latest, indent=2) + '\n')
    Path('VERSION').write_text(version + '\n')
    run('git', 'config', 'user.name', 'github-actions[bot]')
    run('git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    run('git', 'add', 'VERSION', 'upstream.lock.json')
    run('git', 'commit', '-m', f'Package upstream JioTV Go {latest["version"]}')
    run('git', 'push', 'origin', 'HEAD:main')
    run('git', 'tag', tag)
    run('git', 'push', 'origin', tag)
    # GITHUB_TOKEN pushes do not trigger another workflow; dispatch explicitly.
    run('gh', 'workflow', 'run', 'release.yml', '--ref', 'main', '-f', f'ref={tag}')
    print(f'Dispatched container release {tag} for upstream {latest["version"]}')


if __name__ == '__main__':
    main()

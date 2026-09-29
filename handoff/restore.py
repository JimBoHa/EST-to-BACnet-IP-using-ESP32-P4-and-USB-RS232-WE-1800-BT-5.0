#!/usr/bin/env python3
"""Verify and restore a private continuation bundle. No network or device actions."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import subprocess
import sys

GATEWAY_URL = 'https://github.com/JimBoHa/EST-to-BACnet-IP-using-ESP32-P4-and-USB-RS232-WE-1800-BT-5.0.git'
BACNET_URL = 'https://github.com/bacnet-stack/bacnet-stack.git'
CREDENTIALS = ('device-cert.pem', 'device-key.pem', 'host-cert.pem', 'host-key.pem',
               'ota-signing-key.pem', 'ota-signing-public.pem', 'tokens.json', 'provision.h')


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def member(root, name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError('Invalid manifest path')
    parts = PurePosixPath(name)
    if parts.is_absolute() or '..' in parts.parts or str(parts) != name:
        raise ValueError('Unsafe manifest path: ' + name)
    path = root.joinpath(*parts.parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path escapes bundle: ' + name)
    cursor = path
    while cursor != root:
        if cursor.is_symlink():
            raise ValueError('Symlink in bundle path: ' + name)
        cursor = cursor.parent
    return path


def verify(root):
    root = root.resolve()
    manifest = json.loads((root / 'BUNDLE_MANIFEST.json').read_text(encoding='utf-8'))
    if manifest.get('format_version') != 1 or not isinstance(manifest.get('files'), list):
        raise ValueError('Unsupported bundle manifest')
    listed = set()
    for record in manifest['files']:
        name = record['path']
        if name in listed:
            raise ValueError('Duplicate manifest path: ' + name)
        listed.add(name)
        path = member(root, name)
        if not path.is_file():
            raise ValueError('Missing file: ' + name)
        if path.stat().st_size != record['size'] or sha256(path) != record['sha256']:
            raise ValueError('Integrity mismatch: ' + name)
    for path in root.rglob('*'):
        if path.is_symlink():
            raise ValueError('Unexpected symlink in bundle')
        if path.is_file():
            name = path.relative_to(root).as_posix()
            if name not in listed and name != 'BUNDLE_MANIFEST.json' and path.name != '.DS_Store':
                raise ValueError('Unlisted file: ' + name)
    return manifest


def git(*args, cwd=None):
    result = subprocess.run(['git', *map(str, args)], cwd=cwd, check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout.strip()


def restore(root, destination, manifest):
    root = root.resolve()
    destination = destination.expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('Destination already exists; choose a new directory')
    if destination.resolve().is_relative_to(root):
        raise ValueError('Destination must be outside the extracted bundle')
    if not shutil.which('git'):
        raise ValueError('Git is required for restoration')
    repo, sub = manifest['repository'], manifest['submodule']
    if repo['url'] != GATEWAY_URL or sub['url'] != BACNET_URL:
        raise ValueError('Unexpected repository URL')
    if sub['path'] != 'third_party/bacnet-stack':
        raise ValueError('Unexpected submodule path')
    for config in (repo, sub):
        if not re.fullmatch('[0-9a-f]{40}', config['commit']):
            raise ValueError('Invalid Git commit')
    listed = {row['path'] for row in manifest['files']}
    required = {repo['bundle'], sub['bundle'],
                *('payload/private/' + name for name in CREDENTIALS)}
    if not required <= listed:
        raise ValueError('Required repository or credential artifacts missing')
    overlays = []
    for name in sorted(listed):
        if not name.startswith('payload/'):
            continue
        relative = name[len('payload/'):]
        if not (relative.startswith('private/') or relative.startswith('release/') or
                relative in ('evidence/original-flash.bin', 'evidence/original-flash.sha256')):
            raise ValueError('Unexpected restore overlay: ' + relative)
        overlays.append((member(root, name), relative))
    # Verification and preflight finish before the first filesystem mutation.
    destination.parent.mkdir(parents=True, exist_ok=True)
    previous_umask = os.umask(0o077)
    try:
        git('clone', '--no-checkout', member(root, repo['bundle']), destination)
        destination.chmod(0o700)
        git('checkout', '-B', 'main', repo['commit'], cwd=destination)
        if git('rev-parse', 'HEAD', cwd=destination) != repo['commit']:
            raise ValueError('Restored project commit mismatch')
        git('remote', 'set-url', 'origin', GATEWAY_URL, cwd=destination)
        sub_path = destination / sub['path']
        git('clone', '--no-checkout', member(root, sub['bundle']), sub_path)
        git('checkout', '--detach', sub['commit'], cwd=sub_path)
        if git('rev-parse', 'HEAD', cwd=sub_path) != sub['commit']:
            raise ValueError('Restored BACnet commit mismatch')
        git('remote', 'set-url', 'origin', BACNET_URL, cwd=sub_path)
        git('submodule', 'init', cwd=destination)
        git('submodule', 'absorbgitdirs', cwd=destination)
        for source, relative in overlays:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and sha256(target) != sha256(source):
                raise ValueError('Overlay conflicts with checkout: ' + relative)
            shutil.copyfile(source, target)
            target.chmod(0o600)
        for name in ('private', 'release'):
            path = destination / name
            for directory in (path, *[p for p in path.rglob('*') if p.is_dir()]):
                directory.chmod(0o700)
        database = destination / 'private/hardware-bench.sqlite'
        if database.exists():
            with sqlite3.connect(database.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
                if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                    raise ValueError('Restored SQLite integrity check failed')
        if git('status', '--porcelain', cwd=destination):
            raise ValueError('Unexpected tracked/unignored changes after restore')
        (destination / 'private/handoff-restoration.json').write_text(
            json.dumps({'bundle_path': str(root), 'repository_commit': repo['commit'],
                        'submodule_commit': sub['commit'], 'sqlite_integrity': 'ok',
                        'device_contacted': False, 'credentials_regenerated': False}, indent=2) + '\n',
            encoding='utf-8')
    finally:
        os.umask(previous_umask)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=Path(__file__).resolve().parent)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--verify-only', action='store_true')
    choice.add_argument('--destination', type=Path)
    args = parser.parse_args()
    try:
        manifest = verify(args.bundle)
        print('Verified %d files.' % len(manifest['files']))
        if args.destination:
            path = restore(args.bundle, args.destination, manifest)
            print('Restored to ' + str(path))
            print('Git commits, private artifacts and SQLite integrity verified.')
            print('No packages installed, credentials generated, device contacted or firmware uploaded.')
    except (OSError, ValueError, KeyError, sqlite3.Error, subprocess.CalledProcessError) as exc:
        print('Restore stopped: ' + str(exc), file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr.strip(), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

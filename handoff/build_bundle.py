#!/usr/bin/env python3
"""Build a private, verified transfer bundle from this checkout and explicit site inputs."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import zipfile
from contextlib import closing

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('handoff_restore', ROOT / 'handoff/restore.py')
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)


def command(*args, cwd=ROOT):
    return subprocess.check_output(list(map(str, args)), cwd=cwd, text=True).strip()


def copy_file(source, target):
    if source.is_symlink() or not source.is_file():
        raise ValueError('Expected ordinary input file: ' + str(source))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    target.chmod(0o600)


def git_archive(repo, target):
    with tempfile.TemporaryFile() as stream:
        subprocess.run(['git', 'archive', '--format=tar', 'HEAD'], cwd=repo,
                       stdout=stream, check=True)
        stream.seek(0)
        target.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=stream) as archive:
            archive.extractall(target, filter='data')


def manifest_files(output):
    return [{'path': p.relative_to(output).as_posix(), 'size': p.stat().st_size,
             'sha256': restore.sha256(p)} for p in sorted(output.rglob('*'))
            if p.is_file() and p.name != 'BUNDLE_MANIFEST.json']


def snapshot_database(source_path, target):
    """Close both connections before manifesting; context manager alone doesn't."""
    with closing(sqlite3.connect(source_path.as_uri() + '?mode=ro', uri=True)) as source:
        with closing(sqlite3.connect(target)) as destination:
            source.backup(destination)
            if destination.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('Database backup integrity failed: ' + source_path.name)
            destination.execute('PRAGMA journal_mode=DELETE')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--original-spec', type=Path, required=True)
    parser.add_argument('--sdu-directory', type=Path, required=True)
    parser.add_argument('--photos', type=Path, nargs='+', required=True)
    parser.add_argument('--previews', type=Path, nargs='*', default=[])
    args = parser.parse_args()
    if command('git', 'status', '--porcelain'):
        raise SystemExit('Commit/review project changes before bundling; checkout must be clean')
    output = args.output.expanduser().absolute()
    zip_path = output.with_suffix('.zip')
    if output.exists() or zip_path.exists():
        raise SystemExit('Output folder or ZIP already exists; choose a new output name')
    if output.resolve().is_relative_to(ROOT):
        raise SystemExit('Private bundle must be outside the public source checkout')
    for name in restore.CREDENTIALS:
        if not (ROOT / 'private' / name).is_file():
            raise SystemExit('Missing existing credential artifact: ' + name)
    sdu_files = sorted(args.sdu_directory.rglob('*.SDU'))
    if not sdu_files or not (args.original_spec / 'IMPLEMENTATION_PLAN.md').is_file():
        raise SystemExit('Original specification and genuine SDU inputs are required')
    os.umask(0o077)
    output.mkdir(parents=True, mode=0o700)
    repo_commit = command('git', 'rev-parse', 'HEAD')
    sub_path = ROOT / 'third_party/bacnet-stack'
    sub_commit = command('git', 'rev-parse', 'HEAD', cwd=sub_path)
    for name in ('START_HERE.md', 'NEXT_SESSION_PROMPT.md', 'COMPLETION_PLAN.md', 'TRANSFER.md', 'restore.py'):
        copy_file(ROOT / 'handoff' / name, output / name)
    (output / 'repositories').mkdir()
    subprocess.run(['git', 'bundle', 'create', str(output / 'repositories/gateway.bundle'),
                    'HEAD', 'refs/heads/main'], cwd=ROOT, check=True)
    subprocess.run(['git', 'bundle', 'create', str(output / 'repositories/bacnet-stack.bundle'),
                    'HEAD'], cwd=sub_path, check=True)
    git_archive(ROOT, output / 'source-preview')
    payload = output / 'payload'
    private = ROOT / 'private'
    # Existing credentials, captures and review summaries only; no old virtualenvs,
    # native libraries, blank NVS images, cache directories or live SQLite WAL files.
    for p in sorted(private.iterdir()):
        if p.is_file() and (p.suffix in ('.pem', '.json', '.jsonl') or p.name == 'provision.h' or
                            (p.suffix == '.bin' and not p.name.startswith('blank-'))):
            copy_file(p, payload / 'private' / p.name)
    database_results = {}
    for p in private.glob('*.sqlite'):
        target = payload / 'private' / p.name
        target.parent.mkdir(parents=True, exist_ok=True)
        snapshot_database(p, target)
        target.chmod(0o600)
        database_results[p.name] = 'backup API snapshot; integrity_check ok'
    review = private / 'sdu-review'
    for p in review.glob('*.json'):
        copy_file(p, payload / 'private/sdu-review' / p.name)
    for version in ('0.1.4', '0.1.5'):
        for p in (ROOT / 'release' / version).iterdir():
            if p.is_file():
                copy_file(p, payload / 'release' / version / p.name)
    for name in ('original-flash.bin', 'original-flash.sha256'):
        copy_file(ROOT / 'evidence' / name, payload / 'evidence' / name)
    provenance = []
    for index, p in enumerate(sdu_files):
        target = output / 'site-inputs/sdu' / p.name
        if target.exists():
            raise ValueError('Duplicate SDU basename; assign unique source paths')
        copy_file(p, target)
        provenance.append({'source_filename': p.name,
                           'bundle_path': target.relative_to(output).as_posix(),
                           'sha256': restore.sha256(p), 'original_unchanged': True})
    for p in [*args.photos, *args.previews]:
        copy_file(p, output / 'site-inputs/photos' / p.name)
    copy_file(ROOT / 'firmware/sdkconfig', output / 'site-inputs/build/sdkconfig-0.1.5-reference')
    if (review / 'pxlib-source/.git').exists():
        git_archive(review / 'pxlib-source', output / 'site-inputs/sdu-tools/pxlib-source')
    package = review / 'python/pypxlib'
    for p in package.rglob('*.py'):
        copy_file(p, output / 'site-inputs/sdu-tools/pypxlib-source/pypxlib' / p.relative_to(package))
    for p in (review / 'python').glob('pypxlib-*.dist-info/METADATA'):
        copy_file(p, output / 'site-inputs/sdu-tools/pypxlib-source/METADATA')
    copy_file(review / 'pxlib-source/COPYING', output / 'site-inputs/sdu-tools/pypxlib-source/COPYING')
    copy_file(ROOT / 'handoff/SDU_READER_NOTES.md', output / 'site-inputs/sdu-tools/README.md')
    for p in sorted(args.original_spec.rglob('*')):
        if p.is_file():
            copy_file(p, output / 'original-spec' / p.relative_to(args.original_spec))
    manifest = {
        'format_version': 1, 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'target_os': 'macOS; fresh native Apple Silicon or Intel tools required',
        'private': True, 'encrypted': False,
        'repository': {'commit': repo_commit, 'url': restore.GATEWAY_URL,
                       'bundle': 'repositories/gateway.bundle'},
        'submodule': {'path': 'third_party/bacnet-stack', 'commit': sub_commit,
                      'url': restore.BACNET_URL, 'bundle': 'repositories/bacnet-stack.bundle'},
        'idf': {'version': 'v5.5.5', 'commit': 'b774170ff46c393eeb5e495ea37936038d3f4f4f'},
        'last_successful_device_test': json.loads((ROOT / 'evidence/field-panel-report-0.1.5.json').read_text()),
        'latest_connection_attempt': json.loads((private / 'handoff-connectivity-attempt.json').read_text()),
        'database_backups': database_results, 'sdu_inputs': provenance,
        'excluded': ['installed toolchains/venvs/build caches', 'blank NVS erase images',
                     'live SQLite WAL/SHM files', 'GitHub login credentials'],
    }
    path = output / 'BUNDLE_MANIFEST.json'
    manifest['files'] = manifest_files(output)
    path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    verified = restore.verify(output)
    with tempfile.TemporaryDirectory(prefix='est3-handoff-restore-') as temp:
        destination = restore.restore(output, Path(temp) / 'restored', verified)
        for name in restore.CREDENTIALS:
            assert restore.sha256(destination / 'private' / name) == restore.sha256(private / name)
        validation = {'result': 'PASS', 'repository_commit': repo_commit,
                      'submodule_commit': sub_commit, 'credentials_identical': True,
                      'sqlite_snapshot_integrity': 'ok', 'restored_worktree_clean': True,
                      'device_contacted_by_restore': False, 'firmware_uploaded': False,
                      'tested_on': command('uname', '-sm')}
    (output / 'RESTORE_VALIDATION.json').write_text(json.dumps(validation, indent=2) + '\n')
    manifest['files'] = manifest_files(output)
    path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    restore.verify(output)
    with zipfile.ZipFile(zip_path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6,
                         allowZip64=True) as archive:
        for p in sorted(output.rglob('*')):
            if p.is_file():
                archive.write(p, output.name + '/' + p.relative_to(output).as_posix())
    zip_path.chmod(0o600)
    with zipfile.ZipFile(zip_path) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP CRC validation failed')
    checksum = restore.sha256(zip_path)
    zip_path.with_suffix('.zip.sha256').write_text(checksum + '  ' + zip_path.name + '\n')
    print(json.dumps({'folder': str(output), 'zip': str(zip_path), 'zip_bytes': zip_path.stat().st_size,
                      'zip_sha256': checksum, 'files': len(manifest['files']),
                      'restore_validation': validation}, indent=2))


if __name__ == '__main__':
    main()

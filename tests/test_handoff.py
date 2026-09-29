"""Bundle integrity and overwrite boundaries; no network or device access."""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('handoff_restore', Path(__file__).parents[1] / 'handoff/restore.py')
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)


def bundle(tmp_path):
    root = tmp_path / 'bundle'
    root.mkdir()
    data = root / 'sample.txt'
    data.write_bytes(b'known contents')
    manifest = {'format_version': 1, 'files': [
        {'path': 'sample.txt', 'size': data.stat().st_size, 'sha256': restore.sha256(data)}]}
    (root / 'BUNDLE_MANIFEST.json').write_text(json.dumps(manifest))
    return root, manifest


def test_valid_bundle_and_modified_bytes(tmp_path):
    root, manifest = bundle(tmp_path)
    assert restore.verify(root) == manifest
    (root / 'sample.txt').write_bytes(b'other contents')
    with pytest.raises(ValueError, match='Integrity mismatch'):
        restore.verify(root)


def test_outside_path_rejected(tmp_path):
    root, manifest = bundle(tmp_path)
    manifest['files'][0]['path'] = '../sample.txt'
    (root / 'BUNDLE_MANIFEST.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='Unsafe manifest path'):
        restore.verify(root)


def test_unlisted_file_rejected(tmp_path):
    root, _ = bundle(tmp_path)
    (root / 'unexpected.txt').write_text('not in manifest')
    with pytest.raises(ValueError, match='Unlisted file'):
        restore.verify(root)


def test_existing_workspace_untouched(tmp_path):
    root, manifest = bundle(tmp_path)
    destination = tmp_path / 'existing-project'
    destination.mkdir()
    sentinel = destination / 'keep.txt'
    sentinel.write_text('user data')
    with pytest.raises(ValueError, match='Destination already exists'):
        restore.restore(root, destination, manifest)
    assert sentinel.read_text() == 'user data'


def test_snapshot_has_no_transient_manifest_sidecars(tmp_path):
    import sqlite3
    import runpy
    builder=runpy.run_path(str(Path(__file__).parents[1]/'handoff/build_bundle.py'))
    source=tmp_path/'source.sqlite';target=tmp_path/'snapshot.sqlite'
    db=sqlite3.connect(source)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE sample(value)')
    db.execute('INSERT INTO sample VALUES (42)');db.commit()
    builder['snapshot_database'](source,target)
    assert not target.with_name(target.name+'-wal').exists()
    assert not target.with_name(target.name+'-shm').exists()
    restored=sqlite3.connect(target.as_uri()+'?mode=ro&immutable=1',uri=True)
    assert restored.execute('SELECT value FROM sample').fetchone()==(42,)
    restored.close();db.close()

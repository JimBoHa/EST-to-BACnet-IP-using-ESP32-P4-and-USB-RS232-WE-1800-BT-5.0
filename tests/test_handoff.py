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

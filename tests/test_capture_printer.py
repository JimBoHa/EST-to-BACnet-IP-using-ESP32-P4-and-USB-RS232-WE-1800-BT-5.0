"""Capture evidence must distinguish overlap, RAM eviction and reboot."""
import pytest
from tools.capture_printer import RecordTracker, capture


def snapshot(ids, boot=31):
    return {'boot_count': boot, 'records': [
        {'id': n, 'offset': n * 20, 'epoch': 2, 'received_monotonic_ms': n * 100,
         'parse_status': 'unrecognized', 'raw_hex': b'synthetic'.hex()} for n in ids]}


def test_overlapping_windows_do_not_duplicate_evidence():
    tracker = RecordTracker()
    assert len(tracker.consume(snapshot(range(1, 5)))) == 4
    assert len(tracker.consume(snapshot(range(3, 7)))) == 2
    assert tracker.consume(snapshot(range(3, 7))) == []
    assert tracker.records == 6 and tracker.missing == 0


def test_initial_eviction_is_distinct_from_missed_records_during_capture():
    tracker = RecordTracker()
    first = tracker.consume(snapshot(range(20, 25)))
    assert first[0]['kind'] == 'prior_records_unavailable'
    assert tracker.missing == 0
    later = tracker.consume(snapshot(range(28, 31)))
    assert later[0] == {'kind': 'missing_records', 'boot_count': 31,
                        'first_id': 25, 'last_id': 27}
    assert tracker.missing == 3


def test_first_empty_window_does_not_hide_later_loss():
    tracker = RecordTracker()
    assert tracker.consume(snapshot([])) == []
    assert tracker.consume(snapshot([4]))[0]['kind'] == 'missing_records'
    assert tracker.missing == 3


def test_reboot_starts_separate_identity_space():
    tracker = RecordTracker()
    tracker.consume(snapshot([1, 2, 3]))
    rows = tracker.consume(snapshot([1, 2], boot=32))
    assert rows[0]['kind'] == 'boot_changed'
    assert len(rows) == 3 and tracker.reboots == 1 and tracker.missing == 0


def test_changed_record_is_not_silently_discarded_as_duplicate():
    tracker = RecordTracker()
    tracker.consume(snapshot([1]))
    changed = snapshot([1]); changed['records'][0]['raw_hex'] = '00'
    with pytest.raises(ValueError, match='retained record changed'):
        tracker.consume(changed)


@pytest.mark.parametrize('ids', [[2, 1], [1, 1], [0], list(range(1, 130))])
def test_invalid_record_windows_rejected(ids):
    with pytest.raises(ValueError):
        RecordTracker().consume(snapshot(ids))


def test_capture_is_get_only_bounded_and_keeps_output_private(tmp_path, monkeypatch):
    from tools import capture_printer as module
    calls = []
    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        def request(self, method, path):
            calls.append((method, path))
            if path == '/api/v1/printer?limit=128':
                return {**snapshot([1, 2]), 'evicted': 0, 'gaps': 1,
                        'partial_bytes': 0, 'stream_offset': 40}
            return {'boot_count': 31}
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module, 'Client', FakeClient)
    monkeypatch.setattr(module.socket, 'gethostbyname', lambda _: '192.0.2.1')
    ticks = iter([0, 0.1, 0.5, 1.1])
    monkeypatch.setattr(module.time, 'monotonic', lambda: next(ticks))
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    output = tmp_path / 'private' / 'capture.jsonl'
    result = capture('fixture.invalid', output, seconds=1)
    assert result['records'] == 2 and result['current_state_validated'] is False
    assert all(method == 'GET' for method, _ in calls)
    assert output.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        capture('fixture.invalid', output, seconds=1)
    with pytest.raises(ValueError, match='under private'):
        capture('fixture.invalid', tmp_path / 'public.jsonl', seconds=1)

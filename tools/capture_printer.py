"""Bounded, read-only collection of P4 printer records during a site visit.

Uses the existing pinned TLS client. Sends GET requests only. The output is a
private diagnostic artifact, not a permanent history service or a state decoder.
Record bytes exclude line terminators; never present this file as a raw wire dump.
"""
import argparse
import json
import os
import socket
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from tools.gateway_client import Client, ROOT
except ModuleNotFoundError:
    from gateway_client import Client, ROOT


class RecordTracker:
    """Deduplicate overlapping RAM windows and make omissions explicit."""

    def __init__(self):
        self.boot = None
        self.last_id = 0
        self.window = {}
        self.records = 0
        self.missing = 0
        self.reboots = 0

    def consume(self, snapshot):
        boot = snapshot['boot_count']
        rows = snapshot['records']
        if type(boot) is not int or boot < 0 or not isinstance(rows, list) or len(rows) > 128:
            raise ValueError('invalid printer snapshot')
        prior = 0
        for row in rows:
            for key in ('id', 'offset', 'epoch', 'received_monotonic_ms'):
                if type(row[key]) is not int or row[key] < (1 if key == 'id' else 0):
                    raise ValueError('invalid record identity or offset')
            if row['id'] <= prior:
                raise ValueError('record IDs are not strictly increasing')
            prior = row['id']
            raw = row['raw_hex']
            if not isinstance(raw, str) or len(raw) > 1024 or len(raw) % 2:
                raise ValueError('invalid record bytes')
            bytes.fromhex(raw)
        output = []
        if boot != self.boot:
            if self.boot is not None:
                self.reboots += 1
                output.append({'kind': 'boot_changed', 'from': self.boot, 'to': boot,
                               'unobserved_bytes': 'unknown; RAM reset'})
            self.boot = boot
            self.last_id = 0
            self.window = {}
            if rows and rows[0]['id'] > 1:
                output.append({'kind': 'prior_records_unavailable', 'boot_count': boot,
                               'first_available_id': rows[0]['id']})
                self.last_id = rows[0]['id'] - 1
        for row in rows:
            rid = row['id']
            if rid <= self.last_id:
                if rid in self.window and self.window[rid] != row:
                    raise ValueError('retained record changed without a new boot/ID')
                continue
            if rid != self.last_id + 1:
                first, last = self.last_id + 1, rid - 1
                self.missing += last - first + 1
                output.append({'kind': 'missing_records', 'boot_count': boot,
                               'first_id': first, 'last_id': last})
            output.append({'kind': 'record', 'boot_count': boot, **row})
            self.last_id = rid
            self.records += 1
        self.window = {row['id']: dict(row) for row in rows}
        return output


def private_output(path):
    path = Path(path).resolve()
    if not path.is_relative_to((ROOT / 'private').resolve()):
        raise ValueError('capture output must be under private/')
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation avoids overwriting earlier site evidence.
    return os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w')


def capture(host, output, seconds=600, interval=0.5):
    if not 1 <= seconds <= 3600 or not 0.1 <= interval <= 5:
        raise ValueError('duration must be 1..3600 seconds; interval 0.1..5 seconds')
    # Resolve mDNS once: repeating it per TLS connection can exceed the RAM
    # retention window during a report. The client still verifies the exact leaf.
    client = Client(socket.gethostbyname(host), timeout=10)
    tracker = RecordTracker()
    samples = 0
    written = 0
    failures = 0
    with private_output(output) as stream:
        def emit(record):
            nonlocal written
            record = {'collected_utc': datetime.now(timezone.utc).isoformat(), **record}
            line = json.dumps(record, separators=(',', ':')) + '\n'
            if written + len(line.encode()) > 64 * 1024 * 1024:
                raise RuntimeError('64 MiB capture limit reached; capture stopped')
            stream.write(line)
            stream.flush()
            written += len(line.encode())

        before = client.request('GET', '/ota/status')
        serial_before = client.request('GET', '/api/v1/serial')
        emit({'kind': 'start', 'status': before, 'serial': serial_before,
              'scope': 'bounded diagnostic capture; no panel requests',
              'encoding': 'raw_hex records omit CR/LF; stream_gap bytes are diagnostic text'})
        print('READY: authenticated read-only capture; output stays private.', flush=True)
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                snapshot = client.request('GET', '/api/v1/printer?limit=128')
            except (OSError, RuntimeError) as exc:
                failures += 1
                emit({'kind': 'request_failed', 'error_type': type(exc).__name__})
                if failures >= 3:
                    raise RuntimeError('three consecutive request failures; capture stopped') from exc
            else:
                failures = 0
                samples += 1
                for record in tracker.consume(snapshot):
                    emit(record)
                emit({'kind': 'window', **{k: snapshot[k] for k in
                      ('boot_count', 'evicted', 'gaps', 'partial_bytes', 'stream_offset')}})
            time.sleep(min(interval, max(0, deadline - time.monotonic())))
        after = client.request('GET', '/ota/status')
        serial_after = client.request('GET', '/api/v1/serial')
        summary = {'samples': samples, 'records': tracker.records,
                   'missing_record_ids': tracker.missing, 'observed_reboots': tracker.reboots,
                   'starting_boot': before['boot_count'], 'ending_boot': after['boot_count'],
                   'partial_bytes': snapshot['partial_bytes'] if samples else None,
                   'current_state_validated': False}
        emit({'kind': 'finish', 'summary': summary, 'status': after, 'serial': serial_after})
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='est3-device.local')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=600)
    parser.add_argument('--interval', type=float, default=0.5)
    args = parser.parse_args()
    print(json.dumps(capture(args.host, args.output, args.seconds, args.interval), indent=2))

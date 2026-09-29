"""Bounded passive receiver baud checks. Never sends serial data to the panel.

Full captures stay in private/; the shareable summary omits all captured payload.
The original receiver baud is restored even when a read fails.
"""
import argparse
import datetime
import json
import time
from pathlib import Path
from gateway_client import Client, ROOT

SUPPORTED = (1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200)


def diagnostics(client):
    value = client.request('GET', '/api/v1/serial')
    if value.get('serial_payload_tx_enabled') is not False:
        raise RuntimeError('Receiver must report serial payload TX disabled')
    if not value['usb_connected']:
        raise RuntimeError('USB receiver disconnected')
    return value


def set_baud(client, baud, boot):
    client.request('POST', '/api/v1/serial', json.dumps({'baud': baud}).encode(),
                   {'Content-Type': 'application/json'})
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        value = diagnostics(client)
        if value['boot_count'] != boot:
            raise RuntimeError('Controller restarted during receiver configuration')
        if value['configuration_error']:
            raise RuntimeError(f"USB configuration error {value['configuration_error']}")
        if value['baud'] == baud and value['requested_baud'] == baud:
            time.sleep(1)  # Exclude configuration/USB buffering boundary from deltas.
            return diagnostics(client)
        time.sleep(.2)
    raise RuntimeError('Receiver baud change not acknowledged')


def run(host, rates, seconds, raw_path, summary_path):
    raw_path = raw_path.resolve()
    if not raw_path.is_relative_to((ROOT / 'private').resolve()):
        raise ValueError('Full serial captures must be saved under private/')
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    client = Client(host)
    initial = diagnostics(client)
    original, boot = initial['baud'], initial['boot_count']
    result = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'host': host, 'boot_count': boot, 'original_baud': original,
              'format': '8N1', 'seconds_per_rate': seconds,
              'serial_payload_tx_enabled': False, 'rates': [], 'errors': []}
    full = {'initial': initial, 'rates': []}
    try:
        for rate in rates:
            baseline = set_baud(client, rate, boot)
            samples = [baseline]
            full['rates'].append({'baud': rate, 'samples': samples})
            started = time.monotonic()
            print(json.dumps({'baud': rate, 'phase': 'listening'}), flush=True)
            for elapsed in range(1, seconds + 1):
                delay = started + elapsed - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
                value = diagnostics(client)
                if value['boot_count'] != boot or value['baud'] != rate:
                    raise RuntimeError('Boot or receiver baud changed during observation')
                samples.append(value)
            last = samples[-1]
            keys = ('usb_in_packets', 'usb_status_only_packets', 'usb_invalid_packets',
                    'usb_line_error_packets', 'usb_payload_bytes', 'rx_bytes',
                    'rx_drops', 'usb_errors', 'line_errors')
            row = {'baud': rate, 'samples': len(samples),
                   'elapsed_seconds': round(time.monotonic() - started, 3),
                   'deltas': {k: (last[k] - baseline[k]) % (2 ** 32) for k in keys},
                   'last_ftdi_modem_status': last['ftdi_modem_status'],
                   'last_ftdi_line_status': last['ftdi_line_status'],
                   'capture_count': last['capture_count']}
            result['rates'].append(row)
            print(json.dumps(row), flush=True)
    except Exception as exc:
        result['errors'].append(str(exc))
    finally:
        try:
            restored = set_baud(client, original, boot)
            result['restored_baud'] = restored['baud']
            full['restored'] = restored
        except Exception as exc:
            result['errors'].append('Receiver baud restoration failed: ' + str(exc))
        raw_path.write_text(json.dumps({'summary': result, **full}, indent=2) + '\n')
        raw_path.chmod(0o600)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(result, indent=2) + '\n')
    if result['errors']:
        raise RuntimeError('; '.join(result['errors']))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', required=True)
    parser.add_argument('--rates', nargs='+', type=int, choices=SUPPORTED,
                        default=[19200, 9600])
    parser.add_argument('--seconds', type=int, choices=range(1, 61), default=30)
    parser.add_argument('--raw-output', type=Path,
                        default=ROOT / 'private/serial-diagnostics.json')
    parser.add_argument('--summary-output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.host, args.rates, args.seconds, args.raw_output,
                         args.summary_output), indent=2))

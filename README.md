# EST3 / ESP32-P4 monitoring gateway

The ESP32-P4 hosts its own HTTPS configuration, diagnostics and device directory,
and exposes read-only BACnet/IP. Only the P4 and Metasys are permanent components;
no Mac, FastAPI service or separate history server is needed in operation.
Recent receiver observations are bounded RAM data, cleared on reboot. Metasys
handles any long-term trending.

Read [STATUS.md](STATUS.md) for installed firmware and measured results, and
[standalone operations](docs/STANDALONE_OPERATIONS.md) for access, import and recovery.
The [coverage matrix](docs/SOURCE_COVERAGE.md) distinguishes available data from
unverified capabilities. **Automatic live EST condition decoding and startup
current-state recovery are still unavailable.** Imported labels do not establish
normal detector states.

## Implemented path

- FTDI USB reception at verified 9600 8N1, physically RX-only; no payload TX.
- On-device revision-report metadata parsing and 128 recent raw-line records,
  with offsets, stream epochs, fragments and visible eviction/loss.
- Private read-only SDU import: 1,214 backup objects, including 674 physical
  sensor/module records; stable UUIDs and BACnet instances. Other source scopes
  remain explicitly qualified. No guessed location/message-blob decoding.
- Embedded status, searchable directory, diagnostics export, receiver configuration,
  registry validation/preview/backup, and signed application OTA.
- Native BACnet Device plus four health BIs and five BIs per catalog object.
  Unsupported current conditions report fault quality; DataValid remains inactive.

Page layout follows the owner's [reference firmware](https://github.com/JimBoHa/ESP32-S3-PoE-ETH-8DI-8RO-C-BACnet-IP-Firmware),
with attribution in [third-party notices](docs/THIRD_PARTY.md).

## Existing-controller build

Restore the existing private credentials and recovery images first. Never run
`tools/provision.py` for this controller. The private transfer bundle contains
source inputs and credentials excluded from Git. The older handoff prompt's
permanent-host and Metasys commissioning requirements are superseded by the
2026-09-29 owner instructions recorded in [WORK_LOG.md](docs/WORK_LOG.md).

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
git submodule update --init
export IDF_PATH="$HOME/esp-idf-v5.5.5"
# Set IDF_TOOLS_PATH when the pinned toolchain uses a separate directory.
tools/idf.sh build
.venv/bin/python tools/package_release.py
```

ESP-IDF v5.5.5 is pinned to `b774170ff46c393eeb5e495ea37936038d3f4f4f`.
Use ESP32-P4 pre-v3 settings, silicon range 1.0–1.99. The installed board is
revision 1.3 with 32 MB flash/PSRAM, native EMAC/IP101 Ethernet and USB-A FTDI.
Keep the partition table, bootloader, NVS identity, signing trust and eFuses.
USB-C recovery is unavailable at the deployment. No Wi-Fi is used.

## Access and updates

Open `https://est3-device.local/` using the retained trusted device certificate.
Load the private device admin key into the page; it stays in page memory.
The CLI verifies certificate trust/time and the exact leaf before sending a token,
so it also works with the controller's current DHCP IP:

```sh
.venv/bin/python tools/gateway_client.py --host DEVICE_IP status
.venv/bin/python tools/gateway_client.py --host DEVICE_IP upload release/VERSION/est3_gateway_rxonly.bin
```

App-only OTA verifies signature, image structure/project and exact running ELF
hash. Confirmation also checks registry retention, USB, 9600 and parser health.
Unconfirmed images roll back after 180 seconds. Private archived binaries contain
the existing TLS key/token; do not publish them. The signing private key never
enters the device or browser. See the runbook for rollback compatibility.

## Verification

```sh
export IDF_PATH="$HOME/esp-idf-v5.5.5"
export PATH="$PWD/.venv/bin:$PATH"
cmake -S tests -B build-tests -G Ninja
cmake --build build-tests
ctest --test-dir build-tests --output-on-failure
.venv/bin/python -m pytest tests -q
```

C tests use ASan/UBSan for parsing, bounded capture, state quality, malformed input,
and 2,048-record identity reconciliation. Python tests cover importer/reconciliation,
handoff snapshots and the retained offline simulator/host. Browser tests use
synthetic API fixtures; deployed HTTPS and independent BACpypes3 tests are separate:

```sh
.venv/bin/python tools/verify_field.py --host DEVICE_IP --local-ip LOCAL_IP \
  --registry private/reviewed-registry.json --all --output private/bacnet-check.json
.venv/bin/python tools/verify_management.py --host DEVICE_IP \
  --registry private/reviewed-registry.json --output private/web-check.json
```

`host/` and `simulator/` remain optional development fixtures. They are not the
production UI or a real EST event source. Metasys automation remains dry-run;
the owner will test integration after reliable automatic panel readings exist.
[PICS](docs/PICS.md) records BACnet support and placeholder assignments.
[TEST_MATRIX.csv](docs/TEST_MATRIX.csv) keeps unperformed physical, automatic-event,
Metasys and 24-hour mixed-load tests distinct from passing software/transport checks.

# EST3 / ESP32-P4 monitoring gateway — first draft

Read [STATUS.md](STATUS.md) for actual results and remaining gates. This implements the supplied `est3-metasys-handoff.zip`; that original archive and planning files remain unchanged. The reference package contains no previous implemented firmware.

The gateway is supplemental monitoring development software. **Real ECP parsing and all serial payload transmission are disabled.** It cannot currently report real EST detector states or obtain complete inventory. The simulation demonstrates the application behavior explicitly as SIMULATION_ONLY. The host and native BACnet simulator run on the Mac; firmware runs on the ESP32-P4.

## Hardware and build

Observed through USB-C: ESP32-P4 revision 1.3, 32 MB flash, 32 MB PSRAM, base/Ethernet MAC `e8:f6:0a:e4:1f:e8`. Programming bridge is `/dev/cu.usbmodem5B910667991` (USB 1a86:55d3). FTDI field converter is on board USB-A and has its own identity in [protocol evidence](docs/protocol-evidence.md).

Pinned ESP-IDF: **v5.5.5**, commit `b774170ff46c393eeb5e495ea37936038d3f4f4f`. Use pre-v3 silicon settings, minimum revision 1.0, maximum 1.99; never force a revision mismatch. Matching board schematic: native EMAC/IP101, MDC GPIO31, MDIO GPIO52, reset GPIO51, PHY address 1, RMII external clock. USB host uses the P4 high-speed controller; FTDI negotiates its own speed. PSRAM uses the board's 200 MHz configuration.

```sh
cd /Users/jimcochran-miller/est3-metasys-gateway
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
git submodule update --init
# Provision only on a NEW checkout without existing private credentials:
.venv/bin/python tools/provision.py
tools/idf.sh build
.venv/bin/python tools/package_release.py
```

`tools/idf.sh` defaults to the already-installed `/Users/jimcochran-miller/esp-idf-v5.5.5`; set `IDF_PATH` for another location. It uses the IDF Python environment and isolated CMake/Ninja. Exact USB dependency hashes are in `firmware/dependencies.lock`. Full build output and binary hashes are under `evidence/`.

Initial installation changes the partition layout. It was performed only after saving all 32 MB to `evidence/original-flash.bin`, with SHA-256 alongside it. That backup is local/private and excluded from Git. Do not casually erase identity storage on later updates. Existing NVS/registry/journal must survive application upgrades.

## Ethernet updates

PoE Ethernet operation, an application update to 0.1.3 and automatic rollback have now been tested on this board with USB-C disconnected. Current DHCP address is `10.0.7.195`; keep EST wires disconnected. DHCP hostname is `est3-p4-e41fe8`; no Wi-Fi is enabled. Locate its lease by MAC, or use a targeted BACnet request on the correct subnet:

```sh
.venv/bin/python tools/discover.py --broadcast YOUR_SUBNET_BROADCAST
.venv/bin/python tools/gateway_client.py --host DEVICE_IP status
.venv/bin/python tools/gateway_client.py --host DEVICE_IP upload firmware/build/est3_gateway_rxonly.bin
```

The client verifies the TLS chain/time and exact device certificate pin, authenticates with the local token, and signs the image with the separate ECDSA signing key. Device validates the signature, project name, image structure/chip compatibility and partition size before boot selection. Two 5 MiB app slots support rollback. The client checks the new boot after 10 seconds and explicitly confirms it. If no authenticated confirmation arrives within 180 seconds, firmware rolls back. Power loss on an unconfirmed image also triggers ESP-IDF rollback. Initial serial installation is not an OTA rollback test.

The uploader also requires the running ELF hash to match the uploaded image before confirming. **Use 0.1.3 or later:** 0.1.1 omits that hash, and 0.1.2 incorrectly truncated it to nine characters through ESP-IDF's configured diagnostic helper. The client refused to confirm 0.1.2, and the board returned to 0.1.1 automatically. Version 0.1.3 formats all 32 descriptor bytes and was successfully confirmed remotely.

`--no-confirm` on upload intentionally tests timeout rollback on a disconnected bench device. Timeout rollback has been observed over Ethernet; physical power-cut recovery remains untested. Application updates preserve NVS. Bootloader/partition-layout updates require USB. No Secure Boot, encryption or anti-rollback eFuses were changed. Keep `private/` and firmware binaries private: the TLS server key and device token are embedded; the OTA signing private key stays on the Mac and never enters the firmware.

## Host and simulator

```sh
.venv/bin/python tools/run_host.py
# HTTPS on https://127.0.0.1:8443; Basic-auth password is the viewer token
# in private/tokens.json. Any username is accepted. Never put tokens in URLs.
.venv/bin/python -m simulator.demo evidence/a-new-demo-directory
```

Host defaults to loopback and `private/history.sqlite`. Set `EST3_DB` to the demo's `simulation.sqlite` before starting the host to browse SIMULATION_ONLY history. For hardware bench testing, use a separate database, `EST3_BIND` set to the Mac's specific LAN address, and `EST3_GATEWAY_ID=P4-e8f60ae41fe8`. Install the local host certificate in a test browser or use a client with `private/host-cert.pem` as trust; do not use insecure TLS bypasses. A permanent always-on host has not been selected or installed into Metasys.

API v1 has separate viewer, manager and gateway credentials. Manager can import the **explicit mock catalog format**, obtain the compact gateway registry and request Metasys dry-run proposals. Gateway can deliver bounded telemetry batches. UI has searchable directory/history and stable `/devices/UUID` links. Source text is HTML-escaped, with restrictive CSP. Canonical schemas are generated in `schemas/` from the Pydantic models. SQLite uses WAL, FULL synchronous commits, and ordered migrations. Use `Store.backup()` for consistent online backups.

Firmware diagnostics use an authenticated HTTPS host endpoint with a fixed trusted host certificate and expected identity `est3-host.local`. Configure its URL using authenticated `POST /api/v1/host` with `{"url":"https://HOST:8443/api/v1/telemetry"}` after arranging the host's actual bind address/firewall. The default loopback host is not reachable from the device. NTP initializes device UTC before outbound certificate-time validation; failed trust, unavailable time or host outage leaves records queued.

The MCU journal retains 32 durable diagnostic records, one per minute plus startup. Its stream/session ID and sequence persist across reboots; each startup creates GATEWAY_BOOT. It retries the identical oldest record until a durable host acknowledgement. Unsurrendered records are never discarded after an uncertain response. Overflow drops only newly generated, never-sent records, reserves their sequence range, and later emits an explicit gap. That policy is bounded diagnostics retention, not proof of continuous EST event capture. Real decoded panel-event delivery remains gated by the missing protocol implementation. At nominal load, a full-blob journal commit is about 21 KiB per diagnostic and again per acknowledgement; measure flash endurance/load before acceptance.

## Tests

```sh
export IDF_PATH=/Users/jimcochran-miller/esp-idf-v5.5.5
export PATH="$PWD/.venv/bin:$PATH"
cmake -S tests -B build-tests -G Ninja
cmake --build build-tests
ctest --test-dir build-tests --output-on-failure
.venv/bin/python -m pytest tests -q
```

Native C tests run ASan/UBSan over state/registry logic, malformed and truncated input. BACpypes3 independently tests the actual C stack/port on localhost. A separate stress test provisions 1,000 logical devices / 5,000 condition BIs plus gateway diagnostics. This is software capacity evidence, not a measured hardware/site capacity claim. `simulator/serial_peer.py` is a separate disconnected RS232 bench peer, never part of production firmware.

Identity allocation, metadata/state separation, telemetry deduplication and gaps, UI injection, restart recovery, and Metasys dry-run behavior are executable tests. [TEST_MATRIX.csv](docs/TEST_MATRIX.csv) retains NOT_RUN for electrical captures, real ECP, actual Metasys and other unperformed acceptance steps.

## Metasys and field gates

[PICS](docs/PICS.md) states implemented BACnet services and read-only behavior. Metasys reconciliation produces deterministic proposals and preserves unmanaged relationships; it performs **no site writes**. Mapper schemas, license/roles, engine capacity, native graphics, alarm configuration and external-page navigation still need the installed system. New points remain unplaced until coordinates/engineering work are supplied.

Do not infer complete inventory from events. A supported contractor export importer cannot be written until its real format is supplied. Version-matched ECP documentation, authorized captures, RS232 electrical verification, independent TX capture, contractor port/wiring confirmation and a mixed-load soak remain gates before field commissioning. Ethernet update and timeout rollback results are recorded in [the hardware test report](docs/ETHERNET_TEST_REPORT.md).

# Tested first draft — USB complete; Ethernet pending

Updated 2026-09-27. Original Desktop ZIP and supplied NEXT_SESSION_PROMPT.md reviewed; ZIP CRC and SHA-256 manifest verified. Source, firmware, host, simulation, schemas, migrations and executable tests are in this repository.

| Item | Actual result |
|---|---|
| Hardware | ESP32-P4 revision 1.3; 32 MB flash; 32 MB PSRAM self-test passed; MAC `e8:f6:0a:e4:1f:e8` |
| USB-A converter | FTDI `0403:6001`, bcdDevice `0600`, `USB-RS232-WE-1800-BT-5.0`, serial `ABBAWJDO`; opened with requested 19200 8N1 |
| Original flash | All 32 MB backed up before installation; private backup and checksum retained |
| Installed application | **0.1.1**, flashed through USB-C; written data hash verified |
| USB observation | 180-second capture; health through uptime 175 s; stable heap after enumeration; zero reported USB/line errors; no spontaneous reset observed |
| Update candidate | **0.1.2**, built and archived, **not installed**; exact running ELF hash added to authenticated status |
| Software checks | **25 pytest tests passed**; **1 native ASan/UBSan C test passed**, including 10,000 malformed inputs |
| Software capacity | 1,000 logical devices / 5,000 condition objects plus 4 health objects and Device object; independent client reads passed |
| Ethernet / PoE | Owner confirmed PoE switch/injector as power source; physical transition confirmation and network tests pending |
| Panel / Metasys | Panel wires disconnected per owner; no panel testing or Metasys writes |

The capacity and native BACnet results are software evidence. The short idle USB observation is not a mixed-load or 24-hour soak. Flashing and console opens intentionally reset the board. The file named `usb-reconnect-observation.log` did **not** observe a confirmed physical hotplug.

## Implemented

- ESP-IDF v5.5.5, pinned FTDI/CDC components, bounded receive queue, counters and reconnect code. ECP and serial payload TX disabled; linked ELF has neither the simulation observer nor the driver's payload transmit function.
- Durable identity registry, epochs, tombstones and independent condition quality. Production rejects simulation registries. No real detector objects are provisioned without a genuine supported export or verified protocol.
- Read-only BACnet/IP using pinned bacnet-stack. Independent native tests cover discovery, RP/RPM, indexing, concurrent conditions, stale quality and control rejection. Production Device 3899000 and vendor 65535 are lab placeholders requiring site/assigned replacements.
- Authenticated HTTPS management and ECDSA-signed dual-slot OTA with remote confirmation and 180-second rollback deadline. Client verifies expected new ELF hash. **Ethernet upload and rollback remain untested.**
- Bounded NVS diagnostic outbox with TLS delivery, durable ACKs and explicit gaps. Ethernet replay/outage/overflow behavior remains untested.
- FastAPI/SQLite host with authentication, migrations, searchable directory/history, stable UUID links and reconciliation. The same simulated events were checked through host API and native BACnet. Mock catalogs are SIMULATION_ONLY. Metasys output is dry-run only.

## Next physical action

Disconnect USB-C, then connect board Ethernet to PoE on the Mac's LAN (currently `10.0.7.x`). Leave FTDI on USB-A and panel wires disconnected. Console capture is stopped and programming port released. Confirm PoE connection; supply DHCP lease if known.

Next checks: targeted discovery, pinned/authenticated status, independent BACnet reads, rejected updates, signed 0.1.2 upgrade, deliberate timeout rollback and host telemetry replay. Preserve the USB-tested 0.1.1 image. No Ethernet test is passed from code/build success alone.

## Remaining field gates

RS232 levels, actual baud, continuity, unused-lead insulation, PoE USB-A VBUS under load, independent zero-payload-TX capture, binary RX, physical hotplug, overload and combined load remain NOT_RUN. No instrument or independent RS232 peer is attached. Driver binds candidate VID/PID and logs descriptors; physical cable verification remains separate.

Real ECP needs exact panel/firmware/mode documentation and authorized captures. Complete inventory, program-change detection and genuine export format remain unavailable. Current CPU/TB2/3-RS232 photos, available port/settings and contractor agreement remain prerequisites. Metasys version, licensing, capacity, schemas, graphics and navigation need installed-site validation. Coordinates and production BACnet assignments are also missing.

**Working remote updates will not make this firmware ready to read EST.** This is a development draft with its panel protocol intentionally disabled.

## Evidence and recovery

- [Test report](docs/TEST_REPORT.md), [acceptance matrix](docs/TEST_MATRIX.csv), [software results](evidence/software-tests.log), [C sanitizer results](evidence/core-tests.log), [USB capture](evidence/usb-0.1.1-soak.log)
- [0.1.1 manifest](evidence/build-manifest-0.1.1.json), [0.1.2 manifest](evidence/build-manifest-0.1.2.json), [0.1.2 build log](evidence/firmware-build-0.1.2.log)
- [Protocol boundaries](docs/protocol-evidence.md), [BACnet support](docs/PICS.md), [recovery](docs/OPERATIONS.md), [licenses](docs/THIRD_PARTY.md)

Credentials and built images stay local, excluded from Git. App images contain the device TLS key/token; signing private key stays on the Mac. Secure Boot and flash encryption are disabled; no eFuses were modified.

# Tested first draft — Ethernet update and rollback verified

Updated 2026-09-28. Original Desktop ZIP and supplied NEXT_SESSION_PROMPT.md reviewed; ZIP CRC and SHA-256 manifest verified. Source, firmware, host, simulation, schemas, migrations and executable tests are in this repository.

**Current field observation:** the device at **192.168.75.157** runs **0.1.4**, remotely installed and confirmed on `ota_0`, boot count **12**. HTTPS and independent BACnet reads passed. The owner's first Printer 2 Revision Levels report produced framing errors at 19200; repeating it at **9600 8N1** delivered a complete **3,564-byte readable report**, with no capture gaps or new UART/USB errors/drops. Panel printer-report reception is confirmed; real-time EST state decoding remains unimplemented. The receiver currently uses 9600, but 0.1.4 still boots at 19200. Owner confirms yellow to TX2, black to COM2 and orange disconnected. See [field results](docs/FIELD_CONNECTION_TEST.md) and [receiver diagnostics](docs/SERIAL_DIAGNOSTICS.md).

| Item | Actual result |
|---|---|
| Hardware | ESP32-P4 revision 1.3; 32 MB flash; 32 MB PSRAM self-test passed; MAC `e8:f6:0a:e4:1f:e8` |
| USB-A converter | FTDI `0403:6001`, bcdDevice `0600`, `USB-RS232-WE-1800-BT-5.0`, serial `ABBAWJDO`; opened with requested 19200 8N1 |
| Original flash | All 32 MB backed up before installation; private backup and checksum retained |
| Installed application | **0.1.4**, uploaded over the field Ethernet route, rebooted, full ELF hash verified and remotely confirmed on 2026-09-28 local time; `ota_0`, boot count 12 |
| USB observation | 180-second capture; health through uptime 175 s; stable heap after enumeration; zero reported USB/line errors; no spontaneous reset observed |
| Recovery test | Unconfirmed **0.1.2** automatically rolled back to **0.1.1** after its 180-second deadline; Ethernet access recovered without USB |
| Software checks | **25 pytest tests passed**; **2 native ASan/UBSan C tests passed**, including 10,000 malformed core inputs and binary/status-prefix/ring-wrap diagnostics tests |
| Software capacity | 1,000 logical devices / 5,000 condition objects plus 4 health objects and Device object; independent client reads passed |
| Ethernet / PoE | Owner connected PoE with USB-C removed; device found at **10.0.7.195**; authenticated HTTPS, FTDI enumeration and independent BACnet RP/RPM passed |
| USB-A hotplug | Physical disconnect/reconnect observed over Ethernet; adapter reconnects increased 1 to 2, boot count stayed 9, no new USB errors; BACnet reads still passed |
| Network load with adapter idle | 60 seconds, 131 authenticated HTTPS status reads plus 564 BACnet reads; FTDI remained attached, no reboot/new USB errors; no serial payload traffic |
| Invalid updates | Bad signature, signed truncated image, wrong project and interrupted upload rejected/aborted; running image and boot count preserved |
| Panel / Metasys | Complete real panel revision report received at 9600 8N1 without new errors/drops; real-time state decoding unimplemented; no Metasys writes |

The capacity and native BACnet results are software evidence. Short idle observations are not a mixed-load or 24-hour soak. Flashing and console opens intentionally reset the board. The older `usb-reconnect-observation.log` did not capture a hotplug; the later physical test is recorded in `evidence/adapter-hotplug-result.json`, at approximately 51 minutes of uptime with no serial traffic.

## Implemented

- ESP-IDF v5.5.5, pinned FTDI/CDC components, bounded receive queue, counters and reconnect code. ECP and serial payload TX disabled; linked ELF has neither the simulation observer nor the driver's payload transmit function.
- Authenticated serial diagnostics separate FTDI USB status packets from UART data and retain the last 512 payload bytes. A bounded receiver-only baud API applies settings in the USB connector task, defaults to 19200 after reboot, and cannot transmit payload. Version 0.1.4 also corrects the pinned driver's modem-control request/masks through explicit FTDI vendor requests. This correction did not produce panel bytes and is not established as the cause of the silent connection.
- Durable identity registry, epochs, tombstones and independent condition quality. Production rejects simulation registries. No real detector objects are provisioned without a genuine supported export or verified protocol.
- Read-only BACnet/IP using pinned bacnet-stack. Independent native tests cover discovery, RP/RPM, indexing, concurrent conditions, stale quality and control rejection. Production Device 3899000 and vendor 65535 are lab placeholders requiring site/assigned replacements.
- Authenticated HTTPS management and ECDSA-signed dual-slot OTA with remote confirmation and 180-second rollback deadline. **Actual Ethernet update, full-hash confirmation and timeout rollback passed.** Version 0.1.2 exposed a truncated hash and was correctly left unconfirmed; 0.1.3 fixes the reporting bug.
- Bounded NVS diagnostic outbox with TLS delivery, durable ACKs and explicit gaps. Actual Ethernet replay delivered all 32 retained records, recorded the 193-record offline gap and drained the queue. See the Ethernet report for the exact scope; extended outage/load tests remain.
- FastAPI/SQLite host with authentication, migrations, searchable directory/history, stable UUID links and reconciliation. The same simulated events were checked through host API and native BACnet. Mock catalogs are SIMULATION_ONLY. Metasys output is dry-run only.

## Current access and next checks

Board is now at `192.168.75.157`, reachable from the Mac at `192.168.2.34`. USB-C remains unavailable; the owner reports panel attachment and FTDI remains connected. Read status with `tools/gateway_client.py`. The address is a DHCP lease; rediscover by Device 3899000 / MAC `e8:f6:0a:e4:1f:e8` if it changes, then verify the saved TLS certificate before authenticating. Recent work installed receiver diagnostics and changed only adapter receiver settings; no serial payload or operational command was sent to the panel. Disconnected-bench disruption tests are not appropriate to this reported attachment state.

Remote application updates and rollback were verified on the previous bench LAN; the 0.1.4 update and confirmation also passed across the field-network route. Bootloader/partition-table changes and physical hardware faults are outside that recovery path. An extended mixed-load soak remains outstanding. Preserve the private keys and known-good release images. See [actual Ethernet results](docs/ETHERNET_TEST_REPORT.md).

Three genuine owner-local SDU project backups were found and read without modifying the originals. The newest has March 2026 cabinet data identifying main cabinet 01 as a 3-CPU3 configuration consistent with the photos. Its ECP table has zero active records; raw Port 2 type/baud codes are 1/4, but their enum labels remain unverified. The live report identifies panel 01, CPU 05.30.00, SDU 05.47.00, project 01.01.02 and database date 03/04/26. Those fields are consistent with the newest backup; they do not establish a complete configuration match or validated inventory import.

## Remaining field gates

RS232 levels, actual baud, continuity, unused-lead insulation, PoE USB-A VBUS under load, independent zero-payload-TX capture, binary RX, hotplug during serial traffic, overload and combined load remain NOT_RUN. No instrument or independent RS232 peer is attached. Driver binds candidate VID/PID and logs descriptors; physical cable verification remains separate.

Real ECP needs exact panel/firmware/mode documentation and authorized captures. Genuine SDU backups are now available locally, but their schema, complete inventory and match to the installed revision are not validated; program-change detection remains unavailable. CPU/TB2 photos were supplied on 2026-09-28; verified 3-RS232 card identity, live port/settings and contractor agreement remain outstanding. Metasys version, licensing, capacity, schemas, graphics and navigation need installed-site validation. Coordinates and production BACnet assignments are also missing.

**Receiving a readable printer report is not real-time EST state monitoring.** This development draft still has ECP parsing disabled and no validated printer-event decoder.

## Evidence and recovery

- [Test report](docs/TEST_REPORT.md), [acceptance matrix](docs/TEST_MATRIX.csv), [software results](evidence/software-tests.log), [C sanitizer results](evidence/core-tests.log), [USB capture](evidence/usb-0.1.1-soak.log)
- [0.1.1 manifest](evidence/build-manifest-0.1.1.json), [0.1.3 manifest](evidence/build-manifest-0.1.3.json), [0.1.3 build log](evidence/firmware-build-0.1.3.log), [confirmed Ethernet update](evidence/ethernet-update-0.1.3.json), [rollback result](evidence/ethernet-rollback-result.json)
- [0.1.4 manifest](evidence/build-manifest-0.1.4.json), [field update](evidence/field-update-0.1.4.json), [later stability read](evidence/field-stability-0.1.4.json), [serial checks](evidence/field-serial-diagnostics-0.1.4.json), [API rejection tests](evidence/serial-api-validation-0.1.4.json), [BACnet reads](evidence/field-bacnet-0.1.4.json), [software tests](evidence/software-tests-0.1.4.log), [C sanitizer tests](evidence/core-tests-0.1.4.log)
- [Real Printer 2 report result](evidence/field-panel-report-0.1.4.json); raw report text stays private.
- [Protocol boundaries](docs/protocol-evidence.md), [BACnet support](docs/PICS.md), [recovery](docs/OPERATIONS.md), [licenses](docs/THIRD_PARTY.md)

Credentials and built images stay local, excluded from Git. App images contain the device TLS key/token; signing private key stays on the Mac. Secure Boot and flash encryption are disabled; no eFuses were modified.

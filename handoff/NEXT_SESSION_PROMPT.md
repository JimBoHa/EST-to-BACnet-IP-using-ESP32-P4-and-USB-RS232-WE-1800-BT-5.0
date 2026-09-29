# Continue the EST3 monitoring system to verified site completion

This is a continuation of an implemented, hardware-tested project. Work from the supplied private handoff bundle and existing repository. Do not restart the design, provision new credentials, or stop at another plan. The owner wants a fully functional supplemental monitoring system exposing **everything that can be reliably obtained from this installed EST panel**, through a searchable device/event service and individual native Metasys points and graphics.

First read `START_HERE.md`, this file, `COMPLETION_PLAN.md`, and `TRANSFER.md` in the bundle. Verify the bundle with `restore.py`, restore it to a new local workspace, then read the restored repository's `STATUS.md`, `docs/FIELD_CONNECTION_TEST.md`, `docs/SERIAL_DIAGNOSTICS.md`, `docs/PICS.md`, and `docs/TEST_MATRIX.csv`. `BUNDLE_MANIFEST.json` records the source commit, toolchain pins, file hashes, and latest connectivity observation. The `original-spec/` directory preserves the detailed original requirements, drawings, manuals and reference reviews. Its old session prompt is historical; newer verified facts below take precedence.

## Owner intent and how to work

Implement, test and document the remaining code and deployment work. The owner has authorized source changes, tests, signed application OTA over Ethernet, and commits/pushes to the repository. Continue independent work while asking only for genuinely missing site information. Do not keep requesting approval for already-authorized routine development or OTA. The owner prefers short updates and dislikes prolonged investigation of hypothetical faults. Take evidence-driven steps and use a concrete field test when it answers the question.

The EST technician has left. That is not a reason to stop software work or insist on an ECP conversion before using the already-working printer output. The owner can use the panel display and has successfully requested read-only revision reports. Ask for authorized read-only reports when useful. Do not promise that a session can conjure unavailable protocol capabilities or site permissions; document specific limitations and implement the best supported path.

No USB-C recovery is available at the deployed controller. Preserve Ethernet management, device identity, signing trust, NVS identity storage and rollback throughout. Keep changes incremental. Source and ordinary test evidence can go to GitHub; the private bundle, keys, firmware images, SDU archives, site drawings/photos, raw serial reports, databases and access details must not be published.

## Verified hardware and current firmware

- Repository: `https://github.com/JimBoHa/EST-to-BACnet-IP-using-ESP32-P4-and-USB-RS232-WE-1800-BT-5.0`. The repository was already renamed from its former Pico2 name. Code/evidence through `6aab69c06fad794c3c9f9b0706963a6ccc28eb92` were pushed; the bundle includes a later handoff commit, identified in its manifest.
- Controller: Waveshare **ESP32-P4-WIFI6-POE-ETH**, P4 silicon revision **1.3**, 32 MB flash, 32 MB PSRAM. Native EMAC + IP101 PHY, MDC GPIO31, MDIO GPIO52, PHY reset GPIO51, PHY address 1, external RMII clock. Use the pre-v3 P4 configuration already committed.
- Power: PoE; USB-C disconnected and unavailable. No Wi-Fi. USB-A hosts the FTDI cable. Do not return to the obsolete ESP32-S3, Pico2, SC16IS752 or W5500 architecture.
- MAC: `e8:f6:0a:e4:1f:e8`; DHCP hostname `est3-p4-e41fe8`; last verified IP **192.168.75.157**. This is a DHCP lease, not a guaranteed permanent address. The previous Mac reached it from `192.168.2.34` through a router. The new machine needs an authorized route/VPN or placement on the site's network.
- Converter: USB VID/PID **0403:6001**, bcdDevice 0600, product `USB-RS232-WE-1800-BT-5.0`, serial **ABBAWJDO**. Physical manufacturer identity/isolation and full electrical measurements are not independently certified.
- Owner reports yellow adapter RX landed on panel **TX2**, black signal common on **COM2**, orange adapter TX disconnected. Other unused leads must be individually insulated; red is auxiliary +5 V, not panel power. Photos are included. Do not change this working connection or infer different wiring from photo perspective.
- Installed application: **0.1.5**, project `est3_gateway_rxonly`, **ota_1**, last validated boot count **13**, explicitly confirmed. Receiver boots at **9600 baud, 8N1, no flow control**. API overrides are volatile. Serial payload transmission and ECP parsing remain disabled.
- Running ELF SHA-256: `ce886d6d019d2093268fc97cba634e816ae203d968f7f40cd6156cf6524e6a89`.
- Archived 0.1.5 app binary SHA-256: `9e08f55021ed88b800211bb56d808209517227806e47c9842146fd4a533a8300` (935,200 bytes). ELF descriptor hash and binary-file hash are different values with different purposes.
- Retained other slot: **0.1.4**, which boots at 19200. Its authenticated receiver API can select 9600 remotely if it is recovered. Private known-good images and checksums are supplied.

First verify the latest observed status from the bundle; then attempt a bounded read-only connection from the new machine. A failed route from one machine does not prove the firmware has failed. Do not send the device token until its TLS chain/time and exact leaf certificate match the retained certificate. Never use an insecure TLS bypass.

## What the panel test proved

The panel was initially silent while idle. New firmware 0.1.4 distinguished healthy USB status-only transfers from actual UART payload. Requesting a Revision Levels report through the display produced bytes with framing errors at 19200. **9600 8N1 resolved the errors.** Three complete reports, 5,346 bytes, were captured on 0.1.4. Firmware 0.1.5 made 9600 the boot default, was installed and confirmed over Ethernet, and received two additional complete reports, 3,564 bytes, after reboot. Across those five reports: no missing capture offsets, no new UART/USB errors, and no application receive drops. The corrupted earlier 19200 capture is separate and is not a valid parser fixture.

Read-only report procedure already worked at this site: physical **Command Menus**, **Report/Reports**, **Revision Levels**, panel **01**, output **Printer 2**. Reference: Edwards EST3 System Operation Manual 270382-EN R012, printed page 35. The report identifies panel 01, CPU **05.30.00**, SDU **05.47.00**, project **01.01.02**, database date **03/04/26**. This manual's stated firmware scope is 5.4x; the specific report path was nevertheless verified on the installed 5.30 CPU. Validate other commands against the installed system instead of assuming universal compatibility.

This proves printer-report reception, not ongoing alarm/restore coverage, complete inventory, current-state recovery or ECP operation. Idle silence is not a hardware failure and not proof that all detectors are normal. A report's historical `ALARM COUNT` is not an assertion that that many alarms are currently active. Preserve panel timestamps separately from host receive UTC: observed report time was about an hour behind the Mac's local time, and the panel clock/time-zone semantics have not been established. Do not change the panel clock.

## Existing implementation: reuse it, understand the gaps

1. `firmware/main/serial_rx.c` handles the FTDI connection and receives queued payload. **Its consumer only updates a CRC and discards payload; it does not parse or forward panel events.** The queue is 128 chunks of up to 64 bytes. `serial_diagnostics.c` provides a 512-byte tail, not a durable event stream.
2. `management.c` exposes authenticated HTTPS status, signed OTA, confirmation, registry upload, host URL configuration, and `/api/v1/serial` diagnostics/receiver baud control. There is no arbitrary serial-write endpoint. The serial GET returns raw payload and must be kept private.
3. FTDI 2.1.1 has incorrect modem-control request/mask definitions in the method previously used. The application works around them with explicit FTDI requests: request 2 disables flow; request 1 with 0x0100 and 0x0200 separately deasserts DTR and RTS. Preserve the raw-IN observer and exactly-once status-byte stripping. Do not reintroduce the old method by a casual refactor.
4. `firmware/components/gateway_core/` implements stable registry identities, epochs, independent alarm/trouble/supervisory/disabled condition quality and stale behavior. Production rejects simulation registries. `gw_observe` is currently absent from the production ELF; adding a validated real decoder will require a deliberate revision of the symbol audit, while keeping simulation injection and serial payload TX excluded.
5. `firmware/components/bacnet_gateway/` provides read-only BACnet/IP discovery, RP and RPM, using pinned bacnet-stack. Current hardware has Device + four health BIs, **zero real detector objects**. Device instance 3899000 and vendor 65535 are explicit lab placeholders. No COV, BBMD/foreign-device registration, segmentation or BACnet/SC is implemented. The core currently allows 1,000 devices / five BIs per logical device; software tests are not measured site capacity.
6. `firmware/main/telemetry.c` is a 32-record **diagnostics-only** durable NVS outbox. It is not a panel event recorder. It records overflow gaps and durable ACKs. Repeatedly serializing the whole roughly 21 KiB blob is not an appropriate unmeasured high-rate event-storage design. Extend storage/transport deliberately, including flash-wear and outage budgets.
7. `host/` has FastAPI, SQLite migrations, authenticated registry/telemetry APIs, directory/history pages, durable UUIDs and reconciliation. `Catalog` currently accepts only `source_mode=simulation` and `fixture_only=true`. `Batch` accepts only simulation/protocol_disabled, with real events rejected in protocol_disabled. Implement versioned real-source schemas and migrations; do not relabel real data as simulated or remove validation indiscriminately.
8. `host/metasys.py` is **dry-run only**. No installed Metasys server/API/license/schema, point engineering or graphic placement has been verified. BACnet discovery alone is not Metasys commissioning.
9. The temporary diagnostics host URL is still the old `https://10.0.7.6:8443/api/v1/telemetry`. It was not migrated to the field route. The outbox filled and recorded drops while that endpoint was unreachable. These diagnostic drops are not the serial receive drop counter. No permanent host service exists yet.

Read `COMPLETION_PLAN.md` for the required implementation and acceptance sequence. Start with durable raw RX capture and actual printer/report parsing, then validated inventory, state recovery, BACnet/host integration and Metasys deployment. Do not start by guessing ECP frames or switching the panel port away from the working printer output.

## Local source evidence now available

The bundle contains three genuine SDU archives under `site-inputs/sdu/`, source photos and PNG previews, raw report captures under the restored `private/`, and the original drawings/manuals. Archives are ZIP containers with Paradox tables. Read-only inspection used pypxlib 2.5 and native pxlib 0.6.8, source commit `e32d17611e5ee353c4e3ce04e61b0b38feb95855`. The original archives were not modified. The old Mac's compiled libraries are not portable; the bundle supplies source/review notes, not a promise that that wheel runs on the new OS.

The newest archive, `100_ENTR_01_01_02_15.SDU`, has March 4, 2026 cabinet data. Main cabinet 01 is a 3-CPU3 configuration and its A/B bypass module matches the photos. Cabinet 02 is the lobby annunciator. Main-cabinet port type/baud values are raw enum codes 1/4; their schema labels were not independently decoded. All three ECP table headers report zero active records. The observed printer output is the reliable live evidence. SDU PC download baud is a separate field and is not the panel auxiliary-port baud.

The live project/version/date are consistent with the newest backup, but no complete live program comparison has been done. The zip member timestamps and a filename saying "most updated" are not authoritative live revision proof. Validate table counts, identities, node/card/loop/address relationships, labels, device types, optional records, logical groups, and coverage before declaring an inventory complete. Paradox files can contain credentials; read selected fields and keep raw tables private.

## Working access, updates and tests

Follow `TRANSFER.md` for Windows/macOS/Linux setup. The restore script never installs packages, opens the device, changes network settings or flashes firmware. It reconstructs the Git checkout/submodule and restores the existing private credentials and recovery artifacts. Do **not** run `tools/provision.py` on this controller's checkout. Do not copy an old `.venv`, CMake cache or compiled Mac library into the new environment.

Pinned ESP-IDF is **v5.5.5**, commit `b774170ff46c393eeb5e495ea37936038d3f4f4f`; pinned bacnet-stack is **1.5.2**, commit `d2468d56de3d156659a9051c95119e3a6e11c421`. Keep the dependency lock and pre-v3 P4 revision range 1.0–1.99. Preserve the partition table, bootloader and eFuses. App changes need a new release version; never overwrite a different archived binary with the same release version.

Use the project Python environment for:

```text
python tools/gateway_client.py --host 192.168.75.157 status
python tools/bench_bacnet.py --host 192.168.75.157 --local-ip YOUR_ROUTED_IP --output private/new-bacnet-check.json
```

The existing uploader signs locally, checks the full running ELF hash against the application descriptor, and confirms a healthy boot after 10 seconds. A new image not confirmed within 180 seconds rolls back. Timeout rollback and invalid/interrupted update tests already passed on the disconnected bench; do not casually repeat disruption tests on the attached live panel. Firmware 0.1.2 had a truncated-hash defect and must not be selected as a working recovery release. 0.1.4 and 0.1.5 field-route updates passed without USB.

Automated baseline: 25 Python tests and two ASan/UBSan native tests passed. Independent BACpypes3 reads passed on real 0.1.5 hardware. The simulator exercised 1,000 logical devices / 5,000 conditions plus health objects in software. No long-duration mixed-load hardware soak, complete binary RS232 peer test, independent TX electrical capture or real Metasys commissioning was performed. Use the test matrix honestly; historic NOT_RUN rows sometimes contain newer partial evidence in current docs, and must be reconciled without relabeling partial tests as full passes.

## Boundaries that remain in force

This is supplemental monitoring, not a replacement for the fire panel or its certified functions. No panel acknowledge, reset, silence, enable, disable, drill, time/date setting, programming or arbitrary serial transmit route belongs in this product. Do not use a live panel for fuzzing, synthetic alarms, brownout, destructive recovery or USB loopback experiments. Such physical acceptance tests need an appropriate isolated bench or specifically coordinated site procedure.

Current deployment is physically RX-only: leave orange disconnected. If printer output demonstrably cannot provide a required capability, quantify the limitation and investigate a supported read-only integration option. Future ECP requires version-matched protocol documentation, exact permitted reads/transport handshakes, independent outbound verification and a concrete coordinated wiring/configuration plan; do not infer permission to add a transmitter from this continuation prompt. The FieldServer manual describes a panel-master poll/response model and is not a complete wire specification.

## Definition of completion

Deliver a working, durable end-to-end path from verified panel output to host history and appropriately qualified native BACnet/Metasys values, with stable identities and tested restore semantics. Include all source-supported information, preserve unknown/raw observations, and publish a capability/coverage matrix identifying information unavailable through the installed interfaces. Never turn missing data, quiet printer output, a gateway heartbeat or a parsed device label into a normal state.

Demonstrate startup/current-state recovery, independent simultaneous conditions, event loss and replay, host/network outages, catalog changes, stable object bindings, native Metasys point/quality/graphic behavior, backups, rollback and at least a 24-hour permitted mixed-load soak. Establish the permanent host, retention, clock/trust handling and operating runbook. Explicitly identify unavoidable export delivery, graphic placement or hardware/contractor steps. Do not claim zero-touch synchronization where the source or Metasys lacks the required capability.

Maintain status, tests, coverage decisions and a resumable work log as you implement. Ask the owner for the minimum concrete missing input when needed, while continuing the independent work. Finish with exact versions/hashes, deployment addresses, recovery procedure, passing evidence and any specific unsupported capability—never a blanket claim that "everything works" based only on a printed report.

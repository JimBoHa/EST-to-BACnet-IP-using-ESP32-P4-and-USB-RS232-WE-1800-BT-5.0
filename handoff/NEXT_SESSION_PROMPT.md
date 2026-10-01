# Continue from deployed standalone 0.1.14

Read repository `STATUS.md`, `docs/WORK_LOG.md`, `docs/SOURCE_COVERAGE.md`,
`docs/PORT_CONFIGURATION_REVIEW.md`, `docs/SITE_VISIT_CHECKLIST.md`,
`docs/AS_BUILT_REVIEW.md`, `docs/STANDALONE_OPERATIONS.md`, `docs/PICS.md` and
`docs/TEST_MATRIX.csv`. This prompt supersedes the original 0.1.5 handoff prompt.
Do not restart completed import/UI work or restore old source over this checkout.

## Owner scope and authorization

Only ESP32-P4 and Metasys are permanent components. The P4 hosts configuration,
diagnostics and the directory. Recent receiver records use bounded RAM, not a
long-term recorder. No permanent Mac/FastAPI/history service is wanted. The owner
will test Metasys after automatic EST readings are reliable; independent BACnet
verification is authorized now. Do not request host or Metasys details again.

Source edits, relevant tests, signed application OTA and commits/pushes are
already authorized. Keep updates incremental and preserve Ethernet recovery.
No USB-C recovery is available. Do not provision new credentials or alter the
bootloader, partitions, eFuses, physical wiring or panel programming. No panel
acknowledge/reset/silence/disable, arbitrary serial writes, live fuzzing, staged
alarms, brownout or physical disruption tests. No permission to add TX follows
from this software task. Do not use another manual Print request as proof of
unattended data acquisition. Owner prefers terse communication.

## Workspace and deployment

- Checkout: `$HOME/est3-metasys-gateway`, branch
  `continuation/printer-pipeline`; repository
  `https://github.com/JimBoHa/EST-to-BACnet-IP-using-ESP32-P4-and-USB-RS232-WE-1800-BT-5.0`.
- Actual running **0.1.14**, `ota_1`, confirmed boot **31** at last check; retained
  slot 0.1.13 has diagnostic startup pauses. Verify fresh status before action.
- Full ELF SHA-256:
  `c3bc8da2dd812651e709475f4a3748c68acaf9d4ab43280dc94249f86915c0f2`.
  App-file hash and exact pins are in `evidence/build-manifest-0.1.14.json`.
- P4 revision 1.3, 32 MB flash/PSRAM, native EMAC/IP101, PoE only. FTDI 0403:6001;
  yellow RX to panel TX2, black common to COM2, orange TX disconnected.
- Current DHCP endpoint and workstation route are in the private field records.
  Web name `est3-device.local` matches the retained certificate.
- Receiver boots at 9600 8N1 with no flow control, payload TX disabled. Preserve
  explicit FTDI vendor request 2 for flow and request 1 masks 0x0100/0x0200 for
  DTR/RTS. Keep USB status stripping exactly once and receive observer linked.
- Actual qualified registry epoch 1: 1,214 source objects, 674 SENSOR/MODULE rows,
  6,075 total BACnet objects. All conditions invalid; no normal state is inferred.
- Existing private credentials remain under `private/`. Never print them or run
  `tools/provision.py`. Verify TLS chain/time and exact leaf before sending a key.
  Browser trust follows the owner's certificate-management procedure.

## Completed implementation and evidence

Portable revision-report parsing, bounded 128-record RAM observations, source
loss/corruption/eviction diagnostics, selected-field SDU importer, stable UUIDs/BI
instances and embedded HTTPS configuration/diagnostics/search/import/update UI
are implemented. Periodic host delivery and diagnostic NVS writes are disabled;
legacy outbox bytes remain for recovery. New qualified registry uses `catalog_v2`,
leaving old `catalog` intact. Old 0.1.5 can recover management with its empty catalog.

48 Python tests, four native ASan/UBSan tests, synthetic browser checks, final
actual HTTPS/API checks and independent BACnet reads pass. Actual 0.1.14 returned
all 6,075 Object_List indices and 26,715 selected property values across all
1,214 records, while HTTPS previews ran. Boot remained 31, confirmed beyond the
rollback deadline, with no new receive errors. This was a short idle-source
transport test, not live condition, Metasys or 24-hour acceptance.

Failed candidates 0.1.7/8/10/11/12 automatically rolled back and must never be
selected for recovery. 0.1.6 has a full-catalog load defect. 0.1.9 passed full
catalog checks but uses older startup/reboot code. Exact early panic causes were
not established without a console trace. 0.1.13/14 complete staged startup with
management available before catalog load, a separately parsed registry published
under the lock, readiness gates and an 8 KiB reboot task. 0.1.14 has no artificial
diagnostic stage delays. Do not claim extended boot/load qualification.

## Remaining source boundary

**30 September update:** fresh authenticated reads recovered a complete 317-byte
tail containing a local-trouble ACT/RST pair and an inbound operator command.
Zero UART/USB errors, receive drops or record evictions; all retained line offsets
match the raw tail. Boot 31 remained confirmed after 37.34 hours uptime. The single
gap marker is the initial offset-zero marker, not observed midstream loss. Original
bytes, receipt times and source join are in `private/port-review-20260930/`.
The address joins one qualified power-supply pseudo point, not a physical sensor
or module. Do not apply this historical restore as fresh normal state. The
production decoder remains revision-only; all condition BIs remain invalid.

Five earlier revision reports establish readable transport and revision syntax:
panel 01, CPU 05.30.00, SDU 05.47.00, project 01.01.02, database date 03/04/26.
Historical alarm count is not current alarm state. Panel clock/timezone is
unverified. On-device report parsing is fixture-tested but has not yet received
a new natural report after deployment.

The owner added `Fire Alarm System Upgrade - Completed on 2019` under the original
Desktop handoff directory and confirmed no existing event log. Its three SDUs
are identical to previously supplied archives. The newest hash is
`c8bd4dedb598fea590bd5167b6fcb692e74625cfb1d00e56bd1b71b275aa200b`, already imported.
Private qualified outputs are `private/site-20260304-v2-{catalog,registry,preview}.json`.
The as-built drawings support EST3/3-CPU3 hardware, but the included 2013 manual
is EST3X/SFS1-CPU and does not establish this CPU's event wire grammar. Do not
substitute its TB5 diagram for the actual TX2/COM2 wiring. Optional BMS-bridge
references are not proof such a bridge exists at the site.

Automatic alarm/supervisory/disabled and broader trouble/restore mappings require
additional source evidence and verified routing. Startup also
needs an authoritative state source: the RX-only connection cannot request a
snapshot, and quiet event output cannot recover conditions already active at
boot. Keep observations unknown until this is resolved. `gw_observe` is absent
from the production ELF; enabling a real decoder requires deliberate validation
and symbol-audit changes, never merely relabeling simulated data.

## Practical continuation

1. Read fresh authenticated status and recent records; compare boot/hash/registry
   and retain any new source records privately before the bounded buffer evicts.
2. Continue only work supported by newly available source evidence. Do not repeat
   requests for the already-unavailable log or promise automatic state from SDU.
3. Match validated events to qualified identities; preserve unknown system/logical
   records. Demonstrate assertion/restore, loss and initial-state semantics before
   setting condition support or DataValid. Any read-only polling alternative
   needs exact documentation and a separately coordinated physical/config plan.
4. Keep explicit limits for production BACnet assignments, electrical acceptance,
   full source recovery, Metasys and a permitted 24-hour mixed-load soak.
5. Update status, coverage, tests and work log with exact evidence. New app changes
   get a new version; never overwrite a different binary under an existing version.

## Owner's next visit

The owner expects to visit late 1 October and wants no further evidence-only trips.
They confirmed **panel access only**, with no programming computer/3-SDU or EST
technician. Do not send them looking for an unverified front-panel port-settings
menu. Automatic event reception already works with yellow RX to TX2 and black to
COM2; leave orange TX disconnected. Do not promise complete ECP/state recovery
from rewiring alone. The site checklist consolidates photos, Status/History
collection and validation before leaving. Manual reports here are one-time
source fixtures, never evidence of automatic snapshots or fresh live events.

`tools/capture_printer.py` is a bounded GET-only private collector for that session,
not a permanent host service. Start it and verify READY before any report; retain
the finish record, loss markers and before/after counters. It deduplicates record
IDs across overlapping RAM windows and detects reboots. Records omit CR/LF and
gap text is synthetic diagnostics, so do not call its JSONL a byte-exact wire dump.
The existing short raw tail separately preserved the complete 317-byte event
capture. A full-rate history capture has not been exercised yet.

Pinned ESP-IDF v5.5.5 is at `$HOME/esp-idf-v5.5.5`; this workstation uses
`IDF_TOOLS_PATH=$HOME/est3-toolchains/idf5.5.5`. See README for build/test commands.
Keep original archives, raw reports, drawings, databases, images, debug ELF/map
and keys private. The original supplied bundle is immutable historical evidence;
393 present files matched hashes, with a narrow missing SQLite-sidecar restore
exception documented privately. The bundler snapshot-close defect is fixed.

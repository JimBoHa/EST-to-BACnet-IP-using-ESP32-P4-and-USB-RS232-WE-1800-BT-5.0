# Standalone P4 deployed; automatic EST state remains unverified

Updated 2026-09-30. **0.1.14 is installed and confirmed**, with an embedded HTTPS
configuration/diagnostics page and 1,214 qualified backup objects exposed through
BACnet/IP. **Unattended alarm/restore decoding and startup current-state recovery
are not complete.** Fresh readback now establishes **automatic printer-event
reception**: one local battery-trouble activation/restore pair and an operator
command record, 317 bytes with no reported receive errors/drops. All bytes were
preserved and checked against record offsets. The event address joins one backup
power-supply pseudo point. Firmware remains unchanged and conditions remain invalid.
Inventory, an inactive BI, or an idle receiver must not be interpreted as normal.

The existing receive connection needs no additional wire for this observed event
path. Exact installed port filters/mode still lack a configuration readback.
See [port review](docs/PORT_CONFIGURATION_REVIEW.md) and the
[1 October site checklist](docs/SITE_VISIT_CHECKLIST.md). The owner has panel-only
access; 3-SDU/ECP commissioning cannot be promised from that visit alone.

The owner's current scope supersedes the earlier permanent-host design: only
ESP32-P4 and Metasys are permanent components. Metasys commissioning is deferred
to the owner after reliable automatic EST data is available. No Mac/FastAPI service
is required. Periodic host delivery and diagnostic flash writes are disabled;
recent observations are bounded RAM data. Legacy NVS bytes remain for recovery.

## Installed and retained state

| Item | Verified state |
|---|---|
| Application | `est3_gateway_rxonly` **0.1.14**, `ota_1`, confirmed boot **31** |
| Reset/startup | Normal software reset (`reset_reason=3`); `startup_phase=ready` |
| Running ELF SHA-256 | `c3bc8da2dd812651e709475f4a3748c68acaf9d4ab43280dc94249f86915c0f2` |
| App-file SHA-256 | `d806e1c6840fa5797bf0c5058c946f00e701582ac2b76a49b69a3db7d50b3bb3` — 986,192 bytes |
| Hardware | P4 revision 1.3; 32 MB flash/PSRAM; native EMAC/IP101; PoE; USB-C recovery unavailable |
| Receiver | FTDI 0403:6001 attached; 9600 8N1, no flow control; physical RX-only wiring unchanged |
| Source registry | Epoch 1; 1,214 objects; 674 SENSOR/MODULE rows; all live conditions unverified |
| BACnet | Device 3899000, Vendor 65535: lab placeholders; Device + 6,074 BIs = **6,075 objects** |
| Management | `https://est3-device.local/`; current DHCP lease `192.168.75.157`; MAC `e8:f6:0a:e4:1f:e8` |
| Retained OTA slot | Confirmed 0.1.13 on `ota_0`; same functionality with diagnostic startup pauses |
| Update boundary | Application only; partition table, deployed bootloader, credentials and eFuses preserved |

[Build manifest](evidence/build-manifest-0.1.14.json) and
[confirmed update](evidence/field-update-0.1.14.json) distinguish ELF-descriptor
hash from binary-file hash. Archived images contain the retained device TLS key
and token and remain private. Do not run provisioning on this controller.

## Implemented and checked

- **On-device parsing:** strict revision-report metadata parser, offsets, stream
  epochs, loss/corruption handling, fragments and unknown raw lines. Latest 128
  records, up to 512 bytes each, stay in RAM and clear at reboot. Historical
  report `ALARM COUNT` never becomes a live alarm. No validated event reducer is
  linked; payload TX and simulation injection remain absent from the image.
- **Qualified inventory:** real selected-field Paradox/SDU import validates
  counts, unique identities and physical/LRM/type joins. All 1,214 OBJECT rows
  retained, including 361 SENSOR and 313 MODULE rows. Special scopes 0 and 255
  remain unresolved. Persistent UUIDs, BI reservations, epochs and tombstones
  survive updates. Renames preserve identity; replacement/rebinding needs review.
- **Embedded page:** status/BACnet, searchable directory and UUID links, recent
  diagnostics/export, volatile receiver baud, registry preview/apply/backup,
  and signed OTA. Existing admin key stays in page memory. Public assets contain
  no site data; all management/data APIs require authentication.
- **Source quality:** four condition BIs per object report communication-failure
  and fault; fifth DataValid BI remains inactive. No labels or quiet input create
  a known normal condition. [PICS](docs/PICS.md) records actual services/limits.
- **Software verification:** 48 Python tests and four native ASan/UBSan tests pass,
  including exhaustive sanitized genuine-report splits, malformed/bounded
  reception, 2,048-record registry constraints, importer identity changes, OTA
  readiness/retention/hash gates, certificate pinning and handoff snapshots.
- **Actual field verification:** final 0.1.14 passed all 6,075 Object_List indices and
  26,715 selected property values across all 1,214 catalog records. Its actual
  HTTPS page/API test checked all directory records, TLS name/trust/time/leaf,
  nine unauthorized routes, and two nonmutating registry previews during the
  195.38-second BACnet run. Boot 31 remained confirmed beyond 180 seconds; no
  new receive errors or reboot occurred. UART payload during the tests was zero.
- **Browser verification:** synthetic desktop/mobile UI, key-memory handling,
  script-like text, UUID links and preview gating pass. Synthetic screenshots
  are labeled as fixtures; they are separate from actual P4 HTTPS tests.

Evidence: [Python](evidence/continuation-python-tests.txt),
[native](evidence/continuation-c-tests.txt),
[source inventory audit](evidence/continuation-inventory-native.txt),
[browser](evidence/embedded-ui-tests.txt),
[0.1.14 full BACnet](evidence/field-bacnet-all-0.1.14.json),
[0.1.14 HTTPS](evidence/field-web-0.1.14.json),
[later stability/backup read](evidence/field-stability-0.1.14.json).
The detailed [acceptance matrix](docs/TEST_MATRIX.csv) preserves unperformed
physical, current-state, Metasys and 24-hour tests as unperformed.

## Deployment failures and recovery

0.1.6 installed and imported the source registry, but concurrent full-catalog
work exposed a timeout/reboot. Registry validation was changed from quadratic
comparisons to sorted indices, bounded-stack merging and scheduler cooperation.
0.1.9 passed full catalog/BACnet and HTTPS checks after that change.

Candidates **0.1.7, 0.1.8, 0.1.10, 0.1.11 and 0.1.12 failed startup** and were
never confirmed. Automatic rollback restored Ethernet and the 1,214-object
registry. They are explicitly excluded from deployment/recovery. Old reset
observations reported PANIC; no serial console crash trace was available, so a
specific sorting, stack or SDK root cause is **not established**.

0.1.13 moved management availability before catalog loading, parsed into a
separate unpublished registry, published under the shared lock, exposed startup
stages, and completed initialization. It also uses an 8 KiB OTA reboot task.
0.1.14 removes the artificial diagnostic pauses. Both completed signed updates
and remote health confirmation with full registry retention and normal software
reset reports. Startup allows at most ten seconds for management availability
before proceeding without Ethernet; network-absent physical acceptance has not
been performed. Extended restart/traffic soak remains outstanding.

Failure records are in `evidence/field-update-*-failure.json`, with the original
0.1.6 load result in `evidence/field-load-0.1.6-failure.json`. Release hashes and
private binaries are retained; failures are not relabeled as acceptance passes.

## Source evidence and remaining boundary

Five historical genuine revision reports establish 9600 8N1 reception. They
identify panel 01, CPU 05.30.00, SDU 05.47.00, project 01.01.02 and database date
03/04/26. They are not automatic alarm/restore fixtures or complete state snapshots.
The newest imported archive hash is
`c8bd4dedb598fea590bd5167b6fcb692e74625cfb1d00e56bd1b71b275aa200b`;
revision metadata is consistent with it, but no full live program comparison exists.

The additional as-built folder was reviewed. Its SDUs duplicate the imported
source. Drawings support EST3/3-CPU3 hardware. The included reference manual is
for EST3X/SFS1-CPU; it does not supply the installed CPU 5.30 printer-event grammar.
The owner confirms no existing event log. See [as-built review](docs/AS_BUILT_REVIEW.md)
and [source coverage](docs/SOURCE_COVERAGE.md).

The 30 September readback found the first genuine local-trouble ACT/RST pair and
an inbound operator-command record on confirmed boot 31 after 37.34 hours uptime.
Raw bytes are private; [sanitized evidence](evidence/field-automatic-printer-2026-09-30.json)
records exact hashes and limits. This supersedes earlier statements that no
automatic events had yet arrived. It is not a complete 24-hour mixed-load test.

Remaining prerequisites are full routing and event/restore coverage, a validated
event decoder, and a supported way to establish conditions already active at boot.
The physically RX-only connection cannot request a snapshot. Keep naturally
arriving unknown bytes available for review; do not substitute another manual
Print request, synthesize live events, change wiring or guess ECP commands.
The temporary GET-only report collector detects overlapping windows, omitted
records and boot changes. It preserves private evidence for the next visit and
does not implement a host service or change firmware. Metasys tests, production
BACnet assignments, physical electrical acceptance,
full source recovery and a permitted 24-hour mixed-load soak remain outstanding.

## Access, recovery and continuation

Use the existing certificate and key as described in
[standalone operations](docs/STANDALONE_OPERATIONS.md). The legacy operations and
handoff material remain historical where superseded by this status and owner
scope. 0.1.5 can restore management with its old empty catalog; qualified data
uses `catalog_v2`, preserving legacy `catalog`. 0.1.9 is privately archived and
has passed full inventory transport tests, but the current confirmed release is
preferred. Never select a failed candidate or write the archived bootloader/
partition artifacts over the deployed controller.

The restored source is on `continuation/printer-pipeline`. The original supplied
bundle is unchanged; its missing SQLite sidecars were handled by a documented
narrow restore exception, and all 393 present files matched hashes. The bundler
now closes snapshots before hashing. [WORK_LOG.md](docs/WORK_LOG.md) records scope,
implementation and failures so continuation does not restart from old assumptions.

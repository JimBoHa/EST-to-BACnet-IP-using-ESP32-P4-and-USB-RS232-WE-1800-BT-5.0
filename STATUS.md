# Standalone P4: trouble observations deployed; full current-state polling unresolved

Updated 2026-10-03. **0.1.15 is installed and confirmed**, with automatic
LOCAL/COMMON TRBL ACT/RST observation decoding, embedded diagnostics and
1,214 qualified backup objects exposed through BACnet/IP. Last printed trouble
actions now map to existing BIs. **All current-condition quality remains
unverified.** A restore observation never marks a device reliably normal.

The latest pre-update capture contains eight trouble records from two matched
addresses: one power-supply pseudo point and one physical module. All eight
passed offline independent BACnet replay against the actual catalog. This is
separate from fresh event acceptance on the deployed decoder; no historical
records were injected into the P4. See [observation semantics and evidence](docs/PRINTER_TROUBLE_OBSERVATIONS.md).

Only ESP32-P4 and Metasys are permanent components. Recent raw lines, structured
observations and per-device last observations are bounded RAM data. No permanent
Mac, external history service or routine event flash writes are required.
Metasys commissioning remains deferred to the owner.

## Installed and retained state

| Item | Verified state |
|---|---|
| Application | `est3_gateway_rxonly` **0.1.15**, `ota_0`, confirmed boot **32** |
| Reset/startup | Software reset (`reset_reason=3`); `startup_phase=ready` |
| Running ELF SHA-256 | `7fb8820729402d0d73ccb28cc45cc3fabeb8da66ea6d9be285040d88a0510c68` |
| App-file SHA-256 | `67569d6ed82be3ea7f5295df93731e65f2644dd9a19815fd72e2bac5cfb90a47` — 991,472 bytes |
| Hardware | P4 revision 1.3; 32 MB flash/PSRAM; native EMAC/IP101; PoE; USB-C recovery unavailable |
| Receiver | FTDI 0403:6001; 9600 8N1, no flow; payload TX compiled out |
| Wiring | Last confirmed: yellow to TX2, black to COM2, orange disconnected. Owner offered orange to RX2; finished wiring confirmation pending. |
| Source registry | Epoch 1; 1,214 objects; 674 SENSOR/MODULE rows; current conditions unverified |
| BACnet | Device 3899000, Vendor 65535 (lab placeholders); **6,075 objects** |
| Management | `https://est3-device.local/`; current DHCP lease `192.168.75.157` |
| Retained OTA slot | Confirmed **0.1.14** on `ota_1` |
| Update boundary | Application only; deployed bootloader, partitions, credentials and eFuses preserved |

[Build manifest](evidence/build-manifest-0.1.15.json) and
[confirmed update](evidence/field-update-0.1.15.json) record distinct ELF and image
hashes. Images contain retained credentials and remain private. Never reprovision.

## Implementation and verification

- Strict revision metadata plus two captured trouble grammars. Incomplete,
  corrupt and unmatched records remain diagnostic evidence. Unknown addresses
  do not create catalog entries. Older/duplicate observations do not refresh a
  device; known report contexts inhibit observation mapping.
- Existing stable UUIDs, instances, binding epochs and tombstones retained.
  No support bit or synchronization is inferred from an event. Trouble values
  report communication-failure/fault; DataValid remains inactive.
- On-device page shows 32 recent structured trouble observations, 128 raw lines,
  decoder counters and last-observation source/time/age. No remote injection
  endpoint. Serial TX and generic simulation observer remain absent from ELF.
- Five ASan/UBSan native tests and 59 Python tests passed, including exhaustive
  frame splits/gaps, malformed input, report inhibition, replay, bounded memory,
  stable inventory and independent BACnet action/quality checks. Browser auth,
  text safety, observation rendering and mobile/stale behavior passed.
- All eight private captured ACT/RST records passed independent localhost
  BACnet reads against the actual 1,214-object registry. This validates captured
  syntax and address joins, not all-condition or current-state coverage.
- Signed 0.1.15 OTA confirmed with exact ELF hash, all 1,214 objects and registry
  epoch/source retained. Field BACnet read all 6,075 indexed objects and 26,715
  properties in 182.04 seconds; HTTPS checked all 1,214 directory rows, nine
  unauthorized routes and two nonmutating previews. Boot 32 remained confirmed
  beyond 180 seconds with no new receive errors. No new panel bytes arrived.

Evidence: [native/Python/browser](evidence/printer-observation-tests-0.1.15.json),
[private capture replay](evidence/printer-capture-replay-2026-10-03.json),
[full field BACnet](evidence/field-bacnet-all-0.1.15.json),
[field HTTPS](evidence/field-web-0.1.15.json).

## Wiring and polling boundary

Orange adapter TX to panel RX2 prepares a return path; yellow RX stays on TX2
and black on COM2. The owner authorized this preparation and offered to make
it. Actual completion has not yet been confirmed. This supersedes older blanket
instructions to leave orange disconnected, but does not enable firmware TX.

The unchanged source is producing printer-format records. There is no verified
printer-port command for configuration, a device list or current state. The
available ECP manual requires Gateway mode configured with 3-SDU, and lacks
complete wire messages needed for an independent implementation. User reports
panel access only. Polling therefore needs a compatible ECP specification or
licensed implementation and an SDU commissioning path; a third wire alone
cannot complete it. See [remaining source requirements](docs/PRINTER_TROUBLE_OBSERVATIONS.md#remaining-source-requirements).

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

Remaining prerequisites are all-condition/routing coverage, current-state recovery,
a supported polling protocol, and serial inventory discovery if available.
The 0.1.15 decoder covers the eight captured trouble observations only. Fresh
post-update events, production BACnet assignments, physical electrical acceptance,
Metasys commissioning and a permitted 24-hour mixed-load soak remain outstanding.
The older 1 October checklist is historical; its keep-orange-disconnected advice
is superseded by the owner's current wiring authorization above.

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

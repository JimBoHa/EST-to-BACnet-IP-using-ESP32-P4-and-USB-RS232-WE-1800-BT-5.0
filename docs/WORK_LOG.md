# Continuation work log

## 2026-09-29 — new workstation

- Restored commit `7a4a9e3c2f3c9de72cd2ba0eaf8f35ab8d92125a` and pinned BACnet submodule to the restored checkout; branch `continuation/printer-pipeline`.
- Original bundle verification stopped on absent SQLite sidecars. All 393 present files match the manifest; the absent WAL is explicitly zero bytes in the manifest. The matching main snapshot passes immutable read-only integrity checking. Restored with this narrow exception recorded in `private/restoration-exception.json`; original bundle unchanged. Fix the bundler's unclosed SQLite connection before the next transfer.
- Fresh Python 3.13 environment installed from the unchanged lockfile. Native pxlib rebuilt from supplied source.
- Exact TLS certificate plus trust/time validation passed from the routed workstation to the controller. Authenticated status: 0.1.5, matching full ELF hash, confirmed boot 13, 9600 8N1, no payload TX, 3,564 received bytes, zero receive/USB/UART drops/errors, zero real devices. Diagnostics outbox full; old host remains unreachable. Private evidence: `new-machine-status.json`.
- Independent BACnet discovery/RP/RPM passed: Device plus four health BIs. Private evidence: `new-machine-bacnet.json`.
- Reconstructed bundled 0.1.5 report bytes with offset continuity checks: 3,564 bytes; SHA-256 matches recorded source. No current-state semantics inferred from revision report.
- Initial clarification asked the owner for a permanent host and Metasys details; the replies below supersede those assumptions.

## Owner scope correction — 2026-09-29

The owner explicitly superseded the separate permanent-host/history design:
only the ESP32-P4 and existing Metasys server are permanent components. The P4
must serve its own configuration/diagnostics page and BACnet data. Long-term
recording on a separate host is not required. Keep only bounded recent receiver
observations in RAM; advertise eviction/reboot loss, not durable history.
The Mac is development/import tooling, not a production dependency. Disable
obsolete periodic host delivery without deleting its retained NVS data.

## Active work (updated to owner scope)

1. Loss-aware bounded raw reception and on-device parsing; explicit discontinuities.
2. On-device revision report metadata, recent unknown lines, qualified SDU inventory/import preview.
3. Embedded authenticated configuration/diagnostics/directory UI and commissioning worksheets.
4. Relevant automated checks, pinned firmware build, incremental signed OTA and field readback.
5. Live report/event semantics, native Metasys commissioning and 24-hour permitted soak require actual evidence; do not mark complete from software replay.

## Implementation and field verification

- Added the on-device portable revision parser, bounded recent RAM records and
  raw unknown-line diagnostics. No event/state observation reducer is linked.
- Imported the genuine March 2026 SDU backup through selected-field validation:
  1,214 OBJECT rows, 674 SENSOR/MODULE records. Applied epoch 1 and read back
  identical NVS content. Physical and logical/special scopes remain qualified.
- Added embedded HTTPS configuration/directory/diagnostics/update UI following
  the owner's 0BSD reference. Assets need no credential; all site data and
  management APIs require the existing key. Browser keeps the key in RAM.
- Disabled periodic host delivery and diagnostic journal writes; legacy data and
  registry key remain intact for old-firmware recovery. New registry uses
  catalog_v2. No permanent host process is installed.
- Fixed transfer snapshot sidecars by closing SQLite connections before hashing.
- Initial 0.1.6 signed OTA and 333-property independent BACnet sample passed.
  Concurrent full enumeration/registry preview then timed out and rebooted twice;
  Ethernet and all imported identities recovered. Failure evidence is retained.
- Removed quadratic registry comparisons and added 2,048-record identity tests.
  0.1.7 and 0.1.8 failed startup and rolled back automatically; neither was
  confirmed. No console was available to establish their exact reset cause.
- Iterative bounded-stack index sorting in 0.1.9 booted successfully (boot 21),
  with complete registry retention. All 6,075 indexed objects and 26,715 selected
  property values passed across 1,214 records; actual HTTPS/preview/directory
  checks also passed. No source UART payload was observed during those tests.
- Newly exposed reset_reason reported PANIC after earlier updates. 0.1.10 moved
  reboot onto the main task; 0.1.11 enlarged the event task and exposed stack
  location; 0.1.12 restored the earlier path with a larger reboot task. All failed
  early startup and rolled back to 0.1.9 with all identities retained. An identical
  0.1.11 retry failed too. Without a console trace, none establishes a root cause.
- 0.1.13 brought management up before loading the catalog, parsed into a separate
  registry, published it under the shared lock, and exposed spaced startup stages.
  Every stage completed; boot 30 was confirmed with all 1,214 entries and normal
  software reset reason 3. 0.1.14 removed artificial stage pauses and also booted
  and confirmed successfully (boot 31, reason 3). The 8 KiB reboot task remains.
- Added OTA client rejection of recovered old images and readiness/retention gates.
  Ten added tests bring the Python suite to 48 passing tests; four native
  ASan/UBSan tests pass. Failed candidate archives are marked not for deployment.
- Owner supplied the as-built folder and confirmed no existing automatic event
  log. All three SDUs duplicate the handoff archives. Relevant drawing/manual
  pages were inspected; EST3X material cannot establish installed EST3 CPU 5.30
  wire semantics or automatic startup recovery. See AS_BUILT_REVIEW.md.

No new panel UART payload has arrived during this continuation. Five historical
revision reports remain the only live syntax evidence. Automatic events and
startup state recovery remain outstanding; do not ask the owner to press Print
as a substitute for unattended operation. Existing event logs or version-matched
printer documentation were requested while implementation continued.

## Final scoped verification — 2026-09-29 UTC

- Confirmed 0.1.14 remained on boot 31 through all 6,075 Object_List indices and
  26,715 property values across every source object (195.38 seconds). Every
  condition retained fault quality and every DataValid point remained inactive.
- Concurrent actual HTTPS checks passed TLS name/trust/time/exact-leaf validation,
  source asset comparison, nine unauthenticated route rejections, all 1,214
  paginated directory records, UUID search and two next-epoch previews. Previews
  took about 2.1 seconds each and did not change the stored registry.
- No new UART payload, receive errors, reboot, diagnostic outbox counter change,
  panel command or Metasys write was observed/performed. This is transport and
  metadata verification; automatic panel conditions remain a source-evidence gap.
- The actual final image, debug ELF/map, private registry, source catalog and
  credentials remain local. Public source/evidence exclude raw site files and keys.

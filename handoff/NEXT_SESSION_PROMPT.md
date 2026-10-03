# Continue from deployed standalone 0.1.15

Updated 2026-10-03. Use the existing checkout, not the older Desktop bundle.
Read [STATUS](../STATUS.md), [observation semantics](../docs/PRINTER_TROUBLE_OBSERVATIONS.md),
[coverage](../docs/SOURCE_COVERAGE.md) and [work log](../docs/WORK_LOG.md).

## Owner scope and authorization

Target: all reliably obtainable fire-device information over BACnet/IP, ideally
including inventory pulled over serial. Only P4 and Metasys are permanent. P4
hosts HTTPS diagnostics/configuration; no permanent Mac or long-term recorder.
Owner handles Metasys acceptance after reliable source data works. Independent
BACnet testing, source edits, relevant tests, signed application-only Ethernet
OTA and commits/pushes are authorized. Do the work without repeated approval.
No USB-C recovery: preserve management, NVS, credentials, partitions and rollback.
Never run provisioning or publish private credentials, images, catalogs or raw data.

Latest owner offered to connect orange. Supplied preparation: **orange adapter
TX → labeled panel RX2; yellow RX stays on TX2; black stays on COM2; unused leads
separately insulated, especially red power.** This supersedes older blanket
keep-orange-disconnected instructions. Last explicit wiring confirmation still
had orange disconnected and settings unchanged. Finished-wiring confirmation is
pending. Do not assume it happened; firmware TX remains compiled out.

No verified printer-port query or complete ECP wire specification exists here.
No guessed probes, panel controls/programming, staged alarms or live fuzzing.
Documented ECP requires 3-SDU Gateway-mode commissioning. Owner previously had
panel access only, without an SDU computer or technician. A wire cannot promise
configuration discovery or one final site visit. Use genuinely new source
information if available; avoid repeating broad searches for the same manual.

## Current deployment

- Checkout `/Users/InfrastructureDashboard/est3-metasys-gateway`; branch
  `continuation/printer-pipeline`; origin
  `https://github.com/JimBoHa/EST-to-BACnet-IP-using-ESP32-P4-and-USB-RS232-WE-1800-BT-5.0.git`.
- P4 rev 1.3, 32 MB flash/PSRAM, native EMAC/IP101, PoE. FTDI 0403:6001,
  USB-RS232-WE-1800-BT-5.0, 9600 8N1/no flow. Preserve explicit FTDI request 2
  flow and request 1 masks 0x0100/0x0200; status bytes stripped exactly once.
- Confirmed **0.1.15**, `ota_0`, boot **32**, normal software reset, ready.
  ELF `7fb8820729402d0d73ccb28cc45cc3fabeb8da66ea6d9be285040d88a0510c68`.
  Binary `67569d6ed82be3ea7f5295df93731e65f2644dd9a19815fd72e2bac5cfb90a47`,
  991,472 bytes. Retained confirmed **0.1.14** on `ota_1`.
- Lease `192.168.75.157`; HTTPS `est3-device.local`; MAC `e8:f6:0a:e4:1f:e8`.
  Mac used `192.168.75.191` for latest BACnet test. Recheck route/lease if needed.
  Existing `private/tokens.json`, certificate and signing key remain. Client
  checks TLS trust/time and exact leaf before token; never bypass verification.
- Registry epoch 1: 1,214 OBJECT rows, 361 SENSOR + 313 MODULE. Device 3899000 /
  Vendor 65535 are lab assignments. Device + four health + five per object =
  6,075 objects. All current-condition quality invalid.
- Archive SHA `c8bd4dedb598fea590bd5167b6fcb692e74625cfb1d00e56bd1b71b275aa200b`.
  `private/site-20260304-v2-catalog.json` and `private/site-20260304-v2-registry.json`.

## Implemented path and evidence

`printer_event.c` accepts captured LOCAL/COMMON TRBL ACT/RST with strict
blank/header/text/blank framing, valid calendar, five-second frame limit, report
inhibition and gap/corruption handling. `printer_observer` joins exact qualified
addresses. Duplicate/older records do not refresh observations. Events do not
create/retire/rebind inventory or infer missing condition states.

`gw_record_printer_trouble` leaves support/synchronization unset. Existing trouble
BI carries the last printed action while Reliability remains communication-failure,
Status_Flags.fault remains set and DataValid remains inactive. RST is not complete
normal state. Alarm/supervisory/disabled stay unknown. Generic `gw_observe` and
serial payload TX remain absent from production ELF; no injection endpoint.

Web page exposes 32 structured observations plus 128 raw lines and per-device
source/time/age metadata. All observations are bounded RAM and reset at reboot.
Registry/boot accounting remain persistent; `catalog_v2` preserves legacy `catalog`.
Old telemetry data remain for recovery; periodic delivery/diagnostic writes disabled.

Private pre-OTA boot-31 snapshots in `private/communication-20261003/` show 869
UART bytes counted and 38 retained lines: eight trouble records, one battery
pseudo-point pair and three physical-module pairs. No receive drops/USB/UART
errors. The 512-byte tail is not a full 869-byte raw capture. All structured
records were saved before OTA; public fixtures change addresses/labels/dates.

All eight private records passed offline production C parser/reducer/stack replay
against the actual catalog plus independent BACpypes3 reads. CRLF was reconstructed
from retained lines. No historical bytes were injected into the P4. This is not
fresh post-update event acceptance.

0.1.15 field BACnet read every Object_List index (6,075) and 26,715 properties in
182.04 seconds. HTTPS checked 1,214 rows, exact assets, nine unauthorized routes
and two nonmutating previews. Confirmed past rollback window; no reboot/errors.
**Zero fresh UART bytes arrived during these tests.** Source acceptance remains
pending. Five ASan/UBSan and 59 Python tests pass. Synthetic browser checks pass
with explicit installed Chromium shell 1243 (default 1234 missing).

## Next useful work

1. Read bounded private snapshots for naturally arriving records; temporary
   GET-only `tools/capture_printer.py` is available. Compare fresh mapped ACT/RST
   with independent BACnet. Do not use manual Print or old replay as fresh proof.
2. Obtain CPU-compatible ECP wire specification/licensed implementation and an
   SDU commissioning path. The MSA manual documents wiring/services but not full
   serialized read/handshake frames. Validate those on an isolated peer before
   field TX, and confirm wiring before transmitting. Treat device-list/label
   discovery separately from point-status polling; neither is established here.
3. Extend only verified formats. Full routing, all-condition coverage, silent
   devices, boot/loss current-state recovery and program synchronization remain
   unresolved. Maintain honest quality and retain unknown records.
4. Keep exact evidence/version/hash records. Metasys, physical electrical and
   24-hour mixed-load acceptance remain unperformed. Never claim complete device
   monitoring simply because all BACnet objects exist.

Use pinned ESP-IDF v5.5.5 and explicit
`IDF_TOOLS_PATH=/Users/InfrastructureDashboard/est3-toolchains/idf5.5.5`.
Never overwrite a release with different bytes. Failed 0.1.7/8/10/11/12 must not
be deployed. Preserve management-before-catalog startup, separate parse and locked
publication, bounded ten-second network wait and 8 KiB reboot task.

# Source coverage and the standalone controller

The owner's 2026-09-29 instructions supersede the earlier permanent-host design.
The ESP32-P4 serves its own HTTPS directory/configuration/diagnostics and read-only
BACnet/IP. Metasys owns long-term trending and the owner will commission Metasys
after automatic panel data is reliable. `host/` remains optional offline/test
software, not a production dependency. Old host delivery is disabled.

The added as-built material was reviewed in [AS_BUILT_REVIEW.md](AS_BUILT_REVIEW.md).
Its SDU files duplicate the imported source; the EST3X manual does not establish
the installed EST3 CPU 5.30 event format. The owner has no existing event log.

The machine-readable companion is [SOURCE_COVERAGE.csv](SOURCE_COVERAGE.csv).
Status applies to the specific claim, not to the whole product.

| Information | Evidence and current representation | Limitation |
|---|---|---|
| Serial reception | Five genuine revision reports at 9600 8N1; USB status stripped exactly once | Does not prove automatic event coverage or physical TX measurements |
| Panel/card revision metadata | Portable C parser replays the sanitized genuine syntax, including all split boundaries; same parser linked on P4 | This firmware's live receive path needs naturally arriving bytes; no manual print dependence is claimed |
| Inventory | 1,214 OBJECT records, including 361 SENSOR + 313 MODULE records; unique panel/LRM/device keys; physical/type/LRM joins checked | Backup metadata, not a full live program comparison |
| Extra SDU objects | Retained as catalog metadata; 7 scope-0 and 198 scope-255 objects explicitly unresolved | These special cabinet codes are not asserted to be physical panel addresses |
| Labels/type codes | Scalar source labels and raw model/type codes preserved; immutable UUIDs and BI instance reservations | Human message blobs and detailed type/condition meanings are not decoded |
| Relationships | 42 LRM, 349 LOGICDEV and 25 SIGNATUREGROUPS rows preserved in private source catalog | Not asserted to be live output states or graphic coordinates |
| Automatic event output | Actual 30 September capture: one local-trouble ACT/RST pair and one inbound operator command; 317 bytes without reported errors/drops; pseudo-point address joins the backup | Establishes this observed event path only; alarm/supervisory/disabled formats and complete routing remain unverified |
| Current alarm/trouble/supervisory/disabled | Reserved per-object BIs show fault quality; DataValid inactive; page says unverified | No initial snapshot or validated automatic event decoder. Inventory never sets normal |
| Current-state recovery | Boot/loss cannot establish state; no known state is created | Physically RX-only interface cannot request a snapshot. Autonomous recovery is not demonstrated |
| Unknown input | Authenticated recent RAM records retain raw bytes, offsets, receive uptime, epoch and parse status | 128 × up to 512-byte records; eviction count visible; clears on reboot |
| Analog/dirty/sensitivity/security/monitor values | Some backup fields exist but are configuration/archival candidates | No verified live measurements; no fabricated analog BACnet values |
| Program changes | Source catalog import diff and stable identities implemented | No verified automatic rename/inventory export signal; owner must supply a new authorized export |
| Gateway health | USB/payload/error/drop counts, heap, uptime, boot, registry, source quality, HTTPS and BACnet | USB status packets and silence never refresh detector quality |

## Automatic operation boundary

Edwards' [270382-EN R012 operation manual](https://alarmspec.com/wp-content/uploads/2025/12/270382-EN-R012-EST3-System-Operation-Manual.pdf),
printed pages 62–64, describes event/restoration printing. That establishes a
candidate automatic source, not the installed port's routing or wire grammar.
The manual's firmware scope differs from the installed 5.30 CPU. The 30 September
capture adds genuine local-trouble activation/restore syntax and an operator
command record to the five earlier revision reports. The complete 317-byte tail
and structured offsets agree; the address matches one backup power-supply pseudo
point. No detector/module event, complete routing or current-state coverage is
inferred. Port filter enum 1919 has not been independently decoded. No panel
settings or wiring were changed. See [port review](PORT_CONFIGURATION_REVIEW.md).

Automatic changes are different from an authoritative current-state snapshot.
At boot, an RX-only event stream can miss previously active conditions. Silence
cannot resolve that. Full unattended current-state recovery requires a verified
source snapshot mechanism or a supported integration capable of read-only polling.
This is a concrete interface/evidence gap, not a missing history server.

No raw serial write, panel reset/acknowledge/silence/disable, synthetic live event,
ECP handshake or guessed state decoder is provided. The current release exposes
the available metadata and observations while keeping all condition quality
unverified. Metasys acceptance is deferred at the owner's request.

## Parser and memory policy

USB callback only copies tagged chunks to a bounded 128 × 64-byte payload queue.
Consumer owns the portable parser; HTTP takes a mutex-protected copy and then
serializes outside that mutex. Chunks include 64-bit byte offsets, receive
uptime, stream epoch and corruption flags. Gaps/reconfiguration/error epochs
invalidate incomplete reports. Queue overflow is visible in drop counts and
offset discontinuities. Disconnect no longer silently resets the queue.

Line fragments are capped at 512 bytes; longer records remain raw fragments.
Unknown/interleaved/corrupt report lines prevent a complete validated report.
The latest complete revision report is metadata, with its original timestamp;
`historical_alarm_count` never updates any alarm BI. All parsing occurs on P4.
No serial observer is exposed as an injection endpoint.

Recent records use RAM only. At the 9600 8N1 theoretical maximum of 960 bytes/s,
64 KiB is at most roughly 68 seconds of payload; short-line record counts can
evict sooner. This is an inspection buffer, not an outage/history budget.
No routine receive or diagnostic records are written to flash. Registry changes
and existing boot accounting remain persistent. Metasys retention is separate.

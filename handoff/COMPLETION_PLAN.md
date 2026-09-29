# Implementation and acceptance plan

Use this as an executable work queue, not a substitute for implementation. Read the current code and original specification before changing contracts. Add evidence as each capability is demonstrated. Existing field facts and boundaries are in `NEXT_SESSION_PROMPT.md`.

## 1. Establish the new workspace and trustworthy access

Restore the private bundle, check both Git commits and all file hashes, and create fresh Python/ESP-IDF environments. Preserve credentials; authenticate separately to GitHub on the new machine if pushing. Confirm a route to the controller, exact certificate identity, version/hash, confirmed boot, 9600 8N1, USB attachment and disabled payload TX. Record UTC, boot/session identifiers, counters and the actual workstation IP. Do not scan unrelated networks.

If the route is unavailable, continue with bundled source, reports, SDU data and offline tests. Give the owner the precise routing/VPN/site input needed; do not reflash, reset, weaken TLS or declare the device broken. The bundle may record a more recent failed connection attempt in addition to the last successful field test.

Inspect the actual device count and preserve the current registry if later work has populated it. At this handoff's last verified state the gateway had zero real devices, and the supplied SQLite snapshot held diagnostics. Do not assume this remains true after another session works on it.

Acceptance: reproducible checkout with matching keys, read-only device access from the new machine or a precise network blocker, and a new-machine status record without secrets/raw site data in public evidence.

## 2. Build a capability and coverage inventory

Create `docs/SOURCE_COVERAGE.md` and a machine-readable matrix. For each field/condition record its source, extraction method, evidence, completeness, freshness, clear/restore meaning, startup recovery, applicable device types and downstream representation. Distinguish `VERIFIED`, `IMPLEMENTED_FIXTURE_ONLY`, `NOT_YET_VERIFIED`, `SOURCE_UNAVAILABLE` and `NOT_APPLICABLE`. Unavailability needs a reason and, where possible, a supported alternative.

Investigate the following as candidates, not promised printer features:

| Information | Candidate source and required proof |
|---|---|
| Panel/node/card identity, firmware, database revision | Captured revision reports; validate multi-panel/card boundaries |
| Complete devices, labels, addresses, type and configured relationships | Genuine SDU/project tables or supported export; include devices that never alarmed |
| Alarm, restore, trouble, supervisory, disabled/enabled observations | Verified live/recorded printer events and documented report semantics |
| Monitor/security/test/prealarm/maintenance/dirty or sensitivity data | Only if present for installed hardware, enabled configuration and supported reports |
| System power, ground, battery, network, card/loop and communications faults | Actual raw event/report examples with correct scope; do not invent per-detector associations |
| Current active conditions and reset/startup recovery | Documented status snapshot/report with explicit completeness and interleaving behavior |
| Event history and chronology | Read-only history reports; preserve original time and reception order, detect omissions/wrap |
| Groups, zones, logical mappings and notification/control modules | SDU and supported reports; distinguish configured function from measured output state |
| Program-change detection and automatic refresh | Verified revision/change signal plus a reliable inventory/text source |
| Analog values or proprietary diagnostics | Separate evidence required; expose unsupported if interface does not provide them |
| Gateway health and data quality | USB/link errors, buffer loss, parser errors, source age, host backlog, clock and storage health |

Preserve every unrecognized complete line/frame as an observable raw record with a parse status and bounded storage policy. Unknown codes must be searchable, not silently discarded. A source document describing an optional feature does not prove that feature exists on this site.

## 3. Replace diagnostic-tail polling with a real receive pipeline

`serial_rx.c:consumer` currently computes CRC only. Design a bounded path for raw receive chunks into parsing and durable delivery, without blocking the USB task on HTTPS, disk or slow parsing. Keep FTDI status stripping exactly once. Track disconnect/reconfiguration/reboot epochs, byte offsets, line errors and queue loss. Drop or invalidate partial records at discontinuities; emit explicit gaps.

The 512-byte authenticated capture tail is useful for diagnostics, not production event capture. At 9600 8N1 the maximum ideal wire rate is approximately 960 bytes/s; size buffers and outage budgets against measured bursts and real requirements. Account for repeated reports, long labels, CRLF/LF variations, non-ASCII bytes, partial lines and report boundaries. Do not assume a larger RAM ring makes history durable.

Choose and document the split between firmware parsing/state and host parsing/history. The original requirement is for gateway BACnet objects to continue during host outages. A host-only decoder requires a supported recovery/state-delivery design and must not masquerade as independent gateway monitoring. Avoid two conflicting authorities for device state.

Acceptance: loss-aware raw capture, bounded memory under continuous source traffic, observed backpressure/overflow behavior, retained raw evidence and no serial transmit path. Meaningful tests should split fixtures at all relevant boundaries and verify output equivalence, reconnect/gap behavior and memory limits.

## 4. Implement a verified printer/report decoder first

Use the supplied clean 9600 reports as real fixtures. They prove revision-report syntax only. Retain their original bytes privately and derive sanitized structural fixtures for Git without changing semantics. The corrupted 19200 capture is a negative fixture, never a valid protocol example.

Start with report envelopes, panel/card identity, database metadata and complete/incomplete markers. Handle multiple reports in one capture, duplicates and interleaved asynchronous lines. Then obtain suitable read-only history/current-status reports and passively observe normal traffic to establish actual event and restore syntax. Use the manufacturer manual and installed CPU version. The owner may request documented read-only reports; do not generate alarm/disable/reset conditions on the live panel to manufacture parser data.

Define a real source profile such as an explicitly versioned EST3 printer profile. A parser must not mark its input as ECP or SIMULATION_ONLY. Separate parser recognition, device resolution and state transition acceptance. Preserve raw text/code, original labels, panel time, receive UTC/monotonic time, source/boot/stream identity and confidence/quality. Reject malformed/truncated records without inventing state.

Future ECP is an optional capability investigation if a specific necessary field cannot be obtained through the supported printer/export workflow. Consult the exact supported integration and protocol documentation before proposing any bidirectional change. Keep the current RX-only configuration working throughout.

Acceptance: replay of real sanitized fixtures plus truncation, split, concatenation, long/unknown text, duplicate, corruption and report-interleaving tests; no crash, fabricated normal state, hidden loss or operational-command handling.

## 5. Build a genuine SDU inventory importer

Use copies under `site-inputs/sdu/`; never modify originals or download a project into the panel. Inspect selected schemas and validate active record counts rather than treating unused Paradox slots as live rows. The local review includes selected cabinet/LRM fields and archive hashes; it is not a complete importer. The previous pypxlib iterator did not work correctly on that environment; bounded indexed reads worked. Empty ECP tables should not be interpreted from stale block contents.

Determine which tables encode physical devices, labels, logical addressing, types, groups, relationships, retirement and revision metadata. Establish panel/card/loop/address normalization against report data and drawings. Preserve original codes when meanings are unverified. Validate maximum counts, duplicate identities/addresses, unexpected schema versions, incomplete/truncated archives and ambiguous address reuse. Do not read/dump credential-bearing fields unnecessarily.

Extend `host/models.py` with a versioned real inventory contract and source provenance/completeness evidence. Preserve the existing SIMULATION_ONLY path for tests. Produce a preview showing additions, renames, retirements, type/binding changes and unresolved decisions before committing catalog changes. Maintain stable UUIDs, immutable BACnet instances, tombstones and historical label snapshots. Ordinary label changes must not allocate new objects; unrelated reuse of an address must not inherit an old device's history silently.

Compare newest backup metadata with the installed report. Matching date/version is useful evidence but not a full live content comparison. Distinguish inventory completeness from confidence that a backup is the currently installed revision. Do not retire devices from a partial/stale archive.

Acceptance: independently counted real catalog including normal never-alarmed devices, schema/provenance checks, supported address mapping, safe reconciliation/migration/restart tests and explicit unresolved source fields. Publish sanitized summaries, not raw site inventory or credentials.

## 6. Establish current state, recovery and freshness

Prove alarm/trouble/supervisory/disabled independence and appropriate system-level conditions. Do not clear trouble because an alarm restored; do not clear every point because the panel resets, goes quiet or reports a heartbeat. Define supported/unsupported conditions per device type. An inventory provides metadata, not current condition truth.

Determine how the source supplies an authoritative current snapshot, if it does. A status report limited to active points can imply normal for missing points only when scope, completeness and every relevant condition are established. Treat event history as historical observations, not necessarily current state. Reconcile snapshot boundaries with events arriving during reports; use sequence/receive order and epochs to prevent older snapshots overwriting newer transitions.

On boot, source loss, error/gap or uncertain program change, preserve last values but mark affected conditions unknown/stale and require an established resynchronization path. Current 60-second stale logic is a prototype; choose source-appropriate measured deadlines. Event-only protocols cannot prove per-condition freshness merely from a quiet serial stream. If the installed printer interface cannot provide automatic complete recovery, expose that limitation and a concrete manual report/export or supported integration path.

The host has to invalidate conditions on gateway/source restart consistently with firmware. Preserve raw panel timestamps and separate receive UTC/time quality; avoid reordering on a guessed one-hour offset. Establish clock recovery, daylight saving, invalid dates and delayed history semantics without setting panel time.

Acceptance: real-source replay covering concurrent conditions, independent restore, duplicate/delayed input, startup during an active condition, report/event overlap, restart, clock loss/change, gap/resync and stale quality in both BACnet and host UI.

## 7. Deliver actual events durably to a permanent host

Choose the always-on host/VM and operating system with the owner; a developer laptop is not a permanent deployment by default. Set a stable address/DNS, service account, restricted routes/firewall, storage/retention budget, backups and service supervision. Use the retained TLS identity initially so the device continues to trust the host. Keep certificate trust and expiry validation; implement planned renewal/rotation before expiration. NTP/time unavailability must be visible rather than disabling validation.

Back up SQLite using its backup API. The supplied `hardware-bench.sqlite` is a consistent snapshot, not a raw copy of a WAL database. Keep simulation databases separate. Do not run two competing writers/services with the same identity or assume the old host process moved with the files.

Before changing the gateway URL, start and verify the host at its actual bind address with the supplied cert/key and expected gateway identity `P4-e8f60ae41fe8`. Then use the authenticated `/api/v1/host` configuration route. The firmware expects HTTPS, the exact `/api/v1/telemetry` path and certificate common name `est3-host.local`, even when connecting to a numeric address. Extend the real-event schema/version before attempting panel event upload; current diagnostics will still use protocol_disabled.

Design bounded durable event batches, ACK/retry/deduplication, stream/boot identity, gap records and safe schema migration. Distinguish historical replay from current state. Measure storage writes/endurance, queue capacity in bytes/time and behavior after uncertain delivery. A missing ACK must not erase undelivered events; a full queue must not conceal loss.

Acceptance: actual panel-derived records persist and survive host/gateway restarts, disconnected-host backlogs replay within stated budgets, explicit gaps appear beyond capacity, no double application occurs, backup restore is verified in isolation, and BACnet behavior remains correct during a host outage.

## 8. Complete read-only BACnet representation

Validate an assigned vendor identity and unique site Device instance rather than using 65535/3899000 as silent production defaults. Keep stable per-device object identifiers and the registry as the authority. Expose current supported conditions with valid/fault/reliability semantics; unsupported, retired, stale and unknown must remain distinguishable. Preserve last known values with invalid quality when required, so an active alarm is not silently cleared by a communication outage.

Add extra status/analog/text objects only for proven source values and after capacity/service compatibility checks. Calculate actual object counts, name/description limits, APDU/RPM boundaries, polling load and memory usage. COV may be implemented if useful and bounded; otherwise accurately advertise polling. A routed BACnet deployment may require site BBMD/FDR or other supported arrangements; directed broadcast discovery is not guaranteed across the owner's routers.

Revisit the release symbol audit when linking a real observation path. It must distinguish validated production parsing from simulation-only injection without weakening the serial TX guard. Preserve no WriteProperty, DCC, reset, create/delete or BACnet-to-panel control routes.

Acceptance: independent client reads/discovery/quality tests on the actual firmware, representative catalog size on hardware, unsupported-service rejection, stable objects across OTA/reboot/rename and no control route to EST. Do not rerun disruptive bench cases on the live panel without an appropriate test setup.

## 9. Complete the companion interface

Expose all catalog devices, including those with no events. Provide search/filtering by label, address, type, location, condition and time; per-device stable URLs; raw/normalized history; current versus historical labels; source quality/last observation; unrecognized events; inventory revision/age and unresolved mappings. Make communication loss and history gaps prominent. Distinguish active conditions from historical events.

Render source text safely with size limits and raw preservation. Maintain authenticated viewer/manager/gateway roles, TLS and safe exports. Add appropriate pagination, time-zone handling and retention controls. Remove stale hard-coded UI/protocol-disabled claims only as the corresponding implementation is actually enabled; do not replace them with a misleading global "healthy" flag.

Acceptance: working real-data UI with meaningful filters, stable links after renames, correct quality/retirement/gap rendering, role isolation, injection/Unicode/long-label handling and measured performance on the real inventory/history scale.

## 10. Commission Metasys against the installed system

Obtain the actual server/engine/API/UI releases, license/role scope, integration parent, supported mapper types/schemas, point capacity and designated engineering/test area. Read current configuration first and preserve unmanaged relationships. No Metasys access was established in the previous session.

Use supported native BACnet point engineering and actual API contracts. Keep dry-run change reports idempotent and reviewable before applying site changes. A generic BACnet CreateObject call is not local Metasys mapper creation. If supported automation is unavailable, provide exact actionable engineering/import worksheets and demonstrate that workflow; do not claim unattended sync.

Map representative detector and pull-station conditions/quality, system-level faults and source-supported extra points. Configure appropriate local alarm routing/priority/restore behavior; BAS acknowledgement must not acknowledge or silence the EST panel. Prove runtime quality and simultaneous independent conditions on the native interface.

Bind individual symbols to native floor plans using supplied location/coordinate data. Preserve bindings on renames and appropriate replacements. New/moved devices without verified coordinates must be visibly unplaced. Establish supported navigation/authentication for host event/device pages; do not assume iframes are permitted.

Acceptance: installed-site point/quality/alarm/graphics examples, capacity margin, repeatable idempotent reconciliation/recovery after partial failure, stable labels and links, dependency-safe retirement and an explicit supported automation/manual boundary.

## 11. Prove change synchronization

Implement revision/change detection only from a verified source. If a fresh contractor export is necessary, provide an authenticated import/watch workflow with provenance, completeness and revision checks. A watched folder does not create files that the panel cannot export automatically. An event-only stream cannot detect a rename of a quiet normal device without another source.

Demonstrate add, rename, normal never-alarmed device, replacement, ambiguous address reuse, retirement and partial/stale export handling end to end through inventory, gateway, host and Metasys. Keep metadata freshness separate from condition freshness. Preserve native graphic/equipment/history relationships. Explicitly retain manual placement/approval work where the downstream product requires it.

Acceptance: one real authorized contractor-change/export workflow and the relevant fault/retry tests. Publish the precise automation boundary and remaining manual steps.

## 12. Finish physical validation and operational acceptance

Reconcile every applicable row in `docs/TEST_MATRIX.csv` with current evidence; keep the original detailed requirements in `original-spec/TEST_MATRIX.csv`. Add printer-profile rows rather than forcing printer results into ECP tests. Current report reception and post-OTA 9600 behavior are real passes. Independent electrical measurements, all-byte RS232 peer tests, long-duration throughput/overflow, hotplug during traffic, power/brownout and zero-TX capture remain separate unperformed tests.

Perform electrical/disruptive tests on an isolated bench or a specifically coordinated site plan. The user currently has no second RS232 adapter/tester and cannot return the installed unit to USB for troubleshooting; identify required equipment without blocking independent development. Do not unplug panel wires, short a loopback, disable points, generate alarms or reboot the panel simply to improve test coverage.

Run at least a 24-hour permitted mixed-load soak using real/approved traffic and measured bounds for latency, heap, reset count, storage growth, event completeness and reconnection/replay. Complete backup/isolated restore, known-good OTA recovery, permanent-host restart and credential/certificate management exercises. Compare representative actual panel observations to native BACnet, host history and Metasys with responsible site owners.

Final deliverables: current source and versioned recovery images privately archived; complete capability/coverage matrix; actual tests and limits; deployment/service configuration; device/IP/BACnet assignments; field wiring and enclosure/strain-relief record; inventory/identity policy; retention and time/quality behavior; Metasys reconciliation/placement workflow; owner runbook; backups with restore proof; and exact unavoidable site inputs or source-unavailable features. A printed report alone is never the completion criterion.

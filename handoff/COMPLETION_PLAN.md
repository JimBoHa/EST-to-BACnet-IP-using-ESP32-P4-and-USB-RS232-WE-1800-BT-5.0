# Remaining standalone acceptance work

Read `NEXT_SESSION_PROMPT.md` and repository `STATUS.md` first. The owner replaced
the permanent host/history design with P4-hosted configuration/diagnostics and
Metasys trending, and deferred Metasys commissioning until automatic panel data
is reliable. Do not reintroduce those old dependencies.

## Completed in this continuation

- Restore, pinned toolchain and authenticated field access using existing trust.
- On-device revision metadata parser and bounded, loss-aware recent RAM records.
- Qualified SDU import, 1,214 catalog objects, persistent UUIDs/BI instances and
  explicit unresolved scopes; no normal-state inference.
- Embedded HTTPS page and API for status/search/diagnostics/configuration/registry
  preview/backup and signed OTA, based on the owner's reference UI.
- Disabled periodic external delivery and diagnostic flash writes, preserving
  legacy bytes and rollback-compatible registry storage.
- 0.1.14 installed/confirmed with retained registry; full actual BACnet and HTTPS
  checks, 48 Python tests, four native sanitizer tests and synthetic browser checks.
- Reviewed added as-built material and documented source coverage/limitations.

## Next dependency: automatic source and recovery

On 30 September the P4 yielded a complete 317-byte capture containing one real
local-trouble ACT/RST pair and an inbound operator-command record, with no reported
errors/drops. The event address joins one backup power-supply pseudo point. This
establishes scoped automatic printer reception, not every event class or complete
current state. Production decoding remains revision-only. See
`docs/PORT_CONFIGURATION_REVIEW.md` and `docs/SITE_VISIT_CHECKLIST.md`.

The owner has panel-only access for the planned 1 October visit, without 3-SDU or
a technician. Complete physical photos and scoped Status/History capture in one
session, verifying artifacts before leaving. The temporary capture helper makes
GET requests only. No manual report is a substitute for autonomous monitoring.
Complete ECP commissioning cannot be guaranteed without programming access and
the exact supported protocol.

Required proof:

1. Installed automatic output/routing and exact record boundaries, identity,
   condition, assertion/restore and timestamp meanings.
2. Explicit completeness and ordering for initial state and post-loss recovery.
   RX-only event listening cannot recover already-active conditions by silence.
3. Physical/logical/system event mapping that does not force every record into
   a detector condition. Preserve unknown bytes and unresolved source scopes.
4. Byte-boundary, truncation/corruption, interleaving, duplicate/loss, multiple
   simultaneous conditions and restart tests using authorized real fixtures.
5. Deliberate production decoder/symbol-audit update; all unsupported conditions
   remain invalid. No speculative ECP or payload transmit path.

A supported polling interface, if needed, requires exact version-matched
read-only documentation and a separately coordinated wiring/configuration plan.
Do not add TX, modify the panel or ask for another manual print as a substitute
for autonomous monitoring.

## Acceptance after the source exists

- Compare source-supported objects/current states with the installed system;
  backup consistency alone is not a complete live program comparison.
- Verify state and quality over independent BACnet/IP during startup, source
  loss, restore, catalog changes and a permitted mixed-load soak of at least
  24 hours. Do not relabel existing short idle-source tests as this acceptance.
- Obtain production BACnet identities and validate network/point capacity.
- Owner performs Metasys integration once source data is reliable. Any later
  automation/graphics work needs actual installed schemas, permissions and
  coordinate mapping; existing Metasys code remains dry-run.
- Preserve electrical/TX capture, controlled outage and isolated replacement
  restore tests as unperformed until appropriate bench/site access exists.

Keep `docs/TEST_MATRIX.csv`, coverage and `docs/WORK_LOG.md` current. The failed
startup candidates remain excluded from recovery; use the confirmed release in
STATUS.md and preserve the private images/keys/source catalogs. No destructive
recovery experiment is authorized on the attached panel.

# Standalone P4 operation

Only the P4 and Metasys are required at runtime. The development computer is
used for source builds, signed updates, private source import and scoped tests.
No FastAPI process or permanent SQLite service is required. The legacy host URL
and diagnostic NVS bytes remain available to old firmware on rollback, but
0.1.6 and later do not send, enqueue or periodically write those diagnostics.

## Open the built-in page

Open **https://est3-device.local/** on the controller's LAN. mDNS advertisement and address resolution were observed on the field VLAN. The firmware
advertises this name using pinned Espressif mDNS 1.13.1. Routed networks must
provide an authorized name-resolution path for the same name if multicast does
not cross the router.

The retained certificate's DNS SAN is `est3-device.local`; it does not contain
the DHCP IP. Trust the exact retained `private/device-cert.pem` certificate in
the browser/OS through the owner's normal certificate-management procedure.
Do not bypass TLS verification or substitute a newly generated certificate.
The management CLI validates trust/time and the exact leaf before sending its
token, so it can continue using the numeric DHCP address.

Use **Load saved key** with `private/est3-web-admin-key.json`, or paste the
existing device token from the private credential file. The page keeps it in
memory only. Lock/reload clears it. Public page assets contain no site data;
all status, raw observations, inventory and management routes require the token.

- **BACnet & Status:** firmware, network, receiver health, assignment and last
  complete revision metadata. Source conditions remain explicitly unverified.
- **Device directory:** searches retained backup labels, raw types, addresses
  and UUIDs; stable `#device=<uuid>` links and per-condition BI/quality details.
- **Receiver diagnostics:** recent raw records, offsets/epochs/errors, incomplete
  fragments, evictions and private on-demand JSON export. RAM clears at boot.
- **Configuration:** volatile receiver baud and registry validation/preview/apply.
  Verified boot default remains 9600 8N1. Other rates cannot create validated
  reports. Registry import never establishes a normal state.
- **Firmware:** signed application image plus detached signature JSON. It verifies
  image hash, new boot, registry, FTDI/9600 and diagnostics before confirmation.

There is no panel command, reset/acknowledge/silence/disable or serial-write UI.
Network is DHCP; existing BACnet Device 3899000 and Vendor 65535 remain explicit
lab assignments pending site engineering. BACnet COV, BBMD/FDR and segmentation
are not advertised. Metasys must inspect Reliability/Status_Flags/DataValid;
an inactive Present_Value with invalid quality is not evidence of normal.

## Source import and stable identities

Build the optional native SDU reader as described in `handoff/SDU_READER_NOTES.md`.
Read archives through scratch copies and keep all outputs private:

```sh
PYTHONPATH=private/sdu-reader/python .venv/bin/python tools/sdu_inventory.py \
  /private/path/current.SDU --site-id P4-e8f60ae41fe8 \
  --output-prefix private/reviewed-source
```

This produces a source catalog, registry and preview. It reads selected scalar
columns only, checks active table counts, unique panel/LRM/device keys, physical
and LRM joins, capacity and labels. Conditions are all unverified. Raw message
blobs remain in the original archive; no invented location decoding is used.

Subsequent imports require `--previous-registry` and `--previous-catalog`.
Renames preserve UUIDs/instances. Changes in physical source identity, binding or
type stop for review. Missing rows are retained, never automatically retired
from a possibly stale backup. Unknown special scopes remain explicitly labeled.
Review both archive provenance and the preview before applying. Save the source
catalog alongside the controller registry backup. A watched folder cannot
produce a fresh contractor export or detect a quiet-device rename automatically.

## Signed OTA and recovery

Keep `IDF_PATH` set to the pinned v5.5.5 checkout and the correct native tools
environment. App-only updates preserve partition table, bootloader and eFuses.
Never run provisioning, serial flash or erase against this deployment.

```sh
.venv/bin/python tools/package_release.py
.venv/bin/python tools/sign_release.py release/0.1.14/est3_gateway_rxonly.bin \
  --output private/ota-0.1.14-signature.json
.venv/bin/python tools/gateway_client.py --host GATEWAY_IP \
  upload release/0.1.14/est3_gateway_rxonly.bin
```

The signature key never enters the browser. Never replace a release archive
with a different binary bearing the same version. Unconfirmed images roll back
after 180 seconds. The CLI verifies the complete running ELF descriptor hash;
that is different from the binary-file SHA-256.

New qualified registries use NVS key `catalog_v2` in the existing registry
partition. Legacy `catalog` is preserved. Therefore 0.1.5 rollback retains its
old compatible registry (empty at this handoff), and 0.1.6 or later can recover the new
one later. Old firmware will not expose new catalog objects. Do not claim full
monitoring during that rollback; its purpose is recoverable Ethernet management.
Use confirmed 0.1.14, listed in STATUS.md. The retained other slot is confirmed
0.1.13, which has diagnostic startup pauses. Never deploy 0.1.7, 0.1.8, 0.1.10,
0.1.11 or 0.1.12: those candidates failed startup. 0.1.6 has a known full-catalog
preview/load defect. Archived 0.1.9 passed full catalog/BACnet checks but uses the
older startup/reboot path. Archived 0.1.5 uses 9600 at boot with its old empty
catalog. 0.1.4 uses 19200 and needs an authenticated volatile receiver change to
9600; 0.1.2 is not a valid working recovery release.

Application startup exposes `startup_phase`; confirmation and registry mutation
wait for `ready`. Management is started before catalog loading when Ethernet is
available. The initial wait is bounded at ten seconds, so unavailable DHCP does
not indefinitely prevent receiver startup. Physical network-absent acceptance
and extended restart/load soak are still outstanding.

Backup source catalogs, registry JSON, existing credentials, signing trust and
release files privately. Never publish raw SDU archives, raw serial records,
device keys/tokens, images or the private transfer bundle. The bundler now closes
SQLite snapshot connections before hashing to avoid disappearing WAL/SHM entries.

## Automatic monitoring acceptance

See `SOURCE_COVERAGE.md`. The 30 September readback preserved one automatically
received local-trouble ACT/RST pair and an inbound operator-command record on the
existing receive connection. See [port review](PORT_CONFIGURATION_REVIEW.md) and
[site checklist](SITE_VISIT_CHECKLIST.md). These establish a scoped event path;
the decoder remains revision-only and every condition remains invalid.
Printer reports prove bytes and metadata, not unattended current-state
recovery. Continue observing natural traffic; do not generate live faults or
change panel routing to manufacture fixtures. Event assertion/restore mappings
need exact, authorized source evidence before enabling the observation reducer.
A verified automatic snapshot or supported read-only integration is needed to
establish conditions already active when the gateway boots.

Independent BACnet tests and short stable readbacks are not a 24-hour mixed-load
soak, physical electrical certification or installed Metasys acceptance.

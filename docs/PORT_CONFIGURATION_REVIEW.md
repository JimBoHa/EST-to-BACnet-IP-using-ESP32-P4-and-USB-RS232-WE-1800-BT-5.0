# Panel / port review - 30 September 2026

**Automatic printer output is now observed on the existing Port 2 receive path.**
No rewiring, serial transmission or panel programming was required to receive it.
Exact installed port-menu settings are still not available as a remote readback.

## Direct evidence

Authenticated, certificate-pinned GET requests retrieved 317 retained serial
payload bytes from confirmed firmware 0.1.14, boot 31, after 37.34 hours uptime.
The receiver remained 9600 8N1, with no flow control or payload TX. Its complete
512-byte diagnostic tail contained all 317 bytes from offset zero. Every retained
printer line was checked against that tail at its reported offset.

There is one local-trouble ACT record and one matching RST record, plus an inbound
operator panel-silence record. The common event address matches exactly one
qualified power-supply pseudo point in the March backup; it is not a detector or
module physical-row match. Event timestamps remain panel-local and unverified.
The gateway did not initiate the logged command. These records are formatted as
individual event output, with reception times separated by the event intervals;
there is no manual-report envelope in the complete retained byte sequence.
No report or panel operation was requested by this session.

UART/USB error counters, receive drops and record evictions were zero. The parser's
one gap marker is its expected initialization marker at offset zero before first
input; there is no observed midstream byte discontinuity. This is not an electrical
certification, a full-load soak, a complete routing test or a current-state snapshot.

Sanitized [field evidence](../evidence/field-automatic-printer-2026-09-30.json)
includes firmware and raw-payload hashes. Original bytes, exact addresses/labels,
individual receipt times and source joins remain in `private/port-review-20260930/`.
No firmware update or settings mutation was performed.

## Backup configuration

The newest archive is unchanged, SHA-256
`c8bd4dedb598fea590bd5167b6fcb692e74625cfb1d00e56bd1b71b275aa200b`.
Selected active rows were inspected again using the native Paradox reader.
No credential tables were read. The main cabinet has:

| Setting | Backup value | Meaning established here |
|---|---|---|
| Port 1 / Port 2 Type | 1 / 1 | Enum label not independently verified |
| Port 1 / Port 2 Baud | 4 / 4 | Enum label not independently verified; actual Port 2 reception works at 9600 |
| Port 1 / Port 2 Filter | 1919 / 1919 | Individual filter-bit meanings not independently verified |
| Port 2 annunciation group | 0 | Exact join to `Default_Display_Group` |
| State routing | 0 | Exact join to route named `All_Cabinets` |
| Partition routing | 0 | Exact join to route named `All_Partitions` |
| ECP.DB | 0 active rows | No active ECP configuration rows in this backup |

Route labels and scalar references are established; route matrices and all
object-specific message filters have not been fully decoded. An empty ECP table
does not prove the live panel's mode. Revision metadata agrees with the newest
backup, but no full live-program comparison exists. The live observations support
printer behavior; they do not establish every event class or every routed point.

## What the documentation resolves

Edwards' [Wireless Service Application Guide, 3102425-EN R002](https://learning.edwardsfire.com/pluginfile.php/7722/mod_resource/content/4/3102425-EN%20R002%20Edwards%20Wireless%20Service%20Application%20Guide.pdf)
shows printer mode, baud and event selection in 3-SDU (printed page 4), and gateway
mode setup in 3-SDU (printed page 7). Its network hardware example is not proposed
as additional equipment for this project.

The manufacturer-authored [3-SDU Help](https://pdfcoffee.com/3-sdu-help-pdf-free.html),
under Cabinet Configuration - Ports and Sending events to an ancillary printer,
identifies port filters, state routing and message-annunciation routing as distinct
controls. The help is a public mirror and is not a version-matched enum schema.

MSA's [EST3 ECP manual, sections 2.1.2, 3.4, 6.4 and 8.2](https://assetlibrary.msasafety.com/m/31ef0005e95bcd13/original/Protocol-Driver-Manual-EST3-ECP-8700-39.pdf)
requires gateway configuration in 3-SDU and describes Report/Delta services. The
panel initiates the link poll/response cycle; the gateway inserts requests into
responses. It also supervises that communication. Converting a port before a
compatible responder is ready can introduce a communications trouble. This manual
does not give us a complete implementation specification for CPU 05.30.

Reviewed operation manuals provide Status/Report procedures but no verified
front-display path for reading or editing all port configuration. Therefore, do
not send the owner searching for a promised port-settings menu or connect TX as
a substitute for configuration. The owner has confirmed panel-only access.

## Remaining work and the visit

Automatic **event transport** is observed for this pair. Automatic **complete
current state**, source liveness during silence, all condition mappings and
recovery after a P4 restart/lost data are not established. Production firmware
still treats these lines as raw observations and keeps BACnet conditions invalid.
The restore is historical evidence, not proof that the point remains normal now.

[SITE_VISIT_CHECKLIST.md](SITE_VISIT_CHECKLIST.md) consolidates physical photos,
read-only display/report collection and verification before leaving. Its temporary
GET-only capture helper has overlap/loss/reboot tests. It installs no permanent
host service. Further parser work and deployment can use Ethernet; full polling
still needs verified protocol/configuration evidence and may require 3-SDU access.

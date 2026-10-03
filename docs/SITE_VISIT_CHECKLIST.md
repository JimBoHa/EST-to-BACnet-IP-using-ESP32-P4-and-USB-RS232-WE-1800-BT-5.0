# Site visit: 1 October 2026

**Historical checklist — superseded 2026-10-03:** Owner now authorizes preparing orange TX → RX2; completed wiring remains unconfirmed. Firmware TX stays disabled. [Current source/polling requirements](PRINTER_TROUBLE_OBSERVATIONS.md) apply; another manual Print is not an autonomous recovery solution.

## Decision before travelling

**Keep the working receive connection. No additional wire is needed for automatic
printer events.** On 30 September the P4 retained one local battery-trouble
activation, its restore and an operator-command record. The 317-byte capture is
complete, with no reported UART/USB errors or dropped bytes. The event address
matches one qualified backup pseudo point. This establishes the observed event
path, not complete device-state coverage. See [port review](PORT_CONFIGURATION_REVIEW.md).

Only panel access is available for this visit; no 3-SDU computer or technician.
There is no verified front-panel procedure for reading/changing every port mode,
filter and routing setting. The documented configuration path uses 3-SDU.
Accordingly, this visit can complete physical documentation and collect source
evidence, but cannot guarantee ECP commissioning or automatic state recovery.
If full current-state recovery is mandatory before leaving, programming access
and the supported ECP implementation must be arranged first. Wiring alone
cannot satisfy that requirement.

The existing backup can be inspected by a service company off site. The exact
request to forward is at the end of this checklist. No message has been sent.

## Bring / prepare

- Phone/camera with space for clear photos; access to this checklist and the P4
  page at `https://est3-device.local/` on the site network. Keep the existing key
  available privately if using the page. No password or token needs to enter chat.
- Confirm remote Ethernet access before touching anything. Record any networking
  change planned for the site; Ethernet is the firmware recovery path.
- Start the temporary capture below before requesting any report. It must print
  **READY**. A capture is not scheduled or left running by this document.
- Have the existing authorized panel access credential available if needed for
  History. If unavailable, record that limitation; do not change credentials.

## Collect at the main cabinet

1. Photograph the normal front screen, date/time and all event/disabled counts.
   Record the actual phone time and timezone alongside it. Do not set the panel
   clock. Its timestamps have not been aligned to workstation time.
2. Photograph the cabinet identification, accessible CPU/serial-card model and
   revision labels, and a wide view of existing wiring. Do not remove cards to
   expose a label. Include a close view of TB2 labels and conductor entry points
   for both serial ports, plus the adapter model label and USB/P4 connection.
3. Verify the existing connection visually: yellow adapter RX to panel TX2,
   black serial common to COM2. Record whether Port 1 has another attached
   device and its model; do not disconnect it. Orange TX stays disconnected.
   Each unused lead must be separately insulated, including red auxiliary +5 V.
   These are documentation checks; no ECP rewiring is prescribed for this visit.
4. At the main panel, use **Command Menus > Status > All active points > 01 >
   Display**. Photograph every resulting page and any explicit empty result.
   Collect the **Disabled points** list too. Repeat for panel **02** if offered.
   Use the Status menu rather than acknowledging queues. If labels differ,
   photograph the choices instead of entering another control menu.
5. With capture READY, collect those same status lists using **Print Locally >
   Printer 2**, one list at a time. Wait for the complete output to be checked
   before starting the next list.
6. If authorized access permits, use **Command Menus > Report > History >
   History With Text > 01 > Printer 2**; then repeat for **02**. Preserve any
   displayed scope/options. History is useful for past event syntax; historical
   records must never be applied as newly occurring events.

The status/history navigation follows Edwards' [EST3 operation manual,
printed pages 24-25 and 34-35](https://alarmspec.com/wp-content/uploads/2025/12/270382-EN-R012-EST3-System-Operation-Manual.pdf).
That revision covers CPU 5.4x, while this panel reported 5.30; confirm the visible
menu labels. Do not force a different menu path. Reports are one-time evidence
collection, not the proposed unattended operating method. Another Revision
Levels report is unnecessary unless the installed revision has changed.

No reset, silence, acknowledge, disable/enable, test/drill, battery disconnection,
panel reboot or program download is part of this checklist. The earlier battery
event includes a restore; it is not evidence of a currently active battery fault.

## Check before leaving

- Photos show terminal labels and connections clearly, and display evidence
  identifies the panel, scope and time.
- Report captures have identifiable beginnings/endings and agree with the
  requested panel/list. Every page or output limitation is accounted for. Keep
  empty results and password-denied results too.
- Capture shows no missing record IDs within the session, unexpected boot change
  or unexplained stream discontinuity. Compare receiver errors/drops before and
  after. The ordinary first-input marker at offset zero is not a lost packet.
- P4 HTTPS remains reachable; firmware is confirmed, USB attached and receiver
  remains 9600 8N1. The panel has no newly introduced trouble from this work.
- Preserve capture/photos privately before closing the session. Confirm receipt
  and readability while still on site, so a missing image or truncated report is
  discovered there.

Passing these checks completes this evidence visit. It does not certify all
alarm/supervisory/disabled mappings or startup recovery. Future decoder updates
can use existing Ethernet OTA. A future panel-mode change may still need 3-SDU
and site access; that requirement cannot be removed by a promise or spare wire.

## Temporary capture on the development computer

Run from the repository, immediately before the report collection:

```sh
.venv/bin/python tools/capture_printer.py \
  --host est3-device.local --seconds 1800 \
  --output private/site-visit-20261001-printer.jsonl
```

The existing certificate trust/time and exact leaf are checked before the key is
sent. The tool makes GET requests only, resolves the target once, deduplicates
overlapping RAM windows, reports missed IDs/reboots and writes a new private
file with mode 0600. It stops after the requested duration (maximum one hour),
64 MiB or three consecutive request failures. It creates no permanent service.
Use a new output filename for a new session; it refuses to overwrite evidence.

The JSONL records preserve raw line bytes, IDs, offsets, epochs and receipt
uptimes. CR/LF delimiters are absent from this API; this is **not a byte-exact wire
dump**. Gap records contain diagnostic text, not panel data. Partial lines at the
end are explicitly counted. A finish record confirms normal collector completion,
not completeness of an individual report. RAM eviction need not mean collector
loss if all IDs were captured. Check actual beginning/end and requested scope.

The P4's own export retains only its current 128-record RAM window. A long history
report can outgrow that window; use the live temporary collector and inspect its
loss markers. The collector was tested on the current retained event records;
full-rate history output remains to be verified during this visit.

## Exact off-site request for the service company

Please inspect a copy of the current EST3 project using the compatible 3-SDU
version (the panel reported SDU 05.47 and CPU 05.30). Do not modify/download it
for this request. Provide:

- **Configure > Cabinet > main cabinet 01 > Ports > Port 2**: displayed Port Type,
  baud, all event-enable checkboxes and Message Annunciation Group. Include Port 1
  and its current purpose. A backup screenshot is not a live configuration readback.
- The cabinet's State/partition routing and object message-annunciation routes,
  including whether any objects are excluded from Port 2. Identify project
  revision/date and evidence that this is the running panel program.
- Whether CPU 05.30 supports a documented, read-only query on the current printer
  interface. If not, the supported ECP mode and a complete matching specification
  for link framing, handshake, Report/Delta reads, timeouts and initial-state
  recovery. The available FieldServer configuration manual is not that wire spec.
- Whether port conversion can be completed through an already commissioned remote
  service path. Do not assume one exists or create an exposed serial tunnel.

Edwards documents printer selection/filtering and Gateway Type III configuration
in [3102425-EN R002, printed pages 4 and 7](https://learning.edwardsfire.com/pluginfile.php/7722/mod_resource/content/4/3102425-EN%20R002%20Edwards%20Wireless%20Service%20Application%20Guide.pdf).
The [3-SDU Help, Cabinet Configuration - Ports](https://pdfcoffee.com/3-sdu-help-pdf-free.html)
also describes network routing and event filtering. These establish which
settings to inspect, not the numeric enum meanings in our archive.

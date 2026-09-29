# Field connection observation — 2026-09-28

The owner reported moving the controller to `192.168.75.x` and connecting its adapter to the EST panel following the earlier wiring guidance. The exact physical wiring, installed panel card and panel port configuration were not independently verified. The initial observation below changed no firmware/settings. Subsequent sections record the 0.1.4 diagnostics update, receiver baud checks and an owner-requested front-panel report. No serial payload or operational command was transmitted by the gateway.

## Device identification and access

The Mac used `192.168.2.34/24`, routed through `192.168.2.1`. A bounded TCP 443 search on `192.168.75.0/24` identified the controller at **192.168.75.157** by exact comparison with its saved device certificate, with normal TLS trust/time checks enabled. Credentials were sent only after that identity check.

The authenticated response confirmed:

- Project `est3_gateway_rxonly`, version **0.1.3**, partition `ota_1`, boot count **11**.
- ELF SHA-256 `c601654d378a81ca734ddff2e1897c7c7bf5b6a982d19d2cf80a353173bdaac3`, matching the previously confirmed release.
- `awaiting_confirmation=false`, `serial_payload_tx_enabled=false`, `simulation=false`.
- FTDI USB adapter connected; firmware requested **19200 baud, 8N1**, and deasserted DTR/RTS. A later source review found incorrect modem-control request/masks in the pinned driver, corrected by application vendor requests in 0.1.4 below. The initial response did not measure the actual output levels or establish matching panel settings.

Independent BACpypes3 discovery, ReadProperty and ReadPropertyMultiple passed across this route. The device exposed its Device object and four gateway health objects; **no EST point objects or EST state data were present**. BACnet network success does not establish panel communication. Evidence: [BACnet result](../evidence/field-bacnet-2026-09-28.json).

## Passive serial observation

From 23:56:27 to 23:57:27 UTC, 13 authenticated status samples were collected at five-second intervals over 60.209 seconds. All requests succeeded. Boot count stayed 11, USB stayed connected with connection count 1, and no new USB errors, line errors or dropped receive bytes were reported. Both starting and ending receive counts were **zero bytes**; CRC remained zero.

**Result: the network and USB connection responded, but EST serial data reception remains unverified.** The observation does not establish a bad cable or bad panel, nor a healthy physical serial path: no received payload was available to inspect. ECP parsing remains disabled in this firmware. Evidence: [complete passive samples](../evidence/field-passive-serial-2026-09-28.json).

## Owner wiring confirmation and photos

After the observation, the owner explicitly confirmed orange disconnected and the other two wires connected as previously indicated: yellow RX to TX2 and black serial common to COM2. Local photos `Downloads/IMG_8281.HEIC` and `IMG_8282.HEIC` were reviewed; originals were left unchanged and were not copied into the repository. They show the expected TB2 serial labels and are consistent with that description. Perspective and hidden wire-entry points prevent an independent termination/continuity verification. They do not reveal programmed baud/interface mode or conclusively identify the optional serial card.

Unused wire ends, including orange, appear exposed. The owner was advised to insulate each unused lead separately, especially red auxiliary +5 V. Electrical levels, actual cable functions, suitable field termination and continuity remain unmeasured.

A further authenticated status read at 2026-09-29 00:02:08 UTC (2026-09-28 local time), uptime 642.756 seconds, still showed boot 11, USB connected and zero received bytes/USB errors/line errors/drops. Evidence and source-photo hashes: [photo follow-up](../evidence/field-photo-followup-2026-09-28.json).

The owner confirmed that the port settings are unknown. Next diagnostic input is the **existing Port 2 baud rate and interface mode**, obtainable from the current configuration or responsible EST technician. No panel setting changes were requested. Do not infer panel settings from the adapter's configured 19200 8N1, and do not infer a hardware fault solely from silent receive counters.

Signed OTA and timeout rollback were already tested on the previous bench LAN. Authenticated management now responds on the new network, but this field check did not repeat an update or reboot. The diagnostics host was not migrated from its previous `10.0.7.6:8443` endpoint or revalidated; its queue increased during the observation. Direct management reads provided the evidence above.

## Firmware 0.1.4 and active USB IN evidence

On 2026-09-29 UTC (2026-09-28 local time), firmware 0.1.4 was signed and uploaded over the same field Ethernet route, booted on `ota_0`, and explicitly confirmed after its complete ELF hash matched the local build. Boot count became 12. The previous 0.1.3 image remains in the other slot. Bootloader, partition layout and eFuses were not changed. Evidence: [confirmed update](../evidence/field-update-0.1.4.json), [build manifest](../evidence/build-manifest-0.1.4.json).

New [serial diagnostics](SERIAL_DIAGNOSTICS.md) observe raw FTDI USB IN transfers before status stripping, expose bounded payload capture and permit authenticated receiver-only baud changes. Direct FTDI vendor requests also correct the pinned driver's modem-control request and masks. No payload OUT buffer or serial transmitter was added. Correcting that defect alone did not cause bytes to arrive.

Two 30-second observations at 19200 and 9600 8N1 each counted **1,896 status-only USB packets**, zero payload and zero new USB errors, line errors, invalid packets or drops. The original receiver rate was restored to 19200. This proves USB IN callbacks were active while the panel was quiet; it does not prove electrical byte accuracy. [Results](../evidence/field-serial-diagnostics-0.1.4.json).

Independent BACnet discovery/RP/RPM passed after the update; only Device plus four gateway health objects were present. Live diagnostics API rejection tests returned 400 for invalid/fractional baud and extra transmit fields, and 401 for an invalid token, without changing baud/boot. The firmware build, symbol audit, 25 Python tests and two native ASan/UBSan tests passed. A later exact-hash read at uptime 837 seconds confirmed the same boot and zero RX/USB/line errors. [BACnet](../evidence/field-bacnet-0.1.4.json), [API checks](../evidence/serial-api-validation-0.1.4.json), [later read](../evidence/field-stability-0.1.4.json).

The legacy telemetry endpoint remains on the previous LAN. By that later read its diagnostic outbox held 32 records and reported 202 lifetime telemetry drops. This is diagnostic-outbox overflow, separate from the serial receive drop counter, which was zero.

## Local SDU backup discovery

Three genuine owner-local SDU archives were inspected read-only and their original hashes rechecked unchanged. Selected Paradox cabinet/LRM fields were read using a locally built native pxlib with pypxlib; source archives and all extracted data remain private. The newest cabinet table is dated 2026-03-04 and identifies main cabinet 01 as a 3-CPU3 configuration with an A/B bypass module, consistent with the supplied photos.

In the newest backup, both main-cabinet ports have raw type code 1 and baud code 4. These enumeration labels have not been verified, so they are not asserted to mean a specific mode/rate. The ECP table header reports zero active records. The two older archives also have zero active ECP records; their port settings differ. No archive has yet been matched to the live installed program revision. The project-level PC communications baud is a separate setting and is not evidence for the auxiliary port baud.

These findings support a read-only printer report as the next test and provide candidate inventory data for later schema validation. They do not prove that the running panel is in printer mode, has ECP disabled, or has a validated complete inventory.

## Front-panel report test

Following [Edwards' Revision Levels procedure, printed page 35](https://alarmspec.com/wp-content/uploads/2025/12/270382-EN-R012-EST3-System-Operation-Manual-1.pdf#page=42), the owner confirmed sending the report to Printer 2. With the receiver at **19200 8N1**, the gateway received **3,509 payload bytes**, with **3,547 USB packets carrying UART error status** and 1,389 changed line-status error indications. There were no USB errors or application receive drops. Counts refer to packets/indications, not distinct bad characters.

This establishes arriving panel-to-adapter data associated with the requested report. The bytes are not reliable text at this setting. The receiver was then changed to **9600 8N1**, and the owner was asked to repeat the same report. The 512-byte capture ring overran between some HTTPS samples during the first report; missing offset ranges are recorded privately. No claim of a complete first-report capture is made.

The owner repeated the report at **9600 8N1**. This produced **3,564 bytes**, all printable ASCII or normal whitespace, with the revision-report header and complete end marker. Offset-aware reconstruction of the private HTTPS samples recovered all 3,564 bytes without a gap. The USB/UART error and application drop counters did not increase. **Panel Printer 2 report reception is confirmed.** [Sanitized result](../evidence/field-panel-report-0.1.4.json).

The report identifies panel 01, CPU firmware 05.30.00, SDU 05.47.00, project 01.01.02 and database date 03/04/26, consistent with selected fields in the newest local backup. This is not a byte-for-byte live configuration comparison or proof that every device/card matches that archive. The receiver remains at 9600; 0.1.4's boot default remains 19200 until a follow-up build changes it.

Raw report captures remain in `private/`. ECP parsing, real-time event coverage and inventory completeness remain separate work.

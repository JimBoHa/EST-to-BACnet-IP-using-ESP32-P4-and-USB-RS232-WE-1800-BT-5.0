# Field connection observation — 2026-09-28

The owner reported moving the controller to `192.168.75.x` and connecting its adapter to the EST panel following the earlier wiring guidance. The exact physical wiring, installed panel card and panel port configuration were not independently verified. Testing remained passive with respect to the panel; no serial payload or operational command was sent, and no device firmware/settings changed.

## Device identification and access

The Mac used `192.168.2.34/24`, routed through `192.168.2.1`. A bounded TCP 443 search on `192.168.75.0/24` identified the controller at **192.168.75.157** by exact comparison with its saved device certificate, with normal TLS trust/time checks enabled. Credentials were sent only after that identity check.

The authenticated response confirmed:

- Project `est3_gateway_rxonly`, version **0.1.3**, partition `ota_1`, boot count **11**.
- ELF SHA-256 `c601654d378a81ca734ddff2e1897c7c7bf5b6a982d19d2cf80a353173bdaac3`, matching the previously confirmed release.
- `awaiting_confirmation=false`, `serial_payload_tx_enabled=false`, `simulation=false`.
- FTDI USB adapter connected; configured by the unchanged firmware for **19200 baud, 8N1**, with DTR/RTS deasserted. This does not measure the physical baud rate or establish matching panel settings.

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

# Actual PoE/Ethernet tests — 2026-09-27

Owner moved the ESP32-P4 to PoE Ethernet with USB-C disconnected. EST panel wires remained disconnected. No USB operation was used for the tests or firmware correction below.

Device: MAC `e8:f6:0a:e4:1f:e8`, DHCP `10.0.7.195`, BACnet Device 3899000. Mac: `10.0.7.6`. The certificate-pinned, authenticated HTTPS client identified the installed 0.1.1 application, boot count 6, and connected FTDI adapter.

| Check | Observed result | Evidence |
|---|---|---|
| DHCP/discovery/management | PASS: targeted discovery and pinned HTTPS status | `ethernet-initial-status.json` |
| First signed update | Image uploaded and booted as 0.1.2, `ota_1`, boot 7. Confirmation correctly refused because reported hash was truncated | `ethernet-0.1.2-pending-status.json`, `ethernet-update-0.1.2-errors.log` |
| Automatic timeout rollback | PASS: unconfirmed 0.1.2 returned to 0.1.1, `ota_0`, boot 8, after the 180-second deadline; Ethernet access recovered | `ethernet-rollback-0.1.2.jsonl`, `ethernet-rollback-result.json` |
| Wrong credential | PASS: HTTP 401 | `ethernet-ota-rejections.json` |
| Bad signature | PASS: HTTP 400; current image unchanged | Same |
| Correctly signed but truncated image | PASS: ESP image validation rejected it | Same |
| Wrong project | PASS: HTTP 400 | Same |
| Connection closed mid-upload | PASS: current version/partition/boot count unchanged | Same |
| Corrected signed update | PASS: 0.1.3 uploaded, rebooted as `ota_1`, boot 9; full ELF hash matched local image and remote confirmation succeeded | `ethernet-update-0.1.3.json` |
| Independent BACnet client | PASS on actual board: Who-Is/I-Am, indexed five-object list, RP/RPM, protocol-disabled/USB health and advertised service bits | `ethernet-bacnet-0.1.3.json` |
| Durable diagnostics delivery | PASS: retained sequences 1–32 delivered over authenticated HTTPS; explicit gap 33–225 recorded; ACK advanced to 228; device queue emptied | `ethernet-telemetry-replay.json` |

Evidence filenames above are under `evidence/`. No registry devices are provisioned, so BACnet exposes the Device object and four gateway-health objects, not invented detector data.

## Fix actually required

`esp_app_get_elf_sha256()` limits its string to `CONFIG_APP_RETRIEVE_LEN_ELF_SHA`, configured as 9. The 0.1.2 status endpoint therefore returned a nine-character hash even with a 65-byte output buffer. The client required all 64 hexadecimal characters and refused confirmation. Version 0.1.3 formats all 32 bytes from `esp_app_get_description()->app_elf_sha256` directly. The actual Ethernet update verifies this fix against the image descriptor.

Confirmed 0.1.3 ELF SHA-256: `c601654d378a81ca734ddff2e1897c7c7bf5b6a982d19d2cf80a353173bdaac3`.

The diagnostic outbox had filled during earlier operation without a host. All first 32 persisted records survived the move, failed update, rollback and corrected update. The 193 omitted records were explicitly represented as a gap rather than silently reported as complete history. These are gateway diagnostics only; no EST events were decoded.

## Limits

The tests prove working Ethernet application updates, timeout rollback and the listed rejection paths on this board. They do not prove recovery from every hardware/network fault, physical power loss during flashing, damaged bootloader/partition tables, a 24-hour mixed-load soak or field-network reachability. PoE USB voltage/load margins and independent RS232 TX capture remain unmeasured. Real EST ECP remains disabled.

Reproduce reads with `tools/bench_bacnet.py --host DEVICE_IP --local-ip MAC_IP --output RESULT.json`. Negative OTA checks are in `tools/bench_ota_rejection.py` and require `--disconnected-bench`; they overwrite the inactive app slot and must be followed by a valid signed update. Never use those stress/rejection checks on an attached building panel.

# Real EST ECP is disabled

No complete manufacturer ECP wire specification or verified ECP captures have been supplied. No operational command encoder, serial tunnel, or BACnet-to-panel command route exists in this release. Production source calls no serial payload transmit function; the linked image is audited for its absence. The USB driver opens with an OUT buffer size of zero. USB enumeration and FTDI setup vendor-control transfers still occur and require independent electrical/output measurement.

**30 September update:** automatic local-trouble ACT/RST and an inbound operator
command were retained on the current 9600 receive path. See
[port review](PORT_CONFIGURATION_REVIEW.md) for exact evidence and limits.
Earlier bench/initial-attachment rows below retain their historical scope.

| Capability | Evidence | Status |
|---|---|---|
| FTDI USB driver API | Espressif FTDI 2.1.1 / CDC ACM 2.3.0 source and dependency lock | IMPLEMENTED |
| FTDI status handling | 0.1.4 observes raw MPS-sized transfers before the pinned driver removes the status prefix; 1,896 status-only packets per 30-second idle check at each of 19200/9600; native binary/ring tests pass | STATUS_ONLY_USB_TRAFFIC_OBSERVED; independent physical byte accuracy NOT_RUN |
| Converter USB identity | VID 0403, PID 6001, bcdDevice 0600; FTDI / USB-RS232-WE-1800-BT-5.0 / ABBAWJDO | USB_BENCH_OBSERVED |
| RS232 electrical levels / color mapping / isolation | Two owner-supplied CPU/TB2 photos reviewed; owner confirms yellow to TX2, black to COM2 and orange disconnected; no continuity or electrical measurements | Wiring OWNER_REPORTED, PHOTO_CONSISTENT; electrical levels/isolation UNKNOWN |
| Candidate serial configuration | 0.1.4 applies 19200/9600 8N1 without flow control and correct FTDI modem-control requests to deassert DTR/RTS; receive settings are volatile | USB_API_ACCEPTED; physical signal measurement NOT_RUN |
| Physical USB-A reconnect | Disconnect then reconnect observed; connection count 1 to 2, boot count remained 9, zero new USB errors; Ethernet and subsequent BACnet reads available | IDLE_HOTPLUG_PASS; serial-traffic hotplug NOT_RUN |
| Attached adapter during network reads | 131 authenticated HTTPS reads and 564 BACnet reads in 60 seconds; adapter remained connected with no new boot/errors | IDLE_NETWORK_LOAD_PASS; serial throughput NOT_RUN |
| Owner-reported EST attachment, 2026-09-28 | Same certificate at 192.168.75.157; 13 passive status samples over 60 seconds, USB connected, zero RX bytes and no new boots/reconnects/USB or line errors | NETWORK_ACCESS_PASS; EST data connection UNVERIFIED |
| Owner-requested Printer 2 revision report | 19200 produced UART errors; 9600 8N1 produced five complete reports totaling 8,910 readable bytes across 0.1.4/0.1.5, including after reboot, with no capture gaps or new errors/drops | REAL_PANEL_REPORT_RX_PASS; live event decoding NOT_IMPLEMENTED |
| Automatic printer events, 2026-09-30 | Complete 317-byte tail and matching retained offsets; one local-trouble ACT/RST pair and an inbound operator command; no reported USB/UART errors/drops; one backup pseudo-point join | AUTOMATIC_RX_PASS_SCOPED; full condition coverage/current-state recovery NOT_VERIFIED |
| ECP framing / checksum / addressing / sequence / session | No version-matched specification | UNKNOWN; DISABLED |
| ECP reads / transport acknowledgements | Public FieldServer manual is not a wire specification | UNKNOWN; DISABLED |
| Current-state recovery / independent conditions | Application simulation only | SIMULATION_ONLY |
| Complete inventory / device text / program-change detection | Three genuine local SDU backups inspected read-only; selected cabinet/LRM fields readable, raw port enum labels and match to installed program unverified | CANDIDATE_BACKUPS_AVAILABLE; complete importer/live match UNKNOWN |
| Native Metasys mapper/graphics provisioning | No installed-site capability results | DRY_RUN_ONLY |

Independent zero-payload TX capture remains NOT_RUN. No transmitted bytes in application code and a successful boot are not physical proof that the RS232 output is silent. The owner reported panel attachment on 2026-09-28; actual wiring and live port configuration remain unverified. After the initial passive check, firmware was remotely updated to 0.1.4, adapter receiver rates were checked and the owner requested a read-only panel report. The gateway sent no serial payload or panel operational commands; no panel program changes were requested. The handoff's electrical, protocol, contractor and commissioning checks remain outstanding; attachment alone does not satisfy them.

The manufacturer's [FieldServer EST3 ECP driver manual](https://assetlibrary.msasafety.com/m/31ef0005e95bcd13/original/Protocol-Driver-Manual-EST3-ECP-8700-39.pdf) describes the panel as the master initiating poll/response traffic (section 8.2). A claim that a configured ECP panel must remain silent until this gateway initiates communication is therefore not established. That integration manual is not a complete ECP wire specification and does not authorize guessed protocol requests.

Primary sources: [Waveshare board guide](https://docs.waveshare.com/ESP32-P4-WIFI6-POE-ETH), [revision configuration](https://docs.waveshare.com/ESP32-P4-WIFI6-POE-ETH/ESP-IDF), [FTDI component 2.1.1](https://components.espressif.com/components/espressif/usb_host_ftdi_vcp/versions/2.1.1/readme), [ESP-IDF OTA rollback](https://docs.espressif.com/projects/esp-idf/en/v5.5.5/esp32p4/api-reference/system/ota.html).

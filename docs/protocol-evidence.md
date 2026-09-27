# Real EST ECP is disabled

No manufacturer wire specification or authorized EST captures have been supplied. No operational command encoder, serial tunnel, or BACnet-to-panel command route exists in this release. Production source calls no serial payload transmit function; the linked image is audited for its absence. The USB driver opens with an OUT buffer size of zero. USB enumeration and FTDI setup vendor-control transfers still occur and require independent electrical/output measurement.

| Capability | Evidence | Status |
|---|---|---|
| FTDI USB driver API | Espressif FTDI 2.1.1 / CDC ACM 2.3.0 source and dependency lock | IMPLEMENTED |
| FTDI status handling | Driver `usb_host_ftdi_vcp.c` removes two bytes and forwards changed line-status flags; MPS-sized input transfers (`in_buffer_size=0`) | SOURCE_REVIEWED; packet traffic test NOT_RUN |
| Converter USB identity | VID 0403, PID 6001, bcdDevice 0600; FTDI / USB-RS232-WE-1800-BT-5.0 / ABBAWJDO | USB_BENCH_OBSERVED |
| RS232 electrical levels / color mapping / isolation | No measurements or inspected assembly photos | UNKNOWN |
| Candidate serial configuration | Driver accepts 19200 8N1, DTR/RTS deasserted | USB_API_ACCEPTED; actual baud measurement NOT_RUN |
| Physical USB-A reconnect | Disconnect then reconnect observed; connection count 1 to 2, boot count remained 9, zero new USB errors; Ethernet and subsequent BACnet reads available | IDLE_HOTPLUG_PASS; serial-traffic hotplug NOT_RUN |
| Attached adapter during network reads | 131 authenticated HTTPS reads and 564 BACnet reads in 60 seconds; adapter remained connected with no new boot/errors | IDLE_NETWORK_LOAD_PASS; serial throughput NOT_RUN |
| ECP framing / checksum / addressing / sequence / session | No version-matched specification | UNKNOWN; DISABLED |
| ECP reads / transport acknowledgements | Public FieldServer manual is not a wire specification | UNKNOWN; DISABLED |
| Current-state recovery / independent conditions | Application simulation only | SIMULATION_ONLY |
| Complete inventory / device text / program-change detection | No panel proof or supported export sample | UNKNOWN |
| Native Metasys mapper/graphics provisioning | No installed-site capability results | DRY_RUN_ONLY |

Independent zero-payload TX capture remains NOT_RUN. No transmitted bytes in application code, zero RX counters, and a successful boot are not physical proof that the RS232 output is silent. Before panel attachment, follow the handoff's electrical, protocol, contractor and commissioning gates. No panel attachment or live alarm generation was performed.

Primary sources: [Waveshare board guide](https://docs.waveshare.com/ESP32-P4-WIFI6-POE-ETH), [revision configuration](https://docs.waveshare.com/ESP32-P4-WIFI6-POE-ETH/ESP-IDF), [FTDI component 2.1.1](https://components.espressif.com/components/espressif/usb_host_ftdi_vcp/versions/2.1.1/readme), [ESP-IDF OTA rollback](https://docs.espressif.com/projects/esp-idf/en/v5.5.5/esp32p4/api-reference/system/ota.html).

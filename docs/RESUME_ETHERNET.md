# Resume remote Ethernet work

Read STATUS.md, FIELD_CONNECTION_TEST.md and ETHERNET_TEST_REPORT.md first. Board runs **0.1.3** at **192.168.75.157**, MAC `e8:f6:0a:e4:1f:e8`, with `ota_1` valid and boot count 11 on 2026-09-28. USB-C is disconnected and unavailable. FTDI USB-A remains connected; **owner now reports panel wires connected**. Exact wiring and panel serial settings have not been verified. Do not treat this as the earlier disconnected bench setup.

Field access from Mac `192.168.2.34` passed exact TLS certificate verification, authenticated HTTPS status and independent unicast BACnet reads. Thirteen status samples over 60 seconds showed USB connected, zero new boots/reconnects/errors/drops, and **zero received serial bytes**. A follow-up at 642 seconds uptime still showed zero bytes. EST communication remains unverified. ECP parsing and all serial payload transmission remain disabled; no firmware or device settings changed during this check. Owner confirmed yellow to TX2, black to COM2 and orange disconnected; local `Downloads/IMG_8281.HEIC` and `IMG_8282.HEIC` are consistent with that description. Photos do not independently establish continuity or settings. Exposed unused wire ends were visible; owner was advised to insulate each separately, especially red +5 V. Next useful input is the existing panel port baud/interface mode, not an assumption that silent receive counters prove a hardware fault.

Actual tests passed: signed upload/reboot/full-hash confirmation, automatic timeout rollback, invalid-signature/truncated/wrong-project rejection, interrupted upload, independent BACnet RP/RPM, and persisted diagnostic replay with an explicit overflow gap. The 0.1.2 hash-reporting defect was corrected in 0.1.3. Do not reinstall 0.1.2 as a working release.

```sh
.venv/bin/python tools/gateway_client.py --host 192.168.75.157 status
```

The updater signs locally, verifies the device certificate, checks all 64 ELF hash characters after reboot and explicitly confirms the new slot. Keep signing credentials and binaries private. Do not change bootloader/partition layout remotely. `--no-confirm` deliberately tests rollback and should be used only for a defined disconnected bench test.

The current address is a DHCP lease. Discovery uses Device 3899000. `tools/discover.py --broadcast 192.168.75.255` is intended for a client on that subnet; directed broadcasts may not cross routers. The Mac was instead on `192.168.2.34`, with a working route to `192.168.75.0/24`. A bounded TCP 443 search followed by certificate verification identified this board. Do not send its management token to another device or disable TLS verification. Recheck access after future moves.

The temporary diagnostics host was previously launched at `https://10.0.7.6:8443`, using `private/hardware-bench.sqlite`, bound specifically to that old Mac LAN address. It used `EST3_BIND=10.0.7.6`, `EST3_GATEWAY_ID=P4-e8f60ae41fe8`, and `tools/run_host.py`. Process 70385 was the initial launch; check the current process before stopping it. The host endpoint was not migrated or revalidated during the field observation, and queued diagnostics increased. It is not installed as a persistent service. Live log `evidence/hardware-host.log` is excluded from Git; a fixed session snapshot is retained. Do not mix this database with SIMULATION_ONLY data.

An idle physical USB-A unplug/replug test also passed: reconnect count increased from 1 to 2 with no reboot or new USB errors; BACnet reads remained available. Evidence is in `adapter-hotplug-result.json` and `adapter-hotplug-bacnet.json`.

Remaining work: extended mixed-load soak, physical PoE VBUS/RS232 measurements, independent TX capture, actual binary receive traffic and hotplug during traffic. A second true RS232 adapter/tester is needed for independent receive-data verification; no peer was attached during the hotplug test. Real ECP and all serial payload TX stay disabled. Exact panel/protocol documentation, supported export and installed Metasys capability work remain later gates.

# Resume remote Ethernet work

Read STATUS.md and ETHERNET_TEST_REPORT.md first. Board now runs **0.1.3** on PoE Ethernet at **10.0.7.195**, MAC `e8:f6:0a:e4:1f:e8`. USB-C is disconnected and unavailable. FTDI USB-A remains connected; panel wires remain disconnected. No physical change is needed for ordinary application updates.

Actual tests passed: signed upload/reboot/full-hash confirmation, automatic timeout rollback, invalid-signature/truncated/wrong-project rejection, interrupted upload, independent BACnet RP/RPM, and persisted diagnostic replay with an explicit overflow gap. The 0.1.2 hash-reporting defect was corrected in 0.1.3. Do not reinstall 0.1.2 as a working release.

```sh
.venv/bin/python tools/gateway_client.py --host 10.0.7.195 status
.venv/bin/python tools/gateway_client.py --host 10.0.7.195 upload release/0.1.3/est3_gateway_rxonly.bin
```

The updater signs locally, verifies the device certificate, checks all 64 ELF hash characters after reboot and explicitly confirms the new slot. Keep signing credentials and binaries private. Do not change bootloader/partition layout remotely. `--no-confirm` deliberately tests rollback and should be used only for a defined disconnected bench test.

The current address is a DHCP lease. Rediscover with `tools/discover.py --broadcast 10.0.7.255` if needed; verify the Mac remains on that subnet first. Discovery uses Device 3899000. Future access from a different site/network requires routing or an authorized remote-access arrangement; none has been configured here.

The temporary diagnostics host is running on `https://10.0.7.6:8443`, using `private/hardware-bench.sqlite`, bound specifically to the Mac LAN address. It was launched with `EST3_BIND=10.0.7.6`, `EST3_GATEWAY_ID=P4-e8f60ae41fe8`, and `tools/run_host.py`. Process 70385 was the initial launch; check the current process before stopping it. It is not installed as a persistent service. Live log `evidence/hardware-host.log` is excluded from Git; a fixed session snapshot is retained. The board queues diagnostics if the host stops. Do not mix this database with SIMULATION_ONLY data.

An idle physical USB-A unplug/replug test also passed: reconnect count increased from 1 to 2 with no reboot or new USB errors; BACnet reads remained available. Evidence is in `adapter-hotplug-result.json` and `adapter-hotplug-bacnet.json`.

Remaining work: extended mixed-load soak, physical PoE VBUS/RS232 measurements, independent TX capture, actual binary receive traffic and hotplug during traffic. A second true RS232 adapter/tester is needed for independent receive-data verification; no peer was attached during the hotplug test. Real ECP and all serial payload TX stay disabled. Exact panel/protocol documentation, supported export and installed Metasys capability work remain later gates.

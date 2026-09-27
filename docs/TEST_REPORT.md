# First-draft test report — 2026-09-27

## Executed software tests

| Group | Result | Scope |
|---|---|---|
| `test_host.py` | 23 passed | Independent conditions; heartbeat/stale handling; retry/gap recovery; epochs; identity reconciliation; quarantine/tombstones; migrations/backup; roles/escaping; dry-run idempotence |
| `test_bacnet.py` | 1 passed | Independent BACpypes3 against shared C stack/port on localhost; discovery, RP/RPM, indexed objects/errors, advertised services, control rejection, concurrent states, rename and stale quality |
| `test_stress.py` | 1 passed | 1,000 devices, 5,005 objects; indexed last-object access and bounded oversized-list response |
| Native C test | 1 passed | Registry bounds/collisions, simulation rejection, startup/state/freshness/epochs, every fixture truncation and 10,000 pseudorandom inputs under ASan/UBSan |
| Deterministic demo | Passed | `evidence/demo-01/`: two-device alarm/trouble/restore, rename/add, address-reuse quarantine, gap, dry-run proposals and SQLite backup |
| Production build | Passed | IDF v5.5.5, esp32p4 pre-v3 range 1.0–1.99; 0.1.2 app 932,160 bytes; two 5 MiB slots |
| Production separation | Passed, software scope | Production rejects simulation registry; linked ELF lacks `gw_observe` and `cdc_acm_host_data_tx_blocking`; no serial-write route/ECP implementation |

Latest pytest: **25 passed in 2.76 s**, one dependency deprecation warning about Starlette TestClient/HTTPX. Native CTest: **1/1 passed**. Actual output: `evidence/software-tests.log`, `evidence/core-tests.log`. Native network tests use loopback and a distinct SIMULATION_ONLY Device identity.

The same neutral simulated observations reach the authenticated host telemetry API and C simulator. Both show simultaneous alarm/trouble and independent restore. Host API uses FastAPI TestClient; this does not exercise TLS or MCU outbox delivery. Complete host snapshots combine all applicable conditions. This is application integration evidence, not EST wire-protocol evidence.

Development failures were corrected before the passing run: BACnet discovery response routing, backlog observation age, and an incomplete snapshot in the integration test harness. Latest logs document final results, not formal protocol certification.

## Actual USB evidence

Original complete flash backup: `evidence/original-flash.bin`, 32 MiB, private. SHA-256 `1b4cfc24426ad0f3e630e82d3ed1874ac4bfb6ba565f408e8a45cbde0fe80b20`. Original demo output: `evidence/original-runtime.log`.

Gateway installation and 0.1.1 application upgrade completed with esptool data-hash verification (`first-flash.log`, `usb-upgrade-0.1.1.log`). Observed P4 revision 1.3, 32 MB flash and 32 MB PSRAM; PSRAM initialization/self-test passed.

FTDI VID `0403`, PID `6001`, bcdDevice `0600`, product `USB-RS232-WE-1800-BT-5.0`, serial `ABBAWJDO`; IN `0x81`, OUT `0x02`, MPS 64. Driver accepted requested 19200/8N1, DTR/RTS deasserted, zero-sized OUT buffer. Programming bridge is separate `1a86:55d3`.

The 180-second 0.1.1 capture reports stable post-enumeration free heap 33,227,475 bytes; minimum 33,194,648 bytes. RX/drop/USB-error/line-error counters stayed zero. No external peer existed: zero RX proves no traffic-integrity claim. No spontaneous reset observed; console/flashing resets were intentional.

## Not executed

Ethernet/PoE operation, HTTPS update/confirmation/rollback, device invalid-image handling, host delivery/replay, electrical levels, VBUS load, independent baud/zero-TX capture, binary packet RX, physical hotplug, overload, brownout, mixed load, full-day soak, real ECP, genuine contractor exports and installed Metasys commissioning.

Inherited acceptance rows remain NOT_RUN when their full procedure or specified evidence tier was not satisfied. Partial simulation/software observations are recorded without promoting them to contractor, hardware or site passes. Software test count is distinct from acceptance-gate count.

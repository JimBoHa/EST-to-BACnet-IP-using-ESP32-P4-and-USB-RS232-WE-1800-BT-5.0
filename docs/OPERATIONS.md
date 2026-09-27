# Bench operations and recovery

1. Keep EST absent during all current software, update, invalid-request and transport testing.
2. Preserve `private/`, original-flash backup/checksum, host SQLite backups, registry and known-good app image separately. Do not publish credentials or firmware binaries.
3. Initial USB-C flashing has a verified complete original flash backup. Full original restoration is a recovery action only: use esptool with the correct P4/32 MB target and write the backup at address zero. This restores the former Waveshare demo and replaces all current gateway storage. Do not do this during ordinary upgrades.
4. Normal upgrades use the signed HTTPS uploader and unchanged partition table. Validate target identity, registry epoch, zero serial-payload-TX capability and new version after boot. Awaiting-confirmation must become false. Test timeout rollback and interrupted upload on the disconnected bench before remote-only use.
5. If a new app fails to boot or remains unconfirmed, bootloader/application rollback selects the previous valid slot. If the bootloader/partition layout itself is damaged, use USB recovery; OTA cannot repair those layers in this draft.
6. Export host registry and use SQLite's backup API. Restore to an isolated instance and verify IDs before replacing a device. Do not run two gateways with the same Device instance on the live BACnet network.

The compact registry is durable NVS state. Failed/corrupt identity storage reports a fault rather than generating new IDs. Identical registry-upload retries succeed without allocating again. New or changed bindings invalidate source state; label-only edits preserve unchanged binding epochs and observations. Tombstones cannot be omitted or renumbered.

The diagnostics journal is a bounded durable session stream, not an EST event recorder. On host failure, BACnet and USB tasks continue independently. TLS trust/time/authentication failures retain pending records. Records dropped before any transmission become explicit sequence gaps. Cold restart uses the same journal stream and emits a GATEWAY_BOOT diagnostic; host invalidates cached conditions. Event capture during power loss is not established without a verified ECP source.

PoE-only USB VBUS under load and RS232 levels need actual instruments. The schematic shows PoE VCC_5V feeding the USB power switch; an enumeration success does not measure voltage margin. Owner removed USB-C and applied PoE; Ethernet services and FTDI enumeration worked. Neither concurrent power behavior nor cable isolation is claimed as measured. Signed application update and automatic timeout rollback have been observed without USB; see [ETHERNET_TEST_REPORT.md](ETHERNET_TEST_REPORT.md).

Before a field pilot, resolve every mandatory test gate with responsible site/contractor owners. Remote updates working does not itself establish EST protocol support, electrical compatibility or operational readiness.

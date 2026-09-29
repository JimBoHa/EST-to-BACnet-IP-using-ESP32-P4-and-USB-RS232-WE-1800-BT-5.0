# BACnet support statement — development profile, not BTL certified

Stack: bacnet-stack 1.5.2, commit d2468d56de3d156659a9051c95119e3a6e11c421. BACnet/IPv4, UDP 47808, local subnet. No BBMD/foreign-device registration, routing, segmentation, intrinsic life-safety event reporting, or BACnet/SC.

- Services: Who-Is with unicast I-Am reply, ReadProperty, ReadPropertyMultiple. ServicesSupported is generated from the installed read handlers.
- Unsupported confirmed services, including WriteProperty/Multiple, alarm acknowledgement, DCC, reinitialization, create/delete and file operations receive Reject/unrecognized-service. Unimplemented unconfirmed services (including time synchronization) are ignored. No control service is registered.
- Device object; BI 1 validated current-state decoder available (false), BI 2 converter connected, BI 3 registry loaded, BI 4 all active source conditions valid. Converter connection does not mean panel communication.
- Each known logical point reserves five immutable instances for alarm, trouble, supervisory, disabled and DataValid. Unsupported conditions are exposed with communication-failure reliability; they are not verified inactive. Condition BIs retain their last value when stale, with fault/reliability indication. DataValid becomes inactive.
- Startup conditions are unknown. A loaded catalog, healthy heartbeat or USB link does not establish normal detector states. Retirement preserves objects with invalid condition quality.
- Stable technical names are the stack's `BINARY INPUT <instance>` names. Description carries the source label, bounded to 191 UTF-8 bytes. The real SDU importer rejects oversized labels instead of silently truncating; original source stays private.
- Maximum application APDU 1476. Object_List supports index 0 (count), individual indices, and bounded all-elements reads. Large reads return a protocol abort instead of claiming segmentation.
- COV is not implemented or advertised; polling is required. Its subscription/lifetime/resource tests remain NOT_RUN.

Current bench Device instance: **3899000**. Native software simulator: **3899001**, bound only to localhost. Both are lab assignments; verify uniqueness before site commissioning. Vendor identifier **65535** and name `UNASSIGNED LAB ONLY` are an explicit bench placeholder, not a production vendor registration. Obtain the owner's assigned BACnet Vendor ID through ASHRAE and a site-approved Device instance before field commissioning. Do not use another manufacturer's identity.

The qualified SDU registry has 1,214 archive objects: 6,070 per-object BIs plus four
health BIs and Device, totaling 6,075 BACnet objects. The firmware allows 2,048
catalog entries, including tombstones; that ceiling is not a measured field load
rating. All four condition mappings for imported SDU objects remain unsupported,
with fault quality and DataValid inactive. No source observation reducer is linked
into this production release.

Independent BACpypes3 tests exercise the same C code compiled natively and the
actual P4 over Ethernet. See [STATUS.md](../STATUS.md) for the current hardware
checks and retained load-test failures. Installed Metasys commissioning is deferred
by the owner until automatic panel readings are reliable. No point or graphic
engineering has been performed in Metasys.

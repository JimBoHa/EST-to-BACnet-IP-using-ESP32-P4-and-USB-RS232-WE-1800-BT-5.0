# Printer trouble observations — 0.1.15

Updated 2026-10-03. The P4 now decodes the two trouble record formats actually
captured from the installed CPU 05.30: `LOCAL TRBL ACT/RST` and
`COMMON TRBL ACT/RST`. It matches qualified catalog addresses and exposes the
last printed action through the device's existing trouble BI. **Reliability
remains communication-failure, Status_Flags.fault remains set, and DataValid
remains inactive.** Neither ACT nor RST establishes a complete current state.

## Evidence and limits

Before OTA, confirmed 0.1.14 boot 31 held 869 UART bytes and 38 line records,
including one local trouble/restore pair at a backup power-supply pseudo point
and three common trouble/restore pairs at a physical module. USB/UART errors
and receive drops were zero. There was one initial stream boundary and no
record eviction. Raw captures and site identities remain private under
`private/communication-20261003/`.

The 512-byte diagnostic tail cannot contain all 869 bytes. The saved structured
line records contain all retained line content; their offsets and original
panel timestamps are preserved. The offline replay reconstructs CRLF framing
from those lines. It is not described as an independently captured full raw
869-byte file. The checked-in fixture changes addresses, labels and dates.

[Private-capture replay results](../evidence/printer-capture-replay-2026-10-03.json)
record all eight ACT/RST values read by independent BACpypes3 against the
production C parser, reducer and BACnet stack, using the actual private
1,214-object catalog. This ran on localhost, with no serial connection or
injection into the P4. It proves the implementation handles the captured
records, not that fresh events have arrived after deploying this decoder.

## Interpretation

The observed address is `Pnn Cnn Dnnnn`; it must exactly match a nonretired
qualified SDU record. Printed text is retained separately from the imported
label. No record creates, retires, renames or rebinds a catalog device. Unknown
addresses remain in diagnostics and increment an unmatched counter.

The trouble BI's Present_Value is the most recent accepted ACT/RST action,
not the aggregate of every possible trouble subtype. For example, restoring
one battery trouble does not prove the absence of another trouble. The decoder
does not set support bits or synchronization. Alarm, supervisory and disabled
conditions stay untouched and unverified. The four health BI meanings remain
unchanged; decoder/current-state health remains false.

The web directory labels these values `observation_only`, with event type,
panel time, receive uptime, age, source record ID, byte offset and stream epoch.
The diagnostics page shows the latest 32 structured observations alongside
the existing 128 raw records. These and per-device last observations are RAM
only and reset at reboot. No permanent host or flash event journal is needed.

## Framing, loss and replay

- Accept only blank/header/one printable description/blank framing, with exact
  header delimiters and fixed digit widths. Validate the calendar and clock.
  A frame must finish within five seconds of its header.
- Partial, extra-line, malformed, oversized or corrupt frames never update a
  device. Stream gaps discard pending frames. Unsupported record types remain
  raw; operator commands are not executed or used as device states.
- Known report markers inhibit trouble observations until the explicit report
  end. An interrupted report can leave this conservative inhibit active; the
  API exposes it. Unknown history formats cannot establish current quality
  even if their records have the same syntax.
- Older panel timestamps, repeated sequence IDs and duplicate same-time/type/
  action observations do not replace or refresh an accepted observation.
  Different actions in the same panel second follow receive order. A backward
  panel clock can cause later records to be ignored until its ordering catches
  up; raw records remain available. No panel timezone or UTC offset is inferred.
- Registry changes preserve observations only for an unchanged binding.
  Rebinding, support changes or retirement clear them. There is no production
  event injection endpoint and no serial payload TX.

## Remaining source requirements

Automatic records from two addresses do not prove coverage of every device,
condition, partition or routing filter. No initial-state snapshot, all-device
discovery, alarm/supervisory/disable grammar or live/history distinction has
been verified. Existing devices come from the qualified SDU backup, not serial
enumeration. Silent devices retain unknown condition quality.

The owner offered to add orange TX. Authorized preparation is orange adapter
TX to labeled panel RX2, leaving yellow RX on TX2 and black on COM2. At the last
explicit confirmation orange was disconnected and settings were unchanged;
finished wiring confirmation remains pending. Firmware transmission stays
compiled out. Other leads remain individually insulated, especially red power.

MSA's [EST3 ECP driver manual](https://assetlibrary.msasafety.com/m/31ef0005e95bcd13/original/Protocol-Driver-Manual-EST3-ECP-8700-39.pdf)
requires Gateway mode set with 3-SDU and describes Report/Delta services. It
does not supply the full wire framing, checksums and permitted handshake/read
messages needed to implement an independent client. It also does not establish
automatic enumeration of every device and label. Adding a return wire alone
does not resolve those requirements or establish a configuration query on the
unchanged printer port.

The next supported polling step needs a version-compatible EST3 ECP wire
specification or a licensed, documented implementation, plus access to the
current 3-SDU project to commission the chosen port. Read/handshake frames must
be validated on an isolated peer before use on this panel. No guessed command,
port reprogramming, panel control or staged fire event was attempted. The owner
previously reported panel access only, without an SDU computer or technician;
that external prerequisite remains unresolved.

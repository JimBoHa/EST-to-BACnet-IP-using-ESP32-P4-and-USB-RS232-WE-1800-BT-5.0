# Receive-only serial diagnostics

**0.1.15 update:** `/api/v1/printer` profile is `est3_printer_observations_v2`, with 32 structured trouble observations plus 128 raw lines. [Trouble observation semantics](PRINTER_TROUBLE_OBSERVATIONS.md) describe mapping and quality. Serial payload TX remains disabled.

Firmware 0.1.4 adds authenticated diagnostics for the FT232 at USB VID/PID `0403:6001`, interface 0. The gateway still has no serial payload transmitter or ECP parser. The pinned FTDI/CDC dependency sources remain unchanged.

## What is measured

A linker wrapper observes each MPS-sized USB IN packet before the FTDI driver strips its two status bytes, then calls the original callback with its original context. A two-byte status-only transfer is counted as USB traffic, never as panel payload. Separate counters track malformed packets, UART error status, payload bytes, application receive bytes and drops. The observer retains the latest 512 payload bytes in a ring.

`GET /api/v1/serial` requires the same pinned TLS connection and bearer credential as other management routes. Its response contains:

- USB attachment, boot count, requested/applied baud, configuration error and baud epoch.
- USB packet/status-only/error counters and the latest raw FTDI modem/line status.
- Payload/application byte counters, drops and last packet/payload uptime.
- Capture epoch, global starting byte offset, count and hexadecimal payload.

This is a diagnostic tail, not a durable or lossless event stream. Polls can miss bytes when more than 512 arrive between requests. Detect gaps from capture offsets; do not concatenate overlapping snapshots blindly. Baud changes clear the capture and increment its epoch while preserving lifetime counters. Reboots reset counters; counters are 32-bit. Raw payload may contain site information and must remain private.

## Receiver settings

Authenticated `POST /api/v1/serial` accepts a single integer field, for example `{"baud":9600}`. Allowed rates are 1200, 2400, 4800, 9600, 19200, 38400, 57600 and 115200. The response is `202 Accepted`; poll until both `baud` and `requested_baud` match and `configuration_error` is zero. The connector task applies settings using its own USB handle, avoiding cross-task close/configuration races.

In **0.1.5 the boot default is 9600**, validated against actual Printer 2 revision reports. Version 0.1.4 instead boots at 19200. API overrides remain volatile and return to the build's default on reboot. Format remains 8N1, flow control disabled, DTR/RTS deasserted. Unsupported rates, fractional values and additional fields are rejected. No request field enables payload transmission or panel commands. Changing the receiver baud does not reprogram the panel.

The pinned Espressif FTDI 2.1.1 source uses request `0x02` and masks `0x10`/`0x20` for modem outputs. FTDI SIO defines modem control as request `0x01`, with DTR/RTS update masks `0x0100`/`0x0200`; request `0x02` selects flow control. The application bypasses that driver method with explicit control requests to disable flow and separately deassert DTR and RTS. Sources: [Espressif FTDI component source](https://github.com/espressif/esp-usb/blob/master/host/class/cdc/usb_host_ftdi_vcp/usb_host_ftdi_vcp.c), [Linux FTDI SIO definitions](https://github.com/torvalds/linux/blob/master/drivers/usb/serial/ftdi_sio.h). This corrects a source-level defect; it did not by itself produce received panel data.

## Bounded passive checks

```sh
.venv/bin/python tools/diagnose_serial.py \
  --host 192.168.75.157 --rates 19200 9600 --seconds 30 \
  --raw-output private/serial-diagnostics-new.json \
  --summary-output evidence/serial-diagnostics-new.json
```

The helper verifies the device certificate before sending credentials, checks boot/connection state, changes only receiver baud, and attempts to restore the original baud in `finally`. Full samples are restricted to `private/`; the public summary omits payload. If restoration fails, the tool reports failure; read back settings before assuming the receiver was restored. One-second samples are intended for counters and diagnostic tails, not complete report capture.

The first 0.1.4 field check observed 1,896 status-only packets at each rate over 30 seconds, zero payload and no new errors/drops. This establishes functioning USB IN transfers while the panel was quiet, not electrical receive accuracy. Later front-panel report tests are recorded in [the field log](FIELD_CONNECTION_TEST.md).

Native ASan/UBSan tests cover invalid packet lengths, status-prefix separation, all byte values, ring wrap, ordered tails and capture reset. Live API checks rejected invalid baud, a fractional baud, an added transmit field and an invalid token while preserving boot/baud. Firmware build, symbol audit, signed field OTA, full-hash confirmation and independent BACnet reads also passed. See the versioned 0.1.4 evidence files.

## Requesting a panel report

Edwards' [EST3 System Operation Manual, 270382-EN R012, printed page 35](https://alarmspec.com/wp-content/uploads/2025/12/270382-EN-R012-EST3-System-Operation-Manual-1.pdf#page=42) documents this read-only test:

1. Press **Command Menus** and choose **Report** (also called Reports).
2. Choose **Revision Levels**.
3. Enter the target panel's two-digit address. The inspected local backup identifies the main cabinet as **01**; this is backup evidence, not an independently read live address.
4. Send the report to **Printer 2**, corresponding to the attached Port 2.

This requests report output without changing panel programming. Record the selected destination and receiver settings before interpreting the resulting bytes. A report is evidence of report reception only; real-time event coverage, inventory completeness and ECP operation require separate validation.

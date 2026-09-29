#include "serial_diagnostics.h"

bool serial_baud_supported(uint32_t baud) {
    switch (baud) {
    case 1200: case 2400: case 4800: case 9600: case 19200:
    case 38400: case 57600: case 115200: return true;
    default: return false;
    }
}

void serial_diagnostics_feed(serial_diagnostics *d, const uint8_t *packet,
                             size_t length, uint64_t now_ms) {
    d->packets++;
    d->last_packet_ms = now_ms;
    /* FT232 full-speed, one max-packet-size transfer, two status bytes. */
    if (!packet || length < 2 || length > 64) {
        d->invalid_packets++;
        return;
    }
    d->modem_status = packet[0];
    d->line_status = packet[1];
    if (packet[1] & 0x1e) d->error_packets++;
    if (length == 2) {
        d->status_only_packets++;
        return;
    }
    d->last_payload_ms = now_ms;
    d->payload_bytes += (uint32_t)(length - 2);
    for (size_t i = 2; i < length; i++) {
        d->capture[d->capture_next] = packet[i];
        d->capture_next = (d->capture_next + 1) % SERIAL_CAPTURE_CAPACITY;
        if (d->capture_count < SERIAL_CAPTURE_CAPACITY) d->capture_count++;
    }
}

void serial_diagnostics_clear_capture(serial_diagnostics *d) {
    d->capture_count = d->capture_next = 0;
    d->capture_epoch++;
}

size_t serial_diagnostics_payload(const serial_diagnostics *d, uint8_t *out,
                                 size_t capacity) {
    size_t n = d->capture_count < capacity ? d->capture_count : capacity;
    size_t start = (d->capture_next + SERIAL_CAPTURE_CAPACITY - n) % SERIAL_CAPTURE_CAPACITY;
    for (size_t i = 0; i < n; i++) out[i] = d->capture[(start + i) % SERIAL_CAPTURE_CAPACITY];
    return n;
}

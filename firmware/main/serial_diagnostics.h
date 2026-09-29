#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define SERIAL_CAPTURE_CAPACITY 512

/* USB status is not panel payload. Keep those observations separate. */
typedef struct {
    uint32_t packets, status_only_packets, invalid_packets, error_packets;
    uint32_t payload_bytes, capture_count, capture_next, capture_epoch;
    uint8_t modem_status, line_status;
    uint64_t last_packet_ms, last_payload_ms;
    uint8_t capture[SERIAL_CAPTURE_CAPACITY];
} serial_diagnostics;

bool serial_baud_supported(uint32_t baud);
void serial_diagnostics_feed(serial_diagnostics *d, const uint8_t *packet,
                             size_t length, uint64_t now_ms);
void serial_diagnostics_clear_capture(serial_diagnostics *d);
size_t serial_diagnostics_payload(const serial_diagnostics *d, uint8_t *out,
                                 size_t capacity);

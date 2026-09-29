#pragma once
#include "printer.h"
#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
#include "serial_diagnostics.h"
typedef struct {
    bool connected;
    uint32_t connects,bytes,chunks,drops,errors,line_errors,crc32;
    uint32_t baud, requested_baud, baud_epoch;
    esp_err_t configuration_error;
} serial_stats;
esp_err_t serial_rx_start(void);
serial_stats serial_rx_stats(void);
void serial_rx_diagnostics(serial_stats *s, serial_diagnostics *d);
esp_err_t serial_rx_set_baud(uint32_t baud);
bool serial_rx_printer_copy(pr_parser *out);

#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
typedef struct { bool connected; uint32_t connects,bytes,chunks,drops,errors,line_errors,crc32; } serial_stats;
esp_err_t serial_rx_start(void);
serial_stats serial_rx_stats(void);

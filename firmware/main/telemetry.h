#pragma once
#include "esp_err.h"
#include <stdbool.h>
#include <stdint.h>
esp_err_t telemetry_start(void);
esp_err_t telemetry_set_url(const char *url);
void telemetry_stats(uint32_t *queued,uint32_t *dropped,bool *storage_ok);

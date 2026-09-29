#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define GW_MAX_DEVICES 2048
#define GW_MAX_JSON (1024*1024)
#define GW_STALE_MS 60000
#define GW_SERIAL_PAYLOAD_TX_ENABLED 0
#define GW_ECP_ENABLED 0

typedef struct {
    bool known, value, synchronized;
    uint64_t observed_ms, sequence;
} gw_condition;
typedef struct {
    char uuid[37], address[256], type[64], label[192];
    uint32_t binding_epoch, instances[5];
    uint8_t supported;
    bool retired;
    gw_condition conditions[4];
} gw_device;
typedef struct {
    uint32_t epoch;
    size_t count;
    bool simulation;
    char source_hash[65], source_quality[64];
    gw_device devices[GW_MAX_DEVICES];
} gw_registry;

bool gw_parse_registry(const char *json, size_t size, const gw_registry *old,
                       bool allow_simulation, gw_registry *out, char *error, size_t error_size);
bool gw_condition_valid(const gw_device *d, unsigned kind, uint64_t now);
bool gw_data_valid(const gw_device *d, uint64_t now);
void gw_invalidate(gw_registry *r);
bool gw_observe(gw_device *d, uint32_t epoch, unsigned kind, bool value,
                uint64_t now, uint64_t sequence, bool snapshot);

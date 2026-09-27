#pragma once
#include "gateway.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "esp_err.h"
extern SemaphoreHandle_t runtime_lock;
extern gw_registry *runtime_registry;
extern bool runtime_network_ready, runtime_registry_ok, runtime_services_ready;
extern char runtime_ip[16];
extern uint32_t runtime_boot_count;
esp_err_t management_start(void);
esp_err_t registry_apply(const char *data,size_t size,char *error,size_t capacity);
void management_rollback_check(void);

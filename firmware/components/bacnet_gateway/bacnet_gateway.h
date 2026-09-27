#pragma once
#include "gateway.h"
bool bg_start(uint32_t device_instance, const char *bind_ip, uint16_t port, const char *broadcast_ip);
void bg_configure_address(const char *ip, const char *broadcast_ip);
bool bg_registry(gw_registry *registry);
void bg_poll(unsigned timeout_ms, bool usb_connected);
uint64_t bg_now(void);

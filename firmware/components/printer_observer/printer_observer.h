#pragma once
#include "gateway.h"
#include "printer.h"
/* Caller holds the registry lock. No discovery, bindings or support bits change. */
pr_event_result gw_record_printer_trouble(void *registry, const pr_event *event);

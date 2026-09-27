idf_component_register(SRCS "app_main.c" "serial_rx.c" "management.c" "telemetry.c" INCLUDE_DIRS "." "../../private" REQUIRES esp_eth esp_netif nvs_flash usb app_update esp_https_server esp_http_client json gateway_core bacnet_gateway esp_timer esp_psram espressif__usb_host_ftdi_vcp)
idf_build_set_property(LINK_OPTIONS "-Wl,--wrap=cdc_acm_host_data_tx_blocking" APPEND)
idf_component_get_property(json_library json COMPONENT_LIB)
target_compile_definitions(${json_library} PRIVATE CJSON_NESTING_LIMIT=16)

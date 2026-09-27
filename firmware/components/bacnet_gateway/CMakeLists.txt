set(BACNET_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../third_party/bacnet-stack/src")
include("${CMAKE_CURRENT_LIST_DIR}/sources.cmake")
idf_component_register(SRCS ${BACNET_SOURCES} "bacnet_port.c" "bacnet_gateway.c" INCLUDE_DIRS "." "${BACNET_ROOT}" REQUIRES gateway_core lwip esp_timer)
target_compile_definitions(${COMPONENT_LIB} PUBLIC BACDL_BIP BACAPP_ALL BACNET_PROTOCOL_REVISION=16 CONFIG_BACNET_BASIC_OBJECT_BINARY_INPUT MAX_APDU=1476 MAX_TSM_TRANSACTIONS=4 PRINT_ENABLED=0 BACNET_VENDOR_ID=65535)

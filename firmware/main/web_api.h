#pragma once
#include "esp_http_server.h"
#include <stdbool.h>
bool management_authorized(httpd_req_t *request);
esp_err_t web_register(httpd_handle_t server);

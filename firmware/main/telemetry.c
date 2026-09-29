/* The owner requires a standalone controller, not a permanent history host.
 * Retain old journal bytes for rollback; never enqueue, deliver, erase or migrate.
 */
#include "telemetry.h"
#include "nvs_flash.h"
#include "nvs.h"
#include <stdint.h>
#include <stdlib.h>

typedef struct {
    uint32_t version,count;
    uint64_t next,missing_start,missing_end;
    uint32_t dropped;
    char session[33];
    char records[32][640];
} legacy_outbox;
static uint32_t retained_count,retained_drops;
static bool legacy_ok=true;
void telemetry_stats(uint32_t *queued,uint32_t *dropped,bool *ok) {
    *queued=retained_count;*dropped=retained_drops;*ok=legacy_ok;
}
esp_err_t telemetry_set_url(const char *url) {(void)url;return ESP_ERR_NOT_SUPPORTED;}
esp_err_t telemetry_start(void) {
    esp_err_t err=nvs_flash_init_partition("journal");
    if(err!=ESP_OK){legacy_ok=false;return ESP_OK;}
    nvs_handle_t handle;
    err=nvs_open_from_partition("journal","est3_outbox",NVS_READONLY,&handle);
    if(err==ESP_ERR_NVS_NOT_FOUND)return ESP_OK;
    if(err!=ESP_OK){legacy_ok=false;return ESP_OK;}
    legacy_outbox *box=calloc(1,sizeof(*box));
    if(!box){nvs_close(handle);legacy_ok=false;return ESP_OK;}
    size_t length=sizeof(*box);err=nvs_get_blob(handle,"outbox",box,&length);
    if(err==ESP_OK&&length==sizeof(*box)&&box->version==1&&box->count<=32) {
        retained_count=box->count;retained_drops=box->dropped;
    } else legacy_ok=err==ESP_ERR_NVS_NOT_FOUND;
    free(box);nvs_close(handle);return ESP_OK;
}

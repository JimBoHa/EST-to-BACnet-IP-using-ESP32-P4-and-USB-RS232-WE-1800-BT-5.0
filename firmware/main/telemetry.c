/* Durable bounded diagnostics outbox. No ECP events are invented. */
#include "runtime.h"
#include "telemetry.h"
#include "serial_rx.h"
#include "provision.h"
#include "esp_http_client.h"
#include "esp_random.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "cJSON.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>

#define CAPACITY 32
#define RECORD_SIZE 640
typedef struct {uint32_t version,count;uint64_t next,missing_start,missing_end;uint32_t dropped;char session[33];char records[CAPACITY][RECORD_SIZE];} outbox;
static outbox *box;
static nvs_handle_t storage;
static SemaphoreHandle_t mutex;
static bool storage_ok;
static const char *TAG="telemetry";
static char host_url[256];
static esp_err_t commit(void) {
    esp_err_t ret=nvs_set_blob(storage,"outbox",box,sizeof(*box));if(ret==ESP_OK)ret=nvs_commit(storage);
    if(ret!=ESP_OK){storage_ok=false;ESP_LOGE(TAG,"Outbox commit failed; telemetry halted to avoid unrecorded loss");}
    return ret;
}
void telemetry_stats(uint32_t *queued,uint32_t *dropped,bool *ok) {
    if(!mutex){*queued=0;*dropped=0;*ok=false;return;}
    xSemaphoreTake(mutex,portMAX_DELAY);*queued=box?box->count:0;*dropped=box?box->dropped:0;*ok=storage_ok;xSemaphoreGive(mutex);
}
esp_err_t telemetry_set_url(const char *url) {
    if(!mutex||!url||strlen(url)>=sizeof(host_url)||strncmp(url,"https://",8)||strchr(url,'@')||strchr(url,'\r')||strchr(url,'\n'))return ESP_ERR_INVALID_ARG;
    const char *path=strchr(url+8,'/');if(!path||strcmp(path,"/api/v1/telemetry"))return ESP_ERR_INVALID_ARG;
    xSemaphoreTake(mutex,portMAX_DELAY);
    esp_err_t err=nvs_set_str(storage,"host_url",url);if(err==ESP_OK)err=nvs_commit(storage);
    if(err==ESP_OK)strcpy(host_url,url);
    xSemaphoreGive(mutex);return err;
}
static void enqueue_diagnostic(const char *code) {
    if(!storage_ok)return;
    xSemaphoreTake(mutex,portMAX_DELAY);
    if(box->missing_start && box->count<CAPACITY) {
        snprintf(box->records[box->count++],RECORD_SIZE,"{\"sequence\":%llu,\"record_type\":\"history_gap\",\"missing_sequence_start\":%llu,\"missing_sequence_end\":%llu,\"reason\":\"bounded diagnostics outbox overflow; current state requires resynchronization\"}",(unsigned long long)box->next++,(unsigned long long)box->missing_start,(unsigned long long)box->missing_end);
        box->missing_start=box->missing_end=0;
    }
    uint64_t sequence=box->next++;
    if(box->count==CAPACITY) {
        if(!box->missing_start)box->missing_start=sequence;
        box->missing_end=sequence;box->dropped++;
    } else {
        serial_stats s=serial_rx_stats();
        snprintf(box->records[box->count++],RECORD_SIZE,"{\"sequence\":%llu,\"record_type\":\"diagnostic\",\"raw_source_code\":\"%s\",\"monotonic_ms\":%llu,\"reason\":\"ECP disabled; boot=%lu USB=%u RX=%lu drops=%lu errors=%lu\"}",(unsigned long long)sequence,code,(unsigned long long)(esp_timer_get_time()/1000),(unsigned long)runtime_boot_count,s.connected,(unsigned long)s.bytes,(unsigned long)s.drops,(unsigned long)s.errors);
    }
    commit();xSemaphoreGive(mutex);
}
static void deliver(void) {
    if(!storage_ok||!runtime_network_ready||time(NULL)<1700000000)return;
    char url[256],record[RECORD_SIZE],session[33];uint64_t sequence=0;
    xSemaphoreTake(mutex,portMAX_DELAY);
    if(!box->count||!host_url[0]){xSemaphoreGive(mutex);return;}
    strcpy(url,host_url);strcpy(record,box->records[0]);strcpy(session,box->session);xSemaphoreGive(mutex);
    cJSON *r=cJSON_Parse(record);if(!r)return;
    sequence=cJSON_GetObjectItem(r,"sequence")->valuedouble;cJSON_Delete(r);
    char body[1000];snprintf(body,sizeof(body),"{\"schema_version\":1,\"gateway_id\":\"P4-e8f60ae41fe8\",\"boot_id\":\"%s\",\"source_mode\":\"protocol_disabled\",\"records\":[%s]}",session,record);
    esp_http_client_config_t config={.url=url,.cert_pem=HOST_CERT,.common_name="est3-host.local",.timeout_ms=4000,.buffer_size=1024,.buffer_size_tx=1536,.disable_auto_redirect=true};
    esp_http_client_handle_t client=esp_http_client_init(&config);if(!client)return;
    char auth[80];snprintf(auth,sizeof(auth),"Bearer %s",HOST_TOKEN);
    esp_http_client_set_method(client,HTTP_METHOD_POST);esp_http_client_set_header(client,"Authorization",auth);esp_http_client_set_header(client,"Content-Type","application/json");
    esp_err_t err=esp_http_client_open(client,strlen(body));bool accepted=false;
    if(err==ESP_OK) {
        int sent=esp_http_client_write(client,body,strlen(body));
        if(sent==(int)strlen(body) && esp_http_client_fetch_headers(client)>=0 && esp_http_client_get_status_code(client)==200) {
            char response[512];int n=esp_http_client_read_response(client,response,sizeof(response)-1);
            if(n>0) {
                response[n]=0;cJSON *ack=cJSON_Parse(response);cJSON *value=cJSON_GetObjectItem(ack,"ack"),*boot=cJSON_GetObjectItem(ack,"boot_id"),*gw=cJSON_GetObjectItem(ack,"gateway_id");
                accepted=cJSON_IsNumber(value)&&value->valuedouble>=sequence&&cJSON_IsString(boot)&&!strcmp(boot->valuestring,session)&&cJSON_IsString(gw)&&!strcmp(gw->valuestring,"P4-e8f60ae41fe8");cJSON_Delete(ack);
            }
        }
    }
    esp_http_client_close(client);esp_http_client_cleanup(client);
    if(accepted) {
        xSemaphoreTake(mutex,portMAX_DELAY);
        memmove(box->records,box->records+1,(box->count-1)*RECORD_SIZE);box->count--;commit();
        xSemaphoreGive(mutex);
    }
}
static void task(void *unused) {
    (void)unused;enqueue_diagnostic("GATEWAY_BOOT");uint64_t last=esp_timer_get_time();
    for(;;) {
        if(esp_timer_get_time()-last>60000000){enqueue_diagnostic("GATEWAY_HEALTH");last=esp_timer_get_time();}
        deliver();vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
esp_err_t telemetry_start(void) {
    mutex=xSemaphoreCreateMutex();box=calloc(1,sizeof(*box));if(!mutex||!box)return ESP_ERR_NO_MEM;
    esp_err_t err=nvs_flash_init_partition("journal");if(err!=ESP_OK)return err;
    err=nvs_open_from_partition("journal","est3_outbox",NVS_READWRITE,&storage);if(err!=ESP_OK)return err;
    size_t len=sizeof(*box);err=nvs_get_blob(storage,"outbox",box,&len);
    if(err==ESP_ERR_NVS_NOT_FOUND) {
        box->version=1;box->next=1;snprintf(box->session,sizeof(box->session),"%08lx%08lx%08lx%08lx",(unsigned long)esp_random(),(unsigned long)esp_random(),(unsigned long)esp_random(),(unsigned long)esp_random());
        storage_ok=true;err=commit();
    } else storage_ok=err==ESP_OK&&len==sizeof(*box)&&box->version==1&&box->count<=CAPACITY&&box->session[32]==0&&box->next>0&&box->next<9007199254740991ULL;
    if(!storage_ok)return ESP_ERR_INVALID_STATE;
    len=sizeof(host_url);nvs_get_str(storage,"host_url",host_url,&len);
    return xTaskCreate(task,"telemetry",12288,NULL,3,NULL)==pdPASS?ESP_OK:ESP_ERR_NO_MEM;
}

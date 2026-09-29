#include "runtime.h"
#include "serial_rx.h"
#include "telemetry.h"
#include "esp_netif_sntp.h"
#include "bacnet_gateway.h"
#include "esp_eth.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_log.h"
#include "esp_chip_info.h"
#include "esp_app_desc.h"
#include "esp_psram.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "mdns.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
SemaphoreHandle_t runtime_lock;
gw_registry *runtime_registry;
bool runtime_network_ready, runtime_registry_ok, runtime_services_ready;
char runtime_ip[16]="0.0.0.0";
uint32_t runtime_boot_count;
static bool bacnet_started;
static bool ntp_started;
static bool mdns_started;
static const char *TAG="gateway";
static nvs_handle_t registry_nvs;
/* Old firmware must still load its old registry after application rollback. */
static const char *registry_key="catalog_v2";
const char *volatile runtime_startup_phase="boot";
/* Publish startup progress without writing diagnostic history to flash. */
static void startup_phase(const char *name) {
    runtime_startup_phase=name;ESP_LOGI(TAG,"Startup: %s",name);
}
char *registry_export(size_t *size) {
    char *result=NULL;*size=0;
    xSemaphoreTake(runtime_lock,portMAX_DELAY);
    if(runtime_registry_ok&&nvs_get_blob(registry_nvs,registry_key,NULL,size)==ESP_OK&&*size<=GW_MAX_JSON) {
        result=malloc(*size+1);
        if(result&&nvs_get_blob(registry_nvs,registry_key,result,size)!=ESP_OK){free(result);result=NULL;}
        if(result)result[*size]=0;
    }
    xSemaphoreGive(runtime_lock);return result;
}
esp_err_t registry_apply(const char *data,size_t size,char *error,size_t capacity) {
    gw_registry *next=calloc(1,sizeof(*next));if(!next){snprintf(error,capacity,"No memory");return ESP_ERR_NO_MEM;}
    xSemaphoreTake(runtime_lock,portMAX_DELAY);
    size_t stored_size=0;
    if(runtime_registry_ok && nvs_get_blob(registry_nvs,registry_key,NULL,&stored_size)==ESP_OK && stored_size==size) {
        char *saved=malloc(size);
        bool same=saved&&nvs_get_blob(registry_nvs,registry_key,saved,&stored_size)==ESP_OK&&!memcmp(saved,data,size);
        free(saved);
        if(same){xSemaphoreGive(runtime_lock);free(next);return ESP_OK;}
    }
    bool valid=runtime_registry_ok&&gw_parse_registry(data,size,runtime_registry,false,next,error,capacity);
    esp_err_t err=ESP_ERR_INVALID_ARG;
    if(valid) {
        err=nvs_set_blob(registry_nvs,"catalog_v2",data,size);
        if(err==ESP_OK)err=nvs_commit(registry_nvs);
        if(err==ESP_OK) {
            registry_key="catalog_v2";
            gw_registry *previous=runtime_registry;
            if(bacnet_started&&!bg_registry(next)) {runtime_registry_ok=false;ESP_LOGE(TAG,"Object allocation failed after commit; reboot to recover");esp_restart();}
            runtime_registry=next;next=NULL;free(previous);
        } else snprintf(error,capacity,"Registry durable commit failed");
    } else if(!runtime_registry_ok) snprintf(error,capacity,"Registry storage invalid");
    xSemaphoreGive(runtime_lock);free(next);return err;
}
static bool registry_load(gw_registry *next) {
    startup_phase("registry_nvs_init");
    esp_err_t err=nvs_flash_init_partition("registry");
    if(err!=ESP_OK){ESP_LOGE(TAG,"Registry NVS invalid: %s; identities will not be reallocated",esp_err_to_name(err));return false;}
    startup_phase("registry_nvs_open");
    err=nvs_open_from_partition("registry","est3_registry",NVS_READWRITE,&registry_nvs);if(err!=ESP_OK)return false;
    size_t size=0;err=nvs_get_blob(registry_nvs,registry_key,NULL,&size);
    if(err==ESP_ERR_NVS_NOT_FOUND) {registry_key="catalog";err=nvs_get_blob(registry_nvs,registry_key,NULL,&size);}
    if(err==ESP_ERR_NVS_NOT_FOUND){ESP_LOGW(TAG,"No registry provisioned; no detector states available");return true;}
    if(err!=ESP_OK||size>GW_MAX_JSON||size==0)return false;
    startup_phase("registry_read");
    char *buf=malloc(size+1);if(!buf)return false;
    err=nvs_get_blob(registry_nvs,registry_key,buf,&size);buf[size]=0;char error[128];
    startup_phase("registry_parse");
    bool valid=err==ESP_OK&&gw_parse_registry(buf,size,NULL,false,next,error,sizeof(error));
    free(buf);if(!valid)ESP_LOGE(TAG,"Registry invalid; identity allocation blocked");
    return valid;
}
static void bacnet_task(void *arg) {
    (void)arg;
    for(;;){xSemaphoreTake(runtime_lock,portMAX_DELAY);bg_poll(10,serial_rx_stats().connected);xSemaphoreGive(runtime_lock);vTaskDelay(pdMS_TO_TICKS(5));}
}
static void network_event(void *arg,esp_event_base_t base,int32_t id,void *data) {
    (void)arg;
    if(base==ETH_EVENT) {
        if(id==ETHERNET_EVENT_CONNECTED)ESP_LOGI(TAG,"Ethernet link up; waiting for DHCP");
        if(id==ETHERNET_EVENT_DISCONNECTED){runtime_network_ready=false;strcpy(runtime_ip,"0.0.0.0");ESP_LOGW(TAG,"Ethernet link down");}
    } else if(base==IP_EVENT&&id==IP_EVENT_ETH_GOT_IP) {
        const ip_event_got_ip_t *event=data;
        snprintf(runtime_ip,sizeof(runtime_ip),IPSTR,IP2STR(&event->ip_info.ip));
        esp_ip4_addr_t bc={.addr=event->ip_info.ip.addr|~event->ip_info.netmask.addr};char broadcast[16];snprintf(broadcast,sizeof(broadcast),IPSTR,IP2STR(&bc));
        runtime_network_ready=true;ESP_LOGI(TAG,"DHCP address %s; hostname est3-p4-e41fe8",runtime_ip);
        if(!ntp_started) {esp_sntp_config_t ntp=ESP_NETIF_SNTP_DEFAULT_CONFIG("pool.ntp.org");ntp_started=esp_netif_sntp_init(&ntp)==ESP_OK;}
        xSemaphoreTake(runtime_lock,portMAX_DELAY);
        if(!bacnet_started) {
            bacnet_started=bg_start(3899000,"0.0.0.0",47808,broadcast);
            if(bacnet_started) {bg_configure_address(runtime_ip,broadcast);ESP_ERROR_CHECK(bg_registry(runtime_registry)?ESP_OK:ESP_ERR_NO_MEM);ESP_ERROR_CHECK(xTaskCreate(bacnet_task,"bacnet",12288,NULL,4,NULL)==pdPASS?ESP_OK:ESP_ERR_NO_MEM);}
        } else bg_configure_address(runtime_ip,broadcast);
        xSemaphoreGive(runtime_lock);
        runtime_services_ready=bacnet_started&&management_start()==ESP_OK;
        if(!mdns_started&&mdns_init()==ESP_OK) {
            mdns_started=true;
            /* Match the retained certificate SAN; do not replace device trust. */
            mdns_hostname_set("est3-device");mdns_instance_name_set("EST3 P4 e41fe8");
            mdns_service_add(NULL,"_https","_tcp",443,NULL,0);
        }
    }
}
static void ethernet_start(void) {
    ESP_ERROR_CHECK(esp_netif_init());ESP_ERROR_CHECK(esp_event_loop_create_default());
    eth_mac_config_t mac_cfg=ETH_MAC_DEFAULT_CONFIG();
    eth_phy_config_t phy_cfg=ETH_PHY_DEFAULT_CONFIG();phy_cfg.phy_addr=1;phy_cfg.reset_gpio_num=51;
    eth_esp32_emac_config_t emac_cfg=ETH_ESP32_EMAC_DEFAULT_CONFIG();emac_cfg.smi_gpio.mdc_num=31;emac_cfg.smi_gpio.mdio_num=52;
    esp_eth_mac_t *mac=esp_eth_mac_new_esp32(&emac_cfg,&mac_cfg);esp_eth_phy_t *phy=esp_eth_phy_new_ip101(&phy_cfg);
    ESP_ERROR_CHECK(mac&&phy?ESP_OK:ESP_ERR_NO_MEM);
    esp_eth_handle_t eth;esp_eth_config_t driver=ETH_DEFAULT_CONFIG(mac,phy);ESP_ERROR_CHECK(esp_eth_driver_install(&driver,&eth));
    esp_netif_config_t nc=ESP_NETIF_DEFAULT_ETH();esp_netif_t *netif=esp_netif_new(&nc);ESP_ERROR_CHECK(netif?ESP_OK:ESP_ERR_NO_MEM);
    ESP_ERROR_CHECK(esp_netif_set_hostname(netif,"est3-p4-e41fe8"));ESP_ERROR_CHECK(esp_netif_attach(netif,esp_eth_new_netif_glue(eth)));
    ESP_ERROR_CHECK(esp_event_handler_register(ETH_EVENT,ESP_EVENT_ANY_ID,network_event,NULL));ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT,IP_EVENT_ETH_GOT_IP,network_event,NULL));ESP_ERROR_CHECK(esp_eth_start(eth));
}
void app_main(void) {
    runtime_lock=xSemaphoreCreateMutex();ESP_ERROR_CHECK(runtime_lock?ESP_OK:ESP_ERR_NO_MEM);ESP_ERROR_CHECK(nvs_flash_init());
    nvs_handle_t n;ESP_ERROR_CHECK(nvs_open("est3_boot",NVS_READWRITE,&n));nvs_get_u32(n,"boots",&runtime_boot_count);runtime_boot_count++;ESP_ERROR_CHECK(nvs_set_u32(n,"boots",runtime_boot_count));ESP_ERROR_CHECK(nvs_commit(n));nvs_close(n);
    esp_chip_info_t chip;esp_chip_info(&chip);
    ESP_LOGI(TAG,"EST3 RX-only %s, revision %u, PSRAM %u, boot %lu",esp_app_get_description()->version,chip.revision,(unsigned)esp_psram_get_size(),(unsigned long)runtime_boot_count);
    ESP_LOGW(TAG,"REAL ECP DISABLED. SERIAL PAYLOAD TX COMPILED OUT. No verified panel state.");
    runtime_registry=calloc(1,sizeof(*runtime_registry));ESP_ERROR_CHECK(runtime_registry?ESP_OK:ESP_ERR_NO_MEM);
    startup_phase("network");ethernet_start();
    /* Bring management up before loading a large catalog when a lease is
       available. The ten-second bound lets USB start even without Ethernet. */
    for(unsigned i=0;i<100&&!runtime_services_ready;i++)vTaskDelay(pdMS_TO_TICKS(100));
    startup_phase("registry_allocate");
    gw_registry *next=calloc(1,sizeof(*next));ESP_ERROR_CHECK(next?ESP_OK:ESP_ERR_NO_MEM);
    bool valid=registry_load(next);
    startup_phase("bacnet_catalog");
    xSemaphoreTake(runtime_lock,portMAX_DELAY);
    if(valid) {
        if(bacnet_started)ESP_ERROR_CHECK(bg_registry(next)?ESP_OK:ESP_ERR_NO_MEM);
        gw_registry *previous=runtime_registry;runtime_registry=next;next=NULL;free(previous);
    }
    runtime_registry_ok=valid;xSemaphoreGive(runtime_lock);free(next);
    startup_phase("serial_init");ESP_ERROR_CHECK(serial_rx_start());
    startup_phase("legacy_diagnostics");ESP_ERROR_CHECK(telemetry_start());
    startup_phase("ready");
    for(;;) {
        serial_stats s=serial_rx_stats();
        ESP_LOGI(TAG,"health uptime=%llu usb=%d connects=%lu rx=%lu drops=%lu errors=%lu line_errors=%lu heap=%lu min_heap=%lu ip=%s registry=%d",(unsigned long long)(esp_timer_get_time()/1000000),s.connected,(unsigned long)s.connects,(unsigned long)s.bytes,(unsigned long)s.drops,(unsigned long)s.errors,(unsigned long)s.line_errors,(unsigned long)esp_get_free_heap_size(),(unsigned long)esp_get_minimum_free_heap_size(),runtime_ip,runtime_registry_ok);
        management_rollback_check();vTaskDelay(pdMS_TO_TICKS(10000));
    }
}

#include "runtime.h"
#include "serial_rx.h"
#include "telemetry.h"
#include "provision.h"
#include "web_api.h"
#include "mdns.h"
#include "cJSON.h"
#include "esp_https_server.h"
#include "esp_ota_ops.h"
#include "esp_app_desc.h"
#include "esp_image_format.h"
#include "esp_timer.h"
#include "esp_system.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "mbedtls/sha256.h"
#include "mbedtls/pk.h"
#include "mbedtls/base64.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

static httpd_handle_t server;
static bool awaiting_confirmation;
static const char *TAG="management";
bool management_authorized(httpd_req_t *r) {
    char header[96];size_t n=httpd_req_get_hdr_value_len(r,"Authorization");
    if(n!=7+strlen(DEVICE_TOKEN)||n>=sizeof(header)||httpd_req_get_hdr_value_str(r,"Authorization",header,sizeof(header))!=ESP_OK)return false;
    unsigned diff=0;for(size_t i=0;i<7;i++)diff|=(unsigned char)header[i]^(unsigned char)"Bearer "[i];
    for(size_t i=0;i<strlen(DEVICE_TOKEN);i++)diff|=(unsigned char)header[i+7]^(unsigned char)DEVICE_TOKEN[i];
    return diff==0;
}
#define authorized management_authorized
static esp_err_t json_response(httpd_req_t *r,cJSON *obj) {
    char *s=cJSON_PrintUnformatted(obj);cJSON_Delete(obj);if(!s)return ESP_ERR_NO_MEM;
    httpd_resp_set_type(r,"application/json");httpd_resp_set_hdr(r,"Cache-Control","no-store");
    esp_err_t ret=httpd_resp_sendstr(r,s);free(s);return ret;
}
static esp_err_t deny(httpd_req_t *r) {return httpd_resp_send_err(r,HTTPD_401_UNAUTHORIZED,"Authentication required");}
static esp_err_t unavailable(httpd_req_t *r,const char *why) {httpd_resp_set_status(r,"503 Service Unavailable");return httpd_resp_sendstr(r,why);}
static esp_err_t status(httpd_req_t *r) {
    if(!authorized(r))return deny(r);
    cJSON *j=cJSON_CreateObject();serial_stats s=serial_rx_stats();
    const esp_partition_t *p=esp_ota_get_running_partition();
    cJSON_AddStringToObject(j,"project",esp_app_get_description()->project_name);
    cJSON_AddStringToObject(j,"version",esp_app_get_description()->version);
    cJSON_AddNumberToObject(j,"reset_reason",esp_reset_reason());
    cJSON_AddStringToObject(j,"startup_phase",runtime_startup_phase);
    /* esp_app_get_elf_sha256() is capped by CONFIG_APP_RETRIEVE_LEN_ELF_SHA
       (9 for this build). OTA confirmation needs all 32 descriptor bytes. */
    char elf_hash[65];const uint8_t *hash=esp_app_get_description()->app_elf_sha256;
    for(size_t i=0;i<32;i++)snprintf(elf_hash+2*i,3,"%02x",hash[i]);
    cJSON_AddStringToObject(j,"elf_sha256",elf_hash);
    cJSON_AddStringToObject(j,"partition",p?p->label:"unknown");
    cJSON_AddStringToObject(j,"ip",runtime_ip);
    cJSON_AddStringToObject(j,"protocol","DISABLED_NO_VERIFIED_ECP_PROFILE");
    cJSON_AddStringToObject(j,"printer_profile",PR_PROFILE);
    cJSON_AddBoolToObject(j,"event_decoder_validated",false);
    cJSON_AddBoolToObject(j,"trouble_observation_decoder",true);
    cJSON_AddBoolToObject(j,"external_host_delivery_enabled",false);
    cJSON_AddNumberToObject(j,"bacnet_device_instance",3899000);
    cJSON_AddNumberToObject(j,"bacnet_vendor_id",65535);
    cJSON_AddStringToObject(j,"bacnet_assignment","lab placeholders; site assignment pending");
    char mdns_name[MDNS_NAME_BUF_LEN]="";
    bool name_ok=mdns_hostname_get(mdns_name)==ESP_OK&&!strcmp(mdns_name,"est3-device");
    cJSON_AddStringToObject(j,"web_url","https://est3-device.local/");
    cJSON_AddBoolToObject(j,"web_name_configured",name_ok);
    cJSON_AddBoolToObject(j,"serial_payload_tx_enabled",false);
    cJSON_AddBoolToObject(j,"simulation",false);
    cJSON_AddBoolToObject(j,"usb_connected",s.connected);
    cJSON_AddNumberToObject(j,"usb_connects",s.connects);
    cJSON_AddNumberToObject(j,"rx_bytes",s.bytes);
    cJSON_AddNumberToObject(j,"rx_drops",s.drops);
    cJSON_AddNumberToObject(j,"rx_crc32",s.crc32);
    cJSON_AddNumberToObject(j,"usb_errors",s.errors);
    cJSON_AddNumberToObject(j,"line_errors",s.line_errors);
    uint32_t queued,dropped;bool journal_ok;telemetry_stats(&queued,&dropped,&journal_ok);
    cJSON_AddNumberToObject(j,"telemetry_queued",queued);cJSON_AddNumberToObject(j,"telemetry_dropped",dropped);cJSON_AddBoolToObject(j,"journal_ok",journal_ok);
    cJSON_AddBoolToObject(j,"awaiting_confirmation",awaiting_confirmation);
    cJSON_AddNumberToObject(j,"uptime_ms",esp_timer_get_time()/1000);
    cJSON_AddNumberToObject(j,"boot_count",runtime_boot_count);
    cJSON_AddNumberToObject(j,"heap_free",esp_get_free_heap_size());
    cJSON_AddNumberToObject(j,"internal_heap_free",heap_caps_get_free_size(MALLOC_CAP_INTERNAL));
    xSemaphoreTake(runtime_lock,portMAX_DELAY);
    cJSON_AddBoolToObject(j,"registry_ok",runtime_registry_ok);
    cJSON_AddNumberToObject(j,"registry_epoch",runtime_registry?runtime_registry->epoch:0);
    cJSON_AddNumberToObject(j,"device_count",runtime_registry?runtime_registry->count:0);
    cJSON_AddStringToObject(j,"inventory_source_sha256",runtime_registry?runtime_registry->source_hash:"");
    xSemaphoreGive(runtime_lock);
    return json_response(r,j);
}
static esp_err_t confirm(httpd_req_t *r) {
    if(!authorized(r))return deny(r);
    if(esp_timer_get_time()<10000000 || !runtime_network_ready || !runtime_registry_ok || !runtime_services_ready || strcmp(runtime_startup_phase,"ready"))
        return unavailable(r,"Local checks not ready");
    if(awaiting_confirmation) {
        esp_err_t err=esp_ota_mark_app_valid_cancel_rollback();
        if(err!=ESP_OK)return httpd_resp_send_err(r,HTTPD_500_INTERNAL_SERVER_ERROR,"Cannot confirm image");
        awaiting_confirmation=false;ESP_LOGI(TAG,"Authenticated remote health confirmation; OTA image marked valid");
    }
    return httpd_resp_sendstr(r,"{\"confirmed\":true}");
}
static void reboot_task(void *unused) {(void)unused;vTaskDelay(pdMS_TO_TICKS(1500));esp_restart();}
static esp_err_t upload(httpd_req_t *r) {
    if(!authorized(r))return deny(r);
    const esp_partition_t *partition=esp_ota_get_next_update_partition(NULL);
    if(awaiting_confirmation||!partition||r->content_len<sizeof(esp_image_header_t)+sizeof(esp_image_segment_header_t)+sizeof(esp_app_desc_t)||r->content_len>partition->size)
        return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Image size or OTA state invalid");
    char encoded[160];uint8_t signature[100];size_t signature_size=0;
    if(httpd_req_get_hdr_value_str(r,"X-Image-Signature",encoded,sizeof(encoded))!=ESP_OK || mbedtls_base64_decode(signature,sizeof(signature),&signature_size,(unsigned char*)encoded,strlen(encoded))!=0)
        return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Detached ECDSA signature required");
    esp_ota_handle_t handle=0;
    if(esp_ota_begin(partition,r->content_len,&handle)!=ESP_OK)return httpd_resp_send_err(r,HTTPD_500_INTERNAL_SERVER_ERROR,"Cannot begin OTA");
    mbedtls_sha256_context sha;mbedtls_sha256_init(&sha);mbedtls_sha256_starts(&sha,0);
    uint8_t *buf=malloc(4096);bool ok=buf!=NULL;size_t received=0;uint8_t prefix[sizeof(esp_image_header_t)+sizeof(esp_image_segment_header_t)+sizeof(esp_app_desc_t)];size_t prefix_size=0;
    while(ok&&received<r->content_len) {
        int n=httpd_req_recv(r,(char*)buf,(r->content_len-received)>4096?4096:r->content_len-received);
        if(n<=0){ok=false;break;}
        size_t extra=sizeof(prefix)-prefix_size;if(extra>(size_t)n)extra=n;
        memcpy(prefix+prefix_size,buf,extra);prefix_size+=extra;
        if(prefix_size==sizeof(prefix)) {
            esp_app_desc_t desc;memcpy(&desc,prefix+sizeof(esp_image_header_t)+sizeof(esp_image_segment_header_t),sizeof(desc));
            if(desc.magic_word!=ESP_APP_DESC_MAGIC_WORD||strncmp(desc.project_name,"est3_gateway_rxonly",sizeof(desc.project_name))) {ok=false;break;}
        }
        mbedtls_sha256_update(&sha,buf,n);
        if(esp_ota_write(handle,buf,n)!=ESP_OK){ok=false;break;}received+=n;
    }
    free(buf);uint8_t hash[32];mbedtls_sha256_finish(&sha,hash);mbedtls_sha256_free(&sha);
    mbedtls_pk_context public_key;mbedtls_pk_init(&public_key);
    if(mbedtls_pk_parse_public_key(&public_key,(const unsigned char*)SIGNING_PUBLIC,sizeof(SIGNING_PUBLIC))!=0 || mbedtls_pk_verify(&public_key,MBEDTLS_MD_SHA256,hash,sizeof(hash),signature,signature_size)!=0)ok=false;
    mbedtls_pk_free(&public_key);
    if(!ok){esp_ota_abort(handle);return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Rejected: incomplete image, wrong project, or bad signature");}
    if(esp_ota_end(handle)!=ESP_OK)return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"ESP image validation failed");
    if(esp_ota_set_boot_partition(partition)!=ESP_OK)return httpd_resp_send_err(r,HTTPD_500_INTERNAL_SERVER_ERROR,"Cannot select image");
    httpd_resp_set_status(r,"202 Accepted");httpd_resp_sendstr(r,"{\"accepted\":true,\"confirmation_required\":true,\"deadline_seconds\":180}");
    /* Keep shutdown off the small 2 KiB stack used by earlier releases. */
    if(xTaskCreate(reboot_task,"ota_reboot",8192,NULL,5,NULL)!=pdPASS) {
        ESP_LOGE(TAG,"Reboot task allocation failed; restarting on HTTPS task stack");
        vTaskDelay(pdMS_TO_TICKS(1500));esp_restart();
    }
    return ESP_OK;
}
static esp_err_t registry_change(httpd_req_t *r,bool preview) {
    if(!authorized(r))return deny(r);
    if(strcmp(runtime_startup_phase,"ready"))return unavailable(r,"Startup still in progress");
    if(r->content_len<=0||r->content_len>GW_MAX_JSON)return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Registry size invalid");
    char *buf=malloc(r->content_len+1);if(!buf)return unavailable(r,"No memory");
    size_t n=0;while(n<r->content_len){int k=httpd_req_recv(r,buf+n,r->content_len-n);if(k<=0){free(buf);return ESP_FAIL;}n+=k;}buf[n]=0;
    if(preview) {
        gw_registry *next=calloc(1,sizeof(*next));char error[128];bool valid=false;unsigned added=0,renamed=0,retired=0;
        xSemaphoreTake(runtime_lock,portMAX_DELAY);
        if(next&&runtime_registry_ok)valid=gw_parse_registry(buf,n,runtime_registry,false,next,error,sizeof(error));
        if(valid)for(size_t i=0;i<next->count;i++) {
            if(i%32==0)vTaskDelay(1);
            const gw_device *d=&next->devices[i];bool found=false;
            for(size_t k=0;k<runtime_registry->count;k++)if(!strcmp(d->uuid,runtime_registry->devices[k].uuid)) {
                const gw_device *old=&runtime_registry->devices[k];found=true;
                if(strcmp(d->label,old->label))renamed++;
                if(d->retired&&!old->retired)retired++;
            }
            if(!found)added++;
        }
        xSemaphoreGive(runtime_lock);free(buf);
        if(!valid){free(next);return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Registry invalid, obsolete, simulated, or identity constraints violated");}
        cJSON *j=cJSON_CreateObject();cJSON_AddBoolToObject(j,"valid",true);cJSON_AddNumberToObject(j,"epoch",next->epoch);
        cJSON_AddNumberToObject(j,"objects",next->count);cJSON_AddNumberToObject(j,"bacnet_binary_inputs",next->count*5+4);
        cJSON_AddNumberToObject(j,"additions",added);cJSON_AddNumberToObject(j,"renames",renamed);cJSON_AddNumberToObject(j,"retirements",retired);
        cJSON_AddStringToObject(j,"condition_quality","No current condition follows from inventory import");free(next);return json_response(r,j);
    }
    char error[128];esp_err_t result=registry_apply(buf,n,error,sizeof(error));free(buf);
    if(result!=ESP_OK)return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,error);
    return httpd_resp_sendstr(r,"{\"applied\":true}");
}
static esp_err_t registry(httpd_req_t *r) {return registry_change(r,false);}
static esp_err_t registry_preview(httpd_req_t *r) {return registry_change(r,true);}
static esp_err_t registry_get(httpd_req_t *r) {
    if(!authorized(r))return deny(r);
    size_t n;char *data=registry_export(&n);
    if(!data)return httpd_resp_send_err(r,HTTPD_404_NOT_FOUND,"No stored registry");
    httpd_resp_set_type(r,"application/json");httpd_resp_set_hdr(r,"Cache-Control","no-store");
    esp_err_t result=httpd_resp_send(r,data,n);free(data);return result;
}
static esp_err_t set_host(httpd_req_t *r) {
    if(!authorized(r))return deny(r);
    if(r->content_len<1||r->content_len>300)return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Invalid host configuration length");
    char buf[301];int have=0;
    while(have<r->content_len){int n=httpd_req_recv(r,buf+have,r->content_len-have);if(n<=0)return ESP_FAIL;have+=n;}buf[have]=0;
    cJSON *obj=cJSON_Parse(buf),*url=cJSON_GetObjectItem(obj,"url");
    esp_err_t err=cJSON_IsObject(obj)&&cJSON_GetArraySize(obj)==1&&cJSON_IsString(url)?telemetry_set_url(url->valuestring):ESP_ERR_INVALID_ARG;
    cJSON_Delete(obj);if(err!=ESP_OK)return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"External host delivery is disabled in standalone firmware");
    return httpd_resp_sendstr(r,"{\"configured\":true}");
}
static esp_err_t serial_get(httpd_req_t *r) {
    if(!authorized(r))return deny(r);
    serial_stats s;serial_diagnostics d;serial_rx_diagnostics(&s,&d);
    uint8_t payload[SERIAL_CAPTURE_CAPACITY];
    char hex[SERIAL_CAPTURE_CAPACITY*2+1];
    size_t n=serial_diagnostics_payload(&d,payload,sizeof(payload));
    static const char digits[]="0123456789abcdef";
    for(size_t i=0;i<n;i++){hex[2*i]=digits[payload[i]>>4];hex[2*i+1]=digits[payload[i]&15];}
    hex[2*n]=0;
    cJSON *j=cJSON_CreateObject();
    cJSON_AddBoolToObject(j,"usb_connected",s.connected);
    cJSON_AddBoolToObject(j,"serial_payload_tx_enabled",false);
    cJSON_AddNumberToObject(j,"boot_count",runtime_boot_count);
    cJSON_AddNumberToObject(j,"baud",s.baud);
    cJSON_AddNumberToObject(j,"requested_baud",s.requested_baud);
    cJSON_AddNumberToObject(j,"baud_epoch",s.baud_epoch);
    cJSON_AddNumberToObject(j,"configuration_error",s.configuration_error);
    cJSON_AddStringToObject(j,"format","8N1");
    cJSON_AddStringToObject(j,"flow_control","none");
    cJSON_AddNumberToObject(j,"usb_in_packets",d.packets);
    cJSON_AddNumberToObject(j,"usb_status_only_packets",d.status_only_packets);
    cJSON_AddNumberToObject(j,"usb_invalid_packets",d.invalid_packets);
    cJSON_AddNumberToObject(j,"usb_line_error_packets",d.error_packets);
    cJSON_AddNumberToObject(j,"ftdi_modem_status",d.modem_status);
    cJSON_AddNumberToObject(j,"ftdi_line_status",d.line_status);
    cJSON_AddNumberToObject(j,"last_usb_packet_ms",(double)d.last_packet_ms);
    cJSON_AddNumberToObject(j,"last_payload_ms",(double)d.last_payload_ms);
    cJSON_AddNumberToObject(j,"usb_payload_bytes",d.payload_bytes);
    cJSON_AddNumberToObject(j,"rx_bytes",s.bytes);
    cJSON_AddNumberToObject(j,"rx_drops",s.drops);
    cJSON_AddNumberToObject(j,"usb_errors",s.errors);
    cJSON_AddNumberToObject(j,"line_errors",s.line_errors);
    cJSON_AddNumberToObject(j,"capture_epoch",d.capture_epoch);
    cJSON_AddNumberToObject(j,"capture_count",n);
    cJSON_AddNumberToObject(j,"capture_start_offset",d.payload_bytes-(uint32_t)n);
    cJSON_AddStringToObject(j,"capture_hex",hex);
    return json_response(r,j);
}
static esp_err_t serial_set(httpd_req_t *r) {
    if(!authorized(r))return deny(r);
    if(r->content_len<1||r->content_len>64)return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Invalid receiver configuration length");
    char body[65];int have=0;
    while(have<r->content_len){int n=httpd_req_recv(r,body+have,r->content_len-have);if(n<=0)return ESP_FAIL;have+=n;}body[have]=0;
    cJSON *obj=cJSON_Parse(body),*baud=cJSON_GetObjectItem(obj,"baud");
    bool valid=cJSON_IsObject(obj)&&cJSON_GetArraySize(obj)==1&&cJSON_IsNumber(baud)&&
        baud->valuedouble>=1200&&baud->valuedouble<=115200&&
        baud->valuedouble==(double)baud->valueint&&serial_baud_supported((uint32_t)baud->valueint);
    esp_err_t err=valid?serial_rx_set_baud((uint32_t)baud->valueint):ESP_ERR_INVALID_ARG;
    cJSON_Delete(obj);
    if(err==ESP_ERR_INVALID_ARG)return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Supported receiver baud required; format fixed at 8N1, payload TX disabled");
    if(err!=ESP_OK)return unavailable(r,"USB receiver not connected");
    httpd_resp_set_status(r,"202 Accepted");
    return httpd_resp_sendstr(r,"{\"accepted\":true,\"volatile\":true,\"serial_payload_tx_enabled\":false}");
}
esp_err_t management_start(void) {
    if(server)return ESP_OK;
    httpd_ssl_config_t config=HTTPD_SSL_CONFIG_DEFAULT();config.httpd.stack_size=16384;config.httpd.max_uri_handlers=16;config.httpd.max_open_sockets=3;config.httpd.recv_wait_timeout=10;config.httpd.send_wait_timeout=10;config.httpd.lru_purge_enable=true;
    config.servercert=(const uint8_t*)DEVICE_CERT;config.servercert_len=sizeof(DEVICE_CERT);
    config.prvtkey_pem=(const uint8_t*)DEVICE_KEY;config.prvtkey_len=sizeof(DEVICE_KEY);
    esp_err_t err=httpd_ssl_start(&server,&config);if(err!=ESP_OK)return err;
    const httpd_uri_t routes[]={ {.uri="/api/v1/status",.method=HTTP_GET,.handler=status}, {.uri="/ota/status",.method=HTTP_GET,.handler=status}, {.uri="/ota",.method=HTTP_POST,.handler=upload}, {.uri="/ota/confirm",.method=HTTP_POST,.handler=confirm}, {.uri="/api/v1/registry",.method=HTTP_POST,.handler=registry}, {.uri="/api/v1/host",.method=HTTP_POST,.handler=set_host}, {.uri="/api/v1/serial",.method=HTTP_GET,.handler=serial_get}, {.uri="/api/v1/serial",.method=HTTP_POST,.handler=serial_set} };
    for(size_t i=0;i<sizeof(routes)/sizeof(routes[0]);i++) {err=httpd_register_uri_handler(server,&routes[i]);if(err!=ESP_OK)return err;}
    const httpd_uri_t export_route={.uri="/api/v1/registry",.method=HTTP_GET,.handler=registry_get};
    const httpd_uri_t preview_route={.uri="/api/v1/registry/preview",.method=HTTP_POST,.handler=registry_preview};
    err=httpd_register_uri_handler(server,&export_route);if(err!=ESP_OK)return err;
    err=httpd_register_uri_handler(server,&preview_route);if(err!=ESP_OK)return err;
    err=web_register(server);if(err!=ESP_OK)return err;
    esp_ota_img_states_t state;
    awaiting_confirmation=esp_ota_get_state_partition(esp_ota_get_running_partition(),&state)==ESP_OK&&state==ESP_OTA_IMG_PENDING_VERIFY;
    ESP_LOGI(TAG,"HTTPS management initialized; pending remote confirmation=%d",awaiting_confirmation);return ESP_OK;
}
void management_rollback_check(void) {
    /* Also inspect state when Ethernet has never linked / HTTPS has not started. */
    esp_ota_img_states_t state;
    if(esp_ota_get_state_partition(esp_ota_get_running_partition(),&state)==ESP_OK && state==ESP_OTA_IMG_PENDING_VERIFY && esp_timer_get_time()>180000000) {
        ESP_LOGE(TAG,"No authenticated remote confirmation within 180 seconds; rolling back");
        esp_ota_mark_app_invalid_rollback_and_reboot();
    }
}

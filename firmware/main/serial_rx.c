#include "serial_rx.h"
#include "gateway.h"
#include "usb/usb_host.h"
#include "usb/cdc_acm_host.h"
#include "usb/vcp_ftdi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "esp_rom_crc.h"
#include <string.h>

_Static_assert(GW_SERIAL_PAYLOAD_TX_ENABLED==0 && GW_ECP_ENABLED==0,"This target must stay RX-only");
static const char *TAG="usb_rx";
static QueueHandle_t queue;
static SemaphoreHandle_t lost;
static portMUX_TYPE lock=portMUX_INITIALIZER_UNLOCKED;
static serial_stats stats;
typedef struct {size_t length;uint8_t data[64];} chunk;
serial_stats serial_rx_stats(void) {portENTER_CRITICAL(&lock);serial_stats copy=stats;portEXIT_CRITICAL(&lock);return copy;}
static bool receive(const uint8_t *data,size_t len,void *arg) {
    (void)arg;
    /* FTDI component removes two status bytes once per MPS-sized transfer.
       in_buffer_size=0 enforces a single USB packet. Do not strip again here. */
    portENTER_CRITICAL(&lock);stats.bytes+=len;stats.chunks++;portEXIT_CRITICAL(&lock);
    for(size_t offset=0;offset<len;offset+=64) {
        chunk c={.length=len-offset>64?64:len-offset};memcpy(c.data,data+offset,c.length);
        if(xQueueSend(queue,&c,0)!=pdTRUE){portENTER_CRITICAL(&lock);stats.drops+=c.length;portEXIT_CRITICAL(&lock);}
    }
    return true;
}
static void event(const cdc_acm_host_dev_event_data_t *ev,void *arg) {
    (void)arg;
    if(ev->type==CDC_ACM_HOST_DEVICE_DISCONNECTED) {
        portENTER_CRITICAL(&lock);stats.connected=false;portEXIT_CRITICAL(&lock);xSemaphoreGive(lost);
    } else if(ev->type==CDC_ACM_HOST_ERROR) {
        portENTER_CRITICAL(&lock);stats.errors++;portEXIT_CRITICAL(&lock);xSemaphoreGive(lost);
    } else if(ev->type==CDC_ACM_HOST_SERIAL_STATE) {
        if(ev->data.serial_state.bFraming||ev->data.serial_state.bParity||ev->data.serial_state.bOverRun||ev->data.serial_state.bBreak) {
            portENTER_CRITICAL(&lock);stats.line_errors++;portEXIT_CRITICAL(&lock);
        }
    }
}
static void new_device(usb_device_handle_t dev) {
    const usb_device_desc_t *desc;usb_device_info_t info;
    if(usb_host_get_device_descriptor(dev,&desc)!=ESP_OK)return;
    ESP_LOGI(TAG,"USB VID=%04x PID=%04x bcdDevice=%04x %s",desc->idVendor,desc->idProduct,desc->bcdDevice,(desc->idVendor==FTDI_VID&&desc->idProduct==FT232_PID)?"candidate FT232 (electrical identity unverified)":"unsupported; will not open");
    if(usb_host_device_info(dev,&info)==ESP_OK) {
        usb_print_string_descriptor(info.str_desc_manufacturer);
        usb_print_string_descriptor(info.str_desc_product);
        usb_print_string_descriptor(info.str_desc_serial_num);
    }
}
static void host_task(void *arg) {
    (void)arg;
    for(;;){uint32_t flags=0;usb_host_lib_handle_events(portMAX_DELAY,&flags);if(flags&USB_HOST_LIB_EVENT_FLAGS_NO_CLIENTS)usb_host_device_free_all();}
}
static void consumer(void *arg) {
    (void)arg;chunk c;
    for(;;)if(xQueueReceive(queue,&c,portMAX_DELAY)==pdTRUE) {
        portENTER_CRITICAL(&lock);stats.crc32=esp_rom_crc32_le(stats.crc32,c.data,c.length);portEXIT_CRITICAL(&lock);
        /* No ECP parser is compiled. Payload is not interpreted as point state. */
    }
}
static void connector(void *arg) {
    (void)arg;
    const cdc_acm_host_device_config_t config={.connection_timeout_ms=3000,.out_buffer_size=0,.in_buffer_size=0,.event_cb=event,.data_cb=receive};
    for(;;) {
        cdc_acm_dev_hdl_t device=NULL;
        while(xSemaphoreTake(lost,0)==pdTRUE){}
        esp_err_t err=ftdi_vcp_open(FT232_PID,0,&config,&device);
        if(err!=ESP_OK){vTaskDelay(pdMS_TO_TICKS(1000));continue;}
        cdc_acm_host_desc_print(device);
        const cdc_acm_line_coding_t line={.dwDTERate=19200,.bCharFormat=0,.bParityType=0,.bDataBits=8};
        err=cdc_acm_host_line_coding_set(device,&line);
        if(err==ESP_OK)err=cdc_acm_host_set_control_line_state(device,false,false);
        if(err==ESP_OK) {
            portENTER_CRITICAL(&lock);stats.connected=true;stats.connects++;portEXIT_CRITICAL(&lock);
            ESP_LOGI(TAG,"FT232 open: 19200 8N1, DTR/RTS deasserted, OUT buffer disabled, ECP disabled");
            xSemaphoreTake(lost,portMAX_DELAY);
        }
        cdc_acm_host_close(device);
        xQueueReset(queue);
        portENTER_CRITICAL(&lock);stats.connected=false;portEXIT_CRITICAL(&lock);
        ESP_LOGW(TAG,"FTDI closed; receive queue discarded; reconnect pending");
    }
}
/* Link guard. No field-channel payload writes exist in this target. */
esp_err_t __wrap_cdc_acm_host_data_tx_blocking(cdc_acm_dev_hdl_t h,const uint8_t *d,size_t n,uint32_t timeout) {
    (void)h;(void)d;(void)n;(void)timeout;return ESP_ERR_NOT_SUPPORTED;
}
esp_err_t serial_rx_start(void) {
    queue=xQueueCreate(128,sizeof(chunk));lost=xSemaphoreCreateBinary();if(!queue||!lost)return ESP_ERR_NO_MEM;
    const usb_host_config_t host={.intr_flags=ESP_INTR_FLAG_LEVEL1};
    esp_err_t err=usb_host_install(&host);if(err!=ESP_OK)return err;
    if(xTaskCreate(host_task,"usb_host",4096,NULL,10,NULL)!=pdPASS)return ESP_ERR_NO_MEM;
    const cdc_acm_host_driver_config_t driver={.driver_task_stack_size=4096,.driver_task_priority=8,.xCoreID=0,.new_dev_cb=new_device};
    err=cdc_acm_host_install(&driver);if(err!=ESP_OK)return err;
    if(xTaskCreate(consumer,"serial_sink",4096,NULL,7,NULL)!=pdPASS || xTaskCreate(connector,"ftdi_connect",6144,NULL,6,NULL)!=pdPASS)return ESP_ERR_NO_MEM;
    return ESP_OK;
}

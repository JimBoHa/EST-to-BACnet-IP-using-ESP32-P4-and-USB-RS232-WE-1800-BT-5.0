#include "web_api.h"
#include "runtime.h"
#include "serial_rx.h"
#include "cJSON.h"
#include "esp_timer.h"
#include <ctype.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

extern const unsigned char web_start[] asm("_binary_index_html_start");
extern const unsigned char web_end[] asm("_binary_index_html_end");
extern const unsigned char js_start[] asm("_binary_app_js_start");
extern const unsigned char js_end[] asm("_binary_app_js_end");
static esp_err_t json(httpd_req_t *r,cJSON *j) {
    char *body=cJSON_PrintUnformatted(j);cJSON_Delete(j);if(!body)return ESP_ERR_NO_MEM;
    httpd_resp_set_type(r,"application/json");httpd_resp_set_hdr(r,"Cache-Control","no-store");
    httpd_resp_set_hdr(r,"X-Content-Type-Options","nosniff");
    esp_err_t err=httpd_resp_sendstr(r,body);free(body);return err;
}
static esp_err_t page(httpd_req_t *r) {
    bool script=!strcmp(r->uri,"/app.js");
    httpd_resp_set_type(r,script?"text/javascript":"text/html; charset=utf-8");
    httpd_resp_set_hdr(r,"Cache-Control","no-store");
    httpd_resp_set_hdr(r,"X-Content-Type-Options","nosniff");
    httpd_resp_set_hdr(r,"Content-Security-Policy","default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");
    return httpd_resp_send(r,(const char*)(script?js_start:web_start),(script?js_end-js_start:web_end-web_start)-1);
}
static bool query(httpd_req_t *r,const char *key,char *out,size_t size) {
    char buffer[768];if(httpd_req_get_url_query_str(r,buffer,sizeof(buffer))!=ESP_OK)return false;
    return httpd_query_key_value(buffer,key,out,size)==ESP_OK;
}
static unsigned query_number(httpd_req_t *r,const char *key,unsigned fallback,unsigned maximum) {
    char buf[24];if(!query(r,key,buf,sizeof(buf)))return fallback;
    char *end;unsigned long n=strtoul(buf,&end,10);return *end||n>maximum?fallback:(unsigned)n;
}
static void decode(char *s) {
    char *d=s;
    while(*s) {
        if(*s=='%'&&s[1]&&s[2]&&isxdigit((unsigned char)s[1])&&isxdigit((unsigned char)s[2])) {
            char hex[3]={s[1],s[2],0};unsigned long v=strtoul(hex,NULL,16);*d++=v?(char)v:'?';s+=3;
        } else {*d++=*s=='+'?' ':*s;s++;}
    }*d=0;
}
static bool contains(const char *text,const char *term) {
    if(!*term)return true;
    for(;*text;text++){size_t i=0;while(term[i]&&text[i]&&tolower((unsigned char)term[i])==tolower((unsigned char)text[i]))i++;if(!term[i])return true;}
    return false;
}
static cJSON *report(const pr_report *r) {
    cJSON *j=cJSON_CreateObject();
    cJSON_AddBoolToObject(j,"complete",r->complete);cJSON_AddBoolToObject(j,"active",r->active);
    cJSON_AddBoolToObject(j,"tainted",r->tainted);cJSON_AddNumberToObject(j,"panel",r->panel);
    cJSON_AddNumberToObject(j,"received_monotonic_ms",(double)r->received_ms);
    cJSON_AddNumberToObject(j,"stream_epoch",r->epoch);
    cJSON_AddStringToObject(j,"source_time",r->source_time);
    cJSON_AddStringToObject(j,"time_quality","panel_clock_timezone_unverified");
    cJSON_AddNumberToObject(j,"historical_alarm_count",r->historical_alarm_count);
    cJSON_AddStringToObject(j,"cpu",r->cpu);cJSON_AddStringToObject(j,"sdu",r->sdu);
    cJSON_AddStringToObject(j,"project",r->project);cJSON_AddStringToObject(j,"database_date",r->database_date);
    cJSON_AddStringToObject(j,"database_serial",r->database_serial);cJSON_AddStringToObject(j,"market",r->market);
    cJSON *cards=cJSON_AddArrayToObject(j,"cards");
    for(size_t i=0;i<r->card_count;i++) {
        const pr_card *c=&r->cards[i];cJSON *v=cJSON_CreateObject();cJSON_AddItemToArray(cards,v);
        cJSON_AddNumberToObject(v,"address",c->address);cJSON_AddStringToObject(v,"type",c->type);
        cJSON_AddStringToObject(v,"ann_type",c->ann_type);cJSON_AddStringToObject(v,"firmware",c->firmware);
        cJSON_AddStringToObject(v,"bootstrap",c->bootstrap);cJSON_AddStringToObject(v,"database",c->database);
        cJSON_AddStringToObject(v,"firmware_date",c->firmware_date);cJSON_AddStringToObject(v,"bootstrap_date",c->bootstrap_date);
        cJSON_AddStringToObject(v,"database_date",c->database_date);
    }
    return j;
}
static esp_err_t printer_get(httpd_req_t *r) {
    if(!management_authorized(r))return httpd_resp_send_err(r,HTTPD_401_UNAUTHORIZED,"Authentication required");
    pr_parser *p=malloc(sizeof(*p));if(!p)return ESP_ERR_NO_MEM;
    if(!serial_rx_printer_copy(p)){free(p);return ESP_FAIL;}
    cJSON *j=cJSON_CreateObject();
    cJSON_AddStringToObject(j,"profile","est3_printer_revision_v1");
    cJSON_AddBoolToObject(j,"current_state_available",false);
    cJSON_AddStringToObject(j,"retention","latest 128 records in RAM; cleared on reboot; no long-term recorder");
    cJSON_AddNumberToObject(j,"boot_count",runtime_boot_count);
    cJSON_AddNumberToObject(j,"retained",p->count);cJSON_AddNumberToObject(j,"evicted",(double)p->evicted);
    cJSON_AddNumberToObject(j,"gaps",(double)p->gaps);cJSON_AddNumberToObject(j,"unrecognized",(double)p->unknown);
    cJSON_AddNumberToObject(j,"complete_reports",(double)p->reports_complete);
    cJSON_AddNumberToObject(j,"incomplete_reports",(double)p->reports_incomplete);
    cJSON_AddNumberToObject(j,"partial_bytes",p->partial_length);cJSON_AddNumberToObject(j,"stream_offset",(double)p->next_offset);
    cJSON_AddItemToObject(j,"last_complete_report",report(&p->last_complete));
    cJSON_AddItemToObject(j,"current_report",report(&p->report));
    cJSON *lines=cJSON_AddArrayToObject(j,"records");
    unsigned limit=query_number(r,"limit",32,128);if(!limit)limit=1;
    size_t start=p->count>limit?p->count-limit:0;
    for(size_t i=start;i<p->count;i++) {
        const pr_line *line=pr_recent(p,i);cJSON *item=cJSON_CreateObject();cJSON_AddItemToArray(lines,item);
        cJSON_AddNumberToObject(item,"id",(double)line->id);cJSON_AddNumberToObject(item,"offset",(double)line->offset);
        cJSON_AddNumberToObject(item,"received_monotonic_ms",(double)line->received_ms);
        cJSON_AddNumberToObject(item,"epoch",line->epoch);cJSON_AddStringToObject(item,"parse_status",pr_kind_name(line->kind));
        char hex[PR_LINE_MAX*2+1];static const char digits[]="0123456789abcdef";
        for(size_t k=0;k<line->length;k++){hex[k*2]=digits[line->raw[k]>>4];hex[k*2+1]=digits[line->raw[k]&15];}hex[line->length*2]=0;
        cJSON_AddStringToObject(item,"raw_hex",hex);
    }
    free(p);return json(r,j);
}
static esp_err_t devices_get(httpd_req_t *r) {
    if(!management_authorized(r))return httpd_resp_send_err(r,HTTPD_401_UNAUTHORIZED,"Authentication required");
    char term[192]="";query(r,"q",term,sizeof(term));decode(term);
    unsigned offset=query_number(r,"offset",0,GW_MAX_DEVICES),limit=query_number(r,"limit",40,100);if(!limit)limit=1;
    cJSON *j=cJSON_CreateObject(),*items=cJSON_AddArrayToObject(j,"devices");
    size_t matched=0;uint64_t now=(uint64_t)(esp_timer_get_time()/1000);
    xSemaphoreTake(runtime_lock,portMAX_DELAY);
    cJSON_AddNumberToObject(j,"registry_epoch",runtime_registry->epoch);
    cJSON_AddNumberToObject(j,"total",runtime_registry->count);
    cJSON_AddStringToObject(j,"source_sha256",runtime_registry->source_hash);
    cJSON_AddStringToObject(j,"source_quality",runtime_registry->source_quality);
    for(size_t i=0;i<runtime_registry->count;i++) {
        gw_device *d=&runtime_registry->devices[i];
        if(!contains(d->label,term)&&!contains(d->address,term)&&!contains(d->type,term)&&!contains(d->uuid,term))continue;
        if(matched++<offset||matched>offset+limit)continue;
        cJSON *v=cJSON_CreateObject();cJSON_AddItemToArray(items,v);
        cJSON_AddStringToObject(v,"uuid",d->uuid);cJSON_AddStringToObject(v,"address",d->address);
        cJSON_AddStringToObject(v,"label",d->label);cJSON_AddStringToObject(v,"type",d->type);
        cJSON_AddNumberToObject(v,"binding_epoch",d->binding_epoch);cJSON_AddBoolToObject(v,"retired",d->retired);
        cJSON_AddBoolToObject(v,"data_valid",gw_data_valid(d,now));
        cJSON *states=cJSON_AddArrayToObject(v,"conditions");
        static const char *const kinds[]={"alarm","trouble","supervisory","disabled"};
        for(unsigned k=0;k<4;k++) {
            cJSON *s=cJSON_CreateObject();cJSON_AddItemToArray(states,s);cJSON_AddStringToObject(s,"condition",kinds[k]);
            cJSON_AddNumberToObject(s,"instance",d->instances[k]);
            if(d->conditions[k].known)cJSON_AddBoolToObject(s,"last_value",d->conditions[k].value);else cJSON_AddNullToObject(s,"last_value");
            const char *quality=d->retired?"retired":!(d->supported&(1u<<k))?"not_source_verified":!d->conditions[k].known?"unknown":gw_condition_valid(d,k,now)?"valid":"stale";
            cJSON_AddStringToObject(s,"quality",quality);
        }
        cJSON_AddNumberToObject(v,"data_valid_instance",d->instances[4]);
    }
    xSemaphoreGive(runtime_lock);
    cJSON_AddNumberToObject(j,"matched",matched);cJSON_AddNumberToObject(j,"offset",offset);
    cJSON_AddStringToObject(j,"inventory_quality","backup metadata; installed content and event mapping require validation");
    return json(r,j);
}
esp_err_t web_register(httpd_handle_t server) {
    const httpd_uri_t routes[]={
        {.uri="/",.method=HTTP_GET,.handler=page},{.uri="/app.js",.method=HTTP_GET,.handler=page},
        {.uri="/api/v1/printer",.method=HTTP_GET,.handler=printer_get},
        {.uri="/api/v1/devices",.method=HTTP_GET,.handler=devices_get}};
    for(size_t i=0;i<sizeof(routes)/sizeof(routes[0]);i++){esp_err_t err=httpd_register_uri_handler(server,&routes[i]);if(err!=ESP_OK)return err;}
    return ESP_OK;
}

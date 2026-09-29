#include "gateway.h"
#include "cJSON.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#ifdef ESP_PLATFORM
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#endif

static void cooperate(size_t progress,size_t interval) {
#ifdef ESP_PLATFORM
    if(progress%interval==0)vTaskDelay(1);
#else
    (void)progress;(void)interval;
#endif
}

static bool field_string(cJSON *obj, const char *key, char *out, size_t capacity) {
    cJSON *v=cJSON_GetObjectItemCaseSensitive(obj,key);
    if (!cJSON_IsString(v) || strlen(v->valuestring)>=capacity) return false;
    strcpy(out,v->valuestring); return true;
}
static bool number(cJSON *v, uint32_t min, uint32_t max, uint32_t *out) {
    if (!cJSON_IsNumber(v) || !isfinite(v->valuedouble) || v->valuedouble<min || v->valuedouble>max || floor(v->valuedouble)!=v->valuedouble) return false;
    *out=(uint32_t)v->valuedouble; return true;
}
static int compare_ids(const void *a,const void *b) {
    uint32_t x=*(const uint32_t*)a,y=*(const uint32_t*)b; return (x>y)-(x<y);
}
/* Iterative merge sort: bounded stack and explicit scheduling points on P4.
   The second half of the allocation is scratch space, never published. */
static void order_devices(gw_device **items,size_t count,bool address) {
    gw_device **source=items,**target=items+count;
    for(size_t width=1;width<count;width*=2) {
        for(size_t base=0;base<count;base+=2*width) {
            size_t middle=base+width<count?base+width:count,end=base+2*width<count?base+2*width:count;
            size_t left=base,right=middle;
            for(size_t out=base;out<end;out++) {
                bool take_left=right==end||(left<middle&&strcmp(address?source[left]->address:source[left]->uuid,address?source[right]->address:source[right]->uuid)<=0);
                target[out]=source[take_left?left++:right++];
            }
            cooperate(base,128);
        }
        gw_device **swap=source;source=target;target=swap;
    }
    if(source!=items)memcpy(items,source,count*sizeof(*items));
}
static gw_device *find_uuid(const char *uuid,gw_device **ordered,size_t count) {
    size_t left=0,right=count;
    while(left<right) {
        size_t middle=left+(right-left)/2;int result=strcmp(uuid,ordered[middle]->uuid);
        if(!result)return ordered[middle];
        if(result<0)right=middle;else left=middle+1;
    }
    return NULL;
}
static bool keys(cJSON *obj,const char *const *allowed) {
    for(cJSON *v=obj->child;v;v=v->next) {
        if(!v->string) return false;
        bool found=false;
        for(size_t i=0;allowed[i];i++) if(!strcmp(v->string,allowed[i])) found=true;
        if(!found) return false;
        for(cJSON *u=v->next;u;u=u->next) if(u->string&&!strcmp(v->string,u->string)) return false;
    }
    return true;
}
bool gw_parse_registry(const char *json,size_t size,const gw_registry *old,bool allow_simulation,gw_registry *out,char *error,size_t error_size) {
    const char *why="invalid registry";
    cJSON *root=NULL;
    uint32_t *ids=NULL;
    gw_device **ordered=NULL;
    if(!json||!out||size==0||size>GW_MAX_JSON) goto fail;
    for(size_t i=0;i<size;i++) {
        if(json[i]==0 && i!=size-1)goto fail;
        if(i+6<=size&&!memcmp(json+i,"\\u0000",6))goto fail;
    }
    const char *end=NULL;
    root=cJSON_ParseWithLengthOpts(json,size,&end,false);
    if(!cJSON_IsObject(root)) goto fail;
    while(end<json+size && (*end==' '||*end=='\r'||*end=='\n'||*end=='\t')) end++;
    if(end<json+size && !(end==json+size-1 && *end==0)) goto fail;
    const char *const top[]={"schema_version","epoch","source_mode","devices","provenance",NULL};
    if(!keys(root,top)) goto fail;
    uint32_t version;
    if(!number(cJSON_GetObjectItemCaseSensitive(root,"schema_version"),1,1,&version) || !number(cJSON_GetObjectItemCaseSensitive(root,"epoch"),1,UINT32_MAX,&out->epoch)) goto fail;
    char mode[32];
    if(!field_string(root,"source_mode",mode,sizeof(mode))) goto fail;
    out->simulation=!strcmp(mode,"simulation");
    if(out->simulation&&!allow_simulation) {why="simulation forbidden in production";goto fail;}
    if(strcmp(mode,"simulation")&&strcmp(mode,"contractor_export_verified")&&strcmp(mode,"est3_sdu_v1")) goto fail;
    if(!strcmp(mode,"est3_sdu_v1")) {
        cJSON *p=cJSON_GetObjectItemCaseSensitive(root,"provenance");
        const char *const fields[]={"archive_sha256","installed_match",NULL};
        if(!cJSON_IsObject(p)||!keys(p,fields)||!field_string(p,"archive_sha256",out->source_hash,sizeof(out->source_hash))||strlen(out->source_hash)!=64||
           !field_string(p,"installed_match",out->source_quality,sizeof(out->source_quality))||strcmp(out->source_quality,"backup_only_not_live_verified"))goto fail;
        for(unsigned i=0;i<64;i++)if(!((out->source_hash[i]>='0'&&out->source_hash[i]<='9')||(out->source_hash[i]>='a'&&out->source_hash[i]<='f')))goto fail;
    }
    cJSON *devices=cJSON_GetObjectItemCaseSensitive(root,"devices");
    if(!cJSON_IsArray(devices) || cJSON_GetArraySize(devices)>GW_MAX_DEVICES) goto fail;
    out->count=cJSON_GetArraySize(devices);
    if(old && out->epoch<=old->epoch) {why="obsolete registry epoch";goto fail;}
    ids=calloc(out->count*5+1,sizeof(uint32_t));
    ordered=calloc(out->count*2+1,sizeof(*ordered));
    if(!ids||!ordered) {why="allocation failed";goto fail;}
    size_t index=0;
    cJSON *item;
    cJSON_ArrayForEach(item,devices) {
        cooperate(index,32);
        const char *const fields[]={"uuid","address","type","label","label_truncated","binding_epoch","instances","supported","retired",NULL};
        if(!cJSON_IsObject(item)||!keys(item,fields)) goto fail;
        gw_device *d=&out->devices[index];
        ordered[index]=d;
        memset(d,0,sizeof(*d));
        if(!field_string(item,"uuid",d->uuid,sizeof(d->uuid)) || strlen(d->uuid)!=36 || !field_string(item,"address",d->address,sizeof(d->address)) || !field_string(item,"type",d->type,sizeof(d->type)) || !field_string(item,"label",d->label,sizeof(d->label))) goto fail;
        for(size_t j=0;j<36;j++) {
            bool dash=j==8||j==13||j==18||j==23;
            if(dash ? d->uuid[j]!='-' : !((d->uuid[j]>='0'&&d->uuid[j]<='9')||(d->uuid[j]>='a'&&d->uuid[j]<='f'))) goto fail;
        }
        uint32_t supported;
        if(!number(cJSON_GetObjectItemCaseSensitive(item,"binding_epoch"),1,out->epoch,&d->binding_epoch) || !number(cJSON_GetObjectItemCaseSensitive(item,"supported"),0,15,&supported)) goto fail;
        if(!strcmp(mode,"est3_sdu_v1")&&supported!=0){why="SDU metadata does not establish supported live conditions";goto fail;}
        d->supported=supported;
        cJSON *retired=cJSON_GetObjectItemCaseSensitive(item,"retired");
        if(!cJSON_IsBool(retired)) goto fail;
        d->retired=cJSON_IsTrue(retired);
        cJSON *instances=cJSON_GetObjectItemCaseSensitive(item,"instances");
        if(!cJSON_IsArray(instances)||cJSON_GetArraySize(instances)!=5) goto fail;
        for(unsigned k=0;k<5;k++) {
            if(!number(cJSON_GetArrayItem(instances,k),100,4194302,&d->instances[k])) goto fail;
            ids[index*5+k]=d->instances[k];
        }
        index++;
    }
    qsort(ids,out->count*5,sizeof(uint32_t),compare_ids);
    for(size_t j=1;j<out->count*5;j++) if(ids[j]==ids[j-1]) {why="BACnet instance collision";goto fail;}
    order_devices(ordered,out->count,false);
    for(size_t j=1;j<out->count;j++)if(!strcmp(ordered[j-1]->uuid,ordered[j]->uuid)){why="duplicate device/address";goto fail;}
    /* Retaining every prior UUID with identical slots, plus unique new slots,
       proves no tombstone slot can be reused. Avoid N*N*25 PSRAM comparisons
       while holding the embedded registry lock. */
    if(old) for(size_t j=0;j<old->count;j++) {
        cooperate(j,32);
        const gw_device *p=&old->devices[j];
        gw_device *d=find_uuid(p->uuid,ordered,out->count);
        if(!d) {why="tombstones must be retained";goto fail;}
        if(memcmp(d->instances,p->instances,sizeof(d->instances))) {why="binding instances cannot change";goto fail;}
        bool changed=strcmp(d->address,p->address)||strcmp(d->type,p->type)||d->supported!=p->supported||d->retired!=p->retired;
        if(d->binding_epoch<p->binding_epoch || (changed&&d->binding_epoch<=p->binding_epoch)) {why="binding epoch did not advance";goto fail;}
        if(!changed&&d->binding_epoch==p->binding_epoch)memcpy(d->conditions,p->conditions,sizeof(d->conditions));
    }
    order_devices(ordered,out->count,true);
    const gw_device *previous=NULL;
    for(size_t j=0;j<out->count;j++)if(!ordered[j]->retired) {
        if(previous&&!strcmp(previous->address,ordered[j]->address)){why="duplicate device/address";goto fail;}
        previous=ordered[j];
    }
    free(ordered);free(ids);cJSON_Delete(root);return true;
fail:
    if(error&&error_size) snprintf(error,error_size,"%s",why);
    free(ordered);free(ids);cJSON_Delete(root);return false;
}
bool gw_condition_valid(const gw_device *d,unsigned k,uint64_t now) {
    if(k>=4||d->retired||!(d->supported&(1u<<k))) return false;
    const gw_condition *c=&d->conditions[k];
    return c->known&&c->synchronized&&now>=c->observed_ms&&now-c->observed_ms<=GW_STALE_MS;
}
bool gw_data_valid(const gw_device *d,uint64_t now) {
    if(d->retired||!d->supported) return false;
    for(unsigned k=0;k<4;k++) if((d->supported&(1u<<k))&&!gw_condition_valid(d,k,now)) return false;
    return true;
}
void gw_invalidate(gw_registry *r) {
    for(size_t i=0;i<r->count;i++) for(unsigned k=0;k<4;k++) r->devices[i].conditions[k].synchronized=false;
}
bool gw_observe(gw_device *d,uint32_t epoch,unsigned k,bool value,uint64_t now,uint64_t seq,bool snapshot) {
    if(k>=4||d->retired||d->binding_epoch!=epoch||!(d->supported&(1u<<k))) return false;
    gw_condition *c=&d->conditions[k];
    if(c->known&&seq<=c->sequence) return false;
    c->known=true;c->value=value;c->observed_ms=now;c->sequence=seq;
    if(snapshot) c->synchronized=true;
    return true;
}

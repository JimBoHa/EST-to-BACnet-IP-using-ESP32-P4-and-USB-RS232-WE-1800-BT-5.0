#include "gateway.h"
#include "cJSON.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static bool parse(cJSON *json,const gw_registry *old,gw_registry *out) {
    char error[128],*body=cJSON_PrintUnformatted(json);assert(body);
    bool okay=gw_parse_registry(body,strlen(body),old,true,out,error,sizeof(error));
    free(body);return okay;
}
int main(void) {
    cJSON *root=cJSON_CreateObject(),*devices=cJSON_AddArrayToObject(root,"devices");
    cJSON_AddNumberToObject(root,"schema_version",1);cJSON_AddNumberToObject(root,"epoch",1);
    cJSON_AddStringToObject(root,"source_mode","simulation");
    for(unsigned i=0;i<GW_MAX_DEVICES;i++) {
        char uuid[37],address[32];snprintf(uuid,sizeof(uuid),"00000000-0000-0000-0000-%012u",i);
        snprintf(address,sizeof(address),"SYNTHETIC %u",i);
        cJSON *d=cJSON_CreateObject();cJSON_AddItemToArray(devices,d);
        cJSON_AddStringToObject(d,"uuid",uuid);cJSON_AddStringToObject(d,"address",address);
        cJSON_AddStringToObject(d,"label","Simulation only");cJSON_AddStringToObject(d,"type","test");
        cJSON_AddNumberToObject(d,"binding_epoch",1);cJSON_AddNumberToObject(d,"supported",3);
        cJSON_AddBoolToObject(d,"retired",false);cJSON *ids=cJSON_AddArrayToObject(d,"instances");
        for(unsigned k=0;k<5;k++)cJSON_AddItemToArray(ids,cJSON_CreateNumber(100+5*i+k));
    }
    gw_registry *old=calloc(1,sizeof(*old)),*next=calloc(1,sizeof(*next));assert(old&&next);
    clock_t start=clock();assert(parse(root,NULL,old));assert(old->count==GW_MAX_DEVICES);
    cJSON_SetNumberValue(cJSON_GetObjectItem(root,"epoch"),2);
    cJSON *reverse=cJSON_CreateArray();
    for(unsigned i=0;i<GW_MAX_DEVICES;i++)cJSON_AddItemToArray(reverse,cJSON_DetachItemFromArray(devices,GW_MAX_DEVICES-i-1));
    cJSON_ReplaceItemInObject(root,"devices",reverse);devices=reverse;
    assert(gw_observe(&old->devices[0],1,0,true,100,1,true));
    assert(parse(root,old,next));assert(next->devices[GW_MAX_DEVICES-1].conditions[0].value);
    cJSON *first=cJSON_GetArrayItem(devices,0),*last=cJSON_GetArrayItem(devices,GW_MAX_DEVICES-1);
    cJSON_ReplaceItemInObject(first,"uuid",cJSON_CreateString("ffffffff-ffff-ffff-ffff-ffffffffffff"));
    assert(!parse(root,old,next)); /* Dropping old identity cannot release its slots. */
    cJSON_ReplaceItemInObject(first,"uuid",cJSON_CreateString(old->devices[GW_MAX_DEVICES-1].uuid));
    cJSON *a=cJSON_DetachItemFromObject(first,"instances"),*b=cJSON_DetachItemFromObject(last,"instances");
    cJSON_AddItemToObject(first,"instances",b);cJSON_AddItemToObject(last,"instances",a);
    assert(!parse(root,old,next)); /* Globally unique swapped bindings remain forbidden. */
    cJSON_DetachItemFromObject(first,"instances");cJSON_DetachItemFromObject(last,"instances");
    cJSON_AddItemToObject(first,"instances",a);cJSON_AddItemToObject(last,"instances",b);
    cJSON_ReplaceItemInObject(first,"address",cJSON_CreateString(old->devices[0].address));
    cJSON_SetNumberValue(cJSON_GetObjectItem(first,"binding_epoch"),2);
    assert(!parse(root,old,next));
    cJSON_ReplaceItemInObject(first,"retired",cJSON_CreateBool(true));
    assert(parse(root,old,next)); /* Retired address may coexist, slots still reserved. */
    printf("PASS: %u records; reordered lookup, state retention, immutable slots, tombstones and active address uniqueness (%.3f native CPU seconds)\n",GW_MAX_DEVICES,(double)(clock()-start)/CLOCKS_PER_SEC);
    cJSON_Delete(root);free(old);free(next);return 0;
}

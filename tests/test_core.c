#include "gateway.h"
#include "cJSON.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char **argv) {
    assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);char *text=calloc(1,GW_MAX_JSON+1);size_t len=fread(text,1,GW_MAX_JSON,f);fclose(f);
    gw_registry *r=calloc(1,sizeof(*r)),*next=calloc(1,sizeof(*next));char error[128];
    assert(!gw_parse_registry(text,len,NULL,false,r,error,sizeof(error)));
    assert(gw_parse_registry(text,len,NULL,true,r,error,sizeof(error)));
    assert(r->count==2);gw_device *d=&r->devices[0];assert(!gw_data_valid(d,100));
    assert(gw_observe(d,1,0,false,100,1,true));assert(gw_observe(d,1,1,false,100,1,true));assert(gw_data_valid(d,100));
    assert(gw_observe(d,1,0,true,101,2,false));assert(gw_observe(d,1,1,true,102,2,false));assert(gw_observe(d,1,0,false,103,3,false));assert(d->conditions[1].value);
    assert(!gw_observe(d,1,0,true,104,2,false));assert(!gw_observe(d,2,0,true,104,4,false));
    assert(!gw_data_valid(d,60104));gw_invalidate(r);assert(!gw_data_valid(d,104));
    cJSON *root=cJSON_Parse(text);cJSON_SetNumberValue(cJSON_GetObjectItem(root,"epoch"),2);
    cJSON *first=cJSON_GetArrayItem(cJSON_GetObjectItem(root,"devices"),0);cJSON_ReplaceItemInObject(first,"label",cJSON_CreateString("renamed"));char *changed=cJSON_PrintUnformatted(root);
    assert(gw_parse_registry(changed,strlen(changed),r,true,next,error,sizeof(error)));assert(next->devices[0].instances[0]==d->instances[0]);assert(next->devices[0].conditions[1].value);free(changed);
    cJSON *ids=cJSON_GetObjectItem(first,"instances");cJSON_SetNumberValue(cJSON_GetArrayItem(ids,1),cJSON_GetArrayItem(ids,0)->valuedouble);changed=cJSON_PrintUnformatted(root);
    assert(!gw_parse_registry(changed,strlen(changed),r,true,next,error,sizeof(error)));free(changed);cJSON_Delete(root);
    for(size_t n=0;n<len;n++)assert(!gw_parse_registry(text,n,NULL,true,next,error,sizeof(error)));
    unsigned x=1;
    for(unsigned i=0;i<10000;i++){char junk[256];for(unsigned j=0;j<sizeof(junk);j++){x=x*1664525u+1013904223u;junk[j]=(char)(x>>24);}gw_parse_registry(junk,i%256,NULL,true,next,error,sizeof(error));}
    puts("PASS: production simulation rejection, registry validation, state/freshness, epochs, collisions, truncations, 10000 malformed inputs");free(text);free(r);free(next);return 0;
}

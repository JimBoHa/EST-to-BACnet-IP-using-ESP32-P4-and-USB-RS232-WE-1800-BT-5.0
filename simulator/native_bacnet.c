/* SIMULATION_ONLY executable for disconnected lab/software tests.
   Never linked into firmware; no USB or serial transmit interface. */
#include "bacnet_gateway.h"
#include "cJSON.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
static char *read_file(const char *path,size_t *size) {
    FILE *f=fopen(path,"rb");if(!f)return NULL;char *buf=malloc(GW_MAX_JSON+1);if(!buf){fclose(f);return NULL;}
    *size=fread(buf,1,GW_MAX_JSON,f);buf[*size]=0;fclose(f);return buf;
}
int main(int argc,char **argv) {
    if(argc<3){fprintf(stderr,"Usage: sim_bacnet registry.json state.json [port]\n");return 2;}
    gw_registry *r=calloc(1,sizeof(*r));size_t size;char *buf=read_file(argv[1],&size);char error[128];
    if(!buf||!gw_parse_registry(buf,size,NULL,true,r,error,sizeof(error))){fprintf(stderr,"Invalid simulation registry\n");return 2;}free(buf);
    if(!bg_start(3899001,"127.0.0.1",argc>3?atoi(argv[3]):47808,"127.0.0.1")||!bg_registry(r))return 3;
    puts("SIMULATION_ONLY BACnet Device 3899001 on localhost");fflush(stdout);
    uint64_t last=0,last_poll=0;
    for(;;) {
        bg_poll(20,false);
        if(bg_now()-last_poll<100)continue;last_poll=bg_now();
        buf=read_file(argv[1],&size);
        if(buf) {gw_registry *next=calloc(1,sizeof(*next));if(gw_parse_registry(buf,size,r,true,next,error,sizeof(error))&&bg_registry(next)){free(r);r=next;}else free(next);free(buf);}
        buf=read_file(argv[2],&size);if(!buf)continue;cJSON *root=cJSON_ParseWithLength(buf,size);free(buf);if(!root)continue;
        cJSON *seq=cJSON_GetObjectItem(root,"sequence");
        if(cJSON_IsNumber(seq)&&(uint64_t)seq->valuedouble>last) {
            last=seq->valuedouble;
            if(cJSON_IsTrue(cJSON_GetObjectItem(root,"invalidate")))gw_invalidate(r);
            cJSON *item;
            cJSON_ArrayForEach(item,cJSON_GetObjectItem(root,"observations")) {
                cJSON *uuid=cJSON_GetObjectItem(item,"uuid"),*k=cJSON_GetObjectItem(item,"condition"),*epoch=cJSON_GetObjectItem(item,"epoch"),*value=cJSON_GetObjectItem(item,"value");
                if(!cJSON_IsString(uuid)||!cJSON_IsNumber(k)||!cJSON_IsNumber(epoch)||!cJSON_IsBool(value))continue;
                for(size_t i=0;i<r->count;i++)if(!strcmp(uuid->valuestring,r->devices[i].uuid))gw_observe(&r->devices[i],epoch->valuedouble,k->valuedouble,cJSON_IsTrue(value),bg_now(),last,cJSON_IsTrue(cJSON_GetObjectItem(item,"snapshot")));
            }
        }
        cJSON_Delete(root);
    }
}

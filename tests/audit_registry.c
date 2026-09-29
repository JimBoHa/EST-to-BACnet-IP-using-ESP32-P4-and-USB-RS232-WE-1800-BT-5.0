#include "gateway.h"
#include "bacnet_gateway.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    FILE *f=fopen(argv[1],"rb");if(!f)return 2;
    char *data=calloc(1,GW_MAX_JSON+1);gw_registry *r=calloc(1,sizeof(*r));if(!data||!r)return 2;
    size_t n=fread(data,1,GW_MAX_JSON,f);fclose(f);char error[128];
    if(!gw_parse_registry(data,n,NULL,false,r,error,sizeof(error))){fprintf(stderr,"%s\n",error);return 1;}
    if(!bg_start(3899001,"127.0.0.1",47991,"127.0.0.1")||!bg_registry(r))return 1;
    for(size_t i=0;i<r->count;i++)if(gw_data_valid(&r->devices[i],0))return 1;
    printf("PASS: production registry %zu objects; %zu BIs allocated; all current values invalid\n",r->count,r->count*5+4);
    /* BACnet stack retains label references until process teardown. */
    return 0;
}

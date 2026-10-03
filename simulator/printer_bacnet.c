/* DISCONNECTED FIXTURE executable. No network injection endpoint or serial I/O.
   Runs the production parser, restricted observer and BACnet stack on localhost. */
#include "printer_observer.h"
#include "bacnet_gateway.h"
#include <stdio.h>
#include <stdlib.h>

int main(int argc,char **argv) {
    if(argc!=4)return 2;
    FILE *f=fopen(argv[1],"rb");if(!f)return 2;
    char *json=calloc(1,GW_MAX_JSON+1);gw_registry *r=calloc(1,sizeof(*r));pr_parser *p=calloc(1,sizeof(*p));
    if(!json||!r||!p)return 2;
    size_t n=fread(json,1,GW_MAX_JSON,f);fclose(f);char error[128];
    if(!gw_parse_registry(json,n,NULL,false,r,error,sizeof(error)))return 2;free(json);
    if(!bg_start(3899001,"127.0.0.1",atoi(argv[3]),"127.0.0.1")||!bg_registry(r))return 3;
    pr_init(p);p->event_sink=gw_record_printer_trouble;p->event_context=r;
    f=fopen(argv[2],"rb");if(!f)return 2;
    puts("FIXTURE_ONLY printer-to-BACnet ready");fflush(stdout);
    for(;;) {
        uint8_t data[64];clearerr(f);n=fread(data,1,sizeof(data),f);
        if(n)pr_feed(p,1,p->next_offset,bg_now(),data,n,false);
        bg_poll(10,true);
    }
}

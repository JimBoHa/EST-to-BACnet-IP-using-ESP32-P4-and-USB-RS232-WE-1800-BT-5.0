#include "printer.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc,char **argv) {
    assert(argc==2);FILE *file=fopen(argv[1],"rb");assert(file);
    uint8_t raw[8192];size_t length=fread(raw,1,sizeof(raw)-1,file);assert(length&&feof(file));raw[length]=0;fclose(file);
    pr_parser *p=calloc(1,sizeof(*p));assert(p);
    for(size_t split=1;split<=length;split++) {
        pr_init(p);pr_feed(p,1,0,100,raw,split,false);
        pr_feed(p,1,split,200,raw+split,length-split,false);
        assert(p->reports_complete==1&&p->last_complete.panel==1);
        assert(!strcmp(p->last_complete.cpu,"V05.30.00"));
        assert(p->last_complete.card_count==5);
        assert(p->last_complete.historical_alarm_count==7);
        assert(p->unknown==0);
    }
    pr_init(p);
    for(size_t i=0;i<length;i++)pr_feed(p,1,i,i,raw+i,1,false);
    assert(p->reports_complete==1);
    pr_feed(p,1,length,5000,raw,length,false);
    assert(p->reports_complete==2); /* distinct observations, never current alarms */
    for(size_t stop=0;stop<length;stop++) {
        pr_init(p);pr_feed(p,1,0,0,raw,stop,false);
        pr_gap(p,2,stop,10,"test disconnect");
        pr_feed(p,2,stop,20,raw+stop,length-stop,false);
        /* Only a fully received report may finish across this experiment. */
        if(stop>strstr((char*)raw,"REVISION REPORT")-(char*)raw+16&&stop<length-24)
            assert(p->reports_complete==0);
    }
    pr_init(p);pr_feed(p,1,0,0,raw,200,false);
    const uint8_t unknown[]="unexpected alarm-like text\n";
    pr_feed(p,1,200,1,unknown,sizeof(unknown)-1,false);
    pr_feed(p,1,200+sizeof(unknown)-1,2,raw+200,length-200,false);
    assert(!p->reports_complete&&p->unknown);
    pr_init(p);uint8_t oversized[PR_LINE_MAX*3+1];memset(oversized,'X',sizeof(oversized));oversized[sizeof(oversized)-1]='\n';
    pr_feed(p,1,0,0,oversized,sizeof(oversized),false);
    assert(p->fragments==3&&p->partial_length==0);
    const uint8_t binary[]={0,255,'A','\r','\n'};
    pr_feed(p,1,sizeof(oversized),1,binary,sizeof(binary),false);
    assert(p->unknown==1);
    uint64_t offset=sizeof(oversized)+sizeof(binary);
    for(unsigned i=0;i<10000;i++){pr_feed(p,1,offset,i,(const uint8_t*)"unknown\n",8,false);offset+=8;}
    assert(p->count==PR_RECENT_COUNT&&p->evicted>0);
    assert(pr_recent(p,0)->id==p->next_id-PR_RECENT_COUNT);
    assert(pr_recent(p,PR_RECENT_COUNT)==NULL);
    pr_init(p);pr_feed(p,1,0,0,raw,length,true);assert(!p->reports_complete);
    free(p);puts("printer split/replay/truncation/gap/interleaving/binary/overflow tests passed");return 0;
}

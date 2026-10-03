#include "printer_observer.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char act[]="\r\nCOMMON TRBL ACT  ::  12:25:51 02/01/2026  P:02  C:04  D:0012\r\nTEST MODULE\r\n\r\n";
static const char rst[]="\r\nCOMMON TRBL RST  ::  12:25:56 02/01/2026  P:02  C:04  D:0012\r\nTEST MODULE\r\n\r\n";
static void feed(pr_parser *p,const char *s,uint64_t now) {
    pr_feed(p,p->initialized?p->epoch:1,p->next_offset,now,(const uint8_t*)s,strlen(s),false);
}
static void reset(pr_parser *p,gw_registry *r) {
    pr_init(p);memset(r,0,sizeof(*r));r->epoch=1;r->count=2;
    strcpy(r->source_quality,"backup_only_not_live_verified");
    strcpy(r->devices[0].address,"P02 C01 D0611");strcpy(r->devices[1].address,"P02 C04 D0012");
    for(unsigned i=0;i<2;i++)r->devices[i].binding_epoch=1;
    p->event_sink=gw_record_printer_trouble;p->event_context=r;
}
static void invalid(const gw_registry *r) {
    for(size_t i=0;i<r->count;i++) {
        const gw_device *d=&r->devices[i];assert(!d->supported&&!gw_data_valid(d,100));
        for(unsigned k=0;k<4;k++){assert(!gw_condition_valid(d,k,100));if(k!=1)assert(!d->conditions[k].known);}
    }
}
int main(int argc,char **argv) {
    assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);
    uint8_t raw[4096];size_t n=fread(raw,1,sizeof(raw),f);assert(n&&feof(f));fclose(f);
    pr_parser *p=calloc(1,sizeof(*p));gw_registry *r=calloc(1,sizeof(*r));assert(p&&r);
    /* Every split in the sanitized eight-event field capture, including CRLF. */
    for(size_t split=0;split<=n;split++) {
        reset(p,r);pr_feed(p,1,0,100,raw,split,false);pr_feed(p,1,split,200,raw+split,n-split,false);
        assert(p->events_complete==8&&p->events_mapped==8&&p->event_count==8);
        assert(r->devices[0].conditions[1].known&&!r->devices[0].conditions[1].value);
        assert(r->devices[1].conditions[1].known&&!r->devices[1].conditions[1].value);invalid(r);
        assert(pr_recent_event(p,0)->type==PR_LOCAL_TROUBLE);
        assert(pr_recent_event(p,7)->type==PR_COMMON_TROUBLE);
    }
    reset(p,r);for(size_t i=0;i<n;i++)pr_feed(p,1,i,i,raw+i,1,false);
    assert(p->events_mapped==8);invalid(r);
    /* Gaps at every byte of a single frame never splice a partial event. */
    size_t length=strlen(act);
    for(size_t cut=3;cut<length-2;cut++) {
        reset(p,r);pr_feed(p,1,0,100,(const uint8_t*)act,cut,false);
        pr_gap(p,2,cut,101,"fixture loss");pr_feed(p,2,cut,102,(const uint8_t*)act+cut,length-cut,false);
        assert(p->events_complete==0&&!r->devices[1].conditions[1].known);
        feed(p,act,200);assert(p->events_mapped==1);invalid(r);
    }
    reset(p,r);feed(p,act,100);assert(r->devices[1].conditions[1].value);invalid(r);
    feed(p,act,200);assert(p->events_ignored==1&&r->devices[1].conditions[1].observed_ms==100);
    feed(p,rst,300);assert(!r->devices[1].conditions[1].value);invalid(r);
    feed(p,act,400);assert(p->events_ignored==2&&!r->devices[1].conditions[1].value);
    assert(r->devices[1].conditions[1].observed_ms==300);
    /* Another class/address never clears a different device or condition. */
    feed(p,"\nLOCAL TRBL ACT  ::  12:26:00 02/01/2026  P:02  C:01  D:0611\nTEST BATTERY\n\n",500);
    assert(r->devices[0].conditions[1].value&&!r->devices[1].conditions[1].value);invalid(r);
    reset(p,r);r->devices[1].retired=true;feed(p,act,100);assert(p->events_unmatched==1);
    reset(p,r);r->simulation=true;feed(p,act,100);assert(p->events_unmatched==1);
    reset(p,r);r->devices[1].supported=2;feed(p,act,100);assert(p->events_unmatched==1&&!r->devices[1].conditions[1].known);
    reset(p,r);strcpy(r->devices[1].address,"P02 C04 D0013");feed(p,act,100);assert(p->events_unmatched==1&&r->count==2);
    /* Reports, unsupported classes/actions, malformed dates, incomplete frames. */
    const char *bad[]={
        "\nHISTORY REPORT\n", "\nREVISION REPORT\n",
        "\nCOMMON TRBL ACT  ::  12:25:51 02/30/2026  P:02  C:04  D:0012\nTEST MODULE\n\n",
        "\nCOMMON TRBL RST  ::  24:25:51 02/01/2026  P:02  C:04  D:0012\nTEST MODULE\n\n",
        "\nCOMMON TRBL ACK  ::  12:25:51 02/01/2026  P:02  C:04  D:0012\nTEST MODULE\n\n",
        "\nCOMMON TRBL ACT  ::  12:25:51 02/01/2026  P:2  C:04  D:0012\nTEST MODULE\n\n",
        "\nCOMMON ALRM ACT  ::  12:25:51 02/01/2026  P:02  C:04  D:0012\nTEST MODULE\n\n",
        "\nCOMMON TRBL ACT  ::  12:25:51 02/01/2026  P:02  C:04  D:0012\nTEST MODULE\nEXTRA\n\n",
        "\nCOMMON TRBL ACT  ::  12:25:51 02/01/2026  P:02  C:04  D:0012\n\n",
        "\nCOMMON TRBL ACT  ::  12:25:51 02/01/2026  P:02  C:04  D:0012\n-OPERATOR COMMAND-\n\n"
    };
    for(unsigned i=0;i<sizeof(bad)/sizeof(*bad);i++) {
        reset(p,r);feed(p,bad[i],100);if(i<2)feed(p,act,200);
        assert(p->events_complete==0);invalid(r);
    }
    reset(p,r);pr_feed(p,1,0,100,(const uint8_t*)act,length,true);assert(!p->events_complete);
    reset(p,r);pr_feed(p,1,0,100,(const uint8_t*)act,length-4,false);feed(p,"\r\n\r\n",6000);assert(!p->events_complete);
    reset(p,r);feed(p,"\nCOMMON TRBL ACT  ::  12:25:51 02/01/2026  P:02  C:04  D:0012\n",100);
    uint8_t binary[]={0,255,'\n','\n'};pr_feed(p,1,p->next_offset,101,binary,sizeof(binary),false);assert(!p->events_complete);
    reset(p,r);for(unsigned i=0;i<1000;i++)feed(p,act,i);
    assert(p->event_count==PR_EVENT_COUNT&&p->events_complete==1000&&p->events_mapped==1&&p->events_ignored==999);
    assert(pr_recent_event(p,PR_EVENT_COUNT)==NULL);invalid(r);
    free(p);free(r);puts("trouble observations: exhaustive splits/loss, ACT/RST mapping, report inhibition, replay, unknowns, bounds and invalid quality passed");
    return 0;
}

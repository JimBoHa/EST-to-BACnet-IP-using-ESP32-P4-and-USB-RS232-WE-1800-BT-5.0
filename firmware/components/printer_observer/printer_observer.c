#include "printer_observer.h"
#include <stdio.h>
#include <string.h>

pr_event_result gw_record_printer_trouble(void *registry,const pr_event *e) {
    gw_registry *r=registry;
    if(!r||r->simulation||strcmp(r->source_quality,"backup_only_not_live_verified")||
       (e->type!=PR_LOCAL_TROUBLE&&e->type!=PR_COMMON_TROUBLE))return PR_UNMATCHED;
    char address[32];snprintf(address,sizeof(address),"P%02u C%02u D%04u",e->panel,e->card,e->device);
    for(size_t i=0;i<r->count;i++) {
        gw_device *d=&r->devices[i];
        if(d->retired||d->supported||strcmp(d->address,address))continue;
        gw_condition *c=&d->conditions[1];
        gw_printer_observation *p=&d->printer_trouble;
        if(c->known&&(e->id<=c->sequence||e->received_ms<c->observed_ms||e->source_order<p->source_order||
           (e->source_order==p->source_order&&e->type==p->type&&e->active==c->value)))return PR_IGNORED;
        c->known=true;c->value=e->active;c->observed_ms=e->received_ms;c->sequence=e->id;
        /* An event restore does not prove absence of other trouble subtypes,
           startup conditions, omitted events, or printed history. Never normal. */
        c->synchronized=false;
        p->source_order=e->source_order;p->offset=e->offset;p->stream_epoch=e->epoch;
        p->type=e->type;memcpy(p->source_time,e->source_time,sizeof(p->source_time));
        return PR_MAPPED;
    }
    return PR_UNMATCHED;
}

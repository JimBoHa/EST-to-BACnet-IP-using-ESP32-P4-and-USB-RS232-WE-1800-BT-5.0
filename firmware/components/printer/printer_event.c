/* Strict grammar from captured CPU 05.30 LOCAL/COMMON TRBL ACT/RST records.
 * Live versus printed-history origin and total device state are NOT established.
 * Require blank/header/text/blank; never complete a frame across loss/corruption.
 */
#include "printer.h"
#include <stdio.h>
#include <string.h>

void pr_event_reset(pr_parser *p) {
    if(p->event_stage)p->events_incomplete++;
    p->event_stage=0;p->event_boundary=false;
}
static bool header(const char *s,pr_event *e) {
    const char *prefix;
    if(!strncmp(s,"LOCAL TRBL ",11)){prefix="LOCAL TRBL";e->type=PR_LOCAL_TROUBLE;}
    else if(!strncmp(s,"COMMON TRBL ",12)){prefix="COMMON TRBL";e->type=PR_COMMON_TROUBLE;}
    else return false;
    char action[4],expected[96];unsigned h,m,sec,month,day,year;int used=0;
    if(sscanf(s+strlen(prefix)," %3s  ::  %2u:%2u:%2u %2u/%2u/%4u  P:%2u  C:%2u  D:%4u%n",
              action,&h,&m,&sec,&month,&day,&year,&e->panel,&e->card,&e->device,&used)!=10 ||
       s[strlen(prefix)+used] || (strcmp(action,"ACT")&&strcmp(action,"RST")))return false;
    if(h>23||m>59||sec>59||month<1||month>12||year<2000||year>9999||e->panel<1)return false;
    static const unsigned days[]={31,28,31,30,31,30,31,31,30,31,30,31};
    unsigned max_day=days[month-1]+(month==2&&year%4==0&&(year%100!=0||year%400==0));
    if(day<1||day>max_day)return false;
    snprintf(expected,sizeof(expected),"%s %s  ::  %02u:%02u:%02u %02u/%02u/%04u  P:%02u  C:%02u  D:%04u",
             prefix,action,h,m,sec,month,day,year,e->panel,e->card,e->device);
    if(strcmp(expected,s))return false; /* Reject shortened fields and changed delimiters. */
    e->active=!strcmp(action,"ACT");
    snprintf(e->source_time,sizeof(e->source_time),"%02u:%02u:%02u %02u/%02u/%04u",h,m,sec,month,day,year);
    e->source_order=((((((uint64_t)year*100+month)*100+day)*100+h)*100+m)*100+sec);
    return true;
}
pr_kind pr_event_line(pr_parser *p,const char *s) {
    size_t n=strlen(s);
    if(p->event_stage&&(p->received_ms<p->pending_event.received_ms||
       p->received_ms-p->pending_event.received_ms>5000))pr_event_reset(p);
    /* Known report boundaries inhibit observations. Unknown history formats
       still cannot assert current quality: the sink always leaves it invalid. */
    if(strstr(s,"REPORT")){pr_event_reset(p);p->event_report=true;return PR_UNKNOWN;}
    if(!strcmp(s,"**END: COMPLETE**")){pr_event_reset(p);p->event_report=false;return PR_BOUNDARY;}
    if(p->event_report)return n?PR_UNKNOWN:PR_BOUNDARY;
    if(!n) {
        if(p->event_stage==2) {
            pr_event *e=&p->pending_event;
            e->result=p->event_sink?p->event_sink(p->event_context,e):PR_UNMAPPED;
            p->events[p->event_head]=*e;p->event_head=(p->event_head+1)%PR_EVENT_COUNT;
            if(p->event_count<PR_EVENT_COUNT)p->event_count++;
            p->events_complete++;
            if(e->result==PR_MAPPED)p->events_mapped++;
            if(e->result==PR_UNMATCHED)p->events_unmatched++;
            if(e->result==PR_IGNORED)p->events_ignored++;
            p->event_stage=0;p->event_boundary=true;return PR_EVENT;
        }
        pr_event_reset(p);p->event_boundary=true;return PR_BOUNDARY;
    }
    if(p->event_stage==1) {
        /* A second header/operator command is not a device description. */
        if(n<=PR_EVENT_TEXT_MAX&&!strstr(s," :: ")&&s[0]!='-'&&strncmp(s,"P:",2)) {
            memcpy(p->pending_event.text,s,n+1);p->event_stage=2;return PR_EVENT;
        }
        pr_event_reset(p);return PR_UNKNOWN;
    }
    if(p->event_stage){pr_event_reset(p);return PR_UNKNOWN;}
    if(p->event_boundary) {
        memset(&p->pending_event,0,sizeof(p->pending_event));
        if(header(s,&p->pending_event)) {
            pr_event *e=&p->pending_event;e->id=p->next_id;e->offset=p->line_offset;
            e->epoch=p->epoch;e->received_ms=p->received_ms;p->event_stage=1;
            p->event_boundary=false;return PR_EVENT;
        }
    }
    p->event_boundary=false;return strspn(s,"-")==n?PR_BOUNDARY:PR_UNKNOWN;
}
const pr_event *pr_recent_event(const pr_parser *p,size_t index) {
    if(index>=p->event_count)return NULL;
    return &p->events[(p->event_head+PR_EVENT_COUNT-p->event_count+index)%PR_EVENT_COUNT];
}
const char *pr_event_type_name(pr_event_type type) {
    return type==PR_LOCAL_TROUBLE?"LOCAL TRBL":type==PR_COMMON_TROUBLE?"COMMON TRBL":"unknown";
}
const char *pr_event_result_name(pr_event_result result) {
    static const char *const names[]={"not_mapped","observation_only","unmatched_address","duplicate_or_older"};
    return (unsigned)result<=PR_IGNORED?names[result]:"invalid";
}

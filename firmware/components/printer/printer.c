/* Evidence profile: EST3 5.30 revision printer report. No event/state guesses. */
#include "printer.h"
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void retain(pr_parser *p, pr_kind kind, const uint8_t *raw, size_t length) {
    pr_line *line=&p->recent[p->head];
    memset(line,0,sizeof(*line));
    line->id=p->next_id++;line->epoch=p->epoch;line->offset=p->line_offset;
    line->received_ms=p->received_ms;line->kind=kind;line->length=length;
    if(length)memcpy(line->raw,raw,length);
    p->head=(p->head+1)%PR_RECENT_COUNT;
    if(p->count<PR_RECENT_COUNT)p->count++;else p->evicted++;
    if(kind==PR_UNKNOWN)p->unknown++;
    if(kind==PR_FRAGMENT)p->fragments++;
}
static bool value(char *dst,size_t capacity,const char *src) {
    size_t n=strlen(src);if(n>=capacity)return false;
    memcpy(dst,src,n+1);return true;
}
static bool version(char *dst,size_t capacity,const char *src) {
    if(strlen(src)!=9||src[0]!='V'||src[3]!='.'||src[6]!='.'||*dst)return false;
    for(unsigned i=1;i<9;i++)if(i!=3&&i!=6&&!isdigit((unsigned char)src[i]))return false;
    return value(dst,capacity,src);
}
static bool number(const char *text,unsigned *out) {
    if(!*text)return false;
    unsigned n=0;
    for(const char *s=text;*s;s++){if(!isdigit((unsigned char)*s)||n>1000000)return false;n=n*10+(unsigned)(*s-'0');}
    *out=n;return true;
}
static bool date_text(const char *s) {
    if(strlen(s)!=8)return false;
    for(unsigned i=0;i<8;i++)if((i==2||i==5)?s[i]!='/':!isdigit((unsigned char)s[i]))return false;
    return true; /* Raw dates, including panel zero dates; no UTC inference. */
}
static pr_kind classify(pr_parser *p) {
    char text[PR_LINE_MAX+1];
    memcpy(text,p->partial,p->partial_length);text[p->partial_length]=0;
    for(size_t i=0;i<p->partial_length;i++)if((p->partial[i]<32&&p->partial[i]!='\t')||p->partial[i]>126){p->report.tainted=true;return PR_UNKNOWN;}
    char *s=text;while(*s==' '||*s=='\t')s++;
    size_t n=strlen(s);while(n&&(s[n-1]==' '||s[n-1]=='\t'))s[--n]=0;
    if(!strcmp(s,"REVISION REPORT")) {
        if(p->report.active)p->reports_incomplete++;
        memset(&p->report,0,sizeof(p->report));p->report.active=true;
        p->report.received_ms=p->received_ms;p->report.epoch=p->epoch;p->date_target=0;
        return PR_BOUNDARY;
    }
    if(!n||strspn(s,"-")==n)return PR_BOUNDARY;
    if(!p->report.active)return PR_UNKNOWN;
    if(!strcmp(s,"**END: COMPLETE**")) {
        pr_report *r=&p->report;
        r->complete=r->panel_seen&&r->cpu[0]&&r->sdu[0]&&r->project[0]&&r->database_date[0]&&!r->tainted;
        r->active=false;
        if(r->complete){p->last_complete=*r;p->reports_complete++;}else p->reports_incomplete++;
        return PR_BOUNDARY;
    }
    if(!n||strspn(s,"-")==n)return PR_BOUNDARY;
    if(!strncmp(s,"PANEL:",6)) {
        unsigned panel,h,m,sec,month,day,year;int consumed=0;
        if(sscanf(s,"PANEL: %2u %2u:%2u:%2u %2u/%2u/%4u%n",&panel,&h,&m,&sec,&month,&day,&year,&consumed)==7&&
           !s[consumed]&&panel>=1&&panel<=99&&h<24&&m<60&&sec<60&&month>=1&&month<=12&&day>=1&&day<=31&&year>=2000&&year<=9999&&!p->report.panel_seen) {
            p->report.panel=panel;p->report.panel_seen=true;
            snprintf(p->report.source_time,sizeof(p->report.source_time),"%02u:%02u:%02u %02u/%02u/%04u",h,m,sec,month,day,year);
            return PR_METADATA;
        }
        p->report.tainted=true;return PR_UNKNOWN;
    }
    if(p->date_target&&date_text(s)&&p->report.card_count) {
        pr_card *c=&p->report.cards[p->report.card_count-1];
        char *target=p->date_target==1?c->firmware_date:p->date_target==2?c->bootstrap_date:c->database_date;
        value(target,16,s);p->date_target=0;return PR_METADATA;
    }
    p->date_target=0;
    char *sep=strchr(s,':');if(!sep){p->report.tainted=true;return PR_UNKNOWN;}
    *sep=0;char *v=sep+1;while(*v==' ')v++;
    n=strlen(s);while(n&&s[n-1]==' ')s[--n]=0;
    if(!strcmp(s,"CARD")) {
        unsigned card;
        if(!number(v,&card)||card>99||p->report.card_count==PR_CARD_MAX){p->report.tainted=true;return PR_UNKNOWN;}
        for(size_t i=0;i<p->report.card_count;i++)if(p->report.cards[i].address==card){p->report.tainted=true;return PR_UNKNOWN;}
        p->report.cards[p->report.card_count++].address=card;return PR_METADATA;
    }
    bool ok=false;
    if(p->report.card_count) {
        pr_card *c=&p->report.cards[p->report.card_count-1];
        if(!strcmp(s,"ANN TYPE"))ok=value(c->ann_type,sizeof(c->ann_type),v);
        else if(!strcmp(s,"CARD TYPE"))ok=value(c->type,sizeof(c->type),v);
        else if(!strcmp(s,"FIRMWARE")){ok=version(c->firmware,sizeof(c->firmware),v);p->date_target=1;}
        else if(!strcmp(s,"BOOTSTRAP")){ok=version(c->bootstrap,sizeof(c->bootstrap),v);p->date_target=2;}
        else if(!strcmp(s,"DATABASE")){ok=version(c->database,sizeof(c->database),v);p->date_target=3;}
    } else {
        pr_report *r=&p->report;
        if(!strcmp(s,"ALARM COUNT"))ok=number(v,&r->historical_alarm_count);
        else if(!strcmp(s,"MARKET"))ok=value(r->market,sizeof(r->market),v);
        else if(!strcmp(s,"CPU"))ok=version(r->cpu,sizeof(r->cpu),v);
        else if(!strcmp(s,"3-SDU"))ok=version(r->sdu,sizeof(r->sdu),v);
        else if(!strcmp(s,"SDU PRJCT"))ok=version(r->project,sizeof(r->project),v);
        else if(!strcmp(s,"DB S/N"))ok=value(r->database_serial,sizeof(r->database_serial),v);
        else if(!strcmp(s,"DB DATE"))ok=value(r->database_date,sizeof(r->database_date),v)&&date_text(v);
        else if(!strcmp(s,"IP ADDR"))ok=value(r->ip,sizeof(r->ip),v);
        else if(!strcmp(s,"IP NTWRK"))ok=value(r->netmask,sizeof(r->netmask),v);
        else if(!strcmp(s,"IP GTWY"))ok=value(r->gateway,sizeof(r->gateway),v);
        else if(!strcmp(s,"AUDIO DB"))ok=strlen(v)<24;
    }
    if(!ok)p->report.tainted=true;
    return ok?PR_METADATA:PR_UNKNOWN;
}
void pr_init(pr_parser *p){memset(p,0,sizeof(*p));p->next_id=1;}
void pr_gap(pr_parser *p,uint32_t epoch,uint64_t offset,uint64_t now,const char *reason) {
    if(p->partial_length)retain(p,PR_FRAGMENT,p->partial,p->partial_length);
    if(p->report.active){p->report.active=false;p->report.tainted=true;p->reports_incomplete++;}
    p->partial_length=0;p->skip_lf=false;p->fragmenting=false;p->date_target=0;
    p->epoch=epoch;p->next_offset=offset;p->line_offset=offset;p->received_ms=now;p->initialized=true;p->gaps++;
    size_t n=strlen(reason);if(n>PR_LINE_MAX)n=PR_LINE_MAX;retain(p,PR_GAP,(const uint8_t*)reason,n);
}
void pr_feed(pr_parser *p,uint32_t epoch,uint64_t offset,uint64_t now,const uint8_t *data,size_t length,bool corrupt) {
    if(!p->initialized||epoch!=p->epoch||offset!=p->next_offset||corrupt)
        pr_gap(p,epoch,offset,now,corrupt?"UART/USB corruption; current state unavailable":"boot, reconfiguration, disconnect or missing bytes");
    p->received_ms=now;
    if(corrupt)p->fragmenting=true;
    for(size_t i=0;i<length;i++) {
        uint8_t b=data[i];p->next_offset++;
        if(b=='\n'&&p->skip_lf){p->skip_lf=false;p->line_offset=p->next_offset;continue;}
        p->skip_lf=false;
        if(b=='\r'||b=='\n') {
            retain(p,p->fragmenting?PR_FRAGMENT:classify(p),p->partial,p->partial_length);
            p->partial_length=0;p->fragmenting=corrupt;p->skip_lf=b=='\r';p->line_offset=p->next_offset;
        } else {
            if(p->partial_length==PR_LINE_MAX) {
                retain(p,PR_FRAGMENT,p->partial,p->partial_length);p->partial_length=0;
                p->fragmenting=true;p->report.tainted=true;p->line_offset=p->next_offset-1;
            }
            p->partial[p->partial_length++]=b;
        }
    }
}
const pr_line *pr_recent(const pr_parser *p,size_t index) {
    if(index>=p->count)return NULL;
    return &p->recent[(p->head+PR_RECENT_COUNT-p->count+index)%PR_RECENT_COUNT];
}
const char *pr_kind_name(pr_kind kind) {
    static const char *const names[]={"unrecognized","revision_metadata","report_boundary","incomplete_or_corrupt","stream_gap"};
    return kind<=PR_GAP?names[kind]:"invalid";
}

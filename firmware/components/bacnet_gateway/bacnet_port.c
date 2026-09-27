/* Minimal local-subnet BACnet/IPv4 datalink; BACnet stack owns NPDU/APDU codecs. */
#include "bacnet_gateway.h"
#include "bacnet/datalink/bip.h"
#include "bacnet/basic/sys/mstimer.h"
#include <string.h>
#include <unistd.h>
#ifdef ESP_PLATFORM
#include "lwip/sockets.h"
#include "esp_timer.h"
#else
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <time.h>
#endif

static int sock=-1;
static uint16_t port_number=47808;
static struct in_addr local_ip,broadcast_ip;
uint64_t bg_now(void) {
#ifdef ESP_PLATFORM
    return esp_timer_get_time()/1000;
#else
    struct timespec ts;clock_gettime(CLOCK_MONOTONIC,&ts);return (uint64_t)ts.tv_sec*1000+ts.tv_nsec/1000000;
#endif
}
unsigned long mstimer_now(void) {return (unsigned long)bg_now();}
void bg_configure_address(const char *ip,const char *broadcast) {inet_pton(AF_INET,ip,&local_ip);inet_pton(AF_INET,broadcast,&broadcast_ip);}
bool bip_init(char *bind_ip) {
    sock=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);if(sock<0)return false;
    int one=1;setsockopt(sock,SOL_SOCKET,SO_BROADCAST,&one,sizeof(one));
    struct sockaddr_in bind_addr={.sin_family=AF_INET,.sin_port=htons(port_number)};
    inet_pton(AF_INET,bind_ip,&bind_addr.sin_addr);
    if(bind(sock,(struct sockaddr*)&bind_addr,sizeof(bind_addr))<0){close(sock);sock=-1;return false;}return true;
}
void bip_set_port(uint16_t port) {port_number=port;}
uint16_t bip_get_port(void) {return port_number;}
bool bip_valid(void) {return sock>=0;}
void bip_cleanup(void) {if(sock>=0)close(sock);sock=-1;}
void bip_get_my_address(BACNET_ADDRESS *a) {
    memset(a,0,sizeof(*a));a->mac_len=6;memcpy(a->mac,&local_ip.s_addr,4);a->mac[4]=port_number>>8;a->mac[5]=port_number;
}
void bip_get_broadcast_address(BACNET_ADDRESS *a) {
    bip_get_my_address(a);memcpy(a->mac,&broadcast_ip.s_addr,4);a->net=BACNET_BROADCAST_NETWORK;
}
int bip_send_pdu(BACNET_ADDRESS *a,BACNET_NPDU_DATA *npdu,uint8_t *pdu,unsigned len) {
    (void)npdu;
    if(len>MAX_PDU||sock<0)return -1;
    bool broadcast=a->net==BACNET_BROADCAST_NETWORK || a->mac_len==0;
    if(!broadcast&&a->mac_len!=6)return -1;
    uint8_t packet[MAX_PDU+4];packet[0]=0x81;packet[1]=broadcast?0x0b:0x0a;packet[2]=(len+4)>>8;packet[3]=len+4;memcpy(packet+4,pdu,len);
    struct sockaddr_in dst={.sin_family=AF_INET,.sin_port=htons(port_number),.sin_addr=broadcast_ip};
    if(!broadcast){memcpy(&dst.sin_addr.s_addr,a->mac,4);dst.sin_port=htons(((uint16_t)a->mac[4]<<8)|a->mac[5]);}
    return sendto(sock,packet,len+4,0,(struct sockaddr*)&dst,sizeof(dst));
}
uint16_t bip_receive(BACNET_ADDRESS *a,uint8_t *pdu,uint16_t capacity,unsigned timeout) {
    if(sock<0)return 0;
    fd_set fds;FD_ZERO(&fds);FD_SET(sock,&fds);struct timeval tv={.tv_sec=timeout/1000,.tv_usec=(timeout%1000)*1000};
    if(select(sock+1,&fds,NULL,NULL,&tv)<=0)return 0;
    uint8_t packet[MAX_PDU+5];struct sockaddr_in src;socklen_t slen=sizeof(src);
    int n=recvfrom(sock,packet,sizeof(packet),0,(struct sockaddr*)&src,&slen);
    if(n<6||n>MAX_PDU+4||packet[0]!=0x81||(packet[1]!=0x0a&&packet[1]!=0x0b)||(((unsigned)packet[2]<<8)|packet[3])!=(unsigned)n||n-4>capacity)return 0;
    memset(a,0,sizeof(*a));a->mac_len=6;memcpy(a->mac,&src.sin_addr.s_addr,4);uint16_t port=ntohs(src.sin_port);a->mac[4]=port>>8;a->mac[5]=port;
    memcpy(pdu,packet+4,n-4);return n-4;
}

#include "serial_diagnostics.h"
#include <assert.h>
#include <string.h>

int main(void) {
    serial_diagnostics d={0};uint8_t out[SERIAL_CAPTURE_CAPACITY];
    uint8_t status[]={0x01,0x60};
    serial_diagnostics_feed(&d,status,sizeof(status),10);
    assert(d.packets==1 && d.status_only_packets==1 && d.payload_bytes==0);
    assert(d.last_packet_ms==10 && d.last_payload_ms==0 && d.line_status==0x60);
    serial_diagnostics_feed(&d,status,1,11);
    serial_diagnostics_feed(&d,NULL,2,12);
    uint8_t oversized[65]={0};serial_diagnostics_feed(&d,oversized,sizeof(oversized),13);
    assert(d.invalid_packets==3 && d.payload_bytes==0);

    /* A changing status prefix must never become UART data, including prefixes
       whose values also occur in the binary payload. Exercise wrap and tails. */
    uint8_t packet[64];size_t total=0;
    while(total<1024) {
        size_t count=1024-total;if(count>62)count=62;
        packet[0]=(uint8_t)total;packet[1]=0x60;
        for(size_t i=0;i<count;i++)packet[i+2]=(uint8_t)(total+i);
        serial_diagnostics_feed(&d,packet,count+2,100+total);total+=count;
    }
    assert(d.payload_bytes==1024 && d.capture_count==SERIAL_CAPTURE_CAPACITY);
    assert(serial_diagnostics_payload(&d,out,sizeof(out))==sizeof(out));
    for(size_t i=0;i<sizeof(out);i++)assert(out[i]==(uint8_t)(512+i));
    assert(serial_diagnostics_payload(&d,out,7)==7);
    for(size_t i=0;i<7;i++)assert(out[i]==(uint8_t)(1017+i));
    packet[0]=0x01;packet[1]=0x7e;
    serial_diagnostics_feed(&d,packet,2,2000);
    assert(d.error_packets==1 && d.payload_bytes==1024);
    uint32_t packets=d.packets;
    serial_diagnostics_clear_capture(&d);
    assert(d.packets==packets && d.capture_count==0 && d.capture_epoch==1);
    assert(serial_diagnostics_payload(&d,out,sizeof(out))==0);
    packet[1]=0x60;packet[2]=0;packet[3]=255;
    serial_diagnostics_feed(&d,packet,4,2001);
    assert(serial_diagnostics_payload(&d,out,sizeof(out))==2);
    assert(out[0]==0 && out[1]==255 && d.payload_bytes==1026 && d.last_payload_ms==2001);
    assert(serial_baud_supported(9600) && serial_baud_supported(19200));
    assert(!serial_baud_supported(0) && !serial_baud_supported(19201) && !serial_baud_supported(UINT32_MAX));
    return 0;
}

"""One bounded BACnet Who-Is for this bench device on the chosen local subnet."""
import argparse
import json
import socket
import time

def discover(broadcast,instance=3899000,timeout=5):
    value=instance.to_bytes(3,'big')
    npdu=b'\x01\x00\x10\x08\x0b'+value+b'\x1b'+value
    packet=b'\x81\x0b'+(len(npdu)+4).to_bytes(2,'big')+npdu
    found=set()
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1);s.bind(('0.0.0.0',0));s.settimeout(.5)
        s.sendto(packet,(broadcast,47808));end=time.monotonic()+timeout
        while time.monotonic()<end:
            try:data,src=s.recvfrom(2048)
            except socket.timeout:continue
            # Local-subnet unsegmented I-Am, followed by application object-id tag.
            if len(data)>=13 and data[:2] in (b'\x81\x0a',b'\x81\x0b') and data[4:9]==b'\x01\x00\x10\x00\xc4':
                object_id=int.from_bytes(data[9:13],'big')
                if object_id>>22==8 and object_id&0x3fffff==instance:found.add(src[0])
    return sorted(found)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--broadcast',required=True);p.add_argument('--instance',type=int,default=3899000);a=p.parse_args()
    print(json.dumps({'device_instance':a.instance,'addresses':discover(a.broadcast,a.instance)},indent=2))

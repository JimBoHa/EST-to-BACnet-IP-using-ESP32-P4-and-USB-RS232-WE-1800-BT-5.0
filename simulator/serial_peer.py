"""Separate PC bench peer. Never runs on production gateway."""
import argparse
import binascii
import random
import serial
import time
from pathlib import Path

def pattern(size):
    randomizer=random.Random(232)
    prefix=bytes(range(256))*4
    return (prefix+randomizer.randbytes(max(0,size-len(prefix))))[:size]

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['send','capture']);p.add_argument('--port',required=True)
    p.add_argument('--disconnected-bench-peer',action='store_true',required=True)
    p.add_argument('--bytes',type=int,default=19200);p.add_argument('--seconds',type=int,default=60);p.add_argument('--output',type=Path)
    a=p.parse_args()
    if '5B910667991' in a.port:raise SystemExit('Refusing to use the gateway USB-C programming port as RS232 peer')
    if not 1<=a.bytes<=10000000 or not 1<=a.seconds<=86400:raise SystemExit('Invalid bounds')
    with serial.Serial(a.port,19200,bytesize=8,parity='N',stopbits=1,timeout=.1,rtscts=False,dsrdtr=False) as s:
        s.dtr=False;s.rts=False
        if a.mode=='send':
            data=pattern(a.bytes)
            for offset in range(0,len(data),61):s.write(data[offset:offset+61])
            s.flush();print(f'SIMULATION_ONLY sent={len(data)} CRC32={binascii.crc32(data):08x}')
        else:
            if not a.output:raise SystemExit('--output is required for capture')
            total=0;crc=0;deadline=time.monotonic()+a.seconds
            with a.output.open('wb') as f:
                while time.monotonic()<deadline:
                    data=s.read(4096);f.write(data);total+=len(data);crc=binascii.crc32(data,crc)
            print(f'Captured={total} CRC32={crc:08x}; zero bytes does not measure analog idle/transients')

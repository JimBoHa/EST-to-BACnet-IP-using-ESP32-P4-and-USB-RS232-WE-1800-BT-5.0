"""Capture only the USB-C programming console; never open the USB-A field path."""
import argparse
import serial
import time
from pathlib import Path

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument('--port',default='/dev/cu.usbmodem5B910667991');p.add_argument('--seconds',type=int,default=30);p.add_argument('--output',required=True);p.add_argument('--reset',action='store_true');a=p.parse_args()
    with serial.Serial(a.port,115200,timeout=.2) as s,Path(a.output).open('wb') as f:
        s.dtr=False;s.rts=False
        if a.reset:s.rts=True;time.sleep(.1);s.rts=False
        deadline=time.monotonic()+a.seconds
        while time.monotonic()<deadline:
            data=s.read(4096)
            if data:f.write(data);f.flush();print(data.decode(errors='replace'),end='',flush=True)

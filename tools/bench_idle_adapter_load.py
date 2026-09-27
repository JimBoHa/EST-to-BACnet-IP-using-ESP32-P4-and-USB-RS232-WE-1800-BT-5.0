"""Bounded network-read load while FTDI remains attached; no serial payload test."""
import argparse
import asyncio
import json
import time
from pathlib import Path
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.app import Application
from gateway_client import Client


async def run(host, local_ip, seconds):
    client=Client(host)
    baseline=await asyncio.to_thread(client.request,'GET','/ota/status')
    assert baseline['usb_connected'] and not baseline['serial_payload_tx_enabled']
    args=SimpleArgumentParser().parse_args(['--address',local_ip+':47829',
        '--instance','3899999','--name','Adapter attached load client'])
    app=Application.from_args(args)
    end=time.monotonic()+seconds
    samples=[]
    counts={'https_reads':0,'bacnet_reads':0}
    async def https_reads():
        while time.monotonic()<end:
            s=await asyncio.to_thread(client.request,'GET','/ota/status')
            for key in ('boot_count','usb_connects','usb_errors','line_errors','rx_drops'):
                assert s[key]==baseline[key],key
            assert s['usb_connected'] and not s['awaiting_confirmation']
            samples.append({k:s[k] for k in ('uptime_ms','heap_free','internal_heap_free','usb_connected','usb_connects','boot_count','usb_errors')})
            counts['https_reads']+=1
            await asyncio.sleep(.25)
    async def bacnet_reads():
        while time.monotonic()<end:
            value=await asyncio.wait_for(app.read_property(host,'binary-input,2','present-value'),timeout=3)
            assert str(value)=='active',str(value)
            counts['bacnet_reads']+=1
            await asyncio.sleep(.1)
    try:
        await asyncio.gather(https_reads(),bacnet_reads())
    finally:
        app.close()
    final=await asyncio.to_thread(client.request,'GET','/ota/status')
    assert final['boot_count']==baseline['boot_count'] and final['usb_connected']
    return {'result':'PASS','scope':'Network reads with idle attached FTDI; no serial payload traffic',
            'duration_seconds':seconds,'counts':counts,'baseline':baseline,'final':final,
            'samples':samples}


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--host',required=True);p.add_argument('--local-ip',required=True)
    p.add_argument('--seconds',type=int,default=60);p.add_argument('--output',required=True)
    a=p.parse_args()
    if not 1<=a.seconds<=300:p.error('--seconds must be 1..300')
    result=asyncio.run(run(a.host,a.local_ip,a.seconds))
    Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('result','scope','duration_seconds','counts')},indent=2))

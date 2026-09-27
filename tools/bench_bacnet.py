"""Read-only independent BACpypes3 checks against the identified bench gateway."""
import argparse
import asyncio
import json
from pathlib import Path
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.app import Application
from bacpypes3.pdu import Address
from gateway_client import Client


async def check(host, local_ip):
    status=Client(host).request('GET','/ota/status')
    assert status['project']=='est3_gateway_rxonly'
    assert not status['serial_payload_tx_enabled'] and not status['simulation']
    args=SimpleArgumentParser().parse_args(['--address',local_ip+':47829',
        '--instance','3899999','--name','Independent bench client'])
    app=Application.from_args(args)
    try:
        found=await app.who_is(3899000,3899000,Address(host),timeout=2)
        assert len(found)==1
        device='device,3899000'
        count=int(await app.read_property(host,device,'object-list',0))
        assert count==5+5*status['device_count']
        objects=[str(await app.read_property(host,device,'object-list',i)) for i in range(1,count+1)]
        services=await app.read_property(host,device,'protocol-services-supported')
        assert services['read-property'] and services['read-property-multiple']
        assert not services['write-property'] and not services['subscribe-cov']
        values={str(i):str(await app.read_property(host,f'binary-input,{i}','present-value')) for i in range(1,5)}
        assert values['1']=='inactive' and values['4']=='inactive'
        assert values['2']==('active' if status['usb_connected'] else 'inactive')
        rpm=await app.read_property_multiple(Address(host),['binary-input,2',
            ['present-value','reliability','status-flags'],'binary-input,4',['present-value']])
        assert len(rpm)==4
        return {'result':'PASS','host':host,'device_instance':3899000,
                'version':status['version'],'boot_count':status['boot_count'],
                'object_count':count,'objects':objects,'health_values':values,
                'rpm':[str(value) for value in rpm],
                'read_property':True,'read_property_multiple':True,'write_property':False,'cov':False}
    finally:
        app.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--host',required=True)
    parser.add_argument('--local-ip',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    result=asyncio.run(check(args.host,args.local_ip))
    text=json.dumps(result,indent=2)+'\n'
    Path(args.output).write_text(text)
    print(text,end='')

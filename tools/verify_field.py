"""Bounded independent BACnet discovery/read/quality checks; no control writes."""
import argparse
import asyncio
import datetime
import json
import time
from pathlib import Path
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.app import Application
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier
from gateway_client import Client


async def verify(host,local_ip,registry,all_objects=False):
    start=time.monotonic();client=Client(host);before=client.request('GET','/ota/status')
    args=SimpleArgumentParser().parse_args(['--address',local_ip+':47829','--instance','3899999','--name','Independent read-only EST3 verifier'])
    app=Application.from_args(args);reads=0
    try:
        found=await app.who_is(3899000,3899000,Address(host),timeout=2)
        assert len(found)==1
        count=int(await app.read_property(host,'device,3899000','object-list',0));reads+=1
        assert count==5+5*len(registry['devices'])
        indexes=range(1,count+1) if all_objects else sorted(set([1,2,5,6,count,*range(6,count,max(1,count//20))]))
        objects=[]
        for index in indexes:
            objects.append(str(await app.read_property(host,'device,3899000','object-list',index)));reads+=1
            if all_objects and index%1000==0:print(f'Read {index}/{count} indexed objects',flush=True)
        assert len(objects)==len(set(objects))
        if all_objects:
            expected={str(ObjectIdentifier(('device',3899000)))}
            expected.update(str(ObjectIdentifier(('binary-input',i))) for i in range(1,5))
            expected.update(str(ObjectIdentifier(('binary-input',i))) for d in registry['devices'] for i in d['instances'])
            assert set(objects)==expected
        services=await app.read_property(host,'device,3899000','protocol-services-supported');reads+=1
        assert services['read-property'] and services['read-property-multiple']
        assert not services['write-property'] and not services['subscribe-cov']
        devices=registry['devices'];selected={0,len(devices)-1}
        for kind in ('Sensor / PS','Module / 278','Module / CR','Unresolved SDU scope 255'):
            first=next((i for i,d in enumerate(devices) if d['type']==kind),None)
            if first is not None:selected.add(first)
        selected.update(range(0,len(devices),max(1,len(devices)//12)))
        if all_objects:selected=set(range(len(devices)))
        for index in sorted(selected):
            d=devices[index];parameters=[]
            for instance in d['instances'][:4]:parameters.extend([f'binary-input,{instance}',['present-value','reliability','status-flags','description']])
            values=await app.read_property_multiple(Address(host),parameters);reads+=16
            assert len(values)==16
            for k in range(4):
                assert str(values[k*4][3]) in (('inactive','active') if k==1 else ('inactive',))
                assert str(values[k*4+1][3])=='communication-failure'
                assert values[k*4+2][3]['fault']
                assert str(values[k*4+3][3])==d['label']
            valid=await app.read_property(host,f"binary-input,{d['instances'][4]}",'present-value');reads+=1
            assert str(valid)=='inactive'
            if all_objects and index%200==0:print(f'Checked conditions and labels for {index+1}/{len(devices)} records',flush=True)
        after=client.request('GET','/ota/status');serial=client.request('GET','/api/v1/serial')
        assert after['boot_count']==before['boot_count'] and after['version']==before['version']
        assert after['rx_drops']==before['rx_drops'] and after['usb_errors']==before['usb_errors']
        assert not after['serial_payload_tx_enabled'] and not after['external_host_delivery_enabled']
        assert serial['baud']==9600 and serial['configuration_error']==0 and serial['usb_connected']
        return {'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'version':after['version'],
                'elf_sha256':after['elf_sha256'],'boot_count':after['boot_count'],'registry_epoch':after['registry_epoch'],
                'catalog_objects':len(devices),'bacnet_object_count':count,'indexed_objects_checked':len(indexes),
                'sample_devices_checked':len(selected),'all_catalog_devices_checked':all_objects,'property_values_checked':reads,'seconds':time.monotonic()-start,
                'discovery':True,'rp':True,'rpm':True,'labels_match_registry':True,'all_sample_conditions_fault':True,
                'all_sample_data_valid_inactive':True,'no_reboot_or_new_receive_errors':True,'no_control_requests_sent':True,
                'source_payload_bytes_during_test':after['rx_bytes']-before['rx_bytes'],
                'scope':'Real P4 inventory/BACnet transport/quality only; no validated live EST condition or Metasys test'}
    finally:app.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host',required=True);p.add_argument('--local-ip',required=True)
    p.add_argument('--registry',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--all',action='store_true',help='Read every indexed object and every catalog condition/label');a=p.parse_args()
    result=asyncio.run(verify(a.host,a.local_ip,json.loads(a.registry.read_text()),a.all))
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

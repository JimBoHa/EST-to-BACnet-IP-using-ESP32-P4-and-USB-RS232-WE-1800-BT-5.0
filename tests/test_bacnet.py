"""Independent BACpypes3 client against exactly the firmware's C stack/port."""
import asyncio
import json
import socket
import subprocess
from pathlib import Path
import pytest
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.app import Application
from bacpypes3.pdu import Address
from bacpypes3.apdu import ErrorRejectAbortNack
from fastapi.testclient import TestClient
from host.api import create_app
from host.store import Store
from simulator.catalog import load_catalog

ROOT=Path(__file__).resolve().parents[1]

def atomic(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value));temp.replace(path)

def controls(port):
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        s.bind(('127.0.0.1',0));s.settimeout(2)
        for service in (0,10,11,15,16,17,20,21):
            payload=bytes([1,4,0,5,33,service])
            if service==15:payload+=bytes.fromhex('0c0040006419553e91013f')
            s.sendto(bytes([0x81,0x0a,0,len(payload)+4])+payload,('127.0.0.1',port))
            answer=s.recv(2048)
            assert answer[6:]==bytes([0x60,33,9]),(service,answer.hex())

def test_independent_bacnet_discovery_properties_quality_and_controls(tmp_path):
    s=Store(tmp_path/'registry.sqlite');s.reconcile(load_catalog())
    reg=tmp_path/'registry.json';state=tmp_path/'state.json'
    atomic(reg,s.registry());atomic(state,{"sequence":0})
    log=(tmp_path/'native.log').open('w')
    process=subprocess.Popen([str(ROOT/'build-tests/sim_bacnet'),str(reg),str(state),'47828'],stdout=log,stderr=log)
    tokens={r:r+'x'*64 for r in ('viewer','manager','gateway')}
    host=TestClient(create_app(s,tokens))
    host_sequence=0
    def publish(sequence,observations):
        # The same neutral simulator observations reach both independent consumers.
        # This does not represent EST wire framing or a production injection path.
        nonlocal host_sequence
        records=[]
        snapshots={}
        for observation in observations:
            kind=('alarm','trouble','supervisory','disabled')[observation['condition']]
            record={'logical_device_id':observation['uuid'],
                    'binding_epoch':observation['epoch'],'raw_source_code':'SIM_'+kind.upper()}
            if observation.get('snapshot'):
                # Host snapshots must contain every applicable condition together.
                if observation['uuid'] not in snapshots:
                    record.update(record_type='snapshot',values={})
                    snapshots[observation['uuid']]=record
                    records.append(record)
                snapshots[observation['uuid']]['values'][kind]=observation['value']
            else:
                record.update(record_type='event',normalized_condition=kind,
                              transition='assert' if observation['value'] else 'restore')
                records.append(record)
        for record in records:
            host_sequence+=1
            record['sequence']=host_sequence
        response=host.post('/api/v1/telemetry',headers={'Authorization':'Bearer '+tokens['gateway']},
                           json={'gateway_id':'SIM-GW','boot_id':'SIM-BACNET-INTEGRATION',
                                 'source_mode':'simulation','records':records})
        assert response.status_code==200,response.text
        assert response.json()['ack']==host_sequence
        atomic(state,{'sequence':sequence,'observations':observations})
    async def check():
        args=SimpleArgumentParser().parse_args(['--address','127.0.0.1:47829','--instance','3899999','--name','Independent lab client'])
        app=Application.from_args(args)
        dst='127.0.0.1:47828'
        try:
            await asyncio.sleep(.3)
            devices=await app.who_is(3899001,3899001,Address(dst),timeout=1)
            assert len(devices)==1
            device='device,3899001'
            assert int(await app.read_property(dst,device,'object-list',0))==15
            assert str(await app.read_property(dst,'binary-input,100','present-value'))=='inactive'
            assert str(await app.read_property(dst,'binary-input,100','reliability'))=='communication-failure'
            assert str(await app.read_property(dst,'binary-input,104','present-value'))=='inactive'
            for index in range(1,16): assert await app.read_property(dst,device,'object-list',index) is not None
            try:
                result=await app.read_property(dst,device,'object-list',9999)
                assert isinstance(result,ErrorRejectAbortNack)
            except ErrorRejectAbortNack:pass
            rpm=await app.read_property_multiple(Address(dst),['binary-input,100',['present-value','reliability','status-flags'],'binary-input,104',['present-value']])
            assert len(rpm)==4
            services=await app.read_property(dst,device,'protocol-services-supported')
            assert services['read-property'] and services['read-property-multiple'] and not services['write-property'] and not services['subscribe-cov']
            observations=[]
            for d in s.devices():
                for k in (0,1):observations.append({'uuid':d['uuid'],'epoch':d['binding_epoch'],'condition':k,'value':False,'snapshot':True})
            publish(1,observations);await asyncio.sleep(.25)
            assert str(await app.read_property(dst,'binary-input,104','present-value'))=='active'
            assert all(d['data_valid'] for d in s.devices())
            observations=[{'uuid':s.devices()[0]['uuid'],'epoch':1,'condition':0,'value':True},{'uuid':s.devices()[0]['uuid'],'epoch':1,'condition':1,'value':True},{'uuid':s.devices()[1]['uuid'],'epoch':1,'condition':0,'value':True}]
            publish(2,observations);await asyncio.sleep(.25)
            for instance in (100,101,105):assert str(await app.read_property(dst,f'binary-input,{instance}','present-value'))=='active'
            a,b=s.devices()
            assert a['conditions']['alarm']['value'] and a['conditions']['trouble']['value'] and b['conditions']['alarm']['value']
            publish(3,[dict(observations[0],value=False)]);await asyncio.sleep(.25)
            assert str(await app.read_property(dst,'binary-input,100','present-value'))=='inactive'
            assert str(await app.read_property(dst,'binary-input,101','present-value'))=='active'
            assert s.devices()[0]['conditions']['alarm']['value'] is False
            assert s.devices()[0]['conditions']['trouble']['value'] is True
            old_name=await app.read_property(dst,'binary-input,100','object-name')
            s.reconcile(load_catalog(2));atomic(reg,s.registry());await asyncio.sleep(.25)
            assert await app.read_property(dst,'binary-input,100','object-name')==old_name
            assert 'renovated' in str(await app.read_property(dst,'binary-input,100','description'))
            await asyncio.to_thread(controls,47828)
            assert str(await app.read_property(dst,'binary-input,101','present-value'))=='active'
            atomic(state,{'sequence':4,'invalidate':True});await asyncio.sleep(.25)
            assert str(await app.read_property(dst,'binary-input,104','present-value'))=='inactive'
            assert str(await app.read_property(dst,'binary-input,101','present-value'))=='active'
            assert str(await app.read_property(dst,'binary-input,101','reliability'))=='communication-failure'
        finally:app.close()
    try:asyncio.run(check())
    finally:
        process.terminate();process.wait(timeout=5);log.close();host.close();s.db.close()
    assert 'ERROR: AddressSanitizer' not in (tmp_path/'native.log').read_text()

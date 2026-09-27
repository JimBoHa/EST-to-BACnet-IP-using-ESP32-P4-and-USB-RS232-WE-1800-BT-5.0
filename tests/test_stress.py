import asyncio
import json
import subprocess
import time
from pathlib import Path
from uuid import UUID
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.app import Application
from bacpypes3.pdu import Address
from bacpypes3.apdu import ErrorRejectAbortNack

ROOT=Path(__file__).resolve().parents[1]

def test_1000_devices_5000_binary_inputs(tmp_path):
    devices=[]
    for i in range(1000):devices.append({'uuid':str(UUID(int=i+1)),'address':f'SIM-{i}','type':'SIMULATION_ONLY','label':f'Simulated point {i}','binding_epoch':1,'instances':list(range(100+5*i,105+5*i)),'supported':15,'retired':False})
    registry=tmp_path/'registry.json';registry.write_text(json.dumps({'schema_version':1,'epoch':1,'source_mode':'simulation','devices':devices}))
    state=tmp_path/'state.json';state.write_text('{"sequence":0}')
    log=(tmp_path/'native.log').open('w')
    process=subprocess.Popen([str(ROOT/'build-tests/sim_bacnet'),str(registry),str(state),'47838'],stdout=log,stderr=log)
    async def check():
        app=Application.from_args(SimpleArgumentParser().parse_args(['--address','127.0.0.1:47839','--instance','3899998','--name','Stress client']))
        try:
            await asyncio.sleep(.6)
            assert len(await app.who_is(3899001,3899001,address=Address('127.0.0.1:47838'),timeout=2))==1
            assert int(await app.read_property('127.0.0.1:47838','device,3899001','object-list',0))==5005
            for index in (1,2,5,6,100,1000,2500,5005):assert await app.read_property('127.0.0.1:47838','device,3899001','object-list',index) is not None
            try:
                value=await app.read_property('127.0.0.1:47838','device,3899001','object-list')
                assert isinstance(value,ErrorRejectAbortNack)
            except ErrorRejectAbortNack:pass
            assert str(await app.read_property('127.0.0.1:47838','binary-input,5099','present-value'))=='inactive'
        finally:app.close()
    try:asyncio.run(check())
    finally:process.terminate();process.wait(timeout=5);log.close()
    assert 'ERROR: AddressSanitizer' not in (tmp_path/'native.log').read_text()

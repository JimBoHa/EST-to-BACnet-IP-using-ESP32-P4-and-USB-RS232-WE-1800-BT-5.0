"""OTA confirmation gates and certificate pin checks without hardware writes."""
import ssl
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import gateway_client as gateway


@pytest.fixture
def update_fixture(tmp_path,monkeypatch):
    key=ec.generate_private_key(ec.SECP256R1())
    (tmp_path/'ota-signing-key.pem').write_bytes(key.private_bytes(
        serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    image=bytearray(240);image[32:36]=bytes.fromhex('3254cdab');image[176:208]=bytes.fromhex('aa'*32)
    path=tmp_path/'app.bin';path.write_bytes(image)
    before=dict(elf_sha256='bb'*32,boot_count=10,registry_epoch=1,device_count=1214,inventory_source_sha256='cc'*32)
    after={**before,'elf_sha256':'aa'*32,'boot_count':11,'uptime_ms':12000,
           'registry_ok':True,'serial_payload_tx_enabled':False,'simulation':False,
           'printer_profile':'est3_printer_revision_v1','external_host_delivery_enabled':False,
           'startup_phase':'ready','awaiting_confirmation':True}
    calls=[];status_reads=0
    client=gateway.Client.__new__(gateway.Client);client.private=tmp_path
    def request(method,url,body=None,headers=None):
        nonlocal status_reads
        calls.append((method,url))
        if url=='/ota/status':
            status_reads+=1
            return before.copy() if status_reads==1 else after.copy()
        if url=='/ota/confirm':after['awaiting_confirmation']=False;return {'confirmed':True}
        if url=='/api/v1/serial':return {'baud':9600,'configuration_error':0,'usb_connected':True}
        if url=='/api/v1/printer?limit=1':return {'profile':'est3_printer_revision_v1'}
        assert url=='/ota' and method=='POST' and headers['X-Image-Signature']
        return {'accepted':True}
    client.request=request
    monkeypatch.setattr(gateway.time,'sleep',lambda _:None)
    ticks=iter(range(2000));monkeypatch.setattr(gateway.time,'monotonic',lambda:next(ticks))
    return client,path,before,after,calls


def test_confirms_only_complete_healthy_boot(update_fixture):
    client,path,_,after,calls=update_fixture
    assert client.upload(path)['awaiting_confirmation'] is False
    assert calls.count(('POST','/ota/confirm'))==1


def test_recovered_previous_image_is_reported_immediately(update_fixture):
    client,path,before,after,calls=update_fixture
    after.update(elf_sha256=before['elf_sha256'],boot_count=12,awaiting_confirmation=False)
    with pytest.raises(gateway.UpdateRolledBack,match='previous confirmed image recovered'):
        client.upload(path)
    assert ('POST','/ota/confirm') not in calls
    assert calls.count(('GET','/ota/status'))==2


@pytest.mark.parametrize('change',[
    {'startup_phase':'registry_parse'}, {'device_count':0}, {'registry_epoch':2},
    {'inventory_source_sha256':'dd'*32}, {'boot_count':10}, {'serial_payload_tx_enabled':True},
    {'elf_sha256':'aa'*4},
])
def test_unhealthy_or_incomplete_candidate_never_confirmed(update_fixture,change):
    client,path,_,after,calls=update_fixture;after.update(change)
    with pytest.raises(RuntimeError,match='not confirmed'):client.upload(path)
    assert ('POST','/ota/confirm') not in calls


def test_wrong_leaf_blocks_request_before_token(monkeypatch):
    client=gateway.Client.__new__(gateway.Client)
    client.host='fixture.invalid';client.context=object();client.timeout=1
    client.expected=b'retained certificate';client.token='synthetic fixture token'
    connection=Mock();connection.sock.getpeercert.return_value=b'other certificate'
    monkeypatch.setattr(gateway.http.client,'HTTPSConnection',lambda *a,**k:connection)
    with pytest.raises(ssl.SSLError,match='pin mismatch'):client.request('GET','/ota/status')
    connection.request.assert_not_called();connection.close.assert_called_once()

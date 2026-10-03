"""Check deployed UI, auth and non-mutating registry preview with strict TLS."""
import argparse
import copy
import datetime
import hashlib
import http.client
import json
import socket
import ssl
import time
from pathlib import Path
from gateway_client import Client, ROOT


def verify(host,registry):
    client=Client(host)
    context=ssl.create_default_context(cafile=str(client.private/'device-cert.pem'))

    def request(method,path,body=None,auth=True):
        # Resolve the known DHCP lease explicitly; still check certificate DNS SAN,
        # trust, expiry and exact leaf before transmitting the existing credential.
        connection=http.client.HTTPSConnection('est3-device.local',context=context,timeout=30)
        try:
            connection.sock=context.wrap_socket(socket.create_connection((host,443),30),server_hostname='est3-device.local')
            if connection.sock.getpeercert(binary_form=True)!=client.expected:raise ssl.SSLError('certificate pin mismatch')
            headers={'Authorization':'Bearer '+client.token} if auth else {}
            if body is not None:headers['Content-Type']='application/json'
            connection.request(method,path,body,headers)
            response=connection.getresponse()
            return response.status,dict(response.getheaders()),response.read()
        finally:connection.close()

    before=client.request('GET','/api/v1/status')
    assets={}
    for path,name in [('/','index.html'),('/app.js','app.js')]:
        status,headers,body=request('GET',path,auth=False)
        assert status==200 and body==(ROOT/'firmware/main/web'/name).read_bytes()
        assert headers['Cache-Control']=='no-store' and headers['X-Content-Type-Options']=='nosniff'
        assert "frame-ancestors 'none'" in headers['Content-Security-Policy']
        assert client.token.encode() not in body
        assets[name]=hashlib.sha256(body).hexdigest()
    protected=[('GET','/api/v1/status'),('GET','/api/v1/serial'),('GET','/api/v1/printer'),
               ('GET','/api/v1/devices'),('GET','/api/v1/registry'),('POST','/api/v1/registry/preview'),
               ('POST','/api/v1/registry'),('POST','/ota'),('POST','/ota/confirm')]
    for method,path in protected:
        assert request(method,path,b'{}' if method=='POST' else None,auth=False)[0]==401
    saved=client.request('GET','/api/v1/registry');assert saved==registry
    preview=copy.deepcopy(saved);preview['epoch']+=1
    preview_seconds=[]
    for path in ['/api/v1/registry/preview','/api/v1/registry/preview?preview=false']:
        started=time.monotonic()
        status,_,body=request('POST',path,json.dumps(preview).encode())
        preview_seconds.append(time.monotonic()-started)
        assert status==200
        result=json.loads(body)
        assert result['valid'] and result['epoch']==preview['epoch']
        assert result['objects']==len(saved['devices']) and result['additions']==result['renames']==result['retirements']==0
    assert client.request('GET','/api/v1/registry')==saved
    directory=[]
    for offset in range(0,len(saved['devices']),100):
        result=client.request('GET',f'/api/v1/devices?offset={offset}&limit=100')
        assert result['total']==result['matched']==len(saved['devices'])
        directory.extend(result['devices'])
    assert len(directory)==len(saved['devices'])
    for actual,expected in zip(directory,saved['devices']):
        for key in ['uuid','address','label','type','binding_epoch','retired']:assert actual[key]==expected[key]
        assert not actual['data_valid']
        for c in actual['conditions']:
            if c['quality']=='observation_only':
                assert c['condition']=='trouble' and isinstance(c['last_value'],bool)
                assert c['source'] in ('LOCAL TRBL','COMMON TRBL') and c['source_time']
                assert c['age_ms']>=0
            else:
                assert c['last_value'] is None and c['quality']=='not_source_verified'
    selected=saved['devices'][len(saved['devices'])//2]
    match=client.request('GET','/api/v1/devices?q='+selected['uuid'])
    assert match['matched']==1 and match['devices'][0]['uuid']==selected['uuid']
    parser=client.request('GET','/api/v1/printer?limit=128')
    assert parser['profile']=='est3_printer_observations_v2' and not parser['current_state_available']
    after=client.request('GET','/api/v1/status')
    assert before['boot_count']==after['boot_count'] and before['registry_epoch']==after['registry_epoch']
    for key in ['rx_drops','usb_errors','telemetry_queued','telemetry_dropped']:assert before[key]==after[key]
    assert not after['awaiting_confirmation'] and after['uptime_ms']>180000
    return {'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'version':after['version'],'boot_count':after['boot_count'],'uptime_ms':after['uptime_ms'],
            'tls_chain_time_hostname_and_exact_leaf_verified':True,'assets_match_source':assets,
            'unauthenticated_routes_denied':len(protected),'preview_did_not_mutate_registry':True,
            'preview_seconds':preview_seconds,
            'directory_records_checked':len(directory),'uuid_search_passed':True,
            'all_directory_conditions_unverified':True,'confirmed_beyond_rollback_window':True,
            'no_reboot_or_new_receive_errors':True,'legacy_outbox_counters_unchanged':True,
            'source_payload_bytes':after['rx_bytes'],'scope':'Direct named TLS to known lease; does not prove mDNS resolution or live EST event decoding'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host',required=True)
    p.add_argument('--registry',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=verify(a.host,json.loads(a.registry.read_text()))
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

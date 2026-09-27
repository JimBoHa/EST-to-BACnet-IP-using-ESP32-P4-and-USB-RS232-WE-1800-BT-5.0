"""Negative OTA tests for an explicitly disconnected bench gateway."""
import argparse
import base64
import hashlib
import http.client
import json
import time
from pathlib import Path
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import ec,utils
from gateway_client import Client


def run(host, image, output):
    client=Client(host)
    before=client.request('GET','/ota/status')
    assert not before['awaiting_confirmation'] and not before['serial_payload_tx_enabled']
    assert before['device_count']==0 and not before['simulation']
    data=Path(image).read_bytes()
    key=serialization.load_pem_private_key((client.private/'ota-signing-key.pem').read_bytes(),password=None)
    def headers(body):
        signature=key.sign(hashlib.sha256(body).digest(),ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        return {'Content-Type':'application/octet-stream','X-Image-Signature':base64.b64encode(signature).decode()}
    checks=[]
    def rejected(name, method, path, body, hdrs, code):
        try:
            client.request(method,path,body,hdrs)
        except RuntimeError as error:
            assert str(error).startswith(f'HTTP {code}:'),str(error)
            checks.append({'test':name,'result':'PASS','response':str(error)})
        else:
            raise AssertionError(name+' unexpectedly accepted')
    rejected('wrong authentication','GET','/ota/status',None,{'Authorization':'Bearer invalid'},401)
    bad=headers(data);bad['X-Image-Signature']=base64.b64encode(b'invalid-signature').decode()
    rejected('bad image signature','POST','/ota',data,bad,400)
    short=data[:len(data)//2]
    rejected('signed truncated image','POST','/ota',short,headers(short),400)
    wrong=bytearray(data[:4096]);wrong[80:112]=b'wrong_project'.ljust(32,b'\0');wrong=bytes(wrong)
    rejected('wrong project','POST','/ota',wrong,headers(wrong),400)
    connection=http.client.HTTPSConnection(host,context=client.context,timeout=30)
    connection.connect()
    assert connection.sock.getpeercert(binary_form=True)==client.expected
    connection.putrequest('POST','/ota')
    for name,value in {'Authorization':'Bearer '+client.token,'Content-Length':str(len(data)),**headers(data)}.items():
        connection.putheader(name,value)
    connection.endheaders();connection.send(data[:8192]);connection.close()
    time.sleep(1)
    after=client.request('GET','/ota/status')
    for name in ('version','partition','boot_count','registry_epoch','device_count'):
        assert after[name]==before[name],name
    assert not after['awaiting_confirmation']
    checks.append({'test':'connection interrupted during upload','result':'PASS','running_image_unchanged':True})
    result={'result':'PASS','host':host,'checks':checks,'before':before,'after':after}
    Path(output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'result':'PASS','checks':checks},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--host',required=True);p.add_argument('--image',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--disconnected-bench',action='store_true',required=True)
    a=p.parse_args();run(a.host,a.image,a.output)

"""Pinned TLS client for the RX-only gateway. Never disables certificate verification."""
import argparse
import base64
import hashlib
import http.client
import json
import ssl
import time
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import ec,utils

ROOT=Path(__file__).resolve().parents[1]

class UpdateRolledBack(RuntimeError):
    """The candidate failed and the previously running image recovered."""


class Client:
    def __init__(self,host,private=ROOT/"private",timeout=30):
        self.host=host
        self.timeout=timeout
        self.private=Path(private)
        self.token=json.loads((self.private/"tokens.json").read_text())["device"]
        certificate=(self.private/"device-cert.pem").read_bytes()
        self.expected=x509.load_pem_x509_certificate(certificate).public_bytes(serialization.Encoding.DER)
        self.context=ssl.create_default_context(cafile=str(self.private/"device-cert.pem"))
        # DHCP changes addresses. Chain/time verification plus exact leaf pin replaces hostname matching.
        self.context.check_hostname=False

    def request(self,method,path,body=None,headers=None):
        connection=http.client.HTTPSConnection(self.host,context=self.context,timeout=self.timeout)
        connection.connect()
        if connection.sock.getpeercert(binary_form=True)!=self.expected:
            connection.close();raise ssl.SSLError("device certificate pin mismatch")
        h={"Authorization":"Bearer "+self.token,**(headers or {})}
        try:
            connection.request(method,path,body,h)
            response=connection.getresponse();data=response.read()
            if response.status>=400:raise RuntimeError(f"HTTP {response.status}: {data.decode(errors='replace')}")
            return json.loads(data)
        finally:connection.close()

    def upload(self,path,confirm=True):
        before=self.request("GET","/ota/status")
        data=Path(path).read_bytes()
        if len(data)<208 or data[32:36]!=bytes.fromhex('3254cdab'):
            raise ValueError('Expected ESP-IDF application image with app descriptor')
        expected_elf=data[176:208].hex()
        key=serialization.load_pem_private_key((self.private/"ota-signing-key.pem").read_bytes(),password=None)
        signature=key.sign(hashlib.sha256(data).digest(),ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        result=self.request("POST","/ota",data,{"Content-Type":"application/octet-stream","X-Image-Signature":base64.b64encode(signature).decode()})
        if not confirm:return result
        time.sleep(12)
        deadline=time.monotonic()+100
        while time.monotonic()<deadline:
            try:
                status=self.request("GET","/ota/status")
                if status["boot_count"]>before["boot_count"] and status.get("elf_sha256")==before.get("elf_sha256") and status.get("elf_sha256")!=expected_elf and not status.get("awaiting_confirmation"):
                    raise UpdateRolledBack("Candidate failed; previous confirmed image recovered with boot "+str(status["boot_count"]))
                healthy=status.get("startup_phase","ready")=="ready" and status.get("elf_sha256")==expected_elf and status["boot_count"]!=before["boot_count"] and status["uptime_ms"]>=10000 and status["registry_ok"] and status["serial_payload_tx_enabled"] is False and status["simulation"] is False
                if healthy and status.get("printer_profile"):
                    receiver=self.request("GET","/api/v1/serial")
                    parser=self.request("GET","/api/v1/printer?limit=1")
                    healthy=receiver["baud"]==9600 and receiver["configuration_error"]==0 and receiver["usb_connected"] and parser["profile"]==status["printer_profile"] and status.get("external_host_delivery_enabled") is False
                    healthy=healthy and all(status.get(k)==before[k] for k in ("registry_epoch","device_count","inventory_source_sha256") if k in before)
                    if "main_stack_in_dram" in status:
                        healthy=healthy and status["main_stack_in_dram"] and status["event_stack_in_dram"]
                if healthy:
                    self.request("POST","/ota/confirm",b"")
                    return self.request("GET","/ota/status")
            except UpdateRolledBack:raise
            except (OSError,RuntimeError):pass
            time.sleep(2)
        raise RuntimeError("Update not confirmed; device should roll back within 180 seconds")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--host",required=True)
    parser.add_argument("command",choices=["status","upload","registry","confirm"])
    parser.add_argument("file",nargs="?")
    parser.add_argument("--no-confirm",action="store_true",help="Bench rollback test: intentionally let new image time out")
    args=parser.parse_args();client=Client(args.host)
    if args.command=="upload":result=client.upload(args.file,not args.no_confirm)
    elif args.command=="registry":result=client.request("POST","/api/v1/registry",Path(args.file).read_bytes(),{"Content-Type":"application/json"})
    elif args.command=="confirm":result=client.request("POST","/ota/confirm",b"")
    else:result=client.request("GET","/ota/status")
    print(json.dumps(result,indent=2))

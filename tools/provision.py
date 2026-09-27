"""Create local-only TLS credentials and an independent OTA signing key."""
from pathlib import Path
import datetime as dt
import ipaddress
import json
import secrets
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

root=Path(__file__).resolve().parents[1]
private=root/"private"
private.mkdir(mode=0o700,exist_ok=True)
if (private/"provision.h").exists():
    raise SystemExit("Credentials already exist; refusing to rotate implicitly")
now=dt.datetime.now(dt.timezone.utc)
for who in ("device","host"):
    key=ec.generate_private_key(ec.SECP256R1())
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"est3-"+who+".local")])
    san=[x509.DNSName("est3-"+who+".local"),x509.DNSName("localhost"),x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-dt.timedelta(days=1)).not_valid_after(now+dt.timedelta(days=3650)).add_extension(x509.SubjectAlternativeName(san),False).add_extension(x509.BasicConstraints(ca=True,path_length=0),True).sign(key,hashes.SHA256()))
    (private/f"{who}-key.pem").write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    (private/f"{who}-cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
signing=ec.generate_private_key(ec.SECP256R1())
(private/"ota-signing-key.pem").write_bytes(signing.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
(private/"ota-signing-public.pem").write_bytes(signing.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
tokens={r:secrets.token_hex(32) for r in ("viewer","manager","gateway","device")}
(private/"tokens.json").write_text(json.dumps(tokens,indent=2)+"\n")
header="#pragma once\n"
for macro,file in [("DEVICE_CERT","device-cert.pem"),("DEVICE_KEY","device-key.pem"),("SIGNING_PUBLIC","ota-signing-public.pem"),("HOST_CERT","host-cert.pem")]:
    header+="static const char "+macro+"[] = "+json.dumps((private/file).read_text())+";\n"
header+='static const char DEVICE_TOKEN[] = '+json.dumps(tokens["device"])+";\n"
header+='static const char HOST_TOKEN[] = '+json.dumps(tokens["gateway"])+";\n"
(private/"provision.h").write_text(header)
for p in private.iterdir():
    if p.is_file():p.chmod(0o600)
print("Local credentials created; no secret values printed. Signing private key stays off device.")

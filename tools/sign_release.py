"""Create a private detached signature package for the embedded OTA page."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image',type=Path)
    parser.add_argument('--key',type=Path,default=Path(__file__).resolve().parents[1]/'private/ota-signing-key.pem')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    data=args.image.read_bytes()
    if len(data)<208 or data[32:36]!=bytes.fromhex('3254cdab'):
        parser.error('expected ESP-IDF application image')
    digest=hashlib.sha256(data).digest()
    key=serialization.load_pem_private_key(args.key.read_bytes(),password=None)
    signature=key.sign(digest,ec.ECDSA(utils.Prehashed(hashes.SHA256())))
    body={'schema_version':1,'application_sha256':digest.hex(),'elf_sha256':data[176:208].hex(),
          'signature':base64.b64encode(signature).decode()}
    with args.output.open('x') as output:
        args.output.chmod(0o600)
        output.write(json.dumps(body,indent=2)+'\n')
    print('Wrote detached signature package:',args.output)


if __name__=='__main__':
    main()

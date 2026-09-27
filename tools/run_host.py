import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
tokens=json.loads((ROOT/"private/tokens.json").read_text())
for role in ("viewer","manager","gateway"):os.environ["EST3_"+role.upper()+"_TOKEN"]=tokens[role]
os.environ.setdefault("EST3_DB",str(ROOT/"private/history.sqlite"))
from host.api import create_app
import uvicorn
if __name__=="__main__":
    uvicorn.run(create_app(),host=os.environ.get("EST3_BIND","127.0.0.1"),port=8443,ssl_keyfile=str(ROOT/"private/host-key.pem"),ssl_certfile=str(ROOT/"private/host-cert.pem"))

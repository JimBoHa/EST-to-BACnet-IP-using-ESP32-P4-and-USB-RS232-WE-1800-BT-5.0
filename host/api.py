import base64
import html
import os
import secrets
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from .models import Batch, Catalog
from .store import Store, Conflict
from .metasys import proposed_changes


def create_app(store=None, tokens=None):
    store=store or Store(os.environ.get("EST3_DB","private/history.sqlite"))
    tokens=tokens or {role:os.environ.get("EST3_"+role.upper()+"_TOKEN","") for role in ("viewer","manager","gateway")}
    if any(len(t)<32 for t in tokens.values()) or len(set(tokens.values()))!=3:
        raise ValueError("three distinct tokens of at least 32 characters are required")
    app=FastAPI(title="EST3 monitoring draft",docs_url=None,redoc_url=None,openapi_url=None)

    @app.middleware("http")
    async def authenticate(request:Request, call_next):
        auth=request.headers.get("authorization","")
        token=""
        if auth.startswith("Bearer "): token=auth[7:]
        elif auth.startswith("Basic "):
            try: token=base64.b64decode(auth[6:],validate=True).decode().split(":",1)[1]
            except (ValueError,IndexError,UnicodeError): pass
        role=next((r for r,t in tokens.items() if secrets.compare_digest(token,t)),None)
        if role is None:
            return HTMLResponse("Authentication required",401,headers={"WWW-Authenticate":'Basic realm="EST3 monitoring"'})
        request.state.role=role
        received=0
        original=request._receive
        async def bounded_receive():
            nonlocal received
            message=await original()
            received+=len(message.get("body",b""))
            if received>1048576: raise HTTPException(413,"batch exceeds 1 MiB")
            return message
        request._receive=bounded_receive
        response=await call_next(request)
        response.headers["Content-Security-Policy"]="default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'"
        response.headers["Cache-Control"]="no-store"
        response.headers["X-Content-Type-Options"]="nosniff"
        return response

    def require(request, *roles):
        if request.state.role not in roles: raise HTTPException(403,"role cannot perform this action")

    @app.exception_handler(Conflict)
    async def conflict(request,exc):
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail":str(exc)},409)

    @app.post("/api/v1/catalog")
    def catalog(body:Catalog,request:Request):
        require(request,"manager")
        return store.reconcile(body)

    @app.get("/api/v1/registry")
    def registry(request:Request):
        require(request,"manager","gateway")
        return store.registry()

    @app.post("/api/v1/telemetry")
    def telemetry(body:Batch,request:Request):
        require(request,"gateway")
        expected=os.environ.get("EST3_GATEWAY_ID")
        if expected and body.gateway_id!=expected: raise HTTPException(403,"wrong gateway identity")
        return store.ingest(body)

    @app.get("/api/v1/devices")
    def devices(q:str="",floor:str|None=None,kind:str|None=None): return store.devices(q,floor,kind)

    @app.get("/api/v1/events")
    def events(q:str="",uuid:str|None=None,condition:str|None=None,since:float|None=None,until:float|None=None,limit:int=200):
        return store.events(q,uuid,condition,since,until,limit)

    @app.get("/api/v1/metasys/dry-run")
    def mapping(request:Request):
        require(request,"manager")
        import json
        existing={r["binding"]:json.loads(r["managed"]) for r in store.db.execute("SELECT * FROM mappings")}
        return proposed_changes(store.devices(),existing)

    @app.get("/api/v1/status")
    def status():
        return {"protocol":"DISABLED_NO_VERIFIED_ECP_PROFILE","source_mode":store.meta("source_mode","protocol_disabled"),"registry_epoch":store.meta("epoch",0),"metadata_received":store.meta("metadata_received"),"history_gap_count":store.db.execute("SELECT count(*) FROM gaps").fetchone()[0],"metasys":"DRY_RUN_ONLY"}

    def page(title,content):
        return HTMLResponse('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>'+html.escape(title)+'</title><style>body{font:16px system-ui;max-width:1100px;margin:2em auto;padding:1em;background:#f4f6f8;color:#162b3a}a{color:#00579b}table{width:100%;border-collapse:collapse;background:white}td,th{padding:.7em;border-bottom:1px solid #ddd;text-align:left}small{color:#536675}.notice{padding:1em;background:#fff1ba}input,button{padding:.6em}pre{white-space:pre-wrap}</style><nav><a href="/">Devices</a> · <a href="/events">Event history</a></nav><h1>'+html.escape(title)+'</h1><p class="notice">'+html.escape(store.meta("source_mode","PROTOCOL DISABLED"))+' · ECP disabled · Supplemental monitoring draft · Metasys changes remain dry-run</p>'+content+'</html>')

    @app.get("/",response_class=HTMLResponse)
    def directory(q:str=""):
        rows=''.join('<tr><td><a href="/devices/'+d["uuid"]+'">'+html.escape(d["label"])+'</a><br><small>'+html.escape(str(d["address"]))+'</small></td><td>'+html.escape(d["type"])+'</td><td>'+('retired' if d["retired"] else ('valid' if d["data_valid"] else 'UNKNOWN / STALE'))+'</td><td>'+d["placement_status"]+'</td></tr>' for d in store.devices(q))
        return page("Device directory",'<form><input name="q" value="'+html.escape(q,quote=True)+'" placeholder="Search label, address or type"><button>Search</button></form><table><tr><th>Device</th><th>Type</th><th>Quality</th><th>Floor plan</th></tr>'+rows+'</table>')

    @app.get("/devices/{uuid}",response_class=HTMLResponse)
    def device(uuid:str):
        dev=next((d for d in store.devices() if d["uuid"]==uuid),None)
        if not dev: raise HTTPException(404,"device not found")
        rows=''.join('<tr><td>'+k+'</td><td>'+html.escape(str(s["value"]))+'</td><td>'+s["quality"]+'</td><td>'+str(dev["bindings"][k])+'</td></tr>' for k,s in dev["conditions"].items())
        return page(dev["label"],'<p>UUID '+uuid+' · Binding epoch '+str(dev["binding_epoch"])+'</p><table><tr><th>Condition</th><th>Last value</th><th>Quality</th><th>BACnet BI</th></tr>'+rows+'</table><p><a href="/events?uuid='+uuid+'">Device history</a></p>')

    @app.get("/events",response_class=HTMLResponse)
    def event_page(q:str="",uuid:str|None=None,condition:str|None=None,since:float|None=None,until:float|None=None):
        rows=''
        for e in store.events(q,uuid,condition,since,until):
            b=e["body"]
            rows+='<tr><td>'+str(e["sequence"])+'</td><td>'+html.escape(b["received_utc"] or b["time_quality"])+'</td><td>'+html.escape(b["raw_source_code"] or b["record_type"])+'</td><td>'+html.escape(e["label"])+'<br><small>Current: '+html.escape(e["current_label"] or 'unresolved')+'</small></td><td>'+html.escape(b["normalized_condition"]+' / '+b["transition"]+' '+b["reason"])+'</td></tr>'
        return page("Event history",'<form><input name="q" placeholder="Search events"><button>Search</button></form><table><tr><th>Sequence</th><th>Receive time / quality</th><th>Source code</th><th>Historical label</th><th>Transition / gap</th></tr>'+rows+'</table>')
    return app

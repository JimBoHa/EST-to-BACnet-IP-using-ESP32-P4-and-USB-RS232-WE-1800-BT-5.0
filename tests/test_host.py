import copy
import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from host.api import create_app
from host.models import Batch, Catalog
from host.store import Store, Conflict
from host.metasys import proposed_changes
from simulator.catalog import load_catalog

U1="00000000-0000-4000-8000-000000000001"
U2="00000000-0000-4000-8000-000000000002"

@pytest.fixture
def store(tmp_path):
    clock=[1000.0]
    s=Store(tmp_path/"test.sqlite",clock=lambda:clock[0]);s.test_clock=clock
    s.reconcile(load_catalog())
    yield s
    s.db.close()

def ingest(s,*records,boot="boot-1"):
    return s.ingest(Batch.model_validate({"gateway_id":"SIM-GW","boot_id":boot,"source_mode":"simulation","records":list(records)}))

def snap(seq=1,uuid=U1):
    return {"sequence":seq,"record_type":"snapshot","logical_device_id":uuid,"binding_epoch":1,"values":{"alarm":False,"trouble":False}}

def event(seq,kind="alarm",transition="assert",uuid=U1,epoch=1):
    return {"sequence":seq,"record_type":"event","logical_device_id":uuid,"binding_epoch":epoch,"normalized_condition":kind,"transition":transition,"raw_source_code":"SIM_"+kind,"source_label_snapshot":"Historical label <script>alert(1)</script>"}

def test_startup_unknown_and_independent_states(store):
    assert not store.devices()[0]["data_valid"]
    ingest(store,snap(),snap(2,U2),event(3),event(4,"trouble"),event(5,uuid=U2),event(6,transition="restore"))
    a,b=store.devices()
    assert a["conditions"]["trouble"]["value"] is True
    assert a["conditions"]["alarm"]["value"] is False
    assert b["conditions"]["alarm"]["value"] is True
    assert a["data_valid"] and b["data_valid"]
    assert a["conditions"]["disabled"]["quality"]=="unsupported"

def test_heartbeat_and_other_condition_do_not_refresh_alarm(store):
    ingest(store,snap())
    store.test_clock[0]+=61
    ingest(store,{"sequence":2,"record_type":"heartbeat"},event(3,"trouble"))
    d=store.devices()[0]
    assert not d["data_valid"] and d["conditions"]["alarm"]["quality"]=="stale"
    assert d["conditions"]["trouble"]["quality"]=="valid"

def test_retry_gap_restart_and_resync(store):
    assert ingest(store,snap())["ack"]==1
    assert ingest(store,snap())["ack"]==1
    gap={"sequence":5,"record_type":"history_gap","missing_sequence_start":2,"missing_sequence_end":4,"reason":"SIMULATION_ONLY overflow"}
    assert ingest(store,gap)["ack"]==5
    assert not store.devices()[0]["data_valid"]
    ingest(store,event(6));assert not store.devices()[0]["data_valid"]
    ingest(store,snap(7));assert store.devices()[0]["data_valid"]
    assert store.db.execute("select count(*) from events").fetchone()[0]==4
    restarted=Store(store.path,clock=store.clock)
    assert ingest(restarted,snap(7))["ack"]==7
    assert not restarted.devices()[0]["data_valid"]
    restarted.db.close()

def test_out_of_order_waits_for_contiguous_sequence(store):
    assert ingest(store,event(2))["ack"]==0
    assert store.devices()[0]["conditions"]["alarm"]["value"] is None
    assert ingest(store,snap())["ack"]==2
    assert store.devices()[0]["conditions"]["alarm"]["value"] is True

def test_conflicting_duplicate_rolls_back_batch(store):
    ingest(store,snap())
    bad=snap();bad["values"]["alarm"]=True
    with pytest.raises(Conflict):ingest(store,event(2),bad)
    assert len(store.events())==1

def test_rename_add_restart_identity_and_history(store):
    ingest(store,snap(),event(2))
    ids=store.devices()[0]["bindings"]
    result=store.reconcile(load_catalog(2));assert len(result["changes"])==2
    d=store.devices()[0];assert d["bindings"]==ids and d["binding_epoch"]==1 and d["data_valid"]
    assert store.reconcile(load_catalog(2))["idempotent"]
    assert store.events()[0]["label"].startswith("Historical")
    restarted=Store(store.path);assert restarted.devices()[0]["bindings"]==ids;restarted.db.close()

def test_address_reuse_quarantine_and_explicit_new_identity(store):
    body=load_catalog().model_dump();body["revision"]=2
    body["devices"][0]["logical_device_id"]="00000000-0000-4000-8000-000000000099"
    body["approved_retirements"]=True
    with pytest.raises(Conflict):store.reconcile(Catalog.model_validate(body))
    assert store.meta("epoch")==1
    body["identity_decisions"]={body["devices"][0]["logical_device_id"]:"new_identity"}
    store.reconcile(Catalog.model_validate(body))
    ds=store.devices();assert len(ds)==3 and ds[0]["retired"] and ds[2]["first_instance"]>ds[1]["first_instance"]

def test_rebinding_epoch_rejects_old_response(store):
    ingest(store,snap())
    body=load_catalog().model_dump();body["revision"]=2;body["devices"][0]["source_type"]="manual_pull_station"
    with pytest.raises(Conflict):store.reconcile(Catalog.model_validate(body))
    body["identity_decisions"]={U1:"same_logical_replacement"}
    store.reconcile(Catalog.model_validate(body));ingest(store,event(2))
    assert store.devices()[0]["conditions"]["alarm"]["value"] is None

@pytest.mark.parametrize("mutation",["partial","count","duplicate","regression","site"])
def test_bad_catalog_no_corruption(store,mutation):
    body=load_catalog().model_dump();body["revision"]=2
    if mutation=="partial":body["declared_complete"]=False
    if mutation=="count":body["declared_count"]=999
    if mutation=="duplicate":body["devices"][1]["source_address"]=body["devices"][0]["source_address"]
    if mutation=="regression":body["revision"]=1;body["devices"][0]["source_label"]="changed"
    if mutation=="site":body["site_id"]="wrong"
    with pytest.raises(ValueError):store.reconcile(Catalog.model_validate(body))
    assert store.meta("epoch")==1 and len(store.devices())==2

def test_removal_tombstone_and_mass_change_review(store):
    body=load_catalog().model_dump();body["revision"]=2;body["devices"].pop();body["declared_count"]=1
    with pytest.raises(Conflict):store.reconcile(Catalog.model_validate(body))
    body["approved_retirements"]=True;store.reconcile(Catalog.model_validate(body))
    assert store.devices()[1]["retired"] and not store.devices()[1]["data_valid"]

def test_unknown_event_never_clears_alarm(store):
    ingest(store,snap(),event(2),event(3,"unknown","unknown"))
    assert store.devices()[0]["conditions"]["alarm"]["value"] is True
    assert store.events()[0]["condition"]=="unknown"

def test_backup_and_schema_migration(store,tmp_path):
    backup=tmp_path/"backup.sqlite";store.backup(backup)
    restored=Store(backup)
    assert restored.registry()==store.registry()
    assert restored.db.execute("pragma integrity_check").fetchone()[0]=="ok"
    assert restored.db.execute("pragma user_version").fetchone()[0]==2
    restored.db.close()

def test_api_auth_roles_and_injection(store):
    tokens={r:(r+"x"*64) for r in ("viewer","manager","gateway")}
    client=TestClient(create_app(store,tokens))
    assert client.get("/").status_code==401
    viewer={"Authorization":"Bearer "+tokens["viewer"]}
    assert client.post("/api/v1/catalog",json=load_catalog().model_dump(),headers=viewer).status_code==403
    ingest(store,event(1))
    response=client.get("/events",headers=viewer)
    assert "<script>" not in response.text and "&lt;script&gt;" in response.text
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert client.get("/devices/"+U1,headers=viewer).status_code==200
    assert client.get("/api/v1/events?q=Historical",headers=viewer).json()

def test_metasys_idempotent_and_unmanaged_preserved(store):
    first=proposed_changes(store.devices(),{})
    assert first["mode"]=="DRY_RUN" and len(first["changes"])==6
    existing={c["binding"]:{**c["desired"],"graphic_id":"keep","equipment":"keep"} for c in first["changes"]}
    before=copy.deepcopy(existing)
    assert proposed_changes(store.devices(),existing)["changes"]==[]
    assert existing==before

def test_production_telemetry_cannot_inject_simulation():
    with pytest.raises(ValueError):Batch.model_validate({"gateway_id":"GW","boot_id":"B","source_mode":"protocol_disabled","records":[snap()]})

def test_native_registry_fixture_export(store,tmp_path):
    body=store.registry();assert body["source_mode"]=="simulation" and body["epoch"]==1
    ids=[v for d in body["devices"] for v in d["instances"]]
    assert len(ids)==len(set(ids))

def test_backlog_does_not_become_fresh_on_delivery(store):
    batch={"gateway_id":"SIM-GW","boot_id":"B","source_mode":"simulation","sent_monotonic_ms":120000,"records":[snap()]}
    store.ingest(Batch.model_validate(batch))
    assert store.devices()[0]["conditions"]["alarm"]["quality"]=="stale"

def test_out_of_order_observation_keeps_original_age(store):
    ingest(store,event(2))
    store.test_clock[0]+=61
    ingest(store,snap())
    assert store.devices()[0]["conditions"]["alarm"]["quality"]=="stale"

def test_v1_schema_upgrade_preserves_identity(tmp_path):
    from pathlib import Path
    path=tmp_path/'old.sqlite'
    db=sqlite3.connect(path);db.executescript((Path(__file__).parents[1]/'host/migration_001.sql').read_text());db.close()
    upgraded=Store(path)
    assert upgraded.db.execute('pragma user_version').fetchone()[0]==2
    upgraded.reconcile(load_catalog());assert len(upgraded.devices())==2;upgraded.db.close()

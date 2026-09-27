"""Repeatable SIMULATION_ONLY application, history, registry and mapping demo."""
import argparse
import json
from pathlib import Path
from host.models import Batch,Catalog
from host.store import Store,Conflict
from host.metasys import proposed_changes
from simulator.catalog import load_catalog

def run(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    db=directory/'simulation.sqlite'
    if db.exists():raise SystemExit('Use a new demo directory to preserve previous evidence')
    s=Store(db);s.reconcile(load_catalog());initial=s.registry();devices=s.devices()
    records=[]
    for i,d in enumerate(devices):records.append({'sequence':i+1,'record_type':'snapshot','logical_device_id':d['uuid'],'binding_epoch':d['binding_epoch'],'values':{'alarm':False,'trouble':False}})
    for seq,uuid,kind,transition in [(3,devices[0]['uuid'],'alarm','assert'),(4,devices[1]['uuid'],'alarm','assert'),(5,devices[0]['uuid'],'trouble','assert'),(6,devices[0]['uuid'],'alarm','restore')]:
        records.append({'sequence':seq,'record_type':'event','logical_device_id':uuid,'binding_epoch':1,'normalized_condition':kind,'transition':transition,'raw_source_code':'SIM_'+kind.upper(),'source_label_snapshot':next(d['label'] for d in devices if d['uuid']==uuid)})
    body={'gateway_id':'SIM-GW','boot_id':'SIM-DEMO','source_mode':'simulation','records':records}
    ack=s.ingest(Batch.model_validate(body));assert s.ingest(Batch.model_validate(body))==ack
    concurrent=s.devices();rename=s.reconcile(load_catalog(2));after=s.registry()
    assert initial['devices'][0]['instances']==after['devices'][0]['instances']
    conflict=load_catalog(2).model_dump();conflict['revision']=3;conflict['devices'][0]['source_type']='manual_pull_station'
    try:s.reconcile(Catalog.model_validate(conflict));raise AssertionError('address reuse accepted')
    except Conflict:pass
    gap={'gateway_id':'SIM-GW','boot_id':'SIM-DEMO','source_mode':'simulation','records':[{'sequence':10,'record_type':'history_gap','missing_sequence_start':7,'missing_sequence_end':9,'reason':'SIMULATED overflow'}]}
    assert s.ingest(Batch.model_validate(gap))['ack']==10
    (directory/'registry.json').write_text(json.dumps(after,indent=2))
    (directory/'telemetry.json').write_text(json.dumps(body,indent=2))
    (directory/'mapping-dry-run.json').write_text(json.dumps(proposed_changes(s.devices(),{}),indent=2))
    result={'mode':'SIMULATION_ONLY','concurrent_state_before_gap':concurrent,'rename_changes':rename,'after_gap':s.devices(),'ack':10,'address_reuse':'QUARANTINED'}
    (directory/'result.json').write_text(json.dumps(result,indent=2));s.backup(directory/'backup.sqlite');s.db.close()
    print(f'SIMULATION_ONLY demo complete: {directory}')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory');run(p.parse_args().directory)

"""Read selected SDU tables into a qualified inventory; never program a panel.

Requires optional pypxlib 2.5 with the locally built pxlib described in handoff.
All archives and output catalogs are private. No credential tables are read.
"""
import argparse
import copy
import hashlib
import json
import tempfile
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from uuid import NAMESPACE_URL, uuid5

MAX_OBJECTS=2048
FIELDS={
    'OBJECT.DB': ('Cabinet Number','Slot Position','Device Address','Function Flag','LRM Address','CCU Index','SDU Index','Label Text'),
    'SENSOR.DB': ('Cabinet Number','Slot Position','Device Address','Function Flag','Loop Number','Model','Serial Number','CCU Index','SDU Index','Short Address'),
    'MODULE.DB': ('Cabinet Number','Slot Position','Device Address','Function Flag','Loop Number','Model','Serial Number','CCU Index','SDU Index','Short Address'),
    'LRM.DB': ('Cabinet Number','Slot Position','Function Flag','LRM Type','LRM Address'),
    'LOGICDEV.DB': ('Cabinet Number','Slot Position','Device Address','Function Flag','Group LRM','Group Address','LRM Address','Queue Type'),
    'SIGNATUREGROUPS.DB': ('Cabinet Number','Slot Position','Loop','Group_Index_no','Group_name','Output_Type','UniqueIndex'),
}


def clean(value):
    if isinstance(value,bytes):
        return value.decode('ascii')  # Fail closed; this site's selected scalar text is ASCII.
    return value


def read_tables(path):
    from pypxlib import Table
    path=Path(path)
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    result={}
    with tempfile.TemporaryDirectory(prefix='est3-sdu-') as tmp,zipfile.ZipFile(path) as archive:
        names={}
        for info in archive.infolist():
            member=PurePosixPath(info.filename)
            if member.is_absolute() or '..' in member.parts or '\\' in info.filename:
                raise ValueError('unsafe archive member')
            key=info.filename.upper()
            if key in names: raise ValueError('duplicate archive member')
            names[key]=info
        for name,fields in FIELDS.items():
            if name not in names: raise ValueError('missing required table '+name)
            info=names[name]
            if info.file_size>8*1024*1024: raise ValueError('oversized table')
            target=Path(tmp)/name
            target.write_bytes(archive.read(info))
            mb=name[:-3]+'.MB'
            if mb in names:
                if names[mb].file_size>8*1024*1024: raise ValueError('oversized blob table')
                (Path(tmp)/mb).write_bytes(archive.read(names[mb]))
            with Table(str(target)) as table:
                if not set(fields)<=set(table.fields): raise ValueError('unsupported schema '+name)
                if not 0<=len(table)<=10000: raise ValueError('unbounded table '+name)
                rows=[]
                for i in range(len(table)):
                    row=table[i]
                    rows.append({field:clean(row[field]) for field in fields})
                result[name]=rows
    if before!=hashlib.sha256(path.read_bytes()).hexdigest(): raise ValueError('original archive changed')
    return before,result


def key(row):
    return tuple(row[k] for k in ('Cabinet Number','Slot Position','Device Address','Function Flag'))


def build_catalog(tables, archive_hash, site_id):
    tables=copy.deepcopy(tables)
    if not site_id or len(site_id)>64: raise ValueError('site identifier required')
    devices=[];seen=set();physical={};lrms={}
    for row in tables['LRM.DB']:
        k=(row['Cabinet Number'],row['Slot Position'],row['Function Flag'])
        if k in lrms: raise ValueError('ambiguous LRM slot/function')
        lrms[k]=row
    for table in ('SENSOR.DB','MODULE.DB'):
        for row in tables[table]:
            k=key(row)
            if k in physical: raise ValueError('duplicate physical device')
            physical[k]=(table,row)
    joined=set()
    for row in tables['OBJECT.DB']:
        panel,card,address=(row[k] for k in ('Cabinet Number','LRM Address','Device Address'))
        if any(type(n) is not int or not 0<=n<=65535 for n in (panel,card,address)):
            raise ValueError('invalid address components')
        address_key=(panel,card,address)
        if address_key in seen: raise ValueError('duplicate panel/card/address')
        seen.add(address_key)
        lookup=(panel,row['Slot Position'],row['Function Flag'])
        lrm=lrms.get(lookup)
        if panel not in (0,255) and (lrm is None or lrm['LRM Address']!=card): raise ValueError('LRM address join mismatch')
        source_type='SDU object / '+str(row['Function Flag'])
        table,detail=physical.get(key(row),(None,None))
        if detail:
            joined.add(key(row))
            if any(row[k]!=detail[k] for k in ('CCU Index','SDU Index')): raise ValueError('physical object type index mismatch')
            source_type=('Sensor / ' if table=='SENSOR.DB' else 'Module / ')+str(detail['Model'])
        elif lrm: source_type='LRM object / '+str(lrm['LRM Type'])
        elif panel==255: source_type='Unresolved SDU scope 255'
        elif panel==0: source_type='Unresolved SDU scope 0 / '+str(row['Function Flag'])
        normalized=f'P{panel:02d} C{card:02d} D{address:04d}'
        label=row['Label Text'] or normalized
        if not isinstance(label,str) or '\0' in label or len(label.encode())>191: raise ValueError('unsupported label')
        devices.append({'uuid':str(uuid5(NAMESPACE_URL,'est3-sdu-v1:'+site_id+':'+normalized)),
                        'address':normalized,'label':label,'type':source_type,
                        'source_fields':row,'physical':detail,'physical_table':table,
                        'condition_support':'not_yet_verified'})
    if joined!=set(physical): raise ValueError('physical devices absent from OBJECT table')
    if not 1<=len(devices)<=MAX_OBJECTS: raise ValueError('inventory exceeds measured software allocation limit')
    return {'schema_version':2,'source_mode':'est3_sdu_v1','fixture_only':False,'site_id':site_id,
            'archive_sha256':archive_hash,'completeness':'selected_archive_tables_complete',
            'installed_match':'revision_metadata_only_not_full_program_comparison',
            'table_counts':{name:len(rows) for name,rows in tables.items()},
            'physical_count':len(physical),'devices':devices,
            'unresolved_scope_counts':dict(Counter(str(d['source_fields']['Cabinet Number']) for d in devices if d['source_fields']['Cabinet Number'] in (0,255))),
            'relationships':{name:tables[name] for name in ('LRM.DB','LOGICDEV.DB','SIGNATUREGROUPS.DB')},
            'unresolved':['message blobs not interpreted; full raw source retained in original private archive',
                          'raw model and function codes retained; condition capabilities not inferred',
                          'no live content comparison; no automatic retirement',
                          'source address reuse requires reviewed identity decisions before subsequent import']}


def registry_preview(catalog, previous=None, *, prior_catalog=None):
    if catalog.get('schema_version')!=2 or catalog.get('source_mode')!='est3_sdu_v1' or catalog.get('fixture_only') is not False:
        raise ValueError('real SDU catalog required')
    previous=previous or {'epoch':0,'devices':[]}
    if previous.get('source_mode','est3_sdu_v1')!='est3_sdu_v1': raise ValueError('cannot combine simulation/other registries')
    old={d['uuid']:dict(d) for d in previous['devices']}
    if old and (not prior_catalog or prior_catalog.get('site_id')!=catalog['site_id']):
        raise ValueError('previous source catalog required for address-reuse review')
    prior={d['uuid']:d for d in (prior_catalog or {}).get('devices',[])}
    epoch=previous['epoch']+1
    next_id=max([99,*[v for d in old.values() for v in d['instances']]])+1
    result=[];changes=[]
    for d in catalog['devices']:
        u=d['uuid'];p=old.get(u)
        if p:
            before=prior.get(u)
            if not before or before['physical']!=d['physical'] or p['address']!=d['address'] or p['type']!=d['type'] or p['retired']:
                raise ValueError('binding/source identity change requires manual review: '+u)
            if p['label']!=d['label']: changes.append({'uuid':u,'action':'rename','before':p['label'],'after':d['label']})
            p['label']=d['label'];result.append(p)
        else:
            if any(x['address']==d['address'] for x in old.values()): raise ValueError('address reuse requires identity decision')
            result.append({'uuid':u,'address':d['address'],'type':d['type'],'label':d['label'],
                           'label_truncated':False,'binding_epoch':epoch,'instances':list(range(next_id,next_id+5)),
                           'supported':0,'retired':False})
            next_id+=5;changes.append({'uuid':u,'action':'add'})
    incoming={d['uuid'] for d in catalog['devices']}
    for u,d in old.items():
        if u not in incoming: result.append(d);changes.append({'uuid':u,'action':'missing_from_backup_retained_for_review'})
    if len(result)>MAX_OBJECTS: raise ValueError('registry capacity including tombstones exceeded')
    result.sort(key=lambda d:d['instances'][0])
    registry={'schema_version':1,'epoch':epoch,'source_mode':'est3_sdu_v1',
              'provenance':{'archive_sha256':catalog['archive_sha256'],'installed_match':'backup_only_not_live_verified'},'devices':result}
    return registry,{'source_sha256':catalog['archive_sha256'],'objects':len(result),'physical_devices':catalog['physical_count'],
                     'changes':changes,'counts':dict(Counter(c['action'] for c in changes)),
                     'condition_quality':'All current conditions remain unverified; BACnet reliability fault',
                     'unresolved':catalog['unresolved']}


def write_private(path,body):
    with Path(path).open('x') as stream:
        Path(path).chmod(0o600);json.dump(body,stream,indent=2);stream.write('\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive',type=Path);p.add_argument('--site-id',required=True)
    p.add_argument('--output-prefix',type=Path,required=True)
    p.add_argument('--previous-registry',type=Path);p.add_argument('--previous-catalog',type=Path)
    args=p.parse_args();sha,tables=read_tables(args.archive);catalog=build_catalog(tables,sha,args.site_id)
    registry,preview=registry_preview(catalog,json.loads(args.previous_registry.read_text()) if args.previous_registry else None,
        prior_catalog=json.loads(args.previous_catalog.read_text()) if args.previous_catalog else None)
    for suffix,body in (('catalog',catalog),('registry',registry),('preview',preview)):
        write_private(str(args.output_prefix)+'-'+suffix+'.json',body)
    print(json.dumps({'objects':preview['objects'],'physical_devices':preview['physical_devices'],'table_counts':catalog['table_counts'],
                      'changes':preview['counts'],'condition_quality':preview['condition_quality']}))


if __name__=='__main__':main()

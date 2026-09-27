"""Pure dry-run only. No Metasys network writes or invented mapper schema."""
from .store import digest

CHECKLIST = ["Server/API release and license", "Engine capacity including alarm/quality objects", "supportedChildTypes under designated integration", "Actual mapper schema and role scope", "Quality/alarm behavior", "Equipment and floor-plan placement", "External device-page navigation"]


def proposed_changes(devices, existing):
    changes=[]
    for d in devices:
        for condition in (*d["supported"],"data_valid"):
            key=d["uuid"]+":"+condition
            desired={"name":d["label"]+" / "+condition,"instance":d["bindings"][condition],"object_type":"binary-input","retired":bool(d["retired"])}
            old=existing.get(key)
            if old is not None and all(old.get(k)==v for k,v in desired.items()):
                continue
            action="retire_review_dependencies" if d["retired"] else ("update_managed_attributes" if old else "create_mapper_if_supported")
            changes.append({"change_id":digest([key,desired]),"binding":key,"action":action,"desired":desired,"placement_status":d["placement_status"],"device_url":"/devices/"+d["uuid"]})
    return {"mode":"DRY_RUN","site_capabilities_verified":False,"changes":changes,"capability_checklist":CHECKLIST,"unmanaged_relationships":"preserve","deletions":[]}

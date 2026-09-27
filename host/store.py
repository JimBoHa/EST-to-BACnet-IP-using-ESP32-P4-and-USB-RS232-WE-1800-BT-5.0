import hashlib
import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from .models import Batch, Catalog, CONDITIONS


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Conflict(ValueError):
    pass


class Store:
    def __init__(self, path, *, clock=time.time, max_age=60):
        self.path, self.clock, self.max_age = str(path), clock, max_age
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA foreign_keys=ON")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version > 2:
            raise Conflict("database is newer than this software")
        if version == 0:
            self.db.executescript(Path(__file__).with_name("migration_001.sql").read_text())
            version=1
        if version == 1:
            self.db.executescript(Path(__file__).with_name("migration_002.sql").read_text())
        # A host restart cannot establish the freshness of a still-running gateway.
        self.db.execute("UPDATE conditions SET synchronized=0")

    @contextmanager
    def transaction(self):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    def meta(self, key, default=None):
        row = self.db.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def setmeta(self, key, value):
        self.db.execute("INSERT INTO metadata VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, canonical(value)))

    def reconcile(self, catalog: Catalog):
        body = catalog.model_dump()
        source_hash = digest(body)
        try:
            with self.transaction():
                oldrev = self.meta("revision", 0)
                if catalog.revision == oldrev and source_hash == self.meta("source_hash"):
                    return {"epoch": self.meta("epoch", 0), "changes": [], "idempotent": True}
                if catalog.revision <= oldrev:
                    raise Conflict("revision regression or different content at same revision")
                if self.meta("site_id", catalog.site_id) != catalog.site_id:
                    raise Conflict("wrong site")
                old = {r["uuid"]: dict(r) for r in self.db.execute("SELECT * FROM devices")}
                by_address = {r["address"]: r for r in old.values()}
                incoming = {d.logical_device_id: d for d in catalog.devices}
                retiring = [u for u, d in old.items() if not d["retired"] and u not in incoming]
                active_count = sum(not d["retired"] for d in old.values())
                if retiring and len(retiring) / max(active_count, 1) > .3 and not catalog.approved_retirements:
                    raise Conflict("large retirement requires explicit review")
                epoch = self.meta("epoch", 0) + 1
                next_id = self.meta("next_instance", 100)
                changes = []
                for dev in catalog.devices:
                    u = dev.logical_device_id
                    address = canonical(dev.source_address.model_dump())
                    conditions = canonical(sorted(dev.supported_conditions))
                    prior = old.get(u)
                    occupier = by_address.get(address)
                    decision = catalog.identity_decisions.get(u)
                    if occupier and occupier["uuid"] != u:
                        if decision != "new_identity" or occupier["uuid"] in incoming:
                            raise Conflict("address reuse quarantined")
                    changed_binding = prior and (prior["address"] != address or prior["type"] != dev.source_type or prior["supported"] != conditions or prior["retired"])
                    if changed_binding and decision != "same_logical_replacement":
                        raise Conflict("binding/type/reinstatement change requires identity decision")
                    if prior:
                        binding_epoch = epoch if changed_binding else prior["binding_epoch"]
                        self.db.execute("UPDATE devices SET address=?,type=?,label=?,supported=?,retired=0,binding_epoch=? WHERE uuid=?", (address, dev.source_type, dev.source_label, conditions, binding_epoch, u))
                        if changed_binding:
                            self.db.execute("UPDATE conditions SET value=NULL,observed=NULL,synchronized=0 WHERE uuid=?", (u,))
                            self.db.execute("UPDATE devices SET floor=NULL,x=NULL,y=NULL WHERE uuid=?", (u,))
                            changes.append({"uuid": u, "action": "rebind"})
                        elif prior["label"] != dev.source_label:
                            changes.append({"uuid": u, "action": "rename"})
                    else:
                        if next_id + 4 > 4194302:
                            raise Conflict("BACnet instance range exhausted")
                        self.db.execute("INSERT INTO devices(uuid,address,type,label,supported,binding_epoch,first_instance) VALUES (?,?,?,?,?,?,?)", (u,address,dev.source_type,dev.source_label,conditions,epoch,next_id))
                        next_id += 5
                        for kind in CONDITIONS:
                            self.db.execute("INSERT INTO conditions(uuid,kind) VALUES (?,?)", (u,kind))
                        changes.append({"uuid": u, "action": "add"})
                for u in retiring:
                    self.db.execute("UPDATE devices SET retired=1,binding_epoch=? WHERE uuid=?", (epoch,u))
                    self.db.execute("UPDATE conditions SET synchronized=0 WHERE uuid=?", (u,))
                    changes.append({"uuid": u, "action": "retire_review_graphics"})
                for k,v in {"site_id":catalog.site_id,"revision":catalog.revision,"epoch":epoch,"next_instance":next_id,"source_hash":source_hash,"metadata_received":self.clock(),"source_mode":"SIMULATION_ONLY"}.items():
                    self.setmeta(k,v)
                self.db.execute("INSERT INTO journal(kind,source_hash,body,created) VALUES ('catalog_applied',?,?,?)", (source_hash,canonical({"catalog":body,"changes":changes}),self.clock()))
                return {"epoch":epoch,"changes":changes,"idempotent":False}
        except Conflict as exc:
            with self.transaction():
                self.db.execute("INSERT INTO journal(kind,source_hash,body,created) VALUES ('catalog_quarantined',?,?,?)", (source_hash,canonical({"reason":str(exc),"catalog":body}),self.clock()))
            raise

    def _apply_record(self, r, now):
        if r["record_type"] == "history_gap" or (r["record_type"]=="diagnostic" and r["raw_source_code"] in ("GATEWAY_BOOT","SOURCE_GAP")):
            self.db.execute("UPDATE conditions SET synchronized=0")
            return
        if r["record_type"] not in ("event", "snapshot"):
            return  # heartbeat does not refresh any source condition
        dev = self.db.execute("SELECT * FROM devices WHERE uuid=?", (r["logical_device_id"],)).fetchone()
        if not dev or dev["retired"] or r["binding_epoch"] != dev["binding_epoch"]:
            return  # retain historical event, reject obsolete binding for current state
        required = set(json.loads(dev["supported"]))
        if r["record_type"] == "snapshot":
            if set(r["values"]) != required:
                return
            updates = r["values"]
        elif r["normalized_condition"] in required and r["transition"] in ("assert", "restore"):
            updates = {r["normalized_condition"]: r["transition"] == "assert"}
        else:
            return
        for kind,value in updates.items():
            self.db.execute("UPDATE conditions SET value=?, observed=?, synchronized=CASE WHEN ? THEN 1 ELSE synchronized END WHERE uuid=? AND kind=?", (int(value),now,r["record_type"]=="snapshot",dev["uuid"],kind))

    def ingest(self, batch: Batch):
        with self.transaction():
            key = (batch.gateway_id,batch.boot_id)
            stream = self.db.execute("SELECT ack FROM streams WHERE gateway=? AND boot=?",key).fetchone()
            if stream is None:
                self.db.execute("INSERT INTO streams VALUES (?,?,0)",key)
                self.setmeta("active_boot:"+batch.gateway_id,batch.boot_id)
                self.db.execute("UPDATE conditions SET synchronized=0")
            ack = stream[0] if stream else 0
            for rec in batch.records:
                body = rec.model_dump()
                body_hash = digest(body)
                old = self.db.execute("SELECT hash FROM events WHERE gateway=? AND boot=? AND sequence=?", (*key,rec.sequence)).fetchone()
                if old:
                    if old[0] != body_hash:
                        raise Conflict("conflicting duplicate sequence")
                    continue
                overlap = self.db.execute("SELECT 1 FROM gaps WHERE gateway=? AND boot=? AND start<=? AND stop>=?",(*key,rec.sequence,rec.sequence)).fetchone()
                if overlap:
                    raise Conflict("record falls inside a declared gap")
                if rec.record_type == "history_gap":
                    if self.db.execute("SELECT 1 FROM events WHERE gateway=? AND boot=? AND sequence BETWEEN ? AND ?", (*key,rec.missing_sequence_start,rec.missing_sequence_end)).fetchone():
                        raise Conflict("gap overlaps a received record")
                    self.db.execute("INSERT INTO gaps VALUES (?,?,?,?,?)",(*key,rec.sequence,rec.missing_sequence_start,rec.missing_sequence_end))
                now=self.clock()
                age=(batch.sent_monotonic_ms-rec.monotonic_ms)/1000 if batch.sent_monotonic_ms is not None else 0
                self.db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)", (*key,rec.sequence,body_hash,canonical(body),rec.logical_device_id,rec.source_label_snapshot,rec.normalized_condition,now,now-age))
            old_ack=ack
            while True:
                if self.db.execute("SELECT 1 FROM events WHERE gateway=? AND boot=? AND sequence=?",(*key,ack+1)).fetchone():
                    ack+=1
                    continue
                gap=self.db.execute("SELECT stop FROM gaps WHERE gateway=? AND boot=? AND start<=? AND stop>=? ORDER BY stop DESC LIMIT 1",(*key,ack+1,ack+1)).fetchone()
                if gap:
                    ack=gap[0]
                    continue
                break
            if batch.boot_id == self.meta("active_boot:"+batch.gateway_id):
                for row in self.db.execute("SELECT body,observed FROM events WHERE gateway=? AND boot=? AND sequence>? AND sequence<=? ORDER BY sequence",(*key,old_ack,ack)).fetchall():
                    self._apply_record(json.loads(row[0]),row[1])
            self.db.execute("UPDATE streams SET ack=? WHERE gateway=? AND boot=?",(ack,*key))
            return {"schema_version":1,"gateway_id":batch.gateway_id,"boot_id":batch.boot_id,"ack":ack}

    def devices(self, query="", floor=None, kind=None):
        with self.lock:
            result=[]
            for row in self.db.execute("SELECT * FROM devices ORDER BY first_instance"):
                d=dict(row)
                if query.casefold() not in (d["label"]+d["address"]+d["type"]).casefold() or (floor and d["floor"] != floor) or (kind and d["type"] != kind):
                    continue
                d["supported"]=json.loads(d["supported"])
                d["address"]=json.loads(d["address"])
                states={}
                for r in self.db.execute("SELECT * FROM conditions WHERE uuid=?",(d["uuid"],)):
                    state=dict(r)
                    if r["kind"] not in d["supported"]: quality="unsupported"
                    elif d["retired"]: quality="invalid"
                    elif r["value"] is None: quality="unknown"
                    elif not r["synchronized"] or not 0 <= self.clock()-r["observed"] <= self.max_age: quality="stale"
                    else: quality="valid"
                    state["quality"]=quality
                    state["value"]=None if r["value"] is None else bool(r["value"])
                    states[r["kind"]]=state
                d["conditions"]=states
                d["data_valid"]=bool(d["supported"]) and all(states[k]["quality"]=="valid" for k in d["supported"])
                d["bindings"]={k:d["first_instance"]+i for i,k in enumerate((*CONDITIONS,"data_valid"))}
                d["placement_status"]="placed" if d["floor"] and d["x"] is not None and d["y"] is not None else "unplaced"
                result.append(d)
            return result

    def events(self, query="", uuid=None, condition=None, since=None, until=None, limit=200):
        with self.lock:
            rows=self.db.execute("SELECT e.*,d.label AS current_label FROM events e LEFT JOIN devices d ON d.uuid=e.uuid WHERE (? IS NULL OR e.uuid=?) AND (? IS NULL OR e.condition=?) AND (? IS NULL OR e.received>=?) AND (? IS NULL OR e.received<=?) AND (?='' OR instr(lower(e.body||coalesce(d.label,'')),lower(?))>0) ORDER BY e.received DESC,e.sequence DESC LIMIT ?", (uuid,uuid,condition,condition,since,since,until,until,query,query,min(max(limit,1),1000)))
            return [{**dict(r),"body":json.loads(r["body"])} for r in rows]

    def registry(self):
        def cut(text, maximum):
            return text.encode()[:maximum].decode("utf-8",errors="ignore")
        return {"schema_version":1,"epoch":self.meta("epoch",0),"source_mode":"simulation","devices":[{"uuid":d["uuid"],"address":canonical(d["address"]),"type":cut(d["type"],63),"label":cut(d["label"],191),"label_truncated":len(d["label"].encode())>191,"binding_epoch":d["binding_epoch"],"instances":[d["bindings"][k] for k in (*CONDITIONS,"data_valid")],"supported":sum(1<<CONDITIONS.index(k) for k in d["supported"]),"retired":bool(d["retired"])} for d in self.devices()]}

    def backup(self, destination):
        with self.lock, sqlite3.connect(destination) as other:
            self.db.backup(other)

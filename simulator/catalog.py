"""Explicit fixture adapter. No contractor export format has been supplied."""
import json
from pathlib import Path
from host.models import Catalog

def load_catalog(revision=1):
    raw=json.loads((Path(__file__).resolve().parents[1]/"fixtures"/f"catalog-v{revision}.json").read_text())
    return Catalog.model_validate({"source_mode":"simulation","fixture_only":True,"site_id":raw["site_id"],"revision":revision,"declared_complete":True,"declared_count":len(raw["devices"]),"devices":[{k:d[k] for k in ("logical_device_id","source_address","source_type","source_label","supported_conditions")} for d in raw["devices"]]})

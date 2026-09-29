"""Package an already-built application privately; never flash or upload it."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
build=ROOT/'firmware/build'
description=json.loads((build/'project_description.json').read_text())
version=description['project_version']
destination=ROOT/'release'/version
destination.mkdir(parents=True,exist_ok=True)
files={'est3_gateway_rxonly.bin':build/'est3_gateway_rxonly.bin',
       'bootloader.bin':build/'bootloader/bootloader.bin',
       'partition-table.bin':build/'partition_table/partition-table.bin',
       'ota_data_initial.bin':build/'ota_data_initial.bin'}
binary=files['est3_gateway_rxonly.bin'].read_bytes()
if binary[32:36]!=bytes.fromhex('3254cdab'):
    raise SystemExit('Application descriptor missing')
cache=(build/'CMakeCache.txt').read_text().splitlines()
nm=next(line.split('=',1)[1] for line in cache if line.startswith('CMAKE_NM:FILEPATH='))
symbols=subprocess.run([nm,'--defined-only',str(build/'est3_gateway_rxonly.elf')],
                       check=True,capture_output=True,text=True).stdout
names={line.split()[-1] for line in symbols.splitlines() if line.split()}
if {'gw_observe','cdc_acm_host_data_tx_blocking'} & names:
    raise SystemExit('Production image contains simulation observer or serial payload TX')
if not {'__wrap_cdc_acm_host_open','observe_usb_packet'} <= names:
    raise SystemExit('Receive diagnostics USB observer is not linked')
if 'pr_feed' not in names:
    raise SystemExit('On-device printer observation parser is not linked')
hashes={}
for name,source in files.items():
    target=destination/name
    if target.exists() and target.read_bytes()!=source.read_bytes():
        raise SystemExit(f'Refusing to overwrite different archived binary: {target}')
    shutil.copyfile(source,target)
    target.chmod(0o600)
    hashes[name]=hashlib.sha256(target.read_bytes()).hexdigest()
(destination/'SHA256SUMS.txt').write_text(''.join(f'{digest}  {name}\n' for name,digest in hashes.items()))
manifest={'version':version,'built_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'status':'BUILT; consult STATUS.md for installation/test state',
          'idf':'v5.5.5','idf_commit':'b774170ff46c393eeb5e495ea37936038d3f4f4f',
          'target':'esp32p4','chip_range':'1.0-1.99','board_chip':'1.3',
          'elf_sha256':binary[176:208].hex(),'application_size_bytes':len(binary),
          'release_files_sha256':hashes,
          'production_symbol_audit':{'simulation_observer_absent':True,'original_payload_tx_absent':True,
                                     'usb_receive_observer_linked':True,'printer_parser_linked':True},
          'external_history_host_required':False,'current_state_decoder_validated':False,
          'recent_observation_storage':'128 bounded RAM records; no long-term journal'}
for path in (ROOT/f'evidence/build-manifest-{version}.json',ROOT/'evidence/build-manifest.json'):
    path.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))

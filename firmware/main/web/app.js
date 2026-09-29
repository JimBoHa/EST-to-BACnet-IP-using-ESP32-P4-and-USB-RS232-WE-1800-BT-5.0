'use strict';
const $ = id => document.getElementById(id);
let key = '', latest = null, offset = 0, matched = 0, candidate = null, polling = false, updating = false;
const text = (tag, content, className) => { const e=document.createElement(tag); e.textContent=content; if(className)e.className=className; return e; };
function notice(message, error=false) { $('connection').textContent=message; $('connection').className='banner'+(error?' error':''); }
function toast(message, error=false) { $('toast').textContent=message; $('toast').className='show'+(error?' error':''); setTimeout(()=>$('toast').className='',6000); }
async function request(path, method='GET', body, headers={}) {
  if(!key)throw Error('Enter the saved device admin key.');
  const response=await fetch(path,{method,body,cache:'no-store',credentials:'omit',signal:AbortSignal.timeout(method==='POST'?60000:15000),headers:{Authorization:'Bearer '+key,...headers}});
  if(!response.ok)throw Error('HTTP '+response.status+': '+(await response.text()).slice(0,200));
  return response.json();
}
function metrics(id, pairs) { $(id).replaceChildren(...pairs.map(([label,value])=>{const row=text('div','','metric');row.append(text('span',label),text('strong',String(value)));return row;})); }
const bytes = n => n>=1048576?(n/1048576).toFixed(1)+' MiB':n>=1024?(n/1024).toFixed(1)+' KiB':n+' B';
function render(s,r,p) {
  metrics('controllerMetrics',[['Firmware',s.version],['Address',s.ip],['Boot',s.boot_count],['Uptime',(s.uptime_ms/3600000).toFixed(2)+' h'],['Free memory',bytes(s.heap_free)],['Internal free',bytes(s.internal_heap_free)],['OTA',s.awaiting_confirmation?'Confirmation pending':'Confirmed']]);
  metrics('receiverMetrics',[['USB adapter',r.usb_connected?'Connected':'Disconnected'],['Profile',r.baud+' '+r.format],['UART bytes',r.rx_bytes],['Receive drops',r.rx_drops],['Payload TX','Disabled'],['Current conditions','Unverified']]);
  metrics('bacnetMetrics',[['Device instance',s.bacnet_device_instance],['Vendor ID',s.bacnet_vendor_id],['Transport','IPv4 UDP 47808'],['Services','Discovery / RP / RPM'],['Catalog objects',s.device_count],['Registry epoch',s.registry_epoch],['Data valid','No verified current state']]);
  metrics('rxMetrics',[['USB packets',r.usb_in_packets],['Status-only packets',r.usb_status_only_packets],['UART errors',r.usb_line_error_packets],['USB errors',r.usb_errors],['Receive drops',r.rx_drops],['Last payload uptime',(r.last_payload_ms/1000).toFixed(1)+' s']]);
  metrics('parseMetrics',[['Complete reports',p.complete_reports],['Incomplete reports',p.incomplete_reports],['Unknown records',p.unrecognized],['Stream boundaries/gaps',p.gaps],['Retained records',p.retained],['Evicted records',p.evicted],['Partial bytes',p.partial_bytes]]);
  $('networkConfig').textContent='Address: '+s.ip+' · DHCP · Device '+s.bacnet_device_instance+' · Vendor '+s.bacnet_vendor_id+' · '+s.bacnet_assignment;
  const rev=p.last_complete_report;
  if(rev.complete) {
    $('revision').replaceChildren(text('p','Panel '+rev.panel+' · CPU '+rev.cpu+' · SDU '+rev.sdu+' · Project '+rev.project+' · Database '+rev.database_date),text('p','Panel timestamp: '+rev.source_time+' (timezone unverified) · Historical alarm count: '+rev.historical_alarm_count),text('p',rev.cards.map(c=>'Card '+c.address+': '+c.type+' '+c.firmware).join(' · ')));
  } else $('revision').textContent='No complete report received during this boot.';
  const decoder=new TextDecoder('utf-8');
  $('recent').textContent=p.records.map(line=>{
    const raw=Uint8Array.from(line.raw_hex.match(/../g)||[],h=>parseInt(h,16));
    return '#'+line.id+' · '+(line.received_monotonic_ms/1000).toFixed(3)+' s · '+line.parse_status+' · byte '+line.offset+'\n'+decoder.decode(raw).replaceAll('\0','\\0');
  }).join('\n\n')||'No received records during this boot.';
}
async function refresh() {
  if(!key||polling||updating)return;
  polling=true;
  try {const s=await request('/api/v1/status'),r=await request('/api/v1/serial'),p=await request('/api/v1/printer');latest={status:s,serial:r,printer:p};render(s,r,p);notice('Connected to '+s.ip+' · Last read '+new Date().toLocaleTimeString()+' · Panel condition quality remains unverified.');}
  catch(error){notice('Live connection unavailable. Displayed values may be stale. '+error.message,true);}
  finally{polling=false;}
}
async function directory() {
  const result=await request('/api/v1/devices?q='+encodeURIComponent($('query').value)+'&offset='+offset+'&limit=40');matched=result.matched;
  $('inventoryInfo').textContent=result.total+' catalog objects · Registry '+result.registry_epoch+' · '+result.inventory_quality;
  $('deviceRows').replaceChildren(...result.devices.map(d=>{
    const row=document.createElement('tr'),name=document.createElement('td'),button=text('button',d.label||d.uuid,'action');
    button.onclick=()=>{location.hash='device='+encodeURIComponent(d.uuid);showDevice(d);};name.append(button,text('div',d.address,'note'));
    row.append(name,text('td',d.type),text('td',d.retired?'Retired':d.data_valid?'Valid':'Unknown / unverified','quality'),text('td',d.conditions.map(c=>c.instance).join(', ')+' · Valid '+d.data_valid_instance));return row;
  }));
  $('pageInfo').textContent=(matched?offset+1:0)+'–'+Math.min(offset+40,matched)+' of '+matched;
  $('previous').disabled=offset===0;$('next').disabled=offset+40>=matched;
}
function showDevice(d) {
  $('deviceDetail').hidden=false;
  $('deviceDetail').replaceChildren(text('h3',d.label),text('p',d.uuid+' · Binding epoch '+d.binding_epoch),...d.conditions.map(c=>text('p',c.condition+': '+(c.last_value===null?'No observation':c.last_value?'Last active':'Last inactive')+' · '+c.quality+' · BI '+c.instance)));
}
function download(name,value) {
  const link=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'}));link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function action(id, fn) { $(id).addEventListener('click',()=>Promise.resolve().then(fn).catch(e=>toast(e.message,true))); }
document.querySelectorAll('.tab').forEach(button=>button.onclick=()=>{document.querySelectorAll('.tab,.panel').forEach(e=>e.classList.remove('active'));button.classList.add('active');$(button.dataset.panel).classList.add('active');if(button.dataset.panel==='devices'&&key)directory().catch(e=>toast(e.message,true));});
action('connect',async()=>{key=$('key').value.trim();$('key').value='';await refresh();if(location.hash.startsWith('#device=')){const id=decodeURIComponent(location.hash.slice(8));$('query').value=id;await directory();const result=await request('/api/v1/devices?q='+encodeURIComponent(id));if(result.devices[0])showDevice(result.devices[0]);document.querySelector('[data-panel=devices]').click();}});
action('lock',()=>{key='';latest=null;candidate=null;$('key').value='';location.reload();});
$('keyFile').onchange=async()=>{try{const file=$('keyFile').files[0];if(!file||file.size>8192)throw Error('Expected a small device key JSON file.');const value=JSON.parse(await file.text());const found=value.device_token||value.device;if(typeof found!=='string'||found.length<32||found.length>80)throw Error('No device admin key in file.');$('key').value=found;toast('Key loaded. Press Connect.');}catch(e){toast(e.message,true);}finally{$('keyFile').value='';}};
$('search').onsubmit=e=>{e.preventDefault();offset=0;directory().catch(e=>toast(e.message,true));};
action('previous',()=>{offset=Math.max(0,offset-40);return directory();});action('next',()=>{offset+=40;return directory();});
action('download',()=>{if(!latest)throw Error('Connect first.');download('est3-recent-diagnostics.json',latest);});
$('baudForm').onsubmit=async e=>{e.preventDefault();try{await request('/api/v1/serial','POST',JSON.stringify({baud:Number($('baud').value)}),{'Content-Type':'application/json'});toast('Receiver setting requested; verify the applied rate under Status.');await refresh();}catch(error){toast(error.message,true);}};
action('previewRegistry',async()=>{candidate=null;$('applyRegistry').disabled=true;const file=$('registryFile').files[0];if(!file||file.size>1048576)throw Error('Select a registry JSON file up to 1 MiB.');const raw=await file.text();const result=await request('/api/v1/registry/preview','POST',raw,{'Content-Type':'application/json'});candidate=raw;$('registryPreview').textContent=JSON.stringify(result,null,2);$('applyRegistry').disabled=false;});
action('applyRegistry',async()=>{if(!candidate)throw Error('Validate a registry first.');await request('/api/v1/registry','POST',candidate,{'Content-Type':'application/json'});candidate=null;$('applyRegistry').disabled=true;toast('Registry committed.');await refresh();});
$('registryFile').onchange=()=>{candidate=null;$('applyRegistry').disabled=true;$('registryPreview').textContent='';};
action('backupRegistry',async()=>download('est3-registry-backup.json',await request('/api/v1/registry')));
const hex = buffer => Array.from(new Uint8Array(buffer),v=>v.toString(16).padStart(2,'0')).join('');
const delay = ms => new Promise(resolve=>setTimeout(resolve,ms));
action('upload',async()=>{
  const file=$('image').files[0],signature=$('signature').files[0];if(!file||!signature||file.size>0x500000||signature.size>8192)throw Error('Select an application image and its detached signature JSON.');
  const data=await file.arrayBuffer(),sig=JSON.parse(await signature.text()),hash=hex(await crypto.subtle.digest('SHA-256',data));
  if(data.byteLength<208||sig.application_sha256!==hash||sig.elf_sha256!==hex(data.slice(176,208))||typeof sig.signature!=='string')throw Error('Image and signature package do not match.');
  const before=await request('/ota/status');updating=true;$('upload').disabled=true;
  try {
    $('otaResult').textContent='Uploading signed application…';await request('/ota','POST',data,{'Content-Type':'application/octet-stream','X-Image-Signature':sig.signature});
    $('otaResult').textContent='Waiting for reboot and receiver health…';await delay(12000);
    const deadline=Date.now()+100000;
    while(Date.now()<deadline) {
      try {
        const s=await request('/ota/status'),r=await request('/api/v1/serial');
        if(s.elf_sha256===sig.elf_sha256&&s.boot_count!==before.boot_count&&s.uptime_ms>=10000&&s.registry_ok&&!s.serial_payload_tx_enabled&&!s.simulation&&r.baud===9600&&r.configuration_error===0&&r.usb_connected&&!s.external_host_delivery_enabled&&s.registry_epoch===before.registry_epoch&&s.device_count===before.device_count&&s.inventory_source_sha256===before.inventory_source_sha256) {
          await request('/api/v1/printer');await request('/ota/confirm','POST',new Uint8Array());const confirmed=await request('/ota/status');
          if(confirmed.awaiting_confirmation||confirmed.elf_sha256!==sig.elf_sha256)throw Error('Confirmation readback mismatch.');
          $('otaResult').textContent='Confirmed firmware '+confirmed.version+' · Boot '+confirmed.boot_count;return;
        }
      }catch(error){$('otaResult').textContent='Waiting for verified boot: '+error.message;}
      await delay(2500);
    }
    throw Error('Image was not confirmed; automatic rollback is expected within 180 seconds.');
  }finally{updating=false;$('upload').disabled=false;await refresh();}
});
setInterval(refresh,5000);

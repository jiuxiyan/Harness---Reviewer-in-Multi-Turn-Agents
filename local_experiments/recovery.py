"""Explicit replay of durable responses; uncertain dispatches require local decisions."""
import json
import time
from pathlib import Path
from .storage import RunFailure,digest

def read(path):return json.loads(Path(path).read_text())

def inspect_run(directory):
 root=Path(directory);manifest=read(root/'run_manifest.json');events=[];parent=None
 path=root/'journal/events.jsonl'
 if path.exists():
  for line in path.read_text().splitlines():
   try:e=json.loads(line)
   except ValueError:raise RunFailure('recovery_torn_journal_requires_manual_preservation') from None
   h=e.pop('content_hash')
   if digest(e)!=h or e['parent_hash']!=parent or e['protocol_hash']!=manifest['protocol_hash']:raise RunFailure('recovery_journal_integrity_mismatch')
   e['content_hash']=h;parent=h;events.append(e)
 for e in events:
  if e['kind']=='recovery_source':manifest['budget_origin_ns']=e['budget_origin_ns']
 requests={}
 for e in events:
  if e['kind']=='request_dispatched':requests[e['physical_call_id']]={'dispatch':e,'end':None}
  elif e['kind'] in ('response_saved','request_failed'):
   if e['physical_call_id'] not in requests:raise RunFailure('recovery_unpaired_response')
   requests[e['physical_call_id']]['end']=e
 unknown=[]
 for physical,r in requests.items():
  end=r['end']
  if end is None or end.get('status')=='provider_result_unknown':unknown.append(physical)
 return root,manifest,requests,unknown

def plan(directory,output):
 from .storage import write_json
 _,manifest,requests,unknown=inspect_run(directory)
 value={'source_run_id':manifest['run_id'],'protocol_hash':manifest['protocol_hash'],
        'unknown_requests':{str(i):{'decision':'UNRESOLVED','accept_possible_duplicate_charge':False} for i in unknown},
        'choices':['abandon','retry'],'instruction':'Choose each unknown dispatch explicitly. retry requires accept_possible_duplicate_charge=true. Confirmed responses replay locally. Known failures remain failures.'}
 write_json(output,value);return {'unknown_dispatches':len(unknown),'physical_attempts':len(requests),'model_calls':0}

class Recovery:
 def __init__(self,directory,decisions,client):
  self.root,m,requests,unknown=inspect_run(directory);self.client=client;self.groups={}
  if m['config']!=client.config or m['source_hashes']!=client.store.sources or m['mode']!=client.store.mode:raise RunFailure('recovery_config_source_or_mode_mismatch')
  d=read(decisions)
  if d.get('source_run_id')!=m['run_id'] or d.get('protocol_hash')!=m['protocol_hash'] or set(d.get('unknown_requests',{}))!={str(x) for x in unknown}:raise RunFailure('recovery_decision_binding_mismatch')
  for i in unknown:
   choice=d['unknown_requests'][str(i)]
   if choice.get('decision') not in ('abandon','retry') or (choice['decision']=='retry' and choice.get('accept_possible_duplicate_charge') is not True):raise RunFailure('uncertain_request_requires_explicit_decision')
  self.decisions=d['unknown_requests'];self.replayed=set()
  client.store.save('private/recovery_decisions.json',d)
  client.store.event('recovery_source',source_run_id=m['run_id'],source_protocol_hash=m['protocol_hash'],budget_origin_ns=m['budget_origin_ns'])
  client.started=time.monotonic()-(time.time_ns()-m['budget_origin_ns'])/1e9
  for physical,r in sorted(requests.items()):
   event=r['dispatch'];logical=event['logical_request_id'];self.groups.setdefault(logical,[]).append(r)
   payload=read(self.root/f'private/requests/{physical}.json')
   if digest(payload)!=event['stored_payload_digest'] or event['stored_payload_digest']!=event['payload_digest']:raise RunFailure('recovery_redacted_or_corrupt_payload')
   client.store.save(f'private/requests/{physical}.json',payload)
   common={k:event[k] for k in ('physical_call_id','logical_request_id','attempt','role','payload_digest','stored_payload_digest','context')}
   client.store.event('request_dispatched',**common,replayed_from=m['run_id'])
   end=r['end'];record={**common,'status':'provider_result_unknown','usage':None,'cost':None}
   if end is not None:
    if end['kind']=='response_saved':
     response=read(self.root/f'private/responses/{physical}.json')
     if digest(response)!=end['stored_response_digest']:raise RunFailure('recovery_response_integrity_mismatch')
     client.store.save(f'private/responses/{physical}.json',response);r['response']=response
     record.update(status='response_saved',usage=end.get('usage'))
    else:record['status']=end.get('status','http_failure')
    fields={k:v for k,v in end.items() if k not in ('schema_version','event_id','parent_hash','run_id','protocol_hash','evidence_kind','timestamp_ns','kind','content_hash')}
    client.store.event(end['kind'],**fields)
   client.records.append(record)
  client.calls=max(requests,default=0)
 def replay(self,logical,payload):
  if logical not in self.groups:return False,None
  self.replayed.add(logical);records=self.groups[logical]
  if any(r['dispatch']['payload_digest']!=digest(payload) for r in records):raise RunFailure('recovery_request_diverged')
  last=records[-1];end=last['end'];physical=last['dispatch']['physical_call_id']
  if end and end['kind']=='response_saved':return True,last['response']
  if end and end.get('status')!='provider_result_unknown':raise RunFailure('provider_error_exhausted')
  choice=self.decisions[str(physical)]
  if choice['decision']=='abandon':raise RunFailure('provider_result_unknown')
  if logical!=max(self.groups):raise RunFailure('uncertain_retry_requires_no_later_requests')
  self.client.store.event('uncertain_retry_authorized',original_physical_call_id=physical,logical_request_id=logical,possible_duplicate_charge_accepted=True)
  return False,None
 def assert_complete(self):
  if self.replayed!=set(self.groups):raise RunFailure('recovery_did_not_replay_all_requests')

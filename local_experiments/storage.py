"""Private, append-only run evidence and bounded writes; no secrets in metadata."""
import hashlib
import json
import os
from pathlib import Path
import time
from .config import canonical

class RunFailure(RuntimeError): pass

def digest(obj): return hashlib.sha256(canonical(obj).encode()).hexdigest()

def write_json(path, value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf8') as f:
  f.write(canonical(value)+'\n');f.flush();os.fsync(f.fileno())
 path.chmod(0o600)

class Store:
 def __init__(self,root,config,mode):
  self.root=Path(root);self.root.mkdir(parents=True,exist_ok=False);self.root.chmod(0o700)
  self.secrets=();self.config=config;self.mode=mode;self.run_id=self.root.name+'-'+str(time.time_ns())
  from .provenance import source_hashes
  self.sources=source_hashes();self.protocol_hash=digest({'config':config,'sources':self.sources});self.sequence=0;self.used=0;self.parent=None
  self.evidence='scripted_fixture' if mode=='dry-run' else ('confirmatory_live' if config['stage']=='confirmatory-roots' else 'exploratory_live')
  for name in ('private/requests','private/responses','private/checkpoints','private/evaluation','journal','derived'):
   (self.root/name).mkdir(parents=True,exist_ok=True)
  self.save('run_manifest.json',{'run_id':self.run_id,'budget_origin_ns':time.time_ns(),'protocol_hash':self.protocol_hash,'config':config,'mode':mode,'evidence_kind':self.evidence,'schema_version':1,'source_hashes':self.sources})
 def sanitize(self,value):
  if isinstance(value,str):
   for secret in self.secrets: value=value.replace(secret,'[REDACTED_CREDENTIAL]')
   return value
  if isinstance(value,list): return [self.sanitize(x) for x in value]
  if isinstance(value,dict): return {self.sanitize(k):('[REDACTED_HEADER]' if k.lower() in ('authorization','proxy-authorization','x-api-key','api_key') else self.sanitize(v)) for k,v in value.items()}
  return value
 def reserve(self,n):
  if self.used+n>self.config['limits']['max_output_bytes']: raise RunFailure('output_budget_stopped')
  self.used+=n
 def save(self,name,value):
  value=self.sanitize(value)
  self.reserve(len(canonical(value).encode())+1);write_json(self.root/name,value)
 def append(self,name,value):
  value=self.sanitize(value)
  body=canonical(value)+'\n';self.reserve(len(body.encode()))
  with (self.root/name).open('a',encoding='utf8') as f:
   f.write(body);f.flush();os.fsync(f.fileno())
 def event(self,kind,**fields):
  self.sequence+=1
  e={'schema_version':1,'event_id':self.sequence,'parent_hash':self.parent,'run_id':self.run_id,'protocol_hash':self.protocol_hash,'evidence_kind':self.evidence,'timestamp_ns':time.time_ns(),'kind':kind,**fields}
  e=self.sanitize(e)
  e['content_hash']=digest(e);self.append('journal/events.jsonl',e);self.parent=e['content_hash']

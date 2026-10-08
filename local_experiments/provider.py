"""One explicit Chat Completions wire protocol, with injectable offline transport."""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from .storage import RunFailure, digest

class HTTPFailure(Exception):
 def __init__(self,status): self.status=status
class UnknownResult(Exception): pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs): raise HTTPFailure(302)

class HTTPTransport:
 def __init__(self,base_url,key,timeout,max_bytes):
  p=urllib.parse.urlsplit(base_url)
  if p.scheme!='https' or not p.hostname or p.username or p.password or p.query or p.fragment: raise RunFailure('invalid_https_endpoint')
  if not key or '\n' in key or '\r' in key: raise RunFailure('invalid_local_credential')
  self.url=base_url.rstrip('/')+'/chat/completions';self.key=key
  self.timeout=timeout;self.max_bytes=max_bytes
  self.opener=urllib.request.build_opener(NoRedirect())
 def __call__(self,payload):
  request=urllib.request.Request(self.url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.key},method='POST')
  try:
   with self.opener.open(request,timeout=self.timeout) as response: raw=response.read(self.max_bytes+1)
  except urllib.error.HTTPError as e: raise HTTPFailure(e.code) from None
  except (urllib.error.URLError,TimeoutError,OSError): raise UnknownResult() from None
  if len(raw)>self.max_bytes: raise UnknownResult()
  try: return json.loads(raw)
  except (ValueError,UnicodeError): raise UnknownResult() from None

def validate_wire(messages):
 pending=set();seen=set()
 for m in messages:
  if not isinstance(m,dict): raise ValueError()
  if m.get('role') not in ('system','user','assistant','tool'): raise RunFailure('unsupported_message_role')
  if pending and m['role']!='tool': raise RunFailure('missing_tool_result')
  if m['role']=='tool':
   key=m.get('tool_call_id')
   if key not in pending: raise RunFailure('unpaired_tool_result')
   pending.remove(key)
  calls=m.get('tool_calls') or []
  if calls and m['role']!='assistant': raise RunFailure('invalid_tool_owner')
  for c in calls:
   key=c.get('id')
   if not isinstance(key,str) or not key or key in seen: raise RunFailure('duplicate_tool_identity')
   seen.add(key);pending.add(key)
 if pending: raise RunFailure('pending_tool_call_in_request')

def parse_response(response):
 try:
  if not isinstance(response,dict): raise ValueError()
  choices=response['choices']
  if not isinstance(choices,list) or len(choices)!=1: raise ValueError()
  if not isinstance(choices[0],dict): raise ValueError()
  if choices[0].get('finish_reason') not in ('stop','tool_calls'): raise ValueError()
  m=choices[0]['message']
  if not isinstance(m,dict): raise ValueError()
  if m.get('role')!='assistant' or m.get('refusal'): raise ValueError()
  text=m.get('content');calls=m.get('tool_calls') or []
  if text is not None and not isinstance(text,str): raise ValueError()
  if not isinstance(calls,list) or (not text and not calls) or (text and calls): raise ValueError()
  seen=set()
  for c in calls:
   if not isinstance(c,dict): raise ValueError()
   if c.get('type')!='function' or not isinstance(c.get('id'),str) or not c['id'] or c['id'] in seen: raise ValueError()
   seen.add(c['id']);f=c['function']
   if not isinstance(f,dict): raise ValueError()
   if not isinstance(f['name'],str) or not f['name']: raise ValueError()
   args=json.loads(f['arguments'])
   if not isinstance(args,dict): raise ValueError()
  return {'role':'assistant','content':text,'tool_calls':calls}
 except (KeyError,TypeError,ValueError): raise RunFailure('actor_output_invalid') from None

class Client:
 def __init__(self,config,store,transport,models):
  self.config=config;self.store=store;self.transport=transport;self.models=models
  self.calls=0;self.logical=0;self.started=time.monotonic()
 def __deepcopy__(self,memo): return self
 def call(self,role,messages,tools=None,context=None):
  validate_wire(messages);self.logical+=1;logical=self.logical
  messages=json.loads(json.dumps(messages))
  for message in messages:
   for call in message.get('tool_calls') or []: call.pop('name',None)
  c=self.config;m=c['models'];limits=c['limits']
  payload={'model':self.models[role], 'messages':messages, 'temperature':m['temperature'], 'max_completion_tokens':m['max_completion_tokens'],'stream':False,'n':1}
  if tools: payload.update(tools=tools,parallel_tool_calls=False)
  if m['provider_seed_supported']: payload['seed']=(c['sampling']['allocation_seed']+logical)%2147483647
  for attempt in range(limits['max_retries_per_request']+1):
   if self.calls>=limits['max_physical_requests'] or time.monotonic()-self.started>=limits['run_timeout_seconds']: raise RunFailure('budget_stopped')
   self.calls+=1;physical=self.calls;start=time.monotonic()
   self.store.save(f'private/requests/{physical}.json',payload)
   common={'physical_call_id':physical,'logical_request_id':logical,'attempt':attempt,'role':role,'payload_digest':digest(payload),'stored_payload_digest':digest(self.store.sanitize(payload)),'context':context or {}}
   self.store.event('request_dispatched',**common)
   try:
    response=self.transport(payload)
    # Persist before parsing: malformed reviewer output is never redrawn.
    self.store.save(f'private/responses/{physical}.json',response)
   except HTTPFailure as e:
    self.store.event('request_failed',**common,status_code=e.status,charge_status='unknown',latency_seconds=time.monotonic()-start)
    if e.status in (429,500,502,503,504) and attempt<limits['max_retries_per_request']:
     time.sleep(min(limits['retry_backoff_seconds']*(2**attempt),60));continue
    raise RunFailure('provider_error_exhausted') from None
   except UnknownResult:
    self.store.event('request_failed',**common,status='provider_result_unknown',charge_status='unknown',latency_seconds=time.monotonic()-start)
    raise RunFailure('provider_result_unknown') from None
   self.store.event('response_saved',**common,received_response_digest=digest(response),stored_response_digest=digest(self.store.sanitize(response)),usage=usage_fields(response),cost=None,cost_status='unknown',latency_seconds=time.monotonic()-start)
   return parse_response(self.store.sanitize(response))
  raise RunFailure('provider_error_exhausted')

def live_client(config,store):
 # This function is reachable only after explicit CLI --mode live validation.
 m=config['models']
 names=[m[k] for k in ('api_base_url_env','api_key_env','actor_model_env','reviewer_model_env','user_model_env')]
 values=[os.environ.get(name) for name in names]
 if any(not x or x.startswith('REPLACE_') for x in values): raise RunFailure('missing_local_provider_configuration')
 base,key,actor,reviewer,user=values
 store.secrets=(key,)
 return Client(config,store,HTTPTransport(base,key,config['limits']['request_timeout_seconds'],config['limits']['max_response_bytes']),{'actor':actor,'reviewer':reviewer,'user':user})


def usage_fields(response):
 if not isinstance(response,dict) or not isinstance(response.get('usage'),dict): return None
 raw=response['usage'];out={}
 for key in ('prompt_tokens','completion_tokens','total_tokens'):
  if type(raw.get(key)) is int and raw[key]>=0: out[key]=raw[key]
 for group,key in (('prompt_tokens_details','cached_tokens'),('completion_tokens_details','reasoning_tokens')):
  details=raw.get(group)
  if isinstance(details,dict) and type(details.get(key)) is int and details[key]>=0: out[group]={key:details[key]}
 return out or None

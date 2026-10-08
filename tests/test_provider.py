import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from local_experiments.config import DEFAULT
from local_experiments.storage import Store,RunFailure
from local_experiments.provider import Client,HTTPFailure,UnknownResult,HTTPTransport,NoRedirect,parse_response,validate_wire,live_client

RESPONSE={'id':'fake','choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'hello'}}],'usage':{'prompt_tokens':4,'completion_tokens':2}}

class ProviderTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.c=copy.deepcopy(DEFAULT);self.c['limits']['retry_backoff_seconds']=0
  self.store=Store(Path(self.temp.name)/'run',self.c,'dry-run')
 def client(self,transport): return Client(self.c,self.store,transport,{'actor':'fake-model'})
 def test_real_transport_serialization_with_mock_opener(self):
  class Reply:
   def __enter__(self): return self
   def __exit__(self,*args): pass
   def read(self,n): return json.dumps(RESPONSE).encode()
  transport=HTTPTransport('https://provider.example.invalid/v1','VIRTUAL_TEST_CREDENTIAL',1,10000)
  with patch.object(transport.opener,'open',return_value=Reply()) as opener:
   self.assertEqual(self.client(transport).call('actor',[{'role':'user','content':'test'}])['content'],'hello')
   request=opener.call_args.args[0]
   self.assertEqual(request.get_header('Authorization'),'Bearer VIRTUAL_TEST_CREDENTIAL')
   self.assertEqual(json.loads(request.data)['model'],'fake-model')
  for p in self.store.root.rglob('*.json*'): self.assertNotIn('VIRTUAL_TEST_CREDENTIAL',p.read_text())
 def test_redirects_never_forward(self):
  with self.assertRaises(HTTPFailure): NoRedirect().redirect_request(None,None,302,'redirect',{},'https://other.example.invalid')
 def test_https_required(self):
  for url in ('http://example.invalid','https://u:p@example.invalid','https://example.invalid?key=x'):
   with self.assertRaises(RunFailure): HTTPTransport(url,'virtual',1,100)
 def test_retry_counts_every_physical_attempt(self):
  values=[HTTPFailure(429),RESPONSE]
  def transport(payload):
   v=values.pop(0)
   if isinstance(v,Exception): raise v
   return v
  client=self.client(transport);client.call('actor',[{'role':'user','content':'test'}])
  self.assertEqual(client.calls,2)
  events=[json.loads(x) for x in (self.store.root/'journal/events.jsonl').read_text().splitlines()]
  self.assertEqual(len([e for e in events if e['kind']=='request_dispatched']),2)
 def test_uncertain_timeout_not_retried(self):
  calls=[]
  def transport(payload): calls.append(1);raise UnknownResult()
  with self.assertRaisesRegex(RunFailure,'provider_result_unknown'): self.client(transport).call('actor',[{'role':'user','content':'test'}])
  self.assertEqual(len(calls),1)
 def test_invalid_response_persisted_without_redraw(self):
  calls=[]
  def transport(payload): calls.append(1);return {'choices':[]}
  with self.assertRaises(RunFailure): self.client(transport).call('actor',[{'role':'user','content':'test'}])
  self.assertEqual(len(calls),1);self.assertTrue((self.store.root/'private/responses/1.json').is_file())
 def test_budget_checked_before_dispatch(self):
  self.c['limits']['max_physical_requests']=1;client=self.client(lambda p:RESPONSE)
  client.call('actor',[{'role':'user','content':'test'}])
  with self.assertRaisesRegex(RunFailure,'budget_stopped'):client.call('actor',[{'role':'user','content':'test'}])
  self.assertEqual(client.calls,1)
 def test_mismatched_tool_and_truncated_response(self):
  with self.assertRaises(RunFailure): validate_wire([{'role':'tool','tool_call_id':'unknown','content':'data'}])
  r=copy.deepcopy(RESPONSE);r['choices'][0]['finish_reason']='length'
  with self.assertRaises(RunFailure):parse_response(r)
 def test_fake_live_credentials_only_under_explicit_factory(self):
  fake={'MODEL_API_BASE_URL':'https://provider.example.invalid/v1','MODEL_API_KEY':'VIRTUAL_TEST_CREDENTIAL','ACTOR_MODEL':'a','REVIEWER_MODEL':'r','USER_MODEL':'u'}
  with patch('os.environ',fake): client=live_client(self.c,self.store)
  self.assertIsInstance(client.transport,HTTPTransport)
 def test_wrong_json_types_stay_classified(self):
  for response in ([],None,42,{'choices':[None]},{'choices':[{'finish_reason':'stop','message':None}]},{'choices':[{'finish_reason':'tool_calls','message':{'role':'assistant','tool_calls':[None]}}]}):
   with self.subTest(response=response),self.assertRaises(RunFailure):parse_response(response)
 def test_echoed_virtual_key_and_headers_are_redacted(self):
  self.store.secrets=('VIRTUAL_TEST_CREDENTIAL',)
  response=copy.deepcopy(RESPONSE)
  response['choices'][0]['message']['content']='VIRTUAL_TEST_CREDENTIAL'
  response['headers']={'Authorization':'Bearer another-private-value'}
  response['usage']['unexpected']='VIRTUAL_TEST_CREDENTIAL'
  result=self.client(lambda p:response).call('actor',[{'role':'user','content':'test'}])
  self.assertEqual(result['content'],'[REDACTED_CREDENTIAL]')
  for p in self.store.root.rglob('*.json*'):
   text=p.read_text();self.assertNotIn('VIRTUAL_TEST_CREDENTIAL',text);self.assertNotIn('another-private-value',text)

 def test_saved_response_digest_matches_redacted_artifact(self):
  from local_experiments.storage import digest
  self.store.secrets=('VIRTUAL_TEST_CREDENTIAL',)
  response=copy.deepcopy(RESPONSE);response['choices'][0]['message']['content']='VIRTUAL_TEST_CREDENTIAL'
  self.client(lambda p:response).call('actor',[{'role':'user','content':'test'}])
  events=[json.loads(x) for x in (self.store.root/'journal/events.jsonl').read_text().splitlines()]
  stored=json.loads((self.store.root/'private/responses/1.json').read_text())
  self.assertEqual(events[-1]['stored_response_digest'],digest(stored))
  for event in events:
   signature=event.pop('content_hash');self.assertEqual(signature,digest(event))

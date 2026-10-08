import copy
import json
from pathlib import Path
import tempfile
import unittest
from local_experiments.config import DEFAULT
from local_experiments.storage import Store,RunFailure
from local_experiments.provider import Client,UnknownResult,HTTPFailure
from local_experiments.recovery import Recovery,plan
from local_experiments.costs import summarize_costs

REPLY={'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'ok'}}],'usage':{'prompt_tokens':7,'completion_tokens':1}}
MESSAGE=[{'role':'user','content':'hello'}]
class RecoveryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.c=copy.deepcopy(DEFAULT);self.c['limits']['retry_backoff_seconds']=0
 def client(self,name,transport):return Client(self.c,Store(self.root/name,self.c,'dry-run'),transport,{'actor':'fixture'})
 def decisions(self,old,choice=None):
  p=self.root/'decisions.json';plan(old.store.root,p)
  d=json.loads(p.read_text())
  for v in d['unknown_requests'].values():v.update(decision=choice,accept_possible_duplicate_charge=choice=='retry')
  p.write_text(json.dumps(d));return p
 def test_confirmed_response_and_retry_cost_replayed_without_dispatch(self):
  replies=[HTTPFailure(429),REPLY]
  def transport(p):
   v=replies.pop(0)
   if isinstance(v,Exception):raise v
   return v
  old=self.client('old',transport);old.call('actor',MESSAGE)
  new=self.client('new',lambda p:self.fail('confirmed request resent'));new.recovery=Recovery(old.store.root,self.decisions(old),new)
  self.assertEqual(new.call('actor',MESSAGE)['content'],'ok');new.recovery.assert_complete()
  self.assertEqual(new.calls,2)
  report=summarize_costs(new,[{'root_id':'r','arm_id':'C','common_prefix_repeat_id':0,'suffix_repeat_id':0,'logical_request_ids':[1]}])
  self.assertEqual(report['physical_deduplicated']['physical_attempts'],2)
  self.assertEqual(report['logical_paths'][0]['physical_attempts'],2)
  self.assertEqual(report['logical_paths'][0]['reported_input_tokens'],7)
 def test_unknown_requires_decision_then_abandon_no_resend(self):
  def transport(p):raise UnknownResult()
  old=self.client('old',transport)
  with self.assertRaisesRegex(RunFailure,'provider_result_unknown'):old.call('actor',MESSAGE)
  path=self.decisions(old)
  with self.assertRaisesRegex(RunFailure,'explicit_decision'):Recovery(old.store.root,path,self.client('invalid',transport))
  d=json.loads(path.read_text());d['unknown_requests']['1']['decision']='abandon';path.write_text(json.dumps(d))
  new=self.client('new',lambda p:self.fail('unknown request resent'));new.recovery=Recovery(old.store.root,path,new)
  with self.assertRaisesRegex(RunFailure,'provider_result_unknown'):new.call('actor',MESSAGE)
  self.assertEqual(new.calls,1)
 def test_explicit_retry_counts_possible_duplicate_attempt(self):
  def transport(p):raise UnknownResult()
  old=self.client('old',transport)
  with self.assertRaises(RunFailure):old.call('actor',MESSAGE)
  new=self.client('new',lambda p:REPLY);new.recovery=Recovery(old.store.root,self.decisions(old,'retry'),new)
  self.assertEqual(new.call('actor',MESSAGE)['content'],'ok');self.assertEqual(new.calls,2)
  self.assertEqual(len(new.records),2)
 def test_recovery_cannot_reset_physical_budget(self):
  self.c['limits']['max_physical_requests']=1
  old=self.client('old',lambda p:REPLY);old.call('actor',MESSAGE)
  new=self.client('new',lambda p:self.fail('budget reset'));new.recovery=Recovery(old.store.root,self.decisions(old),new)
  new.call('actor',MESSAGE)
  with self.assertRaisesRegex(RunFailure,'budget_stopped'):new.call('actor',MESSAGE)
 def test_recovery_preserves_reported_model_check(self):
  self.c['models']['require_reported_model']=True
  old=self.client('old',lambda p:{**REPLY,'model':'wrong'})
  with self.assertRaisesRegex(RunFailure,'identity_mismatch'):old.call('actor',MESSAGE)
  new=self.client('new',lambda p:self.fail('request resent'));new.recovery=Recovery(old.store.root,self.decisions(old),new)
  with self.assertRaisesRegex(RunFailure,'identity_mismatch'):new.call('actor',MESSAGE)
 def test_payload_change_fails_closed(self):
  old=self.client('old',lambda p:REPLY);old.call('actor',MESSAGE)
  new=self.client('new',lambda p:self.fail('diverged request sent'));new.recovery=Recovery(old.store.root,self.decisions(old),new)
  with self.assertRaisesRegex(RunFailure,'request_diverged'):new.call('actor',[{'role':'user','content':'different'}])

 def test_unknown_retry_cannot_expand_logical_attempt_limit(self):
  replies=[HTTPFailure(429),HTTPFailure(429),UnknownResult()]
  def transport(p):raise replies.pop(0)
  old=self.client('old',transport)
  with self.assertRaisesRegex(RunFailure,'provider_result_unknown'):old.call('actor',MESSAGE)
  new=self.client('new',lambda p:self.fail('per-logical retry limit reset'));new.recovery=Recovery(old.store.root,self.decisions(old,'retry'),new)
  with self.assertRaisesRegex(RunFailure,'provider_error_exhausted'):new.call('actor',MESSAGE)
  self.assertEqual(new.calls,3)
 def test_wall_budget_includes_pause_between_processes(self):
  old=self.client('old',lambda p:REPLY);old.call('actor',MESSAGE)
  path=old.store.root/'run_manifest.json';m=json.loads(path.read_text());m['budget_origin_ns']-=int(2000e9);path.write_text(json.dumps(m))
  new=self.client('new',lambda p:self.fail('wall budget reset'));new.recovery=Recovery(old.store.root,self.decisions(old),new)
  new.call('actor',MESSAGE)
  with self.assertRaisesRegex(RunFailure,'budget_stopped'):new.call('actor',MESSAGE)

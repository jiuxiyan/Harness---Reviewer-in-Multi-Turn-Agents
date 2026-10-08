"""Guarded official-environment integration checks, run in a clean child process."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'code_inputs/reviewer_pilot'))
import no_api_guard as guard
sys.path.insert(0,str(ROOT/'code_inputs/reviewer_pilot/upstream/src'))
from loguru import logger
logger.remove()
from local_experiments import engine as e
from local_experiments.config import DEFAULT
from local_experiments.storage import Store,RunFailure,write_json
from local_experiments.provider import Client
from local_experiments.mock import MockTransport
from tau2.domains.telecom.environment import get_tasks

def setup_run(directory):
 c=copy.deepcopy(DEFAULT);store=Store(Path(directory)/'run',c,'dry-run')
 client=Client(c,store,MockTransport(),{r:'mock-'+r for r in ('actor','user','reviewer')})
 meta=json.loads((ROOT/c['dataset']['manifest']).read_text())['tasks'][0]
 task=next(t for t in get_tasks('base') if t.id==meta['task_id'])
 o=e.make(task,client,c)
 while not o.done and not e.trigger(o):o.step();o._check_termination()
 assert e.trigger(o)
 return c,store,client,task,o

class EngineChecks(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.c,self.store,self.client,self.task,self.o=setup_run(self.temp.name)
 def draw(self): return e.capture(self.o,self.client)
 def test_common_first_and_later_status_only(self):
  draw=self.draw();e.execute(self.o,draw,'P')
  wire=e.to_litellm_messages(self.o.agent_state.system_messages+self.o.agent_state.messages+[self.o.message]);record=self.o.agent.record
  first=[e.project(wire,record,a,0) for a in ('P','R','C')];self.assertEqual(first[0],first[1]);self.assertEqual(first[1],first[2])
  p=e.project(wire,record,'P',1);c=e.project(wire,record,'C',1)
  self.assertEqual(json.dumps(p).replace(e.HEADERS['neutral'],e.HEADERS['consumed']),json.dumps(c))
  r=e.project(wire,record,'R',1);event=json.loads(next(m['content'][len(e.RECEIPT_PREFIX):] for m in r if (m.get('content') or '').startswith(e.RECEIPT_PREFIX)))
  self.assertEqual(event['extra_packet'],'');self.assertIn('execution_receipt',event);self.assertNotIn('advice_lifetime_header',event)
  p0=e.project(wire,record,'P0',1);self.assertNotIn('advice_lifetime_header',json.dumps(p0))
 def test_failed_result_never_closes(self):
  draw=self.draw();draw['selected_action']['arguments']={'id':'unknown-id'}
  e.execute(self.o,draw,'C');self.assertFalse(self.o.agent.record['closable'])
 def test_failed_generation_does_not_consume_exposure(self):
  draw=self.draw();e.execute(self.o,draw,'R')
  before=self.o.agent.valid;self.client.transport=lambda p:{'choices':[]}
  with self.assertRaises(RunFailure):self.o.step()
  self.assertEqual(self.o.agent.valid,before)
 def test_draw_fallback_and_unchanged_and_scope(self):
  original=copy.deepcopy(self.client.transport)
  cases=[('not json','invalid'),(json.dumps({'selected_action':{'name':'unknown','arguments':{}},'packet':'advice','declaration':{'target_action_id':'x','scope':'action_local','instruction':'execute_target_call','close_condition':'normal_tool_return'}}),'out_of_scope')]
  saved=e.snapshot(self.o)
  for text,expected in cases:
   self.o=e.restore(saved,self.task,self.client,self.c)
   self.client.transport=lambda p,text=text:{'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':text}}]}
   q=e.capture(self.o,self.client);self.assertEqual(q['classification'],expected);self.assertEqual(q['selected_action'],e.action(self.o.message));self.assertEqual(q['resamples'],0)
 def test_redraw_rejected(self):
  self.draw()
  saved=e.snapshot(self.o);self.o=e.restore(saved,self.task,self.client,self.c)
  with self.assertRaisesRegex(RunFailure,'redraw_forbidden'): self.draw()
 def test_production_fork_cannot_redraw_or_reexecute(self):
  root=e.snapshot(self.o);draw=self.draw()
  shared=e.restore(root,self.task,self.client,self.c);e.execute(shared,draw,'P')
  saved=e.snapshot(shared);restored=e.restore(saved,self.task,self.client,self.c)
  self.assertTrue(restored.agent.draw_consumed)
  with self.assertRaisesRegex(RunFailure,'redraw_forbidden'):e.capture(restored,self.client)
  with self.assertRaisesRegex(RunFailure,'slot_already_used'):e.execute(restored,draw,'P')
 def test_private_canary_cannot_change_request(self):
  captured=[];old=self.client.transport
  def transport(payload):captured.append(copy.deepcopy(payload));return old(payload)
  self.client.transport=transport
  other=copy.deepcopy(self.o)
  self.draw()
  other.task.evaluation_criteria.env_assertions[0].message='PRIVATE_EVALUATOR_CANARY'
  other.task.evaluation_criteria.env_assertions[0].arguments['expected_status']=False
  e.capture(other,self.client)
  self.assertEqual(captured[0],captured[1])
  self.assertNotIn('PRIVATE_EVALUATOR_CANARY',json.dumps(captured))
 def test_restore_rejects_corruption_and_keeps_native_counters(self):
  saved=e.snapshot(self.o);restored=e.restore(saved,self.task,self.client,self.c)
  self.assertEqual(restored.step_count,self.o.step_count);self.assertEqual(e.env_state(restored.environment),e.env_state(self.o.environment))
  saved['payload']['step_count']+=1
  with self.assertRaisesRegex(RunFailure,'restore_mismatch'):e.restore(saved,self.task,self.client,self.c)
 def test_shared_segment_fork_and_official_finalization(self):
  q=self.draw();e.execute(self.o,q,'P');trace=[];e.advance(self.o,trace,self.task,True)
  saved=e.snapshot(self.o);self.assertEqual(saved['payload']['valid'],1)
  a=e.restore(saved,self.task,self.client,self.c);b=e.restore(saved,self.task,self.client,self.c)
  a.agent.arm='P';b.agent.arm='C';future=e.advance(a,list(trace),self.task)
  self.assertFalse(b.done);self.assertNotEqual(a.step_count,b.step_count)
  result=e.outcome(a,self.task,[0],future);self.assertEqual(result['completion'],1)
  self.assertEqual(result['loss'],0)
 def test_terminal_common_block_is_not_padded_after_later_failure(self):
  self.c['sampling']['common_prefix_repeats']=2
  self.c['sampling']['suffix_repeats']=2
  actual=e.advance;common_calls=[]
  def advance(o,trace,task,one_segment=False):
   if one_segment:
    common_calls.append(1)
    if len(common_calls)==2: raise RunFailure('provider_error_exhausted')
    return actual(o,trace,task,False)
   return actual(o,trace,task,one_segment)
  with patch.object(e,'advance',side_effect=advance): rows=e.run(self.c,self.store,self.client)
  terminal=[r for r in rows if r['common_prefix_repeat_id']==0]
  missing=[r for r in rows if r['common_prefix_repeat_id']==1]
  self.assertEqual(len(terminal),3);self.assertTrue(all(r['common_terminal'] for r in terminal))
  self.assertEqual(len(missing),6);self.assertTrue(all(r['loss'] is None for r in missing))
 def test_native_max_steps_remains_observed_failure(self):
  q=self.draw();e.execute(self.o,q,'P');self.o.max_steps=self.o.step_count+1
  trace=e.advance(self.o,[],self.task)
  self.assertEqual(e.outcome(self.o,self.task,[0],trace)['completion'],0)

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1] in ('save','restore'):
  phase,path=sys.argv[1:];path=Path(path)
  with tempfile.TemporaryDirectory() as tmp:
   c,s,client,task,o=setup_run(tmp)
   if phase=='save':
    q=e.capture(o,client);e.execute(o,q,'P');e.advance(o,[],task,True);write_json(path,e.snapshot(o))
   else:
    saved=json.loads(path.read_text());o=e.restore(saved,task,client,c)
    assert o.agent.valid==1
    assert e.env_state(o.environment)==saved['payload']['environment']
    result=e.outcome(o,task,[0],e.advance(o,[],task));assert result['completion']==1
  print('fresh-process '+phase+' passed')
 else: unittest.main()

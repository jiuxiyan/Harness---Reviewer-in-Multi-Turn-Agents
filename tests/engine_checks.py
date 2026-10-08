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

def setup_run(directory,index=0,scenario="read"):
 c=copy.deepcopy(DEFAULT);c['review']['fixture_scenario']=scenario;store=Store(Path(directory)/'run',c,'dry-run')
 client=Client(c,store,MockTransport(scenario),{r:'mock-'+r for r in ('actor','user','reviewer','self')})
 meta=json.loads((ROOT/c['dataset']['manifest']).read_text())['tasks'][index]
 task=next(t for t in get_tasks(None) if t.id==meta['task_id'])
 o=e.make(task,client,c)
 while not o.done and not e.trigger(o):o.step();o._check_termination()
 assert e.trigger(o)
 return c,store,client,task,o

def history_task(task):
 task=task.model_copy(deep=True);task.initial_state.initialization_data=None;task.initial_state.initialization_actions=[]
 call=e.ToolCall(id='authored-history-toggle',requestor='user',name='toggle_airplane_mode',arguments={})
 env=e.get_environment();response=env.get_response(call);response.timestamp=None
 task.initial_state.message_history=[e.UserMessage(role='user',tool_calls=[call],timestamp=None),response]
 return task

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

 def test_received_truncated_reviewer_is_one_fallback_draw(self):
  before=self.client.calls
  self.client.transport=lambda p:{'choices':[{'finish_reason':'length','message':{'role':'assistant','content':'{"selected_action":'}}]}
  q=self.draw();self.assertEqual(self.client.calls,before+1)
  self.assertEqual(q['classification'],'invalid');self.assertEqual(q['packet'],'')
  self.assertEqual(q['selected_action'],e.action(self.o.message));e.execute(self.o,q,'C')
  self.assertEqual(self.o.agent.record['packet'],'')
 def test_mixed_received_actor_is_native_failure(self):
  q=self.draw();e.execute(self.o,q,'P')
  self.client.transport=lambda p:{'choices':[{'finish_reason':'tool_calls','message':{'role':'assistant','content':'I will check','tool_calls':[{'id':'mixed','type':'function','function':{'name':'get_data_usage','arguments':'{"customer_id":"C1001","line_id":"L1002"}'}}]}}]}
  trace=e.advance(self.o,[],self.task)
  result=e.outcome(self.o,self.task,[],trace)
  self.assertEqual(self.o.termination_reason,e.TerminationReason.AGENT_ERROR)
  self.assertEqual(result['completion'],0);self.assertEqual(self.o.agent.valid,0)
 def test_truncated_actor_is_native_failure(self):
  q=self.draw();e.execute(self.o,q,'P')
  self.client.transport=lambda p:{'choices':[{'finish_reason':'length','message':{'role':'assistant','content':'incomplete'}}]}
  e.advance(self.o,[],self.task)
  self.assertEqual(self.o.termination_reason,e.TerminationReason.AGENT_ERROR)
 def test_nonidempotent_official_initialization_restored_once(self):
  task=next(t for t in get_tasks(None) if t.id=='[service_issue]overdue_bill_suspension[PERSONA:Easy]')
  self.assertIsNone(task.initial_state.initialization_data)
  o=e.make(task,self.client,self.c);saved=e.snapshot(o)
  restored=e.restore(saved,task,self.client,self.c)
  self.assertEqual(e.env_state(o.environment),e.env_state(restored.environment))
 def test_roaming_write_repairs_real_state_and_restores(self):
  with tempfile.TemporaryDirectory() as directory:
   c,store,client,task,o=setup_run(directory,4,'roaming')
   initial=e.env_state(o.environment);before=e.vector(o.environment,task)
   q=e.capture(o,client);self.assertEqual(q['selected_action']['name'],'enable_roaming')
   e.execute(o,q,'C');after=e.vector(o.environment,task)
   self.assertNotEqual(initial,e.env_state(o.environment));self.assertTrue(o.agent.record['state_change_observed'])
   self.assertTrue(o.agent.record['closable']);self.assertTrue(any(not a and b for a,b in zip(before,after)))
   saved=e.snapshot(o);restored=e.restore(saved,task,client,c)
   self.assertEqual(e.env_state(restored.environment),e.env_state(o.environment))
   result=e.outcome(restored,task,[],e.advance(restored,[],task))
   self.assertEqual(result['completion'],1)
 def test_roaming_ongoing_and_error_do_not_close(self):
  with tempfile.TemporaryDirectory() as directory:
   c,store,client,task,o=setup_run(directory,4,'roaming');saved=e.snapshot(o)
   q=e.capture(o,client);q['declaration']['scope']='ongoing';e.execute(o,q,'C')
   self.assertTrue(o.agent.record['state_change_observed']);self.assertFalse(o.agent.record['closable'])
   o=e.restore(saved,task,client,c);q['declaration']['scope']='action_local';q['selected_action']['arguments']['line_id']='missing-line'
   e.execute(o,q,'C');self.assertTrue(o.agent.record['receipt']['result']['error']);self.assertFalse(o.agent.record['closable'])
 def test_s_reconsiders_once_without_extra_packet(self):
  self.client.models['self']='mock-actor'
  q=e.capture(self.o,self.client,True);e.execute(self.o,q,'S')
  self.assertEqual(self.o.agent.record['packet'],'')
  self.assertEqual(self.client.records[-1]['role'],'self')

 def test_actor_and_user_received_invalid_endpoints(self):
  cases=[{'finish_reason':'stop','message':{'role':'assistant','content':''}},
         {'finish_reason':'stop','message':{'role':'assistant','refusal':'no'}},
         {'finish_reason':'length','message':{'role':'assistant','content':'truncated'}},
         {'finish_reason':'tool_calls','message':{'role':'assistant','tool_calls':[{'id':'bad','type':'function','function':{'name':'get_data_usage','arguments':'{'}}]}}]
  for role in ('actor','user'):
   for choice in cases:
    o=e.restore(e.snapshot(self.o),self.task,self.client,self.c)
    # Route to the requested native participant using the existing public message.
    if role=='actor':o.step()
    else:o.from_role=e.Role.AGENT;o.to_role=e.Role.USER;o.message=e.AssistantMessage(role='assistant',content='Please continue.',timestamp=e.get_now())
    self.client.transport=lambda p,choice=choice:{'choices':[choice]}
    o.step();self.assertTrue(o.done)
    self.assertEqual(o.termination_reason,e.TerminationReason.AGENT_ERROR if role=='actor' else e.TerminationReason.USER_ERROR)
    self.assertEqual(e.outcome(o,self.task,[],[])['completion'],0)
 def test_completed_run_recovery_replays_without_model_dispatch(self):
  from local_experiments.recovery import Recovery,plan
  with tempfile.TemporaryDirectory() as directory:
   c=copy.deepcopy(DEFAULT);old=Store(Path(directory)/'old',c,'dry-run')
   client=Client(c,old,MockTransport(),{r:'mock-'+r for r in ('actor','user','reviewer','self')})
   before=e.run(c,old,client);decisions=Path(directory)/'decisions.json';plan(old.root,decisions)
   new=Store(Path(directory)/'new',c,'dry-run')
   recovered=Client(c,new,lambda p:self.fail('durable response resent'),client.models)
   recovered.recovery=Recovery(old.root,decisions,recovered)
   after=e.run(c,new,recovered)
   self.assertEqual(before,after);self.assertEqual(client.calls,recovered.calls)

 def test_nonidempotent_initial_message_history_once(self):
  task=history_task(self.task);o=e.make(task,self.client,self.c);saved=e.snapshot(o)
  restored=e.restore(saved,task,self.client,self.c)
  self.assertEqual(e.env_state(restored.environment),e.env_state(o.environment))

 def test_public_normal_write_close_is_not_oracle_success(self):
  with tempfile.TemporaryDirectory() as directory:
   c,store,client,task,o=setup_run(directory,4,'roaming')
   # Add a completed official enable call to public history, then propose a READ.
   q=e.capture(o,client);e.execute(o,q,'P');e.advance(o,[],task,True)
   o.agent.draw_consumed=False;o.agent.intervention_executed=False
   # This is an authored negative-control root, not a natural sampled draw.
   while not o.done and not (o.from_role==e.Role.AGENT and o.to_role==e.Role.ENV):o.step();o._check_termination()
   before=e.vector(o.environment,task)
   q={'selected_action':{'name':'disable_roaming','arguments':{'customer_id':'C1001','line_id':'L1002'}},'packet':'Execute target call.',
      'declaration':{'target_action_id':e.target_id(o.message,{}),'scope':'action_local','instruction':'execute_target_call','close_condition':'normal_tool_return'}}
   e.execute(o,q,'C');after=e.vector(o.environment,task)
   self.assertTrue(o.agent.record['closable']);self.assertTrue(any(a and not b for a,b in zip(before,after)))

 def test_interrupted_reviewer_requires_explicit_retry_and_keeps_prefix(self):
  from local_experiments.recovery import Recovery,plan
  with tempfile.TemporaryDirectory() as directory:
   c=copy.deepcopy(DEFAULT);old=Store(Path(directory)/'old',c,'dry-run');mock=MockTransport()
   def interrupted(payload):
    if payload['model']=='mock-reviewer':raise KeyboardInterrupt()
    return mock(payload)
   client=Client(c,old,interrupted,{r:'mock-'+r for r in ('actor','user','reviewer','self')})
   with self.assertRaises(KeyboardInterrupt):e.run(c,old,client)
   decisions=Path(directory)/'decisions.json';plan(old.root,decisions)
   decision=json.loads(decisions.read_text());self.assertEqual(len(decision['unknown_requests']),1)
   for value in decision['unknown_requests'].values():value.update(decision='retry',accept_possible_duplicate_charge=True)
   decisions.write_text(json.dumps(decision))
   new=Store(Path(directory)/'new',c,'dry-run');calls=[]
   def transport(payload):calls.append(payload['model']);return mock(payload)
   recovered=Client(c,new,transport,client.models);recovered.recovery=Recovery(old.root,decisions,recovered)
   rows=e.run(c,new,recovered)
   self.assertEqual(calls[0],'mock-reviewer');self.assertEqual(calls.count('mock-reviewer'),1)
   self.assertEqual(len(rows),3);self.assertTrue(all(r['completion']==1 for r in rows))

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1] in ('save','restore','save-write','restore-write','save-init','restore-init','save-history','restore-history'):
  phase,path=sys.argv[1:];path=Path(path)
  with tempfile.TemporaryDirectory() as tmp:
   c,s,client,task,o=setup_run(tmp,4 if 'write' in phase else 0,'roaming' if 'write' in phase else 'read')
   if 'history' in phase:
    task=history_task(task);o=e.make(task,client,c)
    if phase.startswith('save'):write_json(path,e.snapshot(o))
    else:
     saved=json.loads(path.read_text());o=e.restore(saved,task,client,c);assert e.env_state(o.environment)==saved['payload']['environment']
    print('fresh-process nonidempotent history replayed once');raise SystemExit(0)
   if 'init' in phase:
    task=next(t for t in get_tasks(None) if t.id=='[service_issue]overdue_bill_suspension[PERSONA:Easy]');o=e.make(task,client,c)
    if phase.startswith('save'):write_json(path,e.snapshot(o))
    else:
     saved=json.loads(path.read_text());o=e.restore(saved,task,client,c);assert e.env_state(o.environment)==saved['payload']['environment']
    print('fresh-process initialization restored once');raise SystemExit(0)
   if phase.startswith('save'):
    q=e.capture(o,client);e.execute(o,q,'P');e.advance(o,[],task,True);write_json(path,e.snapshot(o))
   else:
    saved=json.loads(path.read_text());o=e.restore(saved,task,client,c)
    assert o.agent.valid==1
    assert e.env_state(o.environment)==saved['payload']['environment']
    result=e.outcome(o,task,[0],e.advance(o,[],task));assert result['completion']==1
  print('fresh-process '+phase+' passed')
 else: unittest.main()

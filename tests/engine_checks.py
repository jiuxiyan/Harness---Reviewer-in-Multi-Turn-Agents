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

def vpn_task():
 return next(t for t in get_tasks(None) if t.id=='[mobile_data_issue]bad_vpn[PERSONA:None]')

def finish_vpn(o,client):
 # Authored user policy: disconnect the broken VPN, then stop. No model/API.
 responses=[{'choices':[{'finish_reason':'tool_calls','message':{'role':'assistant','tool_calls':[{'id':'fixture-vpn-disconnect','type':'function','function':{'name':'disconnect_vpn','arguments':'{}'}}]}}]},
            {'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'###STOP###'}}]}]
 with patch.object(client,'transport',side_effect=lambda payload:responses.pop(0)):
  return e.advance(o,[],o.task)

REFUEL_TASK='[mobile_data_issue]airplane_mode_on|data_usage_exceeded[PERSONA:Easy]'
REFUEL_SCOPE=['enable_roaming','disable_roaming','refuel_data']
REFUEL_GOAL=2 # index of assert_data_refueling_amount in this task's env_assertions

def _reply(content=None,calls=None):
 return {'choices':[{'finish_reason':'tool_calls' if calls else 'stop',
   'message':{'role':'assistant','content':content,'tool_calls':calls or []}}]}

def _call(name,args,tag):
 return [{'id':'fixture-'+tag,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]

def refuel_config():
 c=copy.deepcopy(DEFAULT);c['review']['allowed_writes']=list(REFUEL_SCOPE)
 c['dataset']['manifest']='docs/planning/manifests/tasks_development_refuel.json';c['dataset']['task_indices']=[0]
 c['sampling']['max_roots_per_trajectory']=2
 return c

def refuel_task():
 return next(t for t in get_tasks(None) if t.id==REFUEL_TASK)

def refuel_script():
 # Authored deterministic episode: two READs, the official refuel, then a verification READ.
 # No model or API call is made; this is a fixture, never evidence about model behaviour.
 actor=[_reply(calls=_call('get_customer_by_phone',{'phone_number':'555-123-2002'},'read1')),
        _reply(calls=_call('get_data_usage',{'customer_id':'C1001','line_id':'L1002'},'read2')),
        _reply(calls=_call('refuel_data',{'customer_id':'C1001','line_id':'L1002','gb_amount':2.0},'refuel')),
        _reply(calls=_call('get_details_by_id',{'id':'L1002'},'read3')),
        _reply(content='The data refuel is complete.')]
 user=[_reply(content='My mobile data is not working and I want excellent speed. I am John Smith, phone 555-123-2002.'),
       _reply(calls=[{'id':'fixture-toggle','type':'function','function':{'name':'toggle_airplane_mode','arguments':'{}'}}]),
       _reply(content='Airplane mode is off now; please continue.'),
       _reply(content='###STOP###')]
 return actor,user

def refuel_run(directory,reviewer=None):
 c=refuel_config();store=Store(Path(directory)/'run',c,'dry-run');actor,user=refuel_script()
 state={'actor':actor,'user':user,'reviewer':list(reviewer or []),'self':[]}
 def transport(payload):
  role=payload['model'].split('-',1)[1]
  if not state[role]: raise AssertionError('authored fixture exhausted for role '+role)
  return state[role].pop(0)
 client=Client(c,store,transport,{r:'mock-'+r for r in ('actor','user','reviewer','self')})
 return c,store,client,refuel_task(),e.make(refuel_task(),client,c)

def refuel_roots(o,task,want=2,limit=40):
 """Public trigger points of the authored episode, stopping like max_roots_per_trajectory."""
 trace=[e.vector(o.environment,task)];roots=[]
 for step in range(limit):
  if o.done: break
  if e.trigger(o):
   roots.append({'step':step,'pending':e.pending_supported_call(o),'depth':e.depth(o),
                 'vector':list(trace[-1]),'protected':[i for i,x in enumerate(trace[-1]) if x and not trace[0][i]]})
   if len(roots)>=want: break # leave the orchestrator parked on the pending root call
  o.step();o._check_termination();trace.append(e.vector(o.environment,task))
 return roots,trace

def refuel_draw(o,gb_amount=2.0,line_id='L1002',scope='action_local'):
 return {'selected_action':{'name':'refuel_data','arguments':{'customer_id':'C1001','line_id':line_id,'gb_amount':gb_amount}},
         'packet':'Refuel exactly the requested amount for this line.','raw_q':'fixture','raw_q_digest':'fixture',
         'classification':'valid_changed','semantic_audit':'not_audited','resamples':0,'logical_request_ids':[],
         'declaration':{'target_action_id':e.target_id(o.message,{}),'scope':scope,
                        'instruction':'execute_target_call','close_condition':'normal_tool_return'}}

def refuel_tail(client):
  # Authored continuation from the protected root to USER_STOP, so official evaluation runs on a
  # settled episode. Replaces the fixture transport; still no model or API call.
  state={'actor':[ _reply(content='I have added 2 GB of data to the line.'),_reply(content='All set now.')],
         'user':[_reply(calls=[{'id':'fixture-speed','type':'function','function':{'name':'run_speed_test','arguments':'{}'}}]),
                 _reply(content='###STOP###')]}
  def transport(payload):
   role=payload['model'].split('-',1)[1]
   return state[role].pop(0) if state.get(role) else _reply(content='###STOP###')
  client.transport=transport

class EngineChecks(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.c,self.store,self.client,self.task,self.o=setup_run(self.temp.name)
 def draw(self): return e.capture(self.o,self.client)
 def _episode_config(self,scenario='read',**over):
  c=copy.deepcopy(DEFAULT)
  c['protocol_id']='advice-lifetimes-local-v4';c['stage']='end-to-end';c['arms']=['B','R','P','C']
  c['review']['fixture_scenario']=scenario
  c['dataset']={**DEFAULT['dataset'],'manifest':'docs/planning/manifests/tasks_readiness.json',
                'population':'exposed_development_only','task_indices':[0]}
  for k,v in over.items():
   if k in c['review']:c['review'][k]=v
   elif k in c['sampling']:c['sampling'][k]=v
   else:c[k]=v
  return c
 def _run_episode(self,c,name,scenario='read'):
  store=Store(Path(self.temp.name)/name,c,'dry-run')
  client=Client(c,store,MockTransport(scenario),{r:'mock-'+r for r in ('actor','user','reviewer','self')})
  res=e.run_episode(c,store,client)
  events=[json.loads(l) for l in (store.root/'journal/events.jsonl').read_text().splitlines()]
  return res,store,client,events
 def test_episode_runner_scores_every_arm_after_trigger(self):
  res,store,client,events=self._run_episode(self._episode_config(),'ep-trigger')
  cov=res['coverage']
  self.assertEqual(cov['episodes'],4);self.assertEqual(cov['triggered'],4)
  self.assertEqual(cov['no_trigger'],0);self.assertEqual(cov['episode_failures'],0)
  byarm=res['summary']['arms']
  for arm in ('B','R','P','C'):
   self.assertEqual(byarm[arm]['episodes'],1);self.assertEqual(byarm[arm]['scored'],1)
   self.assertIsNotNone(byarm[arm]['J'])
  # B is a receipt-only control: it never invokes the reviewer; P/R/C each capture exactly one draw.
  self.assertEqual(len([x for x in events if x['kind']=='draw_captured']),3)
  self.assertIsInstance(res['summary']['dJ_C_minus_P'],float)
 def test_episode_no_trigger_still_enters_denominator(self):
  res,store,client,events=self._run_episode(self._episode_config(min_completed_assistant_tools=1000),'ep-notrigger')
  cov=res['coverage']
  self.assertEqual(cov['episodes'],4);self.assertEqual(cov['no_trigger'],4);self.assertEqual(cov['triggered'],0)
  self.assertEqual(len([x for x in events if x['kind']=='draw_captured']),0)
  byarm=res['summary']['arms']
  for arm in ('B','R','P','C'):
   self.assertEqual(byarm[arm]['episodes'],1);self.assertEqual(byarm[arm]['scored'],1)
   self.assertIsNotNone(byarm[arm]['J']) # completion scored even with no intervention
 def test_episode_uses_a_single_review_slot_per_episode(self):
  c=self._episode_config();c['sampling']['starts_per_task']=2
  res,store,client,events=self._run_episode(c,'ep-slots')
  cov=res['coverage'];trig=[x for x in events if x['kind']=='episode_trigger']
  self.assertEqual(cov['episodes'],8);self.assertEqual(len(trig),cov['triggered'])
  self.assertEqual(len({x['episode_id'] for x in trig}),len(trig)) # at most one trigger per episode
  draws=[x for x in events if x['kind']=='draw_captured']
  self.assertEqual(len(draws),sum(1 for x in trig if x['arm'] in ('P','R','C')))
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
 def test_fork_restore_trims_pending_user_tool_call(self):
  # A shared-segment fork can be snapshotted at a user->env boundary: the user simulator
  # proposed a mutating tool call whose ToolMessage is not yet recorded. restore() must drop
  # that trailing pending proposal from replay just as it does for an agent->env root, or tau2
  # set_state hits the dangling tool call and the whole fork is lost as restore_mismatch.
  root=e.snapshot(self.o)
  o=e.restore(root,self.task,self.client,self.c)
  self.assertEqual((o.from_role.value,o.to_role.value),('agent','env'))
  call=e.ToolCall(id='pending-user-toggle',requestor='user',name='toggle_airplane_mode',arguments={})
  o.message=e.UserMessage(role='user',tool_calls=[call],timestamp=None)
  o.trajectory[-1]=o.message;o.from_role=e.Role('user');o.to_role=e.Role('env')
  fork=e.snapshot(o)
  self.assertEqual((fork['payload']['routing']['from'],fork['payload']['routing']['to']),('user','env'))
  restored=e.restore(fork,self.task,self.client,self.c)
  self.assertEqual(e.env_state(restored.environment),fork['payload']['environment'])
  self.assertEqual((restored.from_role.value,restored.to_role.value),('user','env'))
  self.assertEqual(restored.message.tool_calls[0].name,'toggle_airplane_mode')
  self.assertEqual(len(restored.trajectory),len(fork['payload']['history']))
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
 def test_refuel_write_scope_reaches_a_nonempty_protection_set(self):
  # The whole point of the refuel WRITE: an assistant-side goal is acquired mid-episode, so a
  # later structural root carries protected goals instead of the vacuous empty set.
  with tempfile.TemporaryDirectory() as directory:
   c,store,client,task,o=refuel_run(directory)
   self.assertIn('refuel_data',o.agent.allowed_names)
   roots,trace=refuel_roots(o,task)
   self.assertEqual([r['pending'] for r in roots],['refuel_data','get_details_by_id'])
   self.assertEqual(roots[0]['protected'],[])
   self.assertEqual(roots[1]['protected'],[REFUEL_GOAL])
   self.assertTrue(roots[1]['vector'][REFUEL_GOAL]);self.assertFalse(trace[0][REFUEL_GOAL])
   self.assertGreaterEqual(roots[1]['depth'][0],c['review']['min_completed_assistant_tools'])
 def test_refuel_goal_is_regressible_so_loss_is_not_degenerate(self):
  with tempfile.TemporaryDirectory() as directory:
   c,store,client,task,o=refuel_run(directory)
   roots,_=refuel_roots(o,task);self.assertEqual(roots[-1]['protected'],[REFUEL_GOAL])
   saved=e.snapshot(o);protected=roots[-1]['protected']
   e.execute(o,refuel_draw(o),'P') # a second refuel overshoots the exact expected amount
   lost=e.vector(o.environment,task)
   self.assertEqual(lost[REFUEL_GOAL],False)
   self.assertEqual(int(any(not lost[i] for i in protected)),1)
   o=e.restore(saved,task,client,c)
   self.assertEqual(e.vector(o.environment,task)[REFUEL_GOAL],True)
 def test_refuel_receipt_identity_error_and_ongoing_scope(self):
  with tempfile.TemporaryDirectory() as directory:
   c,store,client,task,o=refuel_run(directory)
   while not o.done and not e.trigger(o): o.step();o._check_termination()
   before=e.env_state(o.environment);saved=e.snapshot(o)
   q=refuel_draw(o);call_id=e.target_id(o.message,q['selected_action'])
   e.execute(o,q,'C');record=o.agent.record
   self.assertEqual(record['call_id'],call_id);self.assertEqual(record['receipt']['result']['error'],False)
   self.assertTrue(record['state_change_observed']);self.assertNotEqual(before,e.env_state(o.environment))
   self.assertTrue(record['closable']);self.assertEqual(record['receipt']['selected_action'],q['selected_action'])
   self.assertEqual(e.vector(o.environment,task)[REFUEL_GOAL],True)
   o=e.restore(saved,task,client,c);q['declaration']['scope']='ongoing';e.execute(o,q,'C')
   self.assertFalse(o.agent.record['closable'])
   o=e.restore(saved,task,client,c);q=refuel_draw(o,line_id='missing-line')
   e.execute(o,q,'C')
   self.assertTrue(o.agent.record['receipt']['result']['error']);self.assertFalse(o.agent.record['closable'])
   self.assertEqual(e.env_state(o.environment),before)
 def test_refuel_intervention_slot_is_single_use(self):
  with tempfile.TemporaryDirectory() as directory:
   c,store,client,task,o=refuel_run(directory)
   while not o.done and not e.trigger(o): o.step();o._check_termination()
   q=refuel_draw(o);e.execute(o,q,'C')
   amount=o.environment.tools.db.lines[1].data_refueling_gb
   with self.assertRaises(RunFailure): e.execute(o,q,'C')
   with self.assertRaises(RunFailure): e.capture(o,client)
   self.assertEqual(o.environment.tools.db.lines[1].data_refueling_gb,amount)
 def test_refuel_state_is_isolated_across_task_instances(self):
  with tempfile.TemporaryDirectory() as directory:
   c,store,client,task,o=refuel_run(directory)
   other=e.make(refuel_task(),client,c)
   while not o.done and not e.trigger(o): o.step();o._check_termination()
   other_amount=other.environment.tools.db.lines[1].data_refueling_gb
   e.execute(o,refuel_draw(o),'C')
   self.assertEqual(other.environment.tools.db.lines[1].data_refueling_gb,other_amount)
   self.assertEqual(e.vector(other.environment,task)[REFUEL_GOAL],False)
   self.assertNotEqual(e.env_state(o.environment),e.env_state(other.environment))
 def test_s_reconsiders_once_without_extra_packet(self):
  self.client.models['self']='mock-actor'
  q=e.capture(self.o,self.client,True);e.execute(self.o,q,'S')
  self.assertEqual(self.o.agent.record['packet'],'')
  self.assertEqual(self.client.records[-1]['role'],'self')

 def test_public_trigger_depth_is_structural_and_configurable(self):
  # Roots must be selectable on trajectory shape alone; depth is the only lever, never goal state.
  self.assertTrue(e.trigger(self.o))
  completed,users=e.depth(self.o)
  self.assertEqual(e.pending_supported_call(self.o),e.action(self.o.message)['name'])
  for rule in ((completed+1,users),(completed,users+1)):
   self.o.trigger_rule=rule;self.assertFalse(e.trigger(self.o),rule)
  self.o.trigger_rule=(completed,users);self.assertTrue(e.trigger(self.o))
  deep=copy.deepcopy(self.c);deep['review']['min_completed_assistant_tools']=7;deep['review']['min_user_text_events']=3
  self.assertEqual(e.make(self.task,self.client,deep,initialize=False).trigger_rule,(7,3))

 def test_review_prompt_demands_text_reply_and_closable_literals(self):
  # execute() only closes C on exact literal matches, so a prompt that leaves the declaration
  # vocabulary implicit makes C indistinguishable from P against any live model.
  saved=e.snapshot(self.o)
  def prompt_for(self_review):
   seen=[];inner=self.client.transport
   def spy(payload):
    seen.append(payload['messages'][-1]['content']);return inner(payload)
   with patch.object(self.client,'transport',side_effect=spy):
    if self_review: self.client.models['self']='mock-actor'
    e.capture(self.o,self.client,self_review)
   return seen[0]
  reviewer=prompt_for(False)
  self.o=e.restore(saved,self.task,self.client,self.c)
  self_review=prompt_for(True)
  for prompt in (reviewer,self_review):
   self.assertTrue(prompt.startswith(e.TEXT_ONLY),prompt[:120])
   for literal in ('"action_local"','"ongoing"','"execute_target_call"','"normal_tool_return"'):
    self.assertIn(literal,prompt)
  self.assertIn('Reconsider your own pending action',self_review)

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

 def _mixed_user_reply(self):
  # Regression input modeled on the saved roaming mixed responses
  # (live-roaming-protectable-001/private/responses/8.json, 11.json): the user model emitted
  # preamble text plus exactly one valid device tool call in a single reply.
  return {'model':'mock-user','id':'fixture-mixed','usage':None,
   'choices':[{'finish_reason':'tool_calls','message':{'role':'assistant',
     'content':'Hello! My phone number is 555-123-2002. Let me check my network status first.',
     'tool_calls':[{'id':'fixture-mixed-call','type':'function',
                   'function':{'name':'check_network_status','arguments':'{}'}}]}}]}
 def _route_to_user(self,o):
  o.from_role=e.Role.AGENT;o.to_role=e.Role.USER
  o.message=e.AssistantMessage(role='assistant',content='Could you check your device and confirm your phone number?',timestamp=e.get_now())
 def _events(self,kind):
  path=self.store.root/'journal/events.jsonl'
  if not path.exists(): return []
  return [r for r in (json.loads(l) for l in path.read_text().splitlines()) if r['kind']==kind]

 def test_user_single_channel_convention_is_in_system_prompt(self):
  o=e.restore(e.snapshot(self.o),self.task,self.client,self.c)
  prompt=o.user_state.system_messages[0].content
  self.assertIn('Communication protocol (single channel',prompt)
  self.assertIn('exactly one tool call with no text',prompt)
  for version in ('user_single_channel_prompt_v1','user_single_channel_adapter_v1'):
   c2=copy.deepcopy(self.c);c2['models']['user_comm_protocol']=version
   self.assertIn('Communication protocol (single channel',
                 e.make(self.task,self.client,c2,initialize=False).user.global_simulation_guidelines)

 def test_user_mixed_message_adapter_reroutes_and_retains_text(self):
  # Default user_single_channel_adapter_v1: a mixed reply becomes a clean single tool call, the
  # suppressed preamble is retained in provenance, and the episode does NOT terminate.
  o=e.restore(e.snapshot(self.o),self.task,self.client,self.c)
  self.assertEqual(self.c['models']['user_comm_protocol'],'user_single_channel_adapter_v1')
  self._route_to_user(o);self.client.transport=lambda p: self._mixed_user_reply()
  o.step()
  self.assertFalse(o.done)
  self.assertEqual((o.from_role,o.to_role),(e.Role.USER,e.Role.ENV))
  self.assertTrue(o.message.is_tool_call());self.assertFalse(o.message.has_text_content())
  self.assertEqual(o.message.tool_calls[0].name,'check_network_status')
  adapted=self._events('user_mixed_message_adapted')
  self.assertEqual(len(adapted),1)
  self.assertIn('555-123-2002',adapted[0]['suppressed_text'])
  self.assertEqual(adapted[0]['tool_name'],'check_network_status')
  self.assertEqual(adapted[0]['comm_protocol'],'user_single_channel_adapter_v1')

 def test_user_mixed_message_prompt_only_is_native_user_error(self):
  # The prompt-only version documents that the convention alone does not stop the native
  # communication check from terminating on a mixed reply (doc §5.1 -> §5.2 rationale).
  c=copy.deepcopy(self.c);c['models']['user_comm_protocol']='user_single_channel_prompt_v1'
  o=e.make(self.task,self.client,c)
  self._route_to_user(o);self.client.transport=lambda p: self._mixed_user_reply()
  o.step()
  self.assertTrue(o.done);self.assertEqual(o.termination_reason,e.TerminationReason.USER_ERROR)
  self.assertEqual(e.outcome(o,self.task,[],[])['completion'],0)
  self.assertEqual(len(self._events('user_mixed_message_adapted')),0)

 def test_user_adapted_tool_call_survives_snapshot_restore(self):
  # Recovery path: the adapter's rerouted message is a clean user tool call; parked at user->env it
  # must round-trip like any pending user tool call (restore trims the trailing proposal from replay).
  o=e.restore(e.snapshot(self.o),self.task,self.client,self.c)
  self._route_to_user(o);self.client.transport=lambda p: self._mixed_user_reply()
  o.step();self.assertFalse(o.done)
  adapted=o.message
  self.assertTrue(adapted.is_tool_call());self.assertFalse(adapted.has_text_content())
  self.assertEqual(adapted.tool_calls[0].name,'check_network_status')
  # Park a consistent user->env state carrying the adapted call (mirrors the pending-call fork test).
  o2=e.restore(e.snapshot(self.o),self.task,self.client,self.c)
  o2.message=adapted;o2.trajectory[-1]=adapted;o2.from_role=e.Role('user');o2.to_role=e.Role('env')
  saved=e.snapshot(o2)
  self.assertEqual((saved['payload']['routing']['from'],saved['payload']['routing']['to']),('user','env'))
  restored=e.restore(saved,self.task,self.client,self.c)
  self.assertEqual(e.env_state(restored.environment),saved['payload']['environment'])
  self.assertEqual((restored.from_role.value,restored.to_role.value),('user','env'))
  self.assertTrue(restored.message.is_tool_call());self.assertFalse(restored.message.has_text_content())
  self.assertEqual(restored.message.tool_calls[0].name,'check_network_status')

 def test_user_protocol_endpoints_under_adapter(self):
  # Empty / unknown-tool / multiple-tool replies still reach the native USER_ERROR endpoint with the
  # adapter on; normal single-tool and normal-text replies pass through unchanged.
  def reply(content=None,calls=None,finish=None):
   return {'model':'mock-user','id':'fixture','usage':None,
    'choices':[{'finish_reason':finish or ('tool_calls' if calls else 'stop'),
      'message':{'role':'assistant','content':content,'tool_calls':calls or []}}]}
  def call(name,tag): return [{'id':tag,'type':'function','function':{'name':name,'arguments':'{}'}}]
  cases=[('empty',reply(content=''),'error'),
         ('unknown_tool',reply(calls=call('enable_roaming','u1')),'error'),
         ('multiple_tools',reply(calls=call('check_network_status','m1')+call('check_status_bar','m2')),'error'),
         ('normal_single_tool',reply(calls=call('check_network_status','n1')),'tool'),
         ('normal_text',reply(content='My phone number is 555-123-2002.'),'text')]
  for name,response,expected in cases:
   o=e.restore(e.snapshot(self.o),self.task,self.client,self.c)
   self._route_to_user(o);self.client.transport=lambda p,response=response: response
   o.step()
   if expected=='error':
    self.assertTrue(o.done,name);self.assertEqual(o.termination_reason,e.TerminationReason.USER_ERROR,name)
   elif expected=='tool':
    self.assertFalse(o.done,name);self.assertTrue(o.message.is_tool_call(),name)
    self.assertFalse(o.message.has_text_content(),name)
    self.assertEqual((o.from_role,o.to_role),(e.Role.USER,e.Role.ENV),name)
   else:
    self.assertFalse(o.done,name);self.assertTrue(o.message.has_text_content(),name)
    self.assertFalse(o.message.is_tool_call(),name)
    self.assertEqual((o.from_role,o.to_role),(e.Role.USER,e.Role.AGENT),name)
   if name in ('unknown_tool','multiple_tools'):
    self.assertGreaterEqual(len(self._events('received_model_protocol_error')),1,name)
   # The adapter must never fire on a non-mixed reply.
   self.assertEqual(len(self._events('user_mixed_message_adapted')),0,name)

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

 def test_vpn_defaults_are_per_instance_in_both_orders(self):
  from tau2.domains.telecom.user_tools import TelecomUserTools
  from tau2.domains.telecom.user_data_model import PerformanceLevel
  global_before=TelecomUserTools.default_vpn_details.model_dump()
  for first in (0,1):
   pair=[e.get_environment(),e.get_environment()]
   self.assertIsNot(pair[0].user_tools.default_vpn_details,pair[1].user_tools.default_vpn_details)
   pair[first].user_tools.break_vpn();pair[1-first].user_tools.connect_vpn()
   self.assertEqual(pair[first].user_tools.device.vpn_details.server_performance,PerformanceLevel.POOR)
   self.assertEqual(pair[1-first].user_tools.device.vpn_details.server_performance,PerformanceLevel.EXCELLENT)
   self.assertEqual(TelecomUserTools.default_vpn_details.model_dump(),global_before)
 def test_vpn_factory_ignores_already_polluted_class_default(self):
  from tau2.domains.telecom.user_tools import TelecomUserTools
  from tau2.domains.telecom.user_data_model import PerformanceLevel
  polluted=TelecomUserTools.default_vpn_details.model_copy(deep=True);polluted.server_performance=PerformanceLevel.POOR
  with patch.object(TelecomUserTools,'default_vpn_details',polluted):
   env=e.get_environment();env.user_tools.connect_vpn()
   self.assertEqual(env.user_tools.device.vpn_details.server_performance,PerformanceLevel.EXCELLENT)
   self.assertEqual(polluted.server_performance,PerformanceLevel.POOR)
 def test_vpn_make_restore_and_task_order_are_isolated(self):
  task=vpn_task();baseline=None
  for order in (('bad','clean'),('clean','bad')):
   objects={name:e.make(task if name=='bad' else self.task,self.client,self.c) for name in order}
   before=e.env_state(objects['clean'].environment)
   if baseline is None:baseline=before
   self.assertEqual(before,baseline)
   saved=e.snapshot(objects['bad']);restored=e.restore(saved,task,self.client,self.c)
   self.assertEqual(e.env_state(restored.environment),saved['payload']['environment'])
   self.assertIsNot(restored.environment.user_tools.default_vpn_details,objects['bad'].environment.user_tools.default_vpn_details)
   trace=finish_vpn(restored,self.client);self.assertEqual(e.outcome(restored,task,[],trace)['completion'],1)
   self.assertEqual(e.env_state(objects['clean'].environment),baseline)
 def test_official_evaluation_vpn_constructors_do_not_pollute_live_or_global(self):
  from local_experiments import telecom
  from tau2.domains.telecom.user_tools import TelecomUserTools
  task=vpn_task();o=e.make(task,self.client,self.c);trace=finish_vpn(o,self.client)
  neighbor=e.get_environment();global_before=TelecomUserTools.default_vpn_details.model_dump()
  before=e.env_state(o.environment);neighbor_before=e.env_state(neighbor);created=[]
  original=telecom.registry.get_env_constructor('telecom')
  def factory(**kwargs):
   env=telecom.get_environment(**kwargs);created.append(env);return env
  with patch.dict(telecom.registry._domains,{telecom.EVALUATION_DOMAIN:factory}):
   for _ in range(2):self.assertEqual(e.outcome(o,task,[],trace)['completion'],1)
  self.assertEqual(len(created),6) # schema, predicted and gold for each evaluation
  self.assertEqual(len({id(env.user_tools.default_vpn_details) for env in created}),6)
  self.assertTrue(all(env.user_tools.default_vpn_details is not o.environment.user_tools.default_vpn_details for env in created))
  self.assertEqual(e.env_state(o.environment),before);self.assertEqual(e.env_state(neighbor),neighbor_before)
  self.assertEqual(TelecomUserTools.default_vpn_details.model_dump(),global_before)
  self.assertIs(telecom.registry.get_env_constructor('telecom'),original)

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1] in ('save-refuel','restore-refuel'):
  phase,path=sys.argv[1:];path=Path(path)
  with tempfile.TemporaryDirectory() as tmp:
   c,s,client,task,o=refuel_run(tmp)
   if phase=='save-refuel':
    roots,_=refuel_roots(o,task);assert roots[-1]['protected']==[REFUEL_GOAL],roots
    assert o.environment.tools.db.lines[1].data_refueling_gb==2.0
    write_json(path,e.snapshot(o))
   else:
    saved=json.loads(path.read_text());o=e.restore(saved,task,client,c)
    assert e.env_state(o.environment)==saved['payload']['environment']
    assert o.agent.record is None and o.agent.draw_consumed==saved['payload']['draw_consumed']
    # The non-idempotent official refuel must replay exactly once, not accumulate again.
    assert o.environment.tools.db.lines[1].data_refueling_gb==2.0,o.environment.tools.db.lines[1].data_refueling_gb
    assert e.vector(o.environment,task)[REFUEL_GOAL] is True
    refuel_tail(client);result=e.outcome(o,task,[REFUEL_GOAL],e.advance(o,[],task))
    assert result['termination']=='user_stop',result
    assert result['protected_count']==1 and result['structural_zero'] is False,result
    assert result['loss']==0,result
    assert o.environment.tools.db.lines[1].data_refueling_gb==2.0 # official evaluation replay did not mutate the live env
   print('fresh-process '+phase+' passed')
   raise SystemExit(0)
 if len(sys.argv)>1 and sys.argv[1] in ('save','restore','save-write','restore-write','save-init','restore-init','save-history','restore-history','save-vpn','restore-vpn'):
  phase,path=sys.argv[1:];path=Path(path)
  with tempfile.TemporaryDirectory() as tmp:
   c,s,client,task,o=setup_run(tmp,4 if 'write' in phase else 0,'roaming' if 'write' in phase else 'read')
   if 'vpn' in phase:
    task=vpn_task();o=e.make(task,client,c)
    if phase.startswith('save'):write_json(path,e.snapshot(o))
    else:
     saved=json.loads(path.read_text());o=e.restore(saved,task,client,c);assert e.env_state(o.environment)==saved['payload']['environment']
     result=e.outcome(o,task,[],finish_vpn(o,client));assert result['completion']==1
    print('fresh-process VPN instance isolation passed');raise SystemExit(0)
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

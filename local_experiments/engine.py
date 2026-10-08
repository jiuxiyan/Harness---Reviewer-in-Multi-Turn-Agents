"""Official Telecom READ and roaming-WRITE root experiment; independent generated continuations.

Import only in the sanitized worker. Evaluation is isolated on copies, never used
by trigger, reviewer, renderer, fallback, or transport.
"""
import copy
import json
import random
import time
import numpy as np
from tau2.agent.llm_agent import LLMAgent, LLMAgentState
from tau2.user.user_simulator import UserSimulator
from tau2.user.user_simulator_base import UserState
from tau2.data_model.message import AssistantMessage, UserMessage, ToolCall, ToolMessage, MultiToolMessage
from tau2.data_model.simulation import TerminationReason
from tau2.orchestrator.orchestrator import Orchestrator, Role
from tau2.domains.telecom.environment import get_environment, get_tasks
from tau2.environment.toolkit import ToolType, get_tool_types
from tau2.evaluator.evaluator import evaluate_simulation, EvaluationType
from tau2.utils.llm_utils import to_litellm_messages
from tau2.utils.utils import get_now
from .config import ROOT, canonical
from .storage import RunFailure, digest
from .provider import Client, ModelOutputError

HEADERS = {'neutral': 'Applicability status unchanged; retain the original advice packet.',
           'consumed': 'Target call requirement fulfilled; retain advice as history only.'}
WIDTH=max(map(len,HEADERS.values())); HEADERS={k:v.ljust(WIDTH) for k,v in HEADERS.items()}
RECEIPT_PREFIX='Controller execution record (not an actor generation):\n'
REVIEW_INSTRUCTION='Return exactly one JSON object with selected_action {name,arguments}, packet (nonempty string), declaration {target_action_id,scope,instruction,close_condition}. Select one available assistant tool in the declared READ/roaming-WRITE scope. Public action-local scope is action_local / execute_target_call / normal_tool_return. target_action_id must equal the target ID supplied for the selected action. Do not claim task completion from a tool return. No tools will execute during this review.'

def plain(x): return x.model_dump(mode='json') if hasattr(x,'model_dump') else x

def vector(env,task):
 shadow=copy.deepcopy(env)
 return [bool(shadow.run_env_assertion(a,raise_assertion_error=False)) for a in task.evaluation_criteria.env_assertions]

def env_state(env):
 return {'agent':plain(env.tools.db),'user':plain(env.user_tools.db),
         'ids':dict(env.tools.id_generator.id_counter),
         'network':plain(env.user_tools.network_mode_preference),
         'vpn':plain(env.user_tools.default_vpn_details)}

def action(message):
 if not message.is_tool_call() or len(message.tool_calls)!=1: raise RunFailure('unsupported_path')
 c=message.tool_calls[0];return {'name':c.name,'arguments':copy.deepcopy(c.arguments)}

def target_id(original,selected):
 proposal=plain(original)
 for k in ('timestamp','turn_idx'):proposal.pop(k,None)
 return 'controller-'+digest({'proposal':proposal})[:24]

def project(messages,record,arm,valid_responses):
 """Projection accepts public history and public receipt only, no evaluator."""
 wire=copy.deepcopy(messages)
 if not record or arm=='B_bare': return wire
 call_id=record['call_id'];out=[];found=0;i=0
 while i<len(wire):
  m=wire[i];ids=[x['id'] for x in (m.get('tool_calls') or [])]
  if call_id in ids:
   if ids!=[call_id] or i+1>=len(wire) or wire[i+1].get('tool_call_id')!=call_id: raise RunFailure('receipt_pair_mismatch')
   receipt=record['receipt']
   if wire[i+1].get('content')!=receipt['result']['content']: raise RunFailure('receipt_result_mismatch')
   event={'execution_receipt':receipt,'extra_packet':record['packet'] if arm in ('P0','P','R','C') else ''}
   if event['extra_packet'] and arm in ('P','R','C'):
    if arm=='R' and valid_responses>=1: event['extra_packet']=''
    else:
     state='consumed' if arm=='C' and valid_responses>=1 and record['closable'] else 'neutral'
     event['advice_lifetime_header']={'status':HEADERS[state]}
   out.append({'role':'system','content':RECEIPT_PREFIX+canonical(event)});i+=2;found+=1
  else: out.append(m);i+=1
 if found!=1: raise RunFailure('receipt_span_missing')
 return out

class NativeModelFailure(Exception):
 def __init__(self,message,state,role):self.message=message;self.state=state;self.role=role

class LocalOrchestrator(Orchestrator):
 def _model_failure(self,error):
  # Official step validates empty messages before its communication handler.
  # Route received model failures to that same native endpoint explicitly.
  setattr(self,'agent_state' if error.role=='assistant' else 'user_state',error.state)
  self.message=error.message;self.trajectory.append(error.message)
  self.from_role=Role.AGENT if error.role=='assistant' else Role.USER
  self.to_role=Role.USER if error.role=='assistant' else Role.AGENT
  self.check_communication_error()
  if not self.done:raise RunFailure('model_failure_endpoint_not_reached')
  self.step_count+=1;self.environment.sync_tools()
 def step(self):
  try:return super().step()
  except NativeModelFailure as error:self._model_failure(error)

class Actor(LLMAgent):
 def __init__(self,client,**kwargs):
  super().__init__(**kwargs);self.client=client;self.record=None;self.arm='B_bare';self.valid=0;self.context={};self.draw_consumed=False;self.intervention_executed=False;self.mock_index=0
 def generate_next_message(self,message,state):
  state=state.model_copy(deep=True)
  state.messages.extend(message.tool_messages if isinstance(message,MultiToolMessage) else [message])
  wire=project(to_litellm_messages(state.system_messages+state.messages),self.record,self.arm,self.valid)
  try: response=self.client.call('actor',wire,[t.openai_schema for t in self.tools],self.context)
  except ModelOutputError:
   response={'content':None,'tool_calls':[]} # Native empty-message AGENT_ERROR endpoint.
  msg=decode_model(response,'assistant')
  if msg.is_tool_call():
   if len(msg.tool_calls)!=1 or any(c.name not in {t.name for t in self.tools} for c in msg.tool_calls):
    self.client.store.event('received_model_protocol_error',role='actor',reason='multiple_or_unknown_tool',context=self.context)
    msg=AssistantMessage(role='assistant',content=None,timestamp=get_now())
   elif msg.tool_calls[0].name not in self.allowed_names:raise RunFailure('unsupported_known_write_capability')
  state.messages.append(msg)
  if not msg.has_content() and not msg.is_tool_call():raise NativeModelFailure(msg,state,'assistant')
  if self.record and bool(msg.has_text_content()) != bool(msg.is_tool_call()): self.valid+=1
  return msg,state

class User(UserSimulator):
 def __init__(self,client,**kwargs): super().__init__(**kwargs);self.client=client;self.context={}
 def generate_next_message(self,message,state):
  state=state.model_copy(deep=True)
  if isinstance(message,MultiToolMessage): state.messages.extend(message.tool_messages)
  elif isinstance(message,ToolMessage) or message.has_content() or message.is_tool_call(): state.messages.append(message)
  try: response=self.client.call('user',to_litellm_messages(state.system_messages+state.flip_roles()),[t.openai_schema for t in self.tools],self.context)
  except ModelOutputError:
   response={'content':None,'tool_calls':[]} # Native USER_ERROR endpoint.
  msg=decode_model(response,'user')
  if msg.is_tool_call() and (len(msg.tool_calls)!=1 or any(c.name not in {t.name for t in self.tools} for c in msg.tool_calls)):
   self.client.store.event('received_model_protocol_error',role='user',reason='multiple_or_unknown_tool',context=self.context)
   msg=UserMessage(role='user',content=None,timestamp=get_now())
  state.messages.append(msg)
  if not msg.has_content() and not msg.is_tool_call():raise NativeModelFailure(msg,state,'user')
  return msg,state

def decode_model(value,role):
 calls=[ToolCall(id=c['id'],requestor=role,name=c['function']['name'],arguments=json.loads(c['function']['arguments'])) for c in value.get('tool_calls',[])]
 cls=AssistantMessage if role=='assistant' else UserMessage
 return cls(role=role,content=value.get('content'),tool_calls=calls or None,timestamp=get_now())

def make(task,client,config,initialize=True):
 env=get_environment()
 actor=Actor(client,tools=env.get_tools(),domain_policy=env.get_policy(),llm='explicit-local-transport',llm_args={})
 actor.read_names={k for k,v in get_tool_types(env.tools).items() if v==ToolType.READ}
 actor.allowed_names=actor.read_names|set(config['review']['allowed_writes'])
 user=User(client,tools=env.get_user_tools(),instructions=str(task.user_scenario),llm='explicit-local-transport',llm_args={})
 limits=config['limits']
 o=LocalOrchestrator(domain='telecom',agent=actor,user=user,environment=env,task=task,max_steps=limits['max_native_steps'],max_errors=limits['max_native_errors'],seed=config['sampling']['allocation_seed'],simulation_id='local-'+digest(task.id)[:16],timeout=None,validate_communication=True)
 o._run_start_time=get_now();o._run_start_perf=time.perf_counter();o.run_config_hash=digest(config)
 if initialize: o.initialize()
 return o

def trigger(o):
 if o.done or o.from_role!=Role.AGENT or o.to_role!=Role.ENV: return False
 try: a=action(o.message)
 except RunFailure: return False
 completed=sum(isinstance(m,ToolMessage) and m.requestor=='assistant' for m in o.trajectory)
 users=sum(isinstance(m,UserMessage) and not m.is_tool_call() for m in o.trajectory)
 return a['name'] in o.agent.allowed_names and completed>=2 and users>=1

def snapshot(o):
 from .provenance import source_hashes
 payload={'task_sha256':digest(plain(o.task)),'config_hash':o.run_config_hash,'source_hashes':source_hashes(),'draw_consumed':o.agent.draw_consumed,'intervention_executed':o.agent.intervention_executed,'history':[plain(m) for m in o.trajectory],'actor':plain(o.agent_state),'user':plain(o.user_state),
 'routing':{'from':o.from_role.value,'to':o.to_role.value,'message':plain(o.message)},
 'step_count':o.step_count,'num_errors':o.num_errors,'max_steps':o.max_steps,'max_errors':o.max_errors,
 'done':o.done,'termination':o.termination_reason.value if o.termination_reason else None,
 'record':o.agent.record,'arm':o.agent.arm,'valid':o.agent.valid,'environment':env_state(o.environment),
 'started':o._run_start_time,'elapsed':time.perf_counter()-o._run_start_perf,
 'python_rng':random.getstate(),'numpy_rng':[np.random.get_state()[0],np.random.get_state()[1].tolist(),*np.random.get_state()[2:]]}
 return {'payload':payload,'sha256':digest(payload)}

def tuples(x): return tuple(tuples(i) for i in x) if isinstance(x,list) else x

def native(v): return {'assistant':AssistantMessage,'user':UserMessage,'tool':ToolMessage}[v['role']].model_validate(v)

def restore(saved,task,client,config):
 if digest(saved['payload'])!=saved['sha256']: raise RunFailure('restore_mismatch')
 s=saved['payload']
 from .provenance import source_hashes
 if s['task_sha256']!=digest(plain(task)) or s['config_hash']!=digest(config) or s['source_hashes']!=source_hashes(): raise RunFailure('restore_mismatch')
 o=make(task,client,config,initialize=False);o.agent.draw_consumed=s['draw_consumed'];o.agent.intervention_executed=s['intervention_executed'];history=[native(m) for m in s['history']]
 # At root the last assistant proposal is pending, so do not replay it.
 replay=history[:-1] if s['routing']['from']=='agent' and s['routing']['to']=='env' else history
 initial=task.initial_state
 try: o.environment.set_state(initial.initialization_data if initial else None,initial.initialization_actions if initial else None,replay,strict=True)
 except (ValueError,AssertionError): raise RunFailure('restore_mismatch') from None
 if o.seed is not None: o.agent.set_seed(o.seed);o.user.set_seed(o.seed)
 if env_state(o.environment)!=s['environment']: raise RunFailure('restore_mismatch')
 o.trajectory=history;o.agent_state=LLMAgentState.model_validate(s['actor']);o.user_state=UserState.model_validate(s['user'])
 o.from_role=Role(s['routing']['from']);o.to_role=Role(s['routing']['to']);o.message=native(s['routing']['message'])
 for name in ('step_count','num_errors','max_steps','max_errors','done'): setattr(o,name,s[name])
 o.termination_reason=TerminationReason(s['termination']) if s['termination'] else None
 o.agent.record=copy.deepcopy(s['record']);o.agent.arm=s['arm'];o.agent.valid=s['valid']
 o._run_start_time=s['started'];o._run_start_perf=time.perf_counter()-s['elapsed']
 random.setstate(tuples(s['python_rng']));n=s['numpy_rng'];np.random.set_state((n[0],np.array(n[1],dtype=np.uint32),n[2],n[3],n[4]))
 return o

def capture(o,client,self_review=False):
 if o.agent.draw_consumed: raise RunFailure('reviewer_redraw_forbidden')
 o.agent.draw_consumed=True
 original=o.message.model_copy(deep=True);a0=action(original)
 # Only completed actor-visible history, proposal as data, and public tool schemas.
 messages=to_litellm_messages(o.agent_state.system_messages+o.agent_state.messages[:-1])
 catalog={t.name:t for t in o.agent.tools if t.name in o.agent.allowed_names}
 # Hash binding is specified algorithmically since action arguments are chosen by reviewer.
 instruction=REVIEW_INSTRUCTION+' Target call ID: '+target_id(original,a0)+'\nAvailable intervention tools: '+canonical([t.openai_schema for t in catalog.values()])
 if self_review: instruction='Reconsider your own pending action once under the same public history and fixed response budget. '+instruction+' For this self-control the packet will never be displayed.'
 messages.append({'role':'system','content':instruction+'\nPending action: '+canonical(a0)})
 logical_begin=client.logical+1
 try:
  raw=client.call('self' if self_review else 'reviewer',messages,None,{**o.agent.context,'phase':'self' if self_review else 'review'})
  text=(raw.get('content') or '') if not raw.get('tool_calls') else ''
 except ModelOutputError as e:
  raw=e.response;text=''
 classification='invalid';selected=a0;packet='';dec=None
 try:
  q=json.loads(text)
  if set(q)!={'selected_action','packet','declaration'}: raise ValueError()
  a=q['selected_action'];d=q['declaration']
  if set(a)!={'name','arguments'} or not isinstance(a['arguments'],dict) or not isinstance(q['packet'],str) or not q['packet'].strip(): raise ValueError()
  if not isinstance(d,dict) or set(d)!={'target_action_id','scope','instruction','close_condition'} or any(not isinstance(v,str) or not v for v in d.values()): raise ValueError()
  if a['name'] not in catalog: classification='out_of_scope'
  else:
   params=catalog[a['name']].params
   if set(a['arguments'])-set(params.model_json_schema().get('properties',{})): raise ValueError()
   params.model_validate(a['arguments'],strict=True)
   selected=a;packet=q['packet'];dec=d
   classification='unchanged' if selected==a0 else 'valid_changed'
 except (ValueError,TypeError,KeyError): pass
 result={'raw_q':text,'raw_q_digest':digest(raw),'classification':classification,'selected_action':selected,'packet':packet,'declaration':dec,'semantic_audit':'not_audited','resamples':0,'logical_request_ids':[logical_begin]}
 client.store.event('self_draw_captured' if self_review else 'draw_captured',classification=classification,draw_digest=digest(result),context=o.agent.context)
 client.store.save('private/evaluation/draw-'+str(client.logical)+'.json',result)
 return result

def execute(o,draw,arm):
 if o.done or o.from_role!=Role.AGENT or o.to_role!=Role.ENV or o.agent.intervention_executed: raise RunFailure('intervention_slot_already_used_or_invalid')
 o.agent.draw_consumed=True;o.agent.intervention_executed=True
 original=o.message.model_copy(deep=True);selected=action(original) if arm in ('B','B_bare') else draw['selected_action']
 if arm=='B_bare': o.step();o._check_termination();return
 call_id=target_id(original,selected)
 derived=AssistantMessage(role='assistant',content=None,tool_calls=[ToolCall(id=call_id,requestor='assistant',**selected)],timestamp=original.timestamp,raw_data={'authored_by':'controller','original_proposal_digest':digest(plain(original))})
 o.trajectory[-1]=derived.model_copy(deep=True);o.agent_state.messages[-1]=derived.model_copy(deep=True);o.message=derived
 before=env_state(o.environment);o.step();o._check_termination();result=o.message
 if not isinstance(result,ToolMessage) or result.id!=call_id: raise RunFailure('receipt_pair_mismatch')
 after=env_state(o.environment)
 if selected['name'] in o.agent.read_names and before!=after: raise RunFailure('unsupported_read_mutation')
 dec=draw['declaration'];packet=draw['packet'] if arm not in ('B','A','S') else ''
 closable=bool(dec and dec['target_action_id']==call_id and dec['scope']=='action_local' and dec['instruction']=='execute_target_call' and dec['close_condition']=='normal_tool_return' and result.error is False)
 o.agent.record={'call_id':call_id,'packet':packet,'closable':closable,
 'state_change_observed':before!=after,'state_before_digest':digest(before),'state_after_digest':digest(after),
 'receipt':{'authored_by':'controller','selected_action':selected,'call_id':call_id,'result':{'content':result.content,'error':result.error}}}
 o.agent.arm=arm;o.agent.valid=0

def advance(o,trace,task,one_segment=False):
 called=False
 while not o.done:
  if one_segment and called and o.to_role==Role.AGENT: break
  was_actor=o.to_role==Role.AGENT
  o.step();o._check_termination();trace.append(vector(o.environment,task))
  called=called or was_actor
 return trace

def outcome(o,task,protected,trace):
 # All benchmark reward components supported by these tasks, on a deep-copied run.
 basis={str(x.value if hasattr(x,'value') else x) for x in task.evaluation_criteria.reward_basis}
 if basis!={'ENV_ASSERTION'}: raise RunFailure('unsupported_evaluator_basis')
 simulation=o._finalize();reward=evaluate_simulation(simulation,task,EvaluationType.ALL,False,'telecom',strict_replay=True)
 v=vector(o.environment,task)
 return {'loss':int(any(not v[i] for i in protected)),'completion':int(reward.reward==1.0),
 'protected_count':len(protected),'structural_zero':not protected,
 'immediate_loss':int(any(not trace[0][i] for i in protected)) if trace else 0,
 'transient_loss_recovered':int(any(any(not x[i] for i in protected) for x in trace) and all(v[i] for i in protected)),
 'terminal_vector':v,'official_reward':plain(reward),'termination':o.termination_reason.value,'native_steps':o.step_count}

def run(config,store,client):
 from .freeze import check_dataset
 from .costs import summarize_costs
 inventory=check_dataset(config);tasks={t.id:t for t in get_tasks(None)}
 rows=[];coverage={'starts':0,'roots':0,'no_public_trigger':0,'draws':0,'reference_failures':0}
 assignments=[];root_catalog=[]
 def row(base,o,task,protected,trace,requests,status='completed'):
  value={**base,'status':status,'loss':None,'completion':None,'evidence_kind':store.evidence,'logical_request_ids':sorted(set(requests))}
  if o is not None and o.done:
   value.update(outcome(o,task,protected,trace));value['status']='completed' if value['termination'] in ('user_stop','agent_stop') else 'native_'+value['termination']
  rows.append(value);store.append('derived/root_outcomes.jsonl',value)
 # Freeze reference-root selection before treatment suffixes; no outcome gate.
 for task_index,meta in enumerate(inventory):
  task=tasks[meta['task_id']]
  for start in range(config['sampling']['starts_per_task']):
   coverage['starts']+=1;trajectory=f't{task_index}-s{start}'
   o=make(task,client,config);o.agent.context=o.user.context={'trajectory_id':trajectory,'phase':'reference'}
   store.event('start_assigned',trajectory_id=trajectory)
   trace=[vector(o.environment,task)];reference_requests=[];root_count=0
   try:
    while not o.done and root_count<config['sampling']['max_roots_per_trajectory']:
     if trigger(o):
      root=f'{trajectory}-j{root_count}';root_count+=1;coverage['roots']+=1
      protected=[i for i,x in enumerate(trace[-1]) if x and not trace[0][i]]
      base={'task_id':meta['task_id'],'family_id':meta['family_id'],'trajectory_id':trajectory,'root_id':root}
      saved=snapshot(o)
      store.save('private/evaluation/'+root+'-goals.json',{'protected_indices':protected,'initially_true_indices':[i for i,x in enumerate(trace[0]) if x],'prefix_vectors':trace,'membership_basis':'initial-false acquired, still-required pinned task goals'})
      store.save('private/checkpoints/'+root+'-root.json',saved)
      root_catalog.append((base,task,saved,protected,list(reference_requests)))
      store.event('root_assigned',root_id=root,reference_logical_requests=reference_requests)
     if root_count>=config['sampling']['max_roots_per_trajectory']: break
     begin=client.logical;o.step();o._check_termination();reference_requests.extend(range(begin+1,client.logical+1));trace.append(vector(o.environment,task))
    if root_count==0:coverage['no_public_trigger']+=1;store.event('no_public_trigger',trajectory_id=trajectory)
   except RunFailure as exc:
    coverage['reference_failures']+=1;store.event('reference_incomplete',trajectory_id=trajectory,status=str(exc))
 for root_index,(base,task,saved,protected,reference_requests) in enumerate(root_catalog):
  root=base['root_id'];arms=config['arms'];common=[a for a in ('P','R','C') if a in arms]
  q=None;q_requests=[];self_q=None;self_requests=[]
  # Complete assigned blocks are written before any proposal/treatment request.
  assigned=[]
  for arm in arms:
   ks=range(config['sampling']['common_prefix_repeats']) if arm in common else range(1)
   for k in ks:
    rs=range(config['sampling']['suffix_repeats'] if arm in common else config['sampling']['independent_control_continuations'])
    for r in rs:assigned.append({**base,'common_prefix_repeat_id':k,'suffix_repeat_id':r,'arm_id':arm,'common_terminal':False})
  assignments.extend(assigned);store.append('derived/assignments.jsonl',{'root_id':root,'assignments':assigned})
  if any(a in ('A','P0','P','R','C') for a in arms):
   reviewer=restore(saved,task,client,config);reviewer.agent.context=base
   begin=client.logical
   try:q=capture(reviewer,client);coverage['draws']+=1
   except RunFailure as exc:store.event('review_unavailable',root_id=root,status=str(exc))
   q_requests=list(range(begin+1,client.logical+1))
  if 'S' in arms:
   reconsider=restore(saved,task,client,config);reconsider.agent.context=base;begin=client.logical
   try:self_q=capture(reconsider,client,True)
   except RunFailure as exc:store.event('self_unavailable',root_id=root,status=str(exc))
   self_requests=list(range(begin+1,client.logical+1))
  fallback={'selected_action':action(native(saved['payload']['routing']['message'])),'packet':'','declaration':None,'classification':'original'}
  # Each common segment may fail independently; keep every planned assignment.
  for k in range(config['sampling']['common_prefix_repeats']):
   if not common:break
   common_requests=[]
   try:
    if q is None:raise RunFailure('review_unavailable')
    shared=restore(saved,task,client,config);shared.agent.context=shared.user.context={**base,'common_prefix_repeat_id':k,'phase':'common'}
    execute(shared,q,'P');t=[vector(shared.environment,task)];begin=client.logical
    try:advance(shared,t,task,True)
    finally:common_requests=list(range(begin+1,client.logical+1))
    fork=snapshot(shared);store.save(f'private/checkpoints/{root}-k{k}.json',fork)
    store.event('common_segment_saved',root_id=root,common_prefix_repeat_id=k,checkpoint_digest=fork['sha256'],terminal=shared.done)
    jobs=[(arm,r) for arm in common for r in range(1 if shared.done else config['sampling']['suffix_repeats'])]
    random.Random(config['sampling']['allocation_seed']+root_index*100+k).shuffle(jobs)
    for arm,r in jobs:
     b={**base,'common_prefix_repeat_id':k,'suffix_repeat_id':r,'arm_id':arm,'common_terminal':shared.done}
     branch=None;begin=client.logical
     try:
      branch=restore(fork,task,client,config);branch.agent.arm=arm;branch.agent.context=branch.user.context={**b,'phase':'suffix'}
      future=advance(branch,list(t),task)
      row(b,branch,task,protected,future,reference_requests+q_requests+common_requests+list(range(begin+1,client.logical+1)))
     except RunFailure as exc:row(b,None,task,protected,[],reference_requests+q_requests+common_requests+list(range(begin+1,client.logical+1)),str(exc))
   except RunFailure as exc:
    for arm in common:
     for r in range(config['sampling']['suffix_repeats']):
      row({**base,'common_prefix_repeat_id':k,'suffix_repeat_id':r,'arm_id':arm,'common_terminal':False},None,task,protected,[],reference_requests+q_requests+common_requests,str(exc))
  for arm in (a for a in arms if a not in common):
   for r in range(config['sampling']['independent_control_continuations']):
    b={**base,'common_prefix_repeat_id':0,'suffix_repeat_id':r,'arm_id':arm,'common_terminal':False}
    extra=self_requests if arm=='S' else (q_requests if arm in ('A','P0') else [])
    begin=client.logical
    try:
     selected=self_q if arm=='S' else (q if arm in ('A','P0') else fallback)
     if selected is None:raise RunFailure('self_unavailable' if arm=='S' else 'review_unavailable')
     branch=restore(saved,task,client,config);branch.agent.context=branch.user.context={**b,'phase':'control'}
     execute(branch,selected,arm);future=advance(branch,[vector(branch.environment,task)],task)
     row(b,branch,task,protected,future,reference_requests+extra+list(range(begin+1,client.logical+1)))
    except RunFailure as exc:row(b,None,task,protected,[],reference_requests+extra+list(range(begin+1,client.logical+1)),str(exc))
 if client.recovery:client.recovery.assert_complete()
 store.save('derived/coverage.json',coverage)
 store.save('derived/exposure_manifest.json',{'source_commit':config['source']['benchmark_commit'],'tasks':inventory,'evidence_kind':store.evidence,'use':'include this file in subsequent confirmation exclusion manifests'})
 store.save('derived/costs.json',summarize_costs(client,rows))
 store.event('run_settled',assigned_rows=len(rows),assigned_roots=len(root_catalog))
 store.save('status.json',{'status':'completed_with_missing' if any(r['loss'] is None for r in rows) or coverage['reference_failures'] else 'completed','evidence_kind':store.evidence,'real_model_calls':0 if store.mode=='dry-run' else client.calls,'physical_attempts':client.calls,'outcomes':len(rows),'coverage':coverage})
 return rows

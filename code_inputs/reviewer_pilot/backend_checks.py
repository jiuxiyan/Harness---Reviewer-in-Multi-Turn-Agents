"""Narrow scripted adapter around UNMODIFIED official backend/orchestrator/evaluator.
Scripts replace only model generations; they are not natural episodes or reviewer arms.
"""
import copy,hashlib,json,pathlib,random,sys,uuid,time
import numpy as np
from tau2.agent.llm_agent import LLMAgent
from tau2.user.user_simulator import UserSimulator
from tau2.data_model.message import AssistantMessage,UserMessage,ToolMessage,ToolCall,MultiToolMessage
from tau2.data_model.tasks import Task
from tau2.domains.telecom.environment import get_environment,get_tasks
from tau2.orchestrator.orchestrator import Orchestrator,Role
from tau2.evaluator.evaluator import evaluate_simulation,EvaluationType
from tau2.evaluator.evaluator_env import EnvironmentEvaluator
from tau2.data_model.simulation import SimulationRun,TerminationReason
from tau2.utils.utils import get_now
from tau2.utils.llm_utils import to_litellm_messages
import no_api_guard as guard
R=pathlib.Path(__file__).resolve().parent
OUT=R/'results'
STAMP='2026-10-07T00:00:00.000000'

def dump(obj):
    if hasattr(obj,'model_dump'):return obj.model_dump(mode='json')
    if isinstance(obj,dict):return {str(k):dump(v) for k,v in obj.items()}
    if isinstance(obj,(list,tuple)):return [dump(x) for x in obj]
    if isinstance(obj,np.ndarray):return obj.tolist()
    if isinstance(obj,np.generic):return obj.item()
    if hasattr(obj,'value'):return obj.value
    return obj

def canonical(obj):
    return json.dumps(dump(obj),sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()

def digest(obj):return hashlib.sha256(canonical(obj)).hexdigest()

def normalize(obj):
    obj=dump(obj)
    if isinstance(obj,dict):return {k:normalize(v) for k,v in obj.items() if k not in {'timestamp','turn_idx'}}
    if isinstance(obj,list):return [normalize(v) for v in obj]
    return obj

def write(path,value):
    (OUT/path).write_text(json.dumps(dump(value),indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def decode(obj):
    return {'assistant':AssistantMessage,'user':UserMessage,'tool':ToolMessage}[obj['role']].model_validate(obj)

def emit(role,content=None,call=None):
    cls=AssistantMessage if role=='assistant' else UserMessage
    return cls(role=role,content=content,tool_calls=[call] if call else None,timestamp=STAMP)

def tool(role,name,args,identifier):
    return ToolCall(id=identifier,requestor=role,name=name,arguments=args)

class ScriptedAgent(LLMAgent):
    def __init__(self,queue,**kwargs):super().__init__(**kwargs);self.queue=list(queue)
    def generate_next_message(self,message,state):
        if isinstance(message,MultiToolMessage):state.messages.extend(message.tool_messages)
        else:state.messages.append(message)
        assert self.queue,'scripted agent queue exhausted'
        result=copy.deepcopy(self.queue.pop(0));result.timestamp=get_now();state.messages.append(result)
        return result,state

class ScriptedUser(UserSimulator):
    def __init__(self,queue,**kwargs):super().__init__(**kwargs);self.queue=list(queue)
    def generate_next_message(self,message,state):
        if isinstance(message,MultiToolMessage):state.messages.extend(message.tool_messages)
        else:state.messages.append(message)
        assert self.queue,'scripted user queue exhausted'
        result=copy.deepcopy(self.queue.pop(0));result.timestamp=get_now();state.messages.append(result)
        return result,state

def script(task):
    aq=[];uq=[emit('user','My mobile data is not working properly and I want excellent speed. I am John Smith, phone 555-123-2002.')]
    speed={'set_network_mode_preference','toggle_data_saver_mode'}
    early=[a for a in task.evaluation_criteria.actions if a.name not in speed]
    late=[a for a in task.evaluation_criteria.actions if a.name in speed]
    assert early and late
    def append_action(action,tag):
        call=tool(action.requestor,action.name,action.arguments,tag)
        if action.requestor=='user':
            aq.append(emit('assistant','Please perform this troubleshooting action: '+action.name+'.'))
            uq.extend([emit('user',call=call),emit('user','I followed that instruction; please continue.')])
        else:
            aq.extend([emit('assistant',call=call),emit('assistant','That carrier-side action completed. Please continue troubleshooting with me.')])
            uq.append(emit('user','Please continue.'))
    for n,a in enumerate(early):append_action(a,'early-'+str(n))
    aq.append(emit('assistant','Please run a speed test and report the result.'))
    uq.extend([emit('user',call=tool('user','run_speed_test',{},'prefix-speed-test')),emit('user','I ran the speed test. Please continue addressing the remaining speed problem.')])
    pending=emit('assistant',call=tool('assistant','get_customer_by_phone',{'phone_number':'555-123-2002'},'pending-shared-proposal'))
    aq.append(pending)
    for n,a in enumerate(late):append_action(a,'late-'+str(n))
    aq.append(emit('assistant','The scripted troubleshooting sequence is complete.'))
    uq.append(emit('user','###STOP###'))
    return aq,uq,pending

def make_orchestrator(task,aq,uq):
    env=get_environment()
    agent=ScriptedAgent(aq,tools=env.get_tools(),domain_policy=env.get_policy(),llm='OFFLINE_SCRIPT_ONLY',llm_args={})
    user=ScriptedUser(uq,tools=env.get_user_tools(),instructions=str(task.user_scenario),llm='OFFLINE_SCRIPT_ONLY',llm_args={})
    o=Orchestrator(domain='telecom',agent=agent,user=user,environment=env,task=task,max_steps=200,max_errors=10,seed=0,simulation_id='scripted-readiness-'+digest(task.id)[:12],timeout=None,validate_communication=True)
    o._run_start_time=get_now();o._run_start_perf=time.perf_counter()
    return o

def state(env):
    return {'agent_db':dump(env.tools.db),'user_db':dump(env.user_tools.db),'agent_aux':{'id_counter':dict(env.tools.id_generator.id_counter)},'user_aux':{'network_mode_preference':dump(env.user_tools.network_mode_preference),'default_vpn_details':dump(env.user_tools.default_vpn_details)},'domain':env.domain_name,'policy_sha256':digest(env.get_policy()),'agent_schema_sha256':digest([x.openai_schema for x in env.get_tools()]),'user_schema_sha256':digest([x.openai_schema for x in env.get_user_tools()]),'solo_mode':env.solo_mode}

def vector(env,task):
    # Official assertion calls sync DBs: evaluate a copy, never the live branch.
    private=copy.deepcopy(env)
    return [private.run_env_assertion(a,raise_assertion_error=False) for a in task.evaluation_criteria.env_assertions]

def rng_state():return {'python':dump(random.getstate()),'numpy':dump(np.random.get_state()),'uuid_policy':'Forbidden in this test; supplied simulation id; no UUID-generating tools.'}

def effective_views(o):
    return {"agent":to_litellm_messages(o.agent_state.system_messages+o.agent_state.messages),"user":to_litellm_messages(o.user_state.system_messages+o.user_state.flip_roles())}

def orch_state(o,normalized=True):
    result=dump({'environment':state(o.environment),'history':o.trajectory,'agent_state':o.agent_state,'user_state':o.user_state,'routing':{'from':o.from_role,'to':o.to_role,'message':o.message},'budget':{'step_count':o.step_count,'max_steps':o.max_steps,'remaining_steps':o.max_steps-o.step_count,'num_errors':o.num_errors,'max_errors':o.max_errors,'remaining_errors':o.max_errors-o.num_errors,'timeout':o.timeout,'model_calls':0},'done':o.done,'termination_reason':o.termination_reason,'agent_queue':o.agent.queue,'user_queue':o.user.queue,'rng':rng_state(),'effective_model_history':effective_views(o),'actor_config':{'model':o.agent.llm,'args':o.agent.llm_args},'user_config':{'model':o.user.llm,'args':o.user.llm_args}})
    return normalize(result) if normalized else result

def block_uuid():
    # This deliberate test exclusion is outside upstream code; any call fails the test.
    uuid.uuid4=guard.deny('unsupported-nondeterminism:uuid4')

def create(index):
    random.seed(0);np.random.seed(0);block_uuid()
    ids=next(x['staged_candidate_ids'] for x in json.loads((R/'task_audit.json').read_text())['splits'] if x['split']=='base')
    task=next(t for t in get_tasks('base') if t.id==ids[index])
    aq,uq,pending=script(task)
    o=make_orchestrator(task,aq,uq);o.initialize()
    initial=vector(o.environment,task);assert initial==[False,False],initial
    trajectory_vectors=[{'step_count':0,'vector':initial}]
    while True:
        o.step();o._check_termination()
        current=vector(o.environment,task)
        trajectory_vectors.append({'step_count':o.step_count,'vector':current})
        if isinstance(o.message,AssistantMessage) and o.message.is_tool_call() and o.message.tool_calls[0].id=='pending-shared-proposal':break
        assert o.step_count<100 and not o.done
    assert current==[True,False],current
    assert o.to_role==Role.ENV and o.from_role==Role.AGENT
    completed=o.trajectory[:-1]
    assert completed[-1].role=='user' and not completed[-1].is_tool_call()
    # Pending proposal has been produced but never executed.
    checkpoint={'label':'SCRIPTED INFRASTRUCTURE PREPARATION; NOT NATURAL EPISODE','task_id':task.id,'task_sha256':digest(task),'completed_history':dump(completed),'pending_proposal':dump(o.message),'remaining_agent_queue':dump(o.agent.queue),'remaining_user_queue':dump(o.user.queue),'state':orch_state(o),'raw_checkpoint':orch_state(o,False),'raw_state_sha256':digest({'history':o.trajectory,'agent_state':o.agent_state,'user_state':o.user_state}),'initial_vector':initial,'prefix_vector':current,'prefix_vectors':trajectory_vectors,'normalization':'Only timestamp and turn_idx metadata omitted from semantic comparisons. Raw message records retained.'}
    checkpoint['semantic_checkpoint_sha256']=digest(checkpoint['state'])
    checkpoint['raw_checkpoint_sha256']=digest(checkpoint['raw_checkpoint'])
    write(f'task_{index}_checkpoint.json',checkpoint)
    o.step();o._check_termination()
    live_next_output=normalize(o.message);live_next_state=digest(orch_state(o))
    while not o.done:
        o.step();o._check_termination();assert o.step_count<200
    assert normalize(o.get_trajectory())==normalize(o.trajectory)
    live_sim=o._finalize()
    live_reward=evaluate_simulation(live_sim,task,EvaluationType.ENV,False,'telecom',strict_replay=True)
    assert live_reward.reward==1.0
    write(f'task_{index}_live_continuation.json',{'next_output':live_next_output,'next_state_sha256':live_next_state,'terminal_state_sha256':digest(state(o.environment)),'official_reward':live_reward.reward,'final_steps':o.step_count,'official_finalization_passed':True,'simulation':live_sim})
    result={'phase':'create','task_index':index,'task_id':task.id,'initial_vector':initial,'prefix_vector':current,'pending_executed_at_checkpoint':False,'live_continuation_executed':True,'checkpoint_steps':checkpoint['state']['budget']['step_count'],'live_final_steps':o.step_count,'semantic_checkpoint_sha256':checkpoint['semantic_checkpoint_sha256'],'unexpected_attempts':guard.EVENTS}
    assert not guard.EVENTS
    write(f'task_{index}_create_result.json',result);return result

def restore(index,replicate):
    random.seed(0);np.random.seed(0);block_uuid()
    c=json.loads((OUT/f'task_{index}_checkpoint.json').read_text())
    task=next(t for t in get_tasks('base') if t.id==c['task_id'])
    assert digest(task)==c['task_sha256']
    history=[decode(x) for x in c['completed_history']]
    task_prefix=task.model_copy(deep=True);task_prefix.initial_state.message_history=history
    o=make_orchestrator(task_prefix,[decode(x) for x in c['remaining_agent_queue']],[decode(x) for x in c['remaining_user_queue']]);o.initialize()
    native_reset={'step_count':o.step_count,'num_errors':o.num_errors}
    assert native_reset=={'step_count':0,'num_errors':0}
    # Narrow adapter: complete the same already-generated assistant proposal from a
    # single-message USER -> AGENT boundary, without generating it a second time.
    assert o.from_role==Role.USER and o.to_role==Role.AGENT
    # Restore original prefix metadata exactly; upstream initialize rewrites it.
    for restored_message,original_message in zip(o.trajectory,history):
        restored_message.timestamp=original_message.timestamp;restored_message.turn_idx=original_message.turn_idx
    for role in ['agent_state','user_state']:
        for restored_system,original_system in zip(getattr(o,role).system_messages,c['raw_checkpoint'][role]['system_messages']):
            restored_system.timestamp=original_system['timestamp'];restored_system.turn_idx=original_system['turn_idx']
    pending=decode(c['pending_proposal'])
    o.agent_state.messages.extend([o.message,pending]);o.trajectory.append(pending)
    o.message=pending;o.from_role=Role.AGENT;o.to_role=Role.ENV
    o.step_count=c['state']['budget']['step_count'];o.num_errors=c['state']['budget']['num_errors']
    random.setstate(_tuples(c['state']['rng']['python']))
    nr=c['state']['rng']['numpy'];np.random.set_state((nr[0],np.array(nr[1],dtype=np.uint32),nr[2],nr[3],nr[4]))
    restored=orch_state(o)
    assert orch_state(o,False)==c['raw_checkpoint'],_different(orch_state(o,False),c['raw_checkpoint'])
    assert digest(orch_state(o,False))==c['raw_checkpoint_sha256']
    assert restored==c['state'],_different(restored,c['state'])
    assert digest(restored)==c['semantic_checkpoint_sha256']
    v=vector(o.environment,task);assert v==[True,False]
    step_probe=copy.deepcopy(o);step_probe.max_steps=step_probe.step_count+1
    step_probe.step();step_probe._check_termination()
    assert step_probe.done and step_probe.termination_reason==TerminationReason.MAX_STEPS
    error_probe=copy.deepcopy(o);error_probe.max_errors=error_probe.num_errors+1
    error_probe.message.tool_calls[0].name='__invalid_tool_for_negative_control__'
    error_probe.step();error_probe._check_termination()
    assert error_probe.done and error_probe.termination_reason==TerminationReason.TOO_MANY_ERRORS
    o.step();o._check_termination() # Execute the identical pending agent read, once.
    next_output=normalize(o.message)
    after_next=orch_state(o)
    while not o.done:
        o.step();o._check_termination();assert o.step_count<200
    assert o.termination_reason==TerminationReason.USER_STOP
    terminal_vec=vector(o.environment,task);assert terminal_vec==[True,True]
    # Full official evaluator, including termination validity, on the original task.
    assert normalize(o.get_trajectory())==normalize(o.trajectory)
    sim=o._finalize()
    reward=evaluate_simulation(sim,task,EvaluationType.ENV,False,'telecom',strict_replay=True)
    assert reward.reward==1.0 and all(x.met for x in reward.env_assertions)
    # Negative control: premature termination must remain a failure, even with goals met.
    bad=sim.model_copy(deep=True);bad.termination_reason=TerminationReason.MAX_STEPS
    premature=evaluate_simulation(bad,task,EvaluationType.ENV,False,'telecom',strict_replay=True)
    assert premature.reward==0.0
    assert not guard.EVENTS
    result={'phase':'restore','task_index':index,'replicate':replicate,'task_id':task.id,'strict_replay_passed':True,'canonical_checkpoint_equal':True,'raw_checkpoint_equal_including_timestamps':True,'effective_model_history_equal':True,'native_counter_reset_observed':native_reset,'counter_restore_explicit':True,'semantic_checkpoint_sha256':digest(restored),'next_output':next_output,'next_state_sha256':digest(after_next),'terminal_state_sha256':digest(state(o.environment)),'prefix_vector':v,'terminal_vector':terminal_vec,'official_reward':reward.reward,'official_reward_info':dump(reward),'termination':o.termination_reason.value,'premature_termination_reward':premature.reward,'step_budget_enforced':step_probe.termination_reason.value,'error_budget_enforced':error_probe.termination_reason.value,'official_finalization_passed':True,'final_steps':o.step_count,'remaining_steps':o.max_steps-o.step_count,'unexpected_attempts':guard.EVENTS,'model_calls':0}
    write(f'task_{index}_restore_{replicate}.json',result)
    write(f'task_{index}_suffix_{replicate}.json',{'label':'SCRIPTED; not a model continuation','messages':dump(o.trajectory),'final_state':orch_state(o)})
    return {k:v for k,v in result.items() if k not in ['next_output','official_reward_info']}

def _tuples(obj):return tuple(_tuples(x) for x in obj) if isinstance(obj,list) else obj

def _different(a,b):
    return [k for k in set(a)|set(b) if a.get(k)!=b.get(k)]

def negative_controls():
    random.seed(0);np.random.seed(0);block_uuid()
    c=json.loads((OUT/'task_0_checkpoint.json').read_text())
    task=next(t for t in get_tasks('base') if t.id==c['task_id'])
    history=[decode(x) for x in c['completed_history']]
    rows=[]
    for name,altered in [('corrupted_mutating_response',copy.deepcopy(history)),('unresolved_pending_call',history+[decode(c['pending_proposal'])])]:
        if name=='corrupted_mutating_response':
            first=next(i for i,x in enumerate(altered) if isinstance(x,ToolMessage))
            assert altered[first-1].tool_calls[0].name=='toggle_airplane_mode'
            altered[first].content='"deliberately incorrect response for strict replay test"'
        env=get_environment()
        try:env.set_state(task.initial_state.initialization_data,task.initial_state.initialization_actions,altered,strict=True)
        except ValueError as exc:rows.append({'test':name,'rejected':True,'error_type':'ValueError','message':str(exc)[:180]})
        else:raise AssertionError('Invalid checkpoint was accepted: '+name)
    guard.TESTING=True
    try:
        try:uuid.uuid4()
        except guard.GuardViolation:rows.append({'test':'unsupported_uuid_path','rejected':True})
        else:raise AssertionError('UUID generation allowed')
    finally:guard.TESTING=False
    assert not guard.EVENTS
    result={'status':'PASS','negative_controls':rows,'unexpected_attempts':guard.EVENTS,'no_model_calls':True}
    write('negative_controls.json',result);return result

def read_tool_validation(replicate):
    """Read-only diagnostic transition probes at the seven saved checkpoints."""
    from tau2.environment.toolkit import get_tool_types,ToolType
    random.seed(0);np.random.seed(0);block_uuid()
    rows=[]
    for index in range(7):
        c=json.loads((OUT/f'task_{index}_checkpoint.json').read_text())
        task=next(t for t in get_tasks('base') if t.id==c['task_id'])
        history=[decode(x) for x in c['completed_history']]
        fixture_env=get_environment()
        customer=fixture_env.tools.get_customer_by_id('C1001')
        probes=[('get_customer_by_phone',{'phone_number':'555-123-2002'}),('get_customer_by_id',{'customer_id':'C1001'}),('get_customer_by_name',{'full_name':customer.full_name,'dob':customer.date_of_birth}),('get_details_by_id',{'id':'L1002'}),('get_bills_for_customer',{'customer_id':'C1001','limit':12}),('get_data_usage',{'customer_id':'C1001','line_id':'L1002'})]
        for name,args in probes:
            env=get_environment();env.set_state(task.initial_state.initialization_data,task.initial_state.initialization_actions,history,strict=True)
            assert get_tool_types(env.tools)[name]==ToolType.READ
            before=state(env);assert before==c['raw_checkpoint']['environment']
            output=env.get_response(tool('assistant',name,args,'read-probe-'+name))
            after=state(env)
            assert not output.error,(name,output.content)
            assert before==after,(name,'READ unexpectedly mutated state')
            assert vector(env,task)==[True,False]
            rows.append({'task_index':index,'task_id':task.id,'tool':name,'arguments':dump(args),'declared_tool_type':'read','environment_before_sha256':digest(before),'environment_after_sha256':digest(after),'state_unchanged':True,'output':normalize(output),'output_sha256':digest(normalize(output))})
    assert not guard.EVENTS
    result={'status':'PASS','replicate':replicate,'scope':'Six official agent READ tools, one concrete valid argument set each, at all seven scripted checkpoints; not arbitrary argument or mutating-tool coverage.','probes':rows,'unexpected_attempts':guard.EVENTS,'model_calls':0}
    write('read_tool_validation_'+replicate+'.json',result)
    return {'status':'PASS','replicate':replicate,'tool_names':sorted({x['tool'] for x in rows}),'checkpoint_tool_pairs':len(rows),'state_unchanged':True,'model_calls':0}

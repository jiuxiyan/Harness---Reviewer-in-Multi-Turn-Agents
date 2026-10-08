"""All examples and continuations are scripted public benchmark fixtures, not model outcomes."""
import copy
import json
import pathlib
import unittest
import time
from dataclasses import FrozenInstanceError
from unittest.mock import patch

import no_api_guard as guard
import backend_checks as backend
from offline_backend import load_root, restore_checkpoint
from interventions import (FrozenJSON, canonical, digest, critique_packet, Ledger, WHOLE_BLOCK,
                           classify_q, PREPARATION, BRANCH_USAGE, ArmKind)
from tau2.data_model.message import AssistantMessage, SystemMessage, ToolMessage, ToolCall, UserMessage, MultiToolMessage
from tau2.data_model.simulation import TerminationReason
from tau2.domains.telecom.environment import get_environment
from tau2.orchestrator.orchestrator import Role
from tau2.environment.environment import Environment
from tau2.utils.llm_utils import to_litellm_messages, get_cost
from renderer import (AdapterError, ControllerReceiptRendererV1, ExecutionRecord, ObservedModelOutput,
                      RawUsageLedger, ProviderBlocked, INTRO, PROPOSAL_INTRO, raw, records_from_json,
                      provider_request, validate_native)
from adapter import (ReceiptAwareOfflineAgent, ReceiptAwareState, bind_agent, select_and_execute,
                     checkpoint, restore, validate_derived_history)

C = json.loads((backend.R / 'results/task_0_checkpoint.json').read_text())
A0 = {'name': C['pending_proposal']['tool_calls'][0]['name'], 'arguments': C['pending_proposal']['tool_calls'][0]['arguments']}
A1 = {'name': 'get_details_by_id', 'arguments': {'id': 'L1002'}}
PACKET = critique_packet('SCRIPTED FIXTURE: Inspect the affected line directly before selecting more troubleshooting steps.')
CANARY = 'PRIVATE_EVALUATOR_CANARY_57c35f8a'


def prepare(branch='B'):
    o, task = restore_checkpoint(C)
    bind_agent(o, branch)
    return o, task


def recommend(action, packet=None, component='reviewer', identifier=None):
    available_packet = PACKET if packet is None and action == A1 else (packet or {})
    value = {'selected_action': action, 'packet': available_packet}
    return ObservedModelOutput(identifier or 'shared-recommendation:' + digest(value), component, FrozenJSON.of(value))


def execute(branch='B', action=None, packet=None):
    o, task = prepare(branch)
    action = action or A0
    source = 'original' if branch == 'B' else 'reviewer_fixture'
    rec, before = select_and_execute(o, action, source=source, packet=packet,
                                    recommendation=None if source == 'original' else recommend(action, packet))
    return o, task, rec, before


def request(o):
    return o.agent.request_for(o.message, o.agent_state)


def next_boundary(o):
    o.step(); o._check_termination()
    while not o.done and o.to_role != Role.AGENT:
        o.step(); o._check_termination()
    if o.done:
        raise AssertionError('Expected another actor boundary')
    return o


def strip_packet(projection):
    data = projection.payload.copy()
    for message in data['messages']:
        if message['role'] == 'system' and message['content'].startswith(INTRO):
            record = json.loads(message['content'][len(INTRO):]); record['extra_packet'] = {}
            message['content'] = INTRO + canonical(record)
    return data


class AdapterTests(unittest.TestCase):
    def test_exact_restore_and_binding_preserves_native_state(self):
        o, _ = restore_checkpoint(C)
        before = backend.orch_state(o, False)
        bind_agent(o, 'B')
        after = backend.orch_state(o, False)
        for key in ('renderer_version','receipt_records_json','actor_boundary_count'):
            after['agent_state'].pop(key)
        self.assertEqual(before, after)

    def test_one_execution_preserves_budget_queue_user_rng_catalog_and_read_state(self):
        o, _ = prepare()
        state = backend.orch_state(o, False)
        with patch.object(o.environment, 'get_response', wraps=o.environment.get_response) as spy:
            rec, before = select_and_execute(o, A0)
            self.assertEqual(spy.call_count, 1)
        after = backend.orch_state(o, False)
        self.assertEqual(before.copy(), state)
        for key in ('environment','user_state','agent_queue','user_queue','rng','actor_config','user_config'):
            self.assertEqual(state[key], after[key])
        self.assertEqual(o.step_count, state['budget']['step_count'] + 1)
        self.assertEqual(o.num_errors, state['budget']['num_errors'])
        self.assertEqual([x.openai_schema for x in o.agent.tools], [x.openai_schema for x in o.environment.get_tools()])

    def test_changed_action_official_response_and_id(self):
        o, _, rec, _ = execute('A', A1)
        self.assertNotEqual(rec.call_id, C['pending_proposal']['tool_calls'][0]['id'])
        self.assertEqual(rec.value.copy()['actual_result'], raw(o.message))
        self.assertEqual(json.loads(o.message.content)['line_id'], 'L1002')
        self.assertEqual(rec.public_receipt()['proposal_disposition'], 'not_executed')
        self.assertEqual(rec.value.copy()['observed']['message'], C['pending_proposal'])
        self.assertEqual(rec.value.copy()['derived_call']['raw_data']['authored_by'], 'controller')
        self.assertIsNone(rec.value.copy()['derived_call']['cost'])

    def test_two_boundaries_noop_A_B_byte_identical(self):
        b, *_ = execute(); a, *_ = execute('A-noop', A0)
        self.assertEqual(request(b).bytes, request(a).bytes)
        next_boundary(b); next_boundary(a)
        self.assertEqual(request(b).bytes, request(a).bytes)
        self.assertEqual(backend.normalize(b.trajectory), backend.normalize(a.trajectory))
        for o in (b,a):
            o.step()
            self.assertEqual(o.agent_state.actor_boundary_count, 2)
            self.assertEqual(len(o.agent.ledger.requests), 2)

    def test_two_boundaries_AP_packet_only(self):
        a, *_ = execute('A', A1); p, *_ = execute('P', A1, PACKET)
        for _ in range(2):
            self.assertNotEqual(request(a).bytes, request(p).bytes)
            self.assertEqual(strip_packet(request(a)), strip_packet(request(p)))
            self.assertEqual(backend.normalize(a.trajectory), backend.normalize(p.trajectory))
            next_boundary(a) if a.agent_state.actor_boundary_count == 0 else None
            next_boundary(p) if p.agent_state.actor_boundary_count == 0 else None

    def test_bare_B_is_separate_instrumentation_control(self):
        bare, _ = restore_checkpoint(C); bare.step()
        b, *_ = execute()
        bare_payload = {'messages': to_litellm_messages(bare.agent_state.system_messages + bare.agent_state.messages + [bare.message]),
                        'tools': [x.openai_schema for x in bare.agent.tools], 'config': {'model':bare.agent.llm,'args':bare.agent.llm_args}}
        self.assertNotEqual(canonical(bare_payload), request(b).payload.text)
        self.assertEqual(bare_payload['tools'], request(b).payload.copy()['tools'])
        self.assertEqual(bare_payload['config'], request(b).payload.copy()['config'])

    def test_result_appended_once_and_projection_every_generation(self):
        o, _, rec, _ = execute('A', A1)
        pending_len = len(o.agent_state.messages)
        request(o); request(o)
        self.assertEqual(len(o.agent_state.messages), pending_len)
        next_boundary(o)
        self.assertEqual(sum(type(m) is ToolMessage and m.id == rec.call_id for m in o.agent_state.messages), 1)
        for _ in range(2):
            payload = request(o).payload.copy()
            self.assertFalse(any(c['id'] == rec.call_id for m in payload['messages'] for c in (m.get('tool_calls') or [])))
            self.assertEqual(sum(m['role'] == 'system' and m['content'].startswith(INTRO) for m in payload['messages']), 1)

    def test_checkpoint_restore_at_two_boundaries_and_ledger(self):
        o, _, _, _ = execute('P', A1, PACKET)
        for boundary in range(2):
            saved = checkpoint(o, C)
            r, _ = restore(saved)
            self.assertEqual(backend.orch_state(o, False), backend.orch_state(r, False))
            self.assertEqual(request(o).bytes, request(r).bytes)
            self.assertEqual(o.agent.ledger.report(), r.agent.ledger.report())
            if boundary == 0:
                next_boundary(o)

    def test_restore_replays_executed_history_without_double_prefix(self):
        o, _, _, _ = execute('A', A1)
        saved = checkpoint(o, C)
        replay_calls = []
        original_set_state = Environment.set_state
        def count_set_state(env, *args, **kwargs):
            replay_calls.append(env)
            return original_set_state(env, *args, **kwargs)
        with patch.object(Environment, 'set_state', count_set_state):
            r, task = restore(saved)
        self.assertEqual(len(replay_calls), 1)
        self.assertEqual(backend.state(o.environment), backend.state(r.environment))
        env = get_environment()
        with patch.object(env, 'get_response', wraps=env.get_response) as spy:
            env.set_state(task.initial_state.initialization_data, task.initial_state.initialization_actions, validate_derived_history(r), strict=True)
            names = [call.args[0].name for call in spy.call_args_list]
        self.assertNotIn(A0['name'], names)
        self.assertNotIn(A1['name'], names)  # Official READ replay skips reads; captured result tested separately.
        self.assertEqual(backend.state(env), backend.state(r.environment))

    def test_native_termination_step_budget(self):
        o, _ = prepare(); o.max_steps = o.step_count + 1
        select_and_execute(o, A0)
        self.assertTrue(o.done); self.assertEqual(o.termination_reason, TerminationReason.MAX_STEPS)
        self.assertEqual(o.agent_state.actor_boundary_count, 0)

    def test_native_public_tool_error_and_error_termination(self):
        o, _ = prepare('A'); o.max_errors = o.num_errors + 1
        action = {'name':'get_details_by_id','arguments':{'id':'DOES_NOT_EXIST_PUBLIC_FAKE_ID'}}
        rec, _ = select_and_execute(o, action, source='reviewer_fixture', recommendation=recommend(action))
        self.assertTrue(o.done); self.assertEqual(o.termination_reason, TerminationReason.TOO_MANY_ERRORS)
        self.assertTrue(o.message.error); self.assertEqual(o.num_errors, 1)
        self.assertTrue(rec.public_receipt()['tool_result']['error'])

    def test_scripted_native_completion_and_evaluator_export(self):
        o, task, _, _ = execute('A', A1)
        while not o.done:
            o.step(); o._check_termination()
        self.assertEqual(o.termination_reason, TerminationReason.USER_STOP)
        self.assertEqual(o.agent_state.actor_boundary_count, 2)
        self.assertFalse(any(type(m) is SystemMessage for m in o.trajectory))
        simulation = o._finalize()
        from tau2.evaluator.evaluator import evaluate_simulation, EvaluationType
        result = evaluate_simulation(simulation, task, EvaluationType.ENV, False, 'telecom', strict_replay=True)
        self.assertEqual(result.reward, 1.0)  # Scripted fixture replay sanity only, not causal/model evidence.

    def test_immutable_observed_record_and_shared_checkpoint(self):
        original = canonical(C)
        o, _, rec, before = execute('A', A1)
        value = rec.value.copy(); value['observed']['message']['tool_calls'][0]['name'] = 'tampered'
        self.assertEqual(rec.value.copy()['observed']['message'], C['pending_proposal'])
        with self.assertRaises(FrozenInstanceError): rec.value = FrozenJSON.of({})
        self.assertEqual(canonical(C), original)
        self.assertEqual(before.copy()['routing']['message'], C['pending_proposal'])

    def test_missing_registry_fails_closed(self):
        o, *_ = execute('A', A1); o.agent_state.receipt_records_json = '[]'
        with self.assertRaises(AdapterError): request(o)

    def test_missing_derived_span_fails_closed(self):
        o, *_ = execute('A', A1); o.agent_state.messages.pop()
        with self.assertRaises(AdapterError): request(o)

    def test_removed_provenance_fails_closed(self):
        o, *_ = execute('A', A1); o.agent_state.messages[-1].raw_data = None
        with self.assertRaises(AdapterError): request(o)

    def test_corrupt_result_fails_closed(self):
        o, *_ = execute('A', A1); o.message.content = 'fake result'
        with self.assertRaises(AdapterError): request(o)

    def test_already_appended_result_fails_closed(self):
        o, *_ = execute('A', A1); o.agent_state.messages.append(copy.deepcopy(o.message))
        with self.assertRaises(AdapterError): request(o)

    def test_invalid_registry_and_checkpoint_tampering(self):
        o, *_ = execute('A', A1)
        for text in ('{}','[null]','[{"mode":"scripted_fixture","mode":"live"}]'):
            with self.assertRaises((ValueError, TypeError)): records_from_json(text)
        saved = checkpoint(o, C).copy(); saved['payload']['official_state']['budget']['step_count'] = 0
        with self.assertRaises(AdapterError): restore(FrozenJSON.of(saved))

    def test_timed_checkpoint_and_live_provider_block_before_mutation(self):
        o, _ = prepare(); o.timeout = 10; before = raw(o.message)
        with self.assertRaises(AdapterError): select_and_execute(o, A0)
        self.assertEqual(raw(o.message), before)
        for fn in (provider_request, o.agent.generate_live):
            with self.assertRaises(ProviderBlocked): fn(provider='any', approved=True, total_budget=100)

    def test_public_schema_and_mutation_rejected_without_execution(self):
        for action in ({'name':'toggle_airplane_mode','arguments':{}}, {'name':'get_details_by_id','arguments':{'id':42}}, {'name':'get_details_by_id','arguments':{'id':'L1002','extra':1}}):
            o, _ = prepare('A'); before = backend.orch_state(o, False)
            with self.assertRaises(ValueError): select_and_execute(o, action, source='reviewer_fixture', recommendation=recommend(action))
            self.assertEqual(backend.orch_state(o, False), before)

    def test_selected_package_matches_immutable_recommendation(self):
        o, _ = prepare('P')
        with self.assertRaises(AdapterError): select_and_execute(o, A1, source='reviewer_fixture', packet=PACKET, recommendation=recommend(A1, dict(PACKET, critique='DIFFERENT SCRIPTED CRITIQUE')))
        self.assertEqual(o.step_count, C['state']['budget']['step_count'])

    def test_native_topology_negative_cases(self):
        call = AssistantMessage(role='assistant',tool_calls=[ToolCall(id='x',name='read',arguments={})])
        result = ToolMessage(role='tool',id='x',content='ok')
        cases = [[call], [result], [call,result,result], [call,result,call,result],
                 [call, UserMessage(role='user',content='interrupt'),result],
                 [call, ToolMessage(role='tool',id='wrong',content='ok')],
                 [AssistantMessage(role='assistant',tool_calls=[])],
                 [call.model_copy(update={'content':'mixed'})],
                 [MultiToolMessage(role='tool',tool_messages=[result])],
                 [UserMessage(role='user',tool_calls=[ToolCall(id='u',name='user-tool',arguments={},requestor='user')])]]
        for case in cases:
            with self.subTest(case=str(case)):
                with self.assertRaises(AdapterError): validate_native(case)

    def test_private_checkpoint_and_observed_raw_metadata_excluded(self):
        o, _ = prepare('A')
        for m in (o.message,o.agent_state.messages[-1],o.trajectory[-1]):
            m.raw_data = {'evaluation_criteria':CANARY, 'task_id':CANARY, 'private_oracle':CANARY}
        # pending aliases preserved; raw metadata remains in immutable audit only.
        select_and_execute(o, A1, source='reviewer_fixture', recommendation=recommend(A1))
        text = request(o).payload.text
        self.assertNotIn(CANARY, text); self.assertNotIn('evaluation_criteria',text)
        self.assertIn(CANARY, o.agent_state.receipt_records_json)
        self.assertNotIn(CANARY, canonical(backend.effective_views(o)['user']))

    def test_private_packet_and_public_result_canary_blocked(self):
        for where in ('packet','result'):
            o, _ = prepare('P'); o.agent.private_canaries = (CANARY,)
            packet = copy.deepcopy(PACKET)
            if where == 'packet': packet['critique'] = CANARY
            if where == 'result':
                original = o.environment.get_response
                def contaminated(call):
                    result = original(call); result.content += CANARY; return result
                o.environment.get_response = contaminated
            with self.assertRaises(ValueError):
                select_and_execute(o, A1, source='reviewer_fixture', packet=packet, recommendation=recommend(A1,packet))
            self.assertEqual(len(o.agent.ledger.requests),0)

    def test_private_structural_packet_fields_rejected(self):
        o, _ = prepare('P'); packet = dict(PACKET, evaluation_criteria='leak')
        with self.assertRaises(ValueError): select_and_execute(o,A1,source='reviewer_fixture',packet=packet,recommendation=recommend(A1,packet))
        self.assertEqual(o.step_count, C['state']['budget']['step_count'])

    def test_public_goal_words_are_not_blacklisted(self):
        o, _ = prepare('P'); packet = dict(PACKET, critique='SCRIPTED: The goal is excellent speed and network improvement.')
        select_and_execute(o,A1,source='reviewer_fixture',packet=packet,recommendation=recommend(A1,packet))
        self.assertIn('excellent speed',request(o).payload.text)

    def test_reviewer_self_pending_proposal_is_data_and_request_logged(self):
        o, _ = prepare('A')
        for purpose in ('reviewer','self'):
            projection = o.agent.renderer.proposal_request(o.agent_state.system_messages,o.agent_state.messages,(),
                [x.openai_schema for x in o.agent.tools],{'model':o.agent.llm,'args':o.agent.llm_args},'SCRIPTED: reconsider once.')
            payload = projection.payload.copy()
            self.assertTrue(payload['messages'][-1]['content'].startswith(PROPOSAL_INTRO))
            self.assertFalse(any(c['id']=='pending-shared-proposal' for m in payload['messages'] for c in m.get('tool_calls') or []))
            o.agent.ledger.record_request('fixture:'+purpose,projection)
        self.assertEqual(len(o.agent.ledger.requests),2)
        self.assertEqual(o.step_count,10)

    def test_usage_dedup_conflicts_raw_fields_and_no_synthetic_cost(self):
        ledger = RawUsageLedger()
        observed = ObservedModelOutput('fixture-reviewer','reviewer',FrozenJSON.of({'raw_fixture':'unaltered','usage':None,'cost':None}))
        ledger.record_output(observed,3); ledger.record_output(observed,3)
        self.assertEqual(ledger.report()['test_units'],3)
        with self.assertRaises(AdapterError): ledger.record_output(observed,4)
        self.assertEqual(RawUsageLedger.restore(ledger.report()).report(),ledger.report())
        o, *_ = execute('A',A1); next_boundary(o); o.step()
        report = o.agent.ledger.report()
        self.assertEqual(len(report['effective_requests']),2)
        self.assertEqual(report['actual_model_calls'],0)
        self.assertEqual(report['actual_charges'],0)
        self.assertIsNone(report['real_token_usage'])
        self.assertFalse(any(x['observed']['message'].get('raw_data',{} ) and x['observed']['message'].get('raw_data',{}).get('record_kind')=='derived_intervention_execution' for x in report['observed_fixture_outputs'].values()))

    def test_frozen_fixture_budget_ledger_integration(self):
        root,catalog,names = load_root()
        q = classify_q(root,canonical(A1),catalog,names)
        budget = Ledger(WHOLE_BLOCK); budget.record_proposal(q); budget.charge_preparation(PREPARATION[3]); budget.reserve_four_arm_block(); budget.charge(PREPARATION[4])
        for kind in ArmKind:
            budget.start(kind)
            for row in BRANCH_USAGE:
                if row.arm == kind.value: budget.charge(row)
            o, *_ = execute(kind.value, A0 if kind in (ArmKind.B,ArmKind.S) else A1, PACKET if kind is ArmKind.P else None)
            before = budget.report(); request(o); request(o)
            self.assertEqual(budget.report(),before) # Rendering is not another generation/charge.
            budget.finished.add(kind.value)
        self.assertEqual(budget.report()['spent'],WHOLE_BLOCK-1)
        self.assertEqual(budget.report()['actual_api_calls'],0)

    def test_timestamp_ties_preserve_order_and_backward_sort_rejected(self):
        o, *_ = execute('A',A1)
        for m in o.trajectory: m.timestamp='2026-01-01T00:00:00.000000'
        validate_derived_history(o)
        o.trajectory[-1].timestamp='2025-01-01T00:00:00.000000'
        with self.assertRaises(AdapterError): validate_derived_history(o)

    def test_audio_and_streaming_not_silently_dropped(self):
        for changes in ({'audio_content':'AA==','is_audio':False}, {'chunk_id':0}, {'is_final_chunk':False}):
            o,_ = prepare()
            for m in (o.message, o.agent_state.messages[-1], o.trajectory[-1]):
                for key,value in changes.items(): setattr(m,key,value)
            with self.assertRaises(AdapterError): select_and_execute(o,A0)
            self.assertEqual(o.step_count,10)

    def test_second_intervention_slot_explicitly_unsupported(self):
        o, *_ = execute('A',A1)
        o.step()
        original = backend.decode(C['pending_proposal'])
        original.tool_calls[0].id = 'new-proposal'
        o.message = original; o.agent_state.messages[-1] = original.model_copy(deep=True)
        o.trajectory[-1] = original.model_copy(deep=True)
        o.from_role=Role.AGENT; o.to_role=Role.ENV
        before = o.agent.ledger.report()
        with self.assertRaises(AdapterError): select_and_execute(o,A0)
        self.assertEqual(o.agent.ledger.report(),before)

    def test_elapsed_duration_survives_restore(self):
        o, *_ = execute('A',A1)
        o._run_start_perf = time.perf_counter() - 50
        saved=checkpoint(o,C); r,_=restore(saved)
        self.assertGreaterEqual(time.perf_counter()-r._run_start_perf,50)
        self.assertEqual(r._run_start_time,o._run_start_time)

    def test_immutable_types_and_restored_decision_invariants(self):
        with self.assertRaises(AdapterError): ObservedModelOutput('mutable','actor',{})
        with self.assertRaises(AdapterError): ExecutionRecord({})
        o,_,rec,_ = execute('A',A1)
        value=rec.value.copy(); value['decision']['source']='original'; value['decision']['recommendation']=None
        with self.assertRaises(AdapterError): ExecutionRecord(FrozenJSON.of(value))
        report=o.agent.ledger.report()
        first=next(iter(report['observed_fixture_outputs'].values()))
        first['observed']['message_sha256']='wrong'
        with self.assertRaises(AdapterError): RawUsageLedger.restore(report)

    def test_shared_original_and_AP_recommendation_deduplicate_across_arms(self):
        b,_,rb,_=execute()
        a,_,ra,_=execute('A',A1)
        p,_,rp,_=execute('P',A1,PACKET)
        self.assertEqual(rb.value.copy()['observed'],ra.value.copy()['observed'])
        self.assertEqual(ra.value.copy()['decision']['recommendation'],rp.value.copy()['decision']['recommendation'])
        pooled=RawUsageLedger()
        for o in (b,a,p):
            for row in o.agent.ledger.report()['observed_fixture_outputs'].values():
                observed=row['observed']
                pooled.record_output(ObservedModelOutput(observed['record_id'],observed['component'],FrozenJSON.of(observed['message'])),row['test_units'])
        self.assertEqual(len(pooled.outputs),2)
        self.assertEqual(pooled.report()['test_units'],4)

    def test_guards_offline_and_no_unexpected_attempts(self):
        self.assertTrue(all(x['blocked'] for x in guard.negative_tests()))
        self.assertEqual(guard.EVENTS,[])


def write_demo(destination):
    cases = {}
    for name,action,packet in [('B',A0,None),('A_noop',A0,None),('A',A1,None),('P',A1,PACKET)]:
        o,_,record,_ = execute(name,action,packet)
        first = request(o)
        saved = checkpoint(o,C)
        if name == 'P':
            private = destination.parent / '.runtime'
            (private / 'restart_checkpoint.json').write_text(saved.text)
            (private / 'restart_expected.json').write_text(canonical({'request_sha256':digest(first.payload),
                'official_state_sha256':digest(backend.orch_state(o,False)), 'ledger_sha256':digest(o.agent.ledger.report())}))
        restored,_ = restore(saved)
        next_boundary(o)
        second = request(o)
        cases[name] = {'fixture':True,'mode':'scripted_fixture','observed_proposal':record.value.copy()['observed'],
                       'intervention_decision':record.value.copy()['decision'],'execution_record':record.value.copy(),
                       'derived_execution_history':backend.dump(o.trajectory),'first_actor_request':first.export(),
                       'second_actor_request':second.export(),'restore_first_request_equal':request(restored).bytes==first.bytes,
                       'usage_ledger':o.agent.ledger.report(),'terminal_effect':None,'causal_effect':None}
    report = {'status':'PASS_OFFLINE_SCRIPTED_ADAPTER_ONLY','fixture':True,'source_commit':'4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699',
              'actual_model_calls':0,'provider_runtime':'UNCONDITIONALLY_BLOCKED','provider_format':'UNTESTED',
              'claim':'No effectiveness or causal effect measured. Scripted fixtures only.', 'cases':cases}
    (destination/'demonstration.json').write_text(json.dumps(report,indent=2)+'\n')

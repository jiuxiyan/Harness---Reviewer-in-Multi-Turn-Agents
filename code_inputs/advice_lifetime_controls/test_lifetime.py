"""Authored scripts only. These tests assert operational invariants, not behavior."""
import copy
import json
import pathlib
import unittest
from unittest.mock import patch

import backend_checks as backend
import no_api_guard as guard
from offline_backend import restore_checkpoint
from interventions import FrozenJSON, canonical, digest, critique_packet
from renderer import (AdapterError, INTRO, raw, records_from_json, ProviderBlocked,
                      ControllerReceiptRendererV1)
import adapter as frozen
import lifetime as life
from tau2.data_model.message import AssistantMessage, UserMessage, SystemMessage
from tau2.environment.environment import Environment
from tau2.orchestrator.orchestrator import Role

ROOT = json.loads((backend.R/'results/task_0_checkpoint.json').read_text())
A0 = {'name':ROOT['pending_proposal']['tool_calls'][0]['name'],
      'arguments':ROOT['pending_proposal']['tool_calls'][0]['arguments']}
A1 = {'name':'get_details_by_id','arguments':{'id':'L1002'}}
PACKET = critique_packet('SCRIPTED FIXTURE: Execute the target line-details call once; this is action-local advice.')
PERSISTENT = 'Keep mobile data working while finishing the remaining speed investigation.'


def prepare():
    o, task = restore_checkpoint(ROOT)
    frozen.bind_agent(o, 'common')
    # Explicitly authored three-boundary fixture, not a naturally generated suffix.
    o.agent.queue.insert(1, AssistantMessage(role='assistant',content='SCRIPTED FIXTURE: Please confirm whether you need anything else.'))
    o.user.queue[1].content += ' ' + PERSISTENT
    o.user.queue.insert(2, UserMessage(role='user',content='SCRIPTED FIXTURE: Continue with the final summary.'))
    return o, task


def raw_draw(o, action=A1, scope='action_local', condition='normal_tool_return', target=None, packet=PACKET, instruction='execute_target_call'):
    return canonical({'selected_action':action, 'packet':packet,
        'declaration':{'target_action_id':target or life.execution_id(o.message,action),
                       'scope':scope,'instruction':instruction,'close_condition':condition}})


def execute(**kwargs):
    o, task = prepare()
    q = raw_draw(o, **kwargs)
    d = life.capture_draw(o, 'draw:' + digest(q), q)
    r = life.execute_draw(o,d,'root-0',0)
    return o, task, d, r


def req(o):
    return o.agent.request_for(o.message,o.agent_state)


def event(p):
    m = [m for m in p.payload.copy()['messages'] if m['role']=='system' and m.get('content','').startswith(INTRO)]
    assert len(m)==1
    return json.loads(m[0]['content'][len(INTRO):])


def erase_status(p):
    data=p.payload.copy()
    for m in data['messages']:
        if m['role']=='system' and m.get('content','').startswith(INTRO):
            e=json.loads(m['content'][len(INTRO):])
            if 'advice_lifetime_header' in e:
                e['advice_lifetime_header']['status']='STATUS'
            m['content']=INTRO+canonical(e)
    return data


def base_req(o):
    return frozen.ReceiptAwareOfflineAgent.request_for(o.agent,o.message,o.agent_state)


def make_forks(**kwargs):
    o, task, d, r = execute(**kwargs)
    life.advance_to_next_boundary(o)
    saved=life.checkpoint(o,ROOT)
    branches={a:life.fork(saved,a)[0] for a in life.ARMS}
    return o, saved, branches, d, r


class LifetimeTests(unittest.TestCase):
    def test_public_integration_binding(self):
        here=pathlib.Path(__file__).parent
        freeze=json.loads((here/'public_integration_freeze.json').read_text())
        import hashlib
        self.assertEqual(hashlib.sha256((here/'PLAN.md').read_bytes()).hexdigest(),freeze['plan_sha256'])

    def test_first_exposure_byte_identical_P_R_C(self):
        o,_,d,r=execute()
        base=base_req(o); records=records_from_json(o.agent_state.receipt_records_json)
        views=[life.project(base,records,d,a,0) for a in life.ARMS]
        self.assertEqual(len({v.bytes for v in views}),1)
        self.assertEqual(event(views[0])['advice_lifetime_header']['status'],life.STATUSES['neutral'])
        self.assertEqual(canonical(event(views[0])['extra_packet']).encode(),canonical(PACKET).encode())

    def test_P0_is_exact_frozen_adapter_not_new_P(self):
        o,_,d,r=execute(); base=base_req(o)
        p0=life.project(base,records_from_json(o.agent_state.receipt_records_json),d,'P0',0)
        self.assertEqual(base.bytes,p0.bytes)
        self.assertNotEqual(base.bytes,req(o).bytes)
        self.assertNotIn('advice_lifetime_header',event(p0))

    def test_declared_actual_success_only_after_one_response(self):
        o,_,d,r=execute()
        self.assertEqual(life.closure_reason(d,r),'public_call_requirement_fulfilled')
        self.assertEqual(o.agent_state.actor_boundary_count,0)
        life.advance_to_next_boundary(o)
        c=life.fork(life.checkpoint(o,ROOT),'C')[0]
        self.assertEqual(event(req(c))['advice_lifetime_header']['status'],life.STATUSES['consumed'])

    def test_two_and_three_boundaries_exact_P_C_status_only(self):
        common,saved,branches,d,r=make_forks()
        for boundary in (1,2):
            p,c=branches['P'],branches['C']
            self.assertEqual(p.agent_state.actor_boundary_count,boundary)
            self.assertEqual(erase_status(req(p)),erase_status(req(c)))
            self.assertNotEqual(req(p).bytes,req(c).bytes)
            self.assertEqual(len(req(p).bytes),len(req(c).bytes))
            self.assertEqual(canonical(event(req(p))['extra_packet']).encode(),canonical(event(req(c))['extra_packet']).encode())
            self.assertEqual(event(req(p))['execution_receipt'],event(req(c))['execution_receipt'])
            if boundary==1:
                for o in branches.values(): life.advance_to_next_boundary(o)
        for o in branches.values():
            o.step();o._check_termination()
            self.assertEqual(o.agent_state.actor_boundary_count,3)

    def test_R_removes_whole_packet_and_wrapper_only(self):
        _,_,branches,_,_=make_forks()
        p,r=event(req(branches['P'])),event(req(branches['R']))
        self.assertEqual(r,{'execution_receipt':p['execution_receipt'],'extra_packet':{}})
        for o in branches.values():
            self.assertIn(PERSISTENT,req(o).payload.text)
            self.assertEqual(len(records_from_json(o.agent_state.receipt_records_json)),1)

    def test_failure_C_stays_byte_exact_P(self):
        _,_,branches,d,r=make_forks(action={'name':'get_details_by_id','arguments':{'id':'DOES_NOT_EXIST_PUBLIC_FAKE_ID'}})
        self.assertTrue(r.public_receipt()['tool_result']['error'])
        self.assertEqual(life.closure_reason(d,r),'actual_tool_failure')
        self.assertEqual(req(branches['P']).bytes,req(branches['C']).bytes)
        self.assertEqual(branches['C'].num_errors,1)
        self.assertEqual(event(req(branches['R']))['extra_packet'],{})

    def test_mixed_ongoing_unresolved_declarations_remain_exact_P(self):
        for scope in ('mixed','ongoing','unresolved'):
            with self.subTest(scope=scope):
                _,_,branches,d,r=make_forks(scope=scope)
                self.assertEqual(req(branches['P']).bytes,req(branches['C']).bytes)
                self.assertEqual(life.closure_reason(d,r),'scope_not_action_local')

    def test_unknown_condition_and_target_do_not_close(self):
        for kwargs in ({'condition':'goal_is_fixed'},{'target':'different-public-call'},{'instruction':'keep_network_good'}):
            _,_,branches,d,r=make_forks(**kwargs)
            self.assertEqual(req(branches['P']).bytes,req(branches['C']).bytes)

    def test_semantic_violation_logged_not_oracle_filtered(self):
        o,_=prepare();packet=critique_packet('SCRIPTED MIXED PROSE: Execute the call and keep this rule for all future steps.')
        q=raw_draw(o,packet=packet)
        d=life.capture_draw(o,'violating-prose',q,'scope_violation_observed')
        r=life.execute_draw(o,d,'scope-audit')
        life.advance_to_next_boundary(o)
        c=life.fork(life.checkpoint(o,ROOT),'C')[0]
        self.assertEqual(event(req(c))['advice_lifetime_header']['status'],life.STATUSES['consumed'])
        report=life.all_draw_report([d])
        self.assertEqual(report['n_draws'],1);self.assertEqual(report['excluded_draws'],0)
        self.assertEqual(report['draws'][0]['semantic_audit'],'scope_violation_observed')

    def test_malformed_or_out_of_scope_draws_fallback_once(self):
        rows=[]
        for q_kind in ('malformed','mutation','bad_arg','missing_declaration','bad_packet'):
            o,_=prepare(); q=json.loads(raw_draw(o))
            if q_kind=='mutation': q['selected_action']={'name':'toggle_airplane_mode','arguments':{}}
            if q_kind=='bad_arg': q['selected_action']['arguments']['id']=42
            if q_kind=='missing_declaration': q.pop('declaration')
            if q_kind=='bad_packet': q['packet']={'bad':'packet'}
            text='{' if q_kind=='malformed' else canonical(q)
            d=life.capture_draw(o,q_kind,text); rows.append(d)
            with patch.object(o.environment,'get_response',wraps=o.environment.get_response) as spy:
                r=life.execute_draw(o,d,q_kind)
                self.assertEqual(spy.call_count,1)
            self.assertFalse(d.accepted);self.assertEqual(r.public_receipt()['executed_action'],A0)
            self.assertEqual(event(req(o))['extra_packet'],{})
            self.assertEqual(o.agent.ledger.report()['test_units'],4)
        report=life.all_draw_report(rows)
        self.assertEqual(report['n_draws'],5);self.assertEqual(report['resamples'],0)
        self.assertEqual(report['excluded_draws'],0)

    def test_unchanged_action_remains_draw_and_can_have_feedback(self):
        o,_,d,r=execute(action=A0)
        self.assertEqual(d.value.copy()['classification'],'unchanged')
        self.assertEqual(event(req(o))['extra_packet'],PACKET)

    def test_no_redraw_after_captured_execution(self):
        o,_,d,r=execute()
        with self.assertRaises(AdapterError):life.capture_draw(o,'again',d.value.copy()['raw_q'])
        with self.assertRaises(AdapterError):life.execute_draw(o,d,'again')

    def test_late_or_stale_contract_rejected_before_execution(self):
        o,_=prepare();d=life.capture_draw(o,'early',raw_draw(o))
        o.step_count+=1
        with self.assertRaises(AdapterError):life.execute_draw(o,d,'stale')

    def test_exact_source_binding_rejects_modified_declaration(self):
        o,_,d,r=execute();v=d.value.copy();v['declaration']['scope']='mixed'
        with self.assertRaises(AdapterError):life.CapturedDraw(FrozenJSON.of(v))

    def test_renders_and_failed_queue_do_not_consume_exposure(self):
        o,_,_,_=execute();before=backend.orch_state(o,False);ledger=o.agent.ledger.report()
        for _ in range(3): req(o)
        self.assertEqual(before,backend.orch_state(o,False))
        q=copy.deepcopy(o.agent.queue);o.agent.queue=[]
        with self.assertRaises(AdapterError):o.agent.generate_next_message(o.message,o.agent_state)
        self.assertEqual(o.agent_state.actor_boundary_count,0)
        self.assertEqual(o.agent.ledger.report(),ledger)
        o.agent.queue=q
        restored,_=life.restore(life.checkpoint(o,ROOT))
        self.assertEqual(req(o).bytes,req(restored).bytes)
        self.assertEqual(restored.agent_state.actor_boundary_count,0)

    def test_failed_output_validation_atomic_ledger_and_queue(self):
        o,_,_,_=execute();o.agent.queue[0]=UserMessage(role='user',content='wrong role')
        before=o.agent.ledger.report();queue=backend.dump(o.agent.queue)
        with self.assertRaises(AdapterError):o.agent.generate_next_message(o.message,o.agent_state)
        self.assertEqual(o.agent.ledger.report(),before)
        self.assertEqual(backend.dump(o.agent.queue),queue)
        self.assertEqual(o.agent_state.actor_boundary_count,0)

    def test_counterfactual_neutral_header_probe_changes_only_status(self):
        o,_,d,r=execute(scope='ongoing');base=base_req(o);records=records_from_json(o.agent_state.receipt_records_json)
        main=life.project(base,records,d,'P',1)
        probe=life.project(base,records,d,'P',1,neutral_rewording_probe=True)
        self.assertNotEqual(main.bytes,probe.bytes)
        self.assertEqual(erase_status(main),erase_status(probe))
        self.assertEqual(len(main.bytes),len(probe.bytes))
        self.assertNotEqual(event(probe)['advice_lifetime_header']['status'],life.STATUSES['consumed'])

    def test_counterfactual_probe_cannot_override_consumed_header(self):
        o,_,d,r=execute()
        with self.assertRaises(AdapterError):life.project(base_req(o),records_from_json(o.agent_state.receipt_records_json),d,'C',1,neutral_rewording_probe=True)

    def test_fresh_fork_one_official_restore_and_common_history(self):
        common,saved,branches,_,_=make_forks()
        with patch.object(Environment,'set_state',autospec=True,side_effect=Environment.set_state) as spy:
            restored,_=life.fork(saved,'C',1)
            self.assertEqual(spy.call_count,1)
        self.assertEqual(backend.orch_state(common,False),backend.orch_state(restored,False))
        self.assertEqual(common.agent.native_events,restored.agent.native_events)
        self.assertTrue(any(e['from_role']=='user' for e in common.agent.native_events.copy()))
        self.assertTrue(any(e['from_role']=='env' for e in common.agent.native_events.copy()))

    def test_second_and_third_boundary_restore_complete_state(self):
        _,_,branches,_,_=make_forks()
        for o in branches.values():
            for boundary in (1,2):
                saved=life.checkpoint(o,ROOT);r,_=life.restore(saved)
                self.assertEqual(backend.orch_state(o,False),backend.orch_state(r,False))
                self.assertEqual(req(o).bytes,req(r).bytes)
                self.assertEqual(o.agent.ledger.report(),r.agent.ledger.report())
                self.assertEqual(o.agent.native_events,r.agent.native_events)
                if boundary==1:life.advance_to_next_boundary(o)

    def test_shared_prefix_costs_dedup_actor_reviewer_and_user(self):
        common,saved,branches,_,_=make_forks()
        for o in branches.values():life.advance_to_next_boundary(o)
        report=life.pooled_usage(list(branches.values()))
        outputs=report['physical_deduplicated']['observed_fixture_outputs']
        self.assertEqual(sum(k.startswith('review:') for k in outputs),1)
        self.assertEqual(sum(':actor:1' in k for k in outputs),1)
        self.assertEqual(sum(':actor:2' in k for k in outputs),3)
        users=[e for e in report['native_event_captures'].values() if e['from_role']=='user']
        self.assertEqual(len(users),5)  # Two shared user events; one independent event per suffix.
        self.assertEqual(report['physical_user_fixture_test_units'],5)
        self.assertEqual(report['physical_deduplicated']['actual_model_calls'],0)
        self.assertIsNone(report['physical_deduplicated']['real_token_usage'])

    def test_suffixes_are_fresh_queues_without_cross_branch_future(self):
        common,saved,branches,_,_=make_forks()
        branches['C'].user.queue[0].content='SCRIPTED C-ONLY USER FUTURE'
        life.advance_to_next_boundary(branches['C'])
        self.assertIn('C-ONLY USER FUTURE',req(branches['C']).payload.text)
        self.assertNotIn('C-ONLY USER FUTURE',req(branches['P']).payload.text)
        self.assertNotIn('C-ONLY USER FUTURE',saved.text)

    def test_multiple_prefix_and_suffix_ids_preserve_nondeterminism_warning(self):
        o,_=prepare();d=life.capture_draw(o,'different-root',raw_draw(o));life.execute_draw(o,d,'root',2)
        life.advance_to_next_boundary(o)
        a,_=life.fork(life.checkpoint(o,ROOT),'C',3)
        c=a.agent.lifetime_context.copy()
        self.assertEqual((c['common_repeat'],c['suffix_repeat']),(2,3))
        self.assertEqual(c['randomness']['provider_determinism'],'not_assumed')
        self.assertIn(':common:2:suffix:3:C',a.agent.branch_id)

    def test_terminal_common_prefix_remains_recorded_no_fork(self):
        o,_,d,r=execute();o.max_steps=o.step_count+1
        life.advance_to_next_boundary(o)
        self.assertTrue(o.done)
        self.assertEqual(o.agent_state.actor_boundary_count,1)
        self.assertEqual(life.all_draw_report([d])['n_draws'],1)
        # Native termination may be at an actor-output boundary, so no forced checkpoint/fork.
        self.assertEqual(len(o.agent.ledger.requests),1)

    def test_user_receives_native_history_no_packet_or_status(self):
        common,_,branches,_,_=make_forks()
        for o in [common,*branches.values()]:
            user=canonical(backend.dump(o.user_state))
            self.assertNotIn('advice_lifetime_header',user)
            self.assertNotIn(PACKET['critique'],user)
            self.assertFalse(any(type(m) is SystemMessage for m in o.trajectory))

    def test_no_private_oracle_path_or_privileged_fields(self):
        with patch.object(backend,'vector',side_effect=AssertionError('Oracle must not run')):
            common,_,branches,_,_=make_forks()
        for o in branches.values():
            text=req(o).payload.text
            for key in ('goal_vector','evaluation_criteria','private_checkpoint','semantic_audit'):
                self.assertNotIn(key,text)

    def test_provider_blocked_even_with_approval_flag(self):
        o,_,_,_=execute()
        with self.assertRaises(ProviderBlocked):o.agent.generate_live(approved=True,provider='x')

    def test_tampered_restore_rejected(self):
        o,_,_,_=execute();saved=life.checkpoint(o,ROOT).copy()
        saved['payload']['context']['arm']='C'
        with self.assertRaises(AdapterError):life.restore(FrozenJSON.of(saved))

    def test_duplicate_draw_identity_conflict_rejected(self):
        o,_=prepare();a=life.capture_draw(o,'same',raw_draw(o));other,_=prepare();b=life.capture_draw(other,'same',raw_draw(other,scope='mixed'))
        with self.assertRaises(AdapterError):life.all_draw_report([a,b])
        self.assertEqual(life.all_draw_report([a,a])['n_draws'],1)


    def test_capture_itself_prohibits_redraw_before_execution(self):
        o,_=prepare();d=life.capture_draw(o,'single',raw_draw(o))
        with self.assertRaises(AdapterError):life.capture_draw(o,'redraw',raw_draw(o,scope='mixed'))
        life.execute_draw(o,d,'single')

    def test_failed_request_retry_persists_without_expiring(self):
        o,_,d,_=execute();before=req(o).bytes
        life.record_failed_request(o,'retry-1');life.record_failed_request(o,'retry-1')
        self.assertEqual(len(o.agent.ledger.requests),1)
        restored,_=life.restore(life.checkpoint(o,ROOT))
        self.assertEqual(req(restored).bytes,before)
        self.assertEqual(restored.agent_state.actor_boundary_count,0)
        life.advance_to_next_boundary(restored)
        self.assertEqual(restored.agent_state.actor_boundary_count,1)
        self.assertEqual(len(restored.agent.ledger.requests),2)
        self.assertEqual(life.all_draw_report([d])['resamples'],0)

    def test_private_canary_in_new_declaration_cannot_reach_actor(self):
        for field in ('scope','instruction','condition','target'):
            o,_=prepare();o.agent.private_canaries=('SECRET_CANARY_17',)
            q=raw_draw(o,**{field:'SECRET_CANARY_17'})
            d=life.capture_draw(o,'canary-'+field,q)
            self.assertFalse(d.accepted)
            life.execute_draw(o,d,'canary')
            self.assertNotIn('SECRET_CANARY_17',req(o).payload.text)

    def test_canary_policy_survives_restore_and_checks_projection(self):
        o,_,_,_=execute();o.agent.private_canaries=('SECRET_CANARY_18',)
        r,_=life.restore(life.checkpoint(o,ROOT))
        self.assertEqual(r.agent.private_canaries,('SECRET_CANARY_18',))
        r.message.content += ' SECRET_CANARY_18'
        with self.assertRaises(ValueError):req(r)

    def test_pool_rejects_same_draw_id_with_different_declarations(self):
        a,_=prepare();da=life.capture_draw(a,'conflict',raw_draw(a));life.execute_draw(a,da,'root-a')
        b,_=prepare();db=life.capture_draw(b,'conflict',raw_draw(b,scope='mixed'));life.execute_draw(b,db,'root-b')
        with self.assertRaises(AdapterError):life.pooled_usage([a,b])

    def test_missing_native_event_fails_restore_even_with_rehashed_envelope(self):
        common,saved,_,_,_=make_forks();v=saved.copy()
        v['payload']['native_events'].pop()
        v['sha256']=digest(v['payload'])
        with self.assertRaises(AdapterError):life.restore(FrozenJSON.of(v))


    def test_changed_recommendation_identity_rejected(self):
        o,_,d,r=execute();v=r.value.copy()
        v['decision']['recommendation']['record_id']='not-the-raw-draw'
        changed=type(r)(FrozenJSON.of(v))
        with self.assertRaises(AdapterError):life.verify_binding(d,changed)

    def test_native_event_role_and_ownership_rejected(self):
        _,saved,_,_,_=make_forks()
        for field,value in (('from_role','user'),('capture_id','other-branch:native-step:99'),('to_role','env')):
            v=saved.copy();v['payload']['native_events'][0][field]=value
            v['sha256']=digest(v['payload'])
            with self.assertRaises(AdapterError):life.restore(FrozenJSON.of(v))

    def test_pool_rejects_branch_ownership_collision(self):
        a,_=prepare();da=life.capture_draw(a,'draw-a',raw_draw(a));life.execute_draw(a,da,'same-branch')
        b,_=prepare();db=life.capture_draw(b,'draw-b',raw_draw(b,scope='mixed'));life.execute_draw(b,db,'same-branch')
        with self.assertRaises(AdapterError):life.pooled_usage([a,b])

    def test_multilingual_packet_whitespace_bytes_unchanged(self):
        packet=critique_packet('SCRIPTED FIXTURE:  查询线路。\nKeep  double spaces and café.\t')
        o,_,d,r=execute(packet=packet);base=base_req(o);records=records_from_json(o.agent_state.receipt_records_json)
        for arm in ('P','C'):
            p=life.project(base,records,d,arm,1)
            self.assertEqual(canonical(event(p)['extra_packet']).encode('utf-8'),canonical(packet).encode('utf-8'))



def write_demo(here):
    common,saved,branches,d,r=make_forks()
    first,_,_,_=execute()
    report={'mode':'scripted_fixture','effect_claims':False,'provider_tokens_matched':False,
            'draw_report':life.all_draw_report([d]),'first_request':req(first).export(),
            'closure_reason':life.closure_reason(d,r),'branches':{}}
    for arm,o in branches.items():
        report['branches'][arm]={'second_request':req(o).export()}
        (here/'.runtime'/f'{arm}_second.json').write_text(life.checkpoint(o,ROOT).text)
        life.advance_to_next_boundary(o)
        report['branches'][arm]['third_request']=req(o).export()
        (here/'.runtime'/f'{arm}_third.json').write_text(life.checkpoint(o,ROOT).text)
    report['usage']=life.pooled_usage(list(branches.values()))
    (here/'results/demonstration.json').write_text(json.dumps(report,indent=2)+'\n')


def restore_probe(here):
    checks={}
    for arm in life.ARMS:
        for boundary in ('second','third'):
            saved=FrozenJSON((here/'.runtime'/f'{arm}_{boundary}.json').read_text())
            o,_=life.restore(saved)
            expected=saved.copy()['payload']['adapter_checkpoint']['payload']
            checks[f'{arm}_{boundary}_full_state']=backend.orch_state(o,False)==expected['official_state']
            checks[f'{arm}_{boundary}_request']=digest(req(o).payload)==saved.copy()['payload']['request_sha256']
            checks[f'{arm}_{boundary}_ledger']=o.agent.ledger.report()==expected['ledger']
            checks[f'{arm}_{boundary}_events']=o.agent.native_events.copy()==saved.copy()['payload']['native_events']
            before=o.agent_state.actor_boundary_count
            o.step();o._check_termination()
            checks[f'{arm}_{boundary}_valid_response_once']=o.agent_state.actor_boundary_count==before+1
    checks['no_unexpected_guard_events']=not guard.EVENTS
    return checks

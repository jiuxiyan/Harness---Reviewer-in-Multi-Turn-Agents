"""Offline-only lifetime overlay. All upstream imports require the frozen guard."""
from __future__ import annotations
import copy
import hashlib
import json
import sys
from dataclasses import dataclass

if 'no_api_guard' not in sys.modules:
    raise RuntimeError('Use the guarded launch.py; upstream imports are not standalone')

from interventions import FrozenJSON, canonical, digest, parse_json, check_privacy
from renderer import (AdapterError, ActorRequestProjection, ObservedModelOutput,
                      RawUsageLedger, INTRO, action_of, execution_id, records_from_json,
                      validate_packet, raw)
import adapter as frozen
from tau2.environment.toolkit import ToolType, get_tool_types

VERSION = 'advice-lifetime-v1-scripted'
ARMS = ('P', 'R', 'C')
STATUSES = {
    'neutral': 'Applicability status unchanged; retain the original advice packet.',
    'consumed': 'Target call requirement fulfilled; retain advice as history only.',
    'neutral_rewording_probe': 'Advice applicability unchanged; keep the original reviewer packet.',
}
WIDTH = max(map(len, STATUSES.values()))
STATUSES = {key: value.ljust(WIDTH) for key, value in STATUSES.items()}
DECLARATION_KEYS = {'target_action_id', 'scope', 'instruction', 'close_condition'}


def nonempty(value):
    return type(value) is str and bool(value.strip())


@dataclass(frozen=True)
class CapturedDraw:
    """Public gate is frozen before execution; prose audit is separate, never a gate."""
    value: FrozenJSON

    def __post_init__(self):
        if type(self.value) is not FrozenJSON:
            raise AdapterError('Draw must be immutable')
        v = self.value.copy()
        fields = {'version', 'draw_id', 'raw_q', 'raw_sha256', 'declaration', 'classification',
                  'selected_action', 'packet', 'proposal_sha256', 'captured_step',
                  'semantic_audit', 'resamples', 'mode'}
        if set(v) != fields or v['version'] != VERSION or v['mode'] != 'scripted_fixture':
            raise AdapterError('Unknown draw schema')
        if not nonempty(v['draw_id']) or type(v['raw_q']) is not str or v['resamples'] != 0:
            raise AdapterError('Invalid all-draw identity')
        if hashlib.sha256(v['raw_q'].encode()).hexdigest() != v['raw_sha256']:
            raise AdapterError('Raw draw changed')
        if v['classification'] not in {'valid_changed', 'unchanged', 'invalid', 'out_of_scope'}:
            raise AdapterError('Unknown public classification')
        if v['semantic_audit'] not in {'not_audited', 'no_violation_observed', 'scope_violation_observed'}:
            raise AdapterError('Unknown outcome-blind audit label')
        if v['classification'] in {'valid_changed', 'unchanged'}:
            q = parse_json(v['raw_q'])
            if set(q) != {'selected_action', 'packet', 'declaration'}:
                raise AdapterError('Captured valid draw shape changed')
            if any(q[k] != v[k] for k in ('selected_action','packet','declaration')):
                raise AdapterError('Captured public fields changed')
            if set(v['declaration']) != DECLARATION_KEYS or any(not nonempty(x) for x in v['declaration'].values()):
                raise AdapterError('Declaration changed')
            validate_packet(v['packet'])
        elif v['packet'] or v['declaration'] is not None:
            raise AdapterError('Fallback must not emit advice')

    @property
    def accepted(self):
        return self.value.copy()['classification'] in {'valid_changed', 'unchanged'}


def capture_draw(o, draw_id, raw_q, semantic_audit='not_audited'):
    """Capture every draw exactly once. No oracle argument, callback, or resampling."""
    if type(o.agent_state) is not frozen.ReceiptAwareState or o.agent_state.actor_boundary_count or o.agent_state.receipt_records_json != '[]':
        raise AdapterError('Capture must precede execution at the original slot')
    if getattr(o.agent, 'lifetime_context', None) is not None or getattr(o.agent, 'pending_draw', None) is not None:
        raise AdapterError('One draw per root/repetition; redraw is prohibited')
    a0 = action_of(o.message)
    classification, selected, packet, declaration = 'invalid', a0, {}, None
    try:
        q = parse_json(raw_q)
        if not isinstance(q, dict) or set(q) != {'selected_action', 'packet', 'declaration'}:
            raise ValueError('Public draw shape')
        action = q['selected_action']; dec = q['declaration']
        if not isinstance(dec, dict) or set(dec) != DECLARATION_KEYS or any(not nonempty(x) for x in dec.values()):
            raise ValueError('Public declaration shape')
        validate_packet(q['packet'])
        if not q['packet']:
            raise ValueError('Accepted review requires a recorded packet')
        check_privacy(q, o.agent.private_canaries)
        if not isinstance(action, dict) or set(action) != {'name','arguments'} or type(action['name']) is not str or not isinstance(action['arguments'], dict):
            raise ValueError('Public action shape')
        catalog = {t.name: t for t in o.agent.tools}
        import backend_checks as backend
        allowed = set(json.loads((backend.R / 'results/read_tool_summary.json').read_text())['read_tool_names'])
        if action['name'] not in allowed or action['name'] not in catalog or get_tool_types(o.environment.tools).get(action['name']) != ToolType.READ:
            classification = 'out_of_scope'
        else:
            params = catalog[action['name']].params
            if set(action['arguments']) - set(params.model_json_schema().get('properties', {})):
                raise ValueError('Unknown public arguments')
            params.model_validate(action['arguments'], strict=True)
            classification = 'unchanged' if action == a0 else 'valid_changed'
            selected, packet, declaration = action, q['packet'], dec
    except (ValueError, TypeError, KeyError):
        classification, selected, packet, declaration = 'invalid', a0, {}, None
    captured = CapturedDraw(FrozenJSON.of({
        'version': VERSION, 'draw_id': draw_id, 'raw_q': raw_q,
        'raw_sha256': hashlib.sha256(raw_q.encode()).hexdigest(),
        'declaration': declaration, 'classification': classification,
        'selected_action': selected, 'packet': packet,
        'proposal_sha256': digest(raw(o.message)), 'captured_step': o.step_count,
        'semantic_audit': semantic_audit, 'resamples': 0, 'mode': 'scripted_fixture',
    }))
    o.agent.pending_draw = captured
    return captured


def verify_binding(draw, record):
    v, r = draw.value.copy(), record.value.copy()
    if v['proposal_sha256'] != r['decision']['proposal_sha256'] or v['selected_action'] != r['decision']['selected_action'] or v['packet'] != r['packet']:
        raise AdapterError('Draw, action and actual receipt binding differs')
    if draw.accepted:
        expected = {'selected_action': v['selected_action'], 'packet': v['packet']}
        if r['decision']['recommendation']['record_id'] != 'review:' + v['draw_id'] + ':' + v['raw_sha256']:
            raise AdapterError('Recommendation identity is not the complete raw draw')
        if r['decision']['recommendation']['message'] != expected:
            raise AdapterError('Original captured recommendation changed')
    elif r['decision']['source'] != 'original':
        raise AdapterError('Invalid draw must use original-action fallback')


def closure_reason(draw, record):
    """Only immutable public fields and actual adapter-bound result are inspected."""
    verify_binding(draw, record)
    if not draw.accepted:
        return 'fallback_no_packet'
    d = draw.value.copy()['declaration']
    if d['scope'] != 'action_local':
        return 'scope_not_action_local'
    if d['instruction'] != 'execute_target_call' or d['close_condition'] != 'normal_tool_return':
        return 'unresolved_public_condition'
    if d['target_action_id'] != record.call_id:
        return 'unresolved_target'
    receipt = record.public_receipt()
    if receipt['tool_result']['error'] is not False:
        return 'actual_tool_failure'
    return 'public_call_requirement_fulfilled'


def project(base, records, draw, arm, valid_responses, *, neutral_rewording_probe=False, private_canaries=()):
    """A canonical body is never rewritten. P0 is exactly the frozen base payload."""
    if arm not in (*ARMS, 'P0') or type(valid_responses) is not int or valid_responses < 0:
        raise AdapterError('Invalid lifetime policy')
    if len(records) != 1:
        raise AdapterError('One immutable execution record required')
    record = records[0]
    reason = closure_reason(draw, record)
    if arm == 'P0':
        if neutral_rewording_probe:
            raise AdapterError('P0 is the unchanged frozen renderer')
        return base
    payload = base.payload.copy()
    matches = [m for m in payload['messages'] if m['role'] == 'system' and m.get('content','').startswith(INTRO)]
    if len(matches) != 1:
        raise AdapterError('Exactly one receipt position required')
    m = matches[0]
    event = parse_json(m['content'][len(INTRO):])
    if event != {'execution_receipt': record.public_receipt(), 'extra_packet': draw.value.copy()['packet']}:
        raise AdapterError('Base projection changed')
    if event['extra_packet']:
        if arm == 'R' and valid_responses >= 1:
            event['extra_packet'] = {}
        else:
            status = 'consumed' if arm == 'C' and valid_responses >= 1 and reason == 'public_call_requirement_fulfilled' else 'neutral'
            if neutral_rewording_probe:
                if status != 'neutral':
                    raise AdapterError('Neutral wording control cannot alter a consumed status')
                status = 'neutral_rewording_probe'
            event['advice_lifetime_header'] = {
                'version': VERSION,
                'declaration': draw.value.copy()['declaration'],
                'status': STATUSES[status],
            }
    m['content'] = INTRO + canonical(event)
    check_privacy(payload, private_canaries)
    return ActorRequestProjection(FrozenJSON.of(payload), base.source_messages_sha256,
                                  base.purpose, base.provider_acceptance)


class LifetimeOfflineAgent(frozen.ReceiptAwareOfflineAgent):
    def __init__(self, *, lifetime_context, **kwargs):
        super().__init__(**kwargs)
        self.lifetime_context = lifetime_context
        self.native_events = FrozenJSON.of([])

    def generate_next_message(self, message, state):
        # Stage ledger/queue changes; a failed validation is not a valid exposure.
        old_ledger, old_queue = self.ledger, copy.deepcopy(self.queue)
        self.ledger = RawUsageLedger.restore(old_ledger.report())
        try:
            return super().generate_next_message(message, state)
        except Exception:
            self.ledger, self.queue = old_ledger, old_queue
            raise

    def request_for(self, message, state):
        base = super().request_for(message, state)
        c = self.lifetime_context.copy()
        draw = CapturedDraw(FrozenJSON.of(c['draw']))
        return project(base, records_from_json(state.receipt_records_json), draw,
                       c['arm'], state.actor_boundary_count, private_canaries=self.private_canaries)


def context(draw, prefix_id, arm='P', common_repeat=0, suffix_repeat=None):
    if arm not in ARMS or not nonempty(prefix_id) or type(common_repeat) is not int or common_repeat < 0:
        raise AdapterError('Invalid repetition identity')
    if suffix_repeat is not None and (type(suffix_repeat) is not int or suffix_repeat < 0):
        raise AdapterError('Invalid suffix repetition')
    return FrozenJSON.of({'version': VERSION, 'arm': arm, 'draw': draw.value.copy(),
                          'prefix_id': prefix_id, 'common_repeat': common_repeat,
                          'suffix_repeat': suffix_repeat,
                          'randomness': {'environment_seed': 0, 'provider_seed': None,
                                         'provider_determinism': 'not_assumed',
                                         'mode': 'scripted_fixture_not_a_sample'}})


def upgrade(o, c):
    v = c.copy()
    if set(v) != {'version','arm','draw','prefix_id','common_repeat','suffix_repeat','randomness'} or v['version'] != VERSION:
        raise AdapterError('Unknown persisted lifetime context')
    expected = context(CapturedDraw(FrozenJSON.of(v['draw'])), v['prefix_id'], v['arm'], v['common_repeat'], v['suffix_repeat'])
    if expected != c:
        raise AdapterError('Context or randomness bookkeeping changed')
    old = o.agent
    old_events = getattr(old, 'native_events', FrozenJSON.of([]))
    o.agent = LifetimeOfflineAgent(lifetime_context=c, queue=old.queue,
        branch_id=old.branch_id, ledger=old.ledger, private_canaries=old.private_canaries,
        tools=old.tools, domain_policy=old.domain_policy, llm=old.llm, llm_args=old.llm_args)
    o.agent.native_events = old_events
    return o


def execute_draw(o, draw, prefix_id, common_repeat=0):
    """Freeze context before invoking one official action. No redraw on any result."""
    v = draw.value.copy()
    if getattr(o.agent, 'pending_draw', None) != draw or getattr(o.agent, 'lifetime_context', None) is not None or v['proposal_sha256'] != digest(raw(o.message)) or v['captured_step'] != o.step_count:
        raise AdapterError('Draw was not captured at this still-pending boundary')
    c = context(draw, prefix_id, common_repeat=common_repeat)
    upgrade(o, c)
    o.agent.branch_id = f'{prefix_id}:common:{common_repeat}'
    if draw.accepted:
        rec = ObservedModelOutput('review:' + v['draw_id'] + ':' + v['raw_sha256'], 'reviewer',
             FrozenJSON.of({'selected_action': v['selected_action'], 'packet': v['packet']}))
        record, _ = frozen.select_and_execute(o, v['selected_action'], source='reviewer_fixture', packet=v['packet'], recommendation=rec)
    else:
        # Every invalid draw remains a charged, immutable fixture capture, not an exclusion.
        rec = ObservedModelOutput('review:' + v['draw_id'] + ':' + v['raw_sha256'], 'reviewer', FrozenJSON.of({'raw_q':v['raw_q']}))
        o.agent.ledger.record_output(rec, 3)
        record, _ = frozen.select_and_execute(o, v['selected_action'])
    verify_binding(draw, record)
    return record


def checkpoint(o, base_checkpoint):
    if type(o.agent) is not LifetimeOfflineAgent:
        raise AdapterError('Missing lifetime state')
    validate_events(o)
    saved = frozen.checkpoint(o, base_checkpoint)
    c = o.agent.lifetime_context
    request = o.agent.request_for(o.message, o.agent_state)
    payload = {'version': VERSION, 'adapter_checkpoint': saved.copy(),
               'context': c.copy(), 'private_canaries':list(o.agent.private_canaries), 'native_events': o.agent.native_events.copy(), 'request_sha256': digest(request.payload)}
    return FrozenJSON.of({'payload':payload, 'sha256':digest(payload)})


def restore(saved, private_canaries=()):
    v = saved.copy()
    if set(v) != {'payload','sha256'} or digest(v['payload']) != v['sha256']:
        raise AdapterError('Lifetime checkpoint integrity mismatch')
    p = v['payload']
    if set(p) != {'version','adapter_checkpoint','context','private_canaries','native_events','request_sha256'} or p['version'] != VERSION:
        raise AdapterError('Unknown lifetime checkpoint')
    if type(p['private_canaries']) is not list or any(not nonempty(x) for x in p['private_canaries']):
        raise AdapterError('Invalid canary policy')
    canaries = tuple(dict.fromkeys([*p['private_canaries'], *private_canaries]))
    o, task = frozen.restore(FrozenJSON.of(p['adapter_checkpoint']), private_canaries=canaries)
    upgrade(o, FrozenJSON.of(p['context']))
    o.agent.native_events = FrozenJSON.of(p['native_events'])
    validate_events(o)
    if digest(o.agent.request_for(o.message, o.agent_state).payload) != p['request_sha256']:
        raise AdapterError('Effective request differs after restore')
    return o, task


def fork(saved, arm, suffix_repeat=0):
    o, task = restore(saved)
    c = o.agent.lifetime_context.copy()
    if o.done or o.agent_state.actor_boundary_count != 1 or c['suffix_repeat'] is not None:
        raise AdapterError('Fork only from a live shared one-response prefix')
    new = context(CapturedDraw(FrozenJSON.of(c['draw'])), c['prefix_id'], arm, c['common_repeat'], suffix_repeat)
    upgrade(o, new)
    o.agent.branch_id = f"{c['prefix_id']}:common:{c['common_repeat']}:suffix:{suffix_repeat}:{arm}"
    return o, task


def pooled_usage(orchestrators):
    pooled = RawUsageLedger()
    logical = {}
    events = {}
    draws = []
    branch_owners = {}
    for o in orchestrators:
        ledger = o.agent.ledger
        draws.append(CapturedDraw(FrozenJSON.of(o.agent.lifetime_context.copy()['draw'])))
        validate_events(o)
        RawUsageLedger._insert(branch_owners, o.agent.branch_id, o.agent.lifetime_context.copy())
        logical[o.agent.branch_id] = ledger.report()['test_units'] + sum(e['test_units'] for e in o.agent.native_events.copy())
        for event in o.agent.native_events.copy():
            RawUsageLedger._insert(events, event['capture_id'], event)
        for key, row in ledger.outputs.items():
            pooled._insert(pooled.outputs, key, row)
        for key, row in ledger.requests.items():
            pooled._insert(pooled.requests, key, row)
    return {'all_draw_capture_identity':all_draw_report(draws), 'physical_deduplicated':pooled.report(), 'logical_deployment_test_units':logical, 'native_event_captures':events,
            'physical_user_fixture_test_units':sum(e['test_units'] for e in events.values()),
            'user_simulator_cost': 'Explicit one TEST_UNIT per scripted native user event; not provider cost or token usage.'}


def all_draw_report(draws):
    rows = {}
    for draw in draws:
        row = draw.value.copy(); key = row['draw_id']
        if key in rows and rows[key] != row:
            raise AdapterError('Conflicting draw identity; resampling forbidden')
        rows[key] = row
    return {'draws': list(rows.values()), 'n_draws':len(rows), 'resamples':0,
            'excluded_draws':0, 'semantic_classifier':'none', 'hidden_oracle_used':False}


def advance_to_next_boundary(o):
    """Execute a scripted native segment; retain actor/tool/user capture identities."""
    from tau2.orchestrator.orchestrator import Role
    while not o.done:
        o.step()
        o._check_termination()
        rows = o.agent.native_events.copy()
        event = {'capture_id':f'{o.agent.branch_id}:native-step:{o.step_count}',
                 'step':o.step_count, 'from_role':o.from_role.value, 'to_role':o.to_role.value,
                 'message':raw(o.message), 'mode':'scripted_fixture',
                 'test_units':1 if o.from_role == Role.USER else 0,
                 'actual_model_calls':0, 'provider_usage':None}
        if any(x['capture_id'] == event['capture_id'] for x in rows):
            raise AdapterError('Duplicate native capture identity')
        rows.append(event)
        o.agent.native_events = FrozenJSON.of(rows)
        if o.to_role == Role.AGENT:
            break
    return o


def validate_events(o):
    rows = o.agent.native_events.copy()
    history = [raw(m) for m in o.trajectory]
    record = records_from_json(o.agent_state.receipt_records_json)[0]
    actual = record.value.copy()['actual_result']
    positions = [i for i, m in enumerate(history) if m == actual]
    if len(positions) != 1 or [e['message'] for e in rows] != history[positions[0]+1:]:
        raise AdapterError('Native segment capture missing, duplicated, or not exact')
    c = o.agent.lifetime_context.copy()
    common_owner = f"{c['prefix_id']}:common:{c['common_repeat']}"
    owner = common_owner if c['suffix_repeat'] is None else f"{common_owner}:suffix:{c['suffix_repeat']}:{c['arm']}"
    if o.agent.branch_id != owner:
        raise AdapterError('Branch identity does not match persisted context')
    ids = set(); previous = c['draw']['captured_step'] + 1
    actor_count = 0
    for e in rows:
        if set(e) != {'capture_id','step','from_role','to_role','message','mode','test_units','actual_model_calls','provider_usage'}:
            raise AdapterError('Unknown native event record')
        if e['capture_id'] in ids or type(e['step']) is not int or e['step'] != previous + 1 or e['step'] > o.step_count:
            raise AdapterError('Native event order or identity mismatch')
        ids.add(e['capture_id']); previous = e['step']
        if e['message'] not in history or e['mode'] != 'scripted_fixture' or e['actual_model_calls'] != 0 or e['provider_usage'] is not None:
            raise AdapterError('Native event is not an actual fixture trajectory event')
        role = e['message']['role']
        expected_from = {'assistant':'agent','user':'user','tool':'env'}.get(role)
        if e['from_role'] != expected_from:
            raise AdapterError('Event role does not match its captured message')
        if role == 'tool':
            expected_to = 'agent' if e['message']['requestor'] == 'assistant' else 'user'
        else:
            expected_to = 'env' if e['message'].get('tool_calls') else ('user' if role == 'assistant' else 'agent')
        if e['to_role'] != expected_to:
            raise AdapterError('Event routing does not match its captured message')
        actor_count += int(role == 'assistant')
        event_owner = common_owner if c['suffix_repeat'] is None or actor_count <= 1 else owner
        if e['capture_id'] != f"{event_owner}:native-step:{e['step']}":
            raise AdapterError('Native event belongs to a different branch')
        if e['test_units'] != int(e['from_role'] == 'user'):
            raise AdapterError('Native event accounting changed')
    if actor_count != o.agent_state.actor_boundary_count or previous != o.step_count:
        raise AdapterError('Valid response count or event coverage differs from native state')


def record_failed_request(o, attempt_id):
    """Scripted transport-failure bookkeeping; no transport or provider is called.

    Retain the actual projected request once without inventing an output or advancing
    the exposure count. A real retry adapter and raw provider costs remain unbuilt.
    """
    if not nonempty(attempt_id):
        raise AdapterError('Failure attempt identity required')
    projection = o.agent.request_for(o.message, o.agent_state)
    o.agent.ledger.record_request(o.agent.branch_id + ':failed-attempt:' + attempt_id, projection)
    return projection
